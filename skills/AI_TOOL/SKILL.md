# AI/LLM-Powered Tool Project

## Profile
- **Duration:** 2-8 weeks (focused build)
- **Compute:** LLM API costs ($5-50/month), laptop for development
- **Budget:** $20-100 (API credits, domain, hosting)
- **Scope:** Working tool with LLM integration that solves a specific workflow problem

## Constraints
- Must use LLM as core intelligence (not just a wrapper around ChatGPT)
- Must have a clear non-LLM fallback or graceful degradation
- Must handle LLM failures: timeouts, rate limits, malformed responses
- Token budget must be considered (not unlimited API calls)
- Must work with at least 2 LLM providers (avoid vendor lock-in)
- Response time must be acceptable for the use case (< 30s for interactive, async for batch)
- Must cache expensive LLM calls where possible

## Architecture Patterns
- Pipeline: sequential steps where each stage feeds the next
- Multi-source: fetch from multiple APIs, deduplicate, merge
- Prompt chaining: output of one LLM call becomes input for the next
- Fallback: if primary LLM fails, degrade gracefully (cached results, simpler model, rule-based)

## Key Technical Decisions
- Provider abstraction: one interface, multiple backends
- Adaptive token budgets: different max_tokens per task type
- Structured output: force JSON from LLM, validate schema, handle parse failures
- Rate limit handling: exponential backoff, fast-fail, parallel where safe
- Caching: cache identical prompts, cache expensive computations

## Output Expectations
- Deployed tool accessible via browser or CLI
- Works with free-tier LLM (Gemini, Groq) out of the box
- README with setup instructions (< 5 minutes to first run)
- Handles edge cases without crashing (empty input, API down, malformed response)
- Clear value proposition: "saves X minutes" or "does Y that was previously manual"

## What Makes a Good AI Tool Project
- Solves a real workflow pain point (not a demo)
- LLM adds genuine intelligence (not just reformatting)
- Works reliably (handles failures, retries, caching)
- Cheap to run (token-efficient prompts, smart caching)
- Extensible (new data sources, new LLM providers, community plugins)

## Anti-Patterns to Avoid
- "ChatGPT wrapper" — just forwarding user input to LLM with no added value
- Unbounded token usage — no budget limits, costs spiral
- Single provider dependency — breaks when that API goes down
- No error handling — crashes on first timeout or malformed response
- Over-engineering — building for 1M users when you have 10
