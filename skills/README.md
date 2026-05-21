# ScholarScout Skills

Skills are customizable research profiles that shape how ideas are generated. They define constraints like compute budget, timeline, methodology preferences, and output goals.

## How Skills Work

When you run the pipeline, ScholarScout uses your selected skill profile to:
1. Filter ideas by feasibility (compute, timeline, access requirements)
2. Adjust methodology suggestions (lab vs computational vs clinical)
3. Calibrate difficulty and scope
4. Recommend appropriate tools and datasets

## Built-in Skills

### By Level
- `UNDERGRADUATE/` — 1 semester, laptop/Colab, reproduce + extend
- `MASTERS/` — 6-12 months, cloud GPU, novel combination
- `PHD/` — 1-3 years, institutional resources, fundamental contribution

### By Domain
- `DATA_SCIENTIST/` — Python-first, ML pipelines, public datasets
- `LAB_SCIENTIST/` — Wet lab, physical experiments, bench-top
- `CLINICAL_RESEARCHER/` — Patient data, IRB protocols, clinical trials

### By Goal
- `PUBLICATION/` — Targeting conference/journal paper
- `THESIS/` — Structured for thesis chapters
- `GRANT_PROPOSAL/` — Framed for funding applications

## Creating Custom Skills

Create a new folder in `skills/` with a `SKILL.md` file:

```
skills/
└── MY_CUSTOM_SKILL/
    └── SKILL.md
```

### SKILL.md Format

```markdown
# Skill Name

## Profile
- **Duration:** [timeline]
- **Compute:** [available resources]
- **Budget:** [financial constraints]
- **Scope:** [what constitutes a complete project]

## Constraints
- [What the student CAN do]
- [What the student CANNOT do]
- [Available tools/access]

## Output Expectations
- [What a successful project looks like]
- [Publication target if any]
- [Deliverables]
```

## Community Contributions

We welcome new skills! Common requests:
- Regional skills (specific dataset access in your country)
- Industry-specific skills (pharma R&D, fintech, edtech)
- Interdisciplinary skills (CS + Biology, Engineering + Medicine)

See [CONTRIBUTING.md](../CONTRIBUTING.md) for how to submit a PR.
