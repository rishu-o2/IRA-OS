# Tool Runtime Subsystem

The Tool Runtime is the centralized execution orchestration layer for IRA OS. It receives an `ExecutionRequest` from the Brain and executes it through a registered `Capability` without planning, making AI decisions, or containing any platform-specific logic.

## Architecture

The runtime executes exactly one deterministic pipeline:
1. **Execution Request**: The request is received from the Brain.
2. **Validation**: Validates the request shape and semantic constraints.
3. **Capability Lookup**: Discovers the correct capability via the `CapabilityRegistry`.
4. **Dispatch**: Routes the request to the capability via the `Dispatcher`.
5. **Execute**: Invokes the capability via the `Executor`.
6. **Normalize Result**: Captures standard output and runtime exceptions.
7. **Publish Events**: Publishes the outcome to the `EventBus`.
8. **Execution Result**: Returns an immutable `ExecutionResult`.

## Components
- `RuntimeManager`: Entry point and lifecycle orchestrator.
- `CapabilityRegistry`: Memory registry for registering and looking up capabilities.
- `RuntimeDispatcher`: Determines routing (exact match).
- `RuntimeExecutor`: Safe invocation boundary to catch exceptions.
- `RuntimeValidator`: Execution and argument validation.

## Constraints
This package does NOT implement Android, Windows, Browser tools, or Plugins. It defines the abstract `Capability` interface that future platforms will implement.
