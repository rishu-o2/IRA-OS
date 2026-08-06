"""
Comprehensive tests for the Permission & Security Kernel (Milestone 12).
Covers: imports, contracts, models, events, exceptions, DI wiring,
lifecycle, policy evaluation, request validation, health, and public API.
"""
import inspect
import pytest

from core.container import Container, ContainerProtocol
from core.events import Event, EventBus
from core.lifecycle.states import ComponentState
from core.logging import LoggerFactory
from core.logging.sinks import NullSink

from core.security.contracts import (
    PermissionAuthorizer,
    PermissionManager,
    PermissionValidator,
    PolicyEvaluator,
)
from core.security.events import (
    PermissionDenied,
    PermissionGranted,
    PermissionRequested,
    PolicyEvaluationCompleted,
    PolicyLoaded,
)
from core.security.exceptions import (
    PermissionDeniedError,
    PermissionValidationError,
    PolicyEvaluationError,
    PolicyNotFoundError,
    SecurityError,
)
from core.security.models import (
    PermissionDecision,
    PermissionError,
    PermissionPolicy,
    PermissionRequest,
    PermissionRequirement,
    PermissionResult,
    PermissionState,
    SecurityContext,
    TrustLevel,
)
from core.security.authorizer import DefaultPermissionAuthorizer
from core.security.manager import SecurityManager
from core.security.policy import DefaultPolicyEvaluator
from core.security.security_module import SecurityModule
from core.security.validator import DefaultPermissionValidator


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"

async def build_container() -> Container:
    container = Container()
    event_bus = EventBus()
    logger_factory = LoggerFactory(sinks=[NullSink()])

    container.register_instance(ContainerProtocol, container)
    container.register_instance(EventBus, event_bus)
    container.register_instance(LoggerFactory, logger_factory)

    container.install(SecurityModule())
    return container


def make_context(trust: TrustLevel = TrustLevel.UNTRUSTED) -> SecurityContext:
    return SecurityContext(
        request_id="test-req",
        capability_id="test.cap",
        trust_level=trust
    )


def make_request(trust: TrustLevel = TrustLevel.UNTRUSTED) -> PermissionRequest:
    return PermissionRequest(
        permission_id="perm-1",
        capability_id="test.cap",
        context=make_context(trust)
    )


# ─────────────────────────────────────────────
# Import Safety
# ─────────────────────────────────────────────

def test_import_safety_no_forbidden():
    import sys
    import core.security
    import core.security.manager
    import core.security.policy
    import core.security.validator
    import core.security.authorizer
    
    forbidden = ["core.brain", "core.planner", "core.memory", "core.identity", "core.android", "core.runtime"]
    security_modules = [k for k in sys.modules.keys() if k.startswith("core.security")]

    for mod_name in security_modules:
        mod = sys.modules[mod_name]
        mod_file = getattr(mod, "__file__", None)
        if mod_file and mod_file.endswith(".py"):
            with open(mod_file, encoding="utf-8") as f:
                src = f.read()
            for forb in forbidden:
                assert forb not in src, f"Forbidden import '{forb}' in {mod_name}"


# ─────────────────────────────────────────────
# Contracts
# ─────────────────────────────────────────────

def test_contracts_are_abstract():
    assert inspect.isabstract(PermissionManager)
    assert inspect.isabstract(PolicyEvaluator)
    assert inspect.isabstract(PermissionAuthorizer)
    assert inspect.isabstract(PermissionValidator)

def test_contract_abstract_methods():
    def get_abstract_methods(cls):
        return {name for name, method in inspect.getmembers(cls)
                if getattr(method, "__isabstractmethod__", False)}

    assert "check_permission" in get_abstract_methods(PermissionManager)
    assert "start" in get_abstract_methods(PermissionManager)
    assert "shutdown" in get_abstract_methods(PermissionManager)
    assert "health_check" in get_abstract_methods(PermissionManager)
    
    assert "load_policy" in get_abstract_methods(PolicyEvaluator)
    assert "evaluate" in get_abstract_methods(PolicyEvaluator)
    
    assert "authorize" in get_abstract_methods(PermissionAuthorizer)
    assert "validate" in get_abstract_methods(PermissionValidator)

def test_implementations_satisfy_contracts():
    assert not inspect.isabstract(SecurityManager)
    assert not inspect.isabstract(DefaultPolicyEvaluator)
    assert not inspect.isabstract(DefaultPermissionAuthorizer)
    assert not inspect.isabstract(DefaultPermissionValidator)


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

def test_models_are_frozen():
    for cls in [
        PermissionRequest, PermissionDecision, PermissionResult,
        PermissionPolicy, SecurityContext, PermissionRequirement,
        PermissionError
    ]:
        assert hasattr(cls, "__dataclass_params__")
        assert cls.__dataclass_params__.frozen, f"{cls.__name__} must be frozen"

def test_enums():
    assert TrustLevel.UNTRUSTED.value == "UNTRUSTED"
    assert TrustLevel.CRITICAL.value == "CRITICAL"
    assert PermissionState.PENDING.value == "PENDING"
    assert PermissionState.GRANTED.value == "GRANTED"


# ─────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────

def test_events_inherit_event():
    for cls in [
        PermissionGranted, PermissionDenied, PermissionRequested,
        PolicyLoaded, PolicyEvaluationCompleted
    ]:
        assert issubclass(cls, Event)
        assert getattr(cls, "__dataclass_params__").frozen


# ─────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────

def test_exceptions():
    assert issubclass(SecurityError, Exception)
    assert issubclass(PermissionValidationError, SecurityError)
    assert issubclass(PolicyNotFoundError, SecurityError)
    assert issubclass(PermissionDeniedError, SecurityError)
    assert issubclass(PolicyEvaluationError, SecurityError)


# ─────────────────────────────────────────────
# DI Wiring
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_di_wiring():
    container = await build_container()
    
    manager = await container.resolve(PermissionManager)
    evaluator = await container.resolve(PolicyEvaluator)
    authorizer = await container.resolve(PermissionAuthorizer)
    validator = await container.resolve(PermissionValidator)
    
    assert isinstance(manager, SecurityManager)
    assert isinstance(evaluator, DefaultPolicyEvaluator)
    assert isinstance(authorizer, DefaultPermissionAuthorizer)
    assert isinstance(validator, DefaultPermissionValidator)
    
    manager2 = await container.resolve(PermissionManager)
    assert manager is manager2, "Manager should be singleton"


# ─────────────────────────────────────────────
# Validator
# ─────────────────────────────────────────────

def test_validator_success():
    v = DefaultPermissionValidator()
    v.validate(make_request())

def test_validator_failures():
    v = DefaultPermissionValidator()
    
    with pytest.raises(PermissionValidationError):
        v.validate(None)
        
    with pytest.raises(PermissionValidationError):
        v.validate(object())
        
    with pytest.raises(PermissionValidationError, match="permission_id"):
        req = PermissionRequest("", "cap", make_context())
        v.validate(req)
        
    with pytest.raises(PermissionValidationError, match="capability_id"):
        req = PermissionRequest("perm", "", make_context())
        v.validate(req)


# ─────────────────────────────────────────────
# Policy Evaluator Scaffold
# ─────────────────────────────────────────────

def test_evaluator_deny_by_default():
    """With no loaded policies, any capability must be DENIED (Deny-by-Default)."""
    evaluator = DefaultPolicyEvaluator()
    req = make_request(TrustLevel.UNTRUSTED)
    decision = evaluator.evaluate(req)
    assert decision.state == PermissionState.DENIED
    assert "Deny-by-Default" in decision.denial_reason

def test_evaluator_trust_insufficient():
    evaluator = DefaultPolicyEvaluator()
    policy = PermissionPolicy(
        policy_id="pol-1",
        name="test",
        description="test",
        requirements=(
            PermissionRequirement("test.cap", TrustLevel.HIGH),
        )
    )
    evaluator.load_policy(policy)
    
    req = make_request(TrustLevel.MEDIUM)
    decision = evaluator.evaluate(req)
    assert decision.state == PermissionState.DENIED
    assert "Insufficient trust" in decision.denial_reason

def test_evaluator_trust_sufficient():
    evaluator = DefaultPolicyEvaluator()
    policy = PermissionPolicy(
        policy_id="pol-1",
        name="test",
        description="test",
        requirements=(
            PermissionRequirement("test.cap", TrustLevel.MEDIUM),
        )
    )
    evaluator.load_policy(policy)
    
    req = make_request(TrustLevel.HIGH)
    decision = evaluator.evaluate(req)
    assert decision.state == PermissionState.GRANTED

def test_evaluator_requires_approval():
    evaluator = DefaultPolicyEvaluator()
    policy = PermissionPolicy(
        policy_id="pol-1",
        name="test",
        description="test",
        requirements=(
            PermissionRequirement("test.cap", TrustLevel.UNTRUSTED, requires_user_approval=True),
        )
    )
    evaluator.load_policy(policy)
    
    req = make_request(TrustLevel.UNTRUSTED)
    decision = evaluator.evaluate(req)
    assert decision.state == PermissionState.REQUIRES_APPROVAL


# ─────────────────────────────────────────────
# Authorizer
# ─────────────────────────────────────────────

def test_authorizer_granted():
    auth = DefaultPermissionAuthorizer()
    dec = PermissionDecision("p1", "c1", PermissionState.GRANTED, TrustLevel.UNTRUSTED)
    res = auth.authorize(dec)
    assert res.granted is True
    assert res.state == PermissionState.GRANTED

def test_authorizer_denied():
    auth = DefaultPermissionAuthorizer()
    dec = PermissionDecision("p1", "c1", PermissionState.DENIED, TrustLevel.UNTRUSTED, denial_reason="no")
    res = auth.authorize(dec)
    assert res.granted is False
    assert res.state == PermissionState.DENIED
    assert res.denial_reason == "no"


# ─────────────────────────────────────────────
# Lifecycle & Health
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_lifecycle_and_health():
    container = await build_container()
    manager = await container.resolve(PermissionManager)
    
    h1 = await manager.health_check()
    assert h1.state == ComponentState.STOPPED
    
    await manager.start()
    await manager.start() # idempotent
    h2 = await manager.health_check()
    assert h2.state == ComponentState.RUNNING
    
    await manager.shutdown()
    await manager.shutdown() # idempotent
    h3 = await manager.health_check()
    assert h3.state == ComponentState.STOPPED


# ─────────────────────────────────────────────
# Pipeline (Manager)
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_manager_pipeline_grant():
    """Grant requires an explicit policy defining the capability."""
    container = await build_container()
    manager = await container.resolve(PermissionManager)
    evaluator = await container.resolve(PolicyEvaluator)
    bus = await container.resolve(EventBus)

    # Load an explicit policy permitting the capability
    policy = PermissionPolicy(
        policy_id="pol-grant",
        name="Test Grant",
        description="Explicitly allow test.cap",
        requirements=(
            PermissionRequirement("test.cap", TrustLevel.UNTRUSTED),
        ),
    )
    evaluator.load_policy(policy)

    events = []
    async def sub(ev: Event):
        events.append(ev)
    bus.subscribe(Event, sub)

    req = make_request()
    res = await manager.check_permission(req)

    assert res.granted is True

    event_types = [type(e) for e in events]
    assert PermissionRequested in event_types
    assert PolicyEvaluationCompleted in event_types
    assert PermissionGranted in event_types
    assert PermissionDenied not in event_types

@pytest.mark.anyio
async def test_manager_pipeline_denial_via_policy():
    container = await build_container()
    manager = await container.resolve(PermissionManager)
    evaluator = await container.resolve(PolicyEvaluator)
    bus = await container.resolve(EventBus)
    
    policy = PermissionPolicy(
        policy_id="pol", name="n", description="d",
        requirements=(PermissionRequirement("test.cap", TrustLevel.CRITICAL),)
    )
    evaluator.load_policy(policy)
    
    events = []
    bus.subscribe(PermissionDenied, lambda e: events.append(e))
    
    req = make_request(TrustLevel.UNTRUSTED)
    res = await manager.check_permission(req)
    
    assert res.granted is False
    assert res.state == PermissionState.DENIED
    assert len(events) == 1

@pytest.mark.anyio
async def test_manager_pipeline_validation_error():
    container = await build_container()
    manager = await container.resolve(PermissionManager)
    
    res = await manager.check_permission(None)
    assert res.granted is False
    assert res.state == PermissionState.DENIED
    assert "not a PermissionRequest" in res.denial_reason


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def test_public_api():
    import core.security as sec
    
    expected = [
        "SecurityModule",
        "PermissionManager", "PolicyEvaluator", "PermissionAuthorizer", "PermissionValidator",
        "PermissionRequest", "PermissionResult", "PermissionDecision", "PermissionPolicy",
        "PermissionRequirement", "SecurityContext", "PermissionState", "TrustLevel", "PermissionError",
        "PermissionRequested", "PermissionGranted", "PermissionDenied", "PolicyLoaded", "PolicyEvaluationCompleted",
        "SecurityError", "PermissionValidationError", "PolicyNotFoundError", "PermissionDeniedError", "PolicyEvaluationError"
    ]
    
    for exp in expected:
        assert exp in sec.__all__
        assert hasattr(sec, exp)
        
    forbidden = ["SecurityManager", "DefaultPolicyEvaluator", "DefaultPermissionAuthorizer", "DefaultPermissionValidator"]
    for forb in forbidden:
        assert forb not in sec.__all__
