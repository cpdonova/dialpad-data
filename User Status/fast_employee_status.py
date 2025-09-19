#!/usr/bin/env python3
"""
Fast Employee Status Checker

This script uses cached GlobalNOC user data to quickly check employee status
without having to fetch all users from the API every time.

Usage:
    python3 fast_employee_status.py
    python3 fast_employee_status.py --format detailed
    python3 fast_employee_status.py --format detailed --sort-by-status
    python3 fast_employee_status.py --format detailed --sort-by-status --online-only
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
        self.cache_file = cache_file
        self.simplified_users = self.load_simplified_users()
        self.__init_cache_path__(cache_file)
    
    def load_simplified_users(self) -> Dict[str, Dict[str, Any]]:
        """Load simplified user data from CSV file using email as key"""
        data_dir = Path(__file__).parent.parent / "Data"
        csv_file = data_dir / "simplified_users.csv"
        
        simplified_users = {}
        
        # Load from CSV file
        if csv_file.exists():
            try:
                import csv
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Use email as the unique identifier instead of ID
                        email = row.get('email', '').strip().lower()
                        if email:
                            simplified_users[email] = row
                        else:
                            logger.warning(f"Skipping row with missing email: {row}")
                    
                    logger.info(f"Loaded {len(simplified_users)} simplified users from CSV (keyed by email)")
                    
                    # Debug: show count of users with role/focus team data (less verbose)
                    if simplified_users:
                        users_with_roles = sum(1 for user in simplified_users.values() 
                                             if user.get('Role') or user.get('role'))
                        if users_with_roles > 0:
                            logger.info(f"Found Role/Focus Team data for {users_with_roles} users")
                        
                        sample_emails = list(simplified_users.keys())[:3]
                        logger.debug(f"Sample CSV emails: {sample_emails}")
            except Exception as e:
                logger.error(f"Error loading CSV file: {e}")
        else:
            logger.warning(f"CSV file not found at {csv_file}")
        
        return simplified_users
    
    def __init_cache_path__(self, cache_file: str):
        """Initialize cache file path"""
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
            self.cached_data = load_cached_users(self.cache_file.name if hasattr(self.cache_file, 'name') else self.cache_file)
            
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
            is_online = current_status.get('is_online', False)
            
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
            
            # Get simplified user data for custom fields (using email as key)
            simplified_user = self.simplified_users.get(email.lower(), {})
            if simplified_user:
                logger.debug(f"Found simplified data for {display_name} ({email})")
            else:
                logger.debug(f"No simplified data found for {display_name} ({email})")
            
            employee_details.append({
                'name': display_name,
                'email': email,
                'status': status_text,
                'on_duty_status': on_duty_status,
                'duty_reason': duty_reason,
                'duty_hours': duty_hours,
                'account_state': account_state,
                'do_not_disturb': do_not_disturb,
                'is_online': is_online,
                'status_color': status_color,
                'devices': device_info,
                'department': user.get('department', 'N/A'),
                'title': user.get('title', 'N/A'),
                'user_id': user_id,
                # Custom fields from simplified users
                'role': simplified_user.get('Role', simplified_user.get('role', '')),
                'focus_team': simplified_user.get('Focus Team', simplified_user.get('focus_team', '')),
                'team': simplified_user.get('team', ''),
                'manager': simplified_user.get('manager', ''),
                'shift': simplified_user.get('shift', ''),
                'priority_level': simplified_user.get('priority_level', ''),
                'skills': simplified_user.get('skills', ''),
                'backup_contact': simplified_user.get('backup_contact', ''),
                'notes': simplified_user.get('notes', '')
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
    def print_detailed(data: Dict[str, Any], sort_by_status: bool = False, online_only: bool = False, group_by_team: bool = False) -> None:
        """Print detailed employee information"""
        FastStatusDisplay.print_summary(data)
        
        employees = data['employees']
        
        # Filter to online only if requested
        if online_only:
            employees = [emp for emp in employees if emp['is_online']]
            print(f"\n{Fore.CYAN}🌐 Filtered to online employees only ({len(employees)} online){Style.RESET_ALL}")
        
        if group_by_team:
            # Group employees by focus team
            teams = {}
            for emp in employees:
                focus_team = emp.get('focus_team', '') or 'No Team Assigned'
                if focus_team not in teams:
                    teams[focus_team] = []
                teams[focus_team].append(emp)
            
            # Sort teams alphabetically, but put 'No Team Assigned' last
            sorted_teams = sorted([team for team in teams.keys() if team != 'No Team Assigned'])
            if 'No Team Assigned' in teams:
                sorted_teams.append('No Team Assigned')
            
            print(f"\n{Fore.YELLOW}👥 EMPLOYEE STATUS BY FOCUS TEAM{Style.RESET_ALL}")
            if sort_by_status:
                print(f"{Fore.CYAN}📋 Sorted: Online first, then Available, Unknown, then alphabetically by status{Style.RESET_ALL}")
            
            for team in sorted_teams:
                team_employees = teams[team]
                
                # Sort within each team
                if sort_by_status:
                    def get_status_sort_key(emp):
                        if emp['on_duty_status'] == 'available':
                            return "0_available"
                        elif emp['on_duty_status'] != 'available' and emp['on_duty_status'] != 'unavailable':
                            return "1_unknown"
                        elif not emp['duty_reason'] and emp['on_duty_status'] == 'unavailable':
                            return "2_unavailable"
                        else:
                            status_text = emp['duty_reason'] if emp['duty_reason'] else emp['on_duty_status']
                            return f"2_{status_text}"
                    
                    team_employees = sorted(team_employees, key=lambda emp: (
                        0 if emp['is_online'] else 1,
                        get_status_sort_key(emp),
                        emp['name'].lower()
                    ))
                else:
                    team_employees.sort(key=lambda x: x['name'])
                
                print(f"\n{Fore.MAGENTA}🏢 {team} ({len(team_employees)} employees){Style.RESET_ALL}")
                print("=" * (len(team) + 20))
                
                headers = ['Name', 'Email', 'Role', 'Status', 'Online', 'Duration']
                table_data = []
                for emp in team_employees:
                    # Create combined status column
                    if emp['on_duty_status'] == 'available':
                        combined_status = 'Available'
                        status_color = Fore.GREEN
                    elif emp['duty_reason']:
                        combined_status = emp['duty_reason']
                        status_color = Fore.RED
                    elif emp['on_duty_status'] == 'unavailable':
                        combined_status = 'Unavailable'
                        status_color = Fore.RED
                    else:
                        combined_status = 'Unknown'
                        status_color = Fore.YELLOW
                    
                    status_display = f"{status_color}{combined_status}{Style.RESET_ALL}"
                    online_display = f"{Fore.GREEN}Online{Style.RESET_ALL}" if emp['is_online'] else f"{Fore.RED}Offline{Style.RESET_ALL}"
                    
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
                        emp.get('role', ''),
                        status_display,
                        online_display,
                        duty_time
                    ])
                
                print(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            # Original unified table format
            # Sort employees if requested
            if sort_by_status:
                def get_status_sort_key(emp):
                    """Get sort key for status: Available=0, Unknown=1, others alphabetically starting from 2"""
                    if emp['on_duty_status'] == 'available':
                        return "0_available"
                    elif emp['on_duty_status'] != 'available' and emp['on_duty_status'] != 'unavailable':
                        # This catches cases where status is neither available nor unavailable (Unknown cases)
                        return "1_unknown"
                    elif not emp['duty_reason'] and emp['on_duty_status'] == 'unavailable':
                        # Generic unavailable without specific reason
                        return "2_unavailable"
                    else:
                        # Sort other statuses alphabetically, starting from priority 2
                        status_text = emp['duty_reason'] if emp['duty_reason'] else emp['on_duty_status']
                        return f"2_{status_text}"
                
                if online_only:
                    # For online-only: sort by online first, then custom status order
                    employees = sorted(employees, key=lambda emp: (
                        0 if emp['is_online'] else 1,  # Online employees first
                        get_status_sort_key(emp),  # Custom status sorting
                        emp['name'].lower()  # Final sort by name
                    ))
                else:
                    # Default sorting: custom status order, then online first within each status
                    employees = sorted(employees, key=lambda emp: (
                        get_status_sort_key(emp),  # Custom status sorting
                        0 if emp['is_online'] else 1,  # Online first within each status group
                        emp['name'].lower()  # Final sort by name
                    ))
            
            print(f"\n{Fore.YELLOW}👥 EMPLOYEE DUTY STATUS{Style.RESET_ALL}")
            if sort_by_status:
                if online_only:
                    print(f"{Fore.CYAN}📋 Sorted: Online first, then Available, Unknown, then alphabetically by status{Style.RESET_ALL}")
                else:
                    print(f"{Fore.CYAN}📋 Sorted: Available, Unknown, then alphabetically by status{Style.RESET_ALL}")
            
            # Create table data
            table_data = []
            for emp in employees:
                # Create combined status column
                if emp['on_duty_status'] == 'available':
                    combined_status = 'Available'
                    status_color = Fore.GREEN
                elif emp['duty_reason']:
                    combined_status = emp['duty_reason']
                    status_color = Fore.RED
                elif emp['on_duty_status'] == 'unavailable':
                    combined_status = 'Unavailable'
                    status_color = Fore.RED
                else:
                    combined_status = 'Unknown'
                    status_color = Fore.YELLOW
                
                # Apply color to the combined status
                status_display = f"{status_color}{combined_status}{Style.RESET_ALL}"
                
                # Format online status with color
                online_display = f"{Fore.GREEN}Online{Style.RESET_ALL}" if emp['is_online'] else f"{Fore.RED}Offline{Style.RESET_ALL}"
                
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
                    emp.get('role', ''),
                    emp.get('focus_team', ''),
                    status_display,
                    online_display,
                    duty_time
                ])
            
            headers = ['Name', 'Email', 'Role', 'Focus Team', 'Status', 'Online', 'Duration']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    @staticmethod
    def print_detailed_json(data: Dict[str, Any], sort_by_status: bool = False, online_only: bool = False) -> None:
        """Print detailed employee information as JSON"""
        # Create detailed JSON structure
        detailed_data = {
            "metadata": data['metadata'],
            "office_info": data['office_info'],
            "summary": data['summary'],
            "generated_timestamp": datetime.now().isoformat(),
            "sorted_by_status": sort_by_status,
            "online_only": online_only,
            "employees": []
        }
        
        employees = data['employees']
        
        # Filter to online only if requested
        if online_only:
            employees = [emp for emp in employees if emp['is_online']]
        
        # Sort employees if requested (available first, then online first within each group)
        if sort_by_status:
            employees = sorted(employees, key=lambda emp: (
                0 if emp['on_duty_status'] == 'available' else
                1 if emp['on_duty_status'] == 'unavailable' else
                2,
                0 if emp['is_online'] else 1,  # Online first within each status group
                emp['name'].lower()  # Tertiary sort by name
            ))
        
        # Process employees for detailed JSON
        for emp in employees:
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
            
            # Create combined status
            if emp['on_duty_status'] == 'available':
                combined_status = 'Available'
            elif emp['duty_reason']:
                combined_status = emp['duty_reason']
            elif emp['on_duty_status'] == 'unavailable':
                combined_status = 'Unavailable'
            else:
                combined_status = 'Unknown'
            
            employee_detail = {
                "name": emp['name'],
                "email": emp['email'],
                "role": emp.get('role', ''),
                "focus_team": emp.get('focus_team', ''),
                "status": combined_status,
                "duty_status": emp['on_duty_status'],
                "duty_reason": emp['duty_reason'] or None,
                "duty_hours": emp['duty_hours'],
                "duty_duration_formatted": duty_time_formatted or None,
                "account_state": emp['account_state'],
                "do_not_disturb": emp['do_not_disturb'],
                "is_online": emp['is_online'],
                "user_id": emp['user_id'],
                # Additional custom fields
                "team": emp.get('team', ''),
                "manager": emp.get('manager', ''),
                "shift": emp.get('shift', ''),
                "priority_level": emp.get('priority_level', ''),
                "skills": emp.get('skills', ''),
                "backup_contact": emp.get('backup_contact', ''),
                "notes": emp.get('notes', '')
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
    parser.add_argument('--sort-by-status', action='store_true',
                       help='Sort employees with available/online users at the top')
    parser.add_argument('--online-only', action='store_true',
                       help='Show only employees who are currently online')
    parser.add_argument('--group-by-team', action='store_true',
                       help='Group employees by their Focus Team')
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
            display.print_detailed(status_data, sort_by_status=args.sort_by_status, online_only=args.online_only, group_by_team=args.group_by_team)
        elif args.format == 'json':
            # For raw JSON, we'll apply online filter but not sorting
            if args.online_only:
                filtered_data = status_data.copy()
                filtered_data['employees'] = [emp for emp in status_data['employees'] if emp['is_online']]
                print(json.dumps(filtered_data, indent=2, default=str))
            else:
                print(json.dumps(status_data, indent=2, default=str))
        elif args.format == 'detailed-json':
            display.print_detailed_json(status_data, sort_by_status=args.sort_by_status, online_only=args.online_only)
        
        print(f"\n{Fore.GREEN}✅ Status check completed successfully!{Style.RESET_ALL}")
        
    except Exception as e:
        logger.error(f"Error checking employee status: {e}")
        print(f"\n{Fore.RED}❌ Failed to check status: {e}{Style.RESET_ALL}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())