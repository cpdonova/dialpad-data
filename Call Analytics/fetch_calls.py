#!/usr/bin/env python3
"""
Call Analytics Fetcher

This script fetches historical call data from the Dialpad API for analysis.
It provides options to filter by date range, limit results, and focus on
specific users or call centers.

Usage:
    python3 fetch_calls.py
    python3 fetch_calls.py --limit 100
    python3 fetch_calls.py --days 7  # Last 7 days
    python3 fetch_calls.py --start-date 2024-09-01 --end-date 2024-09-15
    python3 fetch_calls.py --office-only  # Only calls from your office users
"""

import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os
from typing import Dict, Any, List

# Add Configuration to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Configuration'))

from config import Config
from dialpad_service import DialpadAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CallAnalyticsFetcher:
    """Fetches and analyzes call data from Dialpad API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api = DialpadAPI(config)
        
        # Ensure Data directory exists
        self.data_dir = Path(__file__).parent.parent / "Data"
        self.data_dir.mkdir(exist_ok=True)
        
    def fetch_calls(self, limit: int = None, start_date: str = None, end_date: str = None, 
                   office_only: bool = False) -> Dict[str, Any]:
        """Fetch call data with optional filtering"""
        logger.info("Starting call analytics fetch...")
        
        # Convert date strings to ISO format if provided
        start_time = None
        end_time = None
        
        if start_date:
            start_time = f"{start_date}T00:00:00Z"
        if end_date:
            end_time = f"{end_date}T23:59:59Z"
            
        logger.info(f"Fetching calls from Dialpad API...")
        if limit:
            logger.info(f"  Limit: {limit} calls")
        if start_time and end_time:
            logger.info(f"  Date range: {start_date} to {end_date}")
        elif start_time:
            logger.info(f"  From date: {start_date}")
        elif end_time:
            logger.info(f"  Until date: {end_date}")
            
        # Fetch all calls
        all_calls = self.api.get_calls(
            limit=limit,
            start_time=start_time,
            end_time=end_time
        )
        
        logger.info(f"Retrieved {len(all_calls)} total calls")
        
        # Filter by office if requested
        filtered_calls = all_calls
        if office_only:
            logger.info(f"Filtering calls for office users...")
            # Load office users
            office_users = self._load_office_users()
            if office_users:
                office_user_ids = {str(user.get('id')) for user in office_users}
                filtered_calls = []
                
                for call in all_calls:
                    # Check if any participant is from our office
                    participants = call.get('participants', [])
                    for participant in participants:
                        user_id = str(participant.get('user_id', ''))
                        if user_id in office_user_ids:
                            filtered_calls.append(call)
                            break
                            
                logger.info(f"Found {len(filtered_calls)} calls involving office users")
            else:
                logger.warning("Could not load office users for filtering")
        
        # Create metadata
        metadata = {
            "fetch_time": datetime.now().isoformat(),
            "total_calls": len(filtered_calls),
            "all_calls_fetched": len(all_calls),
            "filters_applied": {
                "limit": limit,
                "start_date": start_date,
                "end_date": end_date,
                "office_only": office_only
            },
            "office_id": self.config.office_id,
            "office_name": "IU GlobalNOC Office"
        }
        
        return {
            "metadata": metadata,
            "calls": filtered_calls
        }
    
    def _load_office_users(self) -> List[Dict[str, Any]]:
        """Load cached office users"""
        users_file = self.data_dir / "users.json"
        if users_file.exists():
            try:
                with open(users_file, 'r') as f:
                    data = json.load(f)
                    return data.get('users', [])
            except Exception as e:
                logger.error(f"Error loading users cache: {e}")
        return []
    
    def save_calls(self, call_data: Dict[str, Any], output_file: str = None) -> str:
        """Save call data to JSON file"""
        if not output_file:
            output_file = "calls.json"
            
        output_path = self.data_dir / output_file
        
        logger.info(f"Saving {call_data['metadata']['total_calls']} calls to {output_path}")
        
        with open(output_path, 'w') as f:
            json.dump(call_data, f, indent=2, default=str)
        
        logger.info(f"✅ Successfully saved calls to {output_path}")
        return str(output_path)
    
    def analyze_calls(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform basic analysis on call data"""
        calls = call_data['calls']
        metadata = call_data['metadata']
        
        if not calls:
            return {"error": "No calls to analyze"}
            
        # Basic statistics
        total_calls = len(calls)
        
        # Call directions
        inbound_calls = sum(1 for call in calls if call.get('direction') == 'inbound')
        outbound_calls = sum(1 for call in calls if call.get('direction') == 'outbound')
        
        # Call durations (in seconds)
        durations = []
        for call in calls:
            duration = call.get('duration_seconds', 0)
            if duration and duration > 0:
                durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        total_duration = sum(durations)
        
        # Call states
        states = {}
        for call in calls:
            state = call.get('state', 'unknown')
            states[state] = states.get(state, 0) + 1
        
        analysis = {
            "summary": {
                "total_calls": total_calls,
                "inbound_calls": inbound_calls,
                "outbound_calls": outbound_calls,
                "calls_with_duration": len(durations),
                "average_duration_seconds": round(avg_duration, 2),
                "average_duration_minutes": round(avg_duration / 60, 2),
                "total_duration_seconds": total_duration,
                "total_duration_hours": round(total_duration / 3600, 2)
            },
            "call_states": states,
            "date_range": {
                "filters": metadata['filters_applied'],
                "fetch_time": metadata['fetch_time']
            }
        }
        
        return analysis

def main():
    parser = argparse.ArgumentParser(description='Fetch and analyze Dialpad call data')
    parser.add_argument('--limit', type=int, help='Maximum number of calls to fetch')
    parser.add_argument('--days', type=int, help='Fetch calls from last N days')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--office-only', action='store_true', 
                       help='Only include calls involving office users')
    parser.add_argument('--output', help='Output file name (default: calls.json)')
    parser.add_argument('--analyze', action='store_true', help='Show analysis summary')
    
    args = parser.parse_args()
    
    try:
        # Create fetcher
        config = Config()
        fetcher = CallAnalyticsFetcher(config)
        
        # Handle days parameter
        start_date = args.start_date
        end_date = args.end_date
        
        if args.days:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
        
        # Fetch calls
        call_data = fetcher.fetch_calls(
            limit=args.limit,
            start_date=start_date,
            end_date=end_date,
            office_only=args.office_only
        )
        
        # Save to file
        output_file = fetcher.save_calls(call_data, args.output)
        
        # Show summary
        metadata = call_data['metadata']
        print(f"\n📞 CALL ANALYTICS SUMMARY")
        print("=" * 50)
        print(f"Fetch Time: {metadata['fetch_time']}")
        print(f"Office: {metadata['office_name']} (ID: {metadata['office_id']})")
        print(f"Total Calls Retrieved: {metadata['total_calls']}")
        
        if metadata['total_calls'] != metadata['all_calls_fetched']:
            print(f"Total Calls Before Filtering: {metadata['all_calls_fetched']}")
        
        filters = metadata['filters_applied']
        print(f"Filters Applied:")
        if filters['limit']:
            print(f"  📊 Limit: {filters['limit']} calls")
        if filters['start_date'] or filters['end_date']:
            print(f"  📅 Date Range: {filters['start_date'] or 'N/A'} to {filters['end_date'] or 'N/A'}")
        if filters['office_only']:
            print(f"  🏢 Office Users Only: Yes")
        
        print(f"Cache File: {output_file}")
        
        # Show analysis if requested
        if args.analyze and call_data['calls']:
            analysis = fetcher.analyze_calls(call_data)
            summary = analysis['summary']
            
            print(f"\n📈 CALL ANALYSIS")
            print("=" * 30)
            print(f"📞 Total Calls: {summary['total_calls']}")
            print(f"📥 Inbound: {summary['inbound_calls']}")
            print(f"📤 Outbound: {summary['outbound_calls']}")
            print(f"⏱️  Average Duration: {summary['average_duration_minutes']:.1f} minutes")
            print(f"🕒 Total Talk Time: {summary['total_duration_hours']:.1f} hours")
            
            if analysis['call_states']:
                print(f"\n📋 Call States:")
                for state, count in analysis['call_states'].items():
                    print(f"  {state}: {count}")
        
        print(f"\n✅ Call analytics cache created successfully!")
        print(f"📁 Cache file: {os.path.basename(output_file)}")
        print(f"🔄 To update the cache, run this script again")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()