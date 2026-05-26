"""
Unit tests for PaperClusterer.
Covers: keyword clustering, edge cases (0/1/few papers), cluster invariants.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.core.models import Paper
from src.core.clusterer import PaperClusterer


def _make_paper(title: str, abstract: str = "", category: str = "cs.AI", source: str = "test") -> Paper:
    return Paper(
        id=f"test_{title[:10]}",
        title=title,
        category=category,
        authors="Author A",
        abstract=abstract or f"Abstract about {title}",
        link=f"https://example.com/{title[:5]}",
        submitted_date="2026-01-01",
        source=source,
        citations=0,
    )


class TestPaperClustererKeyword:
    """Tests for keyword-based clustering (no LLM needed)."""

    def test_empty_papers(self):
        clusterer = PaperClusterer(llm_client=None)
        result = clusterer.cluster([], n_clusters=3)
        assert result == []

    def test_single_paper(self):
        papers = [_make_paper("Federated Learning for IoT")]
        clusterer = PaperClusterer(llm_client=None)
        result = clusterer.cluster(papers, n_clusters=3)
        assert len(result) == 1
        assert len(result[0]["papers"]) == 1

    def test_fewer_papers_than_clusters(self):
        papers = [
            _make_paper("Paper A about transformers"),
            _make_paper("Paper B about attention"),
        ]
        clusterer = PaperClusterer(llm_client=None)
        result = clusterer.cluster(papers, n_clusters=5)
        # Should return one cluster per paper (too few to cluster)
        assert len(result) == 2

    def test_basic_clustering_produces_correct_count(self):
        """With enough papers, should produce up to n_clusters clusters."""
        papers = [
            _make_paper("Deep learning for image classification", "CNN architectures for visual recognition"),
            _make_paper("Convolutional neural networks for object detection", "Object detection using deep CNNs"),
            _make_paper("Image segmentation with deep learning", "Semantic segmentation approaches"),
            _make_paper("Natural language processing with transformers", "Transformer models for NLP tasks"),
            _make_paper("BERT fine-tuning for text classification", "Text classification using BERT"),
            _make_paper("Language models for machine translation", "Neural machine translation approaches"),
            _make_paper("Reinforcement learning for robotics", "Robot control via RL policies"),
            _make_paper("Multi-agent reinforcement learning", "Cooperative multi-agent systems"),
            _make_paper("Policy gradient methods for control", "Control optimization with policy gradients"),
        ]
        clusterer = PaperClusterer(llm_client=None)
        result = clusterer.cluster(papers, n_clusters=3)
        # Should produce between 1 and 3 clusters
        assert 1 <= len(result) <= 3

    def test_every_paper_in_exactly_one_cluster(self):
        """Invariant: every input paper must appear in exactly one cluster."""
        papers = [
            _make_paper(f"Paper {i} about topic {i % 3}", f"Abstract {i}")
            for i in range(15)
        ]
        clusterer = PaperClusterer(llm_client=None)
        result = clusterer.cluster(papers, n_clusters=4)

        # Collect all papers from all clusters
        all_clustered = []
        for c in result:
            all_clustered.extend(c["papers"])

        assert len(all_clustered) == len(papers)

    def test_cluster_has_name_and_keywords(self):
        """Each cluster dict should have name, papers, keywords keys."""
        papers = [
            _make_paper(f"Research paper number {i}", f"Abstract content {i}")
            for i in range(10)
        ]
        clusterer = PaperClusterer(llm_client=None)
        result = clusterer.cluster(papers, n_clusters=3)

        for cluster in result:
            assert "name" in cluster
            assert "papers" in cluster
            assert "keywords" in cluster
            assert isinstance(cluster["papers"], list)
            assert len(cluster["papers"]) > 0

    def test_cluster_count_never_exceeds_paper_count(self):
        """Invariant: number of clusters <= number of papers."""
        for n_papers in range(1, 12):
            papers = [_make_paper(f"P{i}") for i in range(n_papers)]
            clusterer = PaperClusterer(llm_client=None)
            result = clusterer.cluster(papers, n_clusters=5)
            assert len(result) <= n_papers
