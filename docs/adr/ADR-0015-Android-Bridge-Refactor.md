# ADR-0015: Android Bridge Refactor (Interface Segregation)

**Date:** August 6, 2026
**Status:** Accepted

## Context
During the Milestone 15 implementation, a monolithic `AndroidBridge` interface was introduced to decouple Android execution logic from IRA OS Capabilities. While this successfully isolated the capability models, it resulted in a critical architectural flaw: an Interface Segregation Principle (ISP) violation.
As IRA OS scales to support 100+ capabilities (camera, SMS, contacts, settings, etc.), the single `AndroidBridge` interface would inevitably become a "God Interface" containing hundreds of loosely related methods, severely degrading maintainability, testing isolation, and extensibility.

## Alternatives Considered
1. **Status Quo (Monolithic Bridge):** Easiest short-term solution, but guarantees an unmaintainable bottleneck as the platform layer expands.
2. **Capability-Specific Bridges:** Creating a 1:1 bridge for every capability. This would result in unnecessary boilerplate and fragmented connections to the underlying Android IPC mechanisms.
3. **Domain-Specific Bridges (Selected):** Segmenting the bridge into broad, logical domains (e.g., `SystemBridge`, `NetworkBridge`, `MediaBridge`) mapping closely to native Android Service boundaries.

## Decision
We decided to refactor the Android Bridge layer according to the Interface Segregation Principle. 
- The singular `AndroidBridge` is entirely removed.
- Capabilities are now injected strictly with domain-specific bridge contracts (e.g., `SystemBridge`, `NetworkBridge`, `LocationBridge`, etc.).
- Capabilities do not call concrete Python methods on the bridge (e.g., `get_battery()`). Instead, they invoke a universal `bridge.execute(action="battery.read", arguments={})` interface. This future-proofs the layer, ensuring capabilities remain completely isolated if the bridge implementation shifts from local Python mocks to RPC, Binder IPC, WebSockets, or gRPC.

## Consequences
- **Positive:** Massive improvement to scalability. We can now comfortably scale to 100+ capabilities.
- **Positive:** Capabilities are firmly insulated against any future shifts in how IRA OS communicates with the Android OS.
- **Positive:** Capabilities remain 100% agnostic of platform execution.
- **Negative:** Increased initial boilerplate to scaffold new bridge contracts.

## Future Roadmap
Placeholders have been proactively established for:
- `CameraBridge`, `TelephonyBridge`, `MessagingBridge`, `ContactsBridge`, `MediaBridge`, `NotificationBridge`, `SettingsBridge`, `FilesBridge`, `SensorsBridge`.
These will be implemented in subsequent milestones as the Android capability catalog expands.
