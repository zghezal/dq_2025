# DQ Builder — Data Quality Management App

## Overview
This is a Dash-based web application for managing Data Quality (DQ) configurations. The app allows users to create, configure, and publish data quality metrics and tests for datasets.

## Purpose
The DQ Builder app helps users:
- Select and configure datasets with aliases
- Define metrics (row_count, sum, mean, distinct_count, ratio)
- Create data quality tests (null_rate, uniqueness, range, regex, foreign_key)
- Preview and publish configurations in JSON or YAML format

## Project Structure
```
.
├── app.py              # Main Dash application (multi-page app)
├── webapp_app.py       # Legacy Dataiku DSS webapp version
├── dataiku_stub.py     # Local development stub for Dataiku API
├── run.py              # Application entry point
├── requirements.txt    # Python dependencies
├── datasets/          # Directory for CSV datasets
└── managed_folders/   # Directory for published configurations
```

## Technology Stack
- **Framework**: Dash 2.15.0+ with Bootstrap components
- **Python**: 3.11
- **UI**: dash-bootstrap-components for responsive layout
- **Config Format**: JSON/YAML via PyYAML

## Recent Changes (Import Setup - Oct 2025)

### Fixed Issues
1. **Multi-page callback error**: Fixed breadcrumb callback that was referencing components from other pages
   - Simplified breadcrumb callback to only use pathname
   - Added validation_layout for proper Dash multi-page support

2. **Test column callback error** (Oct 14, 2025): Fixed console error about test-col component not existing
   - Changed `build-url` pathname from Input to State in fill_test_columns and fill_test_ref_columns callbacks
   - Removed unnecessary pathname trigger that fired before components were rendered

3. **Navigation from DQ page to Build page** (Oct 14, 2025): Fixed "Créer de scratch" button navigation
   - Converted button to html.A link with Bootstrap button styling
   - Added dynamic href callback that updates based on stream/project/dq_point dropdown selections
   - URL-decode pathname in display_page callback to handle encoded query parameters

4. **Nested Location components issue** (Oct 14, 2025): Fixed URL query parameters not being passed to Build page
   - **Root cause**: Nested `dcc.Location` components (build-url, dq-url) were resetting browser URL and clearing query params
   - **Solution**: Removed all nested Location components, now only using main `dcc.Location(id="url")`
   - **URL encoding fix**: Added `urlparse.unquote()` to decode href before extracting query params (href contains %3F instead of ?)
   - **Callbacks updated**: Changed `update_ctx_banner` and `update_dataset_options` to use `Input("url","href")` with URL decoding
   - Context banner now correctly displays Stream/Project from URL parameters
   - Dataset dropdown now correctly filters datasets based on URL context

5. **Input field truncation issue** (Oct 14, 2025): Fixed ID and database fields capturing only first character
   - **Root cause**: Input fields had `debounce=True`, causing callbacks to fire only after blur/Enter, leading to stale values
   - **Solution**: Removed `debounce=True` from all Input fields (metric-id, test-id, and all text inputs)
   - **Result**: Preview updates in real-time as user types, ensuring complete values are captured when adding metrics/tests

6. **Tabbed interface for Steps 2 & 3** (Oct 14, 2025): Added tabs to organize Metrics and Tests sections
   - **Implementation**: Used dbc.Tabs to separate creation forms from defined lists
   - **Step 2 (Metrics)**: Two tabs - "➕ Créer une métrique" and "📋 Métriques définies"
   - **Step 3 (Tests)**: Two tabs - "➕ Créer un test" and "📋 Tests définis"
   - **Auto-switch**: After adding a metric/test, automatically switches to the "définies" tab to show the result
   - **Benefit**: More compact interface, reduces visual clutter once items are configured

### Setup Changes
- Created `run.py` to properly run the app on 0.0.0.0:5000
- Added `.gitignore` for Python project
- Created necessary directories (`datasets/`, `managed_folders/`)
- Configured workflow to run on port 5000 with webview output
- Set up deployment configuration for autoscale

## Running the App

### Development
The app runs automatically via the configured workflow:
```bash
python run.py
```

The app will be available at http://0.0.0.0:5000

### Deployment
Deployment is configured for autoscale mode, suitable for this stateless web application.

## App Architecture

### Multi-Page Structure
- **Home Page** (`/`): Welcome page with navigation
- **DQ Management** (`/dq`): Select stream, project, and DQ point; create or manage configurations
- **Build Page** (`/build`): Four-step wizard for creating DQ configurations
  1. Select datasets and assign aliases
  2. Define metrics
  3. Create tests
  4. Preview and publish

### Key Features
- **Dataset Management**: Uses local CSV files from `./datasets/` directory
- **Metric Types**: row_count, sum, mean, distinct_count, ratio
- **Test Types**: null_rate, uniqueness, range, regex, foreign_key
- **Publication**: Saves configurations to managed folders in JSON or YAML format
- **Local Mode**: Uses `dataiku_stub.py` to simulate Dataiku API for standalone development

## Dependencies
- dash>=2.15.0
- dash-bootstrap-components>=1.5.0
- PyYAML>=6.0.1

## Notes
- The app includes a validation_layout to support callbacks across multiple pages
- Legacy `webapp_app.py` is kept for reference but not used in this deployment
- Console warnings about React lifecycle methods are from Dash's internal React components and can be safely ignored
