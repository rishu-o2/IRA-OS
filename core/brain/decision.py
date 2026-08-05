from __future__ import annotations

from .context import BrainContext
from .exceptions import BrainDecisionError
from .models import BrainDecision, BrainDecisionType


class DecisionEngine:
    """Convert planner output into a Brain decision without executing it."""

    def decide(self, context: BrainContext) -> BrainDecision:
        if context.identity is None:
            raise BrainDecisionError("Identity context is required for decision generation.")
        if context.planner_input is None:
            raise BrainDecisionError("Planner input is required for decision generation.")
        if context.planner_output is None:
            raise BrainDecisionError("Planner output is required for decision generation.")

        return BrainDecision(
            request_id=context.request.request_id,
            user_id=context.identity.identity_id,
            decision_type=BrainDecisionType.PLAN_READY,
            plan_summary=context.planner_output,
            memory_count=len(context.retrieved_memory),
            metadata={
                "intent": context.planner_input.intent,
                "planner_goal_id": context.planner_input.goal_id,
            },
        )
