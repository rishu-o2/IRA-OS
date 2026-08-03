from core.container import Module, ContainerProtocol
from core.config import ConfigurationManager
from core.events import EventBus
from core.logging import LoggerFactory, Logger

from .registry import IdentityRegistry
from .session_registry import SessionRegistry
from .policies import DefaultPermissionPolicy, PermissionPolicy
from .authentication import AuthenticationManager
from .authorization import AuthorizationManager
from .manager import IdentityManager


class IdentityModule(Module):
    """
    Dependency Injection Module for the Identity System.
    Registers the registry, authentication, authorization, and manager.
    """
    def configure(self, container: ContainerProtocol) -> None:
        # Register Core components if they exist in the container, otherwise resolve to None
        
        # Registries (Pure In-Memory)
        container.register_singleton(IdentityRegistry)
        container.register_singleton(SessionRegistry)
        
        # Policies
        container.register_singleton(PermissionPolicy, DefaultPermissionPolicy)
        
        # Managers
        container.register_factory(
            AuthenticationManager,
            factory=self._build_authentication_manager,
            lifetime=container.Scope.SINGLETON if hasattr(container, "Scope") else 1 # Fallback to Singleton
        )
        
        container.register_factory(
            AuthorizationManager,
            factory=self._build_authorization_manager,
            lifetime=container.Scope.SINGLETON if hasattr(container, "Scope") else 1
        )
        
        container.register_factory(
            IdentityManager,
            factory=self._build_identity_manager,
            lifetime=container.Scope.SINGLETON if hasattr(container, "Scope") else 1
        )

    async def _build_authentication_manager(self, container: ContainerProtocol) -> AuthenticationManager:
        id_reg = await container.resolve(IdentityRegistry)
        sess_reg = await container.resolve(SessionRegistry)
        config = await container.resolve(ConfigurationManager)
        
        # Optional EventBus
        event_bus = None
        if container.has(EventBus):
            event_bus = await container.resolve(EventBus)
            
        return AuthenticationManager(id_reg, sess_reg, config, event_bus)

    async def _build_authorization_manager(self, container: ContainerProtocol) -> AuthorizationManager:
        policy = await container.resolve(PermissionPolicy)
        
        # Optional EventBus
        event_bus = None
        if container.has(EventBus):
            event_bus = await container.resolve(EventBus)
            
        return AuthorizationManager(policy, event_bus)

    async def _build_identity_manager(self, container: ContainerProtocol) -> IdentityManager:
        registry = await container.resolve(IdentityRegistry)
        auth = await container.resolve(AuthenticationManager)
        authz = await container.resolve(AuthorizationManager)
        
        log_factory = await container.resolve(LoggerFactory)
        logger = log_factory.get("core.identity")
        
        event_bus = None
        if container.has(EventBus):
            event_bus = await container.resolve(EventBus)
            
        return IdentityManager(registry, auth, authz, logger, event_bus)
