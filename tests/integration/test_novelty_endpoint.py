"""
Integration tests for the /api/novelty endpoint.

Tests the Flask endpoint that checks research idea novelty.
"""

import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path to import preview_server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from preview_server import app


class TestNoveltyEndpoint(unittest.TestCase):
    """Test the /api/novelty endpoint."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    @patch('src.web.routes.analysis.NoveltyChecker')
    def test_novelty_endpoint_success_novel(self, mock_checker_class):
        """Test successful novelty check returning novel status."""
        # Mock NoveltyChecker
        mock_checker = MagicMock()
        mock_checker.check.return_value = {
            "status": "novel",
            "papers": [],
            "max_similarity": 0.2
        }
        mock_checker_class.return_value = mock_checker
        
        # Execute
        response = self.client.post(
            '/api/novelty',
            data=json.dumps({"idea_title": "Novel Research Idea"}),
            content_type='application/json'
        )
        
        # Verify
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "novel")
        self.assertEqual(len(data["papers"]), 0)
        self.assertNotIn("max_similarity", data)  # Should be excluded from API response
    
    @patch('src.web.routes.analysis.NoveltyChecker')
    def test_novelty_endpoint_success_similar(self, mock_checker_class):
        """Test successful novelty check returning similar status."""
        # Mock NoveltyChecker
        mock_checker = MagicMock()
        mock_checker.check.return_value = {
            "status": "similar",
            "papers": [
                {"title": "Similar Paper 1", "url": "https://example.com/1"},
                {"title": "Similar Paper 2", "url": "https://example.com/2"}
            ],
            "max_similarity": 0.55
        }
        mock_checker_class.return_value = mock_checker
        
        # Execute
        response = self.client.post(
            '/api/novelty',
            data=json.dumps({"idea_title": "Research Idea"}),
            content_type='application/json'
        )
        
        # Verify
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "similar")
        self.assertEqual(len(data["papers"]), 2)
        self.assertEqual(data["papers"][0]["title"], "Similar Paper 1")
        self.assertEqual(data["papers"][0]["url"], "https://example.com/1")
    
    @patch('src.web.routes.analysis.NoveltyChecker')
    def test_novelty_endpoint_success_exists(self, mock_checker_class):
        """Test successful novelty check returning exists status."""
        # Mock NoveltyChecker
        mock_checker = MagicMock()
        mock_checker.check.return_value = {
            "status": "exists",
            "papers": [
                {"title": "Existing Paper", "url": "https://example.com/existing"}
            ],
            "max_similarity": 0.85
        }
        mock_checker_class.return_value = mock_checker
        
        # Execute
        response = self.client.post(
            '/api/novelty',
            data=json.dumps({"idea_title": "Existing Research"}),
            content_type='application/json'
        )
        
        # Verify
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "exists")
        self.assertEqual(len(data["papers"]), 1)
    
    def test_novelty_endpoint_missing_idea_title(self):
        """Test endpoint returns 400 when idea_title is missing."""
        # Execute with empty body
        response = self.client.post(
            '/api/novelty',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        # Verify
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
        self.assertIn("required", data["error"].lower())
    
    def test_novelty_endpoint_empty_idea_title(self):
        """Test endpoint returns 400 when idea_title is empty string."""
        # Execute with empty string
        response = self.client.post(
            '/api/novelty',
            data=json.dumps({"idea_title": "   "}),
            content_type='application/json'
        )
        
        # Verify
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
        self.assertIn("empty", data["error"].lower())
    
    def test_novelty_endpoint_no_json_body(self):
        """Test endpoint returns 400 when no JSON body is provided."""
        # Execute without JSON
        response = self.client.post('/api/novelty')
        
        # Verify
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('src.web.routes.analysis.NoveltyChecker')
    def test_novelty_endpoint_runtime_error(self, mock_checker_class):
        """Test endpoint returns 503 when both APIs fail."""
        # Mock NoveltyChecker to raise RuntimeError
        mock_checker = MagicMock()
        mock_checker.check.side_effect = RuntimeError("Both Semantic Scholar and ArXiv APIs failed")
        mock_checker_class.return_value = mock_checker
        
        # Execute
        response = self.client.post(
            '/api/novelty',
            data=json.dumps({"idea_title": "Test Idea"}),
            content_type='application/json'
        )
        
        # Verify
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.data)
        self.assertIn("error", data)
        self.assertIn("failed", data["error"].lower())
    
    @patch('src.web.routes.analysis.NoveltyChecker')
    def test_novelty_endpoint_unexpected_error(self, mock_checker_class):
        """Test endpoint returns 500 for unexpected errors."""
        # Mock NoveltyChecker to raise unexpected exception
        mock_checker = MagicMock()
        mock_checker.check.side_effect = Exception("Unexpected error")
        mock_checker_class.return_value = mock_checker
        
        # Execute
        response = self.client.post(
            '/api/novelty',
            data=json.dumps({"idea_title": "Test Idea"}),
            content_type='application/json'
        )
        
        # Verify
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('src.web.routes.analysis.NoveltyChecker')
    def test_novelty_endpoint_strips_whitespace(self, mock_checker_class):
        """Test endpoint strips whitespace from idea_title."""
        # Mock NoveltyChecker
        mock_checker = MagicMock()
        mock_checker.check.return_value = {
            "status": "novel",
            "papers": [],
            "max_similarity": 0.0
        }
        mock_checker_class.return_value = mock_checker
        
        # Execute with whitespace
        response = self.client.post(
            '/api/novelty',
            data=json.dumps({"idea_title": "  Test Idea  "}),
            content_type='application/json'
        )
        
        # Verify
        self.assertEqual(response.status_code, 200)
        # Verify that check was called with stripped title
        mock_checker.check.assert_called_once_with("Test Idea")


if __name__ == '__main__':
    unittest.main()
