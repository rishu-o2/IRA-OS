import pytest
import anyio
import uuid
import datetime
from typing import Optional, List
from contextvars import ContextVar

from core.config import ConfigurationManager
from core.events import EventBus
from core.logging import LoggerFactory, Logger
from core.container import Container
from core.identity import (
    IdentityManager, IdentityRegistry, SessionRegistry, AuthenticationManager, AuthorizationManager,
    Identity, Role, Permission, Session, IdentityModule, DefaultPermissionPolicy,
    AuthenticationError, AuthorizationError, SessionRegistrationError, IdentityRegistrationError
)


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def config():
    cm = ConfigurationManager()
    cm.load()
    return cm


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def logger():
    return LoggerFactory().get("test.identity")


@pytest.fixture
def identity_manager(config, event_bus, logger):
    id_reg = IdentityRegistry()
    sess_reg = SessionRegistry()
    policy = DefaultPermissionPolicy()
    
    auth_mgr = AuthenticationManager(id_reg, sess_reg, config, event_bus)
    authz_mgr = AuthorizationManager(policy, event_bus)
    
    return IdentityManager(id_reg, auth_mgr, authz_mgr, logger, event_bus)


# --- Registry Tests ---

def test_identity_registration(identity_manager: IdentityManager):
    ident = Identity(id="1", username="admin", display_name="Admin", roles=[Role.ADMIN])
    
    # Needs async? register in IdentityManager is async because it triggers event bus
    # Wait, test is sync, but the function is async. Let's make the test async.
    pass

@pytest.mark.anyio
async def test_identity_registration_async(identity_manager: IdentityManager):
    ident = Identity(id="1", username="admin", display_name="Admin", roles=[Role.ADMIN])
    await identity_manager.register(ident)
    
    assert identity_manager.get_identity("1") == ident
    assert len(identity_manager.list_identities()) == 1

@pytest.mark.anyio
async def test_duplicate_registration(identity_manager: IdentityManager):
    ident = Identity(id="1", username="admin", display_name="Admin", roles=[Role.ADMIN])
    await identity_manager.register(ident)
    
    with pytest.raises(IdentityRegistrationError):
        await identity_manager.register(Identity(id="1", username="other", display_name="Other"))
        
    with pytest.raises(IdentityRegistrationError):
        await identity_manager.register(Identity(id="2", username="admin", display_name="Other"))


# --- Authentication & Session Tests ---

@pytest.mark.anyio
async def test_authentication_success(identity_manager: IdentityManager):
    ident = Identity(id="1", username="admin", display_name="Admin", roles=[Role.ADMIN])
    await identity_manager.register(ident)
    
    session = await identity_manager.authenticate(ident)
    
    assert session.identity_id == "1"
    assert session.authenticated is True
    
    assert identity_manager.current_identity() == ident
    assert identity_manager.current_session() == session

@pytest.mark.anyio
async def test_authentication_unregistered(identity_manager: IdentityManager):
    ident = Identity(id="ghost", username="ghost", display_name="Ghost")
    
    with pytest.raises(AuthenticationError):
        await identity_manager.authenticate(ident)

@pytest.mark.anyio
async def test_logout(identity_manager: IdentityManager):
    ident = Identity(id="1", username="admin", display_name="Admin")
    await identity_manager.register(ident)
    
    session = await identity_manager.authenticate(ident)
    assert identity_manager.current_session() == session
    
    await identity_manager.logout(session.session_id)
    
    assert identity_manager.current_session() is None
    assert identity_manager.current_identity() is None


# --- Authorization & RBAC Tests ---

@pytest.mark.anyio
async def test_rbac_default_policy(identity_manager: IdentityManager):
    ident = Identity(id="owner", username="owner", display_name="Owner", roles=[Role.OWNER])
    await identity_manager.register(ident)
    
    # Owner has all permissions
    assert identity_manager.has_permission(ident, Permission.SYSTEM)
    identity_manager.authorize(ident, Permission.SYSTEM) # Should not raise
    
    guest = Identity(id="guest", username="guest", display_name="Guest", roles=[Role.GUEST])
    await identity_manager.register(guest)
    
    # Guest has limited permissions
    assert identity_manager.has_permission(guest, Permission.READ_MEMORY)
    assert not identity_manager.has_permission(guest, Permission.SYSTEM)
    
    with pytest.raises(AuthorizationError):
        identity_manager.authorize(guest, Permission.SYSTEM)

@pytest.mark.anyio
async def test_explicit_grants(identity_manager: IdentityManager):
    guest = Identity(id="guest", username="guest", display_name="Guest", roles=[Role.GUEST])
    await identity_manager.register(guest)
    
    assert not identity_manager.has_permission(guest, Permission.SYSTEM)
    
    await identity_manager.grant(guest, Permission.SYSTEM)
    assert identity_manager.has_permission(guest, Permission.SYSTEM)
    
    await identity_manager.revoke(guest, Permission.SYSTEM)
    assert not identity_manager.has_permission(guest, Permission.SYSTEM)


# --- DI Container Integration ---

@pytest.mark.anyio
async def test_di_integration():
    from core.container import ContainerProtocol
    container = Container()
    container.register_instance(ContainerProtocol, container)
    
    # Config is required by Auth Manager
    config = ConfigurationManager()
    config.load()
    container.register_instance(ConfigurationManager, config)
    
    # Logging is required by Identity Manager
    log_factory = LoggerFactory()
    container.register_instance(LoggerFactory, log_factory)
    
    # Install identity module
    container.install(IdentityModule())
    
    # Resolve manager
    manager = await container.resolve(IdentityManager)
    
    assert isinstance(manager, IdentityManager)
    assert isinstance(manager._registry, IdentityRegistry)
    assert isinstance(manager._authentication, AuthenticationManager)
    assert isinstance(manager._authorization, AuthorizationManager)
    
    # Test it works
    ident = Identity(id="di_user", username="di_user", display_name="DI")
    await manager.register(ident)
    assert manager.get_identity("di_user") == ident


# --- Event Bus Integration ---

@pytest.mark.anyio
async def test_event_publishing():
    bus = EventBus()
    config = ConfigurationManager()
    config.load()
    log_factory = LoggerFactory()
    logger = log_factory.get("test")
    
    events_received = []
    
    async def handler(event):
        events_received.append(event)
        
    bus.subscribe(EventBus, handler) # Subscribe to all for simplicity (but wildcard is not strictly defined, we can just use the exact type)
    # Actually EventBus uses Type[Event] but allows wildcard if type is Event (which is defined as Event in core.events.models)
    from core.events.models import Event
    bus.subscribe(Event, handler)
    
    manager = IdentityManager(
        IdentityRegistry(),
        AuthenticationManager(IdentityRegistry(), SessionRegistry(), config, bus), # Note: using new IdentityRegistry instance for Auth just for this test is fine, but properly we share it
        AuthorizationManager(DefaultPermissionPolicy(), bus),
        logger,
        bus
    )
    # Fix the shared registry
    id_reg = IdentityRegistry()
    manager._registry = id_reg
    manager._authentication._identity_registry = id_reg
    
    ident = Identity(id="ev_user", username="ev_user", display_name="EV")
    await manager.register(ident)
    
    await anyio.sleep(0.01) # let dispatcher run
    assert any(e.name == "IdentityRegistered" for e in events_received)
    
    sess = await manager.authenticate(ident)
    await anyio.sleep(0.01)
    assert any(e.name == "IdentityAuthenticated" for e in events_received)
    
    await manager.grant(ident, Permission.SYSTEM)
    await anyio.sleep(0.01)
    assert any(e.name == "PermissionGranted" for e in events_received)
