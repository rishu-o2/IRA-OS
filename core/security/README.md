# Permission & Security Kernel

## Overview
The Permission & Security subsystem is IRA OS's central authorization layer.

> **The Permission Kernel decides whether a requested capability execution is permitted. It never executes anything.**

## Architecture Position

```
Brain
  ↓
Tool Runtime
  ↓
Permission Kernel      ← Authorization gate
  ↓
Platform Runtimes (Android, Windows...)
```

## Canonical Pipeline

```
Permission Request
  ↓ Validate Request
  ↓ Load Applicable Policies
  ↓ Evaluate Policy
  ↓ Determine Trust Requirement
  ↓ Authorize / Enforce Denial
  ↓ Publish Security Event
  ↓ Permission Result
```

## Components

| Component | File | Responsibility |
|---|---|---|
| `PermissionManager` | `contracts.py` + `manager.py` | Orchestrates pipeline, lifecycle |
| `PolicyEvaluator` | `contracts.py` + `policy.py` | Evaluates loaded policies |
| `PermissionAuthorizer` | `contracts.py` + `authorizer.py` | Converts decision → result |
| `PermissionValidator` | `contracts.py` + `validator.py` | Validates request shape |
| `SecurityModule` | `security_module.py` | DI wiring |

## Allowed Dependencies

- `core.events`
- `core.logging`
- `core.lifecycle`
- `core.container`

## Non-Responsibilities

The Security Kernel must **never**:
- Execute capabilities
- Perform planning or reasoning
- Access Android/Windows/platform APIs
- Authenticate users (that is Identity's domain)
- Store memory
