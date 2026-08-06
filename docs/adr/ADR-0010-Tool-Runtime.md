# Architecture Decision Record 0010: Tool Runtime

## Title
ADR-0010: Tool Runtime

## Status
Accepted (Frozen for API)

## Date
2026-08-06

## Context
Following the API freeze of the Brain Engine (Milestone 9), the system requires an execution orchestration layer to physically invoke tools and platform capabilities on the user's behalf. The Brain decides WHAT to do, but it intentionally does not know HOW to do it.

## Decision
Implement a Tool Runtime subsystem that:
- Acts as a stateless, purely orchestration-focused execution layer.
- Refers to all executable tools as `Capabilities` to future-proof the architecture for Android, Windows, Cloud, and Browser environments.
- Follows a strict canonical pipeline: Validate -> Lookup -> Dispatch -> Execute -> Normalize -> Publish -> Return.
- Exposes no platform-specific logic or business reasoning.
- Defers the actual execution implementations to future milestones (e.g. Milestone 11).

## Rationale
- Separating the Brain's decision-making from the Runtime's physical execution isolates risk and ensures platform independence.
- Elevating the abstraction to `Capability` allows the OS to invoke diverse targets (like an Android Camera or a generic Python script) under the exact same lifecycle and event structure.
- Adhering to the canonical pipeline provides extreme predictability and makes debugging highly traceable.

## Consequences
- Positive: The Brain and Runtime remain decoupled.
- Positive: We can introduce a vast plugin ecosystem without changing the Runtime.
- Negative: We must write platform adapter wrappers (Capabilities) for every execution target.

## Future
- Implement `AndroidCapability` adapters.
- Implement `WindowsCapability` adapters.
