# FAQ

## General

**What is ScholarScout?**
A tool that reads academic papers and generates ideas — for research, products, or features for your existing project.

**Is it free?**
Yes. Open source, MIT licensed, runs locally. You need an LLM API key (Gemini and Groq have free tiers).

**Does it send my data anywhere?**
Only to the LLM provider you choose. No telemetry, no tracking, no cloud storage. Everything stays on your machine.

**What languages does it support?**
English and Bahasa Indonesia for output. Papers are fetched in any language available on arXiv/OpenAlex/Semantic Scholar.

## Usage

**Quick vs Run — what's the difference?**
- **Run**: Fetches fresh papers from 3 sources, analyzes trends, generates ideas. Takes 2-5 minutes.
- **Quick**: Uses cached papers (from previous runs) or LLM knowledge. Takes ~10 seconds.

Use Quick for fast brainstorming. Use Run when you want fresh, grounded results.

**What are the colored badges in Deep Dive?**
Source-alignment indicators. They measure how closely each Deep Dive section matches the source paper's abstract:
- Green (Source-aligned): closely reflects the paper
- Yellow (Partially aligned): some claims may be inferred
- Red (Low alignment): content may not be directly supported — verify manually

These measure topical similarity, not factual accuracy. Always check the original paper.

**Why did I get 0 ideas for a category?**
Usually rate limiting. Semantic Scholar limits to 100 requests per 5 minutes for free users. Solutions:
- Wait 5 minutes and try again
- Use Quick mode (uses cache)
- Set `S2_API_KEY` environment variable (free, 10000 req/5min)
- Reduce number of categories selected

**Can I use my own LLM (local)?**
Yes. Use Ollama (fully local, no internet) or Custom endpoint (any OpenAI-compatible API like LM Studio, vLLM, 9router).

## Contributing

**How do I add a new paper source?**
Implement `BaseFetcher` in a new file under `src/core/fetchers/`. See existing fetchers for examples.

**How do I create a custom skill?**
Add a markdown file at `skills/ACADEMIC/MY_SKILL/SKILL.md` or `skills/PRODUCT/MY_SKILL/SKILL.md`. See `docs/skills.md` for format.

**How do I run tests?**
```bash
pip install -e ".[dev]"
pytest tests/ -m "not integration"
```
