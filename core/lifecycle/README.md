# Lifecycle Manager

The Lifecycle Manager is the kernel's process manager for IRA OS. It is responsible for orchestrating the boot, start, stop, shutdown, and restart sequences of all registered components.

## Key Features

- **Dependency-Based Ordering**: Components are started based on a topological sort of their dependencies.
- **Priority Resolution**: When components have no explicit dependencies, their order is determined by a numerical `priority`.
- **Lifecycle Hooks**: Components can implement optional hooks (`before_boot`, `after_boot`, `before_start`, `after_start`, etc.).
- **Failure Recovery**: If a critical component fails to start, the orchestrator automatically rolls back (shuts down/stops) already started components.
- **Health Tracking**: Maintains an immutable snapshot of each component's state (`ComponentHealth`).

## Usage

```python
from core.lifecycle import LifecycleManager

manager = LifecycleManager()

# Registering a component
manager.register(
    name="Logger",
    instance=my_logger_instance,
    priority=10
)

# Registering a dependent component
manager.register(
    name="Database",
    instance=my_db_instance,
    dependencies=["Logger"],
    critical=True
)

# Boot phase
await manager.boot()

# Start phase
await manager.start()
```

## Bootstrap

The `Bootstrap` class can be used to construct the base IRA OS kernel components and return a pre-configured `LifecycleManager`.

```python
from core.lifecycle import Bootstrap

lifecycle = Bootstrap.build()
```
