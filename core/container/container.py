from typing import Type, TypeVar, Any, Dict, List
from .interfaces import ContainerProtocol, ScopeProtocol, Module, Disposable
from .lifetime import Lifetime
from .registration import ServiceDescriptor
from .resolver import Resolver
from .validation import Validator
from .exceptions import RegistrationError

T = TypeVar('T')

class Scope(ScopeProtocol):
    """
    Explicit resolution scope for scoped dependencies.
    """
    def __init__(self, resolver: Resolver):
        self._resolver = resolver
        self._scoped_instances: Dict[Type, Any] = {}
        self._is_disposed = False

    async def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency within this scope."""
        if self._is_disposed:
            raise RuntimeError("Cannot resolve from a disposed scope.")
        return await self._resolver.resolve(interface, self._scoped_instances, set())

    async def try_resolve(self, interface: Type[T]) -> T | None:
        """Attempt to resolve, returning None if missing."""
        try:
            return await self.resolve(interface)
        except Exception:
            return None

    async def dispose(self) -> None:
        """Dispose all scoped instances that implement Disposable and clear the scope cache."""
        if self._is_disposed:
            return
        
        self._is_disposed = True
        
        for instance in self._scoped_instances.values():
            if isinstance(instance, Disposable):
                try:
                    await instance.dispose()
                except Exception:
                    pass
        
        self._scoped_instances.clear()


class Container(ContainerProtocol):
    """
    The IRA OS Dependency Injection Container.
    Kernel object manager ensuring decoupled composition.
    """
    def __init__(self):
        self._registry: Dict[Type, ServiceDescriptor] = {}
        self._resolver = Resolver(self._registry)
        self._is_shutdown = False

    def register_singleton(self, interface: Type, implementation: Type = None) -> None:
        impl = implementation or interface
        self._registry[interface] = ServiceDescriptor(interface, Lifetime.SINGLETON, implementation=impl)

    def register_scoped(self, interface: Type, implementation: Type = None) -> None:
        impl = implementation or interface
        self._registry[interface] = ServiceDescriptor(interface, Lifetime.SCOPED, implementation=impl)

    def register_transient(self, interface: Type, implementation: Type = None) -> None:
        impl = implementation or interface
        self._registry[interface] = ServiceDescriptor(interface, Lifetime.TRANSIENT, implementation=impl)

    def register_instance(self, interface: Type, instance: Any) -> None:
        self._registry[interface] = ServiceDescriptor(interface, Lifetime.SINGLETON, instance=instance)

    def register_factory(self, interface: Type, factory: Any, lifetime: Lifetime) -> None:
        self._registry[interface] = ServiceDescriptor(interface, lifetime, factory=factory)

    def install(self, module: Module) -> None:
        module.configure(self)

    def remove(self, interface: Type) -> None:
        self._registry.pop(interface, None)
        self._resolver.evict_singleton(interface)

    def replace(self, interface: Type, descriptor: ServiceDescriptor) -> None:
        self._registry[interface] = descriptor

    def has(self, interface: Type) -> bool:
        return interface in self._registry

    def create_scope(self) -> ScopeProtocol:
        if self._is_shutdown:
             raise RuntimeError("Cannot create scope from a shutdown container.")
        return Scope(self._resolver)

    async def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency from the root container scope."""
        if self._is_shutdown:
            raise RuntimeError("Cannot resolve from a shutdown container.")
        # Root resolution does not have scoped instances, but we provide an empty dict.
        # If a SCOPED dependency is resolved at the root, it effectively acts as a transient or fails
        # depending on strictness. Here, we just give it an empty transient scope dictionary.
        # In a strict implementation, resolving scoped from root throws an error.
        # We will allow it but warn or isolate it.
        return await self._resolver.resolve(interface, {}, set())

    async def try_resolve(self, interface: Type[T]) -> T | None:
        try:
            return await self.resolve(interface)
        except Exception:
            return None
            
    async def resolve_all(self, interface: Type[T]) -> List[T]:
        """
        Future proofing for array resolution. Currently returns the single registered service 
        if it exists, as list.
        """
        if self.has(interface):
            res = await self.resolve(interface)
            return [res]
        return []

    def validate(self) -> List[str]:
        validator = Validator(self._registry)
        return validator.validate()

    async def shutdown(self) -> None:
        """Dispose all singleton instances that implement Disposable, clear all caches."""
        if self._is_shutdown:
            return
            
        self._is_shutdown = True
        await self._resolver.shutdown()
        self._registry.clear()
