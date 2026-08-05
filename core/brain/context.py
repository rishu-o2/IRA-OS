from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Mapping

from core.memory.models import SearchResult

from .models import (
    BrainAnalysis,
    BrainDecision,
    BrainIdentityContext,
    BrainPlannerInput,
    BrainPlanSummary,
    BrainRequest,
    ConversationTurn,
)


def _metadata(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class BrainContext:
    request: BrainRequest
    identity: BrainIdentityContext | None = None
    conversation_context: tuple[ConversationTurn, ...] = field(default_factory=tuple)
    retrieved_memory: tuple[SearchResult, ...] = field(default_factory=tuple)
    analysis: BrainAnalysis | None = None
    planner_input: BrainPlannerInput | None = None
    planner_output: BrainPlanSummary | None = None
    decision: BrainDecision | None = None
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "conversation_context", tuple(self.conversation_context))
        object.__setattr__(self, "retrieved_memory", tuple(self.retrieved_memory))
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    @classmethod
    def from_request(cls, request: BrainRequest) -> "BrainContext":
        return cls(request=request, metadata={"request_id": request.request_id})

    def with_identity(self, identity: BrainIdentityContext) -> "BrainContext":
        return replace(self, identity=identity)

    def with_conversation_context(self, conversation_context: tuple[ConversationTurn, ...]) -> "BrainContext":
        return replace(self, conversation_context=tuple(conversation_context))

    def with_analysis(self, analysis: BrainAnalysis) -> "BrainContext":
        return replace(self, analysis=analysis)

    def with_retrieved_memory(self, retrieved_memory: tuple[SearchResult, ...]) -> "BrainContext":
        return replace(self, retrieved_memory=tuple(retrieved_memory))

    def with_planner_input(self, planner_input: BrainPlannerInput) -> "BrainContext":
        return replace(self, planner_input=planner_input)

    def with_planner_output(self, planner_output: BrainPlanSummary) -> "BrainContext":
        return replace(self, planner_output=planner_output)

    def with_decision(self, decision: BrainDecision) -> "BrainContext":
        return replace(self, decision=decision)

    def with_metadata(self, **metadata: Any) -> "BrainContext":
        merged = dict(self.metadata)
        merged.update(metadata)
        return replace(self, metadata=merged)
