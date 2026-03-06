"""
ARBITER OS v0.2 — Distributed Intelligence Operating System
Autonomous Routing, Bridging, and Inference Topology for Engineered Reasoning

Intelligence shell for CIN (Centralized Inference Network)
"""

from __future__ import annotations

import tomllib
import os
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    RichLog,
    Label,
)
from textual.binding import Binding
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from arbiter_core.tools.registry import load_all_tools, ToolRegistry
from arbiter_core.process.manager import ProcessManager, ProcessStatus
from arbiter_core.skills import load_all_skills, Skill


# ─── Data Models ───────────────────────────────────────────────────

@dataclass
class NodeHardware:
    cpu: str = "unknown"
    ram_gb: int = 0
    gpu: str = "none"
    gpu_arch: str = ""
    compute_backend: str = "cpu"


@dataclass
class NodeInfo:
    name: str = ""
    hostname: str = ""
    role: str = ""
    description: str = ""
    hardware: NodeHardware = field(default_factory=NodeHardware)
    models_available: list[str] = field(default_factory=list)
    default_model: str = ""
    services: dict[str, bool] = field(default_factory=dict)
    online: bool = False  # Phase 1: live polling
    cpu_percent: float = 0.0  # Phase 1: live metrics
    ram_used_gb: float = 0.0  # Phase 1: live metrics


@dataclass
class RoutingRule:
    task_type: str = ""
    description: str = ""
    prefer_model: str = ""
    prefer_node: str = ""
    via: str = ""
    timeout_s: int = 60
    fallback: list[str] = field(default_factory=list)


@dataclass
class ContextEntry:
    timestamp: str = ""
    action: str = ""
    detail: str = ""


# ─── Config Loader ────────────────────────────────────────────────

def load_nodes(config_dir: Path) -> list[NodeInfo]:
    """Load all node TOML configs from the nodes directory."""
    nodes = []
    nodes_dir = config_dir / "nodes"
    if not nodes_dir.exists():
        return nodes

    for toml_file in sorted(nodes_dir.glob("*.toml")):
        with open(toml_file, "rb") as f:
            data = tomllib.load(f)

        node_data = data.get("node", {})
        hw_data = data.get("hardware", {})
        models_data = data.get("models", {})
        services_data = data.get("services", {})

        hw = NodeHardware(
            cpu=hw_data.get("cpu", "unknown"),
            ram_gb=hw_data.get("ram_gb", 0),
            gpu=hw_data.get("gpu", "none"),
            gpu_arch=hw_data.get("gpu_arch", ""),
            compute_backend=hw_data.get("compute_backend", "cpu"),
        )

        node = NodeInfo(
            name=node_data.get("name", toml_file.stem),
            hostname=node_data.get("hostname", ""),
            role=node_data.get("role", ""),
            description=node_data.get("description", ""),
            hardware=hw,
            models_available=models_data.get("available", []),
            default_model=models_data.get("default", ""),
            services=services_data,
            online=True,  # Phase 0: assume online
            cpu_percent=0.0,
            ram_used_gb=0.0,
        )
        nodes.append(node)
    return nodes


def load_routing_rules(config_dir: Path) -> list[RoutingRule]:
    """Load routing rules from TOML."""
    rules_file = config_dir / "routing.toml"
    if not rules_file.exists():
        return []

    with open(rules_file, "rb") as f:
        data = tomllib.load(f)

    rules = []
    for rule_data in data.get("rule", []):
        rule = RoutingRule(
            task_type=rule_data.get("task_type", ""),
            description=rule_data.get("description", ""),
            prefer_model=rule_data.get("prefer_model", ""),
            prefer_node=rule_data.get("prefer_node", ""),
            via=rule_data.get("via", ""),
            timeout_s=rule_data.get("timeout_s", 60),
            fallback=rule_data.get("fallback", []),
        )
        rules.append(rule)
    return rules


# ─── TUI Widgets ──────────────────────────────────────────────────

PHOSPHOR = "#33ff33"
PHOSPHOR_DIM = "#1a8c1a"
DARK_BG = "#0a0a0a"
SCANLINE = "#0d1a0d"


class TopologyPanel(Static):
    """Displays CIN node status."""

    def __init__(self, nodes: list[NodeInfo], **kwargs):
        super().__init__(**kwargs)
        self.nodes = nodes

    def render(self) -> Text:
        lines = []
        lines.append(Text("  T O P O L O G Y", style=f"bold {PHOSPHOR}"))
        lines.append(Text(""))

        for node in self.nodes:
            status = "●" if node.online else "○"
            color = PHOSPHOR if node.online else "red"
            lines.append(Text(f"  {status} {node.name}", style=f"bold {color}"))
            lines.append(Text(f"    role: {node.role}", style=PHOSPHOR_DIM))
            lines.append(Text(f"    cpu:  {node.hardware.cpu[:28]}", style=PHOSPHOR_DIM))
            lines.append(Text(f"    ram:  {node.hardware.ram_gb}GB", style=PHOSPHOR_DIM))
            lines.append(Text(f"    gpu:  {node.hardware.gpu[:28]}", style=PHOSPHOR_DIM))
            lines.append(Text(f"    backend: {node.hardware.compute_backend}", style=PHOSPHOR_DIM))

            if node.models_available:
                models_str = ", ".join(node.models_available[:3])
                lines.append(Text(f"    models: {models_str}", style=PHOSPHOR_DIM))

            svc_up = [k for k, v in node.services.items() if v]
            if svc_up:
                lines.append(Text(f"    svcs: {', '.join(svc_up)}", style=PHOSPHOR_DIM))

            lines.append(Text(""))

        result = Text()
        for line in lines:
            result.append(line)
            result.append("\n")
        return result


class ContextPanel(RichLog):
    """Scrollable context thread / event log."""
    pass


# ─── Main Application ────────────────────────────────────────────

class ArbiterApp(App):
    """Arbiter TUI — CIN Command Fabric"""

    CSS = f"""
    Screen {{
        background: {DARK_BG};
    }}

    #title-bar {{
        height: 3;
        background: #0d0d0d;
        border-bottom: solid {PHOSPHOR_DIM};
        padding: 0 2;
    }}

    #title-text {{
        color: {PHOSPHOR};
        text-style: bold;
    }}

    #main-container {{
        height: 1fr;
    }}

    #topology-panel {{
        width: 38;
        border-right: solid {PHOSPHOR_DIM};
        padding: 1;
        background: {DARK_BG};
    }}

    #context-panel {{
        width: 1fr;
        padding: 1;
        background: {DARK_BG};
        color: {PHOSPHOR};
    }}

    #input-container {{
        height: 3;
        border-top: solid {PHOSPHOR_DIM};
        background: #0d0d0d;
        padding: 0 1;
    }}

    #command-input {{
        background: {DARK_BG};
        color: {PHOSPHOR};
        border: none;
    }}

    #command-input:focus {{
        border: none;
    }}

    Footer {{
        background: #0d0d0d;
        color: {PHOSPHOR_DIM};
    }}

    Header {{
        background: #0d0d0d;
        color: {PHOSPHOR};
    }}

    RichLog {{
        background: {DARK_BG};
        color: {PHOSPHOR};
        scrollbar-color: {PHOSPHOR_DIM};
        scrollbar-color-active: {PHOSPHOR};
        scrollbar-color-hover: {PHOSPHOR};
    }}
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+t", "show_topology", "Topology"),
        Binding("ctrl+r", "show_rules", "Rules"),
        Binding("ctrl+l", "clear_log", "Clear"),
    ]

    def __init__(self, config_dir: Path | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config_dir = config_dir or Path(__file__).parent.parent / "config"
        self.skills_dir = self.config_dir.parent / "skills"
        self.nodes = load_nodes(self.config_dir)
        self.rules = load_routing_rules(self.config_dir)
        self.tool_registry = load_all_tools(self.config_dir)
        self.process_manager = ProcessManager()
        self.skills = load_all_skills(self.skills_dir)
        self.context_log: list[ContextEntry] = []

    def compose(self) -> ComposeResult:
        node_count = len(self.nodes)
        online_count = sum(1 for n in self.nodes if n.online)
        tool_count = len(self.tool_registry.tools)

        yield Container(
            Static(
                f"  A R B I T E R  OS v0.2       CIN: {node_count} nodes ● {online_count} online  │  {tool_count} tools",
                id="title-text",
            ),
            id="title-bar",
        )

        with Horizontal(id="main-container"):
            yield TopologyPanel(self.nodes, id="topology-panel")
            yield ContextPanel(id="context-panel", highlight=True, markup=True)

        with Container(id="input-container"):
            yield Input(placeholder="arbiter> ", id="command-input")

    def on_mount(self) -> None:
        ctx = self.query_one("#context-panel", ContextPanel)
        ctx.write(Text("  A R B I T E R   O S", style=f"bold {PHOSPHOR}"))
        ctx.write(Text("  Distributed Intelligence Operating System", style=PHOSPHOR_DIM))
        ctx.write("")

        # Boot sequence
        self._log_event("init", "Booting Arbiter OS...")
        self._log_event("init", f"Topology: {len(self.nodes)} node(s)")
        self._log_event("init", f"Router: {len(self.rules)} routing rule(s)")
        self._log_event("init", f"Tools: {len(self.tool_registry.tools)} tool(s) in {len(self.tool_registry.all_categories())} categories")
        self._log_event("init", f"Skills: {len(self.skills)} skill(s) loaded")
        self._log_event("init", f"Process Manager: ready (run/kill)")

        # Tool summary per node
        summary = self.tool_registry.summary()
        for node_name, count in summary.items():
            self._log_event("tools", f"{node_name}: {count} tools registered")

        ctx.write("")
        self._log_event("init", "Arbiter OS ready. Type 'help' for commands.")

        self.query_one("#command-input", Input).focus()

    def _log_event(self, category: str, message: str) -> None:
        ctx = self.query_one("#context-panel", ContextPanel)
        now = datetime.now().strftime("%H:%M:%S")
        cat_colors = {
            "system": "bold #33ff33",
            "init": "bold #00ffaa",
            "topology": "#1aff1a",
            "routing": "#66ff66",
            "route": "bold #00ff88",
            "tools": "#33ccff",
            "skill": "bold #ff9933",
            "proc": "bold #ffcc00",
            "error": "bold red",
            "ctx": "#33ffaa",
        }
        style = cat_colors.get(category, PHOSPHOR_DIM)
        prefix = Text(f"  [{now}] ", style=PHOSPHOR_DIM)
        tag = Text(f"[{category}] ", style=style)
        msg = Text(message, style=PHOSPHOR)
        line = Text()
        line.append(prefix)
        line.append(tag)
        line.append(msg)
        ctx.write(line)

        self.context_log.append(ContextEntry(
            timestamp=now, action=category, detail=message
        ))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        event.input.value = ""

        if not cmd:
            return

        self._log_event("ctx", f"$ {cmd}")
        self._handle_command(cmd)

    def _handle_command(self, cmd: str) -> None:
        parts = cmd.split()
        command = parts[0].lower()
        args = parts[1:]

        handlers = {
            "help": self._cmd_help,
            "topology": self._cmd_topology,
            "nodes": self._cmd_topology,
            "rules": self._cmd_rules,
            "route": self._cmd_route,
            "tools": self._cmd_tools,
            "skills": self._cmd_skills,
            "ps": self._cmd_ps,
            "kill": self._cmd_kill,
            "ctx": self._cmd_ctx,
            "briefing": self._cmd_briefing,
            "health": self._cmd_health,
            "clear": self._cmd_clear,
        }

        handler = handlers.get(command)
        if handler:
            handler(args)
        else:
            self._log_event("error", f"Unknown command: {command}. Type 'help'.")

    def _cmd_help(self, args: list[str]) -> None:
        commands = [
            ("", "── CORE ──"),
            ("help", "Show this message"),
            ("topology", "Show all CIN nodes and status"),
            ("health", "System health overview"),
            ("", "── ROUTING ──"),
            ("rules", "Show routing rules"),
            ("route <type>", "Route a task through CIN"),
            ("", "── OS LAYER ──"),
            ("tools [node]", "Show tool registry (optionally filter by node)"),
            ("skills", "Show installed skill plugins"),
            ("ps", "List running processes"),
            ("kill <pid>", "Kill a running process"),
            ("", "── CONTEXT ──"),
            ("ctx", "Show context thread summary"),
            ("briefing", "Generate a briefing snapshot"),
            ("clear", "Clear the context panel"),
        ]
        for name, desc in commands:
            if not name:
                self._log_event("system", f"  {desc}")
            else:
                self._log_event("system", f"  {name:18s} {desc}")

    def _cmd_tools(self, args: list[str]) -> None:
        if args:
            # Filter by node
            node_name = args[0]
            tools = self.tool_registry.find_by_node(node_name)
            if not tools:
                self._log_event("error", f"No tools found for node '{node_name}'")
                available_nodes = list(self.tool_registry.summary().keys())
                self._log_event("tools", f"Nodes with tools: {', '.join(available_nodes)}")
                return
            self._log_event("tools", f"── {node_name} ({len(tools)} tools) ──")
            # Group by category
            cats: dict[str, list] = {}
            for t in tools:
                cats.setdefault(t.category, []).append(t.action)
            for cat, actions in sorted(cats.items()):
                perm = tools[0].permission  # same for category
                self._log_event("tools", f"  {cat}: {', '.join(actions)}  [{perm}]")
        else:
            # Show all tools grouped by node
            summary = self.tool_registry.summary()
            total = len(self.tool_registry.tools)
            self._log_event("tools", f"── TOOL REGISTRY ({total} tools) ──")
            for node_name, count in summary.items():
                self._log_event("tools", f"  {node_name}: {count} tools")
                node_tools = self.tool_registry.find_by_node(node_name)
                cats: dict[str, list] = {}
                for t in node_tools:
                    cats.setdefault(t.category, []).append(t.action)
                for cat, actions in sorted(cats.items()):
                    self._log_event("tools", f"    {cat}: {', '.join(actions)}")

    def _cmd_skills(self, args: list[str]) -> None:
        if not self.skills:
            self._log_event("skill", "No skills installed. Add .yaml files to skills/")
            return
        self._log_event("skill", f"── INSTALLED SKILLS ({len(self.skills)}) ──")
        for skill in self.skills:
            self._log_event("skill", f"  {skill.name} v{skill.version}")
            self._log_event("skill", f"    {skill.description}")
            if skill.requires_tools:
                self._log_event("skill", f"    requires: {', '.join(skill.requires_tools)}")
            self._log_event("skill", f"    workflow: {len(skill.workflow)} steps")
            for i, step in enumerate(skill.workflow, 1):
                target = step.tool or f"route:{step.route}"
                self._log_event("skill", f"      {i}. {step.name} → {target}")

    def _cmd_ps(self, args: list[str]) -> None:
        procs = self.process_manager.all
        if not procs:
            self._log_event("proc", "No processes. Use 'route' to dispatch tasks.")
            return
        self._log_event("proc", f"── PROCESSES ({len(procs)}) ──")
        for p in procs:
            status_color = {
                ProcessStatus.RUNNING: "#ffcc00",
                ProcessStatus.COMPLETED: "#33ff33",
                ProcessStatus.FAILED: "red",
                ProcessStatus.KILLED: "#ff6633",
            }.get(p.status, PHOSPHOR_DIM)
            self._log_event("proc",
                f"  [{p.pid:03d}] {p.status.value:10s} {p.task_type:20s} "
                f"{p.node:15s} {p.elapsed_display}")

    def _cmd_kill(self, args: list[str]) -> None:
        if not args:
            self._log_event("error", "Usage: kill <pid>")
            return
        try:
            pid = int(args[0])
        except ValueError:
            self._log_event("error", f"Invalid PID: {args[0]}")
            return
        if self.process_manager.kill(pid):
            self._log_event("proc", f"Killed process {pid}")
        else:
            self._log_event("error", f"Process {pid} not found or not running")

    def _cmd_topology(self, args: list[str]) -> None:
        for node in self.nodes:
            status = "ONLINE" if node.online else "OFFLINE"
            self._log_event("topology", f"{node.name} [{status}] — {node.role}")
            models = ", ".join(node.models_available) if node.models_available else "none"
            self._log_event("topology", f"  models: {models}")
            self._log_event("topology", f"  compute: {node.hardware.compute_backend}")

    def _cmd_rules(self, args: list[str]) -> None:
        for rule in self.rules:
            via = f" via {rule.via}" if rule.via else ""
            fb = f" fallback: {rule.fallback}" if rule.fallback else ""
            self._log_event("routing",
                f"{rule.task_type} → {rule.prefer_model}@{rule.prefer_node}{via}{fb}")

    def _cmd_route(self, args: list[str]) -> None:
        if not args:
            self._log_event("error", "Usage: route <task_type>")
            self._log_event("routing", "Available types: " +
                ", ".join(r.task_type for r in self.rules))
            return

        task_type = args[0]
        matching = [r for r in self.rules if r.task_type == task_type]

        if not matching:
            self._log_event("error", f"No routing rule for '{task_type}'")
            self._log_event("routing", "Available: " +
                ", ".join(r.task_type for r in self.rules))
            return

        rule = matching[0]
        via = f" via {rule.via}" if rule.via else ""
        self._log_event("route",
            f"▶ {task_type} → {rule.prefer_model}@{rule.prefer_node}{via}")
        self._log_event("route", f"  {rule.description}")
        if rule.fallback:
            self._log_event("route", f"  fallback chain: {' → '.join(rule.fallback)}")

        # Phase 2: actually execute the route
        self._log_event("system", "  [Phase 0: routing display only — execution in Phase 2]")

    def _cmd_ctx(self, args: list[str]) -> None:
        if not self.context_log:
            self._log_event("ctx", "No context entries yet")
            return
        self._log_event("ctx", f"Context thread: {len(self.context_log)} entries this session")

    def _cmd_briefing(self, args: list[str]) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._log_event("ctx", f"── ARBITER OS BRIEFING ({now}) ──")
        self._log_event("ctx", f"  Nodes: {len(self.nodes)} registered")
        for node in self.nodes:
            status = "online" if node.online else "offline"
            self._log_event("ctx", f"  • {node.name}: {status} / {node.role}")
        self._log_event("ctx", f"  Rules: {len(self.rules)} active")
        self._log_event("ctx", f"  Tools: {len(self.tool_registry.tools)} across {len(self.tool_registry.summary())} nodes")
        self._log_event("ctx", f"  Skills: {len(self.skills)} installed")
        running = self.process_manager.running
        self._log_event("ctx", f"  Processes: {len(running)} running")
        self._log_event("ctx", f"  Session events: {len(self.context_log)}")
        self._log_event("ctx", "── END BRIEFING ──")

    def _cmd_health(self, args: list[str]) -> None:
        self._log_event("system", "── CIN HEALTH ──")
        for node in self.nodes:
            self._log_event("system",
                f"  {node.name}: {node.hardware.cpu[:25]} | "
                f"{node.hardware.ram_gb}GB RAM | "
                f"{node.hardware.compute_backend}")
        self._log_event("system", "  [Phase 1: live metrics coming]")
        self._log_event("system", "── END HEALTH ──")

    def _cmd_clear(self, args: list[str]) -> None:
        ctx = self.query_one("#context-panel", ContextPanel)
        ctx.clear()
        self.context_log.clear()
        self._log_event("system", "Context cleared")

    def action_show_topology(self) -> None:
        self._cmd_topology([])

    def action_show_rules(self) -> None:
        self._cmd_rules([])

    def action_clear_log(self) -> None:
        self._cmd_clear([])


# ─── Entry Point ──────────────────────────────────────────────────

def main():
    config_dir = Path(__file__).parent.parent / "config"
    app = ArbiterApp(config_dir=config_dir)
    app.run()


if __name__ == "__main__":
    main()
