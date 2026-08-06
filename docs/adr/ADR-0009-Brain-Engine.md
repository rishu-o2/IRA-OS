# Architecture Decision Record 0009: Brain Engine

## Title
ADR-0009: Brain Engine

## Status
Accepted (Frozen for API)

## Date
2026-08-05

## Context
Milestones 6 through 8 established the frozen kernel foundation with Identity, Memory, and Planner subsystems. Milestone 9 introduces the Brain, which orchestrates these kernel services into an intelligent request-processing pipeline without becoming a runtime executor or tool runtime.

## Decision
Implement a Brain Engine that:
- accepts stateless request input
- follows the canonical 8-stage pipeline (Validate Request, Build Conversation Context, Resolve Identity, Analyze Request, Retrieve Memory, Build Planner Input, Invoke Planner, Make Decision)
- produces a deterministic `BrainResult`
- publishes Brain lifecycle and request events
- integrates with kernel lifecycle and DI
- remains tool-agnostic and LLM-agnostic

## Rationale
- The Brain centralizes request orchestration while preserving the kernel's separation of concerns.
- A stateless Brain avoids request carryover and simplifies kernel auditability.
- Building the Brain on frozen kernel subsystems ensures long-term API stability.
- Deferring execution and tool runtime responsibilities to future milestones keeps the Brain focused on decision making.

## Consequences
- Positive: clean kernel orchestration layer with minimal public API.
- Positive: stable integration point for future runtime and tool systems.
- Negative: the Brain does not implement execution, so future runtime remains necessary for end-to-end requests.

## Alternatives Considered
- Embedding execution or tool orchestration in the Brain: rejected because it violates separation of concerns.
- Making the Brain stateful across requests: rejected to preserve kernel statelessness and auditability.
- Allowing direct LLM dependency: rejected to keep the Brain SDK-agnostic and future-proof.

## Future
- When Tool Runtime arrives, it will consume Brain decisions without changing the Brain API.
- The Brain may be extended with richer reasoning or context modules, but the public request API remains minimal.
