# Evidence Pack

ScholarScout adds an Evidence Pack to each generated idea so research outputs are easier to audit before thesis, paper, or product work.

Each pack can include:

- `source_papers`: fetched papers that grounded the idea.
- `evidence_claims`: key idea claims linked to prompt-local paper refs such as `P1` or `P3`.
- `grounding_score`: deterministic 0-100 score based on valid sources, evidenced claims, and light text overlap.
- `risk_flags`: audit warnings such as `weak_grounding`, `low_source_count`, `missing_evidence_claims`, `stale_papers`, or `llm_unverified_reference`.

## Badge Meanings

- `Grounded`: score is strong and no invalid paper reference was detected.
- `Partial`: the idea has some fetched-paper support, but should be checked before serious use.
- `Needs Review`: evidence is weak, missing, or includes references the parser could not verify.

Old snapshots remain compatible. Ideas without evidence fields still open normally; ScholarScout simply skips the Evidence Pack section for those records.
