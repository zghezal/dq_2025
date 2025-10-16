#!/usr/bin/env python3
# run.py — Run the Dash app locally
from app import app

if __name__ == "__main__":
    # For stability during automated tests/curl, run without the reloader
    app.run(host="0.0.0.0", port=8051, debug=False)
