# Architecture Decision Record 0005: Lifecycle Manager

## Title
ADR-0005: Lifecycle Manager & Dependency DAG Orchestration

## Status
Accepted

## Date
2026-08-03

## Context
As IRA OS transitions from isolated modules (Event Bus, Config, DI, Logging) into a cohesive operating system, a mechanism is required to orchestrate the startup, monitoring, and shutdown of these systems. Hardcoding the startup sequence is brittle. We need a kernel-level process manager that can dynamically order component initialization based on dependencies, recover gracefully from failures, and provide standard lifecycle hooks for future extensibility.

## Decision
We implemented a platform-independent `LifecycleManager` in `core/lifecycle/` that relies exclusively on `core/events`, `core/container`, `core/config`, and `core/logging`.

Key design choices:
1. **Dependency DAG over Simple Priority**: The startup order is computed dynamically using a topological sort of the component dependencies. Explicit `priority` values are used strictly as a tie-breaker for independent components, ensuring deterministic execution.
2. **Lifecycle Hooks**: Components can implement granular async hooks (`before_boot`, `start`, `after_shutdown`, etc.) rather than a monolithic interface. This allows components to opt-in only to the phases they need.
3. **Timeout Support**: Every component registration accepts optional `startup_timeout` and `shutdown_timeout` values to prevent hanging the system.
4. **Automatic Rollback**: If a critical component fails during startup, the orchestrator automatically stops and shuts down all already-started components in reverse topological order.
5. **Separation of Concerns**: The implementation is divided into a `ComponentRegistry` (state), a `HealthMonitor` (observability), and a `LifecycleOrchestrator` (execution), behind a unified `LifecycleManager` facade.
6. **Kernel Bootstrapper**: A `Bootstrap` class assembles the foundational kernel services (Config, Logging, DI, Event Bus) and injects them into the Lifecycle Manager without taking control of the main event loop.

## Alternatives Considered
- **Strict Priority-Based Ordering**: Rejected. While simpler to implement, it becomes impossible to manage as the system scales and components depend on each other implicitly.
- **Synchronous Lifecycle Hooks**: Rejected. Modern Python components (especially network clients or DB connections) require async initialization.
- **Tying Bootstrap to the Event Loop**: Rejected. The Lifecycle Manager should orchestrate components, but the application entry point (e.g., Server or CLI) should own the event loop.

## Consequences
- **Positive**: Robust, extensible startup and shutdown sequences. True dependency management prevents initialization race conditions.
- **Positive**: Non-critical components can fail without bringing down the OS.
- **Negative**: Components must correctly define their dependencies in the registration phase, putting the onus on the developer to understand the graph.

## Version
v1.4.0 (Milestone 5)
