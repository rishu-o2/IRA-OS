# Architecture Decision Record 0002: Dependency Injection Container

## Title
ADR-0002: Dependency Injection Container Architecture

## Status
Accepted

## Date
2026-08-03

## Context
IRA OS is an advanced agentic operating system that requires a highly modular, decoupled architecture. Components such as the brain, memory, tools, and services need to interact without being tightly coupled. Instantiating dependencies directly (e.g., `brain = Brain()`) creates rigid architectures, makes unit testing difficult, and tightly couples modules together. A Dependency Injection (DI) Container is required to act as the kernel's object manager, handling all object construction, lifetimes, and dependency graphs.

## Decision
We will implement an async-first Dependency Injection Container as the composition root of IRA OS.

Key design decisions:
1. **Async-First Architecture**: The container natively supports asynchronous factory functions and asynchronous resolution (`await container.resolve(Type)`).
2. **Explicit Lifetimes**: `Singleton`, `Scoped`, and `Transient` lifetimes are supported to explicitly manage resource lifespans.
3. **Explicit Scopes over ContextVars**: We chose to implement an explicit `Scope` object (`container.create_scope()`) rather than using implicit `contextvars`. This forces developers to pass the scope where needed, improving architectural clarity and avoiding hidden context magic.
4. **Disposal Protocol**: Resource ownership is strict. The container invokes `dispose()` on any singleton or scoped instance that implements the `Disposable` protocol during `container.shutdown()` or `scope.dispose()`.
5. **Graph Validation**: The container can dry-run dependency graphs via `Validator.validate()` to detect missing registrations and circular dependencies (direct, indirect, and self cycles) before runtime execution.
6. **Kernel Independence**: The DI container lives strictly within `core/container/` and has zero dependencies on any higher-level modules (e.g., `brain`, `memory`, `events`).

## Alternatives Considered
- **Third-party DI frameworks (e.g., Dependency Injector, Pydantic)**: Rejected because they add heavy external dependencies, often rely on sync-first patterns, or introduce excessive boilerplate that doesn't fit the IRA OS agentic runtime perfectly.
- **Service Locator Pattern**: Rejected because it hides dependencies rather than explicitly declaring them in constructors, making testing and graph validation significantly harder.

## Consequences
- **Positive**: Complete decoupling of IRA OS modules. Easy testability with mock replacement. Guaranteed resource cleanup. Proactive circular dependency detection.
- **Negative**: Adds a slight overhead to instantiation due to runtime type introspection (`typing.get_type_hints` and `inspect.signature`).

## Future Evolution
The public API has been designed to allow future implementations of lazy resolution (`Lazy[T]`), provider injection (`Provider[T]`), and nested fallback scopes without introducing breaking changes.

## Version
v1.1.0
