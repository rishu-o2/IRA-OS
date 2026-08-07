# ADR 0018: Flashlight Capability Implementation

## Status
Accepted

## Context
Milestone 16.2 requires the implementation of the first real mutating capability in IRA OS: Android Flashlight Control.
This serves as a proof of concept to validate the end-to-end execution pipeline from the Brain to the platform bridge, including the mutation framework and security kernel.

## Decision
We implement `FlashlightCapability` inheriting from `BaseAndroidCapability` (which now correctly integrates with `MutatingCapability` via `DefaultAndroidAdapter`).
It provides control over the device flashlight via the `SystemBridge`.

### Capability Responsibilities
- Describe its metadata completely (including mutation markers, rollback support, audit requirements).
- Provide the actual rollback implementation (e.g. `system.flashlight.on` -> `system.flashlight.off`).
- Must not maintain any state.
- Must execute all real-world interactions through the `SystemBridge`.

### Bridge Interaction
The `SystemBridge` exposes a unified action namespace `system.*` to allow future-proofing (e.g. `system.volume.set`).
For flashlight, the actions are `system.flashlight.on`, `system.flashlight.off`, `system.flashlight.toggle`, and `system.flashlight.status`.
`MockSystemBridge` simulates a device service maintaining the hardware state during testing.

### Mutation Lifecycle and Rollback
The execution flows natively through `MutationManager` -> `ExecutionService` -> `Runtime` -> `AndroidAdapter` -> `FlashlightCapability`.
If an action fails or a rollback is requested, the mutation manager explicitly calls `rollback()` on the capability via its adapter.
For instance, a successful `on` is rolled back by executing `off`.

### Execution Path
1. Workflow / Brain queues ExecutionCommand
2. ExecutionService passes it to MutationManager
3. Security Kernel checks permissions
4. Runtime invokes AndroidAdapter
5. AndroidAdapter forwards to FlashlightCapability
6. FlashlightCapability forwards to SystemBridge

## Consequences
- Validation of the pipeline ensures we can safely implement high-risk mutations (like sending SMS or deleting files) using the same pattern.
- State is properly delegated to the platform (via bridge).
- Full auditability for real-world changes.
