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
    AuthenticationError, AuthorizationError, SessionRegistrationError, IdentityRegistrationError,
    SessionExpiredError
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

@pytest.mark.anyio
async def test_nested_context_restores_parent_context(identity_manager: IdentityManager):
    outer = Identity(id="outer", username="outer", display_name="Outer", roles=[Role.ADMIN])
    inner = Identity(id="inner", username="inner", display_name="Inner", roles=[Role.GUEST])
    await identity_manager.register(outer)
    await identity_manager.register(inner)

    outer_session = await identity_manager.authenticate(outer)
    inner_session = await identity_manager._authentication.authenticate(inner)

    assert identity_manager.current_identity() == inner
    assert identity_manager.current_session() == inner_session

    await identity_manager._authentication.logout(inner_session.session_id)

    assert identity_manager.current_identity() == outer
    assert identity_manager.current_session() == outer_session

@pytest.mark.anyio
async def test_context_isolation_across_tasks(identity_manager: IdentityManager):
    identities = [
        Identity(id=f"task-{i}", username=f"task-{i}", display_name=f"Task {i}", roles=[Role.GUEST])
        for i in range(2)
    ]
    for ident in identities:
        await identity_manager.register(ident)

    async def worker(ident: Identity):
        session = await identity_manager.authenticate(ident)
        await anyio.sleep(0)
        assert identity_manager.current_identity() == ident
        assert identity_manager.current_session() == session
        await identity_manager.logout(session.session_id)

    async with anyio.create_task_group() as tg:
        for ident in identities:
            tg.start_soon(worker, ident)

@pytest.mark.anyio
async def test_expired_sessions_are_rejected(identity_manager: IdentityManager):
    ident = Identity(id="exp", username="exp", display_name="Expired", roles=[Role.GUEST])
    await identity_manager.register(ident)

    config = ConfigurationManager()
    config.load()
    config.override({"identity": {"session_timeout": -1}})
    config.load()

    auth = AuthenticationManager(identity_manager._registry, identity_manager._authentication._session_registry, config, None)

    with pytest.raises(SessionExpiredError):
        await auth.authenticate(ident)

    assert auth.current_session() is None
    assert auth.current_identity() is None


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


def test_models_are_immutable():
    ident = Identity(id="immutable", username="immutable", display_name="Immutable", roles=[Role.ADMIN], metadata={"key": "value"})
    session = Session(session_id="s1", identity_id="immutable", device_id=None, started_at=datetime.datetime.now(datetime.timezone.utc), expires_at=None, authenticated=True, metadata={"source": "test"})

    with pytest.raises(AttributeError):
        ident.roles.append(Role.GUEST)

    with pytest.raises(TypeError):
        ident.metadata["key"] = "new"

    with pytest.raises(TypeError):
        session.metadata["source"] = "changed"


# --- DI Container Integration ---

@pytest.mark.anyio
async def test_registry_replace_and_remove():
    registry = IdentityRegistry()
    original = Identity(id="reg-1", username="first", display_name="First", roles=[Role.GUEST])
    replacement = Identity(id="reg-1", username="second", display_name="Second", roles=[Role.ADMIN])

    registry.register(original)
    registry.replace(replacement)

    assert registry.get("reg-1") == replacement
    assert registry.get_by_username("second") == replacement
    assert registry.get_by_username("first") is None

    registry.remove("reg-1")
    assert registry.exists("reg-1") is False

@pytest.mark.anyio
async def test_lifecycle_idempotency():
    config = ConfigurationManager()
    config.load()
    logger = LoggerFactory().get("test.lifecycle")
    manager = IdentityManager(IdentityRegistry(), AuthenticationManager(IdentityRegistry(), SessionRegistry(), config), AuthorizationManager(DefaultPermissionPolicy()), logger)

    await manager.start()
    await manager.start()
    await manager.shutdown()
    await manager.shutdown()

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
