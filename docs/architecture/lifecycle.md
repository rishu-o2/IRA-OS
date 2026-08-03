# Lifecycle Manager

The Lifecycle Manager is the kernel component responsible for bootstrapping, starting, monitoring, stopping, restarting, and shutting down IRA OS. It acts as the process manager for all core subsystems, enforcing a strict dependency-based execution order and providing robust failure recovery.

## Architecture

The Lifecycle Manager is composed of three primary modules operating behind a unified `LifecycleManager` facade:

1. **ComponentRegistry**: Maintains the list of registered components and their metadata.
2. **HealthMonitor**: Tracks the immutable `ComponentHealth` state of every registered component.
3. **LifecycleOrchestrator**: Executes lifecycle hooks based on a Directed Acyclic Graph (DAG) of dependencies.

### Dependency Graph & Topological Sort

The execution order of components is determined dynamically at startup using a topological sort algorithm on the component dependencies:

1. **Dependencies Always Win**: A component will never start before its dependencies.
2. **Priority Resolves Ties**: When components have no dependency relationship, the explicit `priority` integer resolves the start order (lower numbers start first).
3. **Circular Dependencies Rejected**: If the DAG contains a cycle, the system throws a `StartupError` before executing any hooks.

### Execution Phases

Components transition through states during the execution of lifecycle phases:

- `CREATED`: Component registered but not yet initialized.
- `BOOTING` -> `BOOTED`: Setup configuration and prepare resources (no active background work).
- `STARTING` -> `RUNNING`: Begin active background work, connect to external services.
- `STOPPING` -> `STOPPED`: Gracefully halt active background work.
- `SHUTTING_DOWN` -> `STOPPED`: Release all resources and clean up.
- `FAILED`: Component threw an unhandled exception or timed out during a phase.

### Lifecycle Hooks

Components interact with the lifecycle via optional async hooks defined in `core.lifecycle.interfaces`:

- `before_boot()` / `boot()` / `after_boot()`
- `before_start()` / `start()` / `after_start()`
- `before_stop()` / `stop()` / `after_stop()`
- `before_shutdown()` / `shutdown()` / `after_shutdown()`

These hooks enable extensive customization (e.g., adding a hook to flush logs before shutdown) without altering the Lifecycle Manager's core logic.

### Failure Recovery

If a component fails to start (throws an exception or times out) and is marked as `critical=True` (default), the `LifecycleOrchestrator` will halt the startup sequence and automatically roll back by calling `stop()` and `shutdown()` on all components that have already successfully started, in reverse order. Non-critical components log a warning and allow startup to continue.

## Future Extensibility

The `ComponentRegistration` model includes `enabled`, `critical`, `startup_timeout`, and `shutdown_timeout` fields to allow fine-grained control and future-proof the API against common service manager requirements.
