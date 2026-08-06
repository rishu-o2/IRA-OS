# Execution Service Subsystem

The Execution Service is a first-class kernel module introduced in Milestone 16.0. It acts as the definitive bridge between Workflow orchestration and platform-specific Runtime execution.

## Motivation

Prior to the Execution Service, the Workflow subsystem either had to orchestrate execution directly (coupling it to the Runtime) or simulate execution (breaking the pipeline). By introducing an intermediate `ExecutionService`, IRA OS achieves two critical goals:
1. **Platform Agnosticism**: The Workflow engine schedules work universally. It has zero knowledge of Android, Windows, or Cloud APIs.
2. **Security by Design**: The Execution Service forms an impassable chasm between the Workflow engine and the Runtime. A capability *cannot* be executed without first being explicitly authorized by the Security Kernel.

## Canonical Execution Pipeline

Every command targeting the Runtime MUST flow through this exact pipeline:

```mermaid
graph TD
    Brain[Brain] --> Planner[Planner]
    Planner --> Workflow[Workflow Engine]
    Workflow --> Exec[Execution Service]
    Exec --> Sec[Security (Permission Kernel)]
    Sec --> Exec
    Exec --> Run[Runtime Manager]
    Run --> Plat[Android / Platform Runtime]
    Plat --> Cap[Capability]
```

## Security Enforcement: Deny-by-Default

The Execution Service relies on the Permission Kernel, which operates on a strict **Deny-by-Default** policy. If a capability (e.g., `android.device.flashlight`) is not explicitly defined in a loaded policy, the Permission Kernel returns `PermissionState.DENIED`, and the Execution Service immediately aborts the pipeline, publishing an `ExecutionDenied` event.

## Events Published

The Execution Service provides full observability by publishing the following events:
- `ExecutionRequested`
- `ExecutionAuthorized` (or `ExecutionDenied`)
- `ExecutionDispatched`
- `ExecutionSucceeded` (or `ExecutionFailed`)
