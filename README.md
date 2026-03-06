# ARBITER

### Autonomous Routing, Bridging, and Inference Topology for Engineered Reasoning

> *"When the Arbiter was shamed, he didn't disappear — he became the blade that cut through the lie."*
>
> Named for the Sangheili warrior who broke from the Covenant's dogma to forge an alliance with
> humanity's greatest soldier, Arbiter is a distributed AI agent that exists across machines — not
> on them. It is the command fabric of CIN (Centralized Inference Network), aware of every node's
> hardware, every model's strengths, and every task's requirements.

---

## Table of Contents

1. [What Is Arbiter?](#what-is-arbiter)
2. [What Is CIN?](#what-is-cin)
3. [Architecture Overview](#architecture-overview)
4. [The Three Pillars](#the-three-pillars)
   - [Topology Registry](#1-topology-registry)
   - [Context Thread](#2-context-thread)
   - [Router Engine](#3-router-engine)
5. [TUI Interface](#tui-interface)
6. [Project Structure](#project-structure)
7. [Installation & Setup](#installation--setup)
8. [Configuration](#configuration)
   - [Node Configuration](#node-configuration)
   - [Routing Rules](#routing-rules)
9. [Usage](#usage)
10. [Phase Roadmap](#phase-roadmap)
11. [Tech Stack](#tech-stack)
12. [Design Philosophy](#design-philosophy)
13. [Contributing](#contributing)
14. [License](#license)

---

## What Is Arbiter?

Arbiter is a **distributed AI orchestration agent** — a terminal-based command fabric that spans
every machine on your local inference network. It combines two critical roles:

**Orchestrator**: Arbiter knows what hardware and models exist on each node across your network.
When a task arrives, it routes that task to the optimal combination of node + model based on
configurable rules, hardware capabilities, and fallback chains. A code transformation task goes
to the fast local model. A creative writing task routes through the cloud relay. A deep reasoning
problem hits the 14B parameter model with an extended timeout. Arbiter makes these decisions
transparently and logs every routing choice.

**Liaison**: Arbiter maintains a living context thread — a session-scoped memory of what has been
done, what was routed where, what came back, and what the current state of work is. This context
flows between nodes, enabling seamless handoffs between different AI models and tools. When you
switch from your development workstation to your always-on inference hub, the context follows.
Arbiter bridges the gap between isolated model interactions and continuous, coherent workflow.

Arbiter is **not** a chatbot wrapper. It is **not** a model serving framework. It is a
**topology-aware routing and context layer** that sits above your existing infrastructure
(Ollama, OpenClaw, Claude Code, cloud APIs) and makes them work together as a unified system.

---

## What Is CIN?

**CIN (Centralized Inference Network)** is the name for the personal multi-machine AI
infrastructure that Arbiter manages. A CIN consists of:

- **Nodes**: Physical machines connected via Tailscale VPN mesh and Syncthing for file
  synchronization. Each node has different hardware capabilities, installed models, and roles.

- **Models**: Large language models running locally via Ollama (various sizes from 3B to 14B+
  parameters), cloud models accessed through API relays (like Kimi 2.5 through OpenClaw), and
  external AI tools (like Claude Code).

- **Services**: The infrastructure glue — Tailscale for secure networking, Syncthing for
  configuration and context sync, SSH for remote execution, Proton VPN for privacy.

The current CIN consists of two nodes:

| Node | Role | Key Capabilities |
|------|------|-----------------|
| **ThinkCentre M70q Gen 5** | Always-on inference hub | Ollama with qwen2.5:7b, phi4:mini, deepseek-r1:14b; Kimi 2.5 via OpenClaw relay |
| **GPD Pocket 4** | Active development workstation | Claude Code; AMD Radeon 890M iGPU (Vulkan compute path) |

But CIN is designed to grow. Adding a new node to the network is as simple as dropping a TOML
configuration file into the `config/nodes/` directory and ensuring the machine is reachable
over Tailscale.

---

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────┐
│                       ARBITER CORE                            │
│                                                               │
│   ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│   │   Topology   │  │    Context    │  │     Router       │  │
│   │   Registry   │  │    Thread     │  │     Engine       │  │
│   │              │  │               │  │                  │  │
│   │ • node caps  │  │ • session     │  │ • task→node      │  │
│   │ • GPU/CPU    │  │   memory      │  │ • model          │  │
│   │ • models     │  │ • briefings   │  │   selection      │  │
│   │ • drivers    │  │ • handoffs    │  │ • fallback       │  │
│   │ • services   │  │ • task log    │  │   chains         │  │
│   └──────────────┘  └───────────────┘  └──────────────────┘  │
│                                                               │
│   ┌───────────────────────────────────────────────────────┐   │
│   │               TUI Render Engine                       │   │
│   │   phosphor/vector aesthetic • accessible from any     │   │
│   │   CIN node • Textual framework • async-native        │   │
│   └───────────────────────────────────────────────────────┘   │
└──────────────┬──────────────────────┬─────────────────────────┘
               │                      │
       ┌───────▼────────┐    ┌────────▼───────┐
       │  ThinkCentre   │    │  GPD Pocket 4  │   ... future nodes
       │  M70q Gen 5    │    │                │
       │                │    │                │
       │ • CachyOS      │    │ • CachyOS      │
       │ • Ollama       │    │ • Claude Code  │
       │   - qwen2.5:7b │    │ • AMD iGPU     │
       │   - phi4:mini  │    │ • Vulkan       │
       │   - deepseek   │    │   compute      │
       │     r1:14b     │    │                │
       │ • Kimi 2.5     │    │ • Tailscale    │
       │   (OpenClaw)   │    │ • Syncthing    │
       │ • Tailscale    │    │                │
       │ • Syncthing    │    │                │
       │ • Proton VPN   │    │                │
       └────────────────┘    └────────────────┘
```

The key insight is that Arbiter Core doesn't run on a single machine — it runs on **whichever
machine you're sitting at**. The configuration and context are synced across all nodes via
Syncthing, so launching `arbiter` on any CIN node gives you the same view into the entire
network. The TUI connects to remote nodes over Tailscale for health checks and task execution.

---

## The Three Pillars

Arbiter's functionality is organized into three core subsystems. Each pillar is independent
but they compose together to form the complete command fabric.

### 1. Topology Registry

**Purpose**: Know every machine, every model, every capability across CIN.

The Topology Registry is Arbiter's awareness layer. It maintains a complete inventory of what
exists on the network and what each node can do. This information drives all routing decisions.

**What it tracks per node:**

- **Hardware profile**: CPU model, RAM capacity, GPU (vendor, architecture, VRAM), storage
- **Compute backend**: What acceleration path is available — ROCm, Vulkan, CUDA, or CPU-only.
  This is critical because not all GPUs support all frameworks. For example, the GPD Pocket 4's
  AMD Radeon 890M uses the gfx1150 architecture which has no native ROCm support — it must use
  the Vulkan path via `OLLAMA_VULKAN=1`.
- **Installed models**: Which Ollama models are available, their sizes, and the API endpoint.
  Also tracks cloud model relays (like Kimi 2.5 through OpenClaw).
- **Running services**: Tailscale connectivity, Syncthing sync status, SSH reachability,
  OpenClaw availability, VPN status.
- **Health metrics**: CPU load, RAM usage, temperature, available disk space (Phase 1).

**Storage format**: Each node is defined in a human-readable TOML file under
`config/nodes/<name>.toml`. These files are synced across CIN via Syncthing, so every node
has a complete view of the topology.

**Node discovery**: In Phase 0, nodes are statically configured. Phase 1 introduces live
health polling over Tailscale. Future phases may add mDNS-based automatic discovery for
new nodes joining the Tailscale mesh.

### 2. Context Thread

**Purpose**: Maintain continuity across sessions, nodes, models, and tools.

The Context Thread is Arbiter's memory. It solves a fundamental problem with multi-model
workflows: when you route a task to qwen2.5 for code transformation, then send the result
to Kimi 2.5 for polishing, then hand off to Claude Code for integration — each model
operates in isolation. The Context Thread bridges these gaps.

**What it maintains:**

- **Session context**: What is being worked on right now, what tasks have been dispatched,
  what results have returned. This is the real-time operational memory.
- **Briefing protocol**: Compatible with the `/briefing` slash command system used in
  Claude Code. Arbiter can generate briefing snapshots that summarize the current state of
  work, which can be injected into any model's context to bring it up to speed.
- **Task history**: Every routing decision, including which task type was identified, which
  model was selected, which node executed it, how long it took, and what the outcome was.
  This creates an audit trail and feeds future routing optimization.
- **Agent states**: The last known output or state from each AI agent in the workflow
  (Boo2/Kimi, Claude Code, local Ollama models).

**Format**: Structured markdown with YAML frontmatter. Designed to be both human-readable
(you can open the files in any editor) and machine-parseable (Arbiter and other tools can
extract structured data).

### 3. Router Engine

**Purpose**: Given a task, pick the right model on the right node.

The Router Engine is Arbiter's decision layer. It takes a task description, classifies it
into a task type, and then applies configurable routing rules to determine the optimal
execution path.

**Decision factors:**

1. **Task type classification**: What kind of work is this? Code transformation, creative
   writing, deep reasoning, quick lookup, active development, research? Each task type has
   different requirements for model capability, speed, and resource usage.

2. **Node capability matching**: Which nodes have the required hardware and models? A task
   requiring GPU acceleration can't be sent to a CPU-only node. A task requiring internet
   access can't be sent to an offline node.

3. **Model selection**: Within a capable node, which model best fits the task? Smaller models
   (phi4:mini) for speed-critical tasks, larger models (deepseek-r1:14b) for reasoning,
   cloud models (Kimi 2.5) for creative/idiomatic work.

4. **Fallback chains**: If the preferred model or node is unavailable or overloaded, what's
   the next best option? Each routing rule defines an ordered fallback chain.

5. **Context injection**: What information from the Context Thread does the selected model
   need? Arbiter prepares a context payload that gives the model relevant history without
   overwhelming its context window.

**Configuration**: Routing rules are defined in `config/routing.toml` as a list of rules
with task type matching, preferred model/node, optional relay specification (for cloud
models accessed through tools like OpenClaw), timeout limits, and fallback chains.

---

## TUI Interface

Arbiter's interface is a rich terminal UI (TUI) built with Python's Textual framework. The
aesthetic is deliberately **phosphor green on dark** — the visual lineage of CRT terminals,
vector displays, and early hacker culture. It's not retro for nostalgia; it's functional:
high contrast, zero distraction, information-dense.

**Layout:**

```
╔══════════════════════════════════════════════════════════════╗
║  A R B I T E R  v0.1            CIN: 2 nodes ● online      ║
╠══════════════════╦═══════════════════════════════════════════╣
║  TOPOLOGY        ║  CONTEXT THREAD                          ║
║                  ║                                           ║
║  ● thinkcentre   ║  [14:23] [route] ▶ code_transform →      ║
║    inference-hub  ║          qwen2.5:7b@thinkcentre          ║
║    cpu: i5-13500T ║  [14:24] [route] result: 847 tok, 2.3s  ║
║    ram: 16GB      ║  [14:25] [ctx] briefing synced → gpd    ║
║    backend: cpu   ║                                          ║
║    models:        ║  [14:30] [route] ▶ creative_writing →    ║
║      qwen2.5:7b   ║          kimi-2.5@thinkcentre            ║
║      phi4:mini    ║          via openclaw relay               ║
║      deepseek-r1  ║                                          ║
║                   ║  [14:31] [system] briefing generated     ║
║  ● gpd-pocket-4   ║                                          ║
║    dev-workstation ║                                          ║
║    cpu: Ryzen AI 9 ║                                          ║
║    ram: 32GB       ║                                          ║
║    backend: vulkan ║                                          ║
╠══════════════════╩═══════════════════════════════════════════╣
║  arbiter> route code_transform                               ║
╚══════════════════════════════════════════════════════════════╝
```

**Panels:**

- **Left: Topology Panel** — Real-time view of all CIN nodes with hardware specs, available
  models, service status, and health metrics (when live polling is active).
- **Right: Context Thread** — Scrollable event log showing all routing decisions, system
  events, briefing operations, and command history. Color-coded by category.
- **Bottom: Command Input** — Where you issue Arbiter commands.

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| `Ctrl+Q` | Quit Arbiter |
| `Ctrl+T` | Refresh topology display |
| `Ctrl+R` | Show routing rules |
| `Ctrl+L` | Clear context panel |

---

## Project Structure

```
arbiter/
├── README.md                    # This file — comprehensive project documentation
├── pyproject.toml               # Python project metadata and dependencies
├── run.sh                       # Quick-start launcher script
├── LICENSE                      # MIT License
│
├── arbiter_core/                # Core application package
│   ├── __init__.py              # Package init with version
│   └── app.py                   # Main TUI application (Textual)
│                                #   - ArbiterApp: main app class
│                                #   - TopologyPanel: node status widget
│                                #   - ContextPanel: event log widget
│                                #   - Config loaders (TOML parsing)
│                                #   - Command handlers
│
├── config/                      # All configuration (TOML, human-readable)
│   ├── routing.toml             # Task routing rules and fallback chains
│   └── nodes/                   # One file per CIN node
│       ├── thinkcentre.toml     # ThinkCentre M70q Gen 5 profile
│       └── gpd-pocket-4.toml   # GPD Pocket 4 profile
│
├── docs/                        # Extended documentation
│   ├── ARCHITECTURE.md          # Full architecture specification
│   ├── CONFIGURATION.md         # Detailed config reference
│   ├── PHASES.md                # Development roadmap details
│   └── CIN-OVERVIEW.md          # CIN network concepts
│
└── tests/                       # Test suite (Phase 1+)
    └── test_config_loader.py    # Config parsing tests
```

---

## Installation & Setup

### Prerequisites

- **Python 3.11+** (required for `tomllib` in the standard library)
- **pip** (Python package manager)
- A terminal emulator with Unicode support (virtually all modern terminals)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/Peterc3-dev/arbiter.git
cd arbiter

# Option 1: Use the launcher script
chmod +x run.sh
./run.sh

# Option 2: Manual installation
pip install textual rich --break-system-packages
python3 -m arbiter_core.app
```

### Installation on CIN Nodes

For a proper CIN deployment, you want Arbiter available on every node:

1. **Set up Syncthing sync**: Add the `arbiter/` directory as a shared folder in Syncthing
   across all CIN nodes. This keeps configuration and context in sync automatically.

2. **Or clone on each node**: If you prefer git-based deployment:
   ```bash
   # On each CIN node:
   git clone https://github.com/Peterc3-dev/arbiter.git ~/arbiter
   cd ~/arbiter && pip install textual rich --break-system-packages
   ```

3. **Verify**: Run `./run.sh` on any node. You should see the Arbiter TUI with your full
   CIN topology loaded from configuration.

### Shell Alias (Recommended)

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias arbiter='cd ~/arbiter && python3 -m arbiter_core.app'
```

Now you can launch Arbiter from anywhere with just `arbiter`.

---

## Configuration

All configuration is stored in human-readable TOML files under the `config/` directory.
TOML was chosen deliberately: it's readable without documentation, git-friendly for
version tracking, and maps cleanly to Python data structures.

### Node Configuration

Each machine on CIN gets its own file at `config/nodes/<name>.toml`. Here's a fully
annotated example:

```toml
# ─── Node Identity ────────────────────────────────────────
[node]
name = "thinkcentre"              # Short name used in routing rules
hostname = "thinkcentre.tail"     # Tailscale hostname for network access
role = "inference-hub"            # Semantic role: inference-hub, dev-workstation, etc.
description = "Always-on agent hub — persistent background automation"

# ─── Hardware Profile ─────────────────────────────────────
[hardware]
cpu = "Intel Core i5-13500T"      # CPU model (informational + routing decisions)
ram_gb = 16                       # Total RAM in gigabytes
gpu = "none"                      # GPU model or "none"
gpu_arch = ""                     # GPU architecture (e.g., "gfx1150" for RDNA 3.5)
compute_backend = "cpu"           # Primary compute path: cpu, vulkan, rocm, cuda
                                  # IMPORTANT: ROCm does NOT natively support gfx1150
                                  # For AMD iGPUs on RDNA 3.5, use "vulkan" with
                                  # OLLAMA_VULKAN=1 environment variable

# ─── Local Models ─────────────────────────────────────────
[models]
available = [                     # Ollama model tags installed on this node
    "qwen2.5:7b",                 # Daily driver — good all-around 7B model
    "phi4:mini",                  # Speed model — fast responses, smaller context
    "deepseek-r1:14b",           # Reasoning model — slower but deeper analysis
]
default = "qwen2.5:7b"           # Model to use when no specific preference
ollama_api = "http://localhost:11434"  # Ollama API endpoint

# ─── Cloud Model Relays ──────────────────────────────────
[cloud_models]
# Cloud models accessed through relay tools (not running locally)
kimi_2_5 = {
    name = "Kimi 2.5",           # Display name
    relay = "openclaw",          # How it's accessed (OpenClaw Chrome relay)
    status = "active"            # Current status
}

# ─── Network Services ────────────────────────────────────
[services]
tailscale = true                  # Tailscale VPN mesh active
syncthing = true                  # Syncthing file sync active
ssh = true                        # SSH server running
openclaw = true                   # OpenClaw interface running
proton_vpn = true                 # Proton VPN active
```

**Adding a new node**: Create a new TOML file following this structure. The filename doesn't
matter — Arbiter reads all `.toml` files in the `config/nodes/` directory. The `name` field
inside the file is what's used for routing.

### Routing Rules

Routing rules are defined in `config/routing.toml`. Each rule maps a task type to a preferred
model, node, and fallback chain.

```toml
# Each [[rule]] block defines one routing path.
# Arbiter matches the task_type field against the task you're routing.

[[rule]]
task_type = "code_transform"
description = "Refactoring, formatting, linting, code translation"
prefer_model = "qwen2.5:7b"      # Best model for this task type
prefer_node = "thinkcentre"       # Which CIN node to run on
fallback = ["phi4:mini@thinkcentre"]  # If primary unavailable, try these in order

[[rule]]
task_type = "creative_writing"
description = "Voice, personality, idiomatic text, marketing copy"
prefer_model = "kimi-2.5"
prefer_node = "thinkcentre"
via = "openclaw"                  # Route through OpenClaw relay (cloud model)
fallback = ["qwen2.5:7b@thinkcentre"]

[[rule]]
task_type = "deep_reasoning"
description = "Complex logic, math, multi-step analysis"
prefer_model = "deepseek-r1:14b"
prefer_node = "thinkcentre"
timeout_s = 120                   # Extended timeout for heavy models
fallback = ["qwen2.5:7b@thinkcentre"]

[[rule]]
task_type = "speed_task"
description = "Quick lookups, simple generation, low-latency needs"
prefer_model = "phi4:mini"
prefer_node = "thinkcentre"
fallback = ["qwen2.5:7b@thinkcentre"]

[[rule]]
task_type = "active_dev"
description = "Coding sessions, project scaffolding, agentic work"
prefer_model = "claude-code"
prefer_node = "gpd-pocket-4"
fallback = []                     # No fallback — Claude Code is unique

[[rule]]
task_type = "research"
description = "Web-connected research, current events, documentation lookup"
prefer_model = "claude-opus"
prefer_node = "cloud"
via = "api"
fallback = ["kimi-2.5@thinkcentre"]
```

**The `via` field**: Some models aren't accessed directly through Ollama. Kimi 2.5, for
instance, runs as a cloud model relayed through OpenClaw's Chrome browser interface on the
ThinkCentre. The `via` field tells Arbiter which relay mechanism to use.

**Fallback chains**: Defined as a list of `model@node` strings. Arbiter walks the chain
in order if the primary selection fails (node offline, model not loaded, timeout exceeded).

---

## Usage

### Available Commands

Launch Arbiter and use these commands in the command input:

| Command | Description | Example |
|---------|-------------|---------|
| `help` | Show all available commands | `help` |
| `topology` | Display all CIN nodes with full details | `topology` |
| `rules` | Show all routing rules with models and fallbacks | `rules` |
| `route <type>` | Route a task type and show the execution path | `route code_transform` |
| `ctx` | Show context thread summary | `ctx` |
| `briefing` | Generate a briefing snapshot of current CIN state | `briefing` |
| `health` | System-wide health overview of all nodes | `health` |
| `clear` | Clear the context panel | `clear` |

### Example Session

```
arbiter> topology
  [topology] thinkcentre [ONLINE] — inference-hub
  [topology]   models: qwen2.5:7b, phi4:mini, deepseek-r1:14b
  [topology]   compute: cpu
  [topology] gpd-pocket-4 [ONLINE] — dev-workstation
  [topology]   models: none
  [topology]   compute: vulkan

arbiter> route creative_writing
  [route] ▶ creative_writing → kimi-2.5@thinkcentre via openclaw
  [route]   Voice, personality, idiomatic text, marketing copy
  [route]   fallback chain: qwen2.5:7b@thinkcentre

arbiter> briefing
  [ctx] ── BRIEFING SNAPSHOT (2026-03-05 22:15) ──
  [ctx]   Nodes: 2 registered
  [ctx]   • thinkcentre: online / inference-hub
  [ctx]   • gpd-pocket-4: online / dev-workstation
  [ctx]   Rules: 6 active
  [ctx]   Session events: 12
  [ctx] ── END BRIEFING ──
```

---

## Phase Roadmap

Arbiter is developed in phases. Each phase builds on the previous one, and the system is
functional at every phase boundary.

### Phase 0 — Scaffold ✅ (Current)

**Status**: Complete. This is what you're looking at.

- [x] Python project structure with `pyproject.toml`
- [x] Textual TUI skeleton with phosphor green aesthetic
- [x] TOML-based node configuration schema
- [x] TOML-based routing rules schema
- [x] Static topology display (read configs, render node status)
- [x] Command system (help, topology, rules, route, briefing, health, ctx, clear)
- [x] Context thread event logging with color-coded categories
- [x] Routing rule display and task type lookup

**What works**: You can see your entire CIN topology, browse routing rules, simulate
routing decisions (displays the path but doesn't execute), and generate briefing snapshots.

### Phase 1 — Topology Awareness

**Goal**: Arbiter sees the real-time state of every CIN node.

- [ ] Live node health polling over Tailscale/SSH
  - CPU load, RAM usage, disk space, temperature
  - Refresh on configurable interval
- [ ] Ollama model inventory per node (query `/api/tags` endpoint)
  - Detect which models are actually loaded vs. available
  - Track model sizes and quantization levels
- [ ] Service status checks
  - Tailscale peer status via `tailscale status`
  - Syncthing folder sync status
  - OpenClaw process detection
- [ ] Dynamic topology updates in TUI (real-time refresh)

### Phase 2 — Router Engine

**Goal**: Arbiter can actually execute routed tasks.

- [ ] Routing rules parser with validation
- [ ] Task classification
  - Manual classification first (user specifies task type)
  - Later: LLM-assisted classification (use phi4:mini to classify incoming tasks)
- [ ] Route execution
  - Direct Ollama API calls for local models
  - OpenClaw relay for Kimi 2.5
  - Claude Code handoff protocol
- [ ] Fallback chain logic
  - Automatic failover on timeout, node unreachable, model error
  - Logging of fallback events
- [ ] Response rendering in TUI

### Phase 3 — Context Thread

**Goal**: Continuous context across sessions, nodes, and models.

- [ ] Session context file format (markdown + YAML frontmatter)
- [ ] Briefing generation (structured snapshot compatible with `/briefing` protocol)
- [ ] Cross-node context sync via Syncthing
  - Automatic push of context files to shared Syncthing folder
  - Conflict resolution for concurrent edits
- [ ] Context injection into routed tasks
  - Select relevant context for each model call
  - Respect context window limits per model
- [ ] History/log viewer in TUI with search and filtering

### Phase 4 — Agent Liaison

**Goal**: Multi-agent coordination and task decomposition.

- [ ] Boo2 (Kimi 2.5) integration via OpenClaw relay protocol
- [ ] Claude Code handoff protocol
  - Generate briefings that Claude Code can consume
  - Parse Claude Code outputs back into context thread
- [ ] Multi-agent task decomposition
  - Break complex tasks into subtasks
  - Route subtasks to different models in parallel
  - Aggregate results
- [ ] Routing feedback loop
  - Log actual vs. expected performance per model/task combination
  - Use feedback to optimize routing rules over time

### Future Phases (Conceptual)

- **Phase 5 — Inference Appliance**: GPD Pocket 4 as a GPU-accelerated inference node
  over Tailscale, using Vulkan compute path. Extends CIN's local model capacity.
- **Phase 6 — Auto-Discovery**: mDNS-based automatic node discovery on Tailscale mesh.
  New machines join CIN by running an Arbiter agent.
- **Phase 7 — Web Dashboard**: Optional web UI alongside TUI for remote monitoring.
  Not a replacement for the TUI — a companion.

---

## Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **TUI Framework** | Python [Textual](https://textual.textualize.io/) | Async-native, rich widget system, CSS-like styling, runs on any Python 3.11+ system. No compiled dependencies — deploys anywhere on CIN. |
| **Rich Text** | [Rich](https://rich.readthedocs.io/) | Textual's rendering engine. Handles color, style, panels, tables in the terminal. |
| **Configuration** | [TOML](https://toml.io/) | Human-readable, git-friendly, built into Python 3.11+ stdlib (`tomllib`). No external parser needed. |
| **File Sync** | [Syncthing](https://syncthing.net/) | Already deployed on CIN. Handles config/context sync between nodes without additional infrastructure. |
| **Networking** | [Tailscale](https://tailscale.com/) | Already deployed on CIN. Provides secure mesh VPN between all nodes. Arbiter uses Tailscale hostnames for node addressing. |
| **Remote Execution** | SSH | Already deployed on CIN. Used for live health polling and remote command execution in Phase 1+. |
| **Local LLM API** | [Ollama](https://ollama.ai/) | REST API at port 11434. Arbiter calls `/api/generate`, `/api/tags`, `/api/ps` for model interaction and inventory. |
| **Cloud LLM Relay** | [OpenClaw](https://github.com/nicepkg/openclaw) + Kimi 2.5 | OpenClaw provides browser-based relay for cloud models. Kimi 2.5 accessed via Moonshot API through OpenClaw on ThinkCentre. |
| **Version Control** | Git + GitHub | Source of truth for Arbiter code. Nodes can pull updates via git. |

### Why Python?

Arbiter is a coordination layer, not a performance-critical system. Python provides:

- **Textual**: The best terminal UI framework available, period. Nothing else comes close
  for building rich, async, styled terminal applications.
- **tomllib**: TOML parsing in the standard library (3.11+). Zero external config dependencies.
- **asyncio**: Native async for concurrent health polling, API calls, and TUI rendering.
- **Universal deployment**: Python runs on every machine in CIN without compilation.
- **Ollama integration**: Simple HTTP calls via `httpx` or `urllib`. No SDK needed.

---

## Design Philosophy

### 1. Configuration Over Code

Arbiter's behavior is defined by TOML files, not hardcoded logic. Adding a new node, a new
routing rule, or a new model preference never requires changing source code. This makes
Arbiter adaptable as CIN evolves.

### 2. Topology Awareness

Most AI tools are node-blind — they don't know or care about the hardware they're running
on. Arbiter inverts this. It knows that ROCm doesn't support gfx1150, that the ThinkCentre
has no GPU, that phi4:mini is faster but less capable than qwen2.5:7b. This knowledge
drives every routing decision.

### 3. Context Continuity

The biggest pain point in multi-model workflows is context loss. You explain your project
to one model, switch to another, and start from zero. Arbiter's Context Thread solves this
by maintaining a living record that any model can be briefed from.

### 4. Phosphor Aesthetic

The visual design isn't decoration. Phosphor green on black is the highest-contrast,
lowest-fatigue color scheme for extended terminal use. The CRT/vector aesthetic connects
to a lineage of tools built for operators, not consumers. Arbiter is a tool for someone
who lives in the terminal.

### 5. Progressive Capability

Arbiter is useful at Phase 0 (topology viewer + routing simulator) and becomes more
powerful with each phase. It never requires all phases to be complete to provide value.

---

## Contributing

Arbiter is a personal infrastructure project, but the architecture and approach may be
useful to others building multi-machine AI workflows. Issues and discussions are welcome.

If you're building your own CIN-like setup, the key things to adapt:

1. **Node TOML files**: Replace with your actual hardware profiles
2. **Routing rules**: Define task types and model preferences for your workflow
3. **Service list**: Adjust the services section to match your infrastructure

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*"Were it so easy."* — The Arbiter
