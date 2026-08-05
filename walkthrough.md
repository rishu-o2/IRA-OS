# Planner Architecture Walkthrough

## Planner architecture
The Planner subsystem converts goal definitions and task collections into deterministic execution plans. It is intentionally separated from execution runtime, keeping planning logic focused on dependency validation, ordering, and plan metadata.

## Dependency graph
`ExecutionGraph.build()` constructs a directed graph mapping each task id to its declared dependencies. It validates that every referenced dependency exists and that the graph contains no cycles.

## Goal creation
Goals are created through `PlannerManager.create_goal()`. A `Goal` is immutable once created, and creation publishes a `GoalCreated` event.

## Task graph creation
Tasks are assembled in `TaskManager`. Each `Task` includes a `goal_id`, dependencies, and priority. The planner queries the task manager for tasks belonging to a specific goal.

## Execution plan generation
`PlannerManager.build_plan(goal_id)` performs the following steps:
- loads the goal from `GoalManager`
- loads tasks from `TaskManager` for the goal
- validates the dependency graph with `ExecutionGraph`
- sorts tasks topologically with deterministic priority tie-breaking
- returns a frozen `ExecutionPlan`

## Memory interaction
After successful plan generation, the planner writes a summary `MemoryRecord` into `MemoryManager`. This is audit metadata only; the planner does not query memory for planning decisions.

## Events
Successful and failed planner actions emit events:
- `GoalCreated`
- `PlanCreated`
- `PlanFailed`

These events are published through the kernel event bus and support observability and external listeners.

## Logging
Planner components receive a logger from `LoggerFactory`. `PlannerManager` logs lifecycle transitions and planning outcomes.

## Lifecycle
`PlannerManager` implements kernel lifecycle hooks and health checks, making it compatible with the kernel`s startup/shutdown orchestration.

## Testing
Planner tests cover:
- topological ordering
- cycle detection
- plan generation
- plan persistence to memory
- event publishing
- error handling when no tasks are present

## Performance
- Graph build, cycle detection, and topological sort are O(n + e) where n is the number of tasks and e is the number of dependencies.
- The current planner is deterministic and lightweight, suitable for kernel-level planning without runtime costs.

## Remaining technical debt
- No adaptive runtime replanning.
- No cost/duration estimation.
- No execution scheduling heuristics.
