"""CTI Sentinel Flask API. Start from project root: python -m backend.app."""
from pathlib import Path
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from backend.config.connection import DATABASE_NAME, ensure_indexes, get_client, get_db
from backend.route import register_routes


def create_app():
    # Vite's built assets, when present, are served directly by Flask.
    # In development (without dist), Flask remains an API-only server.
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    app = Flask(__name__, static_folder=str(frontend_dist / "assets") if (frontend_dist / "assets").is_dir() else None,
                static_url_path="/assets")
    # The development frontend uses Vite's /api proxy. Do not allow arbitrary
    # remote sites to call write-enabled endpoints.
    CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}})
    register_routes(app)

    @app.get("/")
    def root():
        if (frontend_dist / "index.html").is_file():
            return send_from_directory(frontend_dist, "index.html")
        return jsonify(service="CTI Sentinel API", api="/api/health", database=DATABASE_NAME)

    @app.get("/<path:page>")
    def frontend_fallback(page):
        if page.startswith("api/") or not (frontend_dist / "index.html").is_file():
            return jsonify(error="Not found"), 404
        return send_from_directory(frontend_dist, "index.html")

    @app.get("/api/health")
    def health():
        try:
            get_client().admin.command("ping")
            return jsonify(service="CTI Sentinel", backend="online", mongodb="connected", database=DATABASE_NAME)
        except Exception:
            # Keep Flask alive so the UI can explain how to fix the connection.
            return jsonify(service="CTI Sentinel", backend="online", mongodb="disconnected", database=DATABASE_NAME)

    @app.errorhandler(ValueError)
    def invalid_value(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(500)
    def server_error(_error):
        app.logger.exception("Request failed")
        return jsonify(error="Backend request failed. See the Flask terminal for details."), 500

    return app


if __name__ == "__main__":
    try:
        get_client().admin.command("ping")
        ensure_indexes(get_db())
        print(f"MongoDB connected: {DATABASE_NAME}")
    except Exception as exc:
        print(f"MongoDB unavailable ({type(exc).__name__}). API starts anyway; check MONGO_URI.")
    print("CTI Sentinel API at http://127.0.0.1:5000 | health: /api/health")
    create_app().run(host=os.getenv("FLASK_HOST", "127.0.0.1"),
                     port=int(os.getenv("FLASK_PORT", "5000")), debug=False)
