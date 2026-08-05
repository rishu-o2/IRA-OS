# Planner Architecture

## Overview
The Planner subsystem is responsible for converting a declared goal and its tasks into a deterministic execution plan. It produces a read-only `ExecutionPlan` that describes task order, dependencies, and plan metadata without performing any execution.

## Responsibilities
- Manage high-level goals via `GoalManager`.
- Manage task lifecycle and task collections via `TaskManager`.
- Build validated dependency graphs using `ExecutionGraph`.
- Produce deterministic plans using `Planner` and `RuleBasedPlanner`.
- Persist plan summaries to kernel memory as a record.
- Publish planning lifecycle events through the kernel event bus.
- Integrate with kernel logging, DI, lifecycle, and memory systems.

## Dependency Boundaries
The Planner subsystem depends only on kernel modules:
- `core.container` for dependency injection
- `core.logging` for structured logging
- `core.events` for event publishing
- `core.memory` for plan persistence and audit
- `core.lifecycle` for lifecycle and health semantics

It does not depend on application-specific runtime, Tools, Brain, Android, Desktop, or external storage.

## Goal Lifecycle
1. A `Goal` is created by calling `PlannerManager.create_goal()`.
2. The goal is stored in `GoalManager` and remains immutable.
3. Creating a goal emits a `GoalCreated` event.
4. The goal is later passed into `build_plan()` to produce an execution plan.

## Task Lifecycle
1. Tasks are created and stored in `TaskManager`.
2. Each `Task` is immutable; state transitions are produced by manager methods.
3. The planner reads tasks for a goal and does not execute or mutate them.
4. Task dependencies are validated when generating the dependency graph.

## ExecutionPlan Lifecycle
1. `PlannerManager.build_plan(goal_id)` loads goal and tasks for the requested goal.
2. The planner validates task dependencies and builds a DAG.
3. The planner topologically sorts tasks into a deterministic order.
4. A frozen `ExecutionPlan` is returned, containing goal, task order, graph, and estimated steps.
5. The plan summary is persisted to memory as a `MemoryRecord` and published.

## Dependency Graph Generation
`ExecutionGraph.build(tasks)` converts task dependency lists into an adjacency mapping from task id to dependency ids. It validates:
- every dependency exists in the task set
- there are no cycles in the graph

Invalid dependency graphs raise `ExecutionGraphError` or `CycleDetectedError`.

## Topological Sorting
The planner uses `ExecutionGraph.topological_sort(tasks)` to produce a linear order that respects dependencies. The sort is implemented as a DAG traversal with in-degree tracking and deterministic selection of ready tasks.

## Priority Tie-Breaking
When multiple tasks become ready at the same time, the planner chooses the next task by:
- descending `Priority` value
- stable task identifier ordering as a secondary tie-breaker

This preserves deterministic plan generation while honoring task priority.

## Memory Integration
Planner persists summary metadata into `core.memory` after successful plan generation. The plan summary record includes:
- goal id
- task ids in plan order
- dependency graph
- estimated steps
- creation timestamp

Memory is treated as read-only for planning logic; planner only writes plan summaries and does not query or mutate historical memory during plan creation.

## Event Publishing
The Planner subsystem publishes events through `core.events`:
- `GoalCreated` when goals are created
- `PlanCreated` when a plan is generated successfully
- `PlanFailed` when plan generation fails

This supports observability and audit without coupling the planner to execution runtime.

## Logging Integration
Planner components receive a `Logger` from `LoggerFactory`. The manager logs lifecycle events and planning outcomes, enabling consistent kernel-level telemetry.

## Lifecycle Integration
`PlannerManager` implements kernel lifecycle interfaces:
- `start()` logs planner startup
- `shutdown()` logs planner shutdown
- `health_check()` reports health through kernel health models

This allows the planner to be managed like other kernel subsystems.

## DI Integration
`PlannerModule` registers planner components with the container:
- `GoalManager`
- `TaskManager`
- `ExecutionGraph`
- `RuleBasedPlanner`
- `Planner`
- `PlannerManager`

Async factory registration is used for components requiring runtime resolution of logger, memory, and event bus.

## Thread-Safety
Planner state is isolated in in-memory managers. `PlannerManager` itself does not use locks because it delegates safe state management to the kernel DI-managed components. Memory writes are protected by `MemoryManager` internals.

## Complexity Analysis
- Graph build: O(n + e) where n is task count and e is dependency count.
- Cycle detection: O(n + e)
- Topological sort: O(n + e)
- Plan persistence: O(1) for recording metadata after generation

## Future Extension Points
- Add adaptive replanning once runtime execution conditions exist.
- Add cost/duration heuristics to the plan model.
- Add support for alternative planning strategies via `PlanningStrategy`.
- Add plan caching or incremental plan updates.
