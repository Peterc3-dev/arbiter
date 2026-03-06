"""Tests for Arbiter OS — Tool Registry, Skills, Process Manager."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from arbiter_core.tools.registry import load_all_tools
from arbiter_core.skills import load_all_skills
from arbiter_core.process.manager import ProcessManager, ProcessStatus


def test_tool_registry():
    config_dir = Path(__file__).parent.parent / "config"
    registry = load_all_tools(config_dir)

    assert len(registry.tools) > 0, "No tools loaded"

    # ThinkCentre should have browser, ollama, kimi tools
    tc_tools = registry.find_by_node("thinkcentre")
    tc_cats = set(t.category for t in tc_tools)
    assert "browser" in tc_cats, "ThinkCentre missing browser tools"
    assert "ollama" in tc_cats, "ThinkCentre missing ollama tools"
    assert "kimi" in tc_cats, "ThinkCentre missing kimi tools"

    # GPD should have claude_code, git, github tools
    gpd_tools = registry.find_by_node("gpd-pocket-4")
    gpd_cats = set(t.category for t in gpd_tools)
    assert "claude_code" in gpd_cats, "GPD missing claude_code tools"
    assert "git" in gpd_cats, "GPD missing git tools"
    assert "github" in gpd_cats, "GPD missing github tools"

    # Permission check
    kimi_tools = registry.find_by_category("kimi")
    assert all(t.permission == "cloud" for t in kimi_tools), "Kimi tools should be cloud permission"

    # Category listing
    all_cats = registry.all_categories()
    assert len(all_cats) >= 8, f"Expected 8+ categories, got {len(all_cats)}"


def test_skills():
    skills_dir = Path(__file__).parent.parent / "skills"
    skills = load_all_skills(skills_dir)

    assert len(skills) >= 1, "No skills loaded"

    di = next((s for s in skills if s.name == "domain-intel"), None)
    assert di is not None, "domain-intel skill not found"
    assert len(di.workflow) == 6, f"Expected 6 workflow steps, got {len(di.workflow)}"
    assert "code:execute" in di.requires_tools
    assert di.requires_network is True

    # Check inputs
    target_input = next((i for i in di.inputs if i.name == "target"), None)
    assert target_input is not None, "Missing 'target' input"
    assert target_input.required is True


def test_process_manager():
    pm = ProcessManager()
    assert len(pm.all) == 0

    # Test run + kill (synchronous parts only)
    async def _test_async():
        async def fake_task():
            await asyncio.sleep(100)
            return "done"

        proc = pm.run("test", "test task", "testnode", "testmodel", fake_task())
        assert proc.pid == 1
        assert proc.status == ProcessStatus.RUNNING
        assert len(pm.running) == 1

        killed = pm.kill(1)
        assert killed is True
        await asyncio.sleep(0.1)  # let cancellation propagate
        assert proc.status == ProcessStatus.KILLED

        # Kill nonexistent
        assert pm.kill(999) is False

    asyncio.run(_test_async())


if __name__ == "__main__":
    test_tool_registry()
    print("✓ test_tool_registry passed")
    test_skills()
    print("✓ test_skills passed")
    test_process_manager()
    print("✓ test_process_manager passed")
    print("\nAll Arbiter OS tests passed.")
