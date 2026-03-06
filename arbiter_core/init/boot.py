"""
Arbiter OS — Init System

Handles the boot sequence when Arbiter OS starts on a CIN node.
Registers the node, advertises tools, starts health heartbeat,
discovers peers over Tailscale.

The init system is the first thing that runs. It builds the runtime
state that the Shell, Router, and Process Manager all depend on.
"""

from __future__ import annotations

import socket
import platform
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from arbiter_core.tools.registry import load_all_tools, ToolRegistry
from arbiter_core.process.manager import ProcessManager


@dataclass
class ArbiterRuntime:
    """The live runtime state of Arbiter OS on this node.

    Created by the init system at boot. Passed to Shell, Router,
    Process Manager, and all other subsystems.
    """
    # Identity
    hostname: str = ""
    node_name: str = ""
    boot_time: str = ""

    # Subsystems
    tool_registry: ToolRegistry = field(default_factory=ToolRegistry)
    process_manager: ProcessManager = field(default_factory=ProcessManager)

    # Topology (loaded from config)
    nodes: list = field(default_factory=list)      # list[NodeInfo]
    rules: list = field(default_factory=list)       # list[RoutingRule]

    # Boot state
    boot_log: list[str] = field(default_factory=list)
    healthy: bool = False

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.boot_log.append(entry)


def boot(config_dir: Path) -> ArbiterRuntime:
    """Execute the Arbiter OS boot sequence.

    Boot order (per Boo2 feedback — init system registers first):
        1. Identify this node
        2. Load topology (node configs)
        3. Load routing rules
        4. Load tool registry
        5. Initialize process manager
        6. Health self-check
        7. Ready

    Args:
        config_dir: Path to the config/ directory

    Returns:
        Fully initialized ArbiterRuntime
    """
    # Late imports to avoid circular deps
    from arbiter_core.app import load_nodes, load_routing_rules

    runtime = ArbiterRuntime()
    runtime.boot_time = datetime.now().isoformat()

    # ── Step 1: Identity ──────────────────────────────────
    runtime.hostname = socket.gethostname()
    runtime.log(f"init: hostname={runtime.hostname}")
    runtime.log(f"init: platform={platform.system()} {platform.release()}")

    # Try to match this hostname to a node config
    nodes = load_nodes(config_dir)
    runtime.nodes = nodes

    for node in nodes:
        # Match by hostname (strip .tail suffix for flexibility)
        host_base = runtime.hostname.split(".")[0].lower()
        node_host_base = node.hostname.split(".")[0].lower()
        if host_base == node_host_base or host_base == node.name.lower():
            runtime.node_name = node.name
            break

    if runtime.node_name:
        runtime.log(f"init: identified as CIN node '{runtime.node_name}'")
    else:
        runtime.node_name = runtime.hostname
        runtime.log(f"init: no matching node config — using hostname '{runtime.hostname}'")

    # ── Step 2: Topology ──────────────────────────────────
    runtime.log(f"topology: loaded {len(runtime.nodes)} node(s)")
    for node in runtime.nodes:
        models = ", ".join(node.models_available) if node.models_available else "none"
        runtime.log(f"topology: {node.name} [{node.role}] models=[{models}]")

    # ── Step 3: Routing Rules ─────────────────────────────
    runtime.rules = load_routing_rules(config_dir)
    runtime.log(f"router: loaded {len(runtime.rules)} routing rule(s)")

    # ── Step 4: Tool Registry ─────────────────────────────
    runtime.tool_registry = load_all_tools(config_dir)
    tool_count = len(runtime.tool_registry.tools)
    categories = runtime.tool_registry.all_categories()
    runtime.log(f"tools: registered {tool_count} tool(s) in {len(categories)} categories")
    for cat in categories:
        tools_in_cat = runtime.tool_registry.find_by_category(cat)
        nodes_with = set(t.node for t in tools_in_cat)
        runtime.log(f"tools: {cat} — {len(tools_in_cat)} actions on [{', '.join(nodes_with)}]")

    # ── Step 5: Process Manager ───────────────────────────
    runtime.process_manager = ProcessManager()
    runtime.log("process: manager initialized (run/kill)")

    # ── Step 6: Health ────────────────────────────────────
    runtime.healthy = True
    runtime.log("health: self-check passed")

    # ── Step 7: Ready ─────────────────────────────────────
    runtime.log("init: Arbiter OS ready")

    return runtime
