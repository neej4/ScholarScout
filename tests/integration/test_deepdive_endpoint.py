"""
Integration tests for /api/deepdive endpoint.
Tests the Flask route with mocked DeepDiveHandler.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from preview_server import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_deepdive_handler():
    """Mock DeepDiveHandler to avoid actual LLM calls."""
    with patch('src.web.routes.analysis.DeepDiveHandler') as mock_handler_class:
        mock_handler = MagicMock()
        mock_handler_class.return_value = mock_handler
        
        # Default successful response
        mock_handler.generate.return_value = {
            "outline": [
                "Bab 1: Pendahuluan",
                "Bab 2: Tinjauan Pustaka",
                "Bab 3: Metodologi",
                "Bab 4: Implementasi",
                "Bab 5: Hasil dan Pembahasan",
                "Bab 6: Kesimpulan"
            ],
            "methodology": "Penelitian ini menggunakan pendekatan eksperimental dengan metode kuantitatif.",
            "datasets": [
                "ImageNet - Dataset gambar berskala besar",
                "COCO - Dataset untuk object detection",
                "CIFAR-10 - Dataset klasifikasi gambar"
            ],
            "references": [
                {"title": "Deep Learning", "url": "https://arxiv.org/abs/1234.5678"},
                {"title": "Neural Networks", "url": "https://arxiv.org/abs/2345.6789"},
                {"title": "Computer Vision", "url": "https://arxiv.org/abs/3456.7890"},
                {"title": "Machine Learning", "url": "https://arxiv.org/abs/4567.8901"},
                {"title": "AI Research", "url": "https://arxiv.org/abs/5678.9012"}
            ],
            "timeline": "Estimasi 12-18 bulan untuk menyelesaikan penelitian ini.",
            "tools": [
                "PyTorch",
                "TensorFlow",
                "Jupyter Notebook",
                "Git",
                "Docker",
                "CUDA"
            ]
        }
        
        yield mock_handler


@pytest.fixture
def mock_llm_client():
    """Mock LLMClient to avoid actual API calls."""
    with patch('src.web.routes.analysis.LLMClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


def test_deepdive_success(client, mock_deepdive_handler, mock_llm_client):
    """Test successful deep dive request."""
    idea = {
        "idea_title": "Deep Learning for Image Classification",
        "field": "Computer Vision",
        "difficulty": "Magister",
        "abstract": "This research explores deep learning techniques for image classification.",
        "why_hard": "Requires understanding of neural networks and large datasets.",
        "inspired_by": "Recent advances in CNN architectures",
        "inspiration_title": "ResNet Paper",
        "inspiration_link": "https://arxiv.org/abs/1512.03385"
    }
    
    response = client.post('/api/deepdive', 
                          data=json.dumps(idea),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Verify all required fields are present
    assert "outline" in data
    assert "methodology" in data
    assert "datasets" in data
    assert "references" in data
    assert "timeline" in data
    assert "tools" in data
    
    # Verify field types
    assert isinstance(data["outline"], list)
    assert isinstance(data["methodology"], str)
    assert isinstance(data["datasets"], list)
    assert isinstance(data["references"], list)
    assert isinstance(data["timeline"], str)
    assert isinstance(data["tools"], list)
    
    # Verify handler was called with correct parameters
    mock_deepdive_handler.generate.assert_called_once()
    call_args = mock_deepdive_handler.generate.call_args
    assert call_args[0][0]["idea_title"] == idea["idea_title"]
    assert call_args[0][1] == "en"  # default language


def test_deepdive_with_language_id(client, mock_deepdive_handler, mock_llm_client):
    """Test deep dive request with Bahasa Indonesia language."""
    idea = {
        "idea_title": "Pembelajaran Mendalam untuk Klasifikasi Gambar",
        "field": "Computer Vision",
        "difficulty": "Magister",
        "abstract": "Penelitian ini mengeksplorasi teknik pembelajaran mendalam.",
        "language": "id"
    }
    
    response = client.post('/api/deepdive',
                          data=json.dumps(idea),
                          content_type='application/json')
    
    assert response.status_code == 200
    
    # Verify handler was called with language='id'
    call_args = mock_deepdive_handler.generate.call_args
    assert call_args[0][1] == "id"


def test_deepdive_missing_idea_title(client, mock_deepdive_handler, mock_llm_client):
    """Test deep dive request without idea_title."""
    idea = {
        "field": "Computer Vision",
        "difficulty": "Magister"
    }
    
    response = client.post('/api/deepdive',
                          data=json.dumps(idea),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "idea_title" in data["error"].lower()


def test_deepdive_empty_body(client, mock_deepdive_handler, mock_llm_client):
    """Test deep dive request with empty body."""
    response = client.post('/api/deepdive',
                          data='',
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data


def test_deepdive_invalid_json(client, mock_deepdive_handler, mock_llm_client):
    """Test deep dive request with invalid JSON."""
    response = client.post('/api/deepdive',
                          data='not valid json',
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data


def test_deepdive_handler_value_error(client, mock_deepdive_handler, mock_llm_client):
    """Test deep dive when handler raises ValueError."""
    mock_deepdive_handler.generate.side_effect = ValueError("Missing required field: timeline")
    
    idea = {
        "idea_title": "Test Idea",
        "field": "AI",
        "difficulty": "Sarjana"
    }
    
    response = client.post('/api/deepdive',
                          data=json.dumps(idea),
                          content_type='application/json')
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    assert "timeline" in data["error"]


def test_deepdive_handler_general_exception(client, mock_deepdive_handler, mock_llm_client):
    """Test deep dive when handler raises general exception."""
    mock_deepdive_handler.generate.side_effect = Exception("Unexpected error")
    
    idea = {
        "idea_title": "Test Idea",
        "field": "AI",
        "difficulty": "Sarjana"
    }
    
    response = client.post('/api/deepdive',
                          data=json.dumps(idea),
                          content_type='application/json')
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    assert "Internal server error" in data["error"]


def test_deepdive_minimal_idea_object(client, mock_deepdive_handler, mock_llm_client):
    """Test deep dive with minimal idea object (only required field)."""
    idea = {
        "idea_title": "Minimal Test Idea"
    }
    
    response = client.post('/api/deepdive',
                          data=json.dumps(idea),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Verify all required fields are present in response
    assert "outline" in data
    assert "methodology" in data
    assert "datasets" in data
    assert "references" in data
    assert "timeline" in data
    assert "tools" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
