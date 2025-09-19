#!/usr/bin/env python3
"""
Call Centers Fetcher

This script fetches all call centers for the company and filters them to show
only those associated with the configured office ID from the environment.

Usage:
    python3 fetch_call_centers.py
    python3 fetch_call_centers.py --output custom_call_centers.json
    python3 fetch_call_centers.py --all  # Show all call centers, not just office-filtered
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

class CallCentersFetcher:
    """Fetches and filters call centers for a specific office"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api = DialpadAPI(config)
        
    def fetch_call_centers(self, filter_by_office: bool = True) -> Dict[str, Any]:
        """Fetch call centers and optionally filter by office"""
        logger.info("Starting call centers fetch...")
        
        # Get all call centers
        logger.info("Fetching all call centers from Dialpad API...")
        all_call_centers = self.api.get_call_centers()
        logger.info(f"Retrieved {len(all_call_centers)} total call centers")
        
        # Get office information for context
        offices = self.api.get_offices()
        office_info = None
        for office in offices:
            if office.get('id') == self.config.office_id:
                office_info = office
                break
        
        # Filter call centers if requested
        if filter_by_office and self.config.office_id:
            logger.info(f"Filtering call centers for office ID: {self.config.office_id}")
            filtered_call_centers = []
            
            for call_center in all_call_centers:
                # Check if call center is associated with our office
                # This might be done through office_id field or other associations
                cc_office_id = call_center.get('office_id')
                if cc_office_id == self.config.office_id:
                    filtered_call_centers.append(call_center)
                    
            logger.info(f"Found {len(filtered_call_centers)} call centers for office {self.config.office_id}")
            call_centers_to_save = filtered_call_centers
        else:
            logger.info("Including all call centers (no office filtering)")
            call_centers_to_save = all_call_centers
        
        # Structure the data
        data = {
            "metadata": {
                "fetch_timestamp": datetime.now().isoformat(),
                "office_id": self.config.office_id,
                "office_name": office_info.get('name', 'Unknown') if office_info else 'Unknown',
                "total_call_centers_in_system": len(all_call_centers),
                "filtered_call_centers_count": len(call_centers_to_save),
                "filter_applied": filter_by_office,
                "api_version": "v2"
            },
            "office_info": office_info,
            "call_centers": call_centers_to_save
        }
        
        return data
    
    def save_to_file(self, data: Dict[str, Any], filename: str = "call_centers.json") -> None:
        """Save the call centers data to a JSON file in the Data folder"""
        # Ensure Data folder exists (create relative to the parent directory of the script)
        script_dir = Path(__file__).parent
        parent_dir = script_dir.parent
        data_dir = parent_dir / "Data"
        data_dir.mkdir(exist_ok=True)
        
        filepath = data_dir / filename
        
        logger.info(f"Saving {len(data['call_centers'])} call centers to {filepath}")
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"✅ Successfully saved call centers to {filepath}")
        
        # Print summary
        metadata = data['metadata']
        print(f"\n📞 CALL CENTERS SUMMARY")
        print(f"=" * 50)
        print(f"Fetch Time: {metadata['fetch_timestamp']}")
        print(f"Office: {metadata['office_name']} (ID: {metadata['office_id']})")
        print(f"Filtered Call Centers: {metadata['filtered_call_centers_count']}")
        print(f"Total System Call Centers: {metadata['total_call_centers_in_system']}")
        print(f"Filter Applied: {'Yes' if metadata['filter_applied'] else 'No (showing all)'}")
        print(f"Cache File: {filepath.absolute()}")
        
        # Show sample call centers
        if data['call_centers']:
            print(f"\n📋 CALL CENTERS:")
            for i, cc in enumerate(data['call_centers'][:10]):  # Show up to 10
                name = cc.get('name', 'Unknown')
                cc_id = cc.get('id', 'Unknown')
                office_id = cc.get('office_id', 'No office')
                print(f"  {i+1}. {name} (ID: {cc_id}) - Office: {office_id}")
            
            if len(data['call_centers']) > 10:
                print(f"  ... and {len(data['call_centers']) - 10} more call centers")
        else:
            print(f"\n⚠️  No call centers found matching the criteria")

def load_cached_call_centers(filename: str = "call_centers.json") -> Dict[str, Any]:
    """Load cached call centers from JSON file in Data folder"""
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
            raise FileNotFoundError(f"Call centers cache file {filename} not found in Data folder or current directory. Run fetch script first.")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    logger.info(f"Loaded {len(data.get('call_centers', []))} call centers from cache at {filepath}")
    return data

def main():
    """Main function to fetch and cache call centers"""
    parser = argparse.ArgumentParser(description="Fetch and cache call centers for the configured office")
    parser.add_argument('--output', '-o', default='call_centers.json',
                       help='Output filename for the cached call centers (default: call_centers.json)')
    parser.add_argument('--all', action='store_true',
                       help='Fetch all call centers, not just those for the configured office')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load configuration
        config = Config()
        
        # Create fetcher and get call centers
        fetcher = CallCentersFetcher(config)
        call_centers_data = fetcher.fetch_call_centers(filter_by_office=not args.all)
        
        # Save to file
        fetcher.save_to_file(call_centers_data, args.output)
        
        print(f"\n✅ Call centers cache created successfully!")
        print(f"📁 Cache file: {Path('Data') / args.output}")
        print(f"🔄 To update the cache, run this script again")
        
        if not args.all and call_centers_data['metadata']['filtered_call_centers_count'] == 0:
            print(f"\n💡 Tip: Try --all flag to see all call centers in the system")
        
    except Exception as e:
        logger.error(f"Error fetching call centers: {e}")
        print(f"\n❌ Failed to fetch call centers: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())