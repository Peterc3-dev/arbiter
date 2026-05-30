"""Pure-logic unit tests for the Tool Registry.

These tests only import ``arbiter_core.tools.registry``, which depends solely
on the standard library (``tomllib``). They do NOT require the TUI stack
(textual/rich) or pyyaml, so they run under a minimal ruff+pytest environment.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from arbiter_core.tools.registry import Tool, ToolRegistry, load_all_tools

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _make_tool(category: str, action: str, node: str, permission: str = "local") -> Tool:
    return Tool(
        name=f"{category}:{action}",
        category=category,
        action=action,
        node=node,
        permission=permission,
    )


def test_register_builds_all_indices():
    reg = ToolRegistry()
    reg.register(_make_tool("browser", "navigate", "nodeA"))
    reg.register(_make_tool("browser", "click", "nodeA"))
    reg.register(_make_tool("git", "commit", "nodeB"))

    assert len(reg.tools) == 3
    # name index keys on category:action
    assert [t.action for t in reg.find_by_name("browser:navigate")] == ["navigate"]
    # node index groups by node
    assert len(reg.find_by_node("nodeA")) == 2
    assert len(reg.find_by_node("nodeB")) == 1
    # category index groups by category
    assert len(reg.find_by_category("browser")) == 2


def test_lookup_misses_return_empty_lists():
    reg = ToolRegistry()
    reg.register(_make_tool("file", "read", "nodeA"))

    assert reg.find_by_name("nope:nope") == []
    assert reg.find_by_node("ghost") == []
    assert reg.find_by_category("ghost") == []


def test_all_categories_and_names_are_sorted_and_unique():
    reg = ToolRegistry()
    reg.register(_make_tool("git", "commit", "nodeB"))
    reg.register(_make_tool("browser", "navigate", "nodeA"))
    reg.register(_make_tool("browser", "click", "nodeA"))

    assert reg.all_categories() == ["browser", "git"]
    assert reg.all_names() == ["browser:click", "browser:navigate", "git:commit"]


def test_summary_counts_tools_per_node():
    reg = ToolRegistry()
    reg.register(_make_tool("browser", "navigate", "nodeA"))
    reg.register(_make_tool("file", "read", "nodeA"))
    reg.register(_make_tool("git", "commit", "nodeB"))

    assert reg.summary() == {"nodeA": 2, "nodeB": 1}


def test_load_all_tools_from_real_config():
    """The loader reads the repo's TOML configs (tomllib, stdlib only)."""
    reg = load_all_tools(CONFIG_DIR)

    assert len(reg.tools) > 0

    tc_cats = {t.category for t in reg.find_by_node("thinkcentre")}
    assert {"browser", "ollama", "kimi"} <= tc_cats

    gpd_cats = {t.category for t in reg.find_by_node("gpd-pocket-4")}
    assert {"claude_code", "git", "github"} <= gpd_cats

    # kimi is declared cloud-permission in the config
    assert all(t.permission == "cloud" for t in reg.find_by_category("kimi"))


def test_load_all_tools_missing_dir_returns_empty(tmp_path):
    reg = load_all_tools(tmp_path / "does-not-exist")
    assert reg.tools == []
