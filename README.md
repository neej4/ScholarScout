<p align="center">
  <img src="docs/banner.png" alt="ScholarScout" width="600">
</p>

<h3 align="center">Papers in. Ideas out.</h3>

<p align="center">
  ScholarScout reads 250M+ academic papers from 8 databases and generates actionable ideas<br>
  tailored to your goal: thesis, hackathon, SaaS product, literature review, or your next feature.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> · 
  <a href="#four-modes">Four Modes</a> · 
  <a href="#features">Features</a> · 
  <a href="https://scholarscout.pages.dev/docs">Documentation</a> · 
  <a href="https://scholarscout.pages.dev">Live Demo</a> · 
  <a href="https://github.com/neej4/ScholarScout/blob/main/CHANGELOG.md">Changelog</a>
</p>

<p align="center">
  <a href="https://youtu.be/gz_UAxNOenw">
    <img src="https://img.shields.io/badge/▶_Watch_Demo-YouTube-red?style=for-the-badge&logo=youtube" alt="Watch Demo on YouTube">
  </a>
  <a href="https://scholarscout.pages.dev">
    <img src="https://img.shields.io/badge/Web-scholarscout.pages.dev-blue?style=for-the-badge&logo=cloudflare" alt="Website">
  </a>
  <a href="https://ko-fi.com/scholarscout">
    <img src="https://img.shields.io/badge/Donate-Ko--fi-ff5e5b?style=for-the-badge&logo=ko-fi" alt="Donate on Ko-fi">
  </a>
</p>

<p align="center">
  <img src="docs/screenshot-ideas.png" alt="Idea Cards" width="700">
</p>

---

## Quick Start

```bash
git clone https://github.com/neej4/ScholarScout.git
cd ScholarScout
pip install -r requirements.txt
python preview_server.py
```

Open **http://localhost:5050** — the setup wizard walks you through in 30 seconds.

## Updating

You do **not** have to keep doing `git pull` if you installed ScholarScout from a downloaded ZIP or release folder.

Pick the path that matches how you installed it:

### 1. If you installed with Git

```bash
cd ScholarScout
git pull
pip install -r requirements.txt
python preview_server.py
```

Use this if you originally ran `git clone`.

### 2. If you installed from ZIP / Download

1. Download the latest release ZIP from GitHub.
2. Extract it to a **new folder** such as `ScholarScout-v1.6.5`.
3. Copy your old `data/` folder into the new folder if you want to keep cache, snapshots, and session history.
4. Copy your `config.yaml` into the new folder if you already set up your provider and API key.
5. Run:

```bash
cd ScholarScout-v1.6.5
pip install -r requirements.txt
python preview_server.py
```

This is the safest update path for non-Git users.

### 3. If you only want a quick overwrite update

You can extract the new ZIP on top of the old folder, but this is less safe because old files can get left behind after big releases.

Preferred rule:

- Replace app files with the new version
- Keep your own `data/` and `config.yaml`
- If anything feels broken after update, start from a fresh folder and copy only `data/` + `config.yaml`

### What should be kept

- `config.yaml`: your provider, model, and API key settings
- `data/`: your cache, snapshots, bookmarks, and session history

### What should be replaced by the new version

- `src/`
- `docs/`
- `skills/`
- `preview_server.py`
- `run_pipeline.py`
- `requirements.txt`, `pyproject.toml`, `VERSION`, and other app files

### Recommended tutorial for end users

1. Close ScholarScout.
2. Download the latest release ZIP.
3. Extract it into a new folder.
4. Move `config.yaml` and `data/` from the old folder into the new one.
5. Open terminal in the new folder.
6. Run `pip install -r requirements.txt`.
7. Run `python preview_server.py`.
8. Open `http://localhost:5050`.

If the dashboard shows an update banner, this is the process it should point to today.

Need an LLM? Pick one:

| Provider | Cost | Speed | Setup |
|----------|------|-------|-------|
| **Gemini** | Free (15 req/min) | Fast | [Get key](https://aistudio.google.com/app/apikey) |
| **Groq** | Free tier | Very fast | [Get key](https://console.groq.com/keys) |
| **Ollama** | Free (local) | GPU-dependent | [Download](https://ollama.com/download) |
| **Custom** | Any | Any | Your local proxy (LM Studio, 9router) |
| OpenRouter | Pay-per-token | Varies | [Get key](https://openrouter.ai/keys) |
| OpenAI | Pay-per-token | Fast | [Get key](https://platform.openai.com/api-keys) |

---

## Four Modes

Same papers, four different lenses:

| Mode | You ask | You get |
|------|---------|---------|
| **Academic** | "What can I research?" | Thesis topics, methodology, key papers, novelty check |
| **Product** | "What can I build?" | MVP features, tech stack, revenue model, competitors |
| **Develop** | "What can I add to my project?" | Features, integrations, optimizations grounded in your codebase |
| **Review** | "What's the state of the field?" | Thematic clusters, synthesis per cluster, gaps, open questions, reading list |

**Develop** mode treats your project description as a hard constraint — every idea must be directly applicable.

**Review** mode doesn't generate ideas. It organizes and synthesizes existing papers into a literature review skeleton.

---

## Features

### Activity Center (v1.5.3)
- Owl Chase pixel art game while pipeline runs (papers spawn as dots you catch)
- Live graph showing papers grouped by category or cluster
- LLM Chat tab narrating what the AI is doing
- Adaptive phase list (5 phases default, 6 phases review)

### Intelligence
- Trend analysis with confidence scoring
- Evidence Pack per generated idea: source papers, evidence claims, grounding score, and audit flags
- Anti-hallucination: P-number grounding (LLM citations are validated against fetched papers)
- Novelty check via semantic similarity (Gemini embeddings) or Jaccard fallback
- Quality scoring 1-10, low-quality filtered
- Deep dive: outline, methodology, datasets, timeline, tools, references
- Paper freshness: least-used papers prioritized, auto-widens date range when exhausted

### Data
- 8 sources: arXiv, OpenAlex, Semantic Scholar, PubMed, Crossref, DOAJ, Scopus, DBLP
- Smart source routing per category (medicine → PubMed+Scopus, CS → arXiv+DBLP)
- 80+ categories across 10 disciplines
- Cache-aware with expiry (7 days configurable)
- Citation-based sorting

### Personalization
- 18+ skill profiles (Academic, Product, Develop, Review)
- File upload (.pdf/.txt/.md/.json) as extra context
- Approach filter: Computational, Experimental, Clinical, Theoretical
- Onboarding wizard in 3 steps

### Dashboard
- Real-time SSE streaming
- Search, filter, bookmark, export all ideas to Markdown
- Session recovery restores ideas plus cached deep dives/implementation scouting
- Evidence badges: Grounded, Partial, or Needs Review
- Session history (last 20 runs, review + default)
- Toast notifications (no browser alerts)
- Keyboard shortcuts

---

## Project Structure

```
ScholarScout/
├── preview_server.py           # Entry point
├── run_pipeline.py             # CLI pipeline runner
├── config.example.yaml         # Config template (copy to config.yaml)
├── src/
│   ├── core/
│   │   ├── orchestrator.py     # Pipeline controller (default + review)
│   │   ├── analyzer.py         # Trend analysis
│   │   ├── generator.py        # 4-mode idea generation
│   │   ├── clusterer.py        # Paper clustering (review mode)
│   │   ├── synthesizer.py      # Literature synthesis (review mode)
│   │   ├── deep_dive.py        # Deep dive analysis
│   │   ├── novelty_checker.py  # Novelty scoring
│   │   ├── llm.py              # Multi-provider LLM client (6 providers)
│   │   ├── config.py           # Configuration + thresholds
│   │   ├── models.py           # Dataclasses
│   │   └── fetchers/           # 8 source fetchers
│   └── web/
│       ├── routes/             # Flask blueprints
│       ├── templates/          # Dashboard HTML
│       └── static/             # JS, sprites, owl game
├── skills/                     # ACADEMIC/ PRODUCT/ DEVELOP/ REVIEW/
├── tests/                      # 90+ automated tests
└── data/                       # Cache, snapshots, history (gitignored)
```

---

## CLI Usage

```bash
# Academic mode
SCOUT_GOAL="THESIS" SCOUT_CATEGORIES="cs.AI,cs.CL" python run_pipeline.py

# Product mode
SCOUT_GOAL="HACKATHON" python run_pipeline.py

# Develop mode
SCOUT_GOAL="FEATURE" SCOUT_CONTEXT="Flask app with LLM integration" python run_pipeline.py

# Review mode
SCOUT_GOAL="SYNTHESIS" SCOUT_CONTEXT="federated learning for healthcare" python run_pipeline.py
```

---

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ --ignore=tests/integration    # Unit tests
npm test                                     # JavaScript tests
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). High-impact areas:

- **New fetchers**: implement `BaseFetcher` (1 file, ~150 LOC)
- **New skill profiles**: add markdown to `skills/`
- **Prompt improvements**: `generator.py`, `analyzer.py`, `synthesizer.py`
- **New categories**: update `KEYWORD_SEEDS` + fetcher mappings

---

## Support

If ScholarScout saved you time, consider supporting:

- [Ko-fi](https://ko-fi.com/scholarscout) (International)
- [Saweria](https://saweria.co/scholarscout) (Indonesia)
- Star this repo

---

## License

MIT — see [LICENSE](LICENSE).
