import json
import csv
import os
import time
import traceback
from datetime import datetime, timezone, timedelta
from typing import List, Callable, Optional, Dict

from src.core.config import Config
from src.core.models import Paper, ProjectIdea
from src.core.fetchers.arxiv_fetcher import ArxivFetcher
from src.core.fetchers.openalex_fetcher import OpenAlexFetcher
from src.core.fetchers.semanticscholar_fetcher import SemanticScholarFetcher
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
        self.llm_client = LLMClient(emit_fn=self._emit)
        
        # Initialize multi-source fetchers
        self.fetchers = [
            ("arXiv", ArxivFetcher(
                start_date=Config.START_DATE, 
                end_date=Config.END_DATE, 
                emit_fn=self._emit
            )),
            ("OpenAlex", OpenAlexFetcher(
                start_date=Config.START_DATE,
                end_date=Config.END_DATE,
                emit_fn=self._emit
            )),
            ("Semantic Scholar", SemanticScholarFetcher(
                start_date=Config.START_DATE,
                end_date=Config.END_DATE,
                emit_fn=self._emit
            )),
        ]
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
        ]
        with open(Config.OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL, extrasaction="ignore")
            writer.writeheader()
            for idea in ideas:
                writer.writerow(idea.to_dict())
                
        self._emit("csv_done", path=Config.OUTPUT_CSV, msg=f"CSV written: {len(ideas)} ideas")

    def run_pipeline(self):
        """Menjalankan seluruh pipeline eksekusi."""
        
        # Kosongkan progress file lama
        open(Config.PROGRESS_FILE, "w").close()

        # ─── FASE 0: Validasi LLM ───────────────────────────────────────────────
        self._emit("start", msg="ScholarScout v1.0 starting",
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

        # ─── FASE 1: Fetching (Multi-Source, Parallel per category) ────────────
        # Calculate how many papers we actually need based on desired ideas
        ideas_per_cat = Config.get_ideas_per_category()
        papers_per_cat = max(7, min(30, ideas_per_cat * 3))  # 3 papers per idea, capped 7-30
        
        self._emit("phase", phase=1, 
             msg=f"Fetching ~{papers_per_cat} papers/category for {ideas_per_cat} ideas/category...",
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
            if len(cached_for_cat) >= papers_per_cat:
                # Sort by recency, take what we need
                cached_for_cat.sort(key=lambda p: p.submitted_date, reverse=True)
                cat_papers = cached_for_cat[:papers_per_cat]
                for p in cat_papers:
                    seen_paper_titles.add(p.title.lower().strip())
                all_papers.extend(cat_papers)
                cat_counts[cat] = len(cat_papers)
                self._emit("cat_done", cat=cat, count=len(cat_papers),
                     phase=1, msg=f"{cat}: {len(cat_papers)} papers from cache (skipped fetch)")
                continue
            
            # Fetch all 3 sources in parallel (saves ~60% time per category)
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(_fetch_one_source, name, fetcher, cat): name
                    for name, fetcher in self.fetchers
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
            
            time.sleep(4)  # Delay between categories to respect arXiv rate limit

        self._emit("phase1_done", total=len(all_papers), cached=cached_total,
             msg=f"Fase 1 done: {len(all_papers)} papers fetched")

        if not all_papers:
            self._emit("fatal_error", msg="No papers fetched from any category. Check date range or network.")
            self._emit("done", papers=0, ideas=0, errors=errors,
                 msg="Pipeline aborted: no papers")
            return

        # ─── FASE 2: Analisis Tren ──────────────────────────────────────────────
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

        self._emit("phase2_done", msg=f"Fase 2 done: {len(trends)} trends analyzed")

        if not trends:
            self._emit("fatal_error", msg="No trends could be analyzed. LLM may be failing silently.")
            self._emit("done", papers=len(all_papers), ideas=0, errors=errors,
                 msg="Pipeline aborted: no trends")
            return

        # ─── FASE 3: Idea Generation ────────────────────────────────────────────
        self._emit("phase", phase=3, msg="Generating ideas via LLM...")
        ideas_per_cat = Config.get_ideas_per_category()
        
        for trend in trends:
            if len(all_ideas) >= Config.MAX_IDEAS: 
                break
            
            self._emit("gen_start", cat=trend.category, 
                 msg=f"Generating {ideas_per_cat} ideas for {trend.category}...")
            try:
                ideas = self.generator.generate(
                    trend, seen_titles, n=ideas_per_cat,
                    research_context=self.research_context,
                    language=self.language,
                    approach=self.approach,
                    goal=self.goal,
                    refine=self.refine,
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

        self._emit("phase3_done", total_ideas=len(all_ideas), msg=f"Fase 3 done: {len(all_ideas)} ideas")

        # ─── FASE 4: Menyimpan Hasil ────────────────────────────────────────────
        self._emit("phase", phase=4, msg="Writing output...")
        self.write_csv(all_ideas)

        # Snapshot file untuk ditampilkan di Dashboard
        run_timestamp = datetime.now(timezone.utc).isoformat()
        snapshot_data = {
            "run_date": Config.TODAY_STR,
            "run_timestamp": run_timestamp,
            "model": Config.LLM_MODEL,
            "approach": self.approach,
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
