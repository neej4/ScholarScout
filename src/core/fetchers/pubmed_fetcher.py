"""
PubMed Fetcher — Free, no API key required.
Accesses 36M+ biomedical papers via NCBI E-utilities.
Docs: https://www.ncbi.nlm.nih.gov/books/NBK25500/
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import time
import re
from datetime import datetime, timezone
from typing import List, Callable, Optional

from src.core.models import Paper
from src.core.fetchers.base import BaseFetcher


# Map ScholarScout categories to PubMed MeSH terms / keywords
CATEGORY_TO_PUBMED = {
    # Computer Science
    "cs.AI": "artificial intelligence",
    "cs.LG": "machine learning deep learning",
    "cs.CL": "natural language processing",
    "cs.CV": "computer vision image recognition",
    "cs.RO": "robotics",
    "cs.CR": "cybersecurity",
    "cs.NE": "neural networks",
    "cs.SE": "software engineering",
    "cs.IR": "information retrieval",
    "cs.HC": "human computer interaction",
    "cs.DB": "database bioinformatics",
    "cs.DC": "distributed computing cloud",
    # Medicine & Health (PubMed's strength)
    "med.cardio": "cardiology[MeSH] OR heart disease",
    "med.neuro": "neurology[MeSH] OR brain disorders",
    "med.onco": "oncology[MeSH] OR cancer treatment",
    "med.pharma": "pharmacology[MeSH] OR drug discovery",
    "med.public": "public health[MeSH] OR epidemiology",
    "med.surgery": "surgery[MeSH] OR surgical techniques",
    "med.radiology": "radiology[MeSH] OR medical imaging",
    "med.genetics": "genetics[MeSH] OR gene therapy",
    "med.pediatrics": "pediatrics[MeSH] OR child health",
    "med.infectious": "infectious disease[MeSH] OR pathogen",
    # Biology
    "q-bio.GN": "genomics sequencing",
    "q-bio.NC": "neuroscience brain",
    "q-bio.QM": "computational biology systems biology",
    "bio.ecology": "ecology biodiversity",
    "bio.molecular": "molecular biology gene expression",
    "bio.microbio": "microbiology microbiome",
    "bio.biotech": "biotechnology CRISPR",
    "bio.marine": "marine biology",
    # Chemistry (biomedical angle)
    "chem.organic": "organic chemistry synthesis",
    "chem.biochem": "biochemistry enzymes",
    "chem.analytical": "analytical chemistry spectroscopy",
    "chem.computational": "computational chemistry molecular",
    # Agriculture / Food
    "agri.crop": "crop science plant breeding",
    "agri.animal": "veterinary animal science",
    "agri.food": "food science nutrition",
    "agri.aquaculture": "aquaculture fisheries",
    # Earth / Environmental
    "earth.climate": "climate change health",
    "earth.sustainability": "sustainability environmental health",
}


class PubMedFetcher(BaseFetcher):
    """Fetches papers from PubMed via NCBI E-utilities (free, no key needed).
    
    Rate limit: 3 req/sec without API key, 10 req/sec with NCBI API key.
    """

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

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
        """Fetch papers from PubMed for a given category."""
        query = CATEGORY_TO_PUBMED.get(category)
        if not query:
            return []

        # Add date range filter
        date_from = self.start_date.strftime("%Y/%m/%d")
        date_to = self.end_date.strftime("%Y/%m/%d")
        full_query = f"({query}) AND (\"{date_from}\"[PDAT] : \"{date_to}\"[PDAT])"

        # Step 1: Search for PMIDs
        pmids = self._search(full_query, max_results)
        if not pmids:
            return []

        # Step 2: Fetch abstracts for those PMIDs
        papers = self._fetch_details(pmids, category)
        
        self._emit("cat_fetch_done", cat=category,
             msg=f"PubMed fetched {len(papers)} papers for {category}")
        return papers

    def _search(self, query: str, max_results: int) -> List[str]:
        """Search PubMed and return list of PMIDs."""
        params = urllib.parse.urlencode({
            "db": "pubmed",
            "term": query,
            "retmax": min(max_results, 50),
            "sort": "date",
            "retmode": "json",
        })
        url = f"{self.ESEARCH_URL}?{params}"

        for attempt in range(3):
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "ScholarScout")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())
                    return data.get("esearchresult", {}).get("idlist", [])
            except Exception as e:
                self._emit("fetch_retry", msg=f"PubMed search attempt {attempt+1}: {str(e)[:60]}")
                time.sleep(2 * (attempt + 1))
        return []

    def _fetch_details(self, pmids: List[str], category: str) -> List[Paper]:
        """Fetch title + abstract for a list of PMIDs using efetch XML."""
        params = urllib.parse.urlencode({
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        })
        url = f"{self.EFETCH_URL}?{params}"

        for attempt in range(3):
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "ScholarScout")
                with urllib.request.urlopen(req, timeout=20) as resp:
                    xml_content = resp.read().decode("utf-8", errors="ignore")
                    return self._parse_xml(xml_content, category)
            except Exception as e:
                self._emit("fetch_retry", msg=f"PubMed fetch attempt {attempt+1}: {str(e)[:60]}")
                time.sleep(2 * (attempt + 1))
        return []

    def _parse_xml(self, xml: str, category: str) -> List[Paper]:
        """Parse PubMed XML response into Paper objects."""
        papers: List[Paper] = []
        
        # Split into individual articles
        articles = re.findall(r"<PubmedArticle>(.*?)</PubmedArticle>", xml, re.DOTALL)
        
        for article in articles:
            try:
                paper = self._parse_article(article, category)
                if paper:
                    papers.append(paper)
            except Exception:
                continue
        
        return papers

    def _parse_article(self, article_xml: str, category: str) -> Optional[Paper]:
        """Parse a single PubMed article XML block."""
        # PMID
        pmid_match = re.search(r"<PMID[^>]*>(\d+)</PMID>", article_xml)
        if not pmid_match:
            return None
        pmid = pmid_match.group(1)

        # Title
        title_match = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", article_xml, re.DOTALL)
        if not title_match:
            return None
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
        if not title:
            return None

        # Abstract
        abstract = ""
        abstract_match = re.search(r"<Abstract>(.*?)</Abstract>", article_xml, re.DOTALL)
        if abstract_match:
            # Combine all AbstractText elements
            texts = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", abstract_match.group(1), re.DOTALL)
            abstract = " ".join(re.sub(r"<[^>]+>", "", t).strip() for t in texts)
        if not abstract:
            abstract = "(No abstract available)"

        # Authors (first 5)
        authors = []
        author_blocks = re.findall(r"<Author[^>]*>(.*?)</Author>", article_xml, re.DOTALL)
        for ab in author_blocks[:5]:
            last = re.search(r"<LastName>(.*?)</LastName>", ab)
            first = re.search(r"<ForeName>(.*?)</ForeName>", ab)
            if last:
                name = last.group(1)
                if first:
                    name = f"{first.group(1)} {name}"
                authors.append(name)

        # Publication date
        pub_date = ""
        year_match = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>.*?(?:<Month>(\w+)</Month>)?.*?(?:<Day>(\d+)</Day>)?", article_xml, re.DOTALL)
        if year_match:
            year = year_match.group(1)
            month = year_match.group(2) or "01"
            day = year_match.group(3) or "01"
            # Convert month name to number if needed
            try:
                month_num = time.strptime(month, "%b").tm_mon if not month.isdigit() else int(month)
            except Exception:
                month_num = 1
            pub_date = f"{year}-{month_num:02d}-{int(day):02d}"

        link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

        return Paper(
            id=f"PMID:{pmid}",
            title=title[:300],
            category=category,
            authors="; ".join(authors),
            abstract=abstract[:500],
            link=link,
            submitted_date=pub_date,
            source="pubmed",
            citations=0,  # PubMed doesn't provide citation count in efetch
        )
