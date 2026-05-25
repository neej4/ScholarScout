"""
Scopus/Elsevier Fetcher — Free for academic non-commercial use.
Accesses 90M+ records via Scopus Search API.
Requires API key from https://dev.elsevier.com/
Docs: https://dev.elsevier.com/documentation/SCOPUSSearchAPI.wadl

API key is optional — if not set (SCOPUS_API_KEY env var), this fetcher
gracefully returns empty results without blocking the pipeline.
"""
import os
import urllib.request
import urllib.parse
import urllib.error
import json
import time
from datetime import datetime, timezone
from typing import List, Callable, Optional

from src.core.models import Paper
from src.core.fetchers.base import BaseFetcher


# Map ScholarScout categories to Scopus subject area codes (SUBJAREA)
CATEGORY_TO_SCOPUS = {
    # Computer Science
    "cs.AI": "COMP",
    "cs.LG": "COMP",
    "cs.CL": "COMP",
    "cs.CV": "COMP",
    "cs.RO": "COMP",
    "cs.CR": "COMP",
    "cs.NE": "COMP",
    "cs.SE": "COMP",
    "cs.IR": "COMP",
    "cs.HC": "COMP",
    "cs.DB": "COMP",
    "cs.DC": "COMP",
    # Medicine
    "med.cardio": "MEDI",
    "med.neuro": "NEUR",
    "med.onco": "MEDI",
    "med.pharma": "PHAR",
    "med.public": "MEDI",
    "med.surgery": "MEDI",
    "med.radiology": "MEDI",
    "med.genetics": "BIOC",
    "med.pediatrics": "MEDI",
    "med.infectious": "IMMU",
    # Biology
    "q-bio.GN": "BIOC",
    "q-bio.NC": "NEUR",
    "q-bio.QM": "BIOC",
    "bio.ecology": "AGRI",
    "bio.molecular": "BIOC",
    "bio.microbio": "IMMU",
    "bio.biotech": "BIOC",
    "bio.marine": "EART",
    # Physics
    "physics.med-ph": "PHYS",
    "physics.optics": "PHYS",
    "physics.quantum": "PHYS",
    "physics.astro": "PHYS",
    "physics.condensed": "PHYS",
    "physics.nuclear": "PHYS",
    "physics.plasma": "PHYS",
    # Engineering
    "eess.AS": "ENGI",
    "eess.IV": "ENGI",
    "eess.SP": "ENGI",
    "eng.civil": "ENGI",
    "eng.mechanical": "ENGI",
    "eng.chemical": "CENG",
    "eng.materials": "MATE",
    "eng.biomedical": "ENGI",
    "eng.environmental": "ENVI",
    # Chemistry
    "chem.organic": "CHEM",
    "chem.inorganic": "CHEM",
    "chem.analytical": "CHEM",
    "chem.physical": "CHEM",
    "chem.biochem": "BIOC",
    "chem.computational": "CHEM",
    # Mathematics
    "stat.ML": "MATH",
    "math.OC": "MATH",
    "math.ST": "MATH",
    "math.NA": "MATH",
    "math.CO": "MATH",
    "math.AP": "MATH",
    # Social Sciences
    "soc.psychology": "PSYC",
    "soc.economics": "ECON",
    "soc.political": "SOCI",
    "soc.sociology": "SOCI",
    "soc.education": "SOCI",
    "soc.communication": "SOCI",
    "soc.law": "SOCI",
    # Earth
    "earth.climate": "EART",
    "earth.geology": "EART",
    "earth.ocean": "EART",
    "earth.atmospheric": "EART",
    "earth.remote": "EART",
    "earth.sustainability": "ENVI",
    # Agriculture
    "agri.crop": "AGRI",
    "agri.animal": "VETE",
    "agri.food": "AGRI",
    "agri.forestry": "AGRI",
    "agri.aquaculture": "AGRI",
}

# More specific keywords per category for Scopus title/abstract search
CATEGORY_TO_KEYWORDS = {
    "cs.AI": "artificial intelligence",
    "cs.LG": "machine learning OR deep learning",
    "cs.CL": "natural language processing",
    "cs.CV": "computer vision",
    "cs.RO": "robotics",
    "med.cardio": "cardiology OR cardiac",
    "med.neuro": "neurology OR neurological",
    "med.onco": "oncology OR cancer",
    "med.pharma": "pharmacology OR drug discovery",
    "med.public": "public health OR epidemiology",
    "bio.ecology": "ecology OR biodiversity",
    "bio.molecular": "molecular biology",
    "soc.psychology": "psychology OR cognitive",
    "soc.economics": "economics OR finance",
    "earth.climate": "climate change",
    "agri.crop": "crop science OR agronomy",
}


class ScopusFetcher(BaseFetcher):
    """Fetches papers from Scopus API (requires SCOPUS_API_KEY env var).
    
    If no API key is set, returns empty list gracefully.
    Free tier: 2 req/sec, 5000 req/week for academic non-commercial use.
    """

    BASE_URL = "https://api.elsevier.com/content/search/scopus"

    def __init__(self, start_date: datetime, end_date: datetime, emit_fn: Optional[Callable] = None):
        self.start_date = start_date
        self.end_date = end_date
        self.emit_fn = emit_fn
        self.api_key = os.environ.get("SCOPUS_API_KEY", "")

    def _emit(self, event: str, **kwargs):
        if self.emit_fn:
            try:
                self.emit_fn(event, **kwargs)
            except Exception:
                pass

    def fetch_papers(self, category: str, max_results: int = 50) -> List[Paper]:
        """Fetch papers from Scopus. Returns empty if no API key."""
        if not self.api_key:
            return []  # Graceful skip — no key, no fetch

        subj_area = CATEGORY_TO_SCOPUS.get(category)
        if not subj_area:
            return []

        # Build Scopus query
        keywords = CATEGORY_TO_KEYWORDS.get(category, "")
        date_from = self.start_date.strftime("%Y")
        date_to = self.end_date.strftime("%Y")

        if keywords:
            query = f"TITLE-ABS-KEY({keywords}) AND SUBJAREA({subj_area}) AND PUBYEAR > {int(date_from) - 1}"
        else:
            query = f"SUBJAREA({subj_area}) AND PUBYEAR > {int(date_from) - 1}"

        params = urllib.parse.urlencode({
            "query": query,
            "count": min(max_results, 25),  # Scopus limits to 25 per page on free tier
            "sort": "-coverDate",
            "field": "dc:title,dc:creator,prism:coverDate,prism:doi,dc:description,citedby-count",
        })
        url = f"{self.BASE_URL}?{params}"

        for attempt in range(3):
            try:
                req = urllib.request.Request(url)
                req.add_header("X-ELS-APIKey", self.api_key)
                req.add_header("Accept", "application/json")

                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())

                entries = data.get("search-results", {}).get("entry", [])
                papers: List[Paper] = []

                for entry in entries:
                    try:
                        paper = self._parse_entry(entry, category)
                        if paper:
                            papers.append(paper)
                    except Exception:
                        continue

                self._emit("cat_fetch_done", cat=category,
                     msg=f"Scopus fetched {len(papers)} papers for {category}")
                return papers

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(5 * (attempt + 1))
                elif e.code == 401:
                    self._emit("fetch_error", cat=category,
                         msg="Scopus API key invalid or expired")
                    return []
                else:
                    time.sleep(3)
            except Exception:
                time.sleep(3)

        return []

    def _parse_entry(self, entry: dict, category: str) -> Optional[Paper]:
        """Parse a Scopus search result entry."""
        # Skip error entries
        if entry.get("@_fa") == "false" or "error" in entry:
            return None

        title = entry.get("dc:title", "")
        if not title:
            return None

        # Abstract (Scopus calls it dc:description)
        abstract = entry.get("dc:description", "")
        if not abstract:
            abstract = "(No abstract available)"

        # Author
        author = entry.get("dc:creator", "")

        # DOI
        doi = entry.get("prism:doi", "")
        link = f"https://doi.org/{doi}" if doi else entry.get("prism:url", "")

        # Date
        pub_date = entry.get("prism:coverDate", "")

        # Citations
        citations = int(entry.get("citedby-count", 0) or 0)

        # ID
        scopus_id = entry.get("dc:identifier", "").replace("SCOPUS_ID:", "")

        return Paper(
            id=f"SCOPUS:{scopus_id}" if scopus_id else f"DOI:{doi}",
            title=title[:300],
            category=category,
            authors=author,
            abstract=abstract[:500],
            link=link,
            submitted_date=pub_date,
            source="scopus",
            citations=citations,
        )
