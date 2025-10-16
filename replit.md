# DQ Builder — Data Quality Management App

## Overview
DQ Builder is a Dash-based web application designed for comprehensive Data Quality (DQ) configuration management. Its primary purpose is to empower users to define, configure, and publish data quality metrics and tests for various datasets. The application streamlines the process of ensuring data integrity by allowing users to select and configure datasets with aliases, define **Range** metrics with multi-column support, create **Range** tests with min/max validation, and then preview and publish these configurations in either JSON or YAML format.

The business vision behind DQ Builder is to provide a user-friendly, efficient tool for data stewards and analysts to proactively manage data quality, reduce data-related errors, and improve decision-making based on reliable data. It aims to simplify a complex process, making advanced DQ configurations accessible without deep technical expertise.

**Builder Navigation Flow**: All Builder access points (navbar, dashboards, buttons) redirect to a 3-step selection wizard:
1. `/select-stream` - Select data Stream
2. `/select-project` - Select Project (filtered by stream)
3. `/select-dq-point` - Select Zone (raw/trusted/sandbox from inventory)
4. `/build` - Configuration page with context parameters in URL (?stream=X&project=X&zone=X)

## User Preferences
- I prefer clear, concise explanations and direct answers.
- I appreciate an iterative development approach, where changes are introduced incrementally.
- Please ask for my approval before implementing any major architectural changes or refactoring large portions of the codebase.
- When making changes, prioritize maintainability and readability.
- Do not make changes to the `managed_folders` directory.

## System Architecture

### UI/UX Decisions
The application utilizes `dash-bootstrap-components` for a responsive and modern user interface. Key UI/UX decisions include:
- **Simplified Navigation Bar**: Minimal navigation with only essential elements:
  - **Portal STDA** branding/home link
  - **Home** link
  - **👤 Profile** link
  - **❓ Help** button for assistance
- **Dual Access System**: Two distinct entry points on the home page:
  - **Check&Drop**: Limited access for providers to deposit datasets and run DQ checks
  - **DQ Management**: Full access for DQ developers with all features (Inventory, Builder, Runner, Drop&DQ)
- A multi-page application structure with a persistent navigation bar.
- A tabbed interface for the 'Build' page, organizing configuration steps (Datasets, Metrics, Tests, Publication) for improved user experience and navigation.
- Interactive tables (`dash_table.DataTable`) for visualizing and managing metrics, tests, and published configurations.
- Use of modals for accessible inline documentation for metrics and tests, improving discoverability and understanding.
- Form enhancements with visual grouping (Cards), sensible default values, helpful placeholders, and inline help text to guide users.
- Radio button selection system in test configuration to choose between database columns or metrics as data source, with conditional rendering of appropriate input fields.

### Technical Implementations
- **Framework**: Dash 2.15.0+
- **Language**: Python 3.11
- **Configuration Format**: JSON/YAML via `PyYAML`
- **Modular Code Organization**: The application is structured into `src/` with dedicated modules for `config`, `utils`, `layouts` (UI components), and `callbacks` (business logic) to enhance maintainability and readability.
- **Multi-Page Structure**: Implemented with `dcc.Location` for navigation between:
  - Home (`/`) with dual access selection
  - Check&Drop Dashboard (`/check-drop-dashboard`) with limited features
  - DQ Management Dashboard (`/dq-management-dashboard`) with full access
  - Build (`/build`), DQ Inventory (`/dq-inventory`), Runner (`/dq-runner`), Drop&DQ (`/drop-dq`), and Configurations (`/configs`) pages
- **Dynamic URL Handling**: Uses URL query parameters to pass context (stream, project, zone) between pages and decode them via `urlparse.unquote()`.
- **Unique ID Generation**: Automatic generation of unique IDs for metrics (M-001, M-002...) and tests (T-001, T-002...).
- **CRUD Operations**: Full Create, Read, Update, Delete (CRUD) support for metrics and tests with unique ID auto-generation.
- **Local Development Stub**: `dataiku_stub.py` provides a local simulation of the Dataiku API for standalone development and testing.

### Feature Specifications
- **Dataset Management**: Selection of datasets and assignment of aliases. Currently supports local CSV files from `./datasets/`.
- **Metric Type (Simplified)**: 
  - **Range**: Only metric type available, supports multi-column selection for range-based data quality metrics
- **Test Type (Simplified)**: 
  - **Range**: Only test type available, validates that values fall within a defined min/max range
- **Test Data Sources**: Tests can be configured to run on either database columns (traditional approach) or on metrics (advanced feature). Radio button interface allows users to switch between these two modes, with appropriate input fields displayed conditionally.
- **Multi-Column Support**: Both metrics and tests support selecting multiple columns simultaneously, displayed as arrays in JSON output
- **Configuration Publication**: Ability to save defined DQ configurations to managed folders in JSON or YAML format.
- **Configuration Visualization**: A dedicated page to browse, display in tabular format, and view full details (via modal) of stored configurations.
- **Inline Documentation**: Integrated help modals for Range metric and test types with examples and parameter explanations.
- **DQ Management Actions**: Full CRUD operations on published configurations:
  - **Modifier**: Redirects to Build page with configuration pre-loaded for editing
  - **Dupliquer**: Creates a copy of the configuration with auto-generated timestamped name
  - **Renommer**: Modal-based renaming with validation to prevent filename conflicts
  - **Supprimer**: Confirmation modal before permanent deletion of configuration files

## Recent Changes (October 16, 2025)

### **Architecture Refactoring: DQ Points → Zones**
- **Replaced DQ Point abstraction** with direct zone selection from inventory:
  - **Before**: Step 3 = DQ Point (Extraction/Transformation/Chargement) with hardcoded mapping to zones
  - **After**: Step 3 = Zone (raw/trusted/sandbox) directly from `config/inventory.yaml`
- **New Inventory Functions** (`src/inventory.py`):
  - `get_zones(stream_id, project_id)` → Returns available zones with dataset counts
  - `get_datasets_for_zone(zone_id, stream_id, project_id)` → Returns datasets for a specific zone
- **Updated Page Layout** (`src/layouts/select_dq_point.py`):
  - Renamed from "Choisir le DQ Point" to "Choisir la Zone"
  - Dynamic zone dropdown populated based on stream/project context
  - Added required stores (store_datasets, inventory-datasets-store)
- **Updated Navigation** (`src/callbacks/navigation.py`):
  - URL parameters changed from `?dq_point=X` to `?zone=X`
  - Callbacks now use zone-based filtering instead of DQ Point mapping
  - Datasets automatically loaded when zone is selected

### **Earlier Changes**
- **Dynamic Inventory Loading**: Modified `src/config.py` to dynamically load streams, projects, and datasets from `config/inventory.yaml` instead of using hardcoded test data
  - Now loads real data: Stream A (P1, P2) and Stream B (P1, P3)
  - Datasets loaded from `sourcing/input/` directory
- **Simplified Navigation**: Reduced navbar to essential elements only (Home, Profile, Help button)
- **Simplified Metric/Test Types**: Removed all non-functional metric and test types, keeping only `range` for both metrics and tests
- **Fixed Multi-Column Selection**: Corrected the handling of multi-column dropdown to properly preserve all selected columns in JSON output
- **Cleaned Codebase**: Removed all references to unused types (null_rate, uniqueness, regex, foreign_key) from layouts, callbacks, and utilities
- **Updated Documentation**: Help modals now accurately reflect only the available Range metric and test types

## External Dependencies
- **dash**: The primary web application framework.
- **dash-bootstrap-components**: Used for responsive UI layouts and components.
- **PyYAML**: For handling YAML configuration file parsing and generation.