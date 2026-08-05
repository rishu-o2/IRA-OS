# Architecture Decision Record 0008: Planner

## Title
ADR-0008: Planner Subsystem

## Status
Accepted

## Date
2026-08-05

## Context
The kernel requires a deterministic, audit-friendly way to convert declared goals and tasks into execution plans without embedding execution concerns. Milestone 8 introduces the Planner as a pure planning engine, separate from runtime execution and external tool orchestration.

## Decision
Implement a Planner subsystem that:
- builds dependency graphs from goals and tasks
- validates task dependencies and detects cycles
- produces a deterministic `ExecutionPlan`
- persists plan summaries to kernel memory
- publishes planner lifecycle events
- does not execute tasks or tools

Planner responsibility is intentionally limited to planning only.

## Rationale
- Planning and execution are separate concerns in kernel architecture.
- A plan-only subsystem enables independent auditing, validation, and future runtime integration.
- DAG-based planning is a natural fit for task dependency resolution.
- Topological sorting preserves dependency order and produces a safe execution sequence.
- Memory is read-only from the planner perspective because the planner must not depend on mutable runtime state.
- Tool execution is excluded because runtime orchestration belongs to later Milestones.

## Why Planner Only Produces Plans
- Keeps the kernel API stable and audit-friendly.
- Avoids coupling planning logic to execution semantics, retries, or tool-specific behavior.
- Enables later layers to consume plans without reusing planner internals.

## Why Execution is Separated
- Execution requires runtime state, retries, side effects, and tool integrations that are not part of a deterministic kernel plan.
- Separation reduces risk and simplifies verification.
- It allows planning to remain platform-independent and testable.

## Why DAG-Based Planning Was Chosen
- Tasks with dependencies naturally form a directed acyclic graph.
- DAGs make it possible to validate consistency and detect cycles before execution.
- DAG-based plans support future extensions like parallel execution and dependency-aware scheduling.

## Why Topological Sorting is Used
- Topological order ensures all dependencies appear before dependent tasks.
- It is deterministic when combined with priority-based tie-breaking.
- It is a proven algorithm for dependency resolution in build systems and workflow engines.

## Why Memory is Read-Only from Planner
- The planner must not rely on execution or historical memory state when producing a plan.
- Plan summary persistence is purely audit/logging metadata, not planner input.
- This minimizes side effects and preserves planner determinism.

## Why Tool Execution is Excluded
- Tool execution belongs to runtime or orchestration subsystems.
- Including it in the planner would prematurely expand the API and break the clean separation of concerns.

## Architectural Constraints
- No external runtime dependencies.
- Only kernel modules may be used.
- Planner must remain platform-independent.
- Public API is frozen for Milestone 8.

## Alternatives Considered
- Embedding execution in the planner: rejected because it violates separation of concerns.
- Using heuristic search or cost optimization: rejected for Milestone 8 due to scope and audit readiness.
- Allowing planner to query memory for historical plans: rejected to preserve plan determinism.

## Consequences
- Positive: stable API interface for goals, tasks, and plans.
- Positive: independent audit readiness.
- Negative: no runtime-aware or adaptive planning in this milestone.
- Negative: no execution cost estimation or schedule optimization.
