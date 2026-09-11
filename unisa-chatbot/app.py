"""Flask server for the UNISA Study Assistant rule-based chatbot.

Endpoints:
    GET  /         -> chat UI
    POST /chat     -> {"message": str, "session_id": str|null} -> response JSON
    POST /feedback -> {"session_id": str, "helpful": bool}
    GET  /health   -> {"status": "ok"}

No AI services, no database, no third-party pip packages beyond Flask.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request

from chatbot import bot, save_json, load_json, utc_now_iso

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONVERSATION_LOG = os.path.join(BASE_DIR, "conversations.log")
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.json")

app = Flask(__name__)

# Conversation logging to a plain text file (no external logging service).
logging.basicConfig(
    filename=CONVERSATION_LOG,
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger("unisa-chatbot")


@app.after_request
def add_cors_headers(response):
    """Enable permissive CORS so the UI can be served from any local origin.

    Args:
        response: The outgoing Flask response.

    Returns:
        The response with CORS headers attached.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/", methods=["GET"])
def index():
    """Serve the chat interface.

    Returns:
        The rendered ``index.html`` template.
    """
    return render_template("index.html")


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    """Handle one chat turn.

    Expects JSON ``{"message": str, "session_id": str|null}``. Always returns
    a valid response object, even on malformed input.

    Returns:
        A Flask JSON response with message, quick_replies, links, session_id.
    """
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        message = payload.get("message", "")
        session_id = payload.get("session_id")
        result = bot.respond(message, session_id)
        logger.info(
            "session=%s user=%s bot=%s",
            result.get("session_id"),
            json.dumps(str(message)[:500]),
            json.dumps(result.get("message", "")[:500]),
        )
        return jsonify(result)
    except Exception as exc:  # noqa: BLE001 - never crash the endpoint.
        logger.exception("chat endpoint error: %s", exc)
        return jsonify(bot.fallback_response("error", "")), 200


@app.route("/feedback", methods=["POST", "OPTIONS"])
def feedback():
    """Record a thumbs up/down for a session.

    Expects JSON ``{"session_id": str, "helpful": bool}``.

    Returns:
        A Flask JSON response confirming receipt.
    """
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        entries = load_json(FEEDBACK_FILE, [])
        if not isinstance(entries, list):
            entries = []
        entries.append(
            {
                "session_id": str(payload.get("session_id", ""))[:64],
                "helpful": bool(payload.get("helpful", False)),
                "timestamp": utc_now_iso(),
            }
        )
        save_json(FEEDBACK_FILE, entries[-5000:])
        return jsonify({"status": "ok", "message": "Thanks for the feedback."})
    except Exception as exc:  # noqa: BLE001
        logger.exception("feedback endpoint error: %s", exc)
        return jsonify({"status": "error", "message": "Could not save feedback."}), 200


@app.route("/health", methods=["GET"])
def health():
    """Simple liveness probe.

    Returns:
        ``{"status": "ok"}``.
    """
    return jsonify({"status": "ok"})


@app.errorhandler(404)
def not_found(_error):
    """Return a friendly JSON 404 instead of an HTML error page.

    Returns:
        A JSON error payload with status 404.
    """
    return jsonify({"status": "error", "message": "Endpoint not found."}), 404


@app.errorhandler(500)
def server_error(_error):
    """Return a friendly JSON 500 instead of a stack trace.

    Returns:
        A JSON error payload with status 500.
    """
    return jsonify({"status": "error", "message": "Server error. Please try again."}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
