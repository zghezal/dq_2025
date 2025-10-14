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
├── app.py                 # Main application entry point
├── run.py                 # Production server launcher
├── dataiku_stub.py        # Local development stub for Dataiku API
├── webapp_app.py          # Legacy Dataiku DSS webapp version (not used)
├── requirements.txt       # Python dependencies
├── src/                   # Application source code (modular structure)
│   ├── config.py          # Constants and configuration (STREAMS, DATASET_MAPPING)
│   ├── utils.py           # Utility functions (helpers, data access)
│   ├── layouts/           # UI components
│   │   ├── navbar.py      # Navigation bar and stepper
│   │   ├── home.py        # Home page layout
│   │   ├── dq.py          # DQ Management page layout
│   │   ├── build.py       # Build page layout (wizard)
│   │   └── configs.py     # Configurations page layout (visualization)
│   └── callbacks/         # Business logic
│       ├── navigation.py  # Navigation and routing callbacks
│       ├── dq.py          # DQ Management page callbacks
│       ├── build.py       # Build page callbacks (datasets, metrics, tests, publication)
│       └── configs.py     # Configurations page callbacks (table display, modal)
├── datasets/              # Directory for CSV datasets
└── managed_folders/       # Directory for published configurations
```

## Technology Stack
- **Framework**: Dash 2.15.0+ with Bootstrap components
- **Python**: 3.11
- **UI**: dash-bootstrap-components for responsive layout
- **Config Format**: JSON/YAML via PyYAML

## Recent Changes

### Enhanced Metric/Test Management (Oct 14, 2025)
**CRUD Operations & Visual Improvements**: Added full management capabilities for metrics and tests
- **Auto-generated IDs**:
  - **Métriques**: Format M-001, M-002, M-003... (incrémentation automatique sans doublons)
  - **Tests**: Format T-001, T-002, T-003... (incrémentation automatique sans doublons)
  - Laissez le champ ID vide pour génération automatique
- **Metric Actions** (Onglet Visualiser):
  - ✏️ **Edit button**: Load metric into form for modification
  - 🗑️ **Delete button**: Remove metric with cascade deletion of associated tests
  - 🖨️ **Print button**: Mark metric for printing (visible for compatible types)
  - Cascade deletion logic: Automatically removes foreign_key tests that reference deleted metrics
- **Test Actions** (Onglet Visualiser):
  - ✏️ **Edit button**: Load test into form for modification
  - 🗑️ **Delete button**: Remove test from configuration
  - 📥 **Export button**: Display test as JSON for inspection or backup
- **Form Enhancements**:
  - **Visual grouping with Cards**: Parameters organized into logical sections
    - Metrics: Identification, Configuration Dataset, Filtres/Options, Prévisualisation
    - Tests: Identification, Application du test, Paramètres, Seuils/Tolérance, Référence (FK)
  - **Default values**: Sensible defaults for all fields (severity=medium, threshold=0.005, first dataset selected)
  - **Helpful placeholders**: Contextual examples in all input fields
  - **Inline help text**: Small descriptions under complex fields
- **Benefits**: 
  - Complete metric/test lifecycle management with full CRUD operations
  - Improved form usability with clear organization
  - Safer operations with cascade deletion for metrics
  - Better user guidance with defaults and examples
  - Guaranteed unique IDs with clean format
  - JSON export capability for tests

### Build Page UI Redesign (Oct 14, 2025)
**Tabbed Interface**: Transformed vertical step-by-step wizard into modern tabbed interface
- **Purpose**: Improved UX with better organization and visibility of all configuration options
- **Changes**:
  - Replaced vertical stepper with 4 main tabs (Datasets, Métriques, Tests, Publication)
  - Added interactive tables for visualizing metrics and tests
  - Metrics tab: Sub-tabs for Créer, Visualiser (table), Liste (JSON)
  - Tests tab: Sub-tabs for Créer, Visualiser (table), Liste (JSON)
  - Auto-switch to Visualiser tab after adding metrics/tests
- **Benefits**: Cleaner interface, easier navigation, better overview of configured items

### Configuration Visualization Feature (Oct 14, 2025)
**New Configurations Page**: Added tabular visualization for stored YAML/JSON configurations
- **Purpose**: Provide synthetic view of configurations (YAML alone is not user-friendly for quick overview)
- **Features**:
  - Browse all saved configurations from managed_folders/dq_params/
  - Tabular display with common parameters: ID, Type, Table/Metric, Column, Description
  - Interactive modal to view complete configuration details by clicking on table rows
  - Separate tabs for Metrics and Tests
  - Context banner showing Stream and Project information
- **Implementation**:
  - New layout: `src/layouts/configs.py`
  - New callbacks: `src/callbacks/configs.py`
  - Added navigation link in navbar
  - Uses dash_table.DataTable for interactive table display

### Code Refactoring (Oct 14, 2025)
**Modular Architecture**: Split monolithic `app.py` (925 lines) into organized modules
- **src/config.py**: Configuration constants and Dataiku client setup
- **src/utils.py**: Utility functions (data access, helpers, first() pattern matching helper)
- **src/layouts/**: UI components separated by page (navbar, home, dq, build)
- **src/callbacks/**: Business logic separated by functionality (navigation, dq, build)
- **Benefits**: Improved maintainability, clearer code organization, easier debugging
- **app.py**: Now a clean 40-line entry point that assembles the application

### Import Setup (Oct 2025)

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

7. **Pattern matching ALL bug** (Oct 14, 2025): Fixed callbacks capturing only first character instead of full values
   - **Root cause**: Dash pattern matching with `ALL` returns a string directly (not a list) when only one component matches
   - **Issue**: Using `value[0]` on string "001" returned first character "0" instead of full value "001"
   - **Solution**: Created helper function `first()` that checks if input is string or list before extraction
   - **Callbacks fixed**: preview_metric, add_metric, preview_test, add_test, fill_test_columns, fill_test_ref_columns, fill_metric_columns (7 callbacks total)
   - **Result**: All input values now captured correctly regardless of how many matching components exist

8. **Missing component error** (Oct 14, 2025): Fixed "nonexistent object" error for metric-column component
   - **Root cause**: Component `{"role":"metric-column"}` only rendered for certain metric types (sum, mean, distinct_count)
   - **Issue**: Callbacks tried to update this component even when it didn't exist for row_count or ratio types
   - **Solution**: Component now always rendered but hidden with `display: none` when not needed
   - **Result**: No more callback errors, component always exists in DOM for callbacks to target

9. **Column loading bug** (Oct 14, 2025): Fixed columns not loading for metrics and tests
   - **Root cause**: `get_columns_for_dataset()` only used Dataiku API, which fails in local mode
   - **Solution**: Added fallback to read CSV file headers when Dataiku is unavailable
   - **Result**: Columns now load correctly from local CSV files in all environments

### Setup Changes
- Created `run.py` to properly run the app on 0.0.0.0:5000
- Added `.gitignore` for Python project
- Created necessary directories (`datasets/`, `managed_folders/`)
- Configured workflow to run on port 5000 with webview output
- Set up deployment configuration for autoscale
- Refactored codebase into modular structure under `src/` directory

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

### Modular Code Organization
- **Entry Point** (`app.py`): Initializes Dash app, imports layouts and callbacks
- **Configuration** (`src/config.py`): Centralized constants and settings
- **Utils** (`src/utils.py`): Shared utility functions and helpers
- **Layouts** (`src/layouts/`): UI components organized by page
- **Callbacks** (`src/callbacks/`): Business logic organized by functionality

### Multi-Page Structure
- **Home Page** (`/`): Welcome page with navigation
- **DQ Management** (`/dq`): Select stream, project, and DQ point; create or manage configurations
- **Build Page** (`/build`): Tabbed interface for creating DQ configurations
  - **Onglet Datasets**: Select datasets and assign aliases
  - **Onglet Métriques**: Define metrics with sub-tabs (Créer, Visualiser, Liste)
  - **Onglet Tests**: Create tests with sub-tabs (Créer, Visualiser, Liste)
  - **Onglet Publication**: Preview and publish configurations
- **Configurations Page** (`/configs`): Visualize stored configurations in table format
  - Browse YAML/JSON configuration files
  - View metrics and tests in tabular format with key parameters
  - Click on rows to see complete configuration details in modal

### Key Features
- **Dataset Management**: Uses local CSV files from `./datasets/` directory
- **Metric Types**: row_count, sum, mean, distinct_count, ratio
- **Test Types**: null_rate, uniqueness, range, regex, foreign_key
- **Publication**: Saves configurations to managed folders in JSON or YAML format
- **Configuration Visualization**: Tabular view of stored YAML/JSON configs with interactive details modal
- **Local Mode**: Uses `dataiku_stub.py` to simulate Dataiku API for standalone development
- **Pattern Matching Helper**: `first()` function safely handles Dash ALL pattern matching

## Dependencies
- dash>=2.15.0
- dash-bootstrap-components>=1.5.0
- PyYAML>=6.0.1

## Notes
- The app includes a validation_layout to support callbacks across multiple pages
- Legacy `webapp_app.py` is kept for reference but not used in this deployment
- Console warnings about React lifecycle methods are from Dash's internal React components and can be safely ignored
