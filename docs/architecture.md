# Architecture (for contributors)

## Pipeline flow

```
User clicks Run
    → /api/run (pipeline.py)
    → subprocess: run_pipeline.py
    → Orchestrator
        → Phase 1: Fetch papers (arXiv + OpenAlex + S2, parallel)
        → Phase 2: Analyze trends (LLM: keywords, gaps, saturation)
        → Phase 3: Generate ideas (LLM: academic/product/develop mode)
        → Phase 4: Write output (CSV + JSON snapshot + session history)
    → SSE stream progress to dashboard
```

## Key modules

| Module | Responsibility |
|--------|---------------|
| `orchestrator.py` | Pipeline controller, coordinates all phases |
| `analyzer.py` | Trend analysis via LLM (+ optional sensitivity check) |
| `generator.py` | Idea generation in 3 modes, chunked, with optional refinement |
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
