# Identity System

The Identity System provides platform-independent kernel infrastructure for managing identities, roles, permissions, sessions, authentication, and authorization within IRA OS.

## Overview

The Identity System is built on the following concepts:
- **Identity**: An immutable representation of a user, service, or automation script.
- **Roles & Policies**: Roles (e.g. `OWNER`, `GUEST`) are mapped to `Permission` sets via a `PermissionPolicy`.
- **Explicit Grants**: Specific permissions can be granted or revoked directly on an identity without altering its roles.
- **Sessions**: Temporary authenticated periods mapped to a specific `Identity`. 
- **Context Tracking**: The currently authenticated identity and session are tracked safely per async-task using `contextvars`, making the entire system thread-safe and async-safe without global mutable state.

## Architecture

- **`IdentityRegistry`**: Pure in-memory O(1) lookup storage for registered identities.
- **`SessionRegistry`**: Pure in-memory storage for active sessions.
- **`AuthenticationManager`**: Issues sessions and manages the `contextvars` context.
- **`AuthorizationManager`**: Determines effective permissions and evaluates access.
- **`IdentityManager`**: The unified public facade combining registry, auth, and authz capabilities.

## Event Bus Integration

The Identity System can optionally publish strongly-typed events (e.g. `IdentityRegistered`, `PermissionGranted`) if an `EventBus` is present in the dependency injection container.

## Usage

```python
from core.identity import Identity, Role, Permission

# 1. Register an Identity
identity = Identity(
    id="u_123",
    username="admin_user",
    display_name="Admin",
    roles=[Role.ADMIN]
)
await identity_manager.register(identity)

# 2. Authenticate
session = await identity_manager.authenticate(identity)

# 3. Check Context anywhere in the async execution path
current_user = identity_manager.current_identity()
current_sess = identity_manager.current_session()

# 4. Check Authorization
identity_manager.authorize(current_user, Permission.READ_MEMORY)

# 5. Grant explicit permission
await identity_manager.grant(current_user, Permission.SYSTEM)
```
