import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import re
import time
from datetime import datetime, timezone
from typing import List, Callable, Optional

from src.core.models import Paper
from src.core.fetchers.base import BaseFetcher
from src.core.config import Config

class ArxivFetcher(BaseFetcher):
    """Fetcher khusus untuk mengambil data dari API arXiv."""
    
    ARXIV_NS = "http://www.w3.org/2005/Atom"
    
    def __init__(self, start_date: datetime, end_date: datetime, emit_fn: Optional[Callable] = None):
        self.start_date = start_date
        self.end_date = end_date
        self.emit_fn = emit_fn

    def _emit(self, event: str, **kwargs):
        """Helper untuk log progress — memanggil Orchestrator._emit."""
        if self.emit_fn:
            try:
                self.emit_fn(event, **kwargs)
            except Exception:
                pass
            
    def fetch_papers(self, category: str, max_results: int = 50) -> List[Paper]:
        """Mengambil data paper dari API arXiv menggunakan urllib (tanpa library tambahan)."""
        params = urllib.parse.urlencode({
            "search_query": f"cat:{category}",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        })
        url = f"http://export.arxiv.org/api/query?{params}"

        data = None
        for attempt in range(2):
            try:
                with urllib.request.urlopen(url, timeout=20) as resp:
                    data = resp.read()
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    if attempt == 0:
                        # First 429: wait briefly and retry once
                        wait = 8
                        self._emit("fetch_retry", cat=category, 
                             msg=f"ArXiv rate limited (429) for {category} — waiting {wait}s")
                        time.sleep(wait)
                    else:
                        # Second 429: give up (OpenAlex will cover)
                        self._emit("fetch_retry", cat=category,
                             msg=f"ArXiv still rate limited for {category} — skipping")
                        return []
                else:
                    self._emit("fetch_retry", cat=category, 
                         msg=f"ArXiv HTTP {e.code} for {category}")
                    return []
            except Exception as e:
                self._emit("fetch_retry", cat=category, 
                     msg=f"ArXiv error for {category}: {str(e)[:50]}")
                if attempt == 0:
                    time.sleep(5)
                else:
                    return []

        if data is None:
            self._emit("cat_error", cat=category, msg=f"No data received for {category}")
            return []

        try:
            root = ET.fromstring(data)
        except ET.ParseError as e:
            self._emit("cat_error", cat=category, msg=f"XML parse error for {category}: {e}")
            return []
            
        papers: List[Paper] = []
        
        for entry in root.findall(f"{{{self.ARXIV_NS}}}entry"):
            try:
                pub_el = entry.find(f"{{{self.ARXIV_NS}}}published")
                if pub_el is None: continue
                
                pub_dt = datetime.fromisoformat(pub_el.text.replace("Z", "+00:00"))
                if pub_dt < self.start_date or pub_dt > self.end_date: 
                    continue

                id_el  = entry.find(f"{{{self.ARXIV_NS}}}id")
                ttl_el = entry.find(f"{{{self.ARXIV_NS}}}title")
                abs_el = entry.find(f"{{{self.ARXIV_NS}}}summary")
                if None in (id_el, ttl_el, abs_el): 
                    continue

                arxiv_id = id_el.text.strip().split("/abs/")[-1]
                title    = re.sub(r"\s+", " ", ttl_el.text.strip())
                abstract = " ".join(re.sub(r"\s+", " ", abs_el.text.strip()).split()[:150])
                
                authors = []
                for a in entry.findall(f"{{{self.ARXIV_NS}}}author"):
                    name_el = a.find(f"{{{self.ARXIV_NS}}}name")
                    if name_el is not None:
                        authors.append(name_el.text.strip())

                paper = Paper(
                    id=arxiv_id,
                    title=title,
                    category=category,
                    authors="; ".join(authors[:5]),
                    abstract=abstract,
                    link=f"https://arxiv.org/abs/{arxiv_id}",
                    submitted_date=pub_dt.strftime("%Y-%m-%d"),
                    source="arxiv"
                )
                papers.append(paper)
                self._emit("paper_found", cat=category, msg=f"ARXIV [{category}] {title[:55]}...")
            except Exception as e:
                # Skip individual paper parse errors without crashing
                continue
            
        self._emit("cat_fetch_done", cat=category, 
             msg=f"Fetched {len(papers)} papers from {category}")
        return papers
