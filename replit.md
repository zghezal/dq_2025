# DQ Builder — Data Quality Management App

## Overview
This is a Python Dash application for managing Data Quality (DQ) configurations. It provides a web interface to build, manage, and publish data quality metrics and tests for various data streams and projects.

**Current State:** Fully functional and ready to use. The app is running on port 5000 with all dependencies installed.

## Recent Changes
- **2024-10-14:** Initial Replit setup completed
  - Installed Python 3.11 and dependencies (Dash, dash-bootstrap-components, PyYAML)
  - Created necessary directories (datasets/, managed_folders/)
  - Configured workflow to run on port 5000
  - Set up deployment configuration for autoscale
  - Created .gitignore for Python projects

## Project Architecture

### File Structure
```
.
├── app.py              # Main Dash application with Bootstrap UI
├── webapp_app.py       # Legacy Dataiku DSS webapp version
├── dataiku_stub.py     # Local development stub for Dataiku API
├── run.py              # Entry point to run the app
├── requirements.txt    # Python dependencies
├── datasets/           # Directory for CSV datasets
└── managed_folders/    # Directory for DQ configuration files
```

### Key Components
1. **Main App (app.py):** Modern Dash application with:
   - Multi-page routing (Home, DQ Management, Build)
   - Bootstrap styling for responsive UI
   - Data quality metric builder
   - Test configuration interface
   - Configuration preview and publication

2. **Dataiku Stub (dataiku_stub.py):** Local development implementation that:
   - Simulates Dataiku API for standalone use
   - Reads datasets from `./datasets/*.csv`
   - Stores configurations in `./managed_folders/`

3. **Legacy Webapp (webapp_app.py):** Older Dataiku DSS-specific version

### Features
- **Stream & Project Management:** Organize DQ configs by stream and project
- **Dataset Management:** Import datasets and assign aliases
- **Metric Builder:** Create metrics (row_count, sum, mean, distinct_count, ratio)
- **Test Builder:** Configure tests (null_rate, uniqueness, range, regex, foreign_key)
- **Preview & Export:** Preview configs in JSON/YAML and publish to managed folders

## Running the Application

### Development
The app runs automatically via the configured workflow:
- **Command:** `python run.py`
- **Port:** 5000
- **Host:** 0.0.0.0 (accessible from outside)

### Deployment
Configured for autoscale deployment:
- Deployment target: autoscale (stateless web app)
- Run command: `python run.py`

## Dependencies
- dash >= 2.15.0
- dash-bootstrap-components >= 1.5.0
- PyYAML >= 6.0.1

## Notes
- The app uses Bootstrap theming for a modern UI
- Multi-page app uses client-side routing with dcc.Location
- Data is stored locally in CSV files and managed folders
- Compatible with Dataiku DSS when deployed in that environment
