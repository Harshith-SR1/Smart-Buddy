"""WSGI entry point for production deployment.

Use with gunicorn:
    gunicorn wsgi:app --workers 4 --bind 0.0.0.0:8000

Or waitress (Windows-friendly):
    waitress-serve --port=8000 wsgi:app
"""
from server_flask import app

if __name__ == "__main__":
    app.run()
