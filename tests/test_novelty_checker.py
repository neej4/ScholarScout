"""
Unit tests for NoveltyChecker module.

Tests the search methods and similarity calculations.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
from src.core.novelty_checker import NoveltyChecker


class TestNoveltyCheckerSearchMethods(unittest.TestCase):
    """Test the search methods for Semantic Scholar and ArXiv."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.checker = NoveltyChecker()
    
    @patch('urllib.request.urlopen')
    def test_search_semantic_scholar_success(self, mock_urlopen):
        """Test successful Semantic Scholar search."""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "data": [
                {
                    "title": "Deep Learning for NLP",
                    "url": "https://www.semanticscholar.org/paper/abc123"
                },
                {
                    "title": "Transformer Networks",
                    "url": "https://www.semanticscholar.org/paper/def456"
                }
            ]
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response
        
        # Execute
        results = self.checker._search_semantic_scholar("deep learning")
        
        # Verify
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Deep Learning for NLP")
        self.assertEqual(results[0]["url"], "https://www.semanticscholar.org/paper/abc123")
        self.assertEqual(results[1]["title"], "Transformer Networks")
        self.assertEqual(results[1]["url"], "https://www.semanticscholar.org/paper/def456")
    
    @patch('urllib.request.urlopen')
    def test_search_semantic_scholar_uses_correct_params(self, mock_urlopen):
        """Test that Semantic Scholar search uses correct parameters."""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": []}).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response
        
        # Execute
        self.checker._search_semantic_scholar("test query")
        
        # Verify the URL contains correct parameters
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        url = request.full_url
        
        self.assertIn("query=test+query", url)
        self.assertIn("fields=title%2Curl", url)
        self.assertIn("limit=5", url)
    
    @patch('urllib.request.urlopen')
    def test_search_semantic_scholar_empty_results(self, mock_urlopen):
        """Test Semantic Scholar search with no results."""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": []}).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response
        
        # Execute
        results = self.checker._search_semantic_scholar("nonexistent topic")
        
        # Verify
        self.assertEqual(len(results), 0)
    
    @patch('urllib.request.urlopen')
    def test_search_semantic_scholar_timeout(self, mock_urlopen):
        """Test Semantic Scholar search timeout handling."""
        # Mock timeout
        mock_urlopen.side_effect = TimeoutError("Connection timeout")
        
        # Execute and verify exception
        with self.assertRaises(Exception) as context:
            self.checker._search_semantic_scholar("test query")
        
        self.assertIn("Semantic Scholar API error", str(context.exception))
    
    @patch('urllib.request.urlopen')
    def test_search_arxiv_success(self, mock_urlopen):
        """Test successful ArXiv search."""
        # Mock XML response
        xml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Attention Is All You Need</title>
                <id>http://arxiv.org/abs/1706.03762v5</id>
            </entry>
            <entry>
                <title>BERT: Pre-training of Deep Bidirectional Transformers</title>
                <id>http://arxiv.org/abs/1810.04805v2</id>
            </entry>
        </feed>
        """
        
        mock_response = MagicMock()
        mock_response.read.return_value = xml_response.encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response
        
        # Execute
        results = self.checker._search_arxiv("transformers")
        
        # Verify
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Attention Is All You Need")
        self.assertEqual(results[0]["url"], "http://arxiv.org/abs/1706.03762v5")
        self.assertEqual(results[1]["title"], "BERT: Pre-training of Deep Bidirectional Transformers")
        self.assertEqual(results[1]["url"], "http://arxiv.org/abs/1810.04805v2")
    
    @patch('urllib.request.urlopen')
    def test_search_arxiv_uses_title_search(self, mock_urlopen):
        """Test that ArXiv search uses title search (ti:) parameter."""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = b'<?xml version="1.0"?><feed></feed>'
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response
        
        # Execute
        self.checker._search_arxiv("neural networks")
        
        # Verify the URL contains ti: prefix
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        url = request.full_url
        
        self.assertIn("search_query=ti%3Aneural+networks", url)
        self.assertIn("max_results=5", url)
    
    @patch('urllib.request.urlopen')
    def test_search_arxiv_empty_results(self, mock_urlopen):
        """Test ArXiv search with no results."""
        # Mock empty XML response
        xml_response = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        
        mock_response = MagicMock()
        mock_response.read.return_value = xml_response.encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response
        
        # Execute
        results = self.checker._search_arxiv("nonexistent topic")
        
        # Verify
        self.assertEqual(len(results), 0)
    
    @patch('urllib.request.urlopen')
    def test_search_arxiv_timeout(self, mock_urlopen):
        """Test ArXiv search timeout handling."""
        # Mock timeout
        mock_urlopen.side_effect = TimeoutError("Connection timeout")
        
        # Execute and verify exception
        with self.assertRaises(Exception) as context:
            self.checker._search_arxiv("test query")
        
        self.assertIn("ArXiv API error", str(context.exception))
    
    @patch('urllib.request.urlopen')
    def test_search_arxiv_handles_multiline_titles(self, mock_urlopen):
        """Test ArXiv search handles titles with newlines and extra spaces."""
        # Mock XML response with multiline title
        xml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>A Very Long Title
                That Spans Multiple Lines
                With Extra   Spaces</title>
                <id>http://arxiv.org/abs/1234.56789v1</id>
            </entry>
        </feed>
        """
        
        mock_response = MagicMock()
        mock_response.read.return_value = xml_response.encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response
        
        # Execute
        results = self.checker._search_arxiv("test")
        
        # Verify title is cleaned up
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "A Very Long Title That Spans Multiple Lines With Extra Spaces")


class TestNoveltyCheckerSimilarity(unittest.TestCase):
    """Test Jaccard similarity calculations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.checker = NoveltyChecker()
    
    def test_jaccard_similarity_identical(self):
        """Test Jaccard similarity for identical titles."""
        title = "Deep Learning for Natural Language Processing"
        similarity = self.checker._jaccard_similarity(title, title)
        self.assertEqual(similarity, 1.0)
    
    def test_jaccard_similarity_completely_different(self):
        """Test Jaccard similarity for completely different titles."""
        title_a = "Deep Learning Networks"
        title_b = "Quantum Computing Algorithms"
        similarity = self.checker._jaccard_similarity(title_a, title_b)
        self.assertEqual(similarity, 0.0)
    
    def test_jaccard_similarity_partial_overlap(self):
        """Test Jaccard similarity for partially overlapping titles."""
        title_a = "Deep Learning for Computer Vision"
        title_b = "Deep Learning for Natural Language"
        similarity = self.checker._jaccard_similarity(title_a, title_b)
        # Both have "deep" and "learning" (2 tokens)
        # Union includes: deep, learning, computer, vision, natural, language (6 tokens)
        # Jaccard = 2/6 = 0.333...
        self.assertAlmostEqual(similarity, 0.333, places=2)
    
    def test_jaccard_similarity_empty_strings(self):
        """Test Jaccard similarity for empty strings."""
        similarity = self.checker._jaccard_similarity("", "")
        self.assertEqual(similarity, 0.0)
    
    def test_jaccard_similarity_one_empty(self):
        """Test Jaccard similarity when one string is empty."""
        similarity = self.checker._jaccard_similarity("Deep Learning", "")
        self.assertEqual(similarity, 0.0)
    
    def test_jaccard_similarity_stopwords_removed(self):
        """Test that stopwords are removed in similarity calculation."""
        title_a = "A Review of the Deep Learning"
        title_b = "The Deep Learning"
        # After removing stopwords (a, of, the), both should have same tokens: deep, learning, review
        # Wait, "review" is not a stopword, so title_a has {review, deep, learning}
        # and title_b has {deep, learning}
        # Let's use titles that truly have only stopword differences
        title_a = "The Deep Learning"
        title_b = "Deep Learning"
        # After removing stopwords (the), both should have same tokens
        similarity = self.checker._jaccard_similarity(title_a, title_b)
        self.assertEqual(similarity, 1.0)
    
    def test_jaccard_similarity_case_insensitive(self):
        """Test that similarity calculation is case-insensitive."""
        title_a = "Deep Learning Networks"
        title_b = "DEEP LEARNING NETWORKS"
        similarity = self.checker._jaccard_similarity(title_a, title_b)
        self.assertEqual(similarity, 1.0)
    
    def test_tokenize_removes_stopwords(self):
        """Test that tokenization removes stopwords."""
        text = "A study of the deep learning for NLP"
        tokens = self.checker._tokenize(text)
        # Should not contain: a, of, the, for
        # Should contain: study, deep, learning, nlp
        self.assertNotIn("a", tokens)
        self.assertNotIn("of", tokens)
        self.assertNotIn("the", tokens)
        self.assertNotIn("for", tokens)
        self.assertIn("study", tokens)
        self.assertIn("deep", tokens)
        self.assertIn("learning", tokens)
        self.assertIn("nlp", tokens)
    
    def test_tokenize_handles_punctuation(self):
        """Test that tokenization handles punctuation correctly."""
        text = "Deep-Learning: A Survey (2023)"
        tokens = self.checker._tokenize(text)
        # Should split on punctuation
        self.assertIn("deep", tokens)
        self.assertIn("learning", tokens)
        self.assertIn("survey", tokens)
        self.assertIn("2023", tokens)


class TestNoveltyCheckerStatusMapping(unittest.TestCase):
    """Test status mapping from similarity scores."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.checker = NoveltyChecker()
    
    def test_score_to_status_novel(self):
        """Test status mapping for novel ideas."""
        self.assertEqual(self.checker._jaccard_score_to_status(0.0), "novel")
        self.assertEqual(self.checker._jaccard_score_to_status(0.1), "novel")
        self.assertEqual(self.checker._jaccard_score_to_status(0.39), "novel")
    
    def test_score_to_status_similar(self):
        """Test status mapping for similar ideas."""
        self.assertEqual(self.checker._jaccard_score_to_status(0.40), "similar")
        self.assertEqual(self.checker._jaccard_score_to_status(0.5), "similar")
        self.assertEqual(self.checker._jaccard_score_to_status(0.69), "similar")
    
    def test_score_to_status_exists(self):
        """Test status mapping for existing ideas."""
        self.assertEqual(self.checker._jaccard_score_to_status(0.70), "exists")
        self.assertEqual(self.checker._jaccard_score_to_status(0.9), "exists")
        self.assertEqual(self.checker._jaccard_score_to_status(1.0), "exists")


class TestNoveltyCheckerIntegration(unittest.TestCase):
    """Integration tests for the complete check flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.checker = NoveltyChecker()
    
    @patch('urllib.request.urlopen')
    def test_check_returns_novel_for_no_results(self, mock_urlopen):
        """Test that check returns novel status when no papers found."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": []}).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response
        
        # Execute
        result = self.checker.check("Completely Novel Research Topic")
        
        # Verify
        self.assertEqual(result["status"], "novel")
        self.assertEqual(len(result["papers"]), 0)
        self.assertEqual(result["max_similarity"], 0.0)
    
    @patch('urllib.request.urlopen')
    def test_check_fallback_to_arxiv(self, mock_urlopen):
        """Test that check falls back to ArXiv when Semantic Scholar fails."""
        # First call (Semantic Scholar) fails, second call (ArXiv) succeeds
        xml_response = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Test Paper</title>
                <id>http://arxiv.org/abs/1234.56789</id>
            </entry>
        </feed>
        """
        
        mock_response_arxiv = MagicMock()
        mock_response_arxiv.read.return_value = xml_response.encode()
        mock_response_arxiv.__enter__ = lambda s: s
        mock_response_arxiv.__exit__ = MagicMock()
        
        # First call fails, second succeeds
        mock_urlopen.side_effect = [
            Exception("Semantic Scholar failed"),
            mock_response_arxiv
        ]
        
        # Execute
        result = self.checker.check("Test Query")
        
        # Verify ArXiv was called (2 calls total)
        self.assertEqual(mock_urlopen.call_count, 2)
    
    def test_check_raises_error_for_empty_title(self):
        """Test that check raises ValueError for empty title."""
        with self.assertRaises(ValueError) as context:
            self.checker.check("")
        
        self.assertIn("cannot be empty", str(context.exception))


if __name__ == '__main__':
    unittest.main()
