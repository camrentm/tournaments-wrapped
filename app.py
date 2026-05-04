"""
Flask entry point. Starts a local web server and opens the UI in the
user's default browser. No installation of system dependencies required.
"""

import threading
import time
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from api import StartGGError, export_to_csv, fetch_owned_tournaments, lookup_user

UI_DIR = Path(__file__).parent / "ui"

app = Flask(__name__, static_folder=str(UI_DIR))

# Holds the last fetch results so /api/save can use them
_last_results = []


@app.route("/")
def index():
    return send_from_directory(UI_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(UI_DIR, filename)


@app.route("/api/verify", methods=["POST"])
def verify():
    body = request.get_json()
    try:
        user = lookup_user(body["token"], body["slug"])
        return jsonify({"ok": True, "user_id": user["id"], "user_name": user.get("name") or body["slug"]})
    except StartGGError as exc:
        return jsonify({"ok": False, "error": str(exc)})


@app.route("/api/fetch", methods=["POST"])
def fetch():
    global _last_results
    body = request.get_json()
    try:
        tournaments = fetch_owned_tournaments(body["token"], body["slug"])
        _last_results = tournaments
        return jsonify({
            "ok": True,
            "count": len(tournaments),
            "total_attendees": sum(t["attendees"] for t in tournaments),
            "tournaments": tournaments,
        })
    except StartGGError as exc:
        return jsonify({"ok": False, "error": str(exc)})


@app.route("/api/save", methods=["POST"])
def save():
    if not _last_results:
        return jsonify({"ok": False, "error": "No results to save."})
    body = request.get_json()
    path = body.get("path", "my_startgg_tournaments.csv")
    try:
        saved = export_to_csv(_last_results, path)
        return jsonify({"ok": True, "path": saved})
    except OSError as exc:
        return jsonify({"ok": False, "error": str(exc)})


def open_browser():
    time.sleep(1)
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    print("Starting Tournaments Wrapped...")
    print("Opening http://localhost:5000 in your browser.")
    print("Press Ctrl+C to quit.\n")
    app.run(port=5000, debug=False)
