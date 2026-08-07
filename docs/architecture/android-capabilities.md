# Android Capabilities Architecture

Android Capabilities in IRA OS are isolated components that interact with the Android platform.

## Core Principles

1. **Stateless**: Capabilities must not hold any state. State is maintained by the platform (simulated by MockSystemBridge in tests).
2. **Bridge Isolation**: Capabilities MUST NOT call Android APIs directly. All interaction flows through a platform bridge (e.g., `SystemBridge`).
3. **Self-Describing**: Capabilities must declare all metadata in their `CapabilityDescriptor` — including `security_level`, `confirmation_level`, `is_mutation`, `supports_rollback`, `audit_required`, and `idempotent`.
4. **Mutation Lifecycle**: Capabilities that change device state must integrate with `MutationManager`. The adapter layer (`DefaultAndroidAdapter`) handles this automatically from the descriptor.
5. **Pre-State Capture**: Mutating capabilities that need precise rollback must embed `"pre_state"` in their bridge response. `rollback()` then uses this to restore exactly.

---

## Bridge Action Namespace

All bridges use a dotted namespace. `SystemBridge` owns the `system.*` namespace:

```
system.flashlight.on
system.flashlight.off
system.flashlight.toggle
system.flashlight.status

system.volume.get
system.volume.set          (args: {"value": int 0–100})
system.volume.up           (args: {"step": int, default 10})
system.volume.down         (args: {"step": int, default 10})
system.volume.mute
system.volume.unmute

# Future (planned)
system.brightness.set
system.rotation.lock
system.vibrate
system.sleep
system.do_not_disturb
```

---

## Capability Execution Pipeline

Every capability — read-only or mutating — flows through the same pipeline:

```
Brain / Workflow
    ↓  ExecutionCommand
MutationManager.process_mutation()
    ↓  ExecutionService.execute()
Security Kernel [Deny-by-Default]
    ↓  authorized
Runtime → DefaultAndroidAdapter.execute()
    ↓
BaseAndroidCapability.execute_action()  [validation]
    ↓
Capability._execute_internal()
    ↓
SystemBridge.execute(action, args)
    ↓
MockSystemBridge  /  Real Android API (future)
```

No step may be bypassed. The `ExecutionService` is the single authoritative entry point.

---

## Implemented Capabilities

| Capability ID | Class | Type | Rollback | ADR |
|---|---|---|---|---|
| `android.hardware.flashlight` | `FlashlightCapability` | Mutation | Logical inversion | ADR-0018 |
| `android.device.volume` | `VolumeCapability` | Mutation | Pre-state precise | ADR-0019 |
| `android.device.battery` | `BatteryCapability` | Read-only | N/A | — |
| `android.device.clipboard.read` | `ClipboardCapability` | Read-only | N/A | — |

---

## Rollback Patterns

### Logical Inversion (Flashlight pattern)
Used when rollback is a pure toggle: `on → off`, `off → on`.
No prior state is needed because the inverse is deterministic.

### Pre-State Capture (Volume pattern)
Used when rollback must restore an exact previous value.
The bridge embeds `"pre_state"` in every mutating response. `rollback()` reads this to restore precisely, or falls back to logical inversion when pre_state is unavailable (failure before bridge execution).

---

## Adding a New Mutable Capability

1. Create `core/android/capabilities/<name>.py` inheriting `BaseAndroidCapability`.
2. Declare the full `CapabilityDescriptor` with all mutation metadata.
3. Implement `_execute_internal()` — call the bridge only.
4. If rollback needs prior values: embed `"pre_state"` in all mutating bridge responses (via `MockSystemBridge` and future real bridge).
5. Implement `supports_rollback()` and `rollback()`.
6. Export from `core/android/capabilities/__init__.py`.
7. Add to `MockSystemBridge`.
8. Write unit tests (`tests/core/android/`) and integration tests (`tests/core/mutation/`).
9. Create an ADR.
