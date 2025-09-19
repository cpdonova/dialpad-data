#!/usr/bin/env python3
"""
GlobalNOC User Fetcher

This script fetches all users from the GlobalNOC office and saves them to a JSON file
for caching. This avoids having to paginate through all 686+ users every time we want
to check employee status.

Usage:
    python3 fetch_globalnoc_users.py
    python3 fetch_globalnoc_users.py --output custom_filename.json
"""

import json
import logging
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