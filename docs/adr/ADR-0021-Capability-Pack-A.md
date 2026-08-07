# ADR-0021: Capability Pack A (Device Controls)

## Status
Accepted

## Date
2026-08-07

## Milestone
Capability Pack A

---

## Context

After proving the capability execution pipeline (Mutation Framework, Security Kernel, and SystemBridge) with individual features (Flashlight, Volume, Brightness), we needed to validate the architecture against a diverse array of mutating device controls. Capability Pack A introduces four capabilities simultaneously to prove the architecture scales safely and elegantly:

1. **Vibrate Capability**: Testing ephemeral mutations.
2. **Do Not Disturb Capability**: Testing OS-level enum abstractions.
3. **Rotation Capability**: Testing multi-dimensional boolean/enum state.
4. **Screen Timeout Capability**: Testing dynamic validation against platform-supported boundaries.

Additionally, we need a way to semantically categorize capabilities for the Brain (e.g. Device, Audio, Display) without loading them into context individually.

---

## Decision

### 1. Ephemeral Mutations
Vibration is an action, not a state. We do not attempt to capture `pre_state` or store its ongoing state. `VibrateCapability` is classified as an **Ephemeral Mutation**. Its rollback uses logical inversion (`system.vibrate.start` -> `system.vibrate.cancel`). The inverse of cancel is a safe no-op since exact duration and waveform of past vibrations cannot be perfectly reproduced.

### 2. OS-Level Generic Enums (DND)
To prevent Android-specific terminology (like `INTERRUPTION_FILTER_PRIORITY`) from leaking above the Android Runtime layer, `DoNotDisturbCapability` defines generic OS-agnostic enums:
`NORMAL`, `PRIORITY`, `ALARMS`, `SILENT`.
The bridge layer is responsible for translating these into Android, Windows, or WearOS specific SDK calls.

### 3. Dynamic Validation (Screen Timeout)
We do not hardcode screen timeout values (e.g., 15s, 30s) in the capability. Instead, the bridge exposes `system.screen_timeout.get_supported` which returns the list of allowed values. The capability dynamically validates user arguments against this list before mutating state. This ensures platform independence (as different OEMs support different timeout steps).

### 4. Semantic Categories
We introduced `CapabilityCategory` to `core.android.models`.
Every `CapabilityDescriptor` now requires a semantic category (`DEVICE`, `DISPLAY`, `AUDIO`, `NETWORK`, etc.). This allows the Brain to discover capabilities by semantic domain rather than loading hundreds of IDs.

Categories applied:
- Flashlight, Battery, Clipboard, Vibrate -> `DEVICE`
- Volume, Do Not Disturb -> `AUDIO`
- Brightness, Rotation, Screen Timeout -> `DISPLAY`

---

## Consequences

### Positive
- The architecture proved robust; zero changes were needed in the `ExecutionService`, `MutationManager`, or `SecurityKernel` to support these four vastly different capabilities.
- Ephemeral mutations are now distinctly separated from persistent state mutations, providing a clear pattern for future actions like taking photos, playing sounds, or showing toasts.
- OS-level generic enums guarantee that the kernel remains completely decoupled from Android SDK terminology.
- `CapabilityCategory` sets up the Brain for scalable semantic discovery of device controls.

### Negative / Trade-offs
- Ephemeral mutation rollback is best-effort (e.g. cancelling a vibration). This is an accepted trade-off since ephemeral actions do not corrupt long-term device state.
- Dynamic validation (Screen Timeout) requires two bridge calls (one to get supported values, one to set). This adds minor latency but guarantees type safety and platform correctness without hardcoded logic.
