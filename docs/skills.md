# Skills system

Skills are markdown files that inject constraints into the idea generation prompt. They tell the LLM what kind of output to produce.

## Structure

```
skills/
├── ACADEMIC/           # Research-oriented
│   ├── UNDERGRADUATE/SKILL.md
│   ├── MASTERS/SKILL.md
│   ├── PHD/SKILL.md
│   ├── THESIS/SKILL.md
│   ├── PUBLICATION/SKILL.md
│   ├── GRANT_PROPOSAL/SKILL.md
│   ├── LAB_SCIENTIST/SKILL.md
│   ├── CLINICAL_RESEARCHER/SKILL.md
│   └── DATA_SCIENTIST/SKILL.md
├── PRODUCT/            # Build something new
│   ├── HACKATHON/SKILL.md
│   ├── SIDE_PROJECT/SKILL.md
│   ├── AI_TOOL/SKILL.md
│   └── INDUSTRY_RND/SKILL.md
└── DEVELOP/            # Improve existing project
    ├── FEATURE/SKILL.md
    ├── INTEGRATION/SKILL.md
    ├── OPTIMIZATION/SKILL.md
    ├── EXTENSION/SKILL.md
    └── PIVOT/SKILL.md
```

## How they work

When you select a goal (e.g., "Hackathon"), the generator loads `skills/PRODUCT/HACKATHON/SKILL.md` and appends it to the LLM prompt. The skill file contains constraints like timeline, budget, output expectations, and anti-patterns.

## Creating a custom skill

1. Create a folder: `skills/PRODUCT/MY_SKILL/`
2. Add `SKILL.md` with your constraints
3. The skill is automatically available when selected as a goal

A skill file should include:
- Profile (duration, compute, budget, scope)
- Constraints (what the output must/must not be)
- Output expectations (what a good result looks like)
- Anti-patterns (what to avoid)

Keep it under 2000 characters — longer files get truncated.

## Contributing skills

Skills are the easiest way to contribute to ScholarScout. If you have domain expertise (e.g., "How to write a LPDP grant proposal"), write it as a skill file and submit a PR.
