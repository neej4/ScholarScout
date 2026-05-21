# Contributing to ScholarScout

Thanks for your interest in contributing! Here's how you can help.

## Quick Start

```bash
git clone https://github.com/neej4/ScholarScout.git
cd ScholarScout
pip install -r requirements.txt
npm install
python preview_server.py
```

## Ways to Contribute

### Add a New Data Source (Fetcher)
1. Create `src/core/fetchers/your_fetcher.py`
2. Inherit from `BaseFetcher` in `base.py`
3. Implement `fetch_papers(category, max_results)` → returns `List[Paper]`
4. Add to `orchestrator.py` fetchers list
5. Map categories in your fetcher

### Improve Prompts
- Edit `src/core/analyzer.py` (trend analysis prompt)
- Edit `src/core/generator.py` (idea generation prompt)
- Run `@prompt-auditor` agent to check quality

### Add Categories
- Add to `CAT_GROUPS` in `dashboard.html`
- Add keyword mapping in `analyzer.py` KEYWORD_SEEDS
- Add concept mapping in `openalex_fetcher.py`
- Add search keywords in `semanticscholar_fetcher.py`

### Create Custom Skills
Skills are research profiles that shape idea generation. See `skills/README.md` for the full guide.

1. Create `skills/YOUR_SKILL_NAME/SKILL.md`
2. Define: Profile, Constraints, Methodology Preferences, Output Expectations
3. Examples: `DATA_SCIENTIST`, `CLINICAL_RESEARCHER`, `THESIS`, `GRANT_PROPOSAL`

Ideas for new skills:
- **Industry R&D** — corporate research constraints (IP, timelines, product focus)
- **Hackathon** — 48-hour scope, demo-driven, team of 3-4
- **Interdisciplinary** — CS + Medicine, Engineering + Biology
- **Regional** — Indonesia-specific datasets, local collaboration networks
- **Open Science** — fully reproducible, open data, preregistered

### Fix Bugs
- Check GitHub Issues for reported bugs

## Running Tests

```bash
# Python tests
pytest tests/

# JavaScript tests
npm test

# Both
pytest tests/ && npm test
```

## Code Style

- Python: Follow existing patterns (dataclasses, type hints, docstrings)
- JavaScript: Vanilla JS, no frameworks, event delegation pattern
- CSS: CSS variables, minimal classes, dark theme
- Prompts: Be specific, avoid generic phrases, include examples

## Pull Request Process

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make changes and run tests
4. Commit with clear message
5. Push and open a PR

## Questions?

Open an issue on GitHub or reach out to the maintainers.
