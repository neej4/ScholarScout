"""
Paper Clusterer for Review Mode.
Groups papers into thematic clusters using:
1. Semantic similarity via Gemini embeddings (if available)
2. Keyword overlap fallback (Jaccard on title+abstract tokens)

Then asks LLM to name each cluster.
"""
import math
import random
from typing import List, Dict, Optional, Tuple
from src.core.models import Paper
from src.core.config import Config


class PaperClusterer:
    """
    Clusters papers into 4-7 thematic groups.
    Uses embedding similarity when Gemini key available, else keyword overlap.
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def cluster(self, papers: List[Paper], n_clusters: int = 5) -> List[Dict]:
        """
        Cluster papers into thematic groups.

        Args:
            papers: List of Paper objects to cluster
            n_clusters: Target number of clusters (4-7)

        Returns:
            List of dicts: [{"name": str, "papers": List[Paper], "keywords": List[str]}]
        """
        if len(papers) <= n_clusters:
            # Too few papers to cluster meaningfully
            return [{"name": p.category, "papers": [p], "keywords": []} for p in papers]

        # Try semantic clustering first
        if Config.LLM_PROVIDER == "gemini" and Config.LLM_API_KEY:
            try:
                clusters = self._cluster_semantic(papers, n_clusters)
                if clusters:
                    return self._name_clusters(clusters)
            except Exception:
                pass

        # Fallback: keyword-based clustering
        clusters = self._cluster_keyword(papers, n_clusters)
        return self._name_clusters(clusters)

    def _cluster_semantic(self, papers: List[Paper], n_clusters: int) -> List[List[Paper]]:
        """Cluster using Gemini embeddings + k-means."""
        from src.core.novelty_checker import NoveltyChecker
        checker = NoveltyChecker()

        # Embed all papers (title + first 200 chars of abstract)
        vectors = []
        valid_papers = []
        for p in papers:
            text = f"{p.title}. {p.abstract[:200]}"
            try:
                vec = checker._embed(text)
                vectors.append(vec)
                valid_papers.append(p)
            except Exception:
                continue

        if len(vectors) < n_clusters:
            return []

        # Simple k-means
        clusters = self._kmeans(vectors, valid_papers, n_clusters)
        return clusters

    def _cluster_keyword(self, papers: List[Paper], n_clusters: int) -> List[List[Paper]]:
        """Cluster using keyword overlap (Jaccard similarity on tokens)."""
        # Tokenize each paper
        paper_tokens = []
        for p in papers:
            text = f"{p.title} {p.abstract}".lower()
            tokens = set(t for t in text.split() if len(t) > 3)
            paper_tokens.append(tokens)

        # Greedy clustering: assign each paper to most similar existing cluster
        clusters: List[List[int]] = []
        cluster_tokens: List[set] = []

        for i, tokens in enumerate(paper_tokens):
            best_cluster = -1
            best_sim = 0.15  # minimum similarity threshold to join a cluster

            for ci, ct in enumerate(cluster_tokens):
                if not ct or not tokens:
                    continue
                sim = len(tokens & ct) / len(tokens | ct)
                if sim > best_sim:
                    best_sim = sim
                    best_cluster = ci

            if best_cluster >= 0 and len(clusters) >= n_clusters:
                clusters[best_cluster].append(i)
                cluster_tokens[best_cluster] |= tokens
            elif len(clusters) < n_clusters:
                clusters.append([i])
                cluster_tokens.append(tokens.copy())
            else:
                # Add to smallest cluster
                smallest = min(range(len(clusters)), key=lambda x: len(clusters[x]))
                clusters[smallest].append(i)
                cluster_tokens[smallest] |= tokens

        return [[papers[i] for i in c] for c in clusters if c]

    def _kmeans(self, vectors: List[List[float]], papers: List[Paper], k: int, iterations: int = 10) -> List[List[Paper]]:
        """Simple k-means clustering."""
        n = len(vectors)
        dim = len(vectors[0])

        # Initialize centroids randomly
        indices = random.sample(range(n), min(k, n))
        centroids = [vectors[i][:] for i in indices]

        assignments = [0] * n

        for _ in range(iterations):
            # Assign each point to nearest centroid
            for i, vec in enumerate(vectors):
                best_dist = float('inf')
                for ci, cent in enumerate(centroids):
                    dist = sum((a - b) ** 2 for a, b in zip(vec, cent))
                    if dist < best_dist:
                        best_dist = dist
                        assignments[i] = ci

            # Update centroids
            for ci in range(k):
                members = [vectors[i] for i in range(n) if assignments[i] == ci]
                if members:
                    centroids[ci] = [sum(v[d] for v in members) / len(members) for d in range(dim)]

        # Build cluster lists
        clusters: List[List[Paper]] = [[] for _ in range(k)]
        for i, ci in enumerate(assignments):
            clusters[ci].append(papers[i])

        return [c for c in clusters if c]  # Remove empty clusters

    def _name_clusters(self, clusters: List[List[Paper]]) -> List[Dict]:
        """Ask LLM to name each cluster based on paper titles."""
        result = []
        for cluster_papers in clusters:
            titles = [p.title for p in cluster_papers[:10]]
            name = self._generate_cluster_name(titles)
            # Extract top keywords
            all_text = " ".join(p.title for p in cluster_papers).lower()
            words = [w for w in all_text.split() if len(w) > 4]
            word_freq = {}
            for w in words:
                word_freq[w] = word_freq.get(w, 0) + 1
            keywords = sorted(word_freq, key=word_freq.get, reverse=True)[:5]

            result.append({
                "name": name,
                "papers": cluster_papers,
                "keywords": keywords,
            })
        return result

    def _generate_cluster_name(self, titles: List[str]) -> str:
        """Use LLM to generate a short cluster name from paper titles."""
        if not self.llm:
            # Fallback: use most common 2-3 word phrase
            return titles[0].split(":")[0][:40] if titles else "Cluster"

        prompt = f"""Given these paper titles from one research cluster, generate a SHORT name (2-5 words) that captures the common theme:

{chr(10).join('- ' + t for t in titles[:8])}

Reply with ONLY the cluster name, nothing else. Example: "Federated Learning for Healthcare" or "Transformer Efficiency Methods"."""

        try:
            name = self.llm.call(prompt, retries=1, task_type="ping")
            if name:
                return name.strip().strip('"').strip("'")[:50]
        except Exception:
            pass

        return titles[0].split(":")[0][:40] if titles else "Cluster"
