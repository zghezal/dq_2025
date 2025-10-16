# DQ Builder — Data Quality Management Dashboard

A Dash-based web application for building and managing data quality configurations.

## Version
v3.6

## Description
DQ Builder is a local Dash application that helps users create, manage, and monitor data quality configurations for their datasets. It provides an intuitive interface for defining quality metrics and managing DQ parameters.

## Features
- **Metric Management**: Stable metric ID field with optimized form handling
- **Dataset Selection**: Dynamic column detection with user notifications
- **Configuration Builder**: Easy-to-use interface for creating DQ configurations
- **Multi-page Navigation**: Clean navigation between Home, DQ, Build, and Configs pages

## Installation

1. Clone this repository:
```bash
git clone https://github.com/zghezal/dq_2025.git
cd dq_2025
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application locally:
```bash
python run.py
```

The application will be available at `http://localhost:5000`

## Project Structure
- `app.py` - Main application entry point
- `run.py` - Application runner
- `src/` - Source code
  - `layouts/` - UI layouts for different pages
  - `callbacks/` - Dash callbacks for interactivity
  - `utils.py` - Utility functions
  - `config.py` - Configuration settings

For detailed architecture and development information, see [replit.md](replit.md).

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Recent Improvements
- **ID métrique**: champ stable (`debounce=True`, `autoComplete=off`, `persistence=session`). Le formulaire n'est *jamais* re-généré pendant la saisie.
- **Colonnes après choix de la base**: callbacks **sans `prevent_initial_call`** et petit **toast** si aucune colonne détectée.
- Boutons *Ajouter* gardent la reconstruction si la préview est vide.
