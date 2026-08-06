# Execution Service Kernel

The Execution Service is a first-class IRA OS kernel subsystem introduced in Milestone 16.0.

## Purpose

The Execution Service is the **single authoritative entry point** for all platform capability execution.

No subsystem other than `ExecutionService` may invoke the `RuntimeManager` directly.

## Canonical Pipeline

```text
Brain
  ↓
Planner
  ↓
Workflow
  ↓
ExecutionService  ← You are here
  ↓
Security (PermissionKernel)
  ↓
Runtime (RuntimeManager)
  ↓
Android Runtime / Platform Runtime
  ↓
Capability
```

## Responsibilities

- Validate every `ExecutionCommand` before processing.
- Enforce security authorization through the `PermissionManager` for **every** command.
- Dispatch authorized commands to the `RuntimeManager`.
- Publish observable events at each pipeline stage.
- Return a normalized `ExecutionOutcome` regardless of outcome.

## What ExecutionService must NEVER do

- Import Android, Windows, or any platform-specific code.
- Call `RuntimeManager` without first calling `PermissionManager`.
- Swallow errors silently.
- Return partial or ambiguous outcomes.
