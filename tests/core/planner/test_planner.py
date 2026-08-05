import asyncio
from dataclasses import dataclass

import pytest

from core.container import Container
from core.events import EventBus, Event
from core.logging import LoggerFactory
from core.logging.sinks import NullSink
from core.memory import MemoryModule, MemoryManager, SearchQuery
from core.planner import (
    Goal,
    Task,
    GoalState,
    Priority,
    TaskState,
    CycleDetectedError,
    Planner,
    RuleBasedPlanner,
    ExecutionGraph,
    PlannerManager,
    PlannerModule,
)


def make_goal(goal_id: str, title: str = "Test Goal") -> Goal:
    return Goal(id=goal_id, title=title, priority=Priority.NORMAL)


def make_task(task_id: str, goal_id: str, dependencies=(), priority=Priority.NORMAL) -> Task:
    return Task(id=task_id, goal_id=goal_id, name=f"Task {task_id}", dependencies=tuple(dependencies), priority=priority)


@pytest.mark.anyio
async def test_execution_graph_topological_sort():
    tasks = [
        make_task("t1", "g1"),
        make_task("t2", "g1", dependencies=("t1",)),
        make_task("t3", "g1", dependencies=("t1",)),
        make_task("t4", "g1", dependencies=("t2", "t3")),
    ]

    graph = ExecutionGraph()
    plan_graph = graph.build(tasks)

    assert plan_graph["t4"] == ("t2", "t3")
    assert plan_graph["t2"] == ("t1",)
    assert plan_graph["t3"] == ("t1",)

    ordered = graph.topological_sort(tasks)
    assert [task.id for task in ordered] == ["t1", "t2", "t3", "t4"]


@pytest.mark.anyio
async def test_execution_graph_detects_cycle():
    tasks = [
        make_task("a", "g1", dependencies=("b",)),
        make_task("b", "g1", dependencies=("c",)),
        make_task("c", "g1", dependencies=("a",)),
    ]

    graph = ExecutionGraph()
    with pytest.raises(CycleDetectedError):
        graph.build(tasks)


@pytest.mark.anyio
async def test_planner_creates_ordered_plan():
    goal = make_goal("goal1")
    tasks = [
        make_task("t1", "goal1", priority=Priority.LOW),
        make_task("t2", "goal1", dependencies=("t1",), priority=Priority.HIGH),
    ]

    planner = Planner(RuleBasedPlanner(ExecutionGraph()))
    plan = planner.plan(goal, tasks)

    assert plan.goal == goal
    assert plan.estimated_steps == 2
    assert [task.id for task in plan.tasks] == ["t1", "t2"]


@pytest.mark.anyio
async def test_planner_rejects_cancelled_goal():
    goal = make_goal("goal_cancelled")
    goal = goal.with_state(GoalState.CANCELLED)
    tasks = [make_task("t1", "goal_cancelled")]

    planner = Planner(RuleBasedPlanner(ExecutionGraph()))
    with pytest.raises(Exception) as excinfo:
        planner.plan(goal, tasks)

    assert "cancelled goal" in str(excinfo.value).lower()


@pytest.mark.anyio
async def test_planner_manager_build_plan_publishes_and_persists():
    container = Container()
    container.register_instance(LoggerFactory, LoggerFactory(sinks=[NullSink()]))
    container.register_instance(EventBus, EventBus())
    container.install(MemoryModule())
    container.install(PlannerModule())

    manager = await container.resolve(PlannerManager)
    event_bus = await container.resolve(EventBus)
    memory_manager = await container.resolve(MemoryManager)

    events = []

    async def handler(event: Event):
        events.append(event.name)

    event_bus.subscribe(Event, handler)

    goal = make_goal("goal2")
    await manager.create_goal(goal)

    await container.resolve(PlannerManager)
    await container.resolve(MemoryManager)

    manager._task_manager.create(make_task("task1", "goal2"))
    manager._task_manager.create(make_task("task2", "goal2", dependencies=("task1",)))

    result = await manager.build_plan("goal2")

    assert result.success is True
    assert result.plan is not None
    assert [task.id for task in result.plan.tasks] == ["task1", "task2"]
    assert "PlanCreated" in events
    assert "GoalCreated" in events

    records = await memory_manager.search(SearchQuery(tags=("planner",), limit=5))
    assert len(records) == 1
    assert records[0].record.owner_id == "goal2"


@pytest.mark.anyio
async def test_planner_manager_build_plan_error_no_tasks():
    container = Container()
    container.register_instance(LoggerFactory, LoggerFactory(sinks=[NullSink()]))
    container.register_instance(EventBus, EventBus())
    container.install(MemoryModule())
    container.install(PlannerModule())

    manager = await container.resolve(PlannerManager)
    await manager.create_goal(make_goal("goal3"))

    result = await manager.build_plan("goal3")

    assert result.success is False
    assert result.error is not None
    assert "No tasks provided" in result.error


@pytest.mark.anyio
async def test_planner_manager_build_plan_error_invalid_graph_publishes_plan_failed():
    container = Container()
    container.register_instance(LoggerFactory, LoggerFactory(sinks=[NullSink()]))
    container.register_instance(EventBus, EventBus())
    container.install(MemoryModule())
    container.install(PlannerModule())

    manager = await container.resolve(PlannerManager)
    event_bus = await container.resolve(EventBus)

    events = []

    async def handler(event: Event):
        events.append(event.name)

    event_bus.subscribe(Event, handler)

    await manager.create_goal(make_goal("goal4"))
    manager._task_manager.create(make_task("t1", "goal4", dependencies=("unknown",)))

    result = await manager.build_plan("goal4")

    assert result.success is False
    assert result.error is not None
    assert "unknown task" in result.error
    assert "PlanFailed" in events


@pytest.mark.anyio
async def test_execution_plan_graph_is_deeply_immutable():
    goal = make_goal("goal5")
    tasks = [
        make_task("t1", "goal5"),
        make_task("t2", "goal5", dependencies=("t1",)),
    ]

    planner = Planner(RuleBasedPlanner(ExecutionGraph()))
    plan = planner.plan(goal, tasks)

    with pytest.raises(TypeError):
        plan.graph["t1"] = ()

    with pytest.raises(TypeError):
        plan.graph["t1"][0] = "modified"
