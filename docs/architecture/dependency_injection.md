# Dependency Injection Container Architecture

## Introduction
The Dependency Injection (DI) Container is the composition root and object manager of the IRA OS kernel. To build a robust, modular, and maintainable operating system, components must not instantiate their dependencies directly. Instead, they declare their dependencies in their constructors, and the DI container resolves them.

This ensures:
- Loose coupling between modules.
- Clean mock replacement during testing.
- Unified lifetime management.

## Lifetime Management
The DI Container manages three distinct lifetime models represented by the `Lifetime` Enum:

1. **Singleton**: Only one instance is created per application lifetime. Subsequent requests return the cached instance. Singleton creation is protected by asynchronous locks (`asyncio.Lock`) to prevent race conditions during concurrent startup.
2. **Scoped**: An explicit resolution scope is created using `container.create_scope()`. Within a scope, only one instance of the scoped service is created. Different scopes receive distinct instances. This is suitable for task or request boundaries.
3. **Transient**: A fresh instance is constructed every time the dependency is requested.

## Resource Ownership & Disposal Lifecycle
The DI container takes ownership of object lifetimes. This means it is also responsible for their disposal.
Classes that allocate unmanaged resources (file handles, database connections, sockets) must implement the `Disposable` protocol by defining an `async def dispose(self) -> None` method.

- **Container Shutdown**: When `await container.shutdown()` is called, all `Singleton` instances that implement `Disposable` are safely disposed, and the singleton cache is cleared. No new scopes or resolutions can be created after shutdown.
- **Scope Disposal**: When `await scope.dispose()` is called, all `Scoped` instances created within that specific scope that implement `Disposable` are safely disposed, and the scope cache is cleared.

## Constructor Injection
The `Resolver` module automatically inspects the constructor (`__init__`) of classes or the parameters of factory functions using `inspect.signature` and `typing.get_type_hints()`. It resolves dependencies recursively:

```
ServiceC -> requires ServiceB -> requires ServiceA
[Container] -> resolves ServiceA -> injects into ServiceB -> injects into ServiceC
```

## Graph Validation and Cycle Detection
To prevent indefinite recursion and runtime failures, the `Validator` can dry-run the dependency graph of all registered services:
- It detects missing dependency registrations.
- It detects direct (A -> A), indirect (A -> B -> C -> A), and pairwise circular dependencies using depth-first search (DFS) with a recursion path stack.
- It returns a validation report containing all detected issues.

## Design for Future Extensibility
The DI Container is designed to support the following without breaking changes to the public API:
- **Lazy Resolution**: Resolving a wrapper `Lazy[T]` that postpones instantiation until accessed.
- **Provider Resolution**: Injecting `Provider[T]` (a factory function) allowing dynamic on-demand generation.
- **Fallback Containers**: Allowing parent-child container hierarchy.

## Examples
### Registering Modules
Logical components register themselves via `Module` implementation:
```python
class DatabaseModule:
    def configure(self, container: ContainerProtocol) -> None:
        container.register_singleton(IDatabase, SQLiteDatabase)
```
Install them globally:
```python
container.install(DatabaseModule())
```
