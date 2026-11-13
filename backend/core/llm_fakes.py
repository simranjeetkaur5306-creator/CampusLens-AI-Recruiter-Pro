"""Test helper: a stand-in for the Gemini client, so tests never call the real API.

    client = FakeGeminiClient(reply={"technical": [...]})
    with override_settings(GEMINI_API_KEY="test-key"), mock.patch("core.llm.get_client", return_value=client):
        ...
    client.sent_text()   # exactly what would have been sent to Gemini (system instruction + contents)
"""
import json
from types import SimpleNamespace


class FakeGeminiClient:
    def __init__(self, reply=None, error=None, content=None, finish_reason="STOP", block_reason=None,
                 no_candidates=False):
        self.reply = reply  # a dict, sent back as JSON text
        self.content = content  # raw text to send back instead (to test unreadable answers)
        self.error = error  # an exception to raise instead of answering
        self.finish_reason = finish_reason
        self.block_reason = block_reason
        self.no_candidates = no_candidates
        self.calls = []
        self.models = SimpleNamespace(generate_content=self._generate_content)

    def _generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        text = self.content if self.content is not None else json.dumps(self.reply)
        candidate = SimpleNamespace(
            finish_reason=self.finish_reason,
            content=SimpleNamespace(parts=[SimpleNamespace(text=text, thought=False)]),
        )
        return SimpleNamespace(
            model_version="fake-model",
            candidates=[] if self.no_candidates else [candidate],
            prompt_feedback=SimpleNamespace(block_reason=self.block_reason),
            usage_metadata=SimpleNamespace(prompt_token_count=120, candidates_token_count=300, thoughts_token_count=40),
        )

    def sent_text(self, call=0):
        """System instruction and contents of one call joined together (to check what would be sent)."""
        sent = self.calls[call]
        return f"{sent['config'].system_instruction or ''}\n{sent['contents']}"


def gemini_error(code, status="", message="test error"):
    """A google-genai API error, as the SDK raises it for an HTTP error response."""
    from google.genai import errors

    cls = errors.ServerError if code >= 500 else errors.ClientError
    return cls(code, {"error": {"code": code, "status": status, "message": message}})
