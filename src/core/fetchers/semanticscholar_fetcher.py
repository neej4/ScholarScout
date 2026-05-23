"""
Semantic Scholar Fetcher — Free, no API key required (rate limited to 100 req/5min).
Accesses 200M+ papers with citation data.
Docs: https://api.semanticscholar.org/
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import os
import time
from datetime import datetime, timezone
from typing import List, Callable, Optional

from src.core.models import Paper
from src.core.fetchers.base import BaseFetcher


# Map categories to Semantic Scholar search keywords
CATEGORY_TO_KEYWORDS = {
    # Computer Science
    "cs.AI": "artificial intelligence agents reasoning",
    "cs.LG": "machine learning deep learning",
    "cs.CL": "natural language processing large language models",
    "cs.CV": "computer vision image recognition",
    "cs.RO": "robotics manipulation locomotion",
    "cs.CR": "cybersecurity adversarial attacks privacy",
    "cs.NE": "neural networks evolutionary computation",
    "cs.SE": "software engineering code generation",
    "cs.IR": "information retrieval recommendation systems",
    "cs.HC": "human-computer interaction user experience",
    "cs.DB": "database systems query optimization",
    "cs.DC": "distributed systems cloud computing",
    # Medicine & Health
    "med.cardio": "cardiology heart disease cardiac",
    "med.neuro": "neurology psychiatry brain disorders",
    "med.onco": "oncology cancer tumor treatment",
    "med.pharma": "pharmacology drug discovery therapeutics",
    "med.public": "public health epidemiology disease prevention",
    "med.surgery": "surgery surgical techniques minimally invasive",
    "med.radiology": "radiology medical imaging diagnosis",
    "med.genetics": "medical genetics gene therapy hereditary",
    "med.pediatrics": "pediatrics child health neonatal",
    "med.infectious": "infectious disease pathogen antimicrobial",
    # Biology
    "q-bio.GN": "genomics bioinformatics",
    "q-bio.NC": "neuroscience brain-computer interface",
    "q-bio.QM": "computational biology systems biology",
    "bio.ecology": "ecology evolution biodiversity",
    "bio.molecular": "molecular biology gene expression protein",
    "bio.microbio": "microbiology bacteria microbiome",
    "bio.biotech": "biotechnology genetic engineering CRISPR",
    "bio.marine": "marine biology ocean ecosystem",
    # Physics
    "physics.med-ph": "medical physics radiotherapy",
    "physics.optics": "optics photonics laser",
    "physics.quantum": "quantum computing quantum mechanics",
    "physics.astro": "astrophysics cosmology exoplanet",
    "physics.condensed": "condensed matter superconductor",
    "physics.nuclear": "nuclear physics particle accelerator",
    "physics.plasma": "plasma physics fusion energy",
    # Engineering
    "eess.AS": "speech recognition audio processing",
    "eess.IV": "medical imaging image processing",
    "eess.SP": "signal processing radar",
    "eng.civil": "civil engineering structural analysis",
    "eng.mechanical": "mechanical engineering thermodynamics",
    "eng.chemical": "chemical engineering process design",
    "eng.materials": "materials science nanomaterials",
    "eng.biomedical": "biomedical engineering prosthetics",
    "eng.environmental": "environmental engineering water treatment",
    # Chemistry
    "chem.organic": "organic chemistry synthesis",
    "chem.inorganic": "inorganic chemistry catalysis",
    "chem.analytical": "analytical chemistry spectroscopy",
    "chem.physical": "physical chemistry thermodynamics",
    "chem.biochem": "biochemistry enzymes metabolism",
    "chem.computational": "computational chemistry molecular simulation",
    # Mathematics
    "stat.ML": "statistical machine learning bayesian",
    "math.OC": "optimization control theory",
    "math.ST": "statistics hypothesis testing",
    "math.NA": "numerical analysis finite element",
    "math.CO": "combinatorics graph theory",
    "math.AP": "applied mathematics differential equations",
    # Social Sciences
    "soc.psychology": "psychology cognitive science behavior",
    "soc.economics": "economics finance market",
    "soc.political": "political science governance policy",
    "soc.sociology": "sociology social networks inequality",
    "soc.education": "education learning pedagogy",
    "soc.communication": "communication media journalism",
    "soc.law": "law legal technology regulation",
    # Earth & Environmental
    "earth.climate": "climate change global warming",
    "earth.geology": "geology geophysics seismology",
    "earth.ocean": "oceanography marine science",
    "earth.atmospheric": "atmospheric science weather prediction",
    "earth.remote": "remote sensing satellite GIS",
    "earth.sustainability": "sustainability renewable energy",
    # Agriculture
    "agri.crop": "crop science agronomy plant breeding",
    "agri.animal": "animal science veterinary livestock",
    "agri.food": "food science nutrition processing",
    "agri.forestry": "forestry conservation natural resources",
    "agri.aquaculture": "aquaculture fisheries marine farming",
}


class SemanticScholarFetcher(BaseFetcher):
    """Fetches papers from Semantic Scholar API.
    
    Free tier: 100 req/5min (unauthenticated).
    With API key: 10,000 req/5min (free, register at semanticscholar.org/product/api).
    """
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    def __init__(self, start_date: datetime, end_date: datetime, emit_fn: Optional[Callable] = None):
        self.start_date = start_date
        self.end_date = end_date
        self.emit_fn = emit_fn
        # S2 API key from environment (optional, massively increases rate limit)
        self.api_key = os.environ.get("S2_API_KEY", "")

    def _emit(self, event: str, **kwargs):
        if self.emit_fn:
            try:
                self.emit_fn(event, **kwargs)
            except Exception:
                pass

    def fetch_papers(self, category: str, max_results: int = 50) -> List[Paper]:
        """Fetch recent papers from Semantic Scholar by category keywords."""
        keywords = CATEGORY_TO_KEYWORDS.get(category, category.replace(".", " "))
        year = self.start_date.year
        
        params = urllib.parse.urlencode({
            "query": keywords,
            "fields": "title,abstract,authors,url,publicationDate,externalIds,citationCount",
            "limit": min(max_results, 50),
            "year": f"{year}-",
            "sort": "publicationDate:desc"
        })
        
        url = f"{self.BASE_URL}?{params}"
        
        for attempt in range(3):
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "ScholarScout/1.4")
                if self.api_key:
                    req.add_header("x-api-key", self.api_key)
                
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode())
                
                results = data.get("data", [])
                papers: List[Paper] = []
                
                for item in results:
                    try:
                        paper = self._parse_paper(item, category)
                        if paper:
                            papers.append(paper)
                            self._emit("paper_found", cat=category,
                                 msg=f"S2 [{category}] {paper.title[:55]}...")
                    except Exception:
                        continue
                
                self._emit("cat_fetch_done", cat=category,
                     msg=f"Semantic Scholar fetched {len(papers)} papers for {category}")
                return papers
                
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # Progressive backoff: 15s, 30s, 60s
                    wait = 15 * (attempt + 1)
                    self._emit("fetch_retry", cat=category,
                         msg=f"S2 rate limited (429) — waiting {wait}s (attempt {attempt+1}/3)")
                    time.sleep(wait)
                elif e.code == 504 or e.code == 503:
                    # Server overloaded — wait and retry
                    wait = 10 * (attempt + 1)
                    self._emit("fetch_retry", cat=category,
                         msg=f"S2 server busy ({e.code}) — waiting {wait}s")
                    time.sleep(wait)
                else:
                    self._emit("fetch_retry", cat=category,
                         msg=f"S2 HTTP {e.code} for {category}")
                    return []
            except Exception as e:
                if attempt < 2:
                    self._emit("fetch_retry", cat=category,
                         msg=f"S2 error for {category}: {str(e)[:40]} — retrying")
                    time.sleep(5)
                else:
                    self._emit("fetch_retry", cat=category,
                         msg=f"S2 failed for {category} after 3 attempts")
                    return []
        
        return []

    def _parse_paper(self, item: dict, category: str) -> Optional[Paper]:
        """Parse a Semantic Scholar paper object into a Paper."""
        title = item.get("title", "")
        if not title:
            return None
        
        # Filter by date range
        pub_date = item.get("publicationDate", "")
        if pub_date:
            try:
                dt = datetime.fromisoformat(pub_date + "T00:00:00+00:00") if "T" not in pub_date else datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                if dt < self.start_date or dt > self.end_date:
                    return None
            except (ValueError, TypeError):
                pass
        
        # Get paper ID
        external_ids = item.get("externalIds", {}) or {}
        paper_id = external_ids.get("ArXiv") or external_ids.get("DOI") or item.get("paperId", "")
        
        # Get authors
        authors = []
        for author in item.get("authors", [])[:5]:
            name = author.get("name", "")
            if name:
                authors.append(name)
        
        # Get URL
        url = item.get("url", "")
        if not url and external_ids.get("ArXiv"):
            url = f"https://arxiv.org/abs/{external_ids['ArXiv']}"
        elif not url and external_ids.get("DOI"):
            url = f"https://doi.org/{external_ids['DOI']}"
        
        # Abstract
        abstract = item.get("abstract", "") or "(No abstract available)"
        if len(abstract) > 500:
            abstract = abstract[:500]
        
        return Paper(
            id=f"s2:{paper_id}" if not paper_id.startswith("s2:") else paper_id,
            title=title.strip(),
            category=category,
            authors="; ".join(authors),
            abstract=abstract,
            link=url,
            submitted_date=pub_date or "",
            source="semantic_scholar",
            citations=item.get("citationCount", 0) or 0
        )
