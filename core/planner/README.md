# Planner Subsystem

The Planner subsystem converts goals and tasks into deterministic execution plans. It builds dependency graphs, validates task relationships, detects cycles, and returns an immutable `ExecutionPlan` without performing runtime execution.

## Folder structure

- `core/planner/goals.py` — manages goal lifecycle and state transitions
- `core/planner/tasks.py` — manages tasks and task lifecycle
- `core/planner/graph.py` — builds dependency graphs and performs topological sorting
- `core/planner/planner.py` — core planning facade
- `core/planner/strategy.py` — planning strategy interface and rule-based implementation
- `core/planner/manager.py` — PlannerManager facade integrating memory, events, logging, and lifecycle
- `core/planner/planner_module.py` — DI module for planner registration
- `core/planner/models.py` — immutable planner models (`Goal`, `Task`, `ExecutionPlan`, `PlanResult`)
- `core/planner/events.py` — planner event models

## Public API

- `GoalManager`
- `TaskManager`
- `ExecutionGraph`
- `Planner`
- `RuleBasedPlanner`
- `PlannerManager`
- `PlannerModule`
- `Goal`
- `Task`
- `ExecutionPlan`
- `PlanResult`
- `GoalCreated`
- `PlanCreated`
- `PlanFailed`

## Example usage

```python
from core.container import Container
from core.events import EventBus
from core.logging import LoggerFactory
from core.memory import MemoryModule
from core.planner import PlannerModule, PlannerManager, Goal, Task, Priority

container = Container()
container.register_instance(LoggerFactory, LoggerFactory())
container.register_instance(EventBus, EventBus())
container.install(MemoryModule())
container.install(PlannerModule())

planner_manager = await container.resolve(PlannerManager)

goal = Goal(id="goal1", title="Prepare release", priority=Priority.HIGH)
await planner_manager.create_goal(goal)

planner_manager._task_manager.create(Task(id="task1", goal_id="goal1", name="Collect requirements"))
planner_manager._task_manager.create(Task(id="task2", goal_id="goal1", name="Review design", dependencies=("task1",)))

result = await planner_manager.build_plan("goal1")
if result.success and result.plan:
    print([task.id for task in result.plan.tasks])
```

## Extension points

- Add alternative planning strategies by implementing `PlanningStrategy`.
- Add plan caching or memoization in `PlannerManager`.
- Add cost or duration heuristics once execution statistics exist.
- Add runtime-aware replanning in later milestones.

## Design philosophy

- Keep planning and execution separate.
- Keep planner models immutable.
- Favor deterministic results over heuristic complexity.
- Keep dependencies bounded to kernel infrastructure only.
