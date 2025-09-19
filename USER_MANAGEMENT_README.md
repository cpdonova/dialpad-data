# Simplified User Management

This directory contains simplified user data files that you can easily edit to add custom variables and information about your employees.

## Files Created

### 📄 `Data/simplified_users.json`
- Clean JSON format with all 50 GlobalNOC employees
- Easy to read and edit programmatically
- Includes custom fields for additional variables

### 📊 `Data/simplified_users.csv` 
- CSV format perfect for Excel/Google Sheets
- Same data as JSON but in spreadsheet format
- Great for bulk editing and data entry

### 🛠️ `User Status/fetch_users.py` (Enhanced)
- Now automatically creates and updates simplified user files
- Smart merging preserves your custom data when updating
- Run this to refresh both main user data and simplified files

### 👀 `view_simplified_users.py`
- View and filter users by custom variables
- Useful for testing your custom data

## Available Fields

### Standard Fields (from Dialpad API)
- `id` - Unique Dialpad user ID
- `display_name` - Full name
- `first_name` / `last_name` - Name components
- `email` - Primary email address
- `job_title` - Job title from Dialpad
- `department` - Department (if set in Dialpad)
- `phone_number` - Dialpad phone number
- `timezone` - User's timezone
- `license` - Dialpad license type
- `is_admin` - Admin status
- `state` - Account state (active/inactive)

### Custom Fields (for you to edit)
- `team` - Team/group assignment
- `manager` - Direct manager name
- `shift` - Work shift (morning/day/evening/night)
- `priority_level` - Escalation priority (high/medium/low)
- `skills` - Special skills or certifications
- `backup_contact` - Emergency backup contact
- `notes` - Additional notes or comments

## How to Add Custom Data

### Option 1: Edit CSV in Excel/Google Sheets
1. Open `Data/simplified_users.csv` in Excel or Google Sheets
2. Fill in the custom columns (team, manager, shift, etc.)
3. Save the file

### Option 2: Edit JSON directly
1. Open `Data/simplified_users.json` in a text editor
2. Find a user and update their custom fields:
   ```json
   {
     "id": "5115246465138688",
     "display_name": "Adam Williamson",
     "email": "adaadwil@iu.edu",
     "team": "Service Desk",
     "manager": "John Smith",
     "shift": "day",
     "priority_level": "high",
     "skills": "Windows, Linux, Network Troubleshooting",
     "backup_contact": "jane.doe@iu.edu",
     "notes": "Team lead for service desk operations"
   }
   ```

## Usage Examples

### View specific user
```bash
python3 view_simplified_users.py --user-id "5115246465138688"
```

### Filter by team (after you've added team data)
```bash
python3 view_simplified_users.py --team "Service Desk"
```

### Filter by manager (after you've added manager data)
```bash
python3 view_simplified_users.py --manager "John Smith"
```

### List all teams
```bash
python3 view_simplified_users.py --list-teams
```

### List all managers
```bash
python3 view_simplified_users.py --list-managers
```

## Integration with Status Reports

You can enhance your status reports to include custom variables by modifying the existing scripts to read from the simplified user files. This allows you to:

- Group employees by team in status reports
- Show manager information for escalation
- Filter by shift for operational planning
- Display priority levels for critical personnel
- Include skills for specialized issue routing

## Refreshing Data

When you need to update user data (new employees, changed info), simply run:
```bash
python3 "User Status/fetch_users.py"
```

This will:
- ✅ Fetch the latest user data from Dialpad API
- ✅ Update the main users.json cache  
- ✅ Automatically update simplified user files
- ✅ **Preserve all your custom data** while adding new users
- ✅ Show you exactly what was updated

### Smart Merging
The enhanced fetch script uses smart merging:
- **New users**: Added with empty custom fields for you to fill
- **Existing users**: Custom data preserved, API data updated
- **Removed users**: Not automatically deleted (manual cleanup if needed)

### Skip Simplified Files
If you only want to update the main cache:
```bash
python3 "User Status/fetch_users.py" --skip-simplified
```

## Tips

1. **Start Small**: Add one custom field at a time (like 'team') before expanding
2. **Use Consistent Values**: For fields like 'shift' or 'priority_level', use consistent values
3. **Backup Your Edits**: Keep a backup of your customized files before regenerating
4. **Excel Friendly**: The CSV format works great with Excel filters and sorting
5. **Version Control**: Consider adding these files to git to track changes over time