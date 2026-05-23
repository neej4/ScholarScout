# Feature Development

## Mode
Generate NEW user-facing features for an existing project, inspired by techniques from recent papers.

## Hard Constraints
- Every feature MUST be directly applicable to the project described in context
- Feature must solve a real user pain point (not "nice to have")
- Must be implementable with the project's existing tech stack (no rewrites)
- Must not break existing functionality (additive, not destructive)
- Effort: 1-5 days for a solo developer

## Output Format
Each idea must include:
- Feature name (specific, not generic)
- User story: "As a [user type], I want [feature] so that [benefit]"
- Which paper technique enables this (cite P-number)
- Implementation sketch: 3-5 bullet points of how to build it
- Effort estimate: hours or days
- Risk: what could go wrong or be harder than expected

## What Makes a Good Feature Idea
- Directly addresses a complaint or friction point users have
- Uses a technique from the papers that the project doesn't currently use
- Small surface area (one endpoint, one UI element, one pipeline step)
- Measurable impact (saves time, reduces errors, increases engagement)
- Can be shipped behind a feature flag for safe rollout

## Anti-Patterns
- "Rebuild the whole system using technique X" — too big
- "Add AI to everything" — too vague
- Features that require new infrastructure (new database, new language)
- Features that duplicate what already exists with slight variation
