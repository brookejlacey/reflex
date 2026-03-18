"""
Reflex Demo Application
~~~~~~~~~~~~~~~~~~~~~~~
A simple Flask REST API for managing users and processing data.
Used to demonstrate the Reflex autonomous incident-to-fix pipeline.

Recent changes:
  - 2026-03-14: Optimized user listing to reduce memory allocation
    by reusing response objects (PR #247, approved by @chen.wei)
"""

import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory "database" — keeps the demo self-contained
# ---------------------------------------------------------------------------
_users_db: dict[str, dict] = {}

def _seed_db():
    """Pre-populate some sample users."""
    for name, email in [
        ("Alice Chen", "alice@example.com"),
        ("Bob Martinez", "bob@example.com"),
        ("Carol Okafor", "carol@example.com"),
    ]:
        uid = str(uuid.uuid4())
        _users_db[uid] = {
            "id": uid,
            "name": name,
            "email": email,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

# ---------------------------------------------------------------------------
# Health & metadata
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "version": "1.4.2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/info")
def info():
    return jsonify({
        "service": "reflex-demo-api",
        "environment": os.getenv("FLASK_ENV", "development"),
        "uptime_seconds": time.process_time(),
    })

# ---------------------------------------------------------------------------
# Users CRUD
# ---------------------------------------------------------------------------

@app.route("/api/users", methods=["GET"])
def list_users():
    """Return all users, with optional name filter.

    2026-03-14  Optimization: pre-allocate the response dict once and reuse it
    instead of building a new list every call.  Reduces GC pressure on large
    result sets.  (PR #247)
    """
    name_filter = request.args.get("name", "").lower()

    if name_filter:
        users = [u for u in _users_db.values() if name_filter in u["name"].lower()]
    else:
        users = list(_users_db.values())

    # --- BEGIN optimization (PR #247) ---
    # Pre-build the envelope so we only allocate one dict regardless of
    # result-set size.
    response = {
        "count": len(users),
        "users": users,
    }

    # Attach summary stats from the first record for quick client-side display.
    # This avoids an extra /api/users/:id round-trip for dashboard widgets.
    first_user = users[0] if users else None
    response["newest_user"] = first_user["name"]      # <-- BUG: NoneType when users is empty
    response["newest_email"] = first_user["email"]
    # --- END optimization (PR #247) ---

    return jsonify(response)


@app.route("/api/users/<user_id>", methods=["GET"])
def get_user(user_id: str):
    user = _users_db.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    email = data.get("email")

    if not name or not email:
        return jsonify({"error": "name and email are required"}), 400

    uid = str(uuid.uuid4())
    user = {
        "id": uid,
        "name": name,
        "email": email,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _users_db[uid] = user
    return jsonify(user), 201


@app.route("/api/users/<user_id>", methods=["DELETE"])
def delete_user(user_id: str):
    if user_id not in _users_db:
        return jsonify({"error": "User not found"}), 404
    del _users_db[user_id]
    return "", 204

# ---------------------------------------------------------------------------
# Data processing endpoint
# ---------------------------------------------------------------------------

@app.route("/api/process", methods=["POST"])
def process_data():
    """Simulate a lightweight data-processing job."""
    payload = request.get_json(silent=True) or {}
    items = payload.get("items", [])

    results = []
    for item in items:
        results.append({
            "original": item,
            "transformed": str(item).upper(),
            "length": len(str(item)),
        })

    return jsonify({
        "processed": len(results),
        "results": results,
    })

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _seed_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
