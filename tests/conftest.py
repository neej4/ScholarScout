"""
Pytest configuration and shared fixtures for ScholarScout tests.

This file provides common test fixtures used across unit and integration tests,
including mock LLMClient and stub data objects.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.core.models import Paper, TrendAnalysis, ProjectIdea


@pytest.fixture
def mock_llm_client():
    """
    Mock LLMClient that returns predefined responses without making actual API calls.
    
    Usage:
        def test_something(mock_llm_client):
            mock_llm_client.call.return_value = '{"some": "json"}'
            # ... test code
    """
    mock_client = Mock()
    mock_client.call = MagicMock(return_value='{"test": "response"}')
    mock_client.ping = MagicMock(return_value=(True, ""))
    mock_client.api_key = "test_api_key"
    mock_client.model = "test_model"
    mock_client.url = "https://test.api.url"
    return mock_client


@pytest.fixture
def stub_paper():
    """
    Stub Paper object for testing.
    
    Returns a single Paper instance with realistic test data.
    """
    return Paper(
        id="2401.12345",
        title="Test Paper: Novel Approach to Machine Learning",
        category="cs.AI",
        authors="John Doe; Jane Smith",
        abstract="This paper presents a novel approach to machine learning that improves accuracy by 10%.",
        link="https://arxiv.org/abs/2401.12345",
        submitted_date="2024-01-15",
        source="arxiv"
    )


@pytest.fixture
def stub_papers():
    """
    Stub list of Paper objects for testing.
    
    Returns a list of 3 Paper instances with varied data.
    """
    return [
        Paper(
            id="2401.12345",
            title="Deep Learning for Natural Language Processing",
            category="cs.CL",
            authors="Alice Johnson; Bob Williams",
            abstract="We propose a new architecture for NLP tasks.",
            link="https://arxiv.org/abs/2401.12345",
            submitted_date="2024-01-15",
            source="arxiv"
        ),
        Paper(
            id="2401.67890",
            title="Reinforcement Learning in Robotics",
            category="cs.RO",
            authors="Charlie Brown; Diana Prince",
            abstract="This work explores RL applications in robotic control.",
            link="https://arxiv.org/abs/2401.67890",
            submitted_date="2024-01-20",
            source="arxiv"
        ),
        Paper(
            id="2402.11111",
            title="Computer Vision for Medical Imaging",
            category="cs.CV",
            authors="Eve Davis; Frank Miller",
            abstract="We apply computer vision techniques to medical diagnosis.",
            link="https://arxiv.org/abs/2402.11111",
            submitted_date="2024-02-01",
            source="arxiv"
        )
    ]


@pytest.fixture
def stub_trend():
    """
    Stub TrendAnalysis object for testing.
    
    Returns a TrendAnalysis instance with realistic test data.
    """
    return TrendAnalysis(
        category="cs.AI",
        paper_count=15,
        top_keywords=["machine learning", "neural networks", "deep learning", "transformers"],
        emerging_methods=["attention mechanisms", "self-supervised learning", "few-shot learning"],
        research_gaps=[
            "Limited work on low-resource languages",
            "Lack of interpretability in deep models",
            "Need for more efficient training methods"
        ],
        ref_papers=[
            Paper(
                id="2401.12345",
                title="Attention Is All You Need",
                category="cs.AI",
                authors="Vaswani et al.",
                abstract="We propose the Transformer architecture.",
                link="https://arxiv.org/abs/1706.03762",
                submitted_date="2017-06-12",
                source="arxiv"
            )
        ]
    )


@pytest.fixture
def stub_idea():
    """
    Stub ProjectIdea object for testing.
    
    Returns a ProjectIdea instance with realistic test data.
    """
    return ProjectIdea(
        idea_title="Efficient Transformer for Low-Resource Languages",
        field="Natural Language Processing",
        difficulty="Master's",
        cost_estimate="Cloud GPU ($50-200)",
        cost_note="Needs cloud GPU access for training",
        why_hard="Requires handling limited training data and adapting pre-trained models",
        resources_needed="GPU access, multilingual datasets, transformer frameworks",
        abstract="This project aims to develop an efficient transformer architecture optimized for low-resource languages, addressing the gap in NLP tools for underrepresented languages.",
        methodology_hint="Fine-tune multilingual model on low-resource data with curriculum learning.",
        next_steps="Survey existing multilingual models | Collect low-resource dataset | Set up fine-tuning pipeline",
        key_papers="Attention Is All You Need | mBERT: Multilingual BERT",
        why_this_idea="No efficient transformer exists for languages with <10K training samples.",
        quality_score=8,
        prerequisites="PyTorch | NLP fundamentals | Transfer learning",
        inspired_by="2401.12345",
        inspiration_title="Attention Is All You Need",
        inspiration_link="https://arxiv.org/abs/1706.03762",
        generated_date=datetime.now().strftime("%Y-%m-%d")
    )


@pytest.fixture
def stub_idea_indonesian():
    """
    Stub ProjectIdea object in Bahasa Indonesia for testing language features.
    """
    return ProjectIdea(
        idea_title="Sistem Deteksi Penyakit Tanaman Berbasis Computer Vision",
        field="Computer Vision",
        difficulty="Undergraduate",
        cost_estimate="Free Tier (Colab/Laptop)",
        cost_note="Biaya pengumpulan dataset dan komputasi",
        why_hard="Memerlukan dataset gambar penyakit tanaman yang beragam dan teknik augmentasi data",
        resources_needed="Kamera smartphone, dataset gambar tanaman, framework deep learning",
        abstract="Proyek ini bertujuan mengembangkan sistem deteksi otomatis penyakit tanaman menggunakan teknik computer vision dan deep learning untuk membantu petani Indonesia.",
        methodology_hint="Transfer learning dari EfficientNet, fine-tune pada dataset PlantVillage.",
        next_steps="Kumpulkan dataset | Implementasi model baseline | Evaluasi akurasi",
        key_papers="EfficientNet | PlantVillage Dataset",
        why_this_idea="Belum ada tool deteksi penyakit tanaman yang akurat untuk varietas lokal Indonesia.",
        quality_score=7,
        prerequisites="Python | Deep learning dasar | OpenCV",
        inspired_by="2402.11111",
        inspiration_title="Computer Vision for Medical Imaging",
        inspiration_link="https://arxiv.org/abs/2402.11111",
        generated_date=datetime.now().strftime("%Y-%m-%d")
    )


@pytest.fixture
def mock_emit_function():
    """
    Mock emit function for testing components that use event emission.
    
    Returns a MagicMock that can be used to track emit calls.
    """
    return MagicMock()


@pytest.fixture
def sample_research_context():
    """
    Sample research context text for testing context injection.
    
    Returns a realistic research context string.
    """
    return """Saya mahasiswa S2 Informatika di Universitas Indonesia. 
Keahlian saya di bidang NLP dan machine learning. 
Lab kami memiliki akses GPU terbatas (1x RTX 3090). 
Saya tertarik riset yang bisa diaplikasikan untuk Bahasa Indonesia."""


@pytest.fixture
def sample_deep_dive_response():
    """
    Sample Deep Dive response for testing.
    
    Returns a dict matching the DeepDiveResponse structure.
    """
    return {
        "outline": [
            "Bab 1: Pendahuluan dan Latar Belakang",
            "Bab 2: Tinjauan Pustaka",
            "Bab 3: Metodologi Penelitian",
            "Bab 4: Implementasi dan Eksperimen",
            "Bab 5: Hasil dan Analisis",
            "Bab 6: Kesimpulan dan Saran"
        ],
        "methodology": "Penelitian ini menggunakan pendekatan eksperimental dengan metode deep learning. Tahap pertama melibatkan pengumpulan dan preprocessing dataset. Tahap kedua adalah perancangan arsitektur model. Tahap ketiga adalah training dan evaluasi model menggunakan metrik standar.",
        "datasets": [
            "ImageNet - Dataset gambar umum untuk pre-training",
            "PlantVillage - Dataset penyakit tanaman dengan 50,000+ gambar",
            "Indonesian Plant Disease Dataset - Dataset lokal dari penelitian sebelumnya"
        ],
        "references": [
            {
                "title": "Deep Residual Learning for Image Recognition",
                "url": "https://arxiv.org/abs/1512.03385"
            },
            {
                "title": "EfficientNet: Rethinking Model Scaling for CNNs",
                "url": "https://arxiv.org/abs/1905.11946"
            },
            {
                "title": "Plant Disease Detection using Deep Learning",
                "url": "https://arxiv.org/abs/2001.12345"
            },
            {
                "title": "Transfer Learning for Agricultural Applications",
                "url": "https://arxiv.org/abs/2002.67890"
            },
            {
                "title": "Mobile Computer Vision for Precision Agriculture",
                "url": "https://arxiv.org/abs/2003.11111"
            }
        ],
        "timeline": "Bulan 1-2: Studi literatur dan pengumpulan dataset. Bulan 3-4: Implementasi model baseline. Bulan 5-6: Eksperimen dan optimisasi. Bulan 7-8: Evaluasi dan penulisan laporan.",
        "tools": [
            "PyTorch",
            "TensorFlow",
            "OpenCV",
            "scikit-learn",
            "Jupyter Notebook",
            "Google Colab",
            "Weights & Biases",
            "Git/GitHub"
        ]
    }
