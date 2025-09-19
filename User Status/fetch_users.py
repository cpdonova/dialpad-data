#!/usr/bin/env python3
"""
GlobalNOC User Fetcher

This script fetches all users from the GlobalNOC office and saves them to a JSON file
for caching. This avoids having to paginate through all 686+ users every time we want
to check employee status.

Also creates simplified user files for easy editing of custom variables.

Usage:
    python3 fetch_globalnoc_users.py
    python3 fetch_globalnoc_users.py --output custom_filename.json
"""

import json
import logging
import csv
from datetime import datetime
from pathlib import Path
import argparse
import sys
import os
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Configuration'))

from config import Config
from dialpad_service import DialpadAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GlobalNOCUserFetcher:
    """Fetches and caches GlobalNOC office users"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api = DialpadAPI(config)
        
    def fetch_globalnoc_users(self) -> Dict[str, Any]:
        """Fetch all GlobalNOC office users and return structured data"""
        logger.info("Starting GlobalNOC user fetch...")
        
        # Get all users with pagination
        logger.info("Fetching all users from Dialpad API...")
        all_users = self.api.get_users()
        logger.info(f"Retrieved {len(all_users)} total users")
        
        # Filter for GlobalNOC office
        logger.info(f"Filtering users for office ID: {self.config.office_id}")
        globalnoc_users = self.api.filter_users_by_office(all_users, self.config.office_id)
        logger.info(f"Found {len(globalnoc_users)} GlobalNOC office users")
        
        # Get office information
        offices = self.api.get_offices()
        office_info = None
        for office in offices:
            if office.get('id') == self.config.office_id:
                office_info = office
                break
        
        # Structure the data
        cache_data = {
            "metadata": {
                "fetch_timestamp": datetime.now().isoformat(),
                "office_id": self.config.office_id,
                "office_name": office_info.get('name', 'Unknown') if office_info else 'Unknown',
                "total_users_in_system": len(all_users),
                "globalnoc_users_count": len(globalnoc_users),
                "api_version": "v2"
            },
            "office_info": office_info,
            "users": globalnoc_users
        }
        
        return cache_data
    
    def save_to_file(self, data: Dict[str, Any], filename: str = "users.json") -> None:
        """Save the user data to a JSON file in the Data folder"""
        # Ensure Data folder exists (create relative to the parent directory of the script)
        script_dir = Path(__file__).parent
        parent_dir = script_dir.parent
        data_dir = parent_dir / "Data"
        data_dir.mkdir(exist_ok=True)
        
        filepath = data_dir / filename
        
        logger.info(f"Saving {len(data['users'])} users to {filepath}")
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"✅ Successfully saved GlobalNOC users to {filepath}")
        
        # Print summary
        metadata = data['metadata']
        print(f"\n📊 GLOBALNOC USER CACHE SUMMARY")
        print(f"=" * 50)
        print(f"Fetch Time: {metadata['fetch_timestamp']}")
        print(f"Office: {metadata['office_name']} (ID: {metadata['office_id']})")
        print(f"GlobalNOC Users: {metadata['globalnoc_users_count']}")
        print(f"Total System Users: {metadata['total_users_in_system']}")
        print(f"Cache File: {filepath.absolute()}")
        
        # Show sample users
        if data['users']:
            print(f"\n👥 SAMPLE USERS:")
            for i, user in enumerate(data['users'][:5]):
                name = user.get('display_name', 'Unknown')
                email = user.get('emails', ['No email'])[0] if user.get('emails') else 'No email'
                print(f"  {i+1}. {name} ({email})")
            
            if len(data['users']) > 5:
                print(f"  ... and {len(data['users']) - 5} more users")
    
    def load_existing_simplified_users(self, data_dir: Path) -> Dict[str, Dict[str, Any]]:
        """Load existing simplified users to preserve custom data"""
        json_file = data_dir / "simplified_users.json"
        csv_file = data_dir / "simplified_users.csv"
        
        existing_users = {}
        
        # Try to load from JSON first
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    if 'users' in data:
                        existing_users = {user['id']: user for user in data['users']}
                        logger.info(f"Loaded {len(existing_users)} existing simplified users from JSON")
            except Exception as e:
                logger.warning(f"Could not load existing JSON simplified users: {e}")
        
        # Try CSV as fallback
        elif csv_file.exists():
            try:
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        existing_users[row['id']] = row
                    logger.info(f"Loaded {len(existing_users)} existing simplified users from CSV")
            except Exception as e:
                logger.warning(f"Could not load existing CSV simplified users: {e}")
        
        return existing_users
    
    def create_simplified_users(self, user_data: Dict[str, Any]) -> None:
        """Create simplified user files with smart merging to preserve custom data"""
        script_dir = Path(__file__).parent
        parent_dir = script_dir.parent
        data_dir = parent_dir / "Data"
        data_dir.mkdir(exist_ok=True)
        
        # Load existing simplified users to preserve custom data
        existing_users = self.load_existing_simplified_users(data_dir)
        
        # Create simplified user list
        simplified_users = []
        new_users_count = 0
        updated_users_count = 0
        
        for user in user_data['users']:
            # Handle emails safely
            email = ''
            if user.get('emails') and isinstance(user['emails'], list) and len(user['emails']) > 0:
                email = user['emails'][0]
            
            # Handle phone numbers safely
            phone_number = ''
            if user.get('phone_numbers') and isinstance(user['phone_numbers'], list) and len(user['phone_numbers']) > 0:
                phone_number = user['phone_numbers'][0]
            
            # Create base simplified user data
            simplified_user = {
                'id': user['id'],
                'display_name': user['display_name'],
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'email': email,
                'job_title': user.get('job_title', ''),
                'department': user.get('department', ''),
                'phone_number': phone_number,
                'timezone': user.get('timezone', ''),
                'license': user.get('license', ''),
                'is_admin': user.get('is_admin', False),
                'state': user.get('state', ''),
                # Custom fields - preserve existing data or initialize empty
                'role': '',
                'focus_team': '',
                'team': '',
                'manager': '',
                'shift': '',
                'priority_level': '',
                'skills': '',
                'backup_contact': '',
                'notes': ''
            }
            
            # Check if user already exists and preserve custom data
            if user['id'] in existing_users:
                existing_user = existing_users[user['id']]
                # Preserve all custom fields from existing data
                custom_fields = ['role', 'focus_team', 'team', 'manager', 'shift', 'priority_level', 'skills', 'backup_contact', 'notes']
                for field in custom_fields:
                    if field in existing_user and existing_user[field]:
                        simplified_user[field] = existing_user[field]
                updated_users_count += 1
            else:
                new_users_count += 1
            
            simplified_users.append(simplified_user)
        
        # Save as JSON
        json_file = data_dir / 'simplified_users.json'
        json_data = {
            'metadata': {
                'created': datetime.now().isoformat(),
                'source': 'users.json',
                'total_users': len(simplified_users),
                'new_users': new_users_count,
                'updated_users': updated_users_count,
                'description': 'Simplified user list for easy editing and custom variables'
            },
            'users': simplified_users
        }
        
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        # Save as CSV
        csv_file = data_dir / 'simplified_users.csv'
        fieldnames = list(simplified_users[0].keys())
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(simplified_users)
        
        logger.info(f"✅ Created simplified user files: {len(simplified_users)} users ({new_users_count} new, {updated_users_count} updated)")
        
        # Print summary
        print(f"\n📋 SIMPLIFIED USER FILES UPDATED")
        print(f"=" * 50)
        print(f"📄 JSON: {json_file}")
        print(f"📊 CSV:  {csv_file}")
        print(f"👥 Total Users: {len(simplified_users)}")
        print(f"🆕 New Users: {new_users_count}")
        print(f"🔄 Updated Users: {updated_users_count}")
        if existing_users:
            print(f"💾 Custom data preserved for existing users")
        
        if new_users_count > 0:
            print(f"\n🆕 NEW USERS ADDED:")
            for user in simplified_users:
                if user['id'] not in existing_users:
                    print(f"   • {user['display_name']} ({user['email']})")

def load_cached_users(filename: str = "users.json") -> Dict[str, Any]:
    """Load cached users from JSON file in Data folder"""
    # Get the script directory and construct path to Data folder
    script_dir = Path(__file__).parent
    parent_dir = script_dir.parent
    data_dir = parent_dir / "Data"
    
    # Check for file in Data folder first, then try current directory as fallback
    filepath = data_dir / filename
    if not filepath.exists():
        # Fallback to current directory for backwards compatibility
        fallback_path = Path(filename)
        if fallback_path.exists():
            filepath = fallback_path
        else:
            raise FileNotFoundError(f"Cache file {filename} not found in Data folder or current directory. Run fetch script first.")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    logger.info(f"Loaded {len(data.get('users', []))} users from cache at {filepath}")
    return data

def main():
    """Main function to fetch and cache GlobalNOC users"""
    parser = argparse.ArgumentParser(description="Fetch and cache GlobalNOC office users")
    parser.add_argument('--output', '-o', default='users.json',
                       help='Output filename for the cached users (default: users.json)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--skip-simplified', action='store_true',
                       help='Skip creating simplified user files')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load configuration
        config = Config()
        
        # Create fetcher and get users
        fetcher = GlobalNOCUserFetcher(config)
        user_data = fetcher.fetch_globalnoc_users()
        
        # Save to file
        fetcher.save_to_file(user_data, args.output)
        
        # Create simplified user files with smart merging (unless skipped)
        if not args.skip_simplified:
            logger.info("Creating simplified user files...")
            fetcher.create_simplified_users(user_data)
        
        print(f"\n✅ GlobalNOC user cache created successfully!")
        print(f"📁 Cache file: {Path(args.output).absolute()}")
        print(f"🔄 To update the cache, run this script again")
        
    except Exception as e:
        logger.error(f"Error fetching GlobalNOC users: {e}")
        print(f"\n❌ Failed to fetch users: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())