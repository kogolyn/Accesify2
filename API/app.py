"""
app.py
------
Flask server entry point for the Access Expiry Engine API.

Member 3 – API Layer

Run with:
    python api/app.py

Endpoints:
    POST /health
    POST /grant-access
    POST /validate-access
    POST /track-usage
    POST /renew-access
    POST /revoke-access
    GET  /get-record
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_cors import CORS
from routes import routes_blueprint


def create_app():
    app = Flask(__name__)

    # Allow requests from the demo HTML page (Member 4)
    CORS(app)

    # Register all routes from routes.py
    app.register_blueprint(routes_blueprint)

    return app


if __name__ == "__main__":
    app = create_app()
    print("Access Expiry Engine API running on http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)