# Dependency Injection (DI) Container

This is the composition root and kernel object manager of IRA OS. It ensures decoupled architecture by controlling object instantiations and lifetimes.

## Features
- **Async-First Construction**: Full support for asynchronous factory functions and classes.
- **Strict Lifetimes**: Supports `Singleton`, `Scoped`, and `Transient` lifetimes.
- **Resource Disposal**: Automated cleanup of resources via `Disposable` protocol.
- **Constructor Injection**: Automatically parses parameter type annotations to resolve dependencies recursively.
- **Circular Dependency Detection**: Validates dependency graphs before runtime to catch dependency cycles and missing registrations.
- **Module Installation**: Register dependencies in logical modules.

## Installation
Ensure you import from `core.container`:
```python
from core.container import Container, Lifetime
from core.container.interfaces import Disposable
```

## Basic Usage
```python
class Database(Disposable):
    def __init__(self):
        self.connected = True
        
    async def dispose(self) -> None:
        self.connected = False
        print("Database disconnected")

class Service:
    def __init__(self, db: Database):
        self.db = db

container = Container()
container.register_singleton(Database)
container.register_transient(Service)

# Resolve asynchronously
service = await container.resolve(Service)

# Shutdown container and dispose singletons
await container.shutdown()
```
