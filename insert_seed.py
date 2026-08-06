HELPER = """
async def seed_test_capability(container) -> None:
    from unittest.mock import AsyncMock, MagicMock
    from core.runtime.interfaces import CapabilityRegistry
    from core.runtime.models import CapabilityMetadata
    from core.security.contracts import PolicyEvaluator
    from core.security.models import PermissionPolicy, PermissionRequirement, TrustLevel
    cap = MagicMock()
    cap.metadata = CapabilityMetadata(id="test.cap", name="Test", description="", version="1")
    cap.execute = AsyncMock(return_value={"ok": True})
    registry = await container.resolve(CapabilityRegistry)
    await registry.register(cap)
    policy = PermissionPolicy(
        policy_id="pol-test", name="Test Policy", description="Allow test.cap",
        requirements=(PermissionRequirement("test.cap", TrustLevel.UNTRUSTED),),
    )
    evaluator = await container.resolve(PolicyEvaluator)
    evaluator.load_policy(policy)

"""

with open("tests/core/workflow/test_workflow.py", "r") as f:
    lines = f.readlines()

lines.insert(95, HELPER)

with open("tests/core/workflow/test_workflow.py", "w") as f:
    f.writelines(lines)

print("Inserted seed helper")
