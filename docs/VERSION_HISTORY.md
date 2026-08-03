# IRA OS Version History

## v1.0.0 (Milestone 1)
- **Event Bus API frozen.**
- Implemented async-first Event Bus in `core/events/`.
- Supported strongly typed events, isolating execution via `asyncio.gather`.
- Middleware onion pipeline enabled.
- ADR-0001 created.

## v1.1.0 (Milestone 2)
- **Dependency Injection (DI) Container implementation complete.**
- Added `Container`, `Resolver`, `Validator`, and `Scope` core models.
- Support for Singleton, Scoped, and Transient lifetimes.
- Auto-resolving constructor injection using `typing.get_type_hints` and `inspect.signature`.
- Added circular dependency tracking for direct, indirect, and self cycles.
- Included `Disposable` protocol for safely managing resource lifetimes via `Scope.dispose()` and `Container.shutdown()`.
- Verified strict separation of dependencies (no external imports).
