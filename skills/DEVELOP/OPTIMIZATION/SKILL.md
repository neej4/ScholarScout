# Optimization Development

## Mode
Generate ideas for improving performance, reducing cost, fixing bottlenecks, or increasing reliability of an existing project — inspired by techniques from recent papers.

## Hard Constraints
- Optimization must be measurable (before/after metric required)
- Must not change user-facing behavior (same input → same output, just faster/cheaper)
- Must be implementable incrementally (no "rewrite from scratch")
- Must have a rollback plan if optimization causes regression
- Target: 2x improvement minimum (not 5% marginal gains)

## Output Format
Each idea must include:
- Optimization name (specific bottleneck addressed)
- Current state: what's slow/expensive/unreliable and why
- Paper technique: which method from the papers solves this
- Expected improvement: quantified (e.g., "reduce API calls by 60%", "cut latency from 8s to 2s")
- Implementation plan: 3-5 steps
- Measurement: how to verify the improvement worked
- Risk: what could regress

## Optimization Categories
- Token/cost reduction: prompt compression, caching, batching, model distillation
- Latency reduction: parallel execution, prefetching, streaming, edge caching
- Reliability: retry strategies, circuit breakers, graceful degradation, redundancy
- Storage: compression, deduplication, indexing, migration to better data structures
- Throughput: connection pooling, queue-based processing, horizontal scaling patterns

## What Makes a Good Optimization Idea
- Addresses the actual bottleneck (profiled, not guessed)
- Paper provides a proven technique with benchmarks
- Can be A/B tested or feature-flagged
- Improvement is noticeable to users (not just internal metrics)
- Does not increase code complexity disproportionately
