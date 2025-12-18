"""Launcher: start the BigSearch server (API + static frontend) with one command.

Usage:
    python main.py

Ensure frontend build is copied to `dist/` first. You can run:
    python sync_frontend_build.py
"""
from app import create_app
import logging
from config import CONFIG


def main():
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    print(f"Starting BigSearch Server on port {CONFIG['PORT']}...")
    app.run(host='0.0.0.0', port=CONFIG['PORT'], debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
