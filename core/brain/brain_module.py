from core.container import ContainerProtocol, Lifetime, Module
from core.events import EventBus
from core.identity import IdentityManager
from core.logging import LoggerFactory
from core.memory import MemoryManager
from core.planner import PlannerManager

from .decision import DecisionEngine
from .manager import BrainManager
from .pipeline import (
    AnalyzeRequestStage,
    BrainPipeline,
    BuildPlannerInputStage,
    ConversationContextStage,
    InvokePlannerStage,
    MakeDecisionStage,
    ResolveIdentityStage,
    RetrieveMemoryStage,
    ValidateRequestStage,
)
from .reasoning import ReasoningEngine


class BrainModule(Module):
    """DI module for the Brain subsystem."""

    def configure(self, container: ContainerProtocol) -> None:
        container.register_singleton(ReasoningEngine)
        container.register_singleton(DecisionEngine)

        async def build_pipeline() -> BrainPipeline:
            reasoning_engine = await container.resolve(ReasoningEngine)
            decision_engine = await container.resolve(DecisionEngine)
            identity_manager = await container.resolve(IdentityManager)
            memory_manager = await container.resolve(MemoryManager)
            planner_manager = await container.resolve(PlannerManager)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.brain.pipeline")
            return BrainPipeline(
                stages=(
                    ValidateRequestStage(),
                    ConversationContextStage(reasoning_engine),
                    ResolveIdentityStage(identity_manager),
                    AnalyzeRequestStage(reasoning_engine),
                    RetrieveMemoryStage(memory_manager),
                    BuildPlannerInputStage(reasoning_engine),
                    InvokePlannerStage(planner_manager),
                    MakeDecisionStage(decision_engine),
                ),
                logger=logger,
            )

        async def build_brain_manager() -> BrainManager:
            pipeline = await container.resolve(BrainPipeline)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.brain")
            event_bus = None
            if container.has(EventBus):
                event_bus = await container.resolve(EventBus)
            return BrainManager(pipeline=pipeline, logger=logger, event_bus=event_bus)

        container.register_factory(BrainPipeline, factory=build_pipeline, lifetime=Lifetime.SINGLETON)
        container.register_factory(BrainManager, factory=build_brain_manager, lifetime=Lifetime.SINGLETON)
