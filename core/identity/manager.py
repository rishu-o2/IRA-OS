import logging
from typing import Optional, List, Set, Any
from core.events import EventBus
from core.logging import Logger

from .models import Identity, IdentityRegistered
from .session import Session
from .permissions import Permission
from .registry import IdentityRegistry
from .authentication import AuthenticationManager
from .authorization import AuthorizationManager
from .exceptions import IdentityRegistrationError


class IdentityManager:
    """
    Public facade for the Identity subsystem.
    Delegates to IdentityRegistry, AuthenticationManager, and AuthorizationManager.
    """
    def __init__(
        self,
        registry: IdentityRegistry,
        authentication: AuthenticationManager,
        authorization: AuthorizationManager,
        logger: Logger,
        event_bus: Optional[Any] = None
    ):
        self._registry = registry
        self._authentication = authentication
        self._authorization = authorization
        self._logger = logger
        self._event_bus = event_bus

    # --- Lifecycle Hooks ---
    
    async def start(self) -> None:
        self._logger.info("IdentityManager starting.")

    async def shutdown(self) -> None:
        self._logger.info("IdentityManager shutting down. Clearing active sessions.")
        # We don't clear the IdentityRegistry because it might be needed for graceful shutdown checks
        # But we clear sessions.
        self._authentication._session_registry.clear()

    # --- Registry Operations ---
    
    async def register(self, identity: Identity) -> None:
        self._registry.register(identity)
        self._logger.info(f"Registered new identity: {identity.id} ({identity.username})")
        
        if self._event_bus:
            event = IdentityRegistered(
                payload={"identity_id": identity.id, "username": identity.username},
                source="IdentityManager",
                identity_id=identity.id,
                username=identity.username
            )
            await self._event_bus.publish(event)
            
    def get_identity(self, identity_id: str) -> Optional[Identity]:
        return self._registry.get(identity_id)
        
    def list_identities(self) -> List[Identity]:
        return self._registry.list()

    # --- Authentication Operations ---
    
    async def authenticate(self, identity: Identity, device_id: Optional[str] = None) -> Session:
        session = await self._authentication.authenticate(identity, device_id)
        self._logger.info(f"Authenticated identity {identity.id}. Issued session {session.session_id}.")
        return session
        
    async def logout(self, session_id: Optional[str] = None) -> None:
        target = session_id or (self.current_session().session_id if self.current_session() else None)
        if target:
            await self._authentication.logout(target)
            self._logger.info(f"Logged out session {target}.")

    def current_identity(self) -> Optional[Identity]:
        return self._authentication.current_identity()
        
    def current_session(self) -> Optional[Session]:
        return self._authentication.current_session()

    # --- Authorization Operations ---
    
    def authorize(self, identity: Identity, permission: Permission) -> None:
        try:
            self._authorization.authorize(identity, permission)
        except Exception as e:
            self._logger.warning(f"Authorization failed for identity {identity.id} on permission {permission.name}")
            raise e

    def has_permission(self, identity: Identity, permission: Permission) -> bool:
        return self._authorization.has_permission(identity, permission)
        
    def get_effective_permissions(self, identity: Identity) -> Set[Permission]:
        return self._authorization.get_effective_permissions(identity)

    async def grant(self, identity: Identity, permission: Permission) -> None:
        await self._authorization.grant(identity, permission)
        self._logger.info(f"Granted permission {permission.name} to identity {identity.id}")

    async def revoke(self, identity: Identity, permission: Permission) -> None:
        await self._authorization.revoke(identity, permission)
        self._logger.info(f"Revoked permission {permission.name} from identity {identity.id}")

