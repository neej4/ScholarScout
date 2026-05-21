"""
Test untuk memverifikasi implementasi DeepDiveHandler.generate() method.
Task 3.2: Implement DeepDiveHandler.generate() method
"""

import json
import pytest
from unittest.mock import Mock, MagicMock
from src.core.deep_dive import DeepDiveHandler, DeepDiveResponse


class TestDeepDiveHandlerGenerate:
    """Test suite untuk DeepDiveHandler.generate() method"""

    def test_generate_with_valid_response_en(self):
        """Test generate() dengan respons LLM valid dalam bahasa Inggris"""
        # Mock LLMClient
        mock_llm = Mock()
        valid_response = {
            "outline": [
                "Chapter 1: Introduction",
                "Chapter 2: Literature Review",
                "Chapter 3: Methodology",
                "Chapter 4: Implementation",
                "Chapter 5: Results",
                "Chapter 6: Conclusion"
            ],
            "methodology": "This research will employ a mixed-methods approach combining quantitative analysis with qualitative case studies.",
            "datasets": [
                "ImageNet - Large-scale image database",
                "COCO Dataset - Common Objects in Context",
                "Open Images - Google's image dataset"
            ],
            "references": [
                {"title": "Deep Learning for Computer Vision", "url": "https://arxiv.org/abs/1234.5678"},
                {"title": "Convolutional Neural Networks", "url": "https://arxiv.org/abs/2345.6789"},
                {"title": "Transfer Learning in Vision", "url": "https://arxiv.org/abs/3456.7890"},
                {"title": "Object Detection Methods", "url": "https://arxiv.org/abs/4567.8901"},
                {"title": "Image Classification Techniques", "url": "https://arxiv.org/abs/5678.9012"}
            ],
            "timeline": "6-8 months: Literature review (1 month), Implementation (3 months), Experiments (2 months), Writing (2 months)",
            "tools": ["PyTorch", "TensorFlow", "OpenCV", "NumPy", "Matplotlib", "Jupyter", "Git"]
        }
        mock_llm.call.return_value = json.dumps(valid_response)

        # Create handler
        handler = DeepDiveHandler(mock_llm)

        # Test idea
        idea = {
            "idea_title": "Deep Learning for Image Classification",
            "field": "Computer Vision",
            "difficulty": "Magister",
            "abstract": "A study on applying deep learning to image classification tasks"
        }

        # Call generate
        result = handler.generate(idea, language='en')

        # Verify LLM was called
        assert mock_llm.call.called
        call_args = mock_llm.call.call_args[0][0]
        assert "Deep Learning for Image Classification" in call_args
        assert "Computer Vision" in call_args
        assert "Magister" in call_args
        # Verify no Indonesian instruction for 'en'
        assert "Bahasa Indonesia" not in call_args

        # Verify result structure
        assert isinstance(result, dict)
        assert set(result.keys()) == DeepDiveResponse.REQUIRED_FIELDS
        assert result == valid_response

    def test_generate_with_valid_response_id(self):
        """Test generate() dengan respons LLM valid dalam bahasa Indonesia"""
        # Mock LLMClient
        mock_llm = Mock()
        valid_response = {
            "outline": [
                "Bab 1: Pendahuluan",
                "Bab 2: Tinjauan Pustaka",
                "Bab 3: Metodologi",
                "Bab 4: Implementasi",
                "Bab 5: Hasil dan Pembahasan",
                "Bab 6: Kesimpulan"
            ],
            "methodology": "Penelitian ini akan menggunakan pendekatan kuantitatif dengan metode eksperimen.",
            "datasets": [
                "ImageNet - Basis data gambar skala besar",
                "COCO Dataset - Dataset objek umum",
                "Open Images - Dataset gambar Google"
            ],
            "references": [
                {"title": "Deep Learning untuk Visi Komputer", "url": "https://arxiv.org/abs/1234.5678"},
                {"title": "Jaringan Neural Konvolusional", "url": "https://arxiv.org/abs/2345.6789"},
                {"title": "Transfer Learning dalam Visi", "url": "https://arxiv.org/abs/3456.7890"},
                {"title": "Metode Deteksi Objek", "url": "https://arxiv.org/abs/4567.8901"},
                {"title": "Teknik Klasifikasi Gambar", "url": "https://arxiv.org/abs/5678.9012"}
            ],
            "timeline": "6-8 bulan: Tinjauan pustaka (1 bulan), Implementasi (3 bulan), Eksperimen (2 bulan), Penulisan (2 bulan)",
            "tools": ["PyTorch", "TensorFlow", "OpenCV", "NumPy", "Matplotlib", "Jupyter", "Git"]
        }
        mock_llm.call.return_value = json.dumps(valid_response)

        # Create handler
        handler = DeepDiveHandler(mock_llm)

        # Test idea
        idea = {
            "idea_title": "Deep Learning untuk Klasifikasi Gambar",
            "field": "Visi Komputer",
            "difficulty": "Magister",
            "abstract": "Studi tentang penerapan deep learning untuk klasifikasi gambar"
        }

        # Call generate with Indonesian
        result = handler.generate(idea, language='id')

        # Verify LLM was called with Indonesian instruction
        assert mock_llm.call.called
        call_args = mock_llm.call.call_args[0][0]
        assert "Bahasa Indonesia akademis" in call_args

        # Verify result
        assert isinstance(result, dict)
        assert set(result.keys()) == DeepDiveResponse.REQUIRED_FIELDS

    def test_generate_with_markdown_wrapped_json(self):
        """Test generate() dengan respons LLM yang dibungkus markdown code block"""
        # Mock LLMClient
        mock_llm = Mock()
        valid_response = {
            "outline": ["Chapter 1", "Chapter 2"],
            "methodology": "Test methodology",
            "datasets": ["Dataset 1", "Dataset 2"],
            "references": [
                {"title": "Paper 1", "url": "https://arxiv.org/abs/1234.5678"},
                {"title": "Paper 2", "url": "https://arxiv.org/abs/2345.6789"},
                {"title": "Paper 3", "url": "https://arxiv.org/abs/3456.7890"},
                {"title": "Paper 4", "url": "https://arxiv.org/abs/4567.8901"},
                {"title": "Paper 5", "url": "https://arxiv.org/abs/5678.9012"}
            ],
            "timeline": "6 months",
            "tools": ["Tool1", "Tool2", "Tool3"]
        }
        # Wrap in markdown
        mock_llm.call.return_value = f"```json\n{json.dumps(valid_response)}\n```"

        handler = DeepDiveHandler(mock_llm)
        idea = {"idea_title": "Test", "field": "Test", "difficulty": "Test", "abstract": "Test"}

        result = handler.generate(idea)

        # Should successfully parse despite markdown wrapper
        assert result == valid_response

    def test_generate_raises_on_invalid_json(self):
        """Test generate() raise ValueError ketika respons bukan JSON valid"""
        mock_llm = Mock()
        mock_llm.call.return_value = "This is not valid JSON"

        handler = DeepDiveHandler(mock_llm)
        idea = {"idea_title": "Test", "field": "Test", "difficulty": "Test", "abstract": "Test"}

        with pytest.raises(ValueError, match="Failed to parse LLM response as JSON"):
            handler.generate(idea)

    def test_generate_raises_on_missing_required_field(self):
        """Test generate() raise ValueError ketika field wajib tidak ada"""
        mock_llm = Mock()
        # Missing 'timeline' field
        incomplete_response = {
            "outline": ["Chapter 1"],
            "methodology": "Test",
            "datasets": ["Dataset 1"],
            "references": [{"title": "Paper", "url": "https://arxiv.org/abs/1234.5678"}],
            "tools": ["Tool1"]
            # 'timeline' is missing
        }
        mock_llm.call.return_value = json.dumps(incomplete_response)

        handler = DeepDiveHandler(mock_llm)
        idea = {"idea_title": "Test", "field": "Test", "difficulty": "Test", "abstract": "Test"}

        with pytest.raises(ValueError, match="Missing required fields"):
            handler.generate(idea)

    def test_generate_raises_on_wrong_type_outline(self):
        """Test generate() raise ValueError ketika 'outline' bukan list"""
        mock_llm = Mock()
        invalid_response = {
            "outline": "This should be a list",  # Wrong type
            "methodology": "Test",
            "datasets": ["Dataset 1"],
            "references": [{"title": "Paper", "url": "https://arxiv.org/abs/1234.5678"}],
            "timeline": "6 months",
            "tools": ["Tool1"]
        }
        mock_llm.call.return_value = json.dumps(invalid_response)

        handler = DeepDiveHandler(mock_llm)
        idea = {"idea_title": "Test", "field": "Test", "difficulty": "Test", "abstract": "Test"}

        with pytest.raises(ValueError, match="'outline' must be a list"):
            handler.generate(idea)

    def test_generate_raises_on_invalid_reference_structure(self):
        """Test generate() raise ValueError ketika reference tidak memiliki 'title' dan 'url'"""
        mock_llm = Mock()
        invalid_response = {
            "outline": ["Chapter 1"],
            "methodology": "Test",
            "datasets": ["Dataset 1"],
            "references": [
                {"title": "Paper 1"},  # Missing 'url'
                {"url": "https://arxiv.org/abs/1234.5678"}  # Missing 'title'
            ],
            "timeline": "6 months",
            "tools": ["Tool1"]
        }
        mock_llm.call.return_value = json.dumps(invalid_response)

        handler = DeepDiveHandler(mock_llm)
        idea = {"idea_title": "Test", "field": "Test", "difficulty": "Test", "abstract": "Test"}

        with pytest.raises(ValueError, match="must have 'title' and 'url' fields"):
            handler.generate(idea)

    def test_generate_raises_on_empty_llm_response(self):
        """Test generate() raise ValueError ketika LLM mengembalikan respons kosong"""
        mock_llm = Mock()
        mock_llm.call.return_value = ""

        handler = DeepDiveHandler(mock_llm)
        idea = {"idea_title": "Test", "field": "Test", "difficulty": "Test", "abstract": "Test"}

        with pytest.raises(ValueError, match="LLM returned empty response"):
            handler.generate(idea)

    def test_generate_handles_missing_optional_idea_fields(self):
        """Test generate() dapat menangani idea dengan field opsional yang hilang"""
        mock_llm = Mock()
        valid_response = {
            "outline": ["Chapter 1"],
            "methodology": "Test",
            "datasets": ["Dataset 1"],
            "references": [{"title": "Paper", "url": "https://arxiv.org/abs/1234.5678"}],
            "timeline": "6 months",
            "tools": ["Tool1"]
        }
        mock_llm.call.return_value = json.dumps(valid_response)

        handler = DeepDiveHandler(mock_llm)
        # Idea with missing fields - should use defaults
        idea = {}

        result = handler.generate(idea)

        # Should not raise error and return valid result
        assert result == valid_response
        
        # Verify prompt used defaults
        call_args = mock_llm.call.call_args[0][0]
        assert "Untitled" in call_args
        assert "Unknown" in call_args
        assert "No abstract provided" in call_args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
