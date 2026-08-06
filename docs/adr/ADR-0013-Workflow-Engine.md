# Architecture Decision Record 0013: Task & Workflow Engine

## Title
ADR-0013: Task & Workflow Engine

## Status
Accepted

## Date
2026-08-06

## Context
IRA OS is capable of planning (Planner), executing (Tool Runtime), and authorizing (Permission Kernel). However, it lacks the ability to schedule future work, retry failures, or manage asynchronous long-running multi-step processes. Milestone 13 introduces the Task & Workflow Engine to fulfill this orchestration role without leaking execution logic.

## Decision
Introduce the Workflow Engine positioned between the Brain and the Permission Kernel.

### Structural Decisions Made

1. **Strict Decoupling:** The Workflow Engine is entirely stateless (where possible), deterministic, and unaware of what platform it is running on. It depends only on core foundational packages (`core.events`, `core.lifecycle`, etc.).

2. **Abstracted Execution:** The engine does not execute platform tools itself. The `WorkflowExecutor` is an abstraction designed to eventually delegate execution to the Tool Runtime/Permission Kernel.

3. **Event-Driven Orchestration:** Every step of the pipeline emits an immutable event (`TaskQueued`, `TaskStarted`, `WorkflowCompleted`).

4. **In-Memory Scaffolding:** For this milestone, the queue and scheduler are implemented in-memory without background threads or asynchronous loops, ensuring deterministic API-freeze behavior.

## Consequences
- Positive: Brain no longer needs to manage its own timers or polling loops for long-running workflows.
- Positive: Tool Runtime is shielded from retry and scheduling complexity.
- Negative: True scheduling and background execution will require a dedicated async runner or threading strategy in a future milestone.
