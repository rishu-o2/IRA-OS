# Architecture Decision Record 0012: Permission & Security Kernel

## Title
ADR-0012: Permission & Security Kernel

## Status
Accepted (Architecture Scaffolding — Awaiting Policy Implementation)

## Date
2026-08-06

## Context
The Brain, Tool Runtime, and Android Runtime are now API-frozen. IRA OS can plan, execute, and interface with platform capabilities. However, there is no authorization layer governing which capabilities can be executed and under what conditions. Milestone 12 introduces IRA's own security kernel as a platform-independent, Brain-independent authorization gate.

This is **not** Android permissions. This is **not** OS permissions. This is IRA's own security policy kernel.

## Decision
Introduce the Permission & Security Kernel as a dedicated subsystem positioned between the Tool Runtime and the Platform Layer.

The key design principle:
> **The Permission Kernel decides whether a requested capability execution is permitted. It never executes anything. It only authorizes.**

### Structural Decisions Made

1. **Canonical 7-Stage Pipeline:** Validate → Publish → Evaluate → Publish → Authorize → Publish → Result. Every step is observable via events.

2. **Contracts-First Design:** `contracts.py` defines `PermissionManager`, `PolicyEvaluator`, `PermissionAuthorizer`, and `PermissionValidator` as enforcing ABCs with `@abstractmethod`. Implementation classes are internal.

3. **Immutable Models:** `PermissionRequest`, `PermissionResult`, `PermissionDecision`, `PermissionPolicy`, `SecurityContext` are all frozen dataclasses.

4. **Trust Level Hierarchy:** `TrustLevel` enum (`UNTRUSTED → LOW → MEDIUM → HIGH → CRITICAL`) provides a clear ordering for policy enforcement.

5. **Default Policy Behavior:** In the absence of an applicable policy, execution is granted. This is intentional for the scaffolding phase — future milestones will introduce deny-by-default postures.

6. **Failure Normalization:** Any exception inside `check_permission()` is caught and normalized into a denied `PermissionResult`. The pipeline never leaks exceptions.

7. **Audit Events:** `PermissionGranted` and `PermissionDenied` events provide an immutable audit trail. All security decisions are observable without polling.

## Rationale
- Decoupling authorization from execution ensures the Tool Runtime remains stateless and platform-agnostic.
- Using a dedicated contracts layer keeps the policy implementation swappable without changing the public API.
- The `TrustLevel` hierarchy provides a simple, extensible model for future identity-based and device-based trust attestation.

## Consequences
- Positive: Authorization is centralized and auditable through the event bus.
- Positive: Policy logic is isolated — future implementations (file-based, DB-backed, remote) require no changes to the pipeline.
- Positive: The pattern is reusable for Windows, Web, and any future platform runtime.
- Negative: Default grant policy must be tightened before production deployment.
- Negative: Real trust level determination requires integration with Identity (future milestone).

## Future Milestones
- **Milestone 12.2:** Implement real policy loading (file-based or declarative policies).
- **Milestone 12.3:** Integrate TrustLevel assignment from Identity subsystem.
- **Milestone 12.4:** Implement deny-by-default posture for production.
