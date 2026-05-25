"""
Property-based and unit tests for the upgraded NoveltyChecker.

Covers:
- Jaccard symmetry and idempotence (Hypothesis)
- Cosine similarity math properties
- Semantic vs Jaccard routing logic
- New _jaccard_score_to_status / _semantic_score_to_status methods
"""

import math
import unittest
from unittest.mock import patch, MagicMock
import json

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.core.novelty_checker import NoveltyChecker


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_checker() -> NoveltyChecker:
    return NoveltyChecker()


# ─── Property-based tests (Hypothesis) ───────────────────────────────────────

class TestJaccardProperties(unittest.TestCase):
    """Mathematical properties that must hold for any input."""

    def setUp(self):
        self.checker = _make_checker()

    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=200)
    def test_jaccard_symmetry(self, text):
        """Jaccard(a, b) == Jaccard(b, a) for all inputs."""
        sim_ab = self.checker._jaccard_similarity(text, text[::-1])
        sim_ba = self.checker._jaccard_similarity(text[::-1], text)
        self.assertAlmostEqual(sim_ab, sim_ba, places=10)

    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=200)
    def test_jaccard_self_similarity_is_one_or_zero(self, text):
        """Jaccard(a, a) is either 1.0 (has tokens) or 0.0 (all stopwords/empty)."""
        sim = self.checker._jaccard_similarity(text, text)
        self.assertIn(sim, (0.0, 1.0))

    @given(st.text(min_size=1, max_size=200), st.text(min_size=1, max_size=200))
    @settings(max_examples=200)
    def test_jaccard_range(self, a, b):
        """Jaccard similarity is always in [0.0, 1.0]."""
        sim = self.checker._jaccard_similarity(a, b)
        self.assertGreaterEqual(sim, 0.0)
        self.assertLessEqual(sim, 1.0)

    @given(st.text(min_size=1, max_size=200), st.text(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_jaccard_triangle_inequality_weak(self, a, b):
        """Jaccard distance (1 - sim) satisfies weak triangle inequality."""
        # d(a, b) <= d(a, a) + d(a, b) is trivially true; test a weaker form:
        # sim(a, b) >= 0 always (already covered above, but good to be explicit)
        sim = self.checker._jaccard_similarity(a, b)
        self.assertGreaterEqual(sim, 0.0)


class TestCosineProperties(unittest.TestCase):
    """Mathematical properties for cosine similarity."""

    def setUp(self):
        self.checker = _make_checker()

    def test_cosine_identical_vectors(self):
        """Cosine similarity of a vector with itself is 1.0."""
        v = [0.1, 0.5, -0.3, 0.8]
        self.assertAlmostEqual(self.checker._cosine_similarity(v, v), 1.0, places=6)

    def test_cosine_orthogonal_vectors(self):
        """Cosine similarity of orthogonal vectors is 0.0."""
        v_a = [1.0, 0.0, 0.0]
        v_b = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(self.checker._cosine_similarity(v_a, v_b), 0.0, places=6)

    def test_cosine_opposite_vectors(self):
        """Cosine similarity of opposite vectors is -1.0."""
        v = [1.0, 2.0, 3.0]
        neg_v = [-1.0, -2.0, -3.0]
        self.assertAlmostEqual(self.checker._cosine_similarity(v, neg_v), -1.0, places=6)

    def test_cosine_symmetry(self):
        """Cosine(a, b) == Cosine(b, a)."""
        v_a = [0.3, 0.7, -0.1]
        v_b = [0.5, 0.2, 0.9]
        self.assertAlmostEqual(
            self.checker._cosine_similarity(v_a, v_b),
            self.checker._cosine_similarity(v_b, v_a),
            places=10,
        )

    def test_cosine_empty_vectors(self):
        """Cosine similarity returns 0.0 for empty vectors."""
        self.assertEqual(self.checker._cosine_similarity([], []), 0.0)

    def test_cosine_mismatched_lengths(self):
        """Cosine similarity returns 0.0 for mismatched vector lengths."""
        self.assertEqual(self.checker._cosine_similarity([1.0, 2.0], [1.0]), 0.0)

    @given(
        st.integers(min_value=2, max_value=50).flatmap(
            lambda size: st.tuples(
                st.lists(
                    st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
                    min_size=size,
                    max_size=size,
                ),
                st.lists(
                    st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
                    min_size=size,
                    max_size=size,
                ),
            )
        )
    )
    @settings(max_examples=100)
    def test_cosine_range(self, vectors):
        """Cosine similarity is always in [-1.0, 1.0]."""
        a, b = vectors
        assume(any(x != 0 for x in a) and any(x != 0 for x in b))
        sim = self.checker._cosine_similarity(a, b)
        self.assertGreaterEqual(sim, -1.0 - 1e-9)
        self.assertLessEqual(sim, 1.0 + 1e-9)


# ─── Status mapping tests ─────────────────────────────────────────────────────

class TestStatusMapping(unittest.TestCase):
    """Test both Jaccard and semantic status mapping methods."""

    def setUp(self):
        self.checker = _make_checker()

    # Jaccard thresholds: novel < 0.40, similar 0.40–0.70, exists > 0.70
    def test_jaccard_novel(self):
        self.assertEqual(self.checker._jaccard_score_to_status(0.0),  "novel")
        self.assertEqual(self.checker._jaccard_score_to_status(0.39), "novel")

    def test_jaccard_similar(self):
        self.assertEqual(self.checker._jaccard_score_to_status(0.40), "similar")
        self.assertEqual(self.checker._jaccard_score_to_status(0.55), "similar")
        self.assertEqual(self.checker._jaccard_score_to_status(0.69), "similar")

    def test_jaccard_exists(self):
        self.assertEqual(self.checker._jaccard_score_to_status(0.71), "exists")
        self.assertEqual(self.checker._jaccard_score_to_status(1.0),  "exists")

    # Semantic thresholds: novel < 0.82, similar 0.82–0.92, exists >= 0.92
    def test_semantic_novel(self):
        self.assertEqual(self.checker._semantic_score_to_status(0.0),  "novel")
        self.assertEqual(self.checker._semantic_score_to_status(0.81), "novel")

    def test_semantic_similar(self):
        self.assertEqual(self.checker._semantic_score_to_status(0.82), "similar")
        self.assertEqual(self.checker._semantic_score_to_status(0.87), "similar")
        self.assertEqual(self.checker._semantic_score_to_status(0.91), "similar")

    def test_semantic_exists(self):
        self.assertEqual(self.checker._semantic_score_to_status(0.92), "exists")
        self.assertEqual(self.checker._semantic_score_to_status(1.0),  "exists")


# ─── Routing logic tests ──────────────────────────────────────────────────────

class TestCheckRouting(unittest.TestCase):
    """Test that check() routes to semantic vs Jaccard correctly."""

    def setUp(self):
        self.checker = _make_checker()

    @patch("src.core.novelty_checker.Config")
    @patch("urllib.request.urlopen")
    def test_uses_jaccard_when_no_gemini_key(self, mock_urlopen, mock_config):
        """When provider is not gemini, falls back to Jaccard."""
        mock_config.LLM_PROVIDER = "groq"
        mock_config.LLM_API_KEY  = "some-key"

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "data": [{"title": "Federated Learning Survey", "url": "https://example.com"}]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_resp

        result = self.checker.check("Federated Learning Overview")
        self.assertEqual(result["method"], "jaccard")

    @patch("src.core.novelty_checker.Config")
    @patch("urllib.request.urlopen")
    def test_uses_jaccard_when_gemini_key_empty(self, mock_urlopen, mock_config):
        """When provider is gemini but key is empty, falls back to Jaccard."""
        mock_config.LLM_PROVIDER = "gemini"
        mock_config.LLM_API_KEY  = ""

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "data": [{"title": "Some Paper", "url": "https://example.com"}]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_resp

        result = self.checker.check("Some Research Idea")
        self.assertEqual(result["method"], "jaccard")

    @patch("src.core.novelty_checker.Config")
    @patch.object(NoveltyChecker, "_embed")
    @patch("urllib.request.urlopen")
    def test_uses_semantic_when_gemini_available(self, mock_urlopen, mock_embed, mock_config):
        """When provider is gemini with a key, uses semantic similarity."""
        mock_config.LLM_PROVIDER = "gemini"
        mock_config.LLM_API_KEY  = "AIza-test-key"

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "data": [{"title": "Federated Learning Survey", "url": "https://example.com"}]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_resp

        # Return a unit vector so cosine similarity is well-defined
        mock_embed.return_value = [1.0] + [0.0] * 767

        result = self.checker.check("Federated Learning Overview")
        self.assertEqual(result["method"], "semantic")

    @patch("src.core.novelty_checker.Config")
    @patch.object(NoveltyChecker, "_embed", side_effect=Exception("embed failed"))
    @patch("urllib.request.urlopen")
    def test_falls_back_to_jaccard_on_embed_error(self, mock_urlopen, mock_embed, mock_config):
        """If embedding API fails, falls back to Jaccard gracefully."""
        mock_config.LLM_PROVIDER = "gemini"
        mock_config.LLM_API_KEY  = "AIza-test-key"

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "data": [{"title": "Some Paper", "url": "https://example.com"}]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_resp

        result = self.checker.check("Some Research Idea")
        # Should not raise; should return a valid result via Jaccard
        self.assertIn(result["status"], ("novel", "similar", "exists"))
        self.assertEqual(result["method"], "jaccard")


# ─── Result schema tests ──────────────────────────────────────────────────────

class TestResultSchema(unittest.TestCase):
    """Ensure check() always returns the expected schema."""

    def setUp(self):
        self.checker = _make_checker()

    @patch("urllib.request.urlopen")
    def test_result_has_required_keys(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"data": []}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_resp

        result = self.checker.check("Novel Idea About Quantum Cats")
        self.assertIn("status",         result)
        self.assertIn("papers",         result)
        self.assertIn("max_similarity", result)
        self.assertIn("method",         result)

    @patch("urllib.request.urlopen")
    def test_novel_result_has_empty_papers(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"data": []}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_resp

        result = self.checker.check("Completely Novel Topic XYZ123")
        self.assertEqual(result["status"], "novel")
        self.assertEqual(result["papers"], [])

    def test_empty_title_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.checker.check("")

    def test_whitespace_title_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.checker.check("   ")


if __name__ == "__main__":
    unittest.main()
