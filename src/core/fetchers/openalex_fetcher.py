"""
OpenAlex Fetcher — Free, no API key required.
Accesses 250M+ academic works via the OpenAlex API.
Docs: https://docs.openalex.org/
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


# OpenAlex concept IDs mapped from categories
CATEGORY_TO_OPENALEX = {
    # Computer Science
    "cs.AI": "C154945302",       # Artificial intelligence
    "cs.LG": "C119857082",       # Machine learning
    "cs.CL": "C204321447",       # Computational linguistics / NLP
    "cs.CV": "C31972630",        # Computer vision
    "cs.RO": "C191935318",       # Robotics
    "cs.CR": "C38652104",        # Computer security
    "cs.NE": "C126838900",       # Neural networks
    "cs.SE": "C121332964",       # Software engineering
    "cs.IR": "C17744445",        # Information retrieval
    "cs.HC": "C105795698",       # Human-computer interaction
    "cs.DB": "C77088390",        # Database
    "cs.DC": "C108583219",       # Distributed computing
    # Medicine & Health
    "med.cardio": "C71924100",   # Cardiology
    "med.neuro": "C134018914",   # Neurology
    "med.onco": "C126322002",    # Oncology
    "med.pharma": "C55493867",   # Pharmacology
    "med.public": "C118552586",  # Public health
    "med.surgery": "C126838900", # Surgery
    "med.radiology": "C16674752",# Radiology
    "med.genetics": "C54355233", # Genetics
    "med.pediatrics": "C126322002",# Pediatrics
    "med.infectious": "C126322002",# Infectious disease
    # Biology
    "q-bio.GN": "C54355233",    # Genomics
    "q-bio.NC": "C41008148",    # Neuroscience
    "q-bio.QM": "C86803240",    # Bioinformatics
    "bio.ecology": "C18903297", # Ecology
    "bio.molecular": "C153911025",# Molecular biology
    "bio.microbio": "C89423630",# Microbiology
    "bio.biotech": "C28490314", # Biotechnology
    "bio.marine": "C55493867",  # Marine biology
    # Physics
    "physics.med-ph": "C126322002",
    "physics.optics": "C120665830",# Optics
    "physics.quantum": "C62520636",# Quantum mechanics
    "physics.astro": "C44249647",# Astrophysics
    "physics.condensed": "C33332235",# Condensed matter
    "physics.nuclear": "C121864883",# Nuclear physics
    "physics.plasma": "C6557445",# Plasma
    # Engineering
    "eess.AS": "C152779818",    # Speech recognition
    "eess.IV": "C44123533",     # Image processing
    "eess.SP": "C108827166",    # Signal processing
    "eng.civil": "C162324750",  # Civil engineering
    "eng.mechanical": "C178790620",# Mechanical engineering
    "eng.chemical": "C185592680",# Chemical engineering
    "eng.materials": "C192562407",# Materials science
    "eng.biomedical": "C55493867",# Biomedical engineering
    "eng.environmental": "C39432304",# Environmental engineering
    # Chemistry
    "chem.organic": "C185592680",# Organic chemistry
    "chem.inorganic": "C178790620",# Inorganic chemistry
    "chem.analytical": "C159985019",# Analytical chemistry
    "chem.physical": "C62520636",# Physical chemistry
    "chem.biochem": "C55493867",# Biochemistry
    "chem.computational": "C119857082",# Computational chemistry
    # Mathematics
    "stat.ML": "C119857082",    # Machine learning
    "math.OC": "C134306372",    # Mathematical optimization
    "math.ST": "C105795698",    # Statistics
    "math.NA": "C134306372",    # Numerical analysis
    "math.CO": "C134306372",    # Combinatorics
    "math.AP": "C134306372",    # Applied mathematics
    # Social Sciences
    "soc.psychology": "C15744967",# Psychology
    "soc.economics": "C162324750",# Economics
    "soc.political": "C17744445",# Political science
    "soc.sociology": "C144024400",# Sociology
    "soc.education": "C185592680",# Education
    "soc.communication": "C204321447",# Communication
    "soc.law": "C138885662",    # Law
    # Earth & Environmental
    "earth.climate": "C39432304",# Climate
    "earth.geology": "C127313418",# Geology
    "earth.ocean": "C55493867", # Oceanography
    "earth.atmospheric": "C39432304",# Atmospheric science
    "earth.remote": "C44123533",# Remote sensing
    "earth.sustainability": "C39432304",# Sustainability
    # Agriculture
    "agri.crop": "C118552586",  # Agronomy
    "agri.animal": "C55493867", # Animal science
    "agri.food": "C55493867",   # Food science
    "agri.forestry": "C18903297",# Forestry
    "agri.aquaculture": "C55493867",# Aquaculture
}


class OpenAlexFetcher(BaseFetcher):
    """Fetches papers from OpenAlex API (free, no key needed)."""
    
    BASE_URL = "https://api.openalex.org/works"
    
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

    # Categories that work better with keyword search (concept IDs unreliable)
    KEYWORD_SEARCH_CATEGORIES = {
        "med.cardio": "cardiology heart cardiac",
        "med.neuro": "neurology brain neurological",
        "med.onco": "oncology cancer tumor",
        "med.pharma": "pharmacology drug therapy",
        "med.public": "public health epidemiology",
        "med.surgery": "surgery surgical operation",
        "med.radiology": "radiology imaging CT MRI",
        "med.genetics": "genetics genomics hereditary",
        "med.pediatrics": "pediatrics children neonatal",
        "med.infectious": "infectious disease pathogen",
        "bio.ecology": "ecology ecosystem biodiversity",
        "bio.molecular": "molecular biology gene protein",
        "bio.microbio": "microbiology bacteria microbiome",
        "bio.biotech": "biotechnology genetic engineering",
        "bio.marine": "marine biology ocean aquatic",
        "soc.psychology": "psychology cognitive behavior",
        "soc.economics": "economics finance market",
        "soc.political": "political science governance",
        "soc.sociology": "sociology social inequality",
        "soc.education": "education learning pedagogy",
        "soc.communication": "communication media digital",
        "soc.law": "law legal regulation",
        "earth.climate": "climate change warming carbon",
        "earth.geology": "geology geophysics seismology",
        "earth.ocean": "oceanography marine ocean",
        "earth.atmospheric": "atmospheric weather meteorology",
        "earth.remote": "remote sensing satellite GIS",
        "earth.sustainability": "sustainability renewable energy",
        "agri.crop": "crop agriculture plant breeding",
        "agri.animal": "animal science livestock veterinary",
        "agri.food": "food science nutrition safety",
        "agri.forestry": "forestry conservation trees",
        "agri.aquaculture": "aquaculture fish farming",
        "chem.organic": "organic chemistry synthesis",
        "chem.inorganic": "inorganic chemistry metal",
        "chem.analytical": "analytical chemistry spectroscopy",
        "chem.physical": "physical chemistry thermodynamics",
        "chem.biochem": "biochemistry enzyme protein",
        "chem.computational": "computational chemistry molecular simulation",
    }

    def fetch_papers(self, category: str, max_results: int = 50) -> List[Paper]:
        """Fetch papers from OpenAlex by concept/topic."""
        # Use keyword search for categories with unreliable concept IDs
        if category in self.KEYWORD_SEARCH_CATEGORIES:
            return self._fetch_by_keyword_direct(category, self.KEYWORD_SEARCH_CATEGORIES[category], max_results)
        
        concept_id = CATEGORY_TO_OPENALEX.get(category)
        if not concept_id:
            return self._fetch_by_keyword(category, max_results)
        
        return self._fetch_by_concept(category, concept_id, max_results)

    def _fetch_by_keyword_direct(self, category: str, keywords: str, max_results: int) -> List[Paper]:
        """Fetch by direct keyword search (more reliable for non-CS categories)."""
        date_from = self.start_date.strftime("%Y-%m-%d")
        date_to = self.end_date.strftime("%Y-%m-%d")
        
        params = urllib.parse.urlencode({
            "search": keywords,
            "filter": f"from_publication_date:{date_from},to_publication_date:{date_to},type:article",
            "sort": "publication_date:desc",
            "per_page": min(max_results, 50),
            "select": "id,title,authorships,abstract_inverted_index,publication_date,primary_location,concepts,cited_by_count",
            "mailto": "scholarscout@users.noreply.github.com"
        })
        
        url = f"{self.BASE_URL}?{params}"
        return self._do_fetch(url, category)

    def _fetch_by_concept(self, category: str, concept_id: str, max_results: int) -> List[Paper]:
        """Fetch by OpenAlex concept ID."""
        date_from = self.start_date.strftime("%Y-%m-%d")
        date_to = self.end_date.strftime("%Y-%m-%d")
        
        params = urllib.parse.urlencode({
            "filter": f"concepts.id:{concept_id},from_publication_date:{date_from},to_publication_date:{date_to}",
            "sort": "publication_date:desc",
            "per_page": min(max_results, 50),
            "select": "id,title,authorships,abstract_inverted_index,publication_date,primary_location,concepts,cited_by_count",
            "mailto": "scholarscout@users.noreply.github.com"
        })
        
        url = f"{self.BASE_URL}?{params}"
        return self._do_fetch(url, category)

    def _fetch_by_keyword(self, category: str, max_results: int) -> List[Paper]:
        """Fallback: search by keyword derived from category name."""
        # Extract keyword from category (e.g., "cs.AI" -> "artificial intelligence")
        keyword = category.split(".")[-1] if "." in category else category
        date_from = self.start_date.strftime("%Y-%m-%d")
        date_to = self.end_date.strftime("%Y-%m-%d")
        
        params = urllib.parse.urlencode({
            "search": keyword,
            "filter": f"from_publication_date:{date_from},to_publication_date:{date_to}",
            "sort": "publication_date:desc",
            "per_page": min(max_results, 50),
            "select": "id,title,authorships,abstract_inverted_index,publication_date,primary_location,concepts,cited_by_count",
            "mailto": "scholarscout@users.noreply.github.com"
        })
        
        url = f"{self.BASE_URL}?{params}"
        return self._do_fetch(url, category)

    def _do_fetch(self, url: str, category: str) -> List[Paper]:
        """Execute the API request and parse results."""
        for attempt in range(3):
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "ScholarScout/1.0 (mailto:scholarscout@users.noreply.github.com)")
                
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode())
                    
                results = data.get("results", [])
                papers: List[Paper] = []
                
                for work in results:
                    try:
                        paper = self._parse_work(work, category)
                        if paper:
                            papers.append(paper)
                            self._emit("paper_found", cat=category,
                                 msg=f"OPENALEX [{category}] {paper.title[:55]}...")
                    except Exception:
                        continue
                
                self._emit("cat_fetch_done", cat=category,
                     msg=f"OpenAlex fetched {len(papers)} papers for {category}")
                return papers
                
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = 5 * (attempt + 1)
                    self._emit("fetch_retry", cat=category,
                         msg=f"OpenAlex rate limited — waiting {wait}s (attempt {attempt+1}/3)")
                    time.sleep(wait)
                else:
                    self._emit("fetch_retry", cat=category,
                         msg=f"OpenAlex HTTP {e.code} for {category} (attempt {attempt+1}/3)")
                    time.sleep(3)
            except Exception as e:
                self._emit("fetch_retry", cat=category,
                     msg=f"OpenAlex attempt {attempt+1}/3 for {category}: {str(e)[:60]}")
                time.sleep(3)
        
        self._emit("cat_error", cat=category, msg=f"OpenAlex failed for {category} after 3 attempts")
        return []

    def _parse_work(self, work: dict, category: str) -> Optional[Paper]:
        """Parse an OpenAlex work object into a Paper."""
        title = work.get("title", "")
        if not title:
            return None
        
        # Reconstruct abstract from inverted index
        abstract = self._reconstruct_abstract(work.get("abstract_inverted_index"))
        if not abstract:
            abstract = "(No abstract available)"
        
        # Get OpenAlex ID (strip URL prefix)
        oa_id = work.get("id", "").replace("https://openalex.org/", "")
        
        # Get authors (first 5)
        authors = []
        for authorship in work.get("authorships", [])[:5]:
            author = authorship.get("author", {})
            name = author.get("display_name", "")
            if name:
                authors.append(name)
        
        # Get URL (prefer DOI, fallback to OpenAlex page)
        link = ""
        primary = work.get("primary_location", {}) or {}
        if primary.get("landing_page_url"):
            link = primary["landing_page_url"]
        elif work.get("doi"):
            link = work["doi"]
        else:
            link = f"https://openalex.org/{oa_id}"
        
        # Publication date
        pub_date = work.get("publication_date", "")
        
        return Paper(
            id=oa_id,
            title=title.strip(),
            category=category,
            authors="; ".join(authors),
            abstract=abstract[:500],
            link=link,
            submitted_date=pub_date,
            source="openalex",
            citations=work.get("cited_by_count", 0) or 0
        )

    def _reconstruct_abstract(self, inverted_index: Optional[dict]) -> str:
        """Reconstruct abstract text from OpenAlex inverted index format."""
        if not inverted_index:
            return ""
        
        # inverted_index = {"word": [position1, position2, ...], ...}
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        
        word_positions.sort(key=lambda x: x[0])
        abstract = " ".join(word for _, word in word_positions)
        
        # Limit to ~150 words
        words = abstract.split()
        if len(words) > 150:
            abstract = " ".join(words[:150])
        
        return abstract
