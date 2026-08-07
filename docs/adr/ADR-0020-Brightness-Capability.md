# ADR-0020: Brightness Capability Implementation

## Status
Accepted

## Date
2026-08-07

## Milestone
16.4

---

## Context

Following Milestone 16.3 (Volume Capability), Milestone 16.4 implements the Android Screen Brightness Control capability. Brightness is the third mutable device capability and serves a specific architectural purpose: validating that the pre-state capture rollback pattern (introduced in Milestone 16.3 for Volume) is truly reusable across different capability domains — not incidental to Volume.

This ADR also documents new concerns not present in earlier capabilities:
- **Type validation**: Brightness accepts a numeric `value` argument. Non-numeric inputs (`"high"`, `None`, booleans coerced to int) must be rejected at the capability layer before they reach the bridge.
- **Auto mode state**: Brightness has a two-dimensional state (level + auto mode), both of which must be captured in `pre_state` for complete rollback.

---

## Decision

### 1. Capability ID and Action Namespace

The capability is registered as `android.device.brightness`.

All bridge actions use the `system.brightness.*` namespace:

| Action | Bridge action | Mutating |
|---|---|---|
| Get current state | `system.brightness.get` | No |
| Set absolute level | `system.brightness.set` | Yes |
| Raise by step | `system.brightness.increase` | Yes |
| Lower by step | `system.brightness.decrease` | Yes |
| Enable auto-brightness | `system.brightness.auto_on` | Yes |
| Disable auto-brightness | `system.brightness.auto_off` | Yes |

### 2. Pre-State Capture (canonical pattern, revalidated)

Every mutating bridge action returns a `"pre_state"` key containing the complete brightness state before mutation:

```json
{
  "level": 80,
  "auto": false,
  "pre_state": { "level": 50, "auto": true }
}
```

`CapabilityResult.data["pre_state"]` is available on the success path. When `rollback(arguments, original_result)` is called:

- If `original_result` is a `CapabilityResult` with `data["pre_state"]` → **precise rollback**: restore exact `level` via `system.brightness.set`, and exact `auto` mode via `system.brightness.auto_on` / `auto_off`.
- If `original_result` is `None` (execution failed before the bridge was reached) → **logical inversion**: `increase` → `decrease`, `auto_on` → `auto_off`, `auto_off` → `auto_on`. `set` is a safe no-op (prior level unknown).

### 3. Input Validation (new in 16.4)

The capability validates the `value` argument for `brightness.set` **before** delegating to the bridge:

1. **Presence check**: `"value"` key must exist in `arguments`.
2. **Type check**: `value` must be `int` or `float`. Non-numeric types (`str`, `None`, `bool` coerced from Python) raise `InvalidArgumentError`.
3. **Range check**: `int(value)` must be in `[0, 100]`.

This is consistent with the principle that capabilities are the last line of type-safe defense before hardware interaction.

> **Note:** `bool` in Python is a subclass of `int`. We accept `True → 1` and `False → 0`. This is intentional — it is semantically valid (though unusual) and prevents unnecessary complexity.

### 4. CapabilityDescriptor Metadata

```python
CapabilityDescriptor(
    id="android.device.brightness",
    security_level=SecurityLevel.LOW,
    confirmation_level=ConfirmationLevel.NONE,
    is_mutation=True,
    supports_rollback=True,
    audit_required=True,
    idempotent=False,
)
```

`SecurityLevel.LOW` because brightness adjustment carries no privacy or safety risk. `ConfirmationLevel.NONE` because brightness changes are immediate, low-risk, and completely reversible.

### 5. MockSystemBridge Extension

`MockSystemBridge` gains independent brightness state:

```python
self._brightness_level: int = 50   # default 50/100
self._brightness_auto: bool = True  # auto-brightness enabled by default
```

Level is clamped to `[0, 100]`. All mutating actions embed `pre_state: {level, auto}` in their response.

### 6. Execution Pipeline (unchanged, validated again)

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
BrightnessCapability.execute_action()   [BaseAndroidCapability validation]
    ↓
BrightnessCapability._execute_internal()
    ↓
MockSystemBridge.execute("system.brightness.*")
```

No layer is bypassed. `DefaultAndroidAdapter` translates `CapabilityDescriptor` metadata into `MutationMetadata` automatically — no changes to the adapter were required.

### 7. Rollback Contract

| Action | Precise (pre_state present) | Approximate (no pre_state) |
|---|---|---|
| `brightness.set` | `brightness.set(pre_state.level)` | no-op (level unknown) |
| `brightness.increase` | `brightness.set(pre_state.level)` | `brightness.decrease(step)` |
| `brightness.decrease` | `brightness.set(pre_state.level)` | `brightness.increase(step)` |
| `brightness.auto_on` | `brightness.auto_off` if `pre_state.auto=False` | `brightness.auto_off` |
| `brightness.auto_off` | `brightness.auto_on` if `pre_state.auto=True` | `brightness.auto_on` |

---

## Consequences

### Positive
- Pre-state capture pattern is confirmed as the canonical, reusable approach for all numeric mutable controls. No pattern changes required between Volume (16.3) and Brightness (16.4).
- Type validation in the capability layer (not the bridge) ensures invalid inputs are caught before any hardware interaction occurs.
- Zero changes to `DefaultAndroidAdapter`, `MutationManager`, `BaseAndroidCapability`, or `CapabilityDescriptor`. The architecture absorbed the new capability without modification.
- Two-dimensional state (`level` + `auto`) in `pre_state` proves the pattern scales to multi-field state without requiring structural changes.

### Negative / Trade-offs
- `brightness.set` rollback without `pre_state` is a no-op. This edge case only occurs when execution fails before the bridge is reached (e.g. argument validation error). In practice, if validation fails, no hardware state changed, so the no-op is semantically correct.

### No Technical Debt Introduced
- No global state.
- No static variables.
- No Android API imports.
- No subsystem boundary violations.
