# DQ Builder — Data Quality Management App

## Overview
DQ Builder is a Dash-based web application designed for comprehensive Data Quality (DQ) configuration management. Its primary purpose is to empower users to define, configure, and publish data quality metrics and tests for various datasets. The application streamlines the process of ensuring data integrity by allowing users to select and configure datasets with aliases, define various metric types (e.g., `row_count`, `sum`, `mean`), create diverse data quality tests (e.g., `null_rate`, `uniqueness`, `foreign_key`), and then preview and publish these configurations in either JSON or YAML format.

The business vision behind DQ Builder is to provide a user-friendly, efficient tool for data stewards and analysts to proactively manage data quality, reduce data-related errors, and improve decision-making based on reliable data. It aims to simplify a complex process, making advanced DQ configurations accessible without deep technical expertise.

## User Preferences
- I prefer clear, concise explanations and direct answers.
- I appreciate an iterative development approach, where changes are introduced incrementally.
- Please ask for my approval before implementing any major architectural changes or refactoring large portions of the codebase.
- When making changes, prioritize maintainability and readability.
- Do not make changes to the `managed_folders` directory.

## System Architecture

### UI/UX Decisions
The application utilizes `dash-bootstrap-components` for a responsive and modern user interface. Key UI/UX decisions include:
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
- **Multi-Page Structure**: Implemented with `dcc.Location` for navigation between Home (`/`), DQ Management (`/dq`), Build (`/build`), and Configurations (`/configs`) pages.
- **Dynamic URL Handling**: Uses URL query parameters to pass context (stream, project, DQ point) between pages and decode them via `urlparse.unquote()`.
- **Unique ID Generation**: Automatic generation of unique IDs for metrics (M-001, M-002...) and tests (T-001, T-002...).
- **CRUD Operations**: Full Create, Read, Update, Delete (CRUD) support for metrics and tests, including cascade deletion for metrics affecting associated foreign_key tests.
- **Local Development Stub**: `dataiku_stub.py` provides a local simulation of the Dataiku API for standalone development and testing.

### Feature Specifications
- **Dataset Management**: Selection of datasets and assignment of aliases. Currently supports local CSV files from `./datasets/`.
- **Metric Types**: `row_count`, `sum`, `mean`, `distinct_count`, `ratio`.
- **Test Types**: `null_rate`, `uniqueness`, `range`, `regex`, `foreign_key`.
- **Test Data Sources**: Tests can be configured to run on either database columns (traditional approach) or on metrics (advanced feature). Radio button interface allows users to switch between these two modes, with appropriate input fields displayed conditionally.
- **Configuration Publication**: Ability to save defined DQ configurations to managed folders in JSON or YAML format.
- **Configuration Visualization**: A dedicated page to browse, display in tabular format, and view full details (via modal) of stored configurations.
- **Inline Documentation**: Integrated help modals for all metric and test types with examples and parameter explanations.

## External Dependencies
- **dash**: The primary web application framework.
- **dash-bootstrap-components**: Used for responsive UI layouts and components.
- **PyYAML**: For handling YAML configuration file parsing and generation.