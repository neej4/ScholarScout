"""
Crossref Fetcher — Free, no API key required.
Accesses 150M+ scholarly works via the Crossref REST API.
Docs: https://api.crossref.org/swagger-ui/index.html
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


# Map ScholarScout categories to Crossref search queries
CATEGORY_TO_CROSSREF = {
    # Computer Science
    "cs.AI": "artificial intelligence",
    "cs.LG": "machine learning deep learning",
    "cs.CL": "natural language processing",
    "cs.CV": "computer vision",
    "cs.RO": "robotics autonomous",
    "cs.CR": "cybersecurity privacy",
    "cs.NE": "neural networks evolutionary",
    "cs.SE": "software engineering",
    "cs.IR": "information retrieval search",
    "cs.HC": "human computer interaction",
    "cs.DB": "database query",
    "cs.DC": "distributed computing cloud",
    # Medicine & Health
    "med.cardio": "cardiology cardiac heart",
    "med.neuro": "neurology brain neurological",
    "med.onco": "oncology cancer tumor",
    "med.pharma": "pharmacology drug therapy",
    "med.public": "public health epidemiology",
    "med.surgery": "surgery surgical",
    "med.radiology": "radiology imaging",
    "med.genetics": "genetics genomics hereditary",
    "med.pediatrics": "pediatrics children neonatal",
    "med.infectious": "infectious disease pathogen",
    # Biology
    "q-bio.GN": "genomics bioinformatics",
    "q-bio.NC": "neuroscience brain",
    "q-bio.QM": "computational biology",
    "bio.ecology": "ecology biodiversity ecosystem",
    "bio.molecular": "molecular biology gene",
    "bio.microbio": "microbiology microbiome",
    "bio.biotech": "biotechnology genetic engineering",
    "bio.marine": "marine biology ocean",
    # Physics
    "physics.med-ph": "medical physics radiotherapy",
    "physics.optics": "optics photonics",
    "physics.quantum": "quantum computing",
    "physics.astro": "astrophysics cosmology",
    "physics.condensed": "condensed matter",
    "physics.nuclear": "nuclear physics",
    "physics.plasma": "plasma physics fusion",
    # Engineering
    "eess.AS": "speech recognition audio",
    "eess.IV": "image processing medical imaging",
    "eess.SP": "signal processing",
    "eng.civil": "civil engineering structural",
    "eng.mechanical": "mechanical engineering",
    "eng.chemical": "chemical engineering",
    "eng.materials": "materials science nanomaterials",
    "eng.biomedical": "biomedical engineering",
    "eng.environmental": "environmental engineering",
    # Chemistry
    "chem.organic": "organic chemistry synthesis",
    "chem.inorganic": "inorganic chemistry catalysis",
    "chem.analytical": "analytical chemistry spectroscopy",
    "chem.physical": "physical chemistry thermodynamics",
    "chem.biochem": "biochemistry enzymes",
    "chem.computational": "computational chemistry molecular",
    # Mathematics
    "stat.ML": "statistical learning",
    "math.OC": "optimization control",
    "math.ST": "statistics inference",
    "math.NA": "numerical analysis",
    "math.CO": "combinatorics graph theory",
    "math.AP": "applied mathematics",
    # Social Sciences
    "soc.psychology": "psychology cognitive",
    "soc.economics": "economics finance",
    "soc.political": "political science governance",
    "soc.sociology": "sociology social",
    "soc.education": "education learning pedagogy",
    "soc.communication": "communication media",
    "soc.law": "law legal regulation",
    # Earth & Environmental
    "earth.climate": "climate change warming",
    "earth.geology": "geology geophysics",
    "earth.ocean": "oceanography marine",
    "earth.atmospheric": "atmospheric weather",
    "earth.remote": "remote sensing satellite",
    "earth.sustainability": "sustainability renewable",
    # Agriculture
    "agri.crop": "crop agriculture plant",
    "agri.animal": "animal science veterinary",
    "agri.food": "food science nutrition",
    "agri.forestry": "forestry conservation",
    "agri.aquaculture": "aquaculture fisheries",
}


class CrossrefFetcher(BaseFetcher):
    """Fetches papers from Crossref REST API (free, no key needed).
    
    Rate limit: ~50 req/sec with polite pool (mailto header).
    """

    BASE_URL = "https://api.crossref.org/works"

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
        """Fetch papers from Crossref for a given category."""
        query = CATEGORY_TO_CROSSREF.get(category)
        if not query:
            return []

        date_from = self.start_date.strftime("%Y-%m-%d")
        date_to = self.end_date.strftime("%Y-%m-%d")

        params = urllib.parse.urlencode({
            "query": query,
            "filter": f"from-pub-date:{date_from},until-pub-date:{date_to},type:journal-article",
            "sort": "published",
            "order": "desc",
            "rows": min(max_results, 50),
            "select": "DOI,title,author,abstract,published,is-referenced-by-count,link",
            "mailto": "scholarscout@users.noreply.github.com",
        })
        url = f"{self.BASE_URL}?{params}"

        for attempt in range(3):
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "ScholarScout/1.5 (mailto:scholarscout@users.noreply.github.com)")

                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode())

                items = data.get("message", {}).get("items", [])
                papers: List[Paper] = []

                for item in items:
                    try:
                        paper = self._parse_item(item, category)
                        if paper:
                            papers.append(paper)
                    except Exception:
                        continue

                self._emit("cat_fetch_done", cat=category,
                     msg=f"Crossref fetched {len(papers)} papers for {category}")
                return papers

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = 5 * (attempt + 1)
                    self._emit("fetch_retry", cat=category,
                         msg=f"Crossref rate limited — waiting {wait}s")
                    time.sleep(wait)
                else:
                    self._emit("fetch_retry", cat=category,
                         msg=f"Crossref HTTP {e.code} (attempt {attempt+1}/3)")
                    time.sleep(3)
            except Exception as e:
                self._emit("fetch_retry", cat=category,
                     msg=f"Crossref attempt {attempt+1}/3: {str(e)[:60]}")
                time.sleep(3)

        self._emit("cat_error", cat=category, msg=f"Crossref failed for {category} after 3 attempts")
        return []

    def _parse_item(self, item: dict, category: str) -> Optional[Paper]:
        """Parse a Crossref work item into a Paper object."""
        # Title
        titles = item.get("title", [])
        title = titles[0] if titles else ""
        if not title:
            return None

        # DOI
        doi = item.get("DOI", "")
        paper_id = f"DOI:{doi}" if doi else ""
        if not paper_id:
            return None

        # Abstract (Crossref provides it as JATS XML sometimes)
        abstract = item.get("abstract", "")
        if abstract:
            # Strip JATS XML tags
            import re
            abstract = re.sub(r"<[^>]+>", "", abstract).strip()
        if not abstract:
            abstract = "(No abstract available)"

        # Authors (first 5)
        authors = []
        for author in item.get("author", [])[:5]:
            given = author.get("given", "")
            family = author.get("family", "")
            if family:
                name = f"{given} {family}".strip()
                authors.append(name)

        # Publication date
        pub_date = ""
        published = item.get("published", {})
        date_parts = published.get("date-parts", [[]])
        if date_parts and date_parts[0]:
            parts = date_parts[0]
            year = parts[0] if len(parts) > 0 else 2024
            month = parts[1] if len(parts) > 1 else 1
            day = parts[2] if len(parts) > 2 else 1
            pub_date = f"{year}-{month:02d}-{day:02d}"

        # Link
        link = f"https://doi.org/{doi}" if doi else ""

        # Citation count
        citations = item.get("is-referenced-by-count", 0) or 0

        return Paper(
            id=paper_id,
            title=title[:300],
            category=category,
            authors="; ".join(authors),
            abstract=abstract[:500],
            link=link,
            submitted_date=pub_date,
            source="crossref",
            citations=citations,
        )
