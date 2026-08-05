from __future__ import annotations

from typing import Any

from .context import BrainContext
from .exceptions import BrainProcessingError, BrainValidationError
from .models import BrainAnalysis, BrainPlannerInput, ConversationTurn


class ReasoningEngine:
    """Prepare deterministic request inputs without AI, tools, or planning."""

    def analyze(self, context: BrainContext) -> BrainAnalysis:
        normalized_text = self.normalize_request(context.request.payload)
        intent = self.prepare_intent(context.request.metadata, normalized_text)
        memory_query_text = str(context.request.metadata.get("memory_query", normalized_text)).strip()
        memory_tags = context.request.metadata.get("memory_tags", ())
        return BrainAnalysis(
            normalized_text=normalized_text,
            intent=intent,
            memory_query_text=memory_query_text or normalized_text,
            memory_tags=memory_tags,
            metadata={
                "payload_type": type(context.request.payload).__name__,
                "conversation_turns": len(context.conversation_context),
            },
        )

    def prepare_planner_input(self, context: BrainContext) -> BrainPlannerInput:
        if context.identity is None:
            raise BrainProcessingError("Identity context is required before preparing planner input.")
        if context.analysis is None:
            raise BrainProcessingError("Request analysis is required before preparing planner input.")

        goal_id = str(
            context.request.metadata.get("planner_goal_id")
            or context.request.metadata.get("goal_id")
            or ""
        ).strip()
        if not goal_id:
            raise BrainValidationError("BrainRequest.metadata.goal_id must be provided for planner invocation.")

        return BrainPlannerInput(
            goal_id=goal_id,
            request_id=context.request.request_id,
            user_id=context.identity.identity_id,
            normalized_request=context.analysis.normalized_text,
            intent=context.analysis.intent,
            memory_ids=tuple(result.record.id for result in context.retrieved_memory),
            metadata={
                "memory_count": len(context.retrieved_memory),
                "source": "Brain",
            },
        )

    def conversation_context(self, raw_value: Any) -> tuple[ConversationTurn, ...]:
        if raw_value is None:
            return ()
        if not isinstance(raw_value, (list, tuple)):
            raise BrainValidationError("BrainRequest.metadata.conversation_context must be a sequence.")

        turns: list[ConversationTurn] = []
        for item in raw_value:
            if isinstance(item, ConversationTurn):
                turns.append(item)
            elif isinstance(item, dict):
                turns.append(
                    ConversationTurn(
                        role=str(item.get("role", "unknown")),
                        content=str(item.get("content", "")),
                        metadata=item.get("metadata", {}),
                    )
                )
            else:
                raise BrainValidationError("Conversation context items must be ConversationTurn or mapping values.")
        return tuple(turns)

    def normalize_request(self, payload: Any) -> str:
        if isinstance(payload, str):
            normalized = " ".join(payload.split())
        elif isinstance(payload, dict):
            normalized = " ".join(f"{key}={payload[key]}" for key in sorted(payload))
        else:
            normalized = str(payload).strip()

        if not normalized:
            raise BrainValidationError("BrainRequest.payload must contain usable request content.")
        return normalized

    def prepare_intent(self, metadata: Any, normalized_text: str) -> str:
        if "intent" in metadata:
            intent = str(metadata["intent"]).strip()
            if intent:
                return intent

        lowered = normalized_text.lower()
        if lowered.startswith(("what ", "why ", "how ", "when ", "where ", "who ")):
            return "answer"
        return "coordinate"
