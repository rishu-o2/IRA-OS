# Task & Workflow Engine

## Overview
The Workflow Engine is a core subsystem of IRA OS responsible for orchestrating task execution, delays, recurring schedules, and multi-step workflows.

> **The Workflow Engine decides WHEN and HOW LONG tasks happen. It leaves WHAT to the Brain, and HOW to the Tool Runtime.**

## Architecture Position

```
Brain
  ↓
Workflow Engine          ← Orchestration
  ↓
Permission Kernel
  ↓
Tool Runtime
```

## Canonical Pipeline

1. **Workflow Request**
2. **Validation**
3. **Schedule Resolution**
4. **Queue Management**
5. **Execution Dispatch**
6. **Result Normalization**
7. **Publish Events**
8. **Workflow Result**

## Responsibilities
- Task scheduling and delay management
- Task queuing
- Workflow lifecycle and state management
- Cancellation, pause, resume
- Retry and timeout tracking
- Event publication

## Non-Responsibilities
- Does NOT execute tools or platform logic
- Does NOT reason or plan
- Does NOT evaluate permissions

## Components
| Component | Contract | Scaffolding Implementation |
|---|---|---|
| Manager | `WorkflowManager` | `WorkflowManagerImpl` |
| Scheduler | `WorkflowScheduler` | `DefaultWorkflowScheduler` |
| Queue | `WorkflowQueue` | `InMemoryWorkflowQueue` |
| Executor | `WorkflowExecutor` | `DefaultWorkflowExecutor` |
