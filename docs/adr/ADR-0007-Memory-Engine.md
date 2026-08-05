# Architecture Decision Record 0007: Memory Engine

## Title
ADR-0007: Kernel Memory Engine

## Status
Accepted

## Date
2026-08-05

## Context
The next kernel milestone must provide a first-class knowledge layer. The Memory Engine is the first subsystem that directly supports IRA's intelligence without introducing reasoning, embeddings, or external storage dependencies.

## Decision
Implement `core/memory/` as an in-memory memory subsystem with the following characteristics:

- `MemoryRecord` is an immutable, JSON-serializable model.
- Storage is in-memory only for Milestone 7.
- Search is deterministic and rule-based; there is no semantic ranking or LLM influence.
- Retention policies are pluggable and support forgetting via TTL, LRU, and importance thresholds.
- The subsystem integrates only with kernel infrastructure: Config, Logging, Event Bus, DI Container, Lifecycle, Identity.
- No usage of Brain, Planner, Tools, Android, Desktop, or application layers.

## Consequences
- **Positive**: A stable kernel API for future persistence and intelligence layers.
- **Positive**: Simplified testing and predictable behavior.
- **Negative**: Memory is volatile until persistence is added in later milestones.

## Notes
This ADR intentionally freezes the API around in-memory storage and simple search semantics. Reasoning, embeddings, and persistent memory storage are deferred to future architecture decisions.
