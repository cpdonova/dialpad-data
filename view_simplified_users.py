#!/usr/bin/env python3
"""
Enhanced employee status checker using simplified user data with custom variables
"""
import json
import csv
import argparse
from pathlib import Path

def load_simplified_users():
    """Load simplified user data"""
    json_file = Path('Data/simplified_users.json')
    csv_file = Path('Data/simplified_users.csv')
    
    if json_file.exists():
        with open(json_file, 'r') as f:
            data = json.load(f)
            return {user['id']: user for user in data['users']}
    elif csv_file.exists():
        users = {}
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users[row['id']] = row
        return users
    else:
        print("❌ No simplified user files found. Run create_simplified_users.py first.")
        return {}

def show_user_info(user_id=None, team=None, manager=None):
    """Show user information with custom variables"""
    users = load_simplified_users()
    
    if not users:
        return
    
    # Filter users based on criteria
    filtered_users = []
    for uid, user in users.items():
        if user_id and uid != user_id:
            continue
        if team and user.get('team', '').lower() != team.lower():
            continue
        if manager and user.get('manager', '').lower() != manager.lower():
            continue
        filtered_users.append(user)
    
    if not filtered_users:
        print("No users found matching the criteria.")
        return
    
    print(f"\n📋 User Information ({len(filtered_users)} users):")
    print("=" * 80)
    
    for user in filtered_users:
        print(f"\n👤 {user['display_name']} ({user['email']})")
        print(f"   📞 Phone: {user['phone_number']}")
        print(f"   💼 Title: {user['job_title']}")
        print(f"   🏢 Department: {user['department']}")
        print(f"   📍 Timezone: {user['timezone']}")
        print(f"   🎫 License: {user['license']}")
        print(f"   🔑 Admin: {'Yes' if user.get('is_admin') else 'No'}")
        
        # Custom fields
        if user.get('team'):
            print(f"   👥 Team: {user['team']}")
        if user.get('manager'):
            print(f"   👨‍💼 Manager: {user['manager']}")
        if user.get('shift'):
            print(f"   🕐 Shift: {user['shift']}")
        if user.get('priority_level'):
            print(f"   ⭐ Priority: {user['priority_level']}")
        if user.get('skills'):
            print(f"   🛠️ Skills: {user['skills']}")
        if user.get('backup_contact'):
            print(f"   📞 Backup: {user['backup_contact']}")
        if user.get('notes'):
            print(f"   📝 Notes: {user['notes']}")

def main():
    parser = argparse.ArgumentParser(description='View simplified user data with custom variables')
    parser.add_argument('--user-id', help='Show specific user by ID')
    parser.add_argument('--team', help='Filter by team')
    parser.add_argument('--manager', help='Filter by manager')
    parser.add_argument('--list-teams', action='store_true', help='List all unique teams')
    parser.add_argument('--list-managers', action='store_true', help='List all unique managers')
    
    args = parser.parse_args()
    
    users = load_simplified_users()
    if not users:
        return 1
    
    if args.list_teams:
        teams = set(user.get('team', '') for user in users.values() if user.get('team'))
        print("📋 Teams:")
        for team in sorted(teams):
            print(f"   • {team}")
        return 0
    
    if args.list_managers:
        managers = set(user.get('manager', '') for user in users.values() if user.get('manager'))
        print("👨‍💼 Managers:")
        for manager in sorted(managers):
            print(f"   • {manager}")
        return 0
    
    show_user_info(args.user_id, args.team, args.manager)
    return 0

if __name__ == '__main__':
    exit(main())