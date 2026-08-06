# ADR-0017: Mutation Lifecycle Framework

**Date:** August 6, 2026
**Status:** Accepted

## Context
As IRA OS transitions from querying state (e.g., Battery, Location) to mutating state (e.g., Flashlight, Volume, SMS), we require a structured lifecycle to ensure destructive changes are secure, auditable, and recoverable. 

A capability that toggles the flashlight is functionally different from one that deletes a file. The OS must provide a platform-agnostic mechanism to:
1. Guarantee user/owner confirmation for sensitive actions.
2. Produce an immutable audit trail of all mutations.
3. Automatically attempt to roll back a capability if an execution step fails or an unexpected side effect occurs.

If we embedded this logic inside the `ExecutionService` or `WorkflowManager`, we would violate the Single Responsibility Principle and bloat the execution path for read-only capabilities. 

## Alternatives Considered
- **Capabilities Own Their Lifecycle:** Push confirmation and auditing into each capability. (Rejected: Results in duplicate code, inconsistent auditing, and prevents central policy enforcement).
- **Security Kernel Expansion:** Make the Security Kernel handle confirmations. (Rejected: Security defines *whether* an action is allowed, not *how* to orchestrate user interaction).
- **Workflow Interception:** Create workflow tasks for confirmation. (Rejected: Capabilities can be invoked outside standard workflows, e.g., direct execution).

## Decision
1. **Introduce `MutationManager`:** A new, first-class kernel subsystem (`core/mutation`) that wraps the execution pipeline for state-changing capabilities.
2. **Pluggable Coordinators:** Introduce `ConfirmationManager` and `AuditManager` to manage pluggable providers/sinks. This prevents the kernel from coupling to UI implementation or database technology.
3. **Capability-driven Rollback:** Capabilities that mutate state must implement the `MutatingCapability` contract, defining `supports_rollback` and `rollback`. The subsystem orchestrates the call, but the capability owns the logic.
4. **Metadata Extension:** Extend `CapabilityMetadata` with `MutationMetadata` (idempotency, confirmation level, destructiveness), allowing the capability definition to declare its requirements declaratively.

## Consequences
- **Positive:** Read-only capabilities maintain a fast-path execution.
- **Positive:** The system can safely implement dangerous capabilities (e.g., financial transactions) because the lifecycle guarantees confirmation and auditing.
- **Positive:** Rollbacks are cleanly decoupled.
- **Negative:** Adds complexity to capability authoring, as developers must define `MutationMetadata` for write operations.
