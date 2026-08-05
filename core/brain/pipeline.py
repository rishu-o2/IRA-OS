from __future__ import annotations

from typing import Iterable

from core.identity import IdentityManager
from core.logging import Logger
from core.memory import MemoryManager
from core.memory.models import SearchQuery
from core.planner import PlannerManager

from .context import BrainContext
from .decision import DecisionEngine
from .exceptions import (
    BrainDecisionError,
    BrainIdentityResolutionError,
    BrainMemoryError,
    BrainPlannerError,
    BrainValidationError,
)
from .models import BrainIdentityContext, BrainPlanSummary, BrainRequest, BrainResult
from .reasoning import ReasoningEngine


class BrainPipelineStage:
    name = "BrainPipelineStage"

    async def run(self, context: BrainContext) -> BrainContext:
        raise NotImplementedError(f"{self.__class__.__name__}.run must be implemented.")


class ValidateRequestStage(BrainPipelineStage):
    name = "validate_request"

    async def run(self, context: BrainContext) -> BrainContext:
        request = context.request
        if not isinstance(request, BrainRequest):
            raise BrainValidationError("BrainPipeline requires a BrainRequest.")
        if not request.request_id:
            raise BrainValidationError("BrainRequest.request_id must not be empty.")
        if not request.user_id:
            raise BrainValidationError("BrainRequest.user_id must not be empty.")
        if request.payload is None:
            raise BrainValidationError("BrainRequest.payload must not be None.")
        return context


class ConversationContextStage(BrainPipelineStage):
    name = "conversation_context"

    def __init__(self, reasoning_engine: ReasoningEngine):
        self._reasoning_engine = reasoning_engine

    async def run(self, context: BrainContext) -> BrainContext:
        raw_context = context.request.metadata.get("conversation_context")
        return context.with_conversation_context(self._reasoning_engine.conversation_context(raw_context))


class ResolveIdentityStage(BrainPipelineStage):
    name = "resolve_identity"

    def __init__(self, identity_manager: IdentityManager):
        self._identity_manager = identity_manager

    async def run(self, context: BrainContext) -> BrainContext:
        identity = self._identity_manager.get_identity(context.request.user_id)
        if identity is None:
            raise BrainIdentityResolutionError("Brain identity could not be resolved.")
        if not identity.active:
            raise BrainIdentityResolutionError("Brain identity is inactive.")
        return context.with_identity(BrainIdentityContext.from_identity(identity))


class AnalyzeRequestStage(BrainPipelineStage):
    name = "analyze_request"

    def __init__(self, reasoning_engine: ReasoningEngine):
        self._reasoning_engine = reasoning_engine

    async def run(self, context: BrainContext) -> BrainContext:
        return context.with_analysis(self._reasoning_engine.analyze(context))


class RetrieveMemoryStage(BrainPipelineStage):
    name = "retrieve_memory"

    def __init__(self, memory_manager: MemoryManager):
        self._memory_manager = memory_manager

    async def run(self, context: BrainContext) -> BrainContext:
        if context.analysis is None:
            raise BrainMemoryError("Request analysis is required before memory retrieval.")

        try:
            limit = int(context.request.metadata.get("memory_limit", 10))
        except (TypeError, ValueError) as exc:
            raise BrainValidationError("BrainRequest.metadata.memory_limit must be an integer.") from exc

        namespace_value = context.request.metadata.get("memory_namespace")
        namespace = str(namespace_value) if namespace_value is not None else None
        query = SearchQuery(
            text=context.analysis.memory_query_text,
            tags=context.analysis.memory_tags,
            namespace=namespace,
            limit=limit,
        )
        try:
            results = await self._memory_manager.search(query)
        except Exception as exc:
            raise BrainMemoryError("Brain memory retrieval failed.") from exc
        return context.with_retrieved_memory(tuple(results))


class BuildPlannerInputStage(BrainPipelineStage):
    name = "build_planner_input"

    def __init__(self, reasoning_engine: ReasoningEngine):
        self._reasoning_engine = reasoning_engine

    async def run(self, context: BrainContext) -> BrainContext:
        return context.with_planner_input(self._reasoning_engine.prepare_planner_input(context))


class InvokePlannerStage(BrainPipelineStage):
    name = "invoke_planner"

    def __init__(self, planner_manager: PlannerManager):
        self._planner_manager = planner_manager

    async def run(self, context: BrainContext) -> BrainContext:
        if context.planner_input is None:
            raise BrainPlannerError("Planner input is required before planner invocation.")

        result = await self._planner_manager.build_plan(context.planner_input.goal_id)
        if not result.success or result.plan is None:
            raise BrainPlannerError("Brain planner invocation failed.")

        plan = result.plan
        summary = BrainPlanSummary(
            goal_id=plan.goal.id,
            task_ids=tuple(task.id for task in plan.tasks),
            estimated_steps=plan.estimated_steps,
            created_at=plan.created_at,
        )
        return context.with_planner_output(summary)


class MakeDecisionStage(BrainPipelineStage):
    name = "make_decision"

    def __init__(self, decision_engine: DecisionEngine):
        self._decision_engine = decision_engine

    async def run(self, context: BrainContext) -> BrainContext:
        try:
            decision = self._decision_engine.decide(context)
        except BrainDecisionError:
            raise
        except Exception as exc:
            raise BrainDecisionError("Brain decision generation failed.") from exc
        return context.with_decision(decision)


class BrainPipeline:
    def __init__(self, stages: Iterable[BrainPipelineStage], logger: Logger):
        self._stages = tuple(stages)
        self._logger = logger
        if not self._stages:
            raise BrainValidationError("BrainPipeline requires at least one stage.")

    @property
    def stages(self) -> tuple[BrainPipelineStage, ...]:
        return self._stages

    async def execute(self, request: BrainRequest) -> BrainResult:
        context = BrainContext.from_request(request)
        for stage in self._stages:
            self._logger.debug("Brain pipeline stage running.", stage=stage.name, request_id=request.request_id)
            context = await stage.run(context)

        if context.decision is None:
            raise BrainDecisionError("Brain pipeline completed without a decision.")
        return BrainResult(success=True, decision=context.decision, request_id=request.request_id)
