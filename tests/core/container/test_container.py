import asyncio
from contextlib import contextmanager
from core.container import Container, Lifetime, CircularDependencyError, ResolutionError, ValidationError
from core.container.interfaces import Disposable

@contextmanager
def assert_raises(exc_type):
    try:
        yield
    except exc_type:
        pass
    except Exception as e:
        raise AssertionError(f"Expected {exc_type.__name__}, but got {type(e).__name__}")
    else:
        raise AssertionError(f"Expected {exc_type.__name__}, but no exception was raised")

class IServiceA:
    pass

class ServiceA(IServiceA):
    pass

class IServiceB:
    pass

class ServiceB(IServiceB):
    def __init__(self, a: IServiceA):
        self.a = a

class IServiceC:
    pass

class ServiceC(IServiceC):
    def __init__(self, b: IServiceB):
        self.b = b

class MockServiceA(IServiceA):
    pass

class DisposableResource(Disposable):
    def __init__(self):
        self.disposed = False
        
    async def dispose(self) -> None:
        self.disposed = True

def test_event_bus_not_touched():
    # Placeholder to assert we are decoupled
    pass

def test_container_registration_and_validation():
    container = Container()
    container.register_transient(IServiceA, ServiceA)
    container.register_transient(IServiceB, ServiceB)
    container.register_transient(IServiceC, ServiceC)
    
    errors = container.validate()
    assert len(errors) == 0

def test_container_validation_missing():
    container = Container()
    # Missing IServiceA registration
    container.register_transient(IServiceB, ServiceB)
    
    errors = container.validate()
    assert len(errors) == 1
    assert "Missing dependency" in errors[0]

class GlobalCycle2:
    pass

class GlobalCycle1:
    def __init__(self, c2: GlobalCycle2):
        pass

class GlobalCycle2:
    def __init__(self, c1: GlobalCycle1):
        pass

def test_container_validation_cycle():
    container = Container()
    
    container.register_transient(GlobalCycle1)
    container.register_transient(GlobalCycle2)
    
    errors = container.validate()
    assert len(errors) > 0
    assert "Circular dependency" in errors[0]

# --- Missing Cycle Tests ---

class SelfCycle:
    def __init__(self, self_dep: 'SelfCycle'):
        pass

def test_validation_self_cycle():
    container = Container()
    container.register_transient(SelfCycle)
    errors = container.validate()
    assert len(errors) > 0
    assert "Circular dependency" in errors[0]

def test_runtime_self_cycle():
    container = Container()
    container.register_transient(SelfCycle)
    
    async def run_test():
        with assert_raises(CircularDependencyError):
            await container.resolve(SelfCycle)
    asyncio.run(run_test())

class IndirectC:
    pass

class IndirectB:
    def __init__(self, c: IndirectC):
        pass

class IndirectA:
    def __init__(self, b: IndirectB):
        pass

class IndirectC:
    def __init__(self, a: IndirectA):
        pass

def test_validation_indirect_cycle():
    container = Container()
    container.register_transient(IndirectA)
    container.register_transient(IndirectB)
    container.register_transient(IndirectC)
    
    errors = container.validate()
    assert len(errors) > 0
    assert "Circular dependency" in errors[0]

def test_runtime_indirect_cycle():
    container = Container()
    container.register_transient(IndirectA)
    container.register_transient(IndirectB)
    container.register_transient(IndirectC)
    
    async def run_test():
        with assert_raises(CircularDependencyError):
            await container.resolve(IndirectA)
    asyncio.run(run_test())

# ---------------------------

def test_singleton_lifetime():
    container = Container()
    container.register_singleton(IServiceA, ServiceA)
    
    async def run_test():
        a1 = await container.resolve(IServiceA)
        a2 = await container.resolve(IServiceA)
        assert a1 is a2

    asyncio.run(run_test())

def test_transient_lifetime():
    container = Container()
    container.register_transient(IServiceA, ServiceA)
    
    async def run_test():
        a1 = await container.resolve(IServiceA)
        a2 = await container.resolve(IServiceA)
        assert a1 is not a2

    asyncio.run(run_test())

def test_scoped_lifetime():
    container = Container()
    container.register_scoped(IServiceA, ServiceA)
    
    async def run_test():
        scope1 = container.create_scope()
        scope2 = container.create_scope()
        
        a1 = await scope1.resolve(IServiceA)
        a2 = await scope1.resolve(IServiceA)
        
        b1 = await scope2.resolve(IServiceA)
        
        assert a1 is a2
        assert a1 is not b1

    asyncio.run(run_test())

def test_nested_constructor_injection():
    container = Container()
    container.register_transient(IServiceA, ServiceA)
    container.register_transient(IServiceB, ServiceB)
    container.register_transient(IServiceC, ServiceC)
    
    async def run_test():
        c = await container.resolve(IServiceC)
        assert isinstance(c, ServiceC)
        assert isinstance(c.b, ServiceB)
        assert isinstance(c.b.a, ServiceA)

    asyncio.run(run_test())

def test_async_factory():
    container = Container()
    
    async def factory_a() -> IServiceA:
        await asyncio.sleep(0.01)
        return ServiceA()
        
    container.register_factory(IServiceA, factory_a, Lifetime.TRANSIENT)
    
    async def run_test():
        a = await container.resolve(IServiceA)
        assert isinstance(a, ServiceA)

    asyncio.run(run_test())

def test_circular_dependency_runtime():
    container = Container()
    
    container.register_transient(GlobalCycle1)
    container.register_transient(GlobalCycle2)
    
    async def run_test():
        with assert_raises(CircularDependencyError):
            await container.resolve(GlobalCycle1)

    asyncio.run(run_test())

def test_mock_replacement():
    container = Container()
    container.register_singleton(IServiceA, ServiceA)
    container.register_instance(IServiceA, MockServiceA())
    
    async def run_test():
        a = await container.resolve(IServiceA)
        assert isinstance(a, MockServiceA)

    asyncio.run(run_test())

def test_async_singleton_safety():
    container = Container()
    
    call_count = 0
    
    async def slow_factory() -> IServiceA:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return ServiceA()
        
    container.register_factory(IServiceA, slow_factory, Lifetime.SINGLETON)
    
    async def run_test():
        # Spawn multiple concurrent resolutions
        tasks = [container.resolve(IServiceA) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Must only call factory once
        assert call_count == 1
        
        # All tasks must get the exact same instance
        first = results[0]
        for r in results:
            assert r is first

    asyncio.run(run_test())

# --- Disposal and Removal Tests ---

def test_scope_disposal():
    container = Container()
    container.register_scoped(DisposableResource)
    
    async def run_test():
        scope = container.create_scope()
        resource = await scope.resolve(DisposableResource)
        
        assert not resource.disposed
        await scope.dispose()
        assert resource.disposed
        
        with assert_raises(RuntimeError):
            await scope.resolve(DisposableResource)

    asyncio.run(run_test())

def test_container_shutdown():
    container = Container()
    container.register_singleton(DisposableResource)
    
    async def run_test():
        resource = await container.resolve(DisposableResource)
        
        assert not resource.disposed
        await container.shutdown()
        assert resource.disposed
        
        with assert_raises(RuntimeError):
            await container.resolve(DisposableResource)
            
        with assert_raises(RuntimeError):
            container.create_scope()

    asyncio.run(run_test())

def test_container_remove_singleton():
    container = Container()
    container.register_singleton(IServiceA, ServiceA)
    
    async def run_test():
        instance1 = await container.resolve(IServiceA)
        
        # Remove the registration
        container.remove(IServiceA)
        
        # Subsequent resolve should fail
        with assert_raises(ResolutionError):
            await container.resolve(IServiceA)
            
        # Re-register and ensure we get a new instance, not the old cached one
        container.register_singleton(IServiceA, ServiceA)
        instance2 = await container.resolve(IServiceA)
        
        assert instance1 is not instance2

    asyncio.run(run_test())
