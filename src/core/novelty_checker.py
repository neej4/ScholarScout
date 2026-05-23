"""
NoveltyChecker module for verifying research idea novelty.

Checks if a research idea title is novel by:
1. Searching Semantic Scholar and ArXiv APIs
2. Computing semantic similarity via Gemini embedding API (if available)
3. Falling back to Jaccard similarity on token level

Semantic similarity is more robust than Jaccard — "Federated Learning for Medical IoT"
and "Federation Learning on Medical Internet of Things" will correctly score as similar.
"""

import re
import urllib.request
import urllib.parse
import json
import math
from typing import List, Dict, Set, Optional

from src.core.config import Config


class NoveltyChecker:
    """
    Checks the novelty of research idea titles by comparing them
    against existing papers in Semantic Scholar and ArXiv.

    Uses Gemini embedding API for semantic similarity when an API key is
    available; falls back to Jaccard similarity otherwise.
    """

    SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    ARXIV_SEARCH_URL = "https://export.arxiv.org/api/query"
    GEMINI_EMBED_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "text-embedding-004:embedContent"
    )

    STOPWORDS: Set[str] = {
        "a", "an", "the", "of", "in", "for", "on", "with", "to",
        "and", "or", "is", "are", "that", "this",
    }

    # Thresholds for semantic similarity (cosine distance)
    SEMANTIC_SIMILAR_THRESHOLD = 0.82   # cosine similarity ≥ this → "similar"
    SEMANTIC_EXISTS_THRESHOLD  = 0.92   # cosine similarity ≥ this → "exists"

    # Thresholds for Jaccard fallback
    JACCARD_SIMILAR_THRESHOLD = 0.40
    JACCARD_EXISTS_THRESHOLD  = 0.70

    TIMEOUT = 10  # seconds per HTTP request

    def check(self, idea_title: str) -> Dict:
        """
        Check the novelty of a research idea title.

        Args:
            idea_title: The research idea title to check.

        Returns:
            Dictionary with keys:
            - status: "novel" | "similar" | "exists"
            - papers: List of similar papers [{"title": str, "url": str}]
            - max_similarity: Highest similarity score (0.0–1.0)
            - method: "semantic" | "jaccard" (which algorithm was used)

        Raises:
            RuntimeError: If both Semantic Scholar and ArXiv APIs fail.
        """
        if not idea_title or not idea_title.strip():
            raise ValueError("idea_title cannot be empty")

        # Fetch candidate papers
        try:
            papers = self._search_semantic_scholar(idea_title)
        except Exception as ss_err:
            try:
                papers = self._search_arxiv(idea_title)
            except Exception as arxiv_err:
                raise RuntimeError(
                    f"Both Semantic Scholar and ArXiv APIs failed. "
                    f"Semantic Scholar: {ss_err}, ArXiv: {arxiv_err}"
                )

        if not papers:
            return {"status": "novel", "papers": [], "max_similarity": 0.0, "method": "jaccard"}

        # Try semantic similarity first (requires Gemini API key)
        if Config.LLM_PROVIDER == "gemini" and Config.LLM_API_KEY:
            try:
                return self._check_semantic(idea_title, papers)
            except Exception:
                pass  # Fall through to Jaccard

        # Jaccard fallback
        return self._check_jaccard(idea_title, papers)

    # ─── Semantic similarity (Gemini embeddings) ──────────────────────────────

    def _check_semantic(self, idea_title: str, papers: List[Dict]) -> Dict:
        """
        Compute cosine similarity between idea_title embedding and each paper title.
        Uses Gemini text-embedding-004 (free tier, 1500 req/min).
        """
        idea_vec = self._embed(idea_title)

        max_similarity = 0.0
        similar_papers: List[Dict] = []

        for paper in papers:
            paper_title = paper.get("title", "")
            if not paper_title:
                continue
            try:
                paper_vec = self._embed(paper_title)
                sim = self._cosine_similarity(idea_vec, paper_vec)
            except Exception:
                # If embedding fails for a single paper, fall back to Jaccard for it
                sim = self._jaccard_similarity(idea_title, paper_title)

            if sim > max_similarity:
                max_similarity = sim

            if sim >= self.SEMANTIC_SIMILAR_THRESHOLD:
                similar_papers.append(paper)

        status = self._semantic_score_to_status(max_similarity)
        return {
            "status": status,
            "papers": similar_papers if status != "novel" else [],
            "max_similarity": round(max_similarity, 4),
            "method": "semantic",
        }

    def _embed(self, text: str) -> List[float]:
        """
        Get embedding vector from Gemini text-embedding-004.

        Args:
            text: Input text to embed.

        Returns:
            List of floats (768-dimensional vector).

        Raises:
            Exception: If the API call fails.
        """
        url = f"{self.GEMINI_EMBED_URL}?key={Config.LLM_API_KEY}"
        payload = json.dumps({
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text[:2000]}]},
            "taskType": "SEMANTIC_SIMILARITY",
        }).encode("utf-8")

        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
            data = json.loads(resp.read())
            return data["embedding"]["values"]

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _semantic_score_to_status(self, score: float) -> str:
        if score >= self.SEMANTIC_EXISTS_THRESHOLD:
            return "exists"
        if score >= self.SEMANTIC_SIMILAR_THRESHOLD:
            return "similar"
        return "novel"

    # ─── Jaccard fallback ─────────────────────────────────────────────────────

    def _check_jaccard(self, idea_title: str, papers: List[Dict]) -> Dict:
        """Token-level Jaccard similarity (no external API needed)."""
        max_similarity = 0.0
        similar_papers: List[Dict] = []

        for paper in papers:
            sim = self._jaccard_similarity(idea_title, paper.get("title", ""))
            if sim > max_similarity:
                max_similarity = sim
            if sim >= self.JACCARD_SIMILAR_THRESHOLD:
                similar_papers.append(paper)

        status = self._jaccard_score_to_status(max_similarity)
        return {
            "status": status,
            "papers": similar_papers if status != "novel" else [],
            "max_similarity": round(max_similarity, 4),
            "method": "jaccard",
        }

    # ─── Paper search ─────────────────────────────────────────────────────────

    def _search_semantic_scholar(self, query: str) -> List[Dict[str, str]]:
        """Search Semantic Scholar for papers matching the query."""
        params = urllib.parse.urlencode({
            "query": query,
            "fields": "title,url",
            "limit": 5,
        })
        url = f"{self.SEMANTIC_SCHOLAR_URL}?{params}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "ScholarScout/1.3")

        try:
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
                return [
                    {"title": item.get("title", ""), "url": item.get("url", "")}
                    for item in data.get("data", [])
                    if item.get("title")
                ]
        except Exception as e:
            raise Exception(f"Semantic Scholar API error: {e}")

    def _search_arxiv(self, query: str) -> List[Dict[str, str]]:
        """Search arXiv for papers matching the query (fallback)."""
        params = urllib.parse.urlencode({
            "search_query": f"ti:{query}",
            "max_results": 5,
        })
        url = f"{self.ARXIV_SEARCH_URL}?{params}"
        req = urllib.request.Request(url)

        try:
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                content = resp.read().decode()
                papers: List[Dict[str, str]] = []
                entries = re.findall(r"<entry>(.*?)</entry>", content, re.DOTALL)
                for entry in entries[:5]:
                    title_m = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
                    id_m = re.search(r"<id>(.*?)</id>", entry)
                    if title_m and id_m:
                        title = re.sub(r"\s+", " ", title_m.group(1)).strip()
                        papers.append({"title": title, "url": id_m.group(1)})
                return papers
        except Exception as e:
            raise Exception(f"ArXiv API error: {e}")

    # ─── Jaccard helpers ──────────────────────────────────────────────────────

    def _jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """Jaccard similarity at token level with stopword removal."""
        tokens_a = self._tokenize(text_a)
        tokens_b = self._tokenize(text_b)
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    def _tokenize(self, text: str) -> Set[str]:
        """Lowercase, split on non-word chars, remove stopwords."""
        text = text.lower()
        tokens = re.split(r"\W+", text)
        return {t for t in tokens if t and t not in self.STOPWORDS}

    def _jaccard_score_to_status(self, score: float) -> str:
        if score >= self.JACCARD_EXISTS_THRESHOLD:
            return "exists"
        if score >= self.JACCARD_SIMILAR_THRESHOLD:
            return "similar"
        return "novel"
