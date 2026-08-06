# Architecture Decision Record 0011: Android Runtime

## Title
ADR-0011: Android Runtime

## Status
Accepted (Frozen for API)

## Date
2026-08-06

## Context
The Brain Engine (Milestone 9) and Tool Runtime (Milestone 10) are now API-frozen. The OS can decide what to do and orchestrate execution, but has no ability to interact with a physical Android device. Milestone 11 defines how Android capabilities are introduced into IRA OS without violating the clean separation between Kernel, Brain, Tool Runtime, and platform-specific execution.

## Decision
Introduce the Android Runtime as a platform adapter layer, positioned strictly beneath the Tool Runtime in the dependency hierarchy.

The key design principle:
> **Android Runtime does not know what the user wants. It only knows how Android can fulfill a capability request.**

### Structural Decisions Made

1. **Capabilities Package**: Capabilities are organized into a dedicated `core/android/capabilities/` package instead of a monolithic `capability.py` to support scalability.

2. **Adapter Layer**: A `DefaultAndroidAdapter` translation layer sits between the `AndroidCapability` interface and the Tool Runtime's `Capability` interface. This isolates Android-specific execution semantics from the Tool Runtime without requiring any changes to it.

3. **Contracts Separation**: All abstract interfaces (`AndroidCapability`, `AndroidAdapter`, `AndroidRegistry`, `AndroidRuntime`) are consolidated in `contracts.py`, mirroring mature framework patterns.

4. **Independent Health Tracking**: `health.py` is separated from `manager.py` to allow them to evolve independently.

5. **Event Naming**: Events use lifecycle-oriented naming (`AndroidRuntimeStarted`, `AndroidCapabilityRegistered`, `AndroidHealthChanged`) for consistency.

6. **Model Scope**: Android models are scoped precisely to Android runtime state (`CapabilityDescriptor`, `AndroidDeviceInfo`, `AndroidRuntimeStatus`, `CapabilityState`). They do not duplicate Tool Runtime execution request/result models.

## Rationale
- Strict dependency direction ensures the Kernel remains completely platform-independent.
- Abstract capabilities mean the Tool Runtime never needs to change when new Android features are added.
- The adapter pattern prevents Android-specific execution semantics from leaking into the Tool Runtime.

## Consequences
- Positive: Android capabilities can be added, removed, or updated without affecting Brain, Planner, or Memory.
- Positive: The same pattern (`PlatformAdapter → CapabilityRegistry → Tool Runtime`) is directly reusable for Windows, Linux, and Web runtimes.
- Negative: Each capability requires an implementation adapter wrapper in the relevant milestone.

## Future Milestones
- **Milestone 11.2**: Implement concrete capability implementations (Call, SMS, Camera, etc.)
- **Milestone 12**: Windows Runtime using the same pattern.
- **Milestone 13+**: Web Runtime, Linux Runtime.

## API Freeze Refinements (Milestone 11.2.1)
- `AndroidRuntime` contract promoted to a proper enforcing ABC with `@abstractmethod` on `start()`, `shutdown()`, and `health_check()`.
- `AndroidRuntimeManager.health_check()` implemented by delegating to `AndroidHealthTracker`.
- Unused imports removed from `models.py`.
- Concrete implementation classes (`AndroidRuntimeManager`, `AndroidHealthTracker`) removed from public `__all__`.
- `capabilities/__init__.py` populated with `__all__` for all 16 abstract capability interfaces.
- Redundant `ABC` and `abstractmethod` imports removed from individual capability files.
- Comprehensive regression test suite added: `tests/core/android/test_android.py` (48 tests covering contracts, models, events, exceptions, lifecycle, registry, adapter, health, DI, public API, import safety).
