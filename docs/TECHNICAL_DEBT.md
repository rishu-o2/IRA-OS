# IRA OS Technical Debt Register

This document tracks known architectural compromises, deferred features, and potential risks in the codebase.

---

## TD-001: Event Bus - Wildcard Subscriptions
- **Status**: Open
- **Description**: The Event Bus currently only routes events based on exact type matches (`Type[Event]`). Wildcard or polymorphic subscriptions (e.g., subscribing to a base `BaseEvent` and receiving all subclasses) are not supported.
- **Impact**: Low
- **Resolution Path**: Update `Dispatcher` to perform `issubclass()` checks during routing if requested.

## TD-002: Event Bus - Persistent Events
- **Status**: Open
- **Description**: Events are held only in memory. If the system crashes, unprocessed events are lost.
- **Impact**: Medium (when distributed events are introduced)
- **Resolution Path**: Add a `PersistentDispatcher` or middleware that writes events to a WAL (Write-Ahead Log) before dispatching.

---

## TD-004: DI Container - Captive Dependency Detection
- **Status**: Open
- **Description**: The DI Container does not prevent a Singleton from capturing a Scoped or Transient dependency, which effectively promotes the shorter-lived dependency to a Singleton.
- **Impact**: Medium
- **Resolution Path**: Add lifetime hierarchy validation during `Validator.validate()`.

## TD-006: DI Container - Introspection Caching
- **Status**: Open
- **Description**: `inspect.signature` and `typing.get_type_hints` are invoked on every uncached resolution, which can degrade performance for high-frequency Transient resolutions.
- **Impact**: Low
- **Resolution Path**: Add a method-level cache for introspected signatures inside `Resolver`.

## TD-007: DI Container - Nested Scopes
- **Status**: Open
- **Description**: `Scope` does not support nested child scopes (e.g., Session Scope containing Request Scopes). Scopes are flat and fall back only to the global Singleton cache.
- **Impact**: Low
- **Resolution Path**: Implement `Scope.create_child_scope()` and hierarchical resolution.

## TD-008: DI Container - Validation Deduplication
- **Status**: Open
- **Description**: `Validator` may report the same cycle or missing dependency multiple times because it dry-runs every registered type independently as a root.
- **Impact**: Low
- **Resolution Path**: Deduplicate validation errors in `validate()` before returning the final report list.
