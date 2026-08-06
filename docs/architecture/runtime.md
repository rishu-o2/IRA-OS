# Tool Runtime Architecture

## Overview
The Tool Runtime subsystem acts as the execution muscle of IRA OS. It safely takes deterministic decisions produced by the Brain and routes them to the correct abstract `Capability` to perform real-world actions.

## Purpose
The Runtime bridges the gap between AI orchestration and physical platform capabilities (Android, Windows, Plugins). It prevents the Brain from tightly coupling to execution environments.

## Responsibilities
- Validate execution requests.
- Discover and route to registered capabilities.
- Safely invoke capabilities and catch all runtime faults.
- Normalize exceptions into predictable failures.
- Publish `ExecutionStarted`, `ExecutionCompleted`, and `ExecutionFailed` events.

## Non-Responsibilities
The Runtime must **never**:
- Perform planning or memory operations.
- Connect directly to Android/Windows/Browser APIs.
- Evaluate AI models.
- Introduce non-deterministic behavior.

## The Canonical Pipeline
The Runtime guarantees exactly this execution order:

1. **Execution Request**
2. **Validation**
3. **Capability Lookup**
4. **Dispatch**
5. **Execute**
6. **Normalize Result**
7. **Publish Events**
8. **Execution Result**

## Extension Strategy
Future platforms integrate with IRA OS by registering instances of the `Capability` interface into the `CapabilityRegistry`. The Runtime simply routes to them without understanding their internal mechanisms.
