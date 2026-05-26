"""
DBLP Fetcher — Free, no API key required.
Accesses 6M+ computer science papers (conferences + journals).
Docs: https://dblp.org/faq/How+to+use+the+dblp+search+API.html
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import time
from datetime import datetime, timezone
from typing import List, Callable, Optional

from src.core.models import Paper
from src.core.fetchers.base import BaseFetcher


# Map CS categories to DBLP search keywords
# DBLP only covers CS — non-CS categories return empty
CATEGORY_TO_DBLP = {
    "cs.AI": "artificial intelligence",
    "cs.LG": "machine learning deep learning",
    "cs.CL": "natural language processing",
    "cs.CV": "computer vision",
    "cs.RO": "robotics",
    "cs.CR": "security privacy",
    "cs.NE": "neural network evolutionary",
    "cs.SE": "software engineering",
    "cs.IR": "information retrieval",
    "cs.HC": "human computer interaction",
    "cs.DB": "database",
    "cs.DC": "distributed computing",
    "stat.ML": "statistical learning",
    "eess.AS": "speech recognition",
    "eess.IV": "image processing",
    "eess.SP": "signal processing",
}


class DBLPFetcher(BaseFetcher):
    """Fetches CS papers from DBLP (free, no key needed).
    
    Only returns results for CS-related categories.
    Non-CS categories gracefully return empty list.
    """

    BASE_URL = "https://dblp.org/search/publ/api"

    def __init__(self, start_date: datetime, end_date: datetime, emit_fn: Optional[Callable] = None):
        self.start_date = start_date
        self.end_date = end_date
        self.emit_fn = emit_fn

    def _emit(self, event: str, **kwargs):
        if self.emit_fn:
            try:
                self.emit_fn(event, **kwargs)
            except Exception:
                pass

    def fetch_papers(self, category: str, max_results: int = 50) -> List[Paper]:
        """Fetch papers from DBLP. Only works for CS categories."""
        query = CATEGORY_TO_DBLP.get(category)
        if not query:
            return []  # Non-CS category — skip silently

        params = urllib.parse.urlencode({
            "q": query,
            "h": min(max_results, 50),
            "format": "json",
        })
        url = f"{self.BASE_URL}?{params}"

        for attempt in range(3):
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "ScholarScout")

                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())

                hits = data.get("result", {}).get("hits", {}).get("hit", [])
                papers: List[Paper] = []

                for hit in hits:
                    try:
                        paper = self._parse_hit(hit, category)
                        if paper:
                            papers.append(paper)
                    except Exception:
                        continue

                self._emit("cat_fetch_done", cat=category,
                     msg=f"DBLP fetched {len(papers)} papers for {category}")
                return papers

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(5 * (attempt + 1))
                else:
                    time.sleep(3)
            except Exception:
                time.sleep(3)

        return []

    def _parse_hit(self, hit: dict, category: str) -> Optional[Paper]:
        """Parse a DBLP search hit into a Paper object."""
        info = hit.get("info", {})
        if not info:
            return None

        title = info.get("title", "")
        if not title:
            return None
        # DBLP titles sometimes end with a period
        title = title.rstrip(".")

        # Authors
        authors_data = info.get("authors", {}).get("author", [])
        if isinstance(authors_data, dict):
            authors_data = [authors_data]
        authors = []
        for a in authors_data[:5]:
            if isinstance(a, dict):
                authors.append(a.get("text", ""))
            elif isinstance(a, str):
                authors.append(a)

        # URL
        link = info.get("ee", "") or info.get("url", "")
        if isinstance(link, list):
            link = link[0] if link else ""

        # Year / date
        year = info.get("year", "")
        pub_date = f"{year}-01-01" if year else ""

        # Filter by date range
        if year:
            try:
                if int(year) < self.start_date.year:
                    return None
            except (ValueError, TypeError):
                pass

        # DBLP key as ID
        dblp_key = info.get("key", "") or hit.get("@id", "")

        # Venue info
        venue = info.get("venue", "")

        return Paper(
            id=f"DBLP:{dblp_key}" if dblp_key else f"DBLP:{title[:30]}",
            title=title[:300],
            category=category,
            authors="; ".join(authors),
            abstract=f"Published at {venue}. (DBLP does not provide abstracts)" if venue else "(No abstract — DBLP metadata only)",
            link=link,
            submitted_date=pub_date,
            source="dblp",
            citations=0,  # DBLP doesn't provide citation counts
        )
