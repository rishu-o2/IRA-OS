# Identity System

The Identity System is the foundational kernel infrastructure component responsible for identifying entities (users, services, automation scripts) and enforcing access control in IRA OS.

## Architecture

The Identity System is built using a decoupled architecture governed by a facade, the `IdentityManager`.

1. **IdentityRegistry**: A pure in-memory, fast `O(1)` storage for registered identities. Identities are immutable.
2. **SessionRegistry**: A pure in-memory store for active sessions.
3. **AuthenticationManager**: Validates identities, issues `Session` objects, and tracks the current context.
4. **AuthorizationManager**: Determines effective permissions by combining Role-Based Access Control (RBAC) via `PermissionPolicy` and explicit grants.

## Execution Context

Unlike traditional web servers that pass `request` objects through every function, IRA OS uses `contextvars` to track the authenticated identity and session within the current `async` execution path.

This guarantees:
- **Thread Safety**: Different async tasks or threads cannot overwrite each other's context.
- **Clean APIs**: Functions do not need to accept an `identity` parameter if they simply need to know who invoked them.

## Roles & Permissions

- **Roles**: High-level groupings (e.g., `OWNER`, `ADMIN`, `GUEST`).
- **Permissions**: Granular actions (e.g., `READ_MEMORY`, `CONTROL_DEVICE`).
- **Policies**: The `PermissionPolicy` defines which Roles inherit which Permissions.
- **Grants**: An individual Identity can be explicitly granted or revoked a specific Permission without altering their Role.

Effective Permissions = (Permissions inherited from Roles) U (Explicitly Granted Permissions)

## Event Bus Integration

The Identity System emits strongly-typed events to the `EventBus` if one is present:
- `IdentityRegistered`
- `IdentityAuthenticated`
- `IdentityLoggedOut`
- `PermissionGranted`
- `PermissionRevoked`

These events allow audit logging, telemetry, or security monitoring to plug in transparently.
