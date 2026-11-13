from contextlib import nullcontext
from unittest import mock

from django.test import SimpleTestCase, override_settings

from core import llm
from core.llm_fakes import FakeGeminiClient, gemini_error

KEY = override_settings(GEMINI_API_KEY="test-key", GEMINI_MODEL="test-model")
MESSAGES = [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "hi"}]


class ChatJsonTests(SimpleTestCase):
    def call(self, client):
        with mock.patch("core.llm.get_client", return_value=client):
            return llm.chat_json(MESSAGES, max_tokens=500)

    def assert_error(self, client, status, code):
        with self.assertRaises(llm.LLMError) as caught:
            self.call(client)
        self.assertEqual((caught.exception.status_code, caught.exception.code), (status, code))
        return caught.exception

    def test_tests_never_have_a_real_key(self):
        self.assertFalse(llm.is_configured())

    def test_missing_key_is_a_clear_503_and_no_request_is_made(self):
        client = FakeGeminiClient(reply={"a": 1})
        error = self.assert_error(client, 503, "ai_not_configured")
        self.assertIn("GEMINI_API_KEY", error.message)
        self.assertEqual(client.calls, [])

    @KEY
    def test_success_returns_data_model_and_token_usage(self):
        client = FakeGeminiClient(reply={"status": "ok"})
        result = self.call(client)
        self.assertEqual(result.data, {"status": "ok"})
        self.assertEqual((result.model, result.prompt_tokens, result.completion_tokens), ("fake-model", 120, 340))
        sent = client.calls[0]
        self.assertEqual(sent["model"], "test-model")
        self.assertEqual(sent["contents"], "hi")
        self.assertEqual(sent["config"].system_instruction, "Be brief.")
        self.assertEqual(sent["config"].response_mime_type, "application/json")
        self.assertEqual(sent["config"].max_output_tokens, 500 + llm.THINKING_HEADROOM_TOKENS)

    @KEY
    def test_gemini_errors_become_friendly_messages(self):
        cases = [
            (gemini_error(400, "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key."), 503, "ai_key_rejected"),
            (gemini_error(403, "PERMISSION_DENIED"), 503, "ai_key_rejected"),
            (gemini_error(429, "RESOURCE_EXHAUSTED"), 429, "ai_rate_limited"),
            (gemini_error(404, "NOT_FOUND", "models/x is not found"), 503, "ai_model_not_found"),
            (gemini_error(503, "UNAVAILABLE", "The model is overloaded."), 503, "ai_unreachable"),
            (gemini_error(500, "INTERNAL"), 502, "ai_error"),
            (gemini_error(400, "INVALID_ARGUMENT", "Request contains an invalid argument."), 502, "ai_error"),
            (ConnectionError("no network"), 503, "ai_unreachable"),
            (TimeoutError("too slow"), 503, "ai_unreachable"),
        ]
        for error, status, code in cases:
            with self.subTest(error=repr(error)), self.assertLogs("core.llm", "WARNING") if code == "ai_error" else nullcontext():
                result = self.assert_error(FakeGeminiClient(error=error), status, code)
                self.assertNotIn("test error", result.message)  # raw provider text is never shown

    @KEY
    def test_unreadable_blocked_or_cut_off_answers(self):
        self.assert_error(FakeGeminiClient(content="not json"), 502, "ai_bad_output")
        self.assert_error(FakeGeminiClient(content="[1, 2]"), 502, "ai_bad_output")
        self.assert_error(FakeGeminiClient(no_candidates=True), 502, "ai_bad_output")
        self.assert_error(FakeGeminiClient(reply={"a": 1}, finish_reason="MAX_TOKENS"), 502, "ai_truncated")
        self.assert_error(FakeGeminiClient(reply={"a": 1}, finish_reason="SAFETY"), 502, "ai_refused")
        self.assert_error(FakeGeminiClient(reply={"a": 1}, block_reason="SAFETY"), 502, "ai_refused")

    @KEY
    def test_json_in_a_code_fence_is_accepted(self):
        self.assertEqual(self.call(FakeGeminiClient(content='```json\n{"ok": true}\n```')).data, {"ok": True})


class CleanTextTests(SimpleTestCase):
    def test_clean_text(self):
        self.assertEqual(llm.clean_text("  a \n  b ", 50), "a b")
        self.assertEqual(llm.clean_text("abcdefghij", 8), "abcde...")
        self.assertEqual(llm.clean_text(None, 10), "")
        self.assertEqual(llm.clean_text(42, 10), "")
