"""
DOAJ Fetcher — Free, no API key required.
Accesses 9M+ open access articles via DOAJ Search API.
Docs: https://doaj.org/api
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


# Map ScholarScout categories to DOAJ search keywords
CATEGORY_TO_DOAJ = {
    # Medicine & Health (DOAJ strong here)
    "med.cardio": "cardiology heart",
    "med.neuro": "neurology brain",
    "med.onco": "oncology cancer",
    "med.pharma": "pharmacology drug",
    "med.public": "public health epidemiology",
    "med.surgery": "surgery surgical",
    "med.radiology": "radiology imaging",
    "med.genetics": "genetics genomics",
    "med.pediatrics": "pediatrics child",
    "med.infectious": "infectious disease",
    # Biology
    "q-bio.GN": "genomics bioinformatics",
    "q-bio.NC": "neuroscience",
    "q-bio.QM": "computational biology",
    "bio.ecology": "ecology biodiversity",
    "bio.molecular": "molecular biology",
    "bio.microbio": "microbiology",
    "bio.biotech": "biotechnology",
    "bio.marine": "marine biology",
    # Social Sciences (DOAJ strong here)
    "soc.psychology": "psychology",
    "soc.economics": "economics",
    "soc.political": "political science",
    "soc.sociology": "sociology",
    "soc.education": "education pedagogy",
    "soc.communication": "communication media",
    "soc.law": "law legal",
    # Earth & Environmental
    "earth.climate": "climate change",
    "earth.geology": "geology",
    "earth.ocean": "oceanography",
    "earth.atmospheric": "atmospheric",
    "earth.remote": "remote sensing",
    "earth.sustainability": "sustainability",
    # Agriculture (DOAJ strong here)
    "agri.crop": "agriculture crop",
    "agri.animal": "veterinary animal",
    "agri.food": "food science nutrition",
    "agri.forestry": "forestry",
    "agri.aquaculture": "aquaculture",
    # Chemistry
    "chem.organic": "organic chemistry",
    "chem.biochem": "biochemistry",
    "chem.analytical": "analytical chemistry",
    # CS (limited in DOAJ but some)
    "cs.AI": "artificial intelligence",
    "cs.LG": "machine learning",
    "cs.CL": "natural language processing",
}


class DOAJFetcher(BaseFetcher):
    """Fetches open access articles from DOAJ API (free, no key needed)."""

    BASE_URL = "https://doaj.org/api/search/articles"

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
        """Fetch articles from DOAJ for a given category."""
        query = CATEGORY_TO_DOAJ.get(category)
        if not query:
            return []

        # DOAJ search with date filter
        date_from = self.start_date.strftime("%Y-%m-%dT00:00:00Z")
        date_to = self.end_date.strftime("%Y-%m-%dT23:59:59Z")

        # DOAJ uses Elasticsearch query syntax
        search_query = urllib.parse.quote(f"{query}")
        url = f"{self.BASE_URL}/{search_query}?page=1&pageSize={min(max_results, 50)}"

        for attempt in range(3):
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "ScholarScout")

                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())

                results = data.get("results", [])
                papers: List[Paper] = []

                for item in results:
                    try:
                        paper = self._parse_item(item, category)
                        if paper:
                            papers.append(paper)
                    except Exception:
                        continue

                self._emit("cat_fetch_done", cat=category,
                     msg=f"DOAJ fetched {len(papers)} papers for {category}")
                return papers

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(5 * (attempt + 1))
                else:
                    time.sleep(3)
            except Exception:
                time.sleep(3)

        return []

    def _parse_item(self, item: dict, category: str) -> Optional[Paper]:
        """Parse a DOAJ article result into a Paper object."""
        bibjson = item.get("bibjson", {})
        if not bibjson:
            return None

        title = bibjson.get("title", "")
        if not title:
            return None

        # Abstract
        abstract = bibjson.get("abstract", "")
        if not abstract:
            abstract = "(No abstract available)"

        # Authors
        authors = []
        for author in bibjson.get("author", [])[:5]:
            name = author.get("name", "")
            if name:
                authors.append(name)

        # ID
        doaj_id = item.get("id", "")

        # Link (prefer DOI)
        link = ""
        for identifier in bibjson.get("identifier", []):
            if identifier.get("type") == "doi":
                link = f"https://doi.org/{identifier.get('val', '')}"
                break
        if not link:
            links = bibjson.get("link", [])
            if links:
                link = links[0].get("url", "")

        # Date
        pub_date = ""
        year = bibjson.get("year", "")
        month = bibjson.get("month", "1")
        if year:
            try:
                pub_date = f"{year}-{int(month):02d}-01"
            except (ValueError, TypeError):
                pub_date = f"{year}-01-01"

        return Paper(
            id=f"DOAJ:{doaj_id}" if doaj_id else f"DOAJ:{title[:30]}",
            title=title[:300],
            category=category,
            authors="; ".join(authors),
            abstract=abstract[:500],
            link=link,
            submitted_date=pub_date,
            source="doaj",
            citations=0,
        )
