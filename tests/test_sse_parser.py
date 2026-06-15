"""
Tests for LLMClient._parse_response() and _parse_sse().
Covers: pure JSON, standard SSE, hybrid JSON+SSE, malformed, empty.
"""
import unittest
from unittest.mock import patch
from src.core.llm import LLMClient


class TestParseResponse(unittest.TestCase):
    """Test _parse_response handles all provider response formats."""

    def setUp(self):
        with patch.object(LLMClient, '__init__', lambda self, **kw: None):
            self.client = LLMClient()
            self.client.emit_fn = None
            self.client.provider = "custom"

    def test_pure_json(self):
        """Standard non-streaming JSON response."""
        raw = '{"choices":[{"message":{"content":"Hello world"}}]}'
        self.assertEqual(self.client._parse_response(raw), "Hello world")

    def test_pure_json_with_whitespace(self):
        """JSON with leading/trailing whitespace."""
        raw = '  \n{"choices":[{"message":{"content":"OK"}}]}\n  '
        self.assertEqual(self.client._parse_response(raw), "OK")

    def test_standard_sse(self):
        """Pure SSE streaming response (data: lines)."""
        raw = (
            'data: {"choices":[{"delta":{"content":"Hel"}}]}\n'
            'data: {"choices":[{"delta":{"content":"lo"}}]}\n'
            'data: {"choices":[{"delta":{"content":" world"}}]}\n'
            'data: [DONE]\n'
        )
        self.assertEqual(self.client._parse_response(raw), "Hello world")

    def test_hybrid_json_plus_sse_trailer(self):
        """JSON body followed by SSE trailer (9router format)."""
        raw = (
            '{"choices":[{"message":{"content":"OK!"}}],"usage":{"prompt_tokens":5}}\n'
            '         data: [DONE]\n\n'
        )
        self.assertEqual(self.client._parse_response(raw), "OK!")

    def test_sse_with_empty_deltas(self):
        """SSE with some empty delta content (common in streaming)."""
        raw = (
            'data: {"choices":[{"delta":{"role":"assistant"}}]}\n'
            'data: {"choices":[{"delta":{"content":""}}]}\n'
            'data: {"choices":[{"delta":{"content":"Hi"}}]}\n'
            'data: [DONE]\n'
        )
        self.assertEqual(self.client._parse_response(raw), "Hi")

    def test_sse_with_non_streaming_message(self):
        """Some providers send full message in SSE format."""
        raw = 'data: {"choices":[{"message":{"content":"Full response"}}]}\ndata: [DONE]\n'
        self.assertEqual(self.client._parse_response(raw), "Full response")

    def test_pure_json_with_reasoning_content_only(self):
        """Reasoning models may leave content empty but include reasoning_content."""
        raw = '{"choices":[{"message":{"content":"","reasoning_content":"Thinking..."}}]}'
        self.assertEqual(self.client._parse_response(raw), "Thinking...")

    def test_malformed_json(self):
        """Malformed JSON returns empty string."""
        raw = '{"choices":[{"message":{"content":"trunca'
        result = self.client._parse_response(raw)
        self.assertEqual(result, "")

    def test_empty_response(self):
        """Empty string returns empty."""
        self.assertEqual(self.client._parse_response(""), "")
        self.assertEqual(self.client._parse_response("   "), "")

    def test_sse_with_malformed_line(self):
        """One malformed SSE line doesn't crash — skipped gracefully."""
        raw = (
            'data: {"choices":[{"delta":{"content":"A"}}]}\n'
            'data: {malformed json\n'
            'data: {"choices":[{"delta":{"content":"B"}}]}\n'
            'data: [DONE]\n'
        )
        self.assertEqual(self.client._parse_response(raw), "AB")

    def test_sse_without_done(self):
        """SSE without [DONE] marker still works."""
        raw = (
            'data: {"choices":[{"delta":{"content":"no done"}}]}\n'
        )
        self.assertEqual(self.client._parse_response(raw), "no done")

    def test_sse_with_reasoning_content_only(self):
        """Streaming/non-streaming chunks with reasoning_content still count as text."""
        raw = (
            'data: {"choices":[{"message":{"content":"","reasoning_content":"Reasoning alive"}}]}\n'
            'data: [DONE]\n'
        )
        self.assertEqual(self.client._parse_response(raw), "Reasoning alive")


class TestParseSse(unittest.TestCase):
    """Test _parse_sse directly."""

    def setUp(self):
        with patch.object(LLMClient, '__init__', lambda self, **kw: None):
            self.client = LLMClient()
            self.client.emit_fn = None
            self.client.provider = "custom"

    def test_basic_stream(self):
        raw = 'data: {"choices":[{"delta":{"content":"A"}}]}\ndata: {"choices":[{"delta":{"content":"B"}}]}\ndata: [DONE]\n'
        self.assertEqual(self.client._parse_sse(raw), "AB")

    def test_ignores_non_data_lines(self):
        raw = ': comment\nretry: 5000\ndata: {"choices":[{"delta":{"content":"X"}}]}\ndata: [DONE]\n'
        self.assertEqual(self.client._parse_sse(raw), "X")

    def test_empty_input(self):
        self.assertEqual(self.client._parse_sse(""), "")


if __name__ == "__main__":
    unittest.main()
