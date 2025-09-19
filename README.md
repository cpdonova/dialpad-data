# Dialpad Employee Status Monitor

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Fast and efficient employee status monitoring for GlobalNOC using Dialpad API.

This system uses a two-script approach for optimal performance, monitoring 50+ employees with sub-minute response times.

## ✨ Features

- **⚡ Fast Caching**: Monitor 50+ employees in ~30 seconds vs 2+ minutes
- **🎯 Real-Time Status**: Shows actual duty status (Available/Unavailable) with reasons
- **📊 Multiple Formats**: Summary, detailed table, and JSON outputs
- **🔒 Secure**: Environment variables and data excluded from git
- **🗂️ Organized**: Professional folder structure for easy maintenance
- **🤖 Automation-Ready**: JSON output perfect for dashboards and scripts

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

## 📊 Output Examples

### Summary View
```
📊 DUTY STATUS SUMMARY
Total Employees: 50
Available: 8
Unavailable: 40
No Duty Status: 2
```

### Detailed View
```
┌─────────────────────┬─────────────────┬──────────────────────────────┬────────────────┬────────────┐
│ Name                │ Email           │ Duty Status                  │ Reason         │ Duration   │
├─────────────────────┼─────────────────┼──────────────────────────────┼────────────────┼────────────┤
│ John Doe            │ jdoe@iu.edu     │ Available                    │ -              │ 2.3h       │
│ Jane Smith          │ jsmith@iu.edu   │ Unavailable (At Break)      │ At Break       │ 15m        │
└─────────────────────┴─────────────────┴──────────────────────────────┴────────────────┴────────────┘
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

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📋 Requirements

- Python 3.9+
- Dialpad API Bearer Token
- Network access to Dialpad API (dialpad.com)

## 🔧 Configuration

The system uses environment variables for configuration:

- `DIALPAD_BEARER_TOKEN`: Your Dialpad API bearer token (required)
- `DIALPAD_API_BASE_URL`: API endpoint (defaults to production)
- `REQUEST_TIMEOUT`: Request timeout in seconds (default: 30)

## ⚠️ Security Notes

- **Never commit** your `.env` file with actual credentials
- The `Data/` folder contains cached user information - excluded from git
- Bearer tokens should be kept secure and rotated regularly

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋 Support

For questions or issues:
- Create an issue in this repository
- Contact: Corey Donovan (cpdonova@iu.edu)