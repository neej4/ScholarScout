# Changelog

## v1.6.5 Release Notes (2026-06-21)

### Gap-first generation
- Added a new gap synthesis stage before idea generation so ScholarScout now reasons over reusable `gap_candidates`, not just paper lists
- Generated ideas can now carry `landscape_gap_summary`, `gap_type`, `anchor_papers`, `supporting_papers`, and paper coverage metadata
- Gap synthesis now supports explicit steering modes: `Balanced`, `Breakthrough-heavy`, and `Practical-first`

### Better use of fetched papers
- Added diversity guards so multiple ideas are less likely to collapse onto the same small paper cluster
- Added contributed-paper and supporting-paper metrics to snapshots and session history
- Added category-level gap diagnostics so each run records which categories produced the strongest gap coverage

### Dashboard and workflow upgrades
- Added a Gap Monitor inside Activity Center to show synthesized gap candidates per category while the pipeline is running
- Added evidence-aware gap chips to idea cards, detail modals, export output, copy output, and print/export views
- Added a lightweight coverage visual in the run summary so users can quickly see which categories produced the densest gap landscape
- Added post-run recommendations that suggest better next moves, such as narrowing categories or switching gap steering mode
- Added an `Update now` flow in the dashboard so ZIP-based users can stage a new build, keep `config.yaml` and `data/`, and launch the updated app without using Git

### Persistence and steering
- Gap steering now persists across the profile modal, quick mode, full pipeline runs, regenerate, presets, snapshots, and session restore
- Run summaries and transparency output now surface gap steering, gap candidate totals, contributed papers, and average supporting-paper depth
- Added a backward-compatible session/snapshot normalizer so older runs without gap-first metadata still restore cleanly
- Synced runtime version sources (`VERSION`, `pyproject.toml`, dashboard badge) to avoid release drift

### Testing and verification
- Added coverage for gap synthesis heuristics, gap steering prompt injection, duplicate gap-cluster filtering, and new dashboard structural hooks
- Added guard coverage for version consistency, legacy session compatibility, and updater helpers
- Core Python tests, JS tests, compile checks, and a local dashboard smoke check passed for the v1.6.5 path

## v1.6.1 Release Notes (2026-06-16)

### Dashboard workflow polish
- Added a shipped `Export All` button in the main dashboard controls for full-run Markdown export
- Added `Export Selected`, so users can pick a smaller working set instead of exporting every generated idea
- Export output now carries refinement notes, user-fit context, evidence claims, source papers, and risk flags
- Added a lightweight run summary strip so users can immediately see category spread and the latest session save timestamp

### Reusable research setup
- Added lightweight run presets for saving and re-applying favorite category, context, and personality configurations
- Added a visible preference memory summary in Settings so vote reasons start surfacing as readable steering hints
- Added `Goal Style` steering with suggested defaults from Goal and mode-aware options for Academic, Product, and Develop workflows
- Goal Style now persists through presets, session state, exports, idea cards, idea detail modal, and pipeline snapshots

### Stability and release fit
- CI now ignores integration tests explicitly instead of relying on collection-time markers
- Capability route no longer breaks ScholarScout startup when `capabilityscout` is not installed; the route degrades gracefully with a clear API error
- Stale structural tests for unfinished dashboard experiments are skipped so shipped UI and test expectations stay aligned
- Release notes and shipped scope were tightened so `v1.6.x` docs no longer overclaim unfinished dashboard shells

### Testing
- Added coverage for Goal Style defaults and prompt steering
- Core Python tests, JS tests, compile checks, and local dashboard smoke checks passed for the shipped v1.6.1 path

## v1.6.0 Release Notes (2026-06-15)

### Research-grade trust layer
- Evidence Pack on every generated idea: source papers, evidence claims, grounding score, and risk flags
- Invalid or missing paper references now surface explicitly instead of failing silently
- Deep Dive grounding verification and evidence-aware serialization are now part of the default research workflow

### Better idea quality
- Self-improvement upgraded from light text cleanup to a critique-and-rewrite loop
- Refined ideas can now explain their main weakness, why the rewritten version is stronger, where the novelty sits, and what execution risk still remains
- Refined ideas are marked directly in the dashboard and idea detail modal

### Personalized idea steering
- Added user preference steering for generation and refinement
- New personality controls: work style, scope preference, risk tolerance, output tone, and extra constraints
- Upvote/downvote now supports reason capture, so ScholarScout can learn what the user actually likes or rejects
- Ideas can now show fit-to-user summary, misalignment flags, and user fit score

### Dashboard workflow improvements
- Idea detail modal upgraded with a floating action rail for Deep Dive, Export, Copy, Bookmark, Regenerate, and feedback
- Export and copy from the modal now include refinement and user-fit context
- Session rendering remains backward-compatible with older ideas that do not yet have evidence or refinement fields

### Reliability and generation fairness
- Idea distribution across selected categories is now dynamic and fairer
- Fixed the old behavior where early categories could consume the full idea budget before later categories were reached
- Quick mode, regenerate, and full pipeline now all accept personality/profile context

### Research tooling
- Implementation discovery support is included for finding related code, tools, datasets, and packages
- Health/usage helpers, evidence helpers, and analysis utilities added to support more audit-ready output
- `config.yaml` removed from version control; `config.example.yaml` remains the source of truth for setup

### API and backend
- Added or extended support for `POST /api/implementations`, `POST /api/refine`, and `POST /api/roadmap`
- Personality-aware request flow now reaches the pipeline and idea generation routes

### Testing
- Added coverage for evidence helpers, refinement flow, personalization helpers, implementation discovery, and UI structural checks
- Core Python tests, JS tests, and compile checks passed for the shipped v1.6 ScholarScout path

## v1.6.0 (2026-05-28)

### Research-Grade Trust Layer (new)
- Evidence Pack on every idea: source papers, evidence claims, grounding score, and risk flags
- Evidence badges in the dashboard: Grounded, Partial, Needs Review
- Invalid or missing paper refs now surface as review warnings instead of disappearing silently

### Persistence & Recovery (improved)
- Browser session recovery now restores ideas together with cached Deep Dive and Implementation Scout results
- Session badge shows when current research artifacts were last saved in the browser
- Older snapshots without evidence fields remain readable

### Implementation Discovery (new)
- "Find Implementations" button on every idea card
- 10 sources: Papers With Code, GitHub, Awesome Lists, Hugging Face, PyPI, ClinicalTrials.gov, ChEMBL, UniProt, Zenodo, Kaggle
- Category-aware routing (e.g., med.* gets ClinicalTrials, chem.* gets ChEMBL)
- Results cached in sessionStorage (no re-query for same idea)
- Smart PyPI lookup with keyword-to-package mapping (60+ research terms)

### Idea Comparison View (new)
- Checkbox on each idea card for selection (max 4)
- Floating "Compare (N)" button when 2+ selected
- Side-by-side table with adaptive dimensions (only shows fields that have data)
- Works across modes (Academic + Product + Develop mixed)

### Export (new)
- Export dropdown: Obsidian (.md + YAML frontmatter), Markdown (.md), Notion (clipboard)
- New "Research Notes" export format for thesis/skripsi-style Markdown
- Includes Deep Dive content if previously fetched
- "Export All" button in comparison modal
- Adaptive — only includes sections with data

### Weekly Diff (new)
- "Diff vs current" button on each session in Recent tab
- Compares ideas (Jaccard on title tokens), source papers, categories, difficulty distribution
- Shows: new ideas, overlapping ideas, removed ideas, new papers, category changes

### Idea Refinement Chat (new)
- "Refine" button in idea detail modal opens interactive chat
- Multi-turn conversation with LLM to refine scope, methodology, assumptions
- Full idea context injected as system prompt (LLM knows the idea deeply)
- Supports all LLM providers (Gemini multi-turn, OpenAI-compatible messages)
- Chat history maintained per session

### Research Roadmap (new)
- "Roadmap" button in idea detail modal generates a zero-to-mastery knowledge graph
- Full-page card-based graph in dedicated Roadmap tab
- LLM generates 12-20 nodes across 4 tiers: Foundation → Intermediate → Advanced → Execution
- Node types: theory, method, tool, paper, experiment, milestone, goal
- Click any node to see description, resources, prerequisites, and what it unlocks
- Progress tracking: mark nodes as done, progress bar shows % complete (saved in localStorage)
- Supports multiple roadmaps (switch between up to 5)

### Security & Polish
- Server binds to 127.0.0.1 by default (SCOUT_HOST env var for LAN)
- MAX_CONTENT_LENGTH = 5MB at Flask level
- Toast warning when Quick mode has no cached papers
- ARIA labels on nav tabs, buttons, and interactive elements
- Keyboard navigation for tabs (Enter/Space)

### API
- `POST /api/implementations` — find code repos, models, datasets for an idea
- `POST /api/refine` — multi-turn chat to refine an idea with LLM
- `POST /api/roadmap` — generate knowledge graph (nodes + edges) for an idea

### Testing
- 43 new unit tests for impl_finder.py (121 total)

---

## v1.5.3 (2026-05-26)

### Review Mode (new)
- 4th mode: Literature Synthesis — clusters papers, synthesizes per cluster, cross-cutting analysis
- 6-phase pipeline: Validate → Fetch → Cluster → Synthesize → Cross-cutting → Save
- Review sessions saved to history with proper cluster rendering in Recent tab
- Context field required for Review mode

### Activity Center
- Owl Chase pixel art game (paper dots spawn one-by-one via drip-feed system)
- Live graph with hover tooltip (category/cluster name + paper count)
- LLM Chat tab (narrated conversation)
- Adaptive phase list (5 or 6 phases based on mode)
- Mini notification bar when closed

### Paper Freshness
- Papers track `_used_count` — least-used prioritized
- Auto-widens date range when all papers exhausted

### Thresholds externalized
- All similarity thresholds in `config.yaml` → `thresholds:` section
- `config.example.yaml` template for contributors

### Security
- `config.yaml` gitignored
- Prompt injection delimiters on paper abstracts
- 14 new unit tests (clusterer + synthesizer)

### Rate limits
- S2 retry reduced (skip faster)
- OpenAlex cs.IR fixed (was returning law papers)
- Inter-category delay 4s → 6s

### UX
- Custom toast notifications (no more browser alerts)
- Profile popup hidden by default
- Goal syncs immediately on card click
- Recent tab handles review sessions properly

### DevEx
- GitHub issue/PR templates
- `package-lock.json` committed
- `CONTRIBUTING.md` cleaned up

---

## v1.5.1 (2026-05-25)

### UX
- Controls bar rearranged: action buttons (Profile, Run, Quick, Clear) on the left, settings (date range, language, max ideas) on the right
- Donate link added to header (Ko-fi)
- White logo variant (`logo_purewhite.png`)

### Pipeline reliability
- Chunked generation: splits large requests into batches of 3 ideas per LLM call. If one batch fails (truncated JSON), remaining batches still succeed.
- Cache expiry: papers older than 7 days (configurable via `features.cache_expiry_days` in config.yaml) are automatically pruned from cache on next run.

### Configuration
- Feature flags centralized in `config.py`: `FEATURE_REFINE`, `FEATURE_SENSITIVITY`, `FEATURE_GROUNDING`, `CACHE_EXPIRY_DAYS`
- Overridable via `config.yaml` `features:` section or environment variables

### CI/CD
- GitHub Actions workflow added (`.github/workflows/ci.yml`)
- Python 3.10, 3.11, 3.12 matrix
- Runs pytest (unit tests) + npm test (JS tests) on every push/PR
- Node.js 22, forced Node 24 action runtime

### Bug fixes
- Deep Dive modal appearing on page refresh (CSS `display:flex` without `display:none` default)
- Structural tests expecting exact string patterns that diverged from actual code (relaxed assertions)

---

## v1.5.0 (2026-05-23)

### Grounding verification for Deep Dive
- Each Deep Dive section now compared against the inspiration paper abstract using semantic similarity (Gemini embeddings) or token overlap (Jaccard fallback)
- Badge per section: `Grounded` (green, ≥65% similarity), `Partial` (yellow, 40-65%), `Caution` (red, <40%)
- Hover badge to see exact similarity percentage
- Opt-in via Settings → Pipeline behavior → "Verify Deep Dive grounding"
- Disabled by default (adds ~5s and a few embedding API calls per Deep Dive)
- Best-effort: grounding never fails the Deep Dive request — empty dict returned if source unavailable

### API
- `POST /api/deepdive` accepts new optional field `verify_grounding: bool`
- Response includes optional `grounding` dict mapping section name to `{score, level}`

---

## v1.4.1 (2026-05-23)

### Cleanup
- Removed light theme (dark only)
- Removed `requirements-dev.txt` (dev deps available via `pip install .[dev]` from `pyproject.toml`)

---

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
