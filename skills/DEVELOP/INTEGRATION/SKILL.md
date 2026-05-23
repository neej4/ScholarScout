# Integration Development

## Mode
Generate ideas for connecting an existing project with external services, APIs, platforms, or ecosystems — inspired by techniques from recent papers.

## Hard Constraints
- Integration must add clear value that the project cannot achieve alone
- Must use publicly available APIs or protocols (no private/enterprise-only)
- Must handle failure gracefully (external service down = degrade, not crash)
- Must not create vendor lock-in (abstraction layer required)
- Auth/credentials must be user-provided, not hardcoded

## Output Format
Each idea must include:
- Integration name: "[Project] × [External Service/Platform]"
- Value proposition: what becomes possible that wasn't before
- Which paper technique or finding motivates this integration
- Data flow: what goes out, what comes back, where it's stored
- API/protocol: specific endpoints or SDKs needed
- Fallback: what happens when the external service is unavailable
- Effort estimate

## Integration Categories to Consider
- Export targets: where users want their data to go (Notion, Google Docs, Zotero, BibTeX)
- Import sources: where additional context comes from (GitHub repos, Google Scholar profiles, ORCID)
- Notification channels: how users want to be alerted (email, Telegram, Discord, Slack)
- Platform embedding: where the tool could live as a plugin (VSCode, TRAE, Obsidian, browser extension)
- Data enrichment: external APIs that add value (citation counts, altmetrics, funding databases)

## What Makes a Good Integration Idea
- Users already manually copy data between the project and the target — automation saves real time
- The external platform has a stable, documented API
- Integration is bidirectional or creates a feedback loop (not just one-way export)
- Enables a workflow that was previously impossible, not just convenient
