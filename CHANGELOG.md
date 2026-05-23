# Changelog

## v1.4.0 (2026-05-23)

### Three Idea Generation Modes
- **Academic mode** (existing) — research project ideas with methodology, thesis outline, key papers
- **Product mode** (new) — buildable product ideas with MVP features, tech stack, revenue model, competitors, moat
- **Develop mode** (new) — features/improvements for existing projects. Context is a hard constraint — every idea must be applicable to the user's project.
- **5 Develop skills**: Feature, Integration, Optimization, Extension, Pivot
- **Skills restructured**: `skills/ACADEMIC/` (9), `skills/PRODUCT/` (4), `skills/DEVELOP/` (5) — 18 total

### Onboarding Wizard
- 3-step setup: pick provider → test connection → choose categories
- Custom provider card (9router, LM Studio, any OpenAI-compatible endpoint)
- Skip test option (continue without successful connection)
- Setup button always visible in header for re-access
- First-time auto-trigger (localStorage-based)

### File Upload
- Drag-and-drop zone in Profile popup (.pdf, .txt, .md, .json)
- SVG icons (no emoji)
- PDF text extraction (basic, no external deps)
- Max 50KB text content
- Used in both Quick mode and full pipeline Run
- Empty file rejection with clear error message

### UI Improvements
- "Why this idea?" visible directly on idea cards (not hidden in detail popup)
- Confidence scoring in trend analysis (LLM self-rates 1-10, shown in console)
- Tooltips on difficulty chips, quality scores, novelty button
- Transparency panel after pipeline (sources, date range, papers count, disclaimer)
- Animated sprite logo during pipeline run (invert for dark mode, normal for light)
- Profile popup goals grouped: Academic / Product / Develop
- Novelty check shows method badge `(semantic)` or `(jaccard)`
- Settings: "Show confidence scores" toggle

### Architecture Refactor
- **Blueprint structure**: `preview_server.py` → 6 route modules (`pipeline`, `sessions`, `ideas`, `analysis`, `settings`, `upload`)
- **`pyproject.toml`**: project metadata, scripts, optional deps, pytest markers
- **`requirements-dev.txt`**: separated from runtime deps
- **SSE response parser**: handles JSON, pure SSE stream, and JSON+SSE hybrid (9router compatibility)
- **Base URL validation**: whitelist per provider, prevents SSRF
- **Cache-aware fetching**: skip API calls if cache has enough papers for category
- **Semantic Scholar API key**: `S2_API_KEY` env var support (10000 req/5min vs 100)
- **Progressive backoff**: S2 rate limits 15s/30s/45s instead of flat 10s
- **Token budget increased**: idea_generation 1500 → 3000 (product mode needs more)

### Novelty Checker Upgrade
- Semantic similarity via Gemini `text-embedding-004` (768-dim, cosine similarity)
- Graceful fallback to Jaccard when embedding API fails
- New thresholds: semantic (0.82/0.92), Jaccard (0.40/0.70)
- Method transparency in API response and UI

### LLM Client
- Custom provider support (no key required for local endpoints)
- `ping()` returns tuple `(bool, error_msg)` — callers get actionable error messages
- Fast ping for local endpoints (10s timeout, 1 attempt, no delay)
- Error capture via emit interception (actual error message reaches frontend)
- Base URL empty guard with clear message

### Testing
- Property-based tests (Hypothesis) for novelty checker
- Conftest fixtures updated with all required ProjectIdea fields
- `mock_llm_client.ping` returns tuple
- pytest markers: `integration`, `slow`

### Bug Fixes
- Hidden `<select id="goalSelect">` missing product/develop options → goal fell back to "any"
- Quick mode always used academic prompt regardless of goal selection
- Profile popup save broken after refactor (wrong open/close mechanism)
- Wizard "Skip" didn't persist → wizard kept reappearing
- Upload endpoint 404 until server restart (blueprint registration)
- `max_tokens` 1500 too low for product mode → truncated JSON parse error
- Empty file upload accepted silently
- Deep Dive modal accidentally refactored (reverted to original mechanism)
- Negative session index wrap-around bug
- Unused `Config.MAX_PER_BATCH` constant removed
- Unused `from src.core.config import Config` in analyzer.py removed

---

## v1.3.0 (2026-05-22)

### New features
- **Quick Mode**: Generate ideas instantly from cached papers without fetching. Ideal for hackathons and brainstorming. Falls back to LLM knowledge if cache is empty.
- **Profile popup**: Approach + Goal + Context combined into one clean card (replaces separate dropdowns and context toggle)
- **12 skills total**: Added Hackathon (4-12h sprint), Side Project (weekend build), Industry R&D (company-funded)
- **6 difficulty levels**: Undergraduate, Master's, PhD, Hackathon, Side Project, Industry
- **Citation quality filter**: Papers sorted by citation count before analysis (high-impact papers prioritized)
- **Saturation level**: Analyzer detects if field is "saturated", "growing", or "emerging"
- **Cross-pollination**: Analyzer suggests combining gaps with techniques from other fields
- **"Future work" scanning**: Analyzer explicitly looks for limitation phrases in abstracts
- **Prerequisites field**: Each idea lists 3-5 skills needed to execute
- **"Why this idea?" field**: Explains which gap is filled and why timing is right
- **Quality scoring**: LLM self-rates ideas 1-10, filters out score < 5
- **Duplicate detection**: Loads last 5 sessions to avoid repeating ideas
- **Thumbs up/down feedback**: Per-idea voting stored in localStorage
- **Deep Dive caching**: Second click loads instantly from memory
- **Regenerate button**: Generate a new idea for the same field without re-running pipeline
- **CHANGELOG.md**: Release notes file with version link in dashboard header
- **Waitress server**: Production WSGI server replaces Flask dev server (no more warning)

### Bug fixes
- Deep Dive "Key References" showing `[object Object]` — now renders as clickable links
- Deep Dive timeout too short (30s) — increased to 180s for slow LLM endpoints
- Regenerate failing because `ref_papers=[]` blocked anti-hallucination — rewritten with standalone prompt
- Settings API key input not styled (missing `input[type=password]` in CSS selector)
- `localStorageAvailable` variable conflict between bookmarks.js and inline script causing all buttons to break
- ArXiv 429 rate limiting — reduced retries, faster skip, parallel fetch compensates
- LLM timeout 60s too short for Claude Sonnet — increased to 180s
- OpenAlex returning irrelevant papers for medical categories — switched to keyword search for 40+ non-CS categories
- `quality_score` parsing crash when LLM returns string instead of int — wrapped in try/except
- Context toggle not clickable — replaced with Profile popup
- Onboarding modal removed (replaced by Profile popup on first Run)

### UI/UX improvements
- Controls bar redesigned: grouped into logical sections, more compact
- Profile popup with selectable cards (not dropdowns)
- Mobile responsive: left panel hidden on small screens, single column layout
- Dark/Light mode toggle with localStorage persistence
- Keyboard shortcuts: Ctrl+Enter = Run, Ctrl+K = search, Esc = close modal
- Notification sound when pipeline finishes or errors
- Copy to clipboard button in idea detail popup
- Per-idea PDF export (opens clean formatted page for printing)
- Tooltips on all controls
- Better error messages with actionable hints (e.g., "Go to Settings tab")
- Version link in header (click to see changelog)
- Bookmark button visibility improved (white color)
- Logo displayed without invert filter
- Favicon added (browser tab icon)
- Welcome guide on first load with feature overview and donate links

### Architecture
- Parallel multi-source fetching (ThreadPoolExecutor) — 3x faster per category
- Fast-fail on rate limits (1 retry then skip, don't block pipeline)
- Adaptive paper fetching: papers_per_cat = ideas_per_cat * 3 (proportional, not hardcoded)
- Papers sorted by citation count before sending to analyzer
- Anti-hallucination: P-number grounding system (LLM can only reference papers by number)
- Skills loaded from markdown files at runtime (community-extensible)
- Session history saved to JSON (last 20 runs)
- `stream: false` in LLM payload for compatibility with streaming endpoints

### Skills system
- Undergraduate (1 semester, laptop)
- Master's (6-12 months, cloud GPU)
- PhD (1-3 years, institutional)
- Data Scientist (Python-first, benchmarks)
- Lab Scientist (wet lab, physical experiments)
- Clinical Researcher (IRB, patient data)
- Thesis (structured for chapters)
- Publication (targeting conference paper)
- Grant Proposal (budget justification, milestones)
- Hackathon (4-12 hours, demo-able)
- Side Project (1-4 weekends, deployable)
- Industry R&D (company-funded, ROI-focused)

---

## v1.0.0 (2026-05-21)

### Initial release
- Multi-source fetching: arXiv, OpenAlex, Semantic Scholar
- LLM trend analysis and idea generation
- Research approach filter: Computational, Experimental, Clinical, Theoretical
- Novelty checking against Semantic Scholar + arXiv
- Deep dive analysis
- 80+ categories across 10 disciplines
- 6 LLM providers: Gemini, Groq, OpenRouter, OpenAI, Ollama, Custom
- Settings UI with test connection
- Bookmark system, PDF export, session history
- Search and filter ideas
- Bahasa Indonesia language support
- 100 automated tests (Python + JavaScript)
- MIT licensed
