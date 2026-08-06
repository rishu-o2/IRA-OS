# Workflow Engine Architecture

## Overview
The Workflow Engine is responsible for managing asynchronous work, scheduled work, long-running jobs, retries, cancellations, and multi-step workflows.

## Architecture Position

```
Kernel
├── Identity
├── Memory
├── Planner
├── Brain
└── Workflow Engine     ← This subsystem
        ↓
    Security Layer
        ↓
    Tool Runtime
        ↓
    Platform Layer
```

## Dependency Direction
The Workflow Engine sits below the Brain and above the Security Layer. It never calls the Brain, Identity, or Platform runtimes directly.

## Canonical Pipeline
1. **Workflow Request** - Incoming `WorkflowRequest`
2. **Validation** - Input sanity checks
3. **Schedule Resolution** - Determines if work is immediate or delayed
4. **Queue Management** - Task is enqueued
5. **Execution Dispatch** - Task dequeued and sent to `WorkflowExecutor`
6. **Result Normalization** - Result collected
7. **Publish Events** - Success/failure events published
8. **Workflow Result** - Final `WorkflowResult` returned

## Components

| Component | Responsibility |
|---|---|
| `WorkflowManager` | Pipeline orchestration and lifecycle |
| `WorkflowScheduler` | Schedule constraints and retry policies |
| `WorkflowQueue` | Enqueue/Dequeue operations and tracking |
| `WorkflowExecutor` | Dispatches task to underlying subsystems |

## Public API

Consumers interact with contracts and models only:
```python
manager = await container.resolve(WorkflowManager)
await manager.start()

request = WorkflowRequest(
    workflow_id="wf-1",
    target_capability="android.call",
    arguments={"number": "555-1234"},
)
result = await manager.submit(request)
```
