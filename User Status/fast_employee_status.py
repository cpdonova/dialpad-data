#!/usr/bin/env python3
"""
Fast Employee Status Checker

This script uses cached GlobalNOC user data to quickly check employee status
without having to fetch all users from the API every time.

Usage:
    python3 fast_employee_status.py
    python3 fast_employee_status.py --format detailed
    python3 fast_employee_status.py --cache custom_users.json
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import sys
import os
from typing import Dict, List, Any, Optional
from tabulate import tabulate
from colorama import init, Fore, Style

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Configuration'))

from config import Config
from dialpad_service import DialpadAPI
from fetch_users import load_cached_users

# Initialize colorama for cross-platform colored output
init()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FastEmployeeStatusChecker:
    """Fast employee status checker using cached user data"""
    
    def __init__(self, config: Config, cache_file: str = "users.json"):
        self.config = config
        self.api = DialpadAPI(config)
        
        # Construct path to Data folder
        script_dir = Path(__file__).parent
        parent_dir = script_dir.parent
        data_dir = parent_dir / "Data"
        self.cache_file = data_dir / cache_file
        
        # Fallback to current directory if Data folder doesn't exist yet
        if not self.cache_file.exists():
            fallback_path = Path(cache_file)
            if fallback_path.exists():
                self.cache_file = fallback_path
            else:
                self.cache_file = data_dir / cache_file  # Keep Data path for error message
        
        self.cached_data = None
        
    def load_user_cache(self) -> bool:
        """Load cached user data"""
        try:
            # Use the load_cached_users function which handles Data folder logic
            self.cached_data = load_cached_users(self.cache_file.name)
            
            # Check cache age
            fetch_time = datetime.fromisoformat(self.cached_data['metadata']['fetch_timestamp'])
            age = datetime.now() - fetch_time
            
            if age > timedelta(hours=24):
                logger.warning(f"Cache is {age} old. Consider refreshing with fetch_users.py")
            
            logger.info(f"Loaded {len(self.cached_data['users'])} users from cache (age: {age})")
            return True
            
        except FileNotFoundError:
            logger.error(f"Cache file {self.cache_file} not found. Run fetch_users.py first.")
            return False
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return False
    
    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """Get current status for a specific user"""
        try:
            url = self.config.get_api_url(f'users/{user_id}/')
            response = self.api.session.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"Error getting status for user {user_id}: {e}")
            return {}
    
    def check_all_employee_status(self) -> Dict[str, Any]:
        """Check status for all cached employees"""
        if not self.load_user_cache():
            return {}
        
        logger.info("Checking status for all GlobalNOC employees...")
        
        users = self.cached_data['users']
        employee_details = []
        
        # Status counters
        online_count = 0
        offline_count = 0
        unknown_count = 0
        
        for i, user in enumerate(users, 1):
            user_id = user.get('id')
            if not user_id:
                continue
                
            logger.debug(f"Checking user {i}/{len(users)}: {user.get('display_name', 'Unknown')}")
            
            # Get current status
            current_status = self.get_user_status(user_id)
            
            # Extract user information
            display_name = user.get('display_name', 'Unknown')
            emails = user.get('emails', [])
            email = emails[0] if emails else 'No email'
            
            # Extract state information (focus on duty status)
            account_state = current_status.get('state', 'unknown')
            on_duty_status = current_status.get('on_duty_status', 'unknown')
            duty_reason = current_status.get('duty_status_reason', '')
            do_not_disturb = current_status.get('do_not_disturb', False)
            duty_started = current_status.get('duty_status_started', '')
            
            # Determine display status and color based on duty status
            if on_duty_status == 'available':
                status_text = 'Available'
                online_count += 1
                status_color = Fore.GREEN
            elif on_duty_status == 'unavailable':
                if duty_reason:
                    status_text = f'Unavailable ({duty_reason})'
                else:
                    status_text = 'Unavailable'
                offline_count += 1
                status_color = Fore.RED
            elif account_state == 'active':
                status_text = 'Active (No Duty Status)'
                unknown_count += 1
                status_color = Fore.YELLOW
            else:
                status_text = f'Unknown ({account_state})'
                unknown_count += 1
                status_color = Fore.YELLOW
            
            # Add DND indicator
            if do_not_disturb:
                status_text += ' [DND]'
            
            # Calculate duty time information
            duty_hours = None
            if duty_started:
                try:
                    from datetime import datetime
                    duty_time = datetime.fromisoformat(duty_started.replace('Z', '+00:00'))
                    now = datetime.now(duty_time.tzinfo)
                    duty_hours = (now - duty_time).total_seconds() / 3600
                except Exception:
                    pass
            
            # Get device information
            devices = current_status.get('devices', [])
            device_info = []
            for device in devices:
                device_type = device.get('type', 'Unknown')
                device_name = device.get('name', 'Unknown')
                device_info.append(f"{device_type}: {device_name}")
            
            employee_details.append({
                'name': display_name,
                'email': email,
                'status': status_text,
                'on_duty_status': on_duty_status,
                'duty_reason': duty_reason,
                'duty_hours': duty_hours,
                'account_state': account_state,
                'do_not_disturb': do_not_disturb,
                'status_color': status_color,
                'devices': device_info,
                'department': user.get('department', 'N/A'),
                'title': user.get('title', 'N/A'),
                'user_id': user_id
            })
        
        return {
            'metadata': self.cached_data['metadata'],
            'office_info': self.cached_data['office_info'],
            'employees': employee_details,
            'summary': {
                'total': len(employee_details),
                'available': online_count,
                'unavailable': offline_count,
                'no_duty_status': unknown_count
            }
        }

class FastStatusDisplay:
    """Display employee status information in various formats"""
    
    @staticmethod
    def print_summary(data: Dict[str, Any]) -> None:
        """Print a summary of employee status"""
        metadata = data['metadata']
        office_info = data['office_info']
        summary = data['summary']
        
        print(f"\n{Fore.CYAN}============================================================")
        print(f"  FAST DIALPAD EMPLOYEE STATUS REPORT")
        print(f"============================================================{Style.RESET_ALL}")
        
        print(f"\n{Fore.BLUE}Company:{Style.RESET_ALL} Indiana University")
        print(f"{Fore.BLUE}Office:{Style.RESET_ALL} {office_info.get('name', 'Unknown')} (ID: {metadata['office_id']})")
        print(f"{Fore.BLUE}Cache Age:{Style.RESET_ALL} {metadata['fetch_timestamp']}")
        print(f"{Fore.BLUE}Generated:{Style.RESET_ALL} {datetime.now().isoformat()}")
        
        print(f"\n{Fore.YELLOW}📊 DUTY STATUS SUMMARY{Style.RESET_ALL}")
        print(f"Total Employees: {summary['total']}")
        print(f"{Fore.GREEN}Available: {summary['available']}{Style.RESET_ALL}")
        print(f"{Fore.RED}Unavailable: {summary['unavailable']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}No Duty Status: {summary['no_duty_status']}{Style.RESET_ALL}")
    
    @staticmethod
    def print_detailed(data: Dict[str, Any]) -> None:
        """Print detailed employee information"""
        FastStatusDisplay.print_summary(data)
        
        employees = data['employees']
        
        print(f"\n{Fore.YELLOW}👥 EMPLOYEE DUTY STATUS{Style.RESET_ALL}")
        
        # Create table data
        table_data = []
        for emp in employees:
            status_display = f"{emp['status_color']}{emp['status']}{Style.RESET_ALL}"
            
            # Format duty hours
            duty_time = ""
            if emp['duty_hours'] is not None:
                hours = emp['duty_hours']
                if hours < 1:
                    duty_time = f"{int(hours * 60)}m"
                elif hours < 24:
                    duty_time = f"{hours:.1f}h"
                else:
                    days = int(hours / 24)
                    remaining_hours = hours % 24
                    duty_time = f"{days}d {remaining_hours:.1f}h"
            
            table_data.append([
                emp['name'],
                emp['email'],
                status_display,
                emp['duty_reason'] or '-',
                duty_time
            ])
        
        headers = ['Name', 'Email', 'Duty Status', 'Reason', 'Duration']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    @staticmethod
    def print_detailed_json(data: Dict[str, Any]) -> None:
        """Print detailed employee information as JSON"""
        # Create detailed JSON structure
        detailed_data = {
            "metadata": data['metadata'],
            "office_info": data['office_info'],
            "summary": data['summary'],
            "generated_timestamp": datetime.now().isoformat(),
            "employees": []
        }
        
        # Process employees for detailed JSON
        for emp in data['employees']:
            # Format duty hours for JSON
            duty_time_formatted = ""
            if emp['duty_hours'] is not None:
                hours = emp['duty_hours']
                if hours < 1:
                    duty_time_formatted = f"{int(hours * 60)}m"
                elif hours < 24:
                    duty_time_formatted = f"{hours:.1f}h"
                else:
                    days = int(hours / 24)
                    remaining_hours = hours % 24
                    duty_time_formatted = f"{days}d {remaining_hours:.1f}h"
            
            employee_detail = {
                "name": emp['name'],
                "email": emp['email'],
                "duty_status": emp['on_duty_status'],
                "duty_reason": emp['duty_reason'] or None,
                "duty_hours": emp['duty_hours'],
                "duty_duration_formatted": duty_time_formatted or None,
                "account_state": emp['account_state'],
                "do_not_disturb": emp['do_not_disturb'],
                "user_id": emp['user_id']
            }
            
            detailed_data["employees"].append(employee_detail)
        
        print(json.dumps(detailed_data, indent=2, default=str))

def main():
    """Main function for fast employee status checking"""
    parser = argparse.ArgumentParser(description="Fast employee status checker using cached data")
    parser.add_argument('--format', choices=['summary', 'detailed', 'json', 'detailed-json'], 
                       default='summary', 
                       help='Output format: summary (text), detailed (table), json (raw), detailed-json (structured JSON)')
    parser.add_argument('--cache', default='users.json',
                       help='Cached users file (default: users.json)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load configuration
        config = Config()
        
        # Create status checker
        checker = FastEmployeeStatusChecker(config, args.cache)
        
        # Check employee status
        status_data = checker.check_all_employee_status()
        
        if not status_data:
            print(f"{Fore.RED}❌ Failed to load cached data or check status{Style.RESET_ALL}")
            return 1
        
        # Display results
        display = FastStatusDisplay()
        
        if args.format == 'summary':
            display.print_summary(status_data)
        elif args.format == 'detailed':
            display.print_detailed(status_data)
        elif args.format == 'json':
            display.print_json(status_data)
        elif args.format == 'detailed-json':
            display.print_detailed_json(status_data)
        
        print(f"\n{Fore.GREEN}✅ Status check completed successfully!{Style.RESET_ALL}")
        
    except Exception as e:
        logger.error(f"Error checking employee status: {e}")
        print(f"\n{Fore.RED}❌ Failed to check status: {e}{Style.RESET_ALL}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())