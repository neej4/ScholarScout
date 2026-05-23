# Extension Development

## Mode
Generate ideas for plugin systems, addon architectures, or modular extensions that allow the project to be extended by third parties or the community — inspired by patterns from recent papers.

## Hard Constraints
- Extension must not require modifying core code to install/use
- Must have a clear interface contract (what the extension provides, what it receives)
- Must be sandboxed or isolated (bad extension cannot crash the system)
- Must be discoverable (users can find and enable extensions)
- Must be documentable in <1 page (simple enough for community contributors)

## Output Format
Each idea must include:
- Extension type: what kind of extensibility this adds
- Interface contract: inputs, outputs, lifecycle hooks
- Example extension: one concrete plugin that would be built first
- Paper inspiration: which technique or architecture pattern from the papers
- Developer experience: how a contributor would create a new extension
- Distribution: how extensions are shared (marketplace, git repo, npm/pip package)

## Extension Patterns to Consider
- Data source plugins: add new paper sources (PubMed, IEEE, DBLP, Google Scholar)
- Analyzer plugins: custom trend analysis logic (domain-specific keyword extraction)
- Output formatters: export to different formats (LaTeX, Notion, Markdown, slide deck)
- Skill profiles: community-contributed research/product profiles
- UI widgets: dashboard components that show custom visualizations
- Webhook/event hooks: trigger external actions when pipeline completes

## What Makes a Good Extension Idea
- Clear separation of concerns (extension does ONE thing)
- Low barrier to entry (contributor can build in <1 day)
- Composable (extensions can work together without conflicts)
- Backward compatible (adding extension doesn't break existing users)
- Inspired by a real paper technique that the core doesn't implement
