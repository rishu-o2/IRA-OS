import inspect
import asyncio
from typing import Type, Any, Dict, Set, Callable
from .exceptions import CircularDependencyError, ResolutionError
from .registration import ServiceDescriptor
from .lifetime import Lifetime

class Resolver:
    """
    Core dependency resolution engine.
    Supports asynchronous construction and circular dependency detection.
    """
    def __init__(self, registry: Dict[Type, ServiceDescriptor]):
        self._registry = registry
        self._singleton_instances: Dict[Type, Any] = {}
        self._singleton_locks: Dict[Type, asyncio.Lock] = {}
        # We use a global lock dict for singletons to avoid race conditions during first creation.

    def _get_singleton_lock(self, interface: Type) -> asyncio.Lock:
        if interface not in self._singleton_locks:
            self._singleton_locks[interface] = asyncio.Lock()
        return self._singleton_locks[interface]

    def evict_singleton(self, interface: Type) -> None:
        self._singleton_instances.pop(interface, None)
        self._singleton_locks.pop(interface, None)

    async def shutdown(self) -> None:
        from .interfaces import Disposable
        for instance in self._singleton_instances.values():
            if isinstance(instance, Disposable):
                try:
                    await instance.dispose()
                except Exception:
                    pass
        self._singleton_instances.clear()
        self._singleton_locks.clear()

    async def resolve(self, interface: Type, scoped_instances: Dict[Type, Any], resolution_chain: Set[Type]) -> Any:
        """
        Resolves a dependency, respecting lifetimes and detecting cycles.
        """
        interface_name = getattr(interface, '__name__', str(interface))
        
        if interface in resolution_chain:
            chain_str = " -> ".join([getattr(t, '__name__', str(t)) for t in resolution_chain]) + f" -> {interface_name}"
            raise CircularDependencyError(f"Circular dependency detected: {chain_str}")

        if interface not in self._registry:
            raise ResolutionError(f"No registration found for {interface_name}")

        descriptor = self._registry[interface]

        # 1. Check if already built
        if descriptor.lifetime == Lifetime.SINGLETON:
            if interface in self._singleton_instances:
                return self._singleton_instances[interface]
        elif descriptor.lifetime == Lifetime.SCOPED:
            if interface in scoped_instances:
                return scoped_instances[interface]

        # Instance registration is treated as a pre-built Singleton
        if descriptor.instance is not None:
            return descriptor.instance

        # 2. Build it
        new_resolution_chain = resolution_chain | {interface}

        if descriptor.lifetime == Lifetime.SINGLETON:
            lock = self._get_singleton_lock(interface)
            async with lock:
                # Double-checked locking
                if interface in self._singleton_instances:
                    return self._singleton_instances[interface]
                instance = await self._build(descriptor, scoped_instances, new_resolution_chain)
                self._singleton_instances[interface] = instance
                return instance
        else:
            instance = await self._build(descriptor, scoped_instances, new_resolution_chain)
            if descriptor.lifetime == Lifetime.SCOPED:
                scoped_instances[interface] = instance
            return instance

    async def _build(self, descriptor: ServiceDescriptor, scoped_instances: Dict[Type, Any], resolution_chain: Set[Type]) -> Any:
        target = descriptor.factory if descriptor.factory else descriptor.implementation
        
        if target is None:
            raise ResolutionError(f"ServiceDescriptor for {descriptor.interface} lacks implementation or factory.")

        # Introspect dependencies
        sig = inspect.signature(target)
        try:
            from typing import get_type_hints
            import sys
            hint_target = target.__init__ if isinstance(target, type) else target
            globalns = sys.modules[target.__module__].__dict__ if hasattr(target, '__module__') and target.__module__ in sys.modules else {}
            type_hints = get_type_hints(hint_target, globalns=globalns)
        except Exception:
            type_hints = {}
            
        kwargs = {}
        
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
                
            param_type = type_hints.get(name, param.annotation)
            
            if param_type == inspect.Parameter.empty:
                raise ResolutionError(f"Parameter '{name}' in {target.__name__} lacks type annotation.")
                
            try:
                kwargs[name] = await self.resolve(param_type, scoped_instances, resolution_chain)
            except CircularDependencyError:
                raise
            except ResolutionError as e:
                if param.default != inspect.Parameter.empty:
                    kwargs[name] = param.default
                else:
                    raise ResolutionError(f"Cannot resolve parameter '{name}' of type {param_type} for {target.__name__}") from e

        if inspect.iscoroutinefunction(target):
            return await target(**kwargs)
        else:
            return target(**kwargs)
