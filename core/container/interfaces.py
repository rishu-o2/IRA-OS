from typing import Protocol, Type, TypeVar, Any, runtime_checkable

T = TypeVar('T')

@runtime_checkable
class Disposable(Protocol):
    """
    Protocol for objects that hold resources requiring explicit cleanup.
    Any singleton or scoped instance implementing this protocol will have
    dispose() called during Container.shutdown() or Scope.dispose().
    """
    async def dispose(self) -> None:
        """Release resources held by this object."""
        ...

class Module(Protocol):
    """
    Protocol for a Container Module.
    Allows logical grouping of registrations.
    """
    def configure(self, container: 'ContainerProtocol') -> None:
        """Called when the module is installed into the container."""
        ...

class ScopeProtocol(Protocol):
    """
    Protocol for an explicit resolution scope.
    """
    async def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency from this scope asynchronously."""
        ...
        
    async def try_resolve(self, interface: Type[T]) -> T | None:
        """Attempt to resolve a dependency, returning None if not found."""
        ...

    async def dispose(self) -> None:
        """Dispose all scoped instances that implement Disposable and clear the scope cache."""
        ...

class ContainerProtocol(ScopeProtocol, Protocol):
    """
    Protocol for the Dependency Injection Container.
    """
    def register_singleton(self, interface: Type, implementation: Type = None) -> None:
        ...

    def register_scoped(self, interface: Type, implementation: Type = None) -> None:
        ...

    def register_transient(self, interface: Type, implementation: Type = None) -> None:
        ...

    def register_instance(self, interface: Type, instance: Any) -> None:
        ...

    def register_factory(self, interface: Type, factory: Any, lifetime: 'Lifetime') -> None:
        ...

    def install(self, module: Module) -> None:
        ...
        
    def create_scope(self) -> ScopeProtocol:
        ...

    async def shutdown(self) -> None:
        """Dispose all singleton instances that implement Disposable, clear all caches."""
        ...
