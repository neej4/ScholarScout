import json
import csv
import os
import time
import random
import math
import traceback
from datetime import datetime, timezone, timedelta
from typing import List, Callable, Optional, Dict

from src.core.config import Config
from src.core.models import Paper, ProjectIdea, ReviewCluster, ReviewOutput
from src.core.fetchers.arxiv_fetcher import ArxivFetcher
from src.core.fetchers.openalex_fetcher import OpenAlexFetcher
from src.core.fetchers.semanticscholar_fetcher import SemanticScholarFetcher
from src.core.fetchers.pubmed_fetcher import PubMedFetcher
from src.core.fetchers.crossref_fetcher import CrossrefFetcher
from src.core.fetchers.doaj_fetcher import DOAJFetcher
from src.core.fetchers.scopus_fetcher import ScopusFetcher
from src.core.fetchers.dblp_fetcher import DBLPFetcher
from src.core.llm import LLMClient
from src.core.analyzer import TrendAnalyzer
from src.core.generator import IdeaGenerator

class Orchestrator:
    """
    Kelas utama (Orchestrator) yang menghubungkan semua komponen: 
    Fetcher -> Analyzer -> Generator -> Output.
    """

    def __init__(self, emit_fn: Optional[Callable] = None,
                 research_context: str = '', language: str = 'en', approach: str = 'any'):
        self.emit_fn = emit_fn
        self.research_context = research_context or os.environ.get('SCOUT_CONTEXT', '')
        self.language = language or os.environ.get('SCOUT_LANGUAGE', 'en')
        self.approach = approach or os.environ.get('SCOUT_APPROACH', 'any')
        self.goal = os.environ.get('SCOUT_GOAL', 'any')
        self.refine = os.environ.get('SCOUT_REFINE', '0') == '1'
        self.sensitivity = os.environ.get('SCOUT_SENSITIVITY', '0') == '1'
        self.force_refresh = os.environ.get('SCOUT_FORCE_REFRESH', '0') == '1'
        self.user_profile = os.environ.get('SCOUT_USER_PROFILE', '')
        self.feedback_summary = os.environ.get('SCOUT_FEEDBACK_SUMMARY', '')
        self.llm_client = LLMClient(emit_fn=self._emit)
        
        # Initialize multi-source fetchers (all available)
        _common = dict(start_date=Config.START_DATE, end_date=Config.END_DATE, emit_fn=self._emit)
        self.all_fetchers = {
            "arXiv":    ArxivFetcher(**_common),
            "OpenAlex": OpenAlexFetcher(**_common),
            "S2":       SemanticScholarFetcher(**_common),
            "PubMed":   PubMedFetcher(**_common),
            "Crossref": CrossrefFetcher(**_common),
            "DOAJ":     DOAJFetcher(**_common),
            "Scopus":   ScopusFetcher(**_common),
            "DBLP":     DBLPFetcher(**_common),
        }
        
        # Source routing: which sources to use per category prefix
        # Each category gets 3-4 most relevant sources (avoids noise + saves rate limits)
        self._source_routes = {
            "cs":      ["arXiv", "S2", "OpenAlex", "DBLP"],
            "stat":    ["arXiv", "S2", "OpenAlex", "DBLP"],
            "eess":    ["arXiv", "S2", "OpenAlex", "DBLP"],
            "med":     ["PubMed", "S2", "Crossref", "Scopus"],
            "q-bio":   ["PubMed", "S2", "OpenAlex", "Crossref"],
            "bio":     ["PubMed", "OpenAlex", "Crossref", "DOAJ"],
            "physics": ["arXiv", "S2", "OpenAlex", "Crossref"],
            "eng":     ["Crossref", "OpenAlex", "S2", "Scopus"],
            "chem":    ["Crossref", "OpenAlex", "S2", "PubMed"],
            "math":    ["arXiv", "S2", "OpenAlex", "Crossref"],
            "soc":     ["Crossref", "OpenAlex", "DOAJ", "S2"],
            "earth":   ["Crossref", "OpenAlex", "DOAJ", "S2"],
            "agri":    ["Crossref", "OpenAlex", "DOAJ", "PubMed"],
        }
        # Fallback: if category prefix not in routes, use these universal sources
        self._default_sources = ["OpenAlex", "S2", "Crossref"]
        self.analyzer = TrendAnalyzer(self.llm_client)
        self.generator = IdeaGenerator(self.llm_client)
        
    def _emit(self, event: str, **kwargs):
        """Helper untuk mencatat dan memancarkan log event."""
        obj = {"event": event, "ts": datetime.now(timezone.utc).isoformat(), **kwargs}
        
        try:
            with open(Config.PROGRESS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass
            
        if self.emit_fn:
            try:
                self.emit_fn(obj)
            except Exception:
                pass
            
        msg = kwargs.get("msg", "")
        if msg:
            print(f"  [{event}] {msg}", flush=True)

    def load_cache(self) -> Dict[str, dict]:
        try:
            with open(Config.CACHE_FILE, encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            return {}

        # Expire papers older than CACHE_EXPIRY_DAYS
        expiry_days = Config.CACHE_EXPIRY_DAYS
        if expiry_days > 0:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=expiry_days)).strftime("%Y-%m-%d")
            before = len(cache)
            cache = {k: v for k, v in cache.items() if v.get("submitted", "9999") >= cutoff}
            expired = before - len(cache)
            if expired > 0:
                self._emit("cache_expiry", msg=f"Expired {expired} papers older than {expiry_days} days")
        return cache

    def save_cache(self, cache: Dict[str, dict]):
        try:
            with open(Config.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False)
        except Exception as e:
            self._emit("cache_error", msg=f"Failed to save cache: {e}")

    def write_csv(self, ideas: List[ProjectIdea]):
        fields = [
            "idea_title", "field", "difficulty", "cost_estimate", "cost_note",
            "why_hard", "resources_needed", "abstract", "inspired_by",
            "inspiration_title", "inspiration_link", "generated_date",
            "grounding_score", "risk_flags", "source_papers", "evidence_claims",
            "critique_summary", "refinement_summary", "novelty_claim",
            "feasibility_warning", "fit_to_user_summary", "misalignment_flags",
            "user_fit_score", "refined",
        ]
        with open(Config.OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL, extrasaction="ignore")
            writer.writeheader()
            for idea in ideas:
                writer.writerow(idea.to_dict())
                
        self._emit("csv_done", path=Config.OUTPUT_CSV, msg=f"CSV written: {len(ideas)} ideas")

    def run_pipeline(self):
        """Run the full pipeline."""
        
        # Clear old progress file
        open(Config.PROGRESS_FILE, "w").close()

        # ─── PHASE 0: Validate LLM ───────────────────────────────────────────────
        self._emit("start", msg="ScholarScout starting",
             total_cats=len(Config.CATEGORIES), 
             date_range=f"{Config.START_DATE.strftime('%Y-%m-%d')} -> {Config.TODAY_STR}",
             model=Config.OPENROUTER_MODEL)

        try:
            ping_ok, ping_err = self.llm_client.ping()
        except Exception as e:
            self._emit("fatal_error", msg=f"Ping crashed: {e}")
            ping_ok = False
            ping_err = str(e)

        if not ping_ok:
            err_detail = ping_err if ping_err else "Check config.yaml (api_key, base_url, model)."
            self._emit("fatal_error", msg=f"LLM unreachable. {err_detail}")
            self._emit("done", papers=0, ideas=0, errors=["LLM ping failed"],
                 msg="Pipeline aborted: LLM unreachable")
            return

        self._emit("phase", phase=0, msg="LLM validated OK")

        all_papers: List[Paper] = []
        all_ideas: List[ProjectIdea] = []
        seen_titles = set()
        errors = []
        cat_counts = {}
        
        # Load previous session titles for duplicate detection
        history_file = os.path.join(Config.DATA_DIR, "session_history.json")
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            for session in history[:5]:  # Check last 5 sessions
                for idea in session.get("ideas", []):
                    if idea.get("idea_title"):
                        seen_titles.add(idea["idea_title"])
            if seen_titles:
                self._emit("dedup", msg=f"Loaded {len(seen_titles)} previous titles for deduplication")
        except:
            pass
        
        cache = self.load_cache()
        cached_total = len(cache)

        # ─── PHASE 1: Fetching (Multi-Source, Parallel per category) ────────────
        # Calculate how many papers we actually need based on desired ideas
        base_ideas_per_cat = Config.get_ideas_per_category()
        papers_per_cat = max(7, min(30, base_ideas_per_cat * 3))  # 3 papers per idea, capped 7-30
        
        self._emit("phase", phase=1, 
             msg=f"Fetching ~{papers_per_cat} papers/category for ~{base_ideas_per_cat} ideas/category...",
             date_from=Config.START_DATE.strftime("%Y-%m-%d"), 
             date_to=Config.END_DATE.strftime("%Y-%m-%d"),
             cached=cached_total)
        
        seen_paper_titles = set()  # Deduplicate across sources
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Each source gets a share of the papers needed (split across 3 sources)
        per_source_limit = max(5, (papers_per_cat // 2) + 3)  # Fetch slightly more to account for dedup
        
        def _fetch_one_source(source_name, fetcher, cat):
            """Fetch from one source — returns (source_name, papers) or (source_name, [])."""
            try:
                return (source_name, fetcher.fetch_papers(category=cat, max_results=per_source_limit))
            except Exception as e:
                return (source_name, [])
             
        for cat in Config.CATEGORIES:
            self._emit("cat_start", cat=cat, phase=1, msg=f"Fetching {cat} (parallel)")
            cat_papers = []
            _cat_exhausted = False  # Track if this category's cache is exhausted

            # Cache-aware: if we already have enough cached papers for this category,
            # use them instead of fetching (avoids rate limits on repeated runs)
            cached_for_cat = []
            for v in cache.values():
                if v.get("category") == cat:
                    cached_for_cat.append(Paper(
                        id=v.get("id", ""),
                        title=v.get("title", ""),
                        category=v.get("category", cat),
                        authors=v.get("authors", ""),
                        abstract=v.get("abstract", ""),
                        link=v.get("link", ""),
                        submitted_date=v.get("submitted", ""),
                        source=v.get("source", "cache"),
                        citations=v.get("citations", 0),
                    ))
            if len(cached_for_cat) >= papers_per_cat and not self.force_refresh:
                # ── Paper freshness: prioritize least-used papers ──
                # Each paper tracks _used_count in cache. Sort by usage (ascending)
                # so papers that haven't been used for idea generation get picked first.
                for p in cached_for_cat:
                    p._used_count = cache.get(p.id, {}).get("_used_count", 0)
                cached_for_cat.sort(key=lambda p: p._used_count)
                
                # Check if ALL papers are exhausted (used 2+ times)
                min_usage = cached_for_cat[0]._used_count if cached_for_cat else 0
                all_exhausted = min_usage >= 2
                
                if all_exhausted:
                    # Notify user that all papers have been used — will try wider date range
                    _cat_exhausted = True
                    self._emit("papers_exhausted", cat=cat,
                         total_cached=len(cached_for_cat),
                         min_usage=min_usage,
                         msg=f"{cat}: All {len(cached_for_cat)} cached papers used {min_usage}+ times. Fetching fresh papers...")
                    # Don't use cache — fall through to fetch with wider date range
                    pass
                else:
                    # Pick least-used papers, shuffle within same usage tier for variety
                    # Group by usage count, shuffle each group, then flatten
                    usage_groups = {}
                    for p in cached_for_cat:
                        usage_groups.setdefault(p._used_count, []).append(p)
                    cat_papers = []
                    for usage_count in sorted(usage_groups.keys()):
                        group = usage_groups[usage_count]
                        random.shuffle(group)
                        cat_papers.extend(group)
                        if len(cat_papers) >= papers_per_cat:
                            break
                    cat_papers = cat_papers[:papers_per_cat]
                    
                    # Increment usage count for selected papers
                    for p in cat_papers:
                        if p.id in cache:
                            cache[p.id]["_used_count"] = cache[p.id].get("_used_count", 0) + 1
                    self.save_cache(cache)
                    
                    for p in cat_papers:
                        seen_paper_titles.add(p.title.lower().strip())
                    all_papers.extend(cat_papers)
                    cat_counts[cat] = len(cat_papers)
                    
                    unused_count = sum(1 for p in cat_papers if getattr(p, '_used_count', 0) == 0)
                    self._emit("cat_done", cat=cat, count=len(cat_papers),
                         phase=1, fresh=unused_count,
                         msg=f"{cat}: {len(cat_papers)} papers from cache ({unused_count} fresh, skipped fetch)")
                    continue
            
            # Determine which sources to use for this category (source routing)
            cat_prefix = cat.split(".")[0] if "." in cat else cat
            source_names = self._source_routes.get(cat_prefix, self._default_sources)
            cat_fetchers = [(name, self.all_fetchers[name]) for name in source_names if name in self.all_fetchers]
            
            # If papers were exhausted, widen date range for fresh fetch
            if _cat_exhausted:
                wider_start = Config.START_DATE - timedelta(days=14)
                for _, fetcher in cat_fetchers:
                    fetcher.start_date = wider_start
                self._emit("date_widen", cat=cat,
                     new_start=wider_start.strftime("%Y-%m-%d"),
                     msg=f"{cat}: Widening date range to {wider_start.strftime('%Y-%m-%d')} for fresh papers")
            
            # Fetch selected sources in parallel
            with ThreadPoolExecutor(max_workers=len(cat_fetchers)) as executor:
                futures = {
                    executor.submit(_fetch_one_source, name, fetcher, cat): name
                    for name, fetcher in cat_fetchers
                }
                for future in as_completed(futures):
                    source_name, papers = future.result()
                    for p in papers:
                        title_key = p.title.lower().strip()
                        if title_key not in seen_paper_titles:
                            seen_paper_titles.add(title_key)
                            cat_papers.append(p)
                            if p.id not in cache:
                                cache[p.id] = p.to_dict()
                            # Mark as used (first use)
                            cache[p.id]["_used_count"] = cache[p.id].get("_used_count", 0) + 1
            
            all_papers.extend(cat_papers)
            cat_counts[cat] = len(cat_papers)
            self.save_cache(cache)
            
            if cat_papers:
                sources_used = set(p.source for p in cat_papers)
                self._emit("cat_done", cat=cat, count=len(cat_papers),
                     phase=1, msg=f"{cat}: {len(cat_papers)} papers from {', '.join(sources_used)}")
            else:
                errors.append(f"No papers: {cat}")
                self._emit("cat_skip", cat=cat, phase=1, msg=f"{cat}: no papers found in date range")
            
            time.sleep(6)  # Delay between categories to respect arXiv rate limit

        self._emit("phase1_done", total=len(all_papers), cached=cached_total,
             msg=f"Phase 1 done: {len(all_papers)} papers fetched")

        if not all_papers:
            self._emit("fatal_error", msg="No papers fetched from any category. Check date range or network.")
            self._emit("done", papers=0, ideas=0, errors=errors,
                 msg="Pipeline aborted: no papers")
            return

        # ─── PHASE 2: Trend Analysis ──────────────────────────────────────────────
        self._emit("phase", phase=2, msg="Analysing trends via LLM...")
        cat_papers = {}
        for p in all_papers:
            cat_papers.setdefault(p.category, []).append(p)

        self._emit("phase2_info", msg=f"Analyzing {len(cat_papers)} categories: {list(cat_papers.keys())}")

        trends = []
        for cat, papers_in_cat in cat_papers.items():
            self._emit("cat_start", cat=cat, phase=2, msg=f"Analysing {cat} ({min(len(papers_in_cat), papers_per_cat)} papers)")
            try:
                # Sort by citations (high-impact papers first) then take top N
                sorted_papers = sorted(papers_in_cat, key=lambda p: p.citations, reverse=True)
                analysis_batch = sorted_papers[:papers_per_cat]
                trend = self.analyzer.analyze(papers=analysis_batch, category=cat, sensitivity=self.sensitivity)
                trends.append(trend)
                kw_preview = trend.top_keywords[:3] if trend.top_keywords else ["(none)"]
                self._emit("trend", cat=cat, keywords=kw_preview,
                     confidence=trend.confidence,
                     msg=f"{cat}: keywords={kw_preview} (confidence: {trend.confidence}/10)")
            except Exception as e:
                self._emit("trend_error", cat=cat, msg=f"Trend analysis failed {cat}: {e}")
                errors.append(f"Trend error: {cat}: {e}")
                traceback.print_exc()
            time.sleep(4)

        self._emit("phase2_done", msg=f"Phase 2 done: {len(trends)} trends analyzed")

        if not trends:
            self._emit("fatal_error", msg="No trends could be analyzed. LLM may be failing silently.")
            self._emit("done", papers=len(all_papers), ideas=0, errors=errors,
                 msg="Pipeline aborted: no trends")
            return

        # ─── PHASE 3: Idea Generation ────────────────────────────────────────────
        self._emit("phase", phase=3, msg="Generating ideas via LLM...")
        
        for idx, trend in enumerate(trends):
            if len(all_ideas) >= Config.MAX_IDEAS: 
                break
            remaining_slots = Config.MAX_IDEAS - len(all_ideas)
            categories_left = max(1, len(trends) - idx)
            ideas_for_cat = max(1, math.ceil(remaining_slots / categories_left))
            
            self._emit("gen_start", cat=trend.category, 
                 msg=f"Generating {ideas_for_cat} ideas for {trend.category}...")
            try:
                ideas = self.generator.generate(
                    trend, seen_titles, n=ideas_for_cat,
                    research_context=self.research_context,
                    language=self.language,
                    approach=self.approach,
                    goal=self.goal,
                    refine=self.refine,
                    user_profile=self.user_profile,
                    feedback_summary=self.feedback_summary,
                )
            except Exception as e:
                self._emit("gen_error", cat=trend.category, msg=f"Generation failed {trend.category}: {e}")
                errors.append(f"Gen error: {trend.category}: {e}")
                traceback.print_exc()
                continue
            
            # Batasi jumlah ide agar tidak melebihi MAX_IDEAS
            available_slots = Config.MAX_IDEAS - len(all_ideas)
            ideas = ideas[:available_slots]
            
            all_ideas.extend(ideas)
            self._emit("cat_ideas", cat=trend.category, count=len(ideas),
                 total=len(all_ideas), msg=f"{trend.category}: +{len(ideas)} ideas (total: {len(all_ideas)})")
            time.sleep(6)

        self._emit("phase3_done", total_ideas=len(all_ideas), msg=f"Phase 3 done: {len(all_ideas)} ideas")

        # ─── PHASE 4: Save Results ────────────────────────────────────────────
        self._emit("phase", phase=4, msg="Writing output...")
        self.write_csv(all_ideas)

        # Snapshot file untuk ditampilkan di Dashboard
        run_timestamp = datetime.now(timezone.utc).isoformat()
        snapshot_data = {
            "run_date": Config.TODAY_STR,
            "run_timestamp": run_timestamp,
            "model": Config.LLM_MODEL,
            "approach": self.approach,
            "user_profile": self.user_profile,
            "feedback_summary": self.feedback_summary,
            "categories": list(cat_counts.keys()),
            "papers_total": len(all_papers), 
            "ideas_total": len(all_ideas),
            "cat_counts": cat_counts, 
            "ideas": [idea.to_dict() for idea in all_ideas],
        }
        with open(Config.SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, indent=2, ensure_ascii=False)
        
        # Save to session history (append, not overwrite)
        history_file = os.path.join(Config.DATA_DIR, "session_history.json")
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []
        
        history.insert(0, {
            "timestamp": run_timestamp,
            "date": Config.TODAY_STR,
            "categories": list(cat_counts.keys()),
            "approach": self.approach,
            "user_profile": self.user_profile,
            "papers_total": len(all_papers),
            "ideas_total": len(all_ideas),
            "ideas": [idea.to_dict() for idea in all_ideas],
        })
        # Keep last 20 sessions
        history = history[:20]
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        diff_counts = {}
        for idea in all_ideas:
            diff_counts[idea.difficulty] = diff_counts.get(idea.difficulty, 0) + 1

        top_cat = max(cat_counts, key=cat_counts.get) if cat_counts else ""
        self._emit("done",
             papers=len(all_papers), ideas=len(all_ideas),
             top_cat=top_cat,
             difficulty_breakdown=diff_counts,
             errors=errors,
             msg=f"Pipeline complete: {len(all_papers)} papers, {len(all_ideas)} ideas")

    def run_review_pipeline(self, topic: str = ''):
        """
        Run the Review Mode pipeline: fetch → cluster → synthesize → cross-cutting map.
        Output is a ReviewOutput (literature map), not ideas.
        """
        from src.core.clusterer import PaperClusterer
        from src.core.synthesizer import LiteratureSynthesizer

        open(Config.PROGRESS_FILE, "w").close()
        topic = topic or self.research_context or 'general'

        # ─── PHASE 0: Validate LLM ───────────────────────────────────────────
        self._emit("start", msg=f"Review Mode: '{topic}'", model=Config.LLM_MODEL)
        try:
            ping_ok, ping_err = self.llm_client.ping()
        except Exception as e:
            ping_ok, ping_err = False, str(e)

        if not ping_ok:
            self._emit("fatal_error", msg=f"LLM unreachable. {ping_err}")
            self._emit("done", papers=0, ideas=0, errors=["LLM ping failed"], msg="Review aborted")
            return

        self._emit("phase", phase=0, msg="LLM validated OK")

        # ─── PHASE 1: Fetch papers by topic ──────────────────────────────────
        self._emit("phase", phase=1, msg=f"Fetching papers for topic: {topic}")
        all_papers: List[Paper] = []
        seen_titles = set()
        errors = []

        from concurrent.futures import ThreadPoolExecutor, as_completed

        # For review mode, fetch from ALL sources using topic as keyword
        def _fetch_topic(name, fetcher):
            try:
                # Use first category or 'cs.AI' as fallback for API compatibility
                cat = Config.CATEGORIES[0] if Config.CATEGORIES else 'cs.AI'
                return (name, fetcher.fetch_papers(category=cat, max_results=15))
            except Exception:
                return (name, [])

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(_fetch_topic, name, fetcher): name
                for name, fetcher in list(self.all_fetchers.items())[:5]
            }
            for future in as_completed(futures):
                source_name, papers = future.result()
                for p in papers:
                    key = p.title.lower().strip()
                    if key not in seen_titles:
                        seen_titles.add(key)
                        all_papers.append(p)
                        self._emit("paper_found", source=p.source, cat=p.category,
                             msg=f"[{source_name}] {p.title[:50]}...")

        self._emit("phase1_done", total=len(all_papers),
             msg=f"Phase 1 done: {len(all_papers)} papers fetched")

        if len(all_papers) < 5:
            self._emit("fatal_error", msg="Not enough papers for review (need at least 5)")
            self._emit("done", papers=len(all_papers), ideas=0, errors=errors, msg="Review aborted")
            return

        # ─── PHASE 2: Cluster papers ─────────────────────────────────────────
        self._emit("phase", phase=2, msg="Clustering papers into themes...")
        clusterer = PaperClusterer(llm_client=self.llm_client)
        # Cluster count = MAX_IDEAS (user wants N clusters, papers distributed freely)
        n_clusters = min(Config.MAX_IDEAS, max(3, len(all_papers) // 3))
        raw_clusters = clusterer.cluster(all_papers, n_clusters=n_clusters)

        self._emit("phase2_done", msg=f"Phase 2 done: {len(raw_clusters)} clusters formed")
        for c in raw_clusters:
            self._emit("cluster_form", cluster_name=c["name"], count=len(c["papers"]),
                 msg=f"Cluster: {c['name']} ({len(c['papers'])} papers)")

        # ─── PHASE 3: Synthesize per cluster ──────────────────────────────────
        self._emit("phase", phase=3, msg="Synthesizing literature per cluster...")
        synthesizer = LiteratureSynthesizer(self.llm_client)
        cluster_summaries = []

        for c in raw_clusters:
            self._emit("gen_start", cat=c["name"], msg=f"Synthesizing: {c['name']}...")
            summary = synthesizer.synthesize_cluster(c["name"], c["papers"])
            cluster_summaries.append(summary)
            self._emit("cat_ideas", cat=c["name"], total=len(cluster_summaries),
                 msg=f"Synthesized: {c['name']}")
            time.sleep(3)

        # ─── PHASE 4: Cross-cutting analysis ──────────────────────────────────
        self._emit("phase", phase=4, msg="Building cross-cutting analysis...")
        cross_cutting = synthesizer.cross_cutting_analysis(cluster_summaries, all_papers)

        # ─── PHASE 5: Save results ───────────────────────────────────────────
        self._emit("phase", phase=5, msg="Saving review output...")

        # Build ReviewOutput
        review_clusters = [
            ReviewCluster(
                name=s["name"],
                paper_count=s["paper_count"],
                methodology_summary=s["methodology_summary"],
                key_findings=s["key_findings"],
                gaps=s["gaps"],
                keywords=raw_clusters[i].get("keywords", []) if i < len(raw_clusters) else [],
                papers=s["papers"],
            )
            for i, s in enumerate(cluster_summaries)
        ]

        review_output = ReviewOutput(
            topic=topic,
            paper_count=len(all_papers),
            clusters=review_clusters,
            timeline=cross_cutting.get("timeline", ""),
            debates=cross_cutting.get("debates", ""),
            open_questions=cross_cutting.get("open_questions", []),
            reading_list=cross_cutting.get("reading_list", []),
        )

        # Save snapshot
        run_timestamp = datetime.now(timezone.utc).isoformat()
        snapshot_data = {
            "run_date": Config.TODAY_STR,
            "run_timestamp": run_timestamp,
            "mode": "review",
            "topic": topic,
            "model": Config.LLM_MODEL,
            "papers_total": len(all_papers),
            "clusters_total": len(review_clusters),
            "review": review_output.to_dict(),
        }
        with open(Config.SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, indent=2, ensure_ascii=False)

        # Save to session history (same as default pipeline)
        history_file = os.path.join(Config.DATA_DIR, "session_history.json")
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

        history.insert(0, {
            "timestamp": run_timestamp,
            "date": Config.TODAY_STR,
            "mode": "review",
            "topic": topic,
            "categories": list(set(p.category for p in all_papers)),
            "approach": "review",
            "papers_total": len(all_papers),
            "ideas_total": len(review_clusters),
            "clusters": [{"name": c.name, "paper_count": c.paper_count, "key_findings": c.key_findings, "gaps": c.gaps} for c in review_clusters],
        })
        history = history[:20]
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        self._emit("done",
             papers=len(all_papers), ideas=len(review_clusters),
             mode="review",
             msg=f"Review complete: {len(all_papers)} papers, {len(review_clusters)} clusters")
