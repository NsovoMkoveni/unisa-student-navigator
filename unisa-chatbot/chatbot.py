"""Rule-based chatbot engine for the UNISA Study Assistant.

This module is 100% deterministic: intent selection is pure keyword scoring
over hard-coded content in ``intents.json``, ``flows.json`` and
``fallback.json``. There are no models, no external calls and no randomness.

Public entry point: :meth:`Chatbot.respond`.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# Configuration constants
# --------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INTENTS_FILE = os.path.join(BASE_DIR, "intents.json")
FLOWS_FILE = os.path.join(BASE_DIR, "flows.json")
FALLBACK_FILE = os.path.join(BASE_DIR, "fallback.json")
SESSIONS_FILE = os.path.join(BASE_DIR, "sessions.json")
UNANSWERED_FILE = os.path.join(BASE_DIR, "unanswered.json")

SESSION_TIMEOUT_MINUTES = 30
MAX_INPUT_LENGTH = 500

# Global commands always win over intent scoring and always exit a flow.
GLOBAL_MENU_WORDS = {"menu", "main menu", "start over", "restart", "home"}
GLOBAL_HUMAN_WORDS = {"human", "agent", "operator", "real person", "live agent"}

# Words ignored when tokenising user input.
STOP_WORDS = {
    "a", "an", "the", "is", "are", "am", "do", "does", "did", "i", "my", "me",
    "you", "your", "to", "for", "of", "on", "in", "at", "and", "or", "it",
    "can", "please", "how", "what", "where", "when", "who", "why", "with",
    "this", "that", "be", "have", "has", "get", "want", "need",
}

_FILE_LOCK = threading.Lock()


# --------------------------------------------------------------------------
# Small file helpers
# --------------------------------------------------------------------------

def load_json(path: str, default: Any = None) -> Any:
    """Read a JSON file, returning ``default`` if it is missing or invalid.

    Args:
        path: Absolute path to the JSON file.
        default: Value returned when the file cannot be read or parsed.

    Returns:
        The parsed JSON content, or ``default``.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default if default is not None else {}


def save_json(path: str, data: Any) -> bool:
    """Write data to a JSON file atomically enough for single-node use.

    Args:
        path: Absolute path to the JSON file.
        data: JSON-serialisable content.

    Returns:
        True on success, False if the write failed (never raises).
    """
    try:
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
        return True
    except (OSError, TypeError, ValueError):
        return False


def utc_now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def parse_iso(value: str) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp, returning None when it is unusable.

    Args:
        value: Timestamp string previously produced by :func:`utc_now_iso`.

    Returns:
        A timezone-aware ``datetime``, or None.
    """
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# --------------------------------------------------------------------------
# Text normalisation
# --------------------------------------------------------------------------

def normalise(text: str) -> str:
    """Lowercase text and strip characters that are not letters/digits.

    Punctuation and emoji become single spaces so that keyword matching is
    unaffected by how the student types.

    Args:
        text: Raw user input.

    Returns:
        A lowercase, single-spaced string.
    """
    if not isinstance(text, str):
        return ""
    lowered = text.lower()
    # Keep apostrophes so "can't" survives, drop everything else non-alphanumeric.
    cleaned = re.sub(r"[^a-z0-9'\s]+", " ", lowered)
    cleaned = cleaned.replace("'", "")
    return re.sub(r"\s+", " ", cleaned).strip()


def tokenise(text: str) -> List[str]:
    """Split normalised text into meaningful word tokens.

    Args:
        text: Already-normalised text.

    Returns:
        A list of tokens with stop words removed.
    """
    return [token for token in text.split(" ") if token and token not in STOP_WORDS]


# --------------------------------------------------------------------------
# Chatbot engine
# --------------------------------------------------------------------------

class Chatbot:
    """Deterministic keyword-and-decision-tree chatbot."""

    def __init__(self) -> None:
        """Load all content files and the persisted session store."""
        self.reload_content()

    # -- content ---------------------------------------------------------

    def reload_content(self) -> None:
        """(Re)load intents, flows and fallbacks from disk.

        Call this after editing the JSON content files to pick up changes
        without restarting the server.
        """
        intents_data = load_json(INTENTS_FILE, {"intents": [], "synonyms": {}})
        self.intents: List[Dict[str, Any]] = intents_data.get("intents", [])
        self.synonyms: Dict[str, List[str]] = intents_data.get("synonyms", {})
        self.flows: Dict[str, Any] = load_json(FLOWS_FILE, {"flows": {}}).get("flows", {})
        self.fallbacks: Dict[str, Any] = load_json(FALLBACK_FILE, {})
        self.intent_index: Dict[str, Dict[str, Any]] = {
            intent["id"]: intent for intent in self.intents if "id" in intent
        }

    # -- sessions --------------------------------------------------------

    def _load_sessions(self) -> Dict[str, Any]:
        """Read the session store from disk, pruning expired sessions.

        Returns:
            A mapping of session_id -> session state.
        """
        sessions = load_json(SESSIONS_FILE, {})
        if not isinstance(sessions, dict):
            return {}
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        live: Dict[str, Any] = {}
        for key, state in sessions.items():
            if not isinstance(state, dict):
                continue
            stamp = parse_iso(state.get("timestamp", ""))
            if stamp is not None and stamp >= cutoff:
                live[key] = state
        return live

    def get_session(self, session_id: Optional[str]) -> Tuple[str, Dict[str, Any]]:
        """Fetch or create a session.

        Args:
            session_id: Client-supplied session id, possibly missing/expired.

        Returns:
            A tuple of (session_id, session state dict).
        """
        sessions = self._load_sessions()
        if not session_id or not isinstance(session_id, str) or session_id not in sessions:
            session_id = uuid.uuid4().hex[:16]
            state = {
                "current_flow": None,
                "current_step": None,
                "timestamp": utc_now_iso(),
            }
        else:
            state = sessions[session_id]
            state.setdefault("current_flow", None)
            state.setdefault("current_step", None)
        return session_id, state

    def save_session(self, session_id: str, state: Dict[str, Any]) -> None:
        """Persist one session's state, refreshing its timestamp.

        Args:
            session_id: The session identifier.
            state: The state dictionary to store.
        """
        with _FILE_LOCK:
            sessions = self._load_sessions()
            state["timestamp"] = utc_now_iso()
            sessions[session_id] = state
            save_json(SESSIONS_FILE, sessions)

    def reset_session(self, session_id: str) -> None:
        """Clear any active flow for a session.

        Args:
            session_id: The session identifier.
        """
        self.save_session(session_id, {"current_flow": None, "current_step": None})

    # -- logging ---------------------------------------------------------

    def log_unanswered(self, message: str) -> None:
        """Append an unmatched question to ``unanswered.json`` for review.

        Args:
            message: The raw user message that produced a fallback.
        """
        with _FILE_LOCK:
            entries = load_json(UNANSWERED_FILE, [])
            if not isinstance(entries, list):
                entries = []
            entries.append({"message": message[:MAX_INPUT_LENGTH], "timestamp": utc_now_iso()})
            save_json(UNANSWERED_FILE, entries[-2000:])

    # -- intent matching -------------------------------------------------

    def _expand_keyword(self, keyword: str) -> List[str]:
        """Expand a keyword into itself plus any configured synonyms.

        Args:
            keyword: A keyword string from ``intents.json``.

        Returns:
            A list of normalised keyword variants.
        """
        variants = {normalise(keyword)}
        for base, alternatives in self.synonyms.items():
            if normalise(base) == normalise(keyword):
                variants.update(normalise(alt) for alt in alternatives)
        return [variant for variant in variants if variant]

    def score_intent(self, intent: Dict[str, Any], text: str, tokens: List[str]) -> int:
        """Score one intent against the user's input.

        Scoring is additive and deterministic:
        * exact multi-word phrase present in the input -> 3 points per word
        * exact single-word token match -> 2 points
        * token prefix match of 5+ characters (partial match) -> 1 point

        Args:
            intent: An intent definition from ``intents.json``.
            text: The normalised user input.
            tokens: Meaningful tokens from the normalised input.

        Returns:
            The integer score for this intent.
        """
        score = 0
        for keyword in intent.get("keywords", []):
            for variant in self._expand_keyword(keyword):
                words = variant.split(" ")
                if len(words) > 1:
                    if variant in text:
                        # Exact phrase, e.g. "reset password".
                        score += 3 * len(words)
                    elif all(word in tokens for word in words):
                        # Same words, different order or separated by filler,
                        # e.g. "how do i reset my password".
                        score += 2 * len(words)
                    continue
                if variant in tokens:
                    score += 2
                    continue
                for token in tokens:
                    if len(variant) >= 5 and token.startswith(variant):
                        score += 1
                        break
        return score

    def match_intent(self, message: str) -> Tuple[Optional[Dict[str, Any]], int]:
        """Find the best-scoring intent for a message.

        Ties are broken by the order intents appear in ``intents.json``,
        keeping the result fully deterministic.

        Args:
            message: Raw user input.

        Returns:
            A tuple of (intent or None, score).
        """
        text = normalise(message)
        tokens = tokenise(text)
        if not text:
            return None, 0

        best_intent: Optional[Dict[str, Any]] = None
        best_score = 0
        for intent in self.intents:
            score = self.score_intent(intent, text, tokens)
            if score > best_score:
                best_intent, best_score = intent, score
        return best_intent, best_score

    # -- response builders ----------------------------------------------

    @staticmethod
    def build_response(
        payload: Dict[str, Any],
        session_id: str,
    ) -> Dict[str, Any]:
        """Normalise any content block into the public response contract.

        Args:
            payload: A dict with ``message`` and optional ``quick_replies``/``links``.
            session_id: The active session id.

        Returns:
            A response dict with message, quick_replies, links and session_id.
        """
        message = (payload or {}).get("message") or (
            "Sorry, I don't have an answer for that. Type 'menu' for the main topics "
            "or 'human' for UNISA contact details."
        )
        return {
            "message": message,
            "quick_replies": (payload or {}).get("quick_replies", []) or [],
            "links": (payload or {}).get("links", []) or [],
            "session_id": session_id,
        }

    def fallback_response(self, key: str, session_id: str) -> Dict[str, Any]:
        """Build a response from a named block in ``fallback.json``.

        Args:
            key: Fallback key, e.g. ``"fallback"`` or ``"error"``.
            session_id: The active session id.

        Returns:
            A complete response dict.
        """
        block = self.fallbacks.get(key) or self.fallbacks.get("fallback") or {}
        return self.build_response(block, session_id)

    def intent_response(self, intent_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Build a response for a known intent id.

        Args:
            intent_id: The intent identifier.
            session_id: The active session id.

        Returns:
            A response dict, or None when the intent does not exist.
        """
        intent = self.intent_index.get(intent_id)
        if not intent:
            return None
        return self.build_response(intent.get("response", {}), session_id)

    # -- flows -----------------------------------------------------------

    def get_step(self, flow_id: str, step_id: str) -> Optional[Dict[str, Any]]:
        """Look up one step inside a flow.

        Args:
            flow_id: Key in ``flows.json``.
            step_id: Step id inside that flow.

        Returns:
            The step dict, or None.
        """
        flow = self.flows.get(flow_id)
        if not flow:
            return None
        return flow.get("steps", {}).get(step_id)

    def start_flow(self, flow_id: str, session_id: str, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enter a flow at its first step and persist the session state.

        Args:
            flow_id: Key in ``flows.json``.
            session_id: The active session id.
            state: The mutable session state.

        Returns:
            The first step's response, or None if the flow is unknown.
        """
        flow = self.flows.get(flow_id)
        if not flow:
            return None
        step_id = flow.get("start")
        step = self.get_step(flow_id, step_id)
        if not step:
            return None
        state["current_flow"] = flow_id
        state["current_step"] = step_id
        self.save_session(session_id, state)
        return self.build_response(step, session_id)

    def advance_flow(
        self,
        message: str,
        session_id: str,
        state: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Advance the active flow using the user's reply.

        Args:
            message: Raw user input (usually "1", "2", "3" or a button value).
            session_id: The active session id.
            state: The mutable session state.

        Returns:
            The next step's response, or None when the reply doesn't map to a
            next step (the caller then falls back to intent matching).
        """
        flow_id = state.get("current_flow")
        step_id = state.get("current_step")
        step = self.get_step(flow_id, step_id) if flow_id and step_id else None
        if not step:
            state["current_flow"] = None
            state["current_step"] = None
            return None

        choice = normalise(message)
        mapping = step.get("next", {}) or {}
        next_id = mapping.get(choice)

        if next_id is None:
            # Allow the label's leading number, e.g. "1. new student".
            leading = re.match(r"^(\d+)", choice)
            if leading:
                next_id = mapping.get(leading.group(1))

        if next_id is None:
            return None

        next_step = self.get_step(flow_id, next_id)
        if not next_step:
            state["current_flow"] = None
            state["current_step"] = None
            self.save_session(session_id, state)
            return None

        if next_step.get("end"):
            state["current_flow"] = None
            state["current_step"] = None
        else:
            state["current_step"] = next_id
        self.save_session(session_id, state)
        return self.build_response(next_step, session_id)

    # -- main entry point -------------------------------------------------

    def respond(self, message: Any, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Produce the bot's reply to one user message.

        This method never raises and never returns an empty message.

        Args:
            message: Raw user input of any type.
            session_id: Existing session id, or None to start a new session.

        Returns:
            A response dict: message, quick_replies, links, session_id.
        """
        try:
            session_id, state = self.get_session(session_id)

            if not isinstance(message, str):
                message = "" if message is None else str(message)
            stripped = message.strip()

            # Edge case: empty input.
            if not stripped:
                self.save_session(session_id, state)
                return self.fallback_response("empty_input", session_id)

            # Edge case: extremely long input.
            if len(stripped) > MAX_INPUT_LENGTH:
                self.save_session(session_id, state)
                return self.fallback_response("too_long", session_id)

            normalised = normalise(stripped)

            # Global commands always take priority and exit any flow.
            if normalised in GLOBAL_MENU_WORDS:
                self.reset_session(session_id)
                return self.intent_response("menu", session_id) or self.fallback_response(
                    "fallback", session_id
                )

            if normalised in GLOBAL_HUMAN_WORDS:
                self.reset_session(session_id)
                return self.fallback_response("human_escalation", session_id)

            # Continue an active flow when the reply maps to a next step.
            if state.get("current_flow"):
                stepped = self.advance_flow(stripped, session_id, state)
                if stepped is not None:
                    return stepped

            # Keyword intent matching.
            intent, score = self.match_intent(stripped)
            if intent and score > 0:
                flow_id = intent.get("start_flow")
                # A bare topic word starts the guided flow; anything more
                # specific gets the direct hard-coded answer.
                if flow_id and len(tokenise(normalised)) <= 2:
                    flow_response = self.start_flow(flow_id, session_id, state)
                    if flow_response is not None:
                        return flow_response
                state["current_flow"] = None
                state["current_step"] = None
                self.save_session(session_id, state)
                return self.build_response(intent.get("response", {}), session_id)

            # Nothing matched: log it and fall back.
            self.log_unanswered(stripped)
            self.save_session(session_id, state)
            return self.fallback_response("fallback", session_id)

        except Exception:  # noqa: BLE001 - the bot must never crash.
            return self.fallback_response("error", session_id or uuid.uuid4().hex[:16])


# A single shared instance used by the Flask app.
bot = Chatbot()
