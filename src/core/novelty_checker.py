"""
NoveltyChecker module for verifying research idea novelty.

This module checks if a research idea title is novel by searching
Semantic Scholar and ArXiv APIs and computing Jaccard similarity
between the idea title and existing papers.
"""

import re
import urllib.request
import urllib.parse
import json
from typing import List, Dict, Set


class NoveltyChecker:
    """
    Checks the novelty of research idea titles by comparing them
    against existing papers in Semantic Scholar and ArXiv.
    """
    
    SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    ARXIV_SEARCH_URL = "https://export.arxiv.org/api/query"
    STOPWORDS = {
        "a", "an", "the", "of", "in", "for", "on", "with", "to", 
        "and", "or", "is", "are", "that", "this"
    }
    TIMEOUT = 10  # seconds
    
    def check(self, idea_title: str) -> Dict[str, any]:
        """
        Check the novelty of a research idea title.
        
        Args:
            idea_title: The research idea title to check
            
        Returns:
            Dictionary with keys:
            - status: "novel" | "similar" | "exists"
            - papers: List of similar papers [{"title": str, "url": str}]
            - max_similarity: Highest Jaccard similarity score (for debugging)
            
        Raises:
            RuntimeError: If both Semantic Scholar and ArXiv APIs fail
        """
        if not idea_title or not idea_title.strip():
            raise ValueError("idea_title cannot be empty")
        
        # Try Semantic Scholar first
        try:
            papers = self._search_semantic_scholar(idea_title)
        except Exception as e:
            # Fallback to ArXiv
            try:
                papers = self._search_arxiv(idea_title)
            except Exception as arxiv_error:
                raise RuntimeError(
                    f"Both Semantic Scholar and ArXiv APIs failed. "
                    f"Semantic Scholar: {str(e)}, ArXiv: {str(arxiv_error)}"
                )
        
        # If no papers found, return novel
        if not papers:
            return {
                "status": "novel",
                "papers": [],
                "max_similarity": 0.0
            }
        
        # Calculate similarity scores
        max_similarity = 0.0
        similar_papers = []
        
        for paper in papers:
            similarity = self._jaccard_similarity(idea_title, paper["title"])
            if similarity > max_similarity:
                max_similarity = similarity
            
            # Collect papers above similarity threshold
            if similarity >= 0.40:
                similar_papers.append(paper)
        
        # Determine status based on max similarity
        status = self._score_to_status(max_similarity)
        
        return {
            "status": status,
            "papers": similar_papers if status != "novel" else [],
            "max_similarity": max_similarity
        }
    
    def _search_semantic_scholar(self, query: str) -> List[Dict[str, str]]:
        """
        Search for papers in Semantic Scholar.
        
        Args:
            query: Search query string
            
        Returns:
            List of papers with "title" and "url" keys
            
        Raises:
            Exception: If the API request fails
        """
        params = urllib.parse.urlencode({
            "query": query,
            "fields": "title,url",
            "limit": 5
        })
        
        url = f"{self.SEMANTIC_SCHOLAR_URL}?{params}"
        
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "ScholarScout/1.0")
        
        try:
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                data = json.loads(response.read().decode())
                
                papers = []
                for item in data.get("data", []):
                    papers.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", "")
                    })
                
                return papers
        except Exception as e:
            raise Exception(f"Semantic Scholar API error: {str(e)}")
    
    def _search_arxiv(self, query: str) -> List[Dict[str, str]]:
        """
        Search for papers in ArXiv (fallback).
        
        Args:
            query: Search query string
            
        Returns:
            List of papers with "title" and "url" keys
            
        Raises:
            Exception: If the API request fails
        """
        params = urllib.parse.urlencode({
            "search_query": f"ti:{query}",
            "max_results": 5
        })
        
        url = f"{self.ARXIV_SEARCH_URL}?{params}"
        
        req = urllib.request.Request(url)
        
        try:
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                content = response.read().decode()
                
                # Parse XML response (simple regex-based parsing)
                papers = []
                entries = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)
                
                for entry in entries[:5]:
                    title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                    id_match = re.search(r'<id>(.*?)</id>', entry)
                    
                    if title_match and id_match:
                        # Clean up title (remove newlines and extra spaces)
                        title = re.sub(r'\s+', ' ', title_match.group(1)).strip()
                        papers.append({
                            "title": title,
                            "url": id_match.group(1)
                        })
                
                return papers
        except Exception as e:
            raise Exception(f"ArXiv API error: {str(e)}")
    
    def _jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """
        Calculate Jaccard similarity between two texts at token level.
        
        Args:
            text_a: First text
            text_b: Second text
            
        Returns:
            Jaccard similarity score in range [0.0, 1.0]
        """
        tokens_a = self._tokenize(text_a)
        tokens_b = self._tokenize(text_b)
        
        # Handle empty sets
        if not tokens_a and not tokens_b:
            return 0.0
        
        if not tokens_a or not tokens_b:
            return 0.0
        
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        
        return len(intersection) / len(union)
    
    def _tokenize(self, text: str) -> Set[str]:
        """
        Tokenize text: lowercase, split by non-word characters, remove stopwords.
        
        Args:
            text: Input text
            
        Returns:
            Set of tokens (non-stopword words)
        """
        # Lowercase
        text = text.lower()
        
        # Split by non-word characters (\W+)
        tokens = re.split(r'\W+', text)
        
        # Remove empty strings and stopwords
        tokens = {token for token in tokens if token and token not in self.STOPWORDS}
        
        return tokens
    
    def _score_to_status(self, score: float) -> str:
        """
        Map Jaccard similarity score to novelty status.
        
        Args:
            score: Jaccard similarity score in range [0.0, 1.0]
            
        Returns:
            "novel" if score < 0.40
            "similar" if 0.40 <= score <= 0.70
            "exists" if score > 0.70
        """
        if score < 0.40:
            return "novel"
        elif score <= 0.70:
            return "similar"
        else:
            return "exists"
