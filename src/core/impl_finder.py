"""
Implementation Discovery — Papers With Code + GitHub + Awesome Lists + Hugging Face + PyPI + ClinicalTrials.

Finds real code implementations, tools, and curated resource lists related to a
generated research idea. Called on-demand when user clicks "Find Implementations".

Sources:
  Phase 1:
    1. Papers With Code — exact paper → repo mapping (high confidence)
    2. GitHub Search — repos by keyword (stars, language, recency)
    3. Awesome Lists — curated community resource lists (GitHub repos with "awesome-" prefix)
  Phase 2:
    4. Hugging Face — pre-trained models + datasets (ML-heavy categories)
    5. PyPI — Python packages that solve part of the problem
    6. ClinicalTrials.gov — active/completed trials (med.* categories)

Rate limits:
  - Papers With Code: ~60 req/min (no key)
  - GitHub Search: 10 req/min (no key) / 30 req/min (with GITHUB_TOKEN)
  - Awesome Lists: shares GitHub Search quota
  - Hugging Face: ~100 req/min (no key)
  - PyPI: no documented limit
  - ClinicalTrials.gov: no documented limit

Usage:
    finder = ImplementationFinder()
    results = finder.find(idea_dict)
"""
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

from src.core.config import Config

logger = logging.getLogger(__name__)

# ─── Category → relevant implementation source routing ─────────────────────────
# All 10 sources: paperswithcode, github, awesome, huggingface, pypi,
#                 clinicaltrials, chembl, uniprot, zenodo, kaggle
IMPL_ROUTES = {
    "cs":      ["paperswithcode", "github", "huggingface", "kaggle", "awesome", "pypi"],
    "stat":    ["paperswithcode", "github", "huggingface", "kaggle", "awesome", "pypi"],
    "eess":    ["paperswithcode", "github", "huggingface", "awesome", "pypi"],
    "med":     ["paperswithcode", "github", "clinicaltrials", "huggingface", "pypi"],
    "bio":     ["paperswithcode", "github", "huggingface", "uniprot", "pypi", "awesome"],
    "q-bio":   ["paperswithcode", "github", "huggingface", "uniprot", "pypi"],
    "physics": ["paperswithcode", "github", "zenodo", "awesome", "pypi"],
    "eng":     ["github", "zenodo", "paperswithcode", "awesome", "pypi"],
    "chem":    ["paperswithcode", "github", "chembl", "awesome", "pypi"],
    "math":    ["paperswithcode", "github", "awesome", "pypi"],
    "soc":     ["github", "kaggle", "huggingface", "awesome", "pypi"],
    "earth":   ["github", "huggingface", "zenodo", "kaggle", "awesome", "pypi"],
    "agri":    ["github", "huggingface", "kaggle", "awesome", "pypi"],
}

# GitHub minimum stars filter per category prefix
_GITHUB_MIN_STARS = {
    "cs": 50,
    "stat": 50,
    "eess": 30,
    "med": 20,
    "bio": 20,
    "q-bio": 20,
    "physics": 30,
    "eng": 30,
    "chem": 20,
    "math": 30,
    "soc": 20,
    "earth": 20,
    "agri": 10,
}

# Awesome Lists minimum stars to filter noise
_AWESOME_MIN_STARS = 500


class ImplementationFinder:
    """Discovers code implementations related to a research idea.

    Queries Papers With Code, GitHub, Awesome Lists, Hugging Face, PyPI,
    and ClinicalTrials.gov. Gracefully returns partial results if any source fails.
    """

    USER_AGENT = "ScholarScout/1.6 (mailto:scholarscout@proton.me)"

    def __init__(self, github_token: Optional[str] = None):
        """
        Args:
            github_token: Optional GitHub personal access token for higher rate limits.
                          Falls back to GITHUB_TOKEN env var.
        """
        self._github_token = github_token or Config.GITHUB_TOKEN or os.environ.get("GITHUB_TOKEN", "")

    # ─── Public API ────────────────────────────────────────────────────────────

    def find(self, idea: dict) -> dict:
        """Find implementations for a given idea.

        Args:
            idea: Idea dict with at minimum 'idea_title'. Also uses:
                  'field', 'inspiration_title', 'methodology_hint',
                  'abstract', 'inspired_by'.

        Returns:
            {
                "paper_repos": [...],       # From Papers With Code
                "related_repos": [...],     # From GitHub Search
                "awesome_lists": [...],     # From Awesome Lists
                "models_datasets": [...],   # From Hugging Face
                "packages": [...],          # From PyPI
                "clinical_trials": [...],   # From ClinicalTrials.gov
                "compounds": [...],         # From ChEMBL
                "proteins": [...],          # From UniProt
                "datasets": [...],          # From Zenodo + Kaggle
                "meta": {"sources_queried": [...], "duration_ms": int}
            }
        """
        t0 = time.time()

        idea_title = idea.get("idea_title", "")
        field = idea.get("field", "")
        inspiration_title = idea.get("inspiration_title", "")
        methodology = idea.get("methodology_hint", "")
        abstract = idea.get("abstract", "")

        # Determine category prefix for routing
        cat_prefix = self._extract_category_prefix(field)
        routes = IMPL_ROUTES.get(cat_prefix, ["paperswithcode", "github", "awesome", "pypi"])

        results = {
            "paper_repos": [],
            "related_repos": [],
            "awesome_lists": [],
            "models_datasets": [],
            "packages": [],
            "clinical_trials": [],
            "compounds": [],
            "proteins": [],
            "datasets": [],
            "meta": {"sources_queried": [], "duration_ms": 0},
        }

        # Build search keywords from idea content
        keywords = self._build_keywords(idea_title, methodology, abstract)

        # ─── Source 1: Papers With Code ────────────────────────────────────
        if "paperswithcode" in routes and inspiration_title:
            try:
                repos = self._query_paperswithcode(inspiration_title)
                results["paper_repos"] = repos
                results["meta"]["sources_queried"].append("paperswithcode")
            except Exception as e:
                logger.warning(f"Papers With Code query failed: {e}")

        # ─── Source 2: GitHub Search ───────────────────────────────────────
        if "github" in routes and keywords:
            try:
                min_stars = _GITHUB_MIN_STARS.get(cat_prefix, 50)
                repos = self._query_github(keywords, min_stars=min_stars)
                results["related_repos"] = repos
                results["meta"]["sources_queried"].append("github")
            except Exception as e:
                logger.warning(f"GitHub Search query failed: {e}")

        # ─── Source 3: Awesome Lists ───────────────────────────────────────
        if "awesome" in routes and keywords:
            try:
                awesome = self._query_awesome_lists(keywords, cat_prefix)
                results["awesome_lists"] = awesome
                results["meta"]["sources_queried"].append("awesome")
            except Exception as e:
                logger.warning(f"Awesome Lists query failed: {e}")

        # ─── Source 4: Hugging Face ────────────────────────────────────────
        if "huggingface" in routes and keywords:
            try:
                models_datasets = self._query_huggingface(keywords)
                results["models_datasets"] = models_datasets
                results["meta"]["sources_queried"].append("huggingface")
            except Exception as e:
                logger.warning(f"Hugging Face query failed: {e}")

        # ─── Source 5: PyPI ────────────────────────────────────────────────
        if "pypi" in routes and keywords:
            try:
                packages = self._query_pypi(keywords)
                results["packages"] = packages
                results["meta"]["sources_queried"].append("pypi")
            except Exception as e:
                logger.warning(f"PyPI query failed: {e}")

        # ─── Source 6: ClinicalTrials.gov ──────────────────────────────────
        if "clinicaltrials" in routes and keywords:
            try:
                trials = self._query_clinicaltrials(keywords)
                results["clinical_trials"] = trials
                results["meta"]["sources_queried"].append("clinicaltrials")
            except Exception as e:
                logger.warning(f"ClinicalTrials query failed: {e}")

        # ─── Source 7: ChEMBL ──────────────────────────────────────────────
        if "chembl" in routes and keywords:
            try:
                compounds = self._query_chembl(keywords)
                results["compounds"] = compounds
                results["meta"]["sources_queried"].append("chembl")
            except Exception as e:
                logger.warning(f"ChEMBL query failed: {e}")

        # ─── Source 8: UniProt ─────────────────────────────────────────────
        if "uniprot" in routes and keywords:
            try:
                proteins = self._query_uniprot(keywords)
                results["proteins"] = proteins
                results["meta"]["sources_queried"].append("uniprot")
            except Exception as e:
                logger.warning(f"UniProt query failed: {e}")

        # ─── Source 9: Zenodo ──────────────────────────────────────────────
        if "zenodo" in routes and keywords:
            try:
                datasets = self._query_zenodo(keywords)
                results["datasets"] = datasets
                results["meta"]["sources_queried"].append("zenodo")
            except Exception as e:
                logger.warning(f"Zenodo query failed: {e}")

        # ─── Source 10: Kaggle ─────────────────────────────────────────────
        if "kaggle" in routes and keywords:
            try:
                kaggle_ds = self._query_kaggle(keywords)
                results["datasets"] = results["datasets"] + kaggle_ds
                results["meta"]["sources_queried"].append("kaggle")
            except Exception as e:
                logger.warning(f"Kaggle query failed: {e}")

        elapsed_ms = int((time.time() - t0) * 1000)
        results["meta"]["duration_ms"] = elapsed_ms
        return results

    # ─── Papers With Code ──────────────────────────────────────────────────────

    def _query_paperswithcode(self, paper_title: str) -> List[dict]:
        """Query Papers With Code for repos linked to a specific paper.

        Steps:
          1. Search paper by title → get paper_id
          2. Fetch repositories for that paper_id
        """
        # Step 1: Search for the paper
        search_url = "https://paperswithcode.com/api/v1/papers/"
        params = urllib.parse.urlencode({"title": paper_title})
        url = f"{search_url}?{params}"

        data = self._http_get_json(url)
        if not data:
            return []

        # PwC returns a paginated response with "results" list
        results_list = data.get("results", [])
        if not results_list:
            return []

        # Take the first (best) match
        paper_id = results_list[0].get("id")
        if not paper_id:
            # Try URL-based ID
            paper_url = results_list[0].get("url_abs", "")
            if paper_url:
                paper_id = paper_url.rstrip("/").split("/")[-1]
            if not paper_id:
                return []

        # Step 2: Get repositories for this paper
        repos_url = f"https://paperswithcode.com/api/v1/papers/{paper_id}/repositories/"
        repos_data = self._http_get_json(repos_url)
        if not repos_data:
            return []

        repos_list = repos_data.get("results", [])
        if not repos_list and isinstance(repos_data, list):
            repos_list = repos_data

        output = []
        for repo in repos_list[:5]:  # Max 5 repos per paper
            url = repo.get("url", "")
            if not url:
                continue
            output.append({
                "name": self._extract_repo_name(url),
                "url": url,
                "stars": repo.get("stars", 0),
                "framework": repo.get("framework", ""),
                "description": repo.get("description", ""),
                "source": "paperswithcode",
            })

        # Sort by stars descending
        output.sort(key=lambda r: r.get("stars", 0), reverse=True)
        return output

    # ─── GitHub Search ─────────────────────────────────────────────────────────

    def _query_github(self, keywords: List[str], min_stars: int = 50,
                      max_results: int = 5) -> List[dict]:
        """Search GitHub repositories by keywords.

        Filters: stars > min_stars, pushed within last year, sorted by stars.
        """
        # Build query string
        query_terms = " ".join(keywords[:4])  # Limit to 4 keywords to avoid overly specific queries
        one_year_ago = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
        q = f"{query_terms} stars:>{min_stars} pushed:>{one_year_ago}"

        params = urllib.parse.urlencode({
            "q": q,
            "sort": "stars",
            "order": "desc",
            "per_page": max_results,
        })
        url = f"https://api.github.com/search/repositories?{params}"

        data = self._http_get_json(url, use_github_auth=True)
        if not data:
            return []

        items = data.get("items", [])
        output = []
        for item in items[:max_results]:
            output.append({
                "name": item.get("full_name", ""),
                "url": item.get("html_url", ""),
                "stars": item.get("stargazers_count", 0),
                "lang": item.get("language", ""),
                "description": (item.get("description") or "")[:200],
                "pushed_at": item.get("pushed_at", ""),
                "source": "github",
            })

        return output

    # ─── Awesome Lists ─────────────────────────────────────────────────────────

    def _query_awesome_lists(self, keywords: List[str], cat_prefix: str) -> List[dict]:
        """Find relevant Awesome Lists on GitHub.

        Searches for repos with "awesome" in the name that match the idea's domain.
        Only returns repos with 500+ stars to filter noise.
        """
        # Use the most relevant keyword for awesome list search
        domain_keyword = self._get_awesome_keyword(keywords, cat_prefix)
        q = f"awesome {domain_keyword} in:name,description stars:>{_AWESOME_MIN_STARS}"

        params = urllib.parse.urlencode({
            "q": q,
            "sort": "stars",
            "order": "desc",
            "per_page": 3,
        })
        url = f"https://api.github.com/search/repositories?{params}"

        data = self._http_get_json(url, use_github_auth=True)
        if not data:
            return []

        items = data.get("items", [])
        output = []
        for item in items[:3]:
            output.append({
                "name": item.get("full_name", ""),
                "url": item.get("html_url", ""),
                "stars": item.get("stargazers_count", 0),
                "description": (item.get("description") or "")[:200],
                "source": "awesome",
            })

        return output

    # ─── Hugging Face ─────────────────────────────────────────────────────────

    def _query_huggingface(self, keywords: List[str], max_results: int = 3) -> List[dict]:
        """Search Hugging Face for pre-trained models and datasets.

        Returns a combined list of models and datasets sorted by downloads.
        """
        search_term = " ".join(keywords[:3])
        output = []

        # Query models
        params = urllib.parse.urlencode({
            "search": search_term,
            "sort": "downloads",
            "direction": "-1",
            "limit": max_results,
        })
        models_url = f"https://huggingface.co/api/models?{params}"
        models_data = self._http_get_json(models_url)

        if models_data and isinstance(models_data, list):
            for model in models_data[:max_results]:
                model_id = model.get("id", "") or model.get("modelId", "")
                if not model_id:
                    continue
                downloads = model.get("downloads", 0)
                pipeline_tag = model.get("pipeline_tag", "")
                output.append({
                    "name": model_id,
                    "type": "model",
                    "downloads": downloads,
                    "pipeline_tag": pipeline_tag,
                    "url": f"https://huggingface.co/{model_id}",
                    "source": "huggingface",
                })

        # Query datasets
        params = urllib.parse.urlencode({
            "search": search_term,
            "sort": "downloads",
            "direction": "-1",
            "limit": max_results,
        })
        datasets_url = f"https://huggingface.co/api/datasets?{params}"
        datasets_data = self._http_get_json(datasets_url)

        if datasets_data and isinstance(datasets_data, list):
            for ds in datasets_data[:max_results]:
                ds_id = ds.get("id", "")
                if not ds_id:
                    continue
                downloads = ds.get("downloads", 0)
                output.append({
                    "name": ds_id,
                    "type": "dataset",
                    "downloads": downloads,
                    "pipeline_tag": "",
                    "url": f"https://huggingface.co/datasets/{ds_id}",
                    "source": "huggingface",
                })

        # Sort combined by downloads, take top results
        output.sort(key=lambda x: x.get("downloads", 0), reverse=True)
        return output[:max_results * 2]  # Max 6 total (3 models + 3 datasets)

    # ─── PyPI ──────────────────────────────────────────────────────────────────

    def _query_pypi(self, keywords: List[str], max_results: int = 3) -> List[dict]:
        """Search PyPI for relevant Python packages.

        Uses the PyPI JSON API for exact package lookups based on keywords.
        Strategy: try the most specific compound keywords first, then individual ones.
        """
        output = []
        tried = set()

        # Build candidate package names from keywords
        candidates = self._build_pypi_candidates(keywords)

        for pkg_name in candidates:
            if len(output) >= max_results:
                break
            if pkg_name in tried:
                continue
            tried.add(pkg_name)

            url = f"https://pypi.org/pypi/{pkg_name}/json"
            data = self._http_get_json(url, retries=0, timeout=8)
            if not data:
                continue

            info = data.get("info", {})
            if not info.get("name"):
                continue

            # Skip packages with very low relevance (no summary)
            summary = info.get("summary", "") or ""
            if not summary:
                continue

            output.append({
                "name": info.get("name", pkg_name),
                "version": info.get("version", ""),
                "summary": summary[:200],
                "url": info.get("project_url", "") or info.get("package_url", "") or f"https://pypi.org/project/{pkg_name}/",
                "home_page": info.get("home_page", "") or "",
                "source": "pypi",
            })

        return output

    def _build_pypi_candidates(self, keywords: List[str]) -> List[str]:
        """Build candidate PyPI package names from keywords.

        Strategy: common ML/science packages that match keywords, plus
        hyphenated combinations of first 2-3 keywords.
        """
        # Well-known package mappings for common research terms
        _keyword_to_packages = {
            "machine": ["scikit-learn", "xgboost"],
            "learning": ["scikit-learn", "pytorch-lightning"],
            "deep": ["torch", "tensorflow"],
            "neural": ["torch", "keras"],
            "network": ["networkx", "torch"],
            "nlp": ["spacy", "nltk", "transformers"],
            "language": ["transformers", "spacy"],
            "transformer": ["transformers"],
            "vision": ["torchvision", "opencv-python"],
            "image": ["pillow", "opencv-python", "scikit-image"],
            "reinforcement": ["gymnasium", "stable-baselines3"],
            "graph": ["networkx", "torch-geometric"],
            "federated": ["flower", "pysyft"],
            "privacy": ["opacus", "diffprivlib"],
            "optimization": ["scipy", "optuna"],
            "clustering": ["scikit-learn", "hdbscan"],
            "classification": ["scikit-learn", "lightgbm"],
            "regression": ["scikit-learn", "statsmodels"],
            "time-series": ["statsmodels", "prophet"],
            "forecasting": ["prophet", "darts"],
            "anomaly": ["pyod", "alibi-detect"],
            "detection": ["ultralytics", "detectron2"],
            "segmentation": ["segmentation-models-pytorch"],
            "medical": ["monai", "medpy"],
            "bio": ["biopython", "scanpy"],
            "genomics": ["biopython", "pysam"],
            "protein": ["biopython", "biotite"],
            "drug": ["rdkit", "deepchem"],
            "molecular": ["rdkit", "deepchem"],
            "chemistry": ["rdkit", "ase"],
            "climate": ["xarray", "cartopy"],
            "geospatial": ["geopandas", "rasterio"],
            "satellite": ["rasterio", "sentinelhub"],
            "robotics": ["roboticstoolbox-python", "pybullet"],
            "simulation": ["simpy", "mesa"],
            "audio": ["librosa", "torchaudio"],
            "speech": ["speechbrain", "whisper"],
            "recommendation": ["surprise", "implicit"],
            "embedding": ["sentence-transformers", "gensim"],
            "scraping": ["scrapy", "beautifulsoup4"],
            "data": ["pandas", "polars"],
            "visualization": ["matplotlib", "plotly"],
            "statistics": ["scipy", "statsmodels"],
        }

        candidates = []
        # First: look up known packages for each keyword
        for kw in keywords[:4]:
            if kw in _keyword_to_packages:
                for pkg in _keyword_to_packages[kw]:
                    if pkg not in candidates:
                        candidates.append(pkg)

        # Second: try hyphenated keyword combinations as package names
        if len(keywords) >= 2:
            combo = f"{keywords[0]}-{keywords[1]}"
            if combo not in candidates:
                candidates.append(combo)
        if len(keywords) >= 3:
            combo = f"{keywords[0]}-{keywords[1]}-{keywords[2]}"
            if combo not in candidates:
                candidates.append(combo)

        # Third: try individual keywords as package names
        for kw in keywords[:3]:
            if kw not in candidates and len(kw) >= 4:
                candidates.append(kw)

        return candidates[:10]  # Cap at 10 lookups to stay fast

    # ─── ClinicalTrials.gov ────────────────────────────────────────────────────

    def _query_clinicaltrials(self, keywords: List[str], max_results: int = 3) -> List[dict]:
        """Search ClinicalTrials.gov for relevant active/completed trials.

        Only called for med.* categories. Uses the v2 API.
        """
        search_term = " ".join(keywords[:4])
        params = urllib.parse.urlencode({
            "query.term": search_term,
            "pageSize": max_results,
            "format": "json",
        })
        url = f"https://clinicaltrials.gov/api/v2/studies?{params}"

        data = self._http_get_json(url, timeout=10)
        if not data:
            return []

        studies = data.get("studies", [])
        output = []

        for study in studies[:max_results]:
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})

            nct_id = id_module.get("nctId", "")
            title = id_module.get("briefTitle", "") or id_module.get("officialTitle", "")
            status = status_module.get("overallStatus", "")
            phases = design_module.get("phases", [])
            phase_str = ", ".join(phases) if phases else ""

            if not nct_id or not title:
                continue

            output.append({
                "nct_id": nct_id,
                "title": title[:200],
                "status": status,
                "phase": phase_str,
                "url": f"https://clinicaltrials.gov/study/{nct_id}",
                "source": "clinicaltrials",
            })

        return output

    # ─── ChEMBL ────────────────────────────────────────────────────────────────

    def _query_chembl(self, keywords: List[str], max_results: int = 3) -> List[dict]:
        """Search ChEMBL for compounds/molecules related to the idea.

        Only called for chem.* categories. Uses the EBI ChEMBL REST API.
        """
        search_term = " ".join(keywords[:3])
        params = urllib.parse.urlencode({
            "q": search_term,
            "format": "json",
            "limit": max_results,
        })
        url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/search?{params}"

        data = self._http_get_json(url, timeout=10)
        if not data:
            return []

        molecules = data.get("molecules", [])
        output = []

        for mol in molecules[:max_results]:
            chembl_id = mol.get("molecule_chembl_id", "")
            pref_name = mol.get("pref_name", "") or ""
            mol_type = mol.get("molecule_type", "")
            max_phase = mol.get("max_phase", "")

            if not chembl_id:
                continue

            output.append({
                "chembl_id": chembl_id,
                "name": pref_name or chembl_id,
                "molecule_type": mol_type,
                "max_phase": str(max_phase) if max_phase else "",
                "url": f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/",
                "source": "chembl",
            })

        return output

    # ─── UniProt ───────────────────────────────────────────────────────────────

    def _query_uniprot(self, keywords: List[str], max_results: int = 3) -> List[dict]:
        """Search UniProt for proteins/genes related to the idea.

        Only called for bio.* and q-bio.* categories.
        """
        search_term = " ".join(keywords[:3])
        params = urllib.parse.urlencode({
            "query": search_term,
            "format": "json",
            "size": max_results,
        })
        url = f"https://rest.uniprot.org/uniprotkb/search?{params}"

        data = self._http_get_json(url, timeout=10)
        if not data:
            return []

        results_list = data.get("results", [])
        output = []

        for entry in results_list[:max_results]:
            accession = entry.get("primaryAccession", "")
            if not accession:
                continue

            # Extract protein name
            protein_desc = entry.get("proteinDescription", {})
            rec_name = protein_desc.get("recommendedName", {})
            full_name = rec_name.get("fullName", {}).get("value", "")
            if not full_name:
                # Try submittedName
                sub_names = protein_desc.get("submissionNames", [])
                if sub_names:
                    full_name = sub_names[0].get("fullName", {}).get("value", "")

            # Organism
            organism = entry.get("organism", {}).get("scientificName", "")

            # Sequence length
            seq_len = entry.get("sequence", {}).get("length", 0)

            output.append({
                "accession": accession,
                "name": full_name or accession,
                "organism": organism,
                "length": seq_len,
                "url": f"https://www.uniprot.org/uniprot/{accession}",
                "source": "uniprot",
            })

        return output

    # ─── Zenodo ────────────────────────────────────────────────────────────────

    def _query_zenodo(self, keywords: List[str], max_results: int = 3) -> List[dict]:
        """Search Zenodo for open datasets and reproducibility packages.

        Only called for physics.*, eng.*, earth.* categories.
        """
        search_term = " ".join(keywords[:4])
        params = urllib.parse.urlencode({
            "q": search_term,
            "sort": "mostrecent",
            "size": max_results,
            "type": "dataset",
        })
        url = f"https://zenodo.org/api/records?{params}"

        data = self._http_get_json(url, timeout=10)
        if not data:
            return []

        # Zenodo returns a "hits" wrapper
        hits = data.get("hits", {}).get("hits", [])
        if not hits and isinstance(data, list):
            hits = data

        output = []
        for record in hits[:max_results]:
            record_id = record.get("id", "")
            metadata = record.get("metadata", record)  # v1 vs v2 API shape
            title = metadata.get("title", "")
            doi = record.get("doi", "") or metadata.get("doi", "")
            description = (metadata.get("description", "") or "")[:150]
            # Strip HTML tags from description
            description = re.sub(r"<[^>]+>", "", description).strip()
            downloads = record.get("stats", {}).get("downloads", 0)

            if not title:
                continue

            output.append({
                "title": title[:200],
                "doi": doi,
                "description": description,
                "downloads": downloads,
                "url": f"https://zenodo.org/records/{record_id}" if record_id else "",
                "source": "zenodo",
            })

        return output

    # ─── Kaggle ────────────────────────────────────────────────────────────────

    def _query_kaggle(self, keywords: List[str], max_results: int = 3) -> List[dict]:
        """Search Kaggle for datasets.

        Requires KAGGLE_USERNAME and KAGGLE_KEY env vars for authentication.
        Returns empty list gracefully if credentials not set.
        """
        kaggle_user = Config.KAGGLE_USERNAME or os.environ.get("KAGGLE_USERNAME", "")
        kaggle_key = Config.KAGGLE_KEY or os.environ.get("KAGGLE_KEY", "")
        if not kaggle_user or not kaggle_key:
            return []  # No credentials — skip silently

        search_term = " ".join(keywords[:3])
        params = urllib.parse.urlencode({
            "search": search_term,
            "sortBy": "hottest",
            "fileSizeMax": 10737418240,  # 10GB max
        })
        url = f"https://www.kaggle.com/api/v1/datasets/list?{params}"

        # Kaggle uses HTTP Basic Auth
        import base64
        credentials = base64.b64encode(f"{kaggle_user}:{kaggle_key}".encode()).decode()
        headers = {
            "User-Agent": self.USER_AGENT,
            "Authorization": f"Basic {credentials}",
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Kaggle API failed: {e}")
            return []

        if not data or not isinstance(data, list):
            return []

        output = []
        for ds in data[:max_results]:
            ref = ds.get("ref", "")
            title = ds.get("title", "")
            subtitle = ds.get("subtitle", "") or ""
            downloads = ds.get("downloadCount", 0)
            usability = ds.get("usabilityRating", 0)

            if not ref or not title:
                continue

            output.append({
                "title": title[:200],
                "description": subtitle[:150],
                "downloads": downloads,
                "usability": round(usability, 1) if usability else 0,
                "url": f"https://www.kaggle.com/datasets/{ref}",
                "source": "kaggle",
            })

        return output

    # ─── HTTP Helpers ──────────────────────────────────────────────────────────

    def _http_get_json(self, url: str, use_github_auth: bool = False,
                       retries: int = 2, timeout: int = 12) -> Optional[dict]:
        """Make an HTTP GET request and return parsed JSON.

        Retries on transient errors (429, 5xx). Returns None on failure.
        """
        headers = {"User-Agent": self.USER_AGENT}

        if use_github_auth and self._github_token:
            headers["Authorization"] = f"token {self._github_token}"
            headers["Accept"] = "application/vnd.github.v3+json"

        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # Rate limited — wait and retry
                    wait = 5 * (attempt + 1)
                    logger.info(f"Rate limited ({url}), waiting {wait}s...")
                    time.sleep(wait)
                elif e.code == 403 and use_github_auth:
                    # GitHub secondary rate limit
                    wait = 10 * (attempt + 1)
                    logger.info(f"GitHub 403 ({url}), waiting {wait}s...")
                    time.sleep(wait)
                elif e.code >= 500:
                    time.sleep(3)
                else:
                    logger.warning(f"HTTP {e.code} for {url}")
                    return None

            except urllib.error.URLError as e:
                logger.warning(f"URL error for {url}: {e.reason}")
                time.sleep(2)

            except Exception as e:
                logger.warning(f"Request failed for {url}: {e}")
                time.sleep(2)

        return None

    # ─── Utility Methods ───────────────────────────────────────────────────────

    def _build_keywords(self, idea_title: str, methodology: str, abstract: str) -> List[str]:
        """Extract meaningful search keywords from idea content.

        Strategy: take significant words from title + methodology, skip stopwords.
        """
        stopwords = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "shall", "this", "that",
            "these", "those", "it", "its", "not", "no", "nor", "so", "if", "then",
            "than", "too", "very", "just", "about", "above", "after", "again",
            "all", "also", "am", "any", "as", "because", "before", "between",
            "both", "each", "few", "more", "most", "other", "our", "out", "own",
            "same", "some", "such", "through", "under", "until", "up", "us",
            "what", "when", "where", "which", "while", "who", "whom", "why",
            "how", "using", "based", "via", "new", "novel", "approach", "method",
            "towards", "toward", "into", "over",
        }

        # Combine title + methodology for keyword extraction
        text = f"{idea_title} {methodology}".lower()
        # Remove special characters
        text = re.sub(r"[^a-z0-9\s\-]", " ", text)
        words = text.split()

        # Filter: keep words 3+ chars, not stopwords, deduplicate preserving order
        seen = set()
        keywords = []
        for w in words:
            w = w.strip("-")
            if len(w) >= 3 and w not in stopwords and w not in seen:
                seen.add(w)
                keywords.append(w)

        # Limit to top 6 keywords (most relevant from title come first)
        return keywords[:6]

    def _get_awesome_keyword(self, keywords: List[str], cat_prefix: str) -> str:
        """Pick the best keyword for awesome list search.

        Uses category-aware mapping for common domains, falls back to first keyword.
        """
        # Category → common awesome list domain terms
        _cat_awesome_map = {
            "cs": "machine-learning",
            "stat": "machine-learning",
            "eess": "signal-processing",
            "med": "healthcare",
            "bio": "bioinformatics",
            "q-bio": "bioinformatics",
            "physics": "physics",
            "eng": "engineering",
            "chem": "chemistry",
            "math": "math",
            "soc": "social-science",
            "earth": "geoscience",
            "agri": "agriculture",
        }

        # If we have a good category mapping, use it
        if cat_prefix in _cat_awesome_map:
            return _cat_awesome_map[cat_prefix]

        # Otherwise use the first keyword
        return keywords[0] if keywords else "research"

    def _extract_category_prefix(self, field: str) -> str:
        """Extract category prefix from field string (e.g., 'cs.AI' → 'cs')."""
        if not field:
            return "cs"  # Default
        return field.split(".")[0].lower().strip()

    def _extract_repo_name(self, url: str) -> str:
        """Extract 'owner/repo' from a GitHub URL."""
        # Handle: https://github.com/owner/repo or https://github.com/owner/repo/...
        match = re.search(r"github\.com/([^/]+/[^/]+)", url)
        if match:
            return match.group(1).rstrip("/")
        return url
