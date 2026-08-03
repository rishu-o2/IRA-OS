import threading
from typing import Dict, Set, Optional, Any
from core.events import EventBus
from .models import Identity, PermissionGranted, PermissionRevoked
from .permissions import Permission
from .policies import PermissionPolicy, DefaultPermissionPolicy
from .exceptions import AuthorizationError


class AuthorizationManager:
    """
    Evaluates permissions based on Role-Based Access Control (RBAC) 
    combined with explicit permission grants.
    """
    def __init__(self, policy: Optional[PermissionPolicy] = None, event_bus: Optional[Any] = None):
        self._policy = policy or DefaultPermissionPolicy()
        self._event_bus = event_bus
        self._lock = threading.RLock()
        
        # Explicit grants stored purely in-memory mapped by identity_id
        self._explicit_grants: Dict[str, Set[Permission]] = {}

    def _get_explicit_grants(self, identity_id: str) -> Set[Permission]:
        with self._lock:
            if identity_id not in self._explicit_grants:
                self._explicit_grants[identity_id] = set()
            return self._explicit_grants[identity_id]

    def get_effective_permissions(self, identity: Identity) -> Set[Permission]:
        """Calculates the full set of permissions for an identity."""
        permissions = set()
        
        # 1. Gather permissions from roles via policy
        for role in identity.roles:
            permissions.update(self._policy.permissions(role))
            
        # 2. Add explicitly granted permissions
        permissions.update(self._get_explicit_grants(identity.id))
        
        return permissions

    def has_permission(self, identity: Identity, permission: Permission) -> bool:
        """Checks if an identity holds a specific permission."""
        if not identity.active:
            return False
            
        effective = self.get_effective_permissions(identity)
        return permission in effective

    def authorize(self, identity: Identity, permission: Permission) -> None:
        """Asserts that an identity has a permission, raising AuthorizationError if not."""
        if not self.has_permission(identity, permission):
            raise AuthorizationError(f"Identity '{identity.id}' lacks permission '{permission.name}'")

    async def grant(self, identity: Identity, permission: Permission) -> None:
        """Explicitly grants a permission to an identity."""
        with self._lock:
            grants = self._get_explicit_grants(identity.id)
            if permission not in grants:
                grants.add(permission)
                
                if self._event_bus:
                    event = PermissionGranted(
                        payload={"identity_id": identity.id, "permission": permission.name},
                        source="AuthorizationManager",
                        identity_id=identity.id,
                        permission=permission.name
                    )
                    await self._event_bus.publish(event)

    async def revoke(self, identity: Identity, permission: Permission) -> None:
        """Explicitly revokes an explicitly granted permission."""
        with self._lock:
            grants = self._get_explicit_grants(identity.id)
            if permission in grants:
                grants.remove(permission)
                
                if self._event_bus:
                    event = PermissionRevoked(
                        payload={"identity_id": identity.id, "permission": permission.name},
                        source="AuthorizationManager",
                        identity_id=identity.id,
                        permission=permission.name
                    )
                    await self._event_bus.publish(event)
