# ADR-0016: Execution Service Kernel

**Date:** August 6, 2026
**Status:** Accepted

## Context
During the preparation for Milestone 16 (Non-Destructive Device Control), an architectural review revealed two major flaws in the IRA OS execution pipeline:
1. **Disconnected Workflow Executor:** The `WorkflowExecutor` was a simulated scaffold that did not route commands to the `RuntimeManager`. If left unaddressed, capabilities would either be mocked or bypass workflow orchestration entirely.
2. **Coupling Risk:** Solving #1 by injecting `RuntimeManager` directly into `WorkflowExecutor` would violate the platform-agnostic design of the Workflow engine, tightly coupling generic task orchestration to platform-specific execution mechanisms.
3. **Default-Grant Security:** The `PermissionKernel` defaulted to `PermissionState.GRANTED` for unregistered capabilities. This is unacceptable for an AI OS performing actual state mutations.

## Alternatives Considered
- **Direct Injection:** Inject `RuntimeManager` and `SecurityManager` directly into `WorkflowExecutor`. (Rejected due to tight coupling and violation of Single Responsibility Principle).
- **Execution Within Runtime:** Push security checks down into the `RuntimeManager`. (Rejected because Runtime should only care about executing capabilities, not defining security policy).

## Decision
1. **Introduce `ExecutionService`:** A new, first-class kernel subsystem (`core/execution`) is created. It sits between Workflow and the Security/Runtime kernels.
2. **Workflow Remains Agnostic:** `WorkflowExecutor` now depends solely on `ExecutionService`. It knows nothing of Android or Windows.
3. **Deny-by-Default:** `DefaultPolicyEvaluator` is modified to `DENY` any capability request that lacks an explicit policy.
4. **Strict Pipeline Enforcement:** `ExecutionService` acts as the single authoritative entry point for capability execution. It explicitly requests permission from `SecurityManager` before dispatching to `RuntimeManager`. No subsystem may bypass this flow.

## Consequences
- **Positive:** The execution pipeline is now completely functional, observable, and strictly secure.
- **Positive:** Workflow remains a pure scheduling engine.
- **Positive:** The Deny-by-Default posture ensures zero-day capabilities or unknown plugins cannot accidentally perform mutations.
- **Negative:** Adds one additional hop (latency) in the execution pipeline, though in-memory overhead is negligible.
