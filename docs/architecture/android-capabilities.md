# Android Capabilities Architecture

Android Capabilities in IRA OS are isolated components that interact with the Android platform.

## Principles
1. **Stateless**: Capabilities must not hold any state. State is maintained by the platform (simulated by MockSystemBridge).
2. **Bridge Isolation**: Capabilities MUST NOT call Android APIs directly. All interaction must go through a platform bridge (e.g., `SystemBridge`).
3. **Self-Describing**: Capabilities must declare all metadata (security level, mutation status, rollback support) in their `CapabilityDescriptor`.
4. **Mutation Lifecycle**: Capabilities that change device state (like toggling a flashlight) must support rollbacks and be processed through the `MutationManager`.

## Bridge Action Namespace
Bridges use a dotted namespace convention to future-proof actions.
Example for `SystemBridge`:
- `system.flashlight.on`
- `system.flashlight.off`
- `system.volume.set`
- `system.brightness.set`

## Pipeline Example: Flashlight Control
The flashlight capability proves the end-to-end execution pipeline.
Execution Path:
1. Brain / Workflow
2. ExecutionService
3. MutationManager
4. Security Kernel (Permission check)
5. Runtime
6. AndroidAdapter
7. FlashlightCapability
8. SystemBridge (platform execution)

This pipeline ensures that every state mutation is audited, confirmed (if necessary), and securely executed.
