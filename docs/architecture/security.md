# Permission & Security Kernel Architecture

## Overview
The Permission & Security subsystem is IRA OS's central authorization layer. Every `ExecutionRequest` produced by the Tool Runtime must pass through the Permission Kernel before execution. The kernel determines whether execution is allowed based on IRA policy.

> **The Permission Kernel decides whether a requested capability execution is permitted. It never executes anything. It only authorizes.**

## Architecture Position

```
Kernel
├── Identity
├── Memory
├── Planner
├── Brain
└── Tool Runtime

Security Layer
└── Permission Kernel        ← Authorization gate
        ↓
Platform Layer
├── Android Runtime
├── Windows Runtime
└── ...
```

## Dependency Direction

```
User
  ↓
Brain
  ↓
Tool Runtime
  ↓
Permission Kernel             ← This subsystem
  ↓
Platform Runtimes
```

The Permission Kernel is a strict downstream consumer. It never calls Brain, Planner, Memory, or Identity.

## Responsibilities

- Capability authorization
- Policy evaluation
- User approval requirements
- Trust level enforcement
- Security decision records
- Execution grants and denials
- Audit logging via events

## Non-Responsibilities

The Permission Kernel must **never**:
- Execute tools or capabilities
- Perform planning or reasoning
- Store conversational memory
- Authenticate users (Identity's responsibility)
- Implement Android/Windows/platform permissions
- Call networking or device APIs

## Canonical Pipeline

```
1. Permission Request
   ↓
2. Validate Request          (PermissionValidator)
   ↓
3. Load Applicable Policies  (PolicyEvaluator.load_policy)
   ↓
4. Evaluate Policy           (PolicyEvaluator.evaluate)
   ↓
5. Determine Trust / Approval(PermissionDecision)
   ↓
6. Authorize / Enforce Denial(PermissionAuthorizer.authorize)
   ↓
7. Publish Security Event    (EventBus)
   ↓
8. Permission Result         (PermissionResult)
```

## Component Map

| Component | File | Responsibility |
|---|---|---|
| `PermissionManager` | `contracts.py` + `manager.py` | Pipeline orchestration, lifecycle |
| `PolicyEvaluator` | `contracts.py` + `policy.py` | Load and evaluate policies |
| `PermissionAuthorizer` | `contracts.py` + `authorizer.py` | Convert decision → result |
| `PermissionValidator` | `contracts.py` + `validator.py` | Validate request shape |
| `SecurityModule` | `security_module.py` | DI wiring |

## Models

| Model | Purpose |
|---|---|
| `PermissionRequest` | Incoming authorization request |
| `SecurityContext` | Caller context and trust level |
| `PermissionDecision` | Intermediate policy decision |
| `PermissionResult` | Final immutable outcome |
| `PermissionPolicy` | A loaded authorization policy |
| `PermissionRequirement` | Capability-specific requirement |
| `TrustLevel` | UNTRUSTED / LOW / MEDIUM / HIGH / CRITICAL |
| `PermissionState` | PENDING / GRANTED / DENIED / REQUIRES_APPROVAL |

## Event Model

| Event | When |
|---|---|
| `PermissionRequested` | Request enters the kernel |
| `PolicyLoaded` | A policy is loaded into the evaluator |
| `PolicyEvaluationCompleted` | Policy evaluation resolves |
| `PermissionGranted` | Capability authorized |
| `PermissionDenied` | Capability refused |

## Health Model

| State | Meaning |
|---|---|
| `STOPPED` | Kernel is not running |
| `RUNNING` | Kernel is fully operational |
| `DEGRADED` | A dependency is missing |

## Public API

```python
# Resolve the manager
manager = await container.resolve(PermissionManager)
await manager.start()

# Build a permission request
request = PermissionRequest(
    permission_id="perm-1",
    capability_id="android.call",
    context=SecurityContext(
        request_id="req-1",
        capability_id="android.call",
        trust_level=TrustLevel.MEDIUM,
    )
)

# Authorize
result = await manager.check_permission(request)
if result.granted:
    # proceed with Tool Runtime execution
    pass
else:
    # handle denial_reason
    pass
```

## Extension Points

- **Policy Plugins:** Implement `PolicyEvaluator` to load policies from files, databases, or remote services.
- **Custom Authorizers:** Implement `PermissionAuthorizer` for role-based or attribute-based access control.
- **Trust Providers:** Future milestones can feed real `TrustLevel` data from Identity or device attestation into `SecurityContext`.

## Allowed Dependencies

- `core.events`
- `core.logging`
- `core.lifecycle`
- `core.container`
