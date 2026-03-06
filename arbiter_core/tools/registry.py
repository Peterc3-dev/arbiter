"""
Arbiter OS — Tool Registry

Nodes advertise tools (callable capabilities), not just models.
A tool is anything a node can execute: browser automation, file ops,
code execution, GitHub operations, email, etc.

Tools are declared in TOML per-node and loaded alongside topology.
The registry provides lookup by tool name, node, or capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib


@dataclass
class Tool:
    """A single callable tool on a CIN node."""
    name: str                    # e.g. "browser:navigate"
    category: str               # e.g. "browser"
    action: str                 # e.g. "navigate"
    node: str                   # which CIN node owns this
    description: str = ""
    requires_network: bool = False
    requires_gpu: bool = False
    permission: str = "local"   # "local" or "cloud" (Boo2: 2 levels only)


@dataclass
class ToolRegistry:
    """Registry of all tools across CIN."""
    tools: list[Tool] = field(default_factory=list)
    _index_by_name: dict[str, list[Tool]] = field(default_factory=dict, repr=False)
    _index_by_node: dict[str, list[Tool]] = field(default_factory=dict, repr=False)
    _index_by_category: dict[str, list[Tool]] = field(default_factory=dict, repr=False)

    def register(self, tool: Tool) -> None:
        """Register a tool and update indices."""
        self.tools.append(tool)

        # Index by full name (category:action)
        full_name = f"{tool.category}:{tool.action}"
        self._index_by_name.setdefault(full_name, []).append(tool)

        # Index by node
        self._index_by_node.setdefault(tool.node, []).append(tool)

        # Index by category
        self._index_by_category.setdefault(tool.category, []).append(tool)

    def find_by_name(self, name: str) -> list[Tool]:
        """Find tools by full name (category:action)."""
        return self._index_by_name.get(name, [])

    def find_by_node(self, node: str) -> list[Tool]:
        """Find all tools on a specific node."""
        return self._index_by_node.get(node, [])

    def find_by_category(self, category: str) -> list[Tool]:
        """Find all tools in a category (e.g. 'browser', 'file', 'github')."""
        return self._index_by_category.get(category, [])

    def all_categories(self) -> list[str]:
        """List all tool categories."""
        return sorted(self._index_by_category.keys())

    def all_names(self) -> list[str]:
        """List all tool names."""
        return sorted(self._index_by_name.keys())

    def summary(self) -> dict[str, int]:
        """Tools per node summary."""
        return {node: len(tools) for node, tools in self._index_by_node.items()}


def load_tools_from_node_config(config_dir: Path) -> ToolRegistry:
    """Load tool declarations from all node TOML configs.

    Tools are declared in [tools.registry] sections:

        [tools.registry.browser]
        actions = ["navigate", "screenshot", "click", "extract"]
        description = "Browser automation via OpenClaw"
        requires_network = true
        permission = "local"
    """
    registry = ToolRegistry()
    nodes_dir = config_dir / "nodes"

    if not nodes_dir.exists():
        return registry

    for toml_file in sorted(nodes_dir.glob("*.toml")):
        with open(toml_file, "rb") as f:
            data = tomllib.load(f)

        node_name = data.get("node", {}).get("name", toml_file.stem)
        tool_registry = data.get("tools", {}).get("registry", {})

        for category, tool_data in tool_registry.items():
            actions = tool_data.get("actions", [])
            description = tool_data.get("description", "")
            requires_network = tool_data.get("requires_network", False)
            requires_gpu = tool_data.get("requires_gpu", False)
            permission = tool_data.get("permission", "local")

            for action in actions:
                tool = Tool(
                    name=f"{category}:{action}",
                    category=category,
                    action=action,
                    node=node_name,
                    description=description,
                    requires_network=requires_network,
                    requires_gpu=requires_gpu,
                    permission=permission,
                )
                registry.register(tool)

    return registry


def load_tools_from_tool_configs(config_dir: Path) -> ToolRegistry:
    """Load standalone tool config files from config/tools/.

    For tools that don't belong to a specific node (cloud APIs, etc).
    """
    registry = ToolRegistry()
    tools_dir = config_dir / "tools"

    if not tools_dir.exists():
        return registry

    for toml_file in sorted(tools_dir.glob("*.toml")):
        with open(toml_file, "rb") as f:
            data = tomllib.load(f)

        node = data.get("node", "cloud")
        categories = data.get("categories", {})

        for category, tool_data in categories.items():
            actions = tool_data.get("actions", [])
            description = tool_data.get("description", "")
            requires_network = tool_data.get("requires_network", True)
            permission = tool_data.get("permission", "cloud")

            for action in actions:
                tool = Tool(
                    name=f"{category}:{action}",
                    category=category,
                    action=action,
                    node=node,
                    description=description,
                    requires_network=requires_network,
                    permission=permission,
                )
                registry.register(tool)

    return registry


def load_all_tools(config_dir: Path) -> ToolRegistry:
    """Load tools from all sources — node configs + standalone tool configs."""
    registry = load_tools_from_node_config(config_dir)
    standalone = load_tools_from_tool_configs(config_dir)

    for tool in standalone.tools:
        registry.register(tool)

    return registry
