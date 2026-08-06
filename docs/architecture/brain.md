# Brain Engine Architecture

## Overview
The Brain Engine is the centralized orchestration layer of IRA OS. It sits above the frozen kernel foundation and coordinates request processing without introducing runtime execution, tool integration, platform-specific code, or external AI dependencies.

The Brain is not another kernel service. It is the kernel's request coordinator:
- stateless between requests
- platform-independent
- tool-agnostic
- LLM-agnostic
- built entirely on frozen kernel modules
- free of business logic belonging to other modules

## Purpose
The Brain receives an incoming request and transforms it into a decision-ready outcome by using the frozen kernel capabilities for identity resolution, context building, memory retrieval, and planning.

## Responsibilities
- Accept and validate a `BrainRequest`
- Resolve identity information through the frozen identity subsystem
- Build request context using kernel metadata and request details
- Retrieve relevant memory from the frozen memory subsystem
- Request a plan from the frozen planner subsystem
- Produce a deterministic `BrainResult`
- Publish Brain lifecycle and request events
- Integrate with kernel lifecycle and DI

## Non-Responsibilities
The Brain must never:
- perform tool execution
- store memory
- perform planning algorithms
- authenticate users directly
- call Android, Windows, or platform-specific APIs
- depend on any LLM SDK
- contain execution or runtime orchestration logic
- manage business workflows belonging to downstream systems

## Public API
The Brain exposes a small, stable API surface centered on orchestration:
- `BrainManager.process_request(request: BrainRequest) -> BrainResult`

The public API is intentionally minimal to preserve long-term freeze stability.

## Internal Architecture
The Brain is composed of a small set of collaboration layers:
- `BrainManager` — orchestration facade and lifecycle component
- `BrainRequest` / `BrainResult` — public request and response models
- `BrainContext` — request-scoped semantic context
- `BrainPipeline` — deterministic request processing pipeline
- `ReasoningEngine` — synthesizes decision inputs
- `DecisionEngine` — generates the final `BrainResult`
- `BrainModule` — DI integration and kernel wiring

## Request Pipeline
Every request follows exactly this canonical deterministic sequence:

1. Validate Request
2. Build Conversation Context
3. Resolve Identity
4. Analyze Request
5. Retrieve Memory
6. Build Planner Input
7. Invoke Planner
8. Make Decision

This pipeline is intentionally sequential and stateless between requests.

## Dependency Graph
The Brain depends only on frozen kernel modules:
- `core.identity`
- `core.memory`
- `core.planner`
- `core.events`
- `core.logging`
- `core.container`
- `core.lifecycle`

No Brain component depends on application-specific or runtime-specific subsystems.

## Event Integration
The Brain publishes kernel events for request lifecycle observability:
- `BrainRequestStarted`
- `BrainRequestCompleted`
- `BrainRequestFailed`

Events are the Brain's only outward integration channel for request diagnostics.

## Lifecycle Integration
The Brain participates in kernel lifecycle semantics:
- `start()` logs readiness
- `shutdown()` logs termination
- `health_check()` reports readiness and availability
- lifecycle hooks are idempotent and safe to call repeatedly

## DI Integration
The Brain is registered through a dedicated `BrainModule`.
The module provides:
- `BrainManager`
- `BrainPipeline`
- `ReasoningEngine`
- `DecisionEngine`
- request and context builders as needed

The Brain module consumes existing kernel services through constructor injection.

## Memory Integration
The Brain reads memory only to enrich request context and decision input.
It does not store or update memory.

## Planner Integration
The Brain consults the frozen Planner for plan generation only.
It does not perform graph construction, cycle detection, or execution.

## Future Tool Runtime Integration
The Brain's output is intentionally decision-centric, not execution-centric.
A future Tool Runtime subsystem can consume `BrainResult` and execute the plan without requiring Brain changes.

## Error Handling
The Brain handles all kernel-level errors at the boundary and returns a deterministic `BrainResult` for every request.
Planning, identity, and memory failures are normalized into a consistent failure contract.

## Extension Strategy
The Brain is designed to be extended by:
- alternative decision engines
- richer context builders
- pluggable reasoning strategies
- future runtime orchestration connections

Extensions must preserve the Brain's stateless orchestration role and kernel boundary.
