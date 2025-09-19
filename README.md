# Dialpad Employee Status Monitor

Fast and efficient employee status monitoring for GlobalNOC using Dialpad API.

This system uses a two-script approach for optimal performance:

## 🚀 Quick Start

### 1. First-time Setup
```bash
# Install dependencies
pip3 install -r requirements.txt

# Set up your environment
cp "Configuration/.env.example" "Configuration/.env"
# Edit Configuration/.env and add your DIALPAD_BEARER_TOKEN
```

### 2. Cache GlobalNOC Users (run once or periodically)
```bash
python3 "User Status/fetch_users.py"
```
This fetches all 50+ GlobalNOC office users and saves them to `Data/users.json`

### 3. Check Employee Status (fast!)
```bash
# Summary view
python3 "User Status/fast_employee_status.py"

# Detailed table view
python3 "User Status/fast_employee_status.py" --format detailed

# Structured JSON for automation
python3 "User Status/fast_employee_status.py" --format detailed-json

# Save to file
python3 "User Status/fast_employee_status.py" --format detailed-json > Data/status.json
```

## 📁 Repository Structure

### User Status Scripts
- **`User Status/fetch_users.py`** - Fetches and caches all GlobalNOC office users
- **`User Status/fast_employee_status.py`** - Fast status checking using cached users

### Configuration & Services  
- **`Configuration/config.py`** - Configuration management and API settings
- **`Configuration/dialpad_service.py`** - Dialpad API service layer
- **`Configuration/.env`** - Environment variables (create from `.env.example`)
- **`Configuration/.env.example`** - Environment template

### Documentation & Dependencies
- **`README.md`** - Complete usage guide
- **`requirements.txt`** - Python dependencies
- **`.gitignore`** - Git ignore patterns

### Data Files
- **`Data/users.json`** - Cached user data (created by fetch script)
- **`Data/`** - Folder for all JSON output files

## 🔄 Workflow

### Daily Usage
```bash
# Quick status check (uses cache)
python3 "User Status/fast_employee_status.py" --format detailed
```

### Weekly/Monthly Cache Refresh
```bash
# Update user cache (when new employees join/leave)
python3 "User Status/fetch_users.py"

# Then continue with fast status checks
python3 "User Status/fast_employee_status.py"
```

## ⚡ Performance Benefits

| Method | Users Fetched | Time | Use Case |
|--------|---------------|------|----------|
| **Fast (cached)** | 50 (from cache) | ~30 seconds | Daily status checks |
| **Direct API** | 686+ (paginated) | ~2 minutes | Full system refresh |

## 🏢 Current Setup

- **Office**: IU GlobalNOC Office (ID: 4909043143819264)
- **Users**: 50 GlobalNOC employees
- **Total System**: 686+ users across all Indiana University

## � Output Formats

### Summary Format
```bash
python3 "User Status/fast_employee_status.py" --format summary
```
Shows totals: Available, Unavailable, No Duty Status

### Detailed Table Format  
```bash
python3 "User Status/fast_employee_status.py" --format detailed
```
Clean table with: Name, Email, Duty Status, Reason, Duration

### JSON Formats
```bash
# Raw data JSON
python3 "User Status/fast_employee_status.py" --format json

# Structured detailed JSON
python3 "User Status/fast_employee_status.py" --format detailed-json
```

## �🔧 Advanced Usage

### Custom Cache File
```bash
# Use different cache file
python3 "User Status/fetch_users.py" --output my_users.json
python3 "User Status/fast_employee_status.py" --cache my_users.json
```

### Verbose Logging
```bash
python3 "User Status/fetch_users.py" --verbose
python3 "User Status/fast_employee_status.py" --verbose
```

### Cache Age Warning
The system warns if cache is older than 24 hours. Refresh when needed:
```bash
python3 "User Status/fetch_users.py"  # Updates timestamp
```

## 📊 Employee Status Categories

- **Available**: Ready to take calls
- **Unavailable**: Not available with reasons:
  - "Off Frontline" - Not on call duty
  - "At Break" - On break
  - "Be Right Back" - Temporarily away  
  - "Ring No Answer" - Missed calls
  - "Unavailable" - General unavailable
- **No Duty Status**: Account active but no duty state set

## 🚨 Technical Notes

- **API Limitation**: Dialpad API doesn't support office filtering, so we manually filter after fetching all users
- **Rate Limits**: 1200 requests/minute - the cached approach reduces API calls significantly  
- **User Changes**: Re-run `User Status/fetch_users.py` when team members join/leave
- **Duration Tracking**: Shows how long employees have been in their current duty state