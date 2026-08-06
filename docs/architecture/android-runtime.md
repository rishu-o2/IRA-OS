# Android Runtime Architecture

## Overview
The Android Runtime is a platform adapter layer in IRA OS. It exposes Android device capabilities to the Tool Runtime as abstract `Capability` objects.

> **Android Runtime does not know what the user wants. It only knows how Android can fulfill a capability request.**

## Architecture Position

```
Kernel
├── Identity
├── Memory
├── Planner
├── Brain
└── Tool Runtime

Platform Layer
└── Android Runtime
        ↓
    Capability Layer
    ├── Call
    ├── SMS
    ├── Camera
    └── ...
```

## Dependency Direction

```
User
  ↓
Brain
  ↓
Tool Runtime
  ↓
Android Runtime          ← Platform Adapter Only
  ↓
Android Capabilities
```

The Android Runtime is a strict downstream consumer of the Tool Runtime. It never flows upward to Brain, Planner, or Memory.

## Responsibilities
- Register Android capabilities into the Tool Runtime.
- Discover available Android capabilities at startup.
- Adapt Tool Runtime execution requests into Android-specific calls.
- Publish lifecycle and capability events.
- Report health and availability.

## Non-Responsibilities
The Android Runtime must **never**:
- Call Brain, Planner, or Memory directly.
- Perform reasoning or planning.
- Manage conversation state.
- Execute platform code belonging to other runtimes (Windows, Linux).

## Component Map

| Component | Purpose |
|---|---|
| `contracts.py` | Defines `AndroidCapability`, `AndroidAdapter`, `AndroidRegistry`, `AndroidRuntime` |
| `models.py` | Immutable models: `CapabilityDescriptor`, `AndroidDeviceInfo`, `AndroidRuntimeStatus`, `CapabilityState` |
| `events.py` | Lifecycle events: `AndroidRuntimeStarted`, `AndroidRuntimeStopped`, `AndroidCapabilityRegistered`, `AndroidCapabilityRemoved`, `AndroidHealthChanged` |
| `adapter.py` | `DefaultAndroidAdapter` — translates Tool Runtime `ExecutionContext` → Android `execute_action()` |
| `registry.py` | `InMemoryAndroidRegistry` — registers, discovers, queries capabilities. Bridges them into the global Tool Runtime registry |
| `health.py` | `AndroidHealthTracker` — independently tracks and publishes health state |
| `manager.py` | `AndroidRuntimeManager` — lifecycle orchestration (start, shutdown) |
| `android_module.py` | DI module wiring |
| `capabilities/` | Per-capability abstract interface files |

## Canonical Capability Interfaces

All capabilities defined in `core/android/capabilities/` are fully abstract:

| File | Capability |
|---|---|
| `call.py` | PhoneCall Capability |
| `sms.py` | SMS Capability |
| `alarm.py` | Alarm Capability |
| `calendar.py` | Calendar Capability |
| `notification.py` | Notification Capability |
| `camera.py` | Camera Capability |
| `contacts.py` | Contacts Capability |
| `files.py` | File System Capability |
| `media.py` | Media Playback Capability |
| `location.py` | Location/GPS Capability |
| `bluetooth.py` | Bluetooth Capability |
| `wifi.py` | Wi-Fi Capability |
| `application.py` | Application Launch Capability |
| `clipboard.py` | Clipboard Capability |
| `battery.py` | Battery Info Capability |
| `device.py` | General Device Info Capability |

## Health Model

Health is tracked by `AndroidHealthTracker` independently from the manager lifecycle. State transitions emit `AndroidHealthChanged` events.

| State | Meaning |
|---|---|
| `STOPPED` | Runtime is not running |
| `INITIALIZING` | Runtime is starting |
| `RUNNING` | Runtime is healthy and available |
| `DEGRADED` | Runtime is running but some capabilities are unavailable |

## Event Model

| Event | When |
|---|---|
| `AndroidRuntimeStarted` | Manager successfully starts |
| `AndroidRuntimeStopped` | Manager shuts down |
| `AndroidCapabilityRegistered` | A new capability is registered |
| `AndroidCapabilityRemoved` | A capability is unregistered |
| `AndroidHealthChanged` | Health state transitions |

## DI Integration

The `AndroidModule` wires:
- `AndroidRegistry` (Singleton)
- `AndroidHealthTracker` (Singleton)
- `AndroidRuntime` (Singleton)

The `AndroidModule` requires the `RuntimeModule` to already be installed so the global `CapabilityRegistry` is available for bridging.

## Public API

All consumers interact with the Android Runtime through its **contracts only**.

```python
# Start the Android Runtime
manager = await container.resolve(AndroidRuntime)
await manager.start()

# Register a capability
registry = await container.resolve(AndroidRegistry)
await registry.register(MyCallCapability())

# Health check (via the AndroidRuntime contract directly)
health = await manager.health_check()
```

**Note:** `AndroidRuntimeManager` and `AndroidHealthTracker` are internal implementation classes. Always resolve `AndroidRuntime` and `AndroidRegistry` from the DI container.

## Extension Strategy

Future Android capabilities:
1. Implement `AndroidCapability` abstract interface.
2. Register with `InMemoryAndroidRegistry`.
3. The `DefaultAndroidAdapter` automatically bridges them into the Tool Runtime.
4. No changes required in Brain, Planner, Memory, or Tool Runtime.
