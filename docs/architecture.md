# Architecture (for contributors)

## Pipeline flow

```
User clicks Run
    → /api/run (pipeline.py)
    → subprocess: run_pipeline.py
    → Orchestrator
        → Fetch papers from routed sources
        → Default modes: analyze trends → synthesize gaps → generate ideas → save CSV, snapshot, and session history
        → Review mode: cluster papers → synthesize clusters → save review snapshot and session history
    → SSE stream progress to dashboard
```

## Key modules

| Module | Responsibility |
|--------|---------------|
| `orchestrator.py` | Pipeline controller, coordinates fetch, analysis, generation/review, and saving |
| `analyzer.py` | Trend analysis via LLM (+ optional sensitivity check) |
| `gap_synthesis.py` | Builds reusable gap candidates before idea generation |
| `generator.py` | Idea generation for Academic, Product, and Develop modes, with chunking and optional refinement |
| `clusterer.py` | Groups papers for Review mode |
| `synthesizer.py` | Builds Review mode literature synthesis from clusters |
| `deep_dive.py` | Detailed analysis per idea (+ optional grounding verification) |
| `novelty_checker.py` | Semantic + Jaccard similarity against existing papers |
| `llm.py` | Multi-provider LLM client with SSE parser |
| `config.py` | Configuration, feature flags, path resolution |
| `fetchers/` | Paper fetching (BaseFetcher abstract class) |

## Adding a new fetcher

1. Create `src/core/fetchers/my_fetcher.py`
2. Implement `BaseFetcher.fetch_papers(category, max_results) -> List[Paper]`
3. Register in `orchestrator.py` → `self.fetchers` list

## Adding a new route

1. Create `src/web/routes/my_route.py` with a Flask Blueprint
2. Register in `preview_server.py` → `create_app()`

## Feature flags

Centralized in `config.py`:
- `FEATURE_REFINE` — self-distillation
- `FEATURE_SENSITIVITY` — prompt sensitivity check
- `FEATURE_GROUNDING` — deep dive grounding verification
- `CACHE_EXPIRY_DAYS` — auto-expire cached papers

Overridable via env vars (`SCOUT_REFINE=1`) or `config.yaml` → `features:` section.

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -m "not integration"   # Unit tests
pytest tests/                         # All tests (needs Flask)
npm test                              # JS tests
```
