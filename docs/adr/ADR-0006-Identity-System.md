# Architecture Decision Record 0006: Identity System

## Title
ADR-0006: Kernel Identity, Context Tracking, and Authorization

## Status
Accepted

## Date
2026-08-03

## Context
IRA OS requires a foundational Identity System before it can implement higher-level constructs like Memory (which requires ownership tracking), Planner (which requires task delegation), and Brain (which requires user personalization). 
The Identity System must be platform-agnostic, persistent-storage-agnostic, and async-safe.

## Decision
We implemented the `core/identity/` package with the following architectural choices:

1. **ContextVars for State**: `AuthenticationManager` uses Python's `contextvars` to store `_current_identity` and `_current_session`. This ensures that identity context automatically flows through the async execution path (like a correlation ID in logging) without relying on global mutable state or polluting function signatures.
2. **Separation of Authentication and Registration**: `AuthenticationManager` handles only login/logout and context. `IdentityRegistry` and `SessionRegistry` handle storage. This respects the Single Responsibility Principle.
3. **Immutable Identities**: The `Identity` model is an immutable dataclass. Mutable state like "Explicit Permission Grants" is maintained in the `AuthorizationManager` rather than directly on the `Identity` object.
4. **Decoupled Policies**: The mapping of `Role` to `Permission` is abstracted behind a `PermissionPolicy`. This allows future expansion (like Enterprise roles or Plugin roles) without modifying the core `AuthorizationManager`.
5. **No Persistence/Crypto**: Passwords, OAuth, and biometrics are explicitly omitted. This system manages the *trusted* identity within the kernel. Authentication adapters will be built as external plugins or application-layer modules.
6. **Strongly-Typed Events**: Identity changes publish fully-formed Event objects (`IdentityAuthenticated`, `PermissionGranted`) to the Event Bus, automatically integrating with telemetry and logging middlewares.

## Consequences
- **Positive**: High extensibility. The system easily scales from a single-user local deployment to a multi-tenant remote server just by changing the authentication adapters and permission policies.
- **Positive**: Clean, async-safe context tracking.
- **Negative**: Because the registries are purely in-memory, identities and explicit grants must be re-registered on every system boot. (This is expected to be solved by an application-level adapter reading from a database in the future).

## Milestone 6.1 Refinements
The freeze-preparation refinement pass preserved the architecture and public API while tightening context restoration, immutable model semantics, and centralized session expiration handling. These refinements are compatibility-preserving and do not alter the underlying architectural decisions.

## Version
v1.5.0 (Milestone 6)
