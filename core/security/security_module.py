from core.container import ContainerProtocol, Lifetime, Module
from core.events import EventBus
from core.logging import LoggerFactory

from .authorizer import DefaultPermissionAuthorizer
from .contracts import PermissionAuthorizer, PermissionManager, PermissionValidator, PolicyEvaluator
from .manager import SecurityManager
from .policy import DefaultPolicyEvaluator
from .validator import DefaultPermissionValidator


class SecurityModule(Module):
    """DI module for the Permission & Security subsystem."""

    def configure(self, container: ContainerProtocol) -> None:
        container.register_singleton(PermissionValidator, DefaultPermissionValidator)
        container.register_singleton(PermissionAuthorizer, DefaultPermissionAuthorizer)

        async def build_policy_evaluator() -> PolicyEvaluator:
            return DefaultPolicyEvaluator()

        async def build_manager() -> PermissionManager:
            validator = await container.resolve(PermissionValidator)
            policy_evaluator = await container.resolve(PolicyEvaluator)
            authorizer = await container.resolve(PermissionAuthorizer)
            event_bus = await container.resolve(EventBus)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.security")

            return SecurityManager(
                validator=validator,
                policy_evaluator=policy_evaluator,
                authorizer=authorizer,
                event_bus=event_bus,
                logger=logger,
            )

        container.register_factory(PolicyEvaluator, factory=build_policy_evaluator, lifetime=Lifetime.SINGLETON)
        container.register_factory(PermissionManager, factory=build_manager, lifetime=Lifetime.SINGLETON)
