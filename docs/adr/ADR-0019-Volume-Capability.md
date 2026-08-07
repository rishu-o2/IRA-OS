# ADR-0019: Volume Capability Implementation

## Status
Accepted

## Date
2026-08-07

## Milestone
16.3

---

## Context

Following Milestone 16.2 (Flashlight Capability), Milestone 16.3 implements the Android Volume Control capability. Volume is the second mutating capability and the first one that requires **state-dependent rollback** — unlike the flashlight where `on` can always be inverted to `off`, a volume rollback must restore the **exact previous numeric level**, not merely invert a direction.

This ADR documents the design decisions made to handle state-dependent rollback without introducing stateful instance variables into the capability.

---

## Decision

### 1. Capability ID and Action Namespace

The capability is registered as `android.device.volume`.

All bridge actions use the `system.volume.*` namespace:

| Action | Bridge action | Mutating |
|---|---|---|
| Get current state | `system.volume.get` | No |
| Set absolute level | `system.volume.set` | Yes |
| Raise by step | `system.volume.up` | Yes |
| Lower by step | `system.volume.down` | Yes |
| Mute output | `system.volume.mute` | Yes |
| Unmute output | `system.volume.unmute` | Yes |

### 2. Pre-State Capture Pattern (key innovation)

The Volume Capability must restore exact prior state on rollback, but capabilities must remain **stateless** (no instance variables that persist device state).

**Solution:** Every mutating bridge action (`set`, `up`, `down`, `mute`, `unmute`) returns a `"pre_state"` key in its response dict:

```json
{
  "level": 80,
  "muted": false,
  "pre_state": { "level": 50, "muted": false }
}
```

The `CapabilityResult.data["pre_state"]` is available on the success path. When `rollback(arguments, original_result)` is called:

- If `original_result` is a `CapabilityResult` with `data["pre_state"]` → **precise rollback**: restore exact values via `system.volume.set`.
- If `original_result` is `None` (execution failed before bridge was reached) → **logical inversion**: `volume.up` → `volume.down`, `volume.mute` → `volume.unmute`.

This design is:
- **Stateless**: the capability holds no instance state.
- **Precise**: exact restore from pre-state on the success path.
- **Resilient**: graceful degradation to logical inversion on the failure path.
- **Extensible**: every future capability can use the same pre-state pattern.

### 3. CapabilityDescriptor Metadata

```python
CapabilityDescriptor(
    id="android.device.volume",
    security_level=SecurityLevel.NORMAL,
    confirmation_level=ConfirmationLevel.NONE,
    is_mutation=True,
    supports_rollback=True,
    audit_required=True,
    idempotent=False,
)
```

`SecurityLevel.NORMAL` reflects that volume control is a slightly elevated system capability (louder than a flashlight). `ConfirmationLevel.NONE` because volume changes are low-risk and reversible.

### 4. MockSystemBridge Extension

`MockSystemBridge` maintains independent volume state:

```python
self._volume_level: int = 50   # default 50/100
self._volume_muted: bool = False
```

Volume level is clamped to `[0, 100]`. All mutating actions embed `pre_state` in their response.

### 5. Execution Pipeline (unchanged, validated)

```
Workflow / Brain
    ↓
ExecutionCommand
    ↓
MutationManager.process_mutation()
    ↓
ExecutionService.execute()   [Security Kernel → Deny-by-Default]
    ↓
DefaultAndroidAdapter.execute()
    ↓
VolumeCapability.execute_action()   [BaseAndroidCapability validation]
    ↓
VolumeCapability._execute_internal()
    ↓
MockSystemBridge.execute("system.volume.*")
```

No layer is bypassed. `DefaultAndroidAdapter` translates `CapabilityDescriptor` metadata into `MutationMetadata` automatically — no changes to the adapter were required.

### 6. Rollback Contract

| Action | Precise (pre_state present) | Approximate (no pre_state) |
|---|---|---|
| `volume.set` | `volume.set(pre_state.level)` | no-op (value unknown) |
| `volume.up` | `volume.set(pre_state.level)` | `volume.down(step)` |
| `volume.down` | `volume.set(pre_state.level)` | `volume.up(step)` |
| `volume.mute` | `volume.unmute` if pre_state.muted=False | `volume.unmute` |
| `volume.unmute` | `volume.mute` if pre_state.muted=True | `volume.mute` |

---

## Consequences

### Positive
- Pre-state capture pattern is now the canonical approach for all future mutable controls.
- Zero changes to `DefaultAndroidAdapter`, `MutationManager`, `BaseAndroidCapability`, or `CapabilityDescriptor`. The architecture absorbed the new capability without modification.
- Every future capability (Brightness, Wi-Fi, Bluetooth, etc.) follows identical patterns.

### Negative / Trade-offs
- `volume.set` rollback without pre_state is a no-op. This edge case only occurs when execution fails before the bridge is reached (e.g. argument validation error). In practice, if validation fails, no hardware state changed, so the no-op is semantically correct.

### No Technical Debt Introduced
- No global state.
- No static variables.
- No Android API imports.
- No subsystem boundary violations.
