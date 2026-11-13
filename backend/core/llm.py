"""Google Gemini calls shared by every AI feature (Phase 11).

This one module handles the API key, model name, timeout, retries and error messages. The
features that use it (interview questions, skill-gap summaries) only build a prompt and check
the answer. Semantic matching and ranking never call Gemini: they use the local embedding model.

The features pass chat-style messages ([{"role": "system" | "user", "content": ...}]). They are
turned into Gemini's system instruction + contents here, so the features do not depend on the
provider. Every call asks for a JSON answer (response_mime_type="application/json"), so the answer
can be checked field by field before it is shown to anyone.
"""
import importlib
import json
import logging
import re
import threading
from dataclasses import dataclass

from django.conf import settings
from rest_framework.exceptions import APIException

log = logging.getLogger(__name__)

_client = None
_client_lock = threading.Lock()

# Thinking models (e.g. Gemini 2.5) spend part of the output budget on internal reasoning before the
# answer. This extra room keeps that from cutting off the JSON answer. Only tokens used are billed.
THINKING_HEADROOM_TOKENS = 4096

# Finish reasons that mean the model would not answer this content
BLOCKED_FINISH_REASONS = {
    "SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "LANGUAGE", "IMAGE_SAFETY",
}


class LLMError(Exception):
    """The language model could not give a usable answer. `message` is safe to show to users."""

    def __init__(self, message, status_code=502, code="ai_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class AIUnavailable(APIException):
    """Turns an LLMError into an API error response with the right status code and message."""

    status_code = 503
    default_detail = "AI features are temporarily unavailable. Please try again later."
    default_code = "ai_unavailable"

    def __init__(self, error):
        super().__init__(detail=error.message, code=error.code)
        self.status_code = error.status_code


@dataclass
class LLMResult:
    data: dict
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


def is_configured():
    return bool((getattr(settings, "GEMINI_API_KEY", "") or "").strip())


def get_client():
    """Creates the Gemini client on first use and keeps it for the life of the process."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                from google import genai
                from google.genai import types

                _client = genai.Client(
                    api_key=settings.GEMINI_API_KEY,
                    http_options=types.HttpOptions(
                        timeout=int(settings.GEMINI_TIMEOUT_SECONDS * 1000),  # milliseconds
                        # retries with exponential backoff, only for rate limits, timeouts and server errors
                        retry_options=types.HttpRetryOptions(attempts=settings.GEMINI_MAX_RETRIES + 1),
                    ),
                )
    return _client


def _network_errors():
    """Exception classes for connection problems and timeouts (the SDK's HTTP library varies by version)."""
    classes = [ConnectionError, TimeoutError]
    for module_name, class_name in (("httpx2", "TransportError"), ("httpx", "TransportError"),
                                    ("requests", "RequestException")):
        try:
            classes.append(getattr(importlib.import_module(module_name), class_name))
        except (ImportError, AttributeError):
            pass
    return tuple(classes)


def _split_messages(messages):
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = "\n\n".join(m["content"] for m in messages if m["role"] != "system")
    return system, contents


def _api_error_to_llm_error(error, model):
    code = getattr(error, "code", None)
    text = f"{getattr(error, 'status', '')} {getattr(error, 'message', '')}".upper()
    if code in (401, 403) or "API_KEY" in text or "API KEY" in text:
        return LLMError("The Gemini API key was rejected. Check GEMINI_API_KEY in the .env file.", 503, "ai_key_rejected")
    if code == 429:
        return LLMError(
            "The AI service is busy or the Gemini quota is used up. Please try again in a minute.",
            429,
            "ai_rate_limited",
        )
    if code == 404:
        return LLMError(
            f"The model '{model}' is not available for this API key. Check GEMINI_MODEL in the .env file.",
            503,
            "ai_model_not_found",
        )
    if code == 503:
        return LLMError("The AI service is overloaded right now. Please try again later.", 503, "ai_unreachable")
    log.warning("Gemini request failed: %s", error)  # bad request, server errors, anything else
    return LLMError("The AI service returned an error. Please try again later.", 502, "ai_error")


def _name(value):
    """Enum value or plain string -> its name, e.g. FinishReason.MAX_TOKENS -> "MAX_TOKENS"."""
    return getattr(value, "name", None) or str(value or "").split(".")[-1]


def _answer_text(response):
    candidate = response.candidates[0]
    parts = getattr(getattr(candidate, "content", None), "parts", None) or []
    # thought summaries (if any) are not part of the answer
    return "".join(p.text for p in parts if getattr(p, "text", None) and not getattr(p, "thought", False))


def _parse_json(text):
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)  # in case the model adds a fence
    if fenced:
        text = fenced.group(1)
    return json.loads(text)


def chat_json(messages, *, max_tokens=1500):
    """Sends chat messages to Gemini and returns its answer as a dict (LLMResult.data).

    Raises LLMError with a user-friendly message for every failure: no API key, a rejected key,
    rate limits or no quota left, an unknown model, network problems, blocked content and
    unreadable answers.
    """
    if not is_configured():
        raise LLMError(
            "AI features are not configured on the server: set GEMINI_API_KEY in the .env file.",
            503,
            "ai_not_configured",
        )

    from google.genai import errors, types

    model = settings.GEMINI_MODEL
    system, contents = _split_messages(messages)
    config = types.GenerateContentConfig(
        system_instruction=system or None,
        response_mime_type="application/json",
        max_output_tokens=max_tokens + THINKING_HEADROOM_TOKENS,
    )
    try:
        response = get_client().models.generate_content(model=model, contents=contents, config=config)
    except errors.APIError as error:
        raise _api_error_to_llm_error(error, model) from None
    except _network_errors():
        raise LLMError("The AI service could not be reached. Please try again later.", 503, "ai_unreachable") from None

    feedback = getattr(response, "prompt_feedback", None)
    if feedback is not None and getattr(feedback, "block_reason", None):
        raise LLMError("The AI declined to answer this request.", 502, "ai_refused")
    if not response.candidates:
        raise LLMError("The AI did not return an answer. Please try again.", 502, "ai_bad_output")

    finish = _name(response.candidates[0].finish_reason)
    if finish == "MAX_TOKENS":
        raise LLMError("The AI answer was too long and got cut off. Please try again.", 502, "ai_truncated")
    if finish in BLOCKED_FINISH_REASONS:
        raise LLMError("The AI declined to answer this request.", 502, "ai_refused")

    try:
        data = _parse_json(_answer_text(response))
    except (TypeError, ValueError):
        raise LLMError("The AI answer could not be read. Please try again.", 502, "ai_bad_output") from None
    if not isinstance(data, dict):
        raise LLMError("The AI answer was not in the expected format. Please try again.", 502, "ai_bad_output")

    usage = getattr(response, "usage_metadata", None)
    return LLMResult(
        data=data,
        model=getattr(response, "model_version", None) or model,
        prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0,
        completion_tokens=(getattr(usage, "candidates_token_count", 0) or 0)
        + (getattr(usage, "thoughts_token_count", 0) or 0),
    )


def clean_text(value, max_chars):
    """Whitespace-normalised text cut to max_chars, or "" for anything that is not text."""
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split())
    return text if len(text) <= max_chars else text[: max_chars - 3].rstrip() + "..."
