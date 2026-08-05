# Brain Engine

The Brain Engine is the stateless orchestration layer of IRA OS. It coordinates frozen kernel services to process a request and return a decision without performing execution, platform integration, tool work, memory management, authentication, or AI reasoning.

## Public API

- `BrainManager.process_request(request: BrainRequest) -> BrainResult`

## Pipeline

Each request gets a new immutable `BrainContext` and moves through deterministic stages:

1. Validate request
2. Build conversation context
3. Resolve identity through Identity
4. Analyze and normalize request
5. Retrieve relevant Memory
6. Build planner input
7. Invoke Planner
8. Produce Brain decision

## Planner Boundary

The Brain invokes the frozen Planner through `PlannerManager.build_plan`. It prepares planner input from request context, but it does not create a planning algorithm, execute tasks, or run tools. Requests must reference an existing planner goal with `metadata["goal_id"]` or `metadata["planner_goal_id"]`.

## Events

The Brain publishes request lifecycle events at orchestration boundaries:

- `BrainRequestStarted`
- `BrainRequestCompleted`
- `BrainRequestFailed`

## Kernel Boundary

The Brain depends only on:

- `core.identity`
- `core.memory`
- `core.planner`
- `core.events`
- `core.logging`
- `core.container`
- `core.lifecycle`

## Lifecycle

`BrainManager.start`, `BrainManager.shutdown`, and `BrainManager.health_check` are idempotent. Health reports `RUNNING` only after startup and dependency wiring are available.
