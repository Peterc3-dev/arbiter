# Arbiter OS — Architecture Specification

## A Distributed Inference Operating System

## Overview

Arbiter OS is a distributed inference operating system that manages AI compute
across a mesh of heterogeneous devices. The core resource being managed is
**inference** — the act of a trained model generating output from input. Just as
a traditional OS abstracts CPU cycles and memory allocation, Arbiter OS abstracts
which node, which model, and which compute backend runs each inference task.

---

## System Model

Arbiter follows a **hub-spoke model with floating hub**. The "hub" is whichever CIN node
you're currently using — Arbiter's TUI runs locally, reads synced configuration, and
reaches out to remote nodes for execution. There is no single server.

```
                    ┌─────────────┐
                    │  You (TUI)  │
                    │  on any     │
                    │  CIN node   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼─────┐ ┌───▼─────┐
        │  Node A   │ │ Node B  │ │ Node C  │
        │  Ollama   │ │ Claude  │ │ Future  │
        │  OpenClaw │ │ Code    │ │ ...     │
        └───────────┘ └─────────┘ └─────────┘
```

**Why floating hub?** In a personal infrastructure, you move between machines. Sometimes
you're at the GPD Pocket, sometimes you SSH into the ThinkCentre. Arbiter doesn't care
which node you're on — it presents the same view of the entire CIN from anywhere.

---

## Data Flow

### Task Routing Flow

```
User Input
    │
    ▼
Task Classification ──► task_type identified
    │
    ▼
Rule Matching ──► find rule where rule.task_type == task_type
    │
    ▼
Node Resolution ──► is prefer_node online? Has capacity?
    │                     │
    │ YES                 │ NO
    ▼                     ▼
Model Check ──►     Walk Fallback Chain
  Is prefer_model         │
  loaded/available?       │
    │                     │
    │ YES                 │
    ▼                     ▼
Context Injection ──► Select relevant context from Thread
    │
    ▼
Execute ──► Ollama API / OpenClaw relay / Claude Code handoff
    │
    ▼
Response ──► Display in TUI + log to Context Thread
```

### Configuration Sync Flow

```
Edit TOML on any node
    │
    ▼
Syncthing detects change
    │
    ▼
Propagate to all CIN nodes (~seconds)
    │
    ▼
Arbiter reloads config on next command (or periodic refresh)
```

---

## Component Details

### Topology Registry

**Responsibilities:**
- Parse and validate node TOML files
- Provide node lookup by name, role, or capability
- Track online/offline status (Phase 1)
- Report health metrics (Phase 1)

**Key interfaces:**

```python
def load_nodes(config_dir: Path) -> list[NodeInfo]
def get_node(name: str) -> NodeInfo | None
def nodes_with_model(model: str) -> list[NodeInfo]
def nodes_with_backend(backend: str) -> list[NodeInfo]
def online_nodes() -> list[NodeInfo]  # Phase 1
```

**Health polling strategy (Phase 1):**
- SSH into each Tailscale peer
- Run lightweight health check script
- Collect: `uptime`, `free -m`, `sensors` (if available), `ollama ps`
- Cache results with configurable TTL (default: 30s)
- Display stale indicators if poll fails

### Router Engine

**Responsibilities:**
- Parse routing rules from TOML
- Match task types to rules
- Resolve node + model for a given task
- Execute fallback chains on failure
- Log routing decisions to Context Thread

**Rule matching algorithm:**
1. Exact match on `task_type`
2. If no match, return error with available task types
3. If match found, check `prefer_node` availability
4. Check `prefer_model` availability on that node
5. If either unavailable, walk `fallback` list in order
6. If all fallbacks exhausted, return routing failure

**Execution paths (Phase 2):**

| Model Type | Execution Method |
|-----------|-----------------|
| Ollama local | HTTP POST to `{node.ollama_api}/api/generate` |
| Kimi 2.5 | OpenClaw relay (browser automation on ThinkCentre) |
| Claude Code | Briefing handoff (generate context file, signal Claude Code) |
| Cloud API | Direct HTTP to provider API (with API key from env) |

### Context Thread

**Responsibilities:**
- Log all routing events, system events, user commands
- Generate briefing snapshots
- Sync context across nodes
- Provide context injection for routed tasks

**File format:**

```markdown
---
type: briefing
timestamp: 2026-03-05T22:15:00
session_id: abc123
nodes_online: [thinkcentre, gpd-pocket-4]
active_task: code_transform
---

## Current State

Working on Arbiter Phase 0 scaffold. ThinkCentre running all local models.
GPD Pocket 4 active for development.

## Recent Events

- [22:10] Routed code_transform → qwen2.5:7b@thinkcentre (847 tokens, 2.3s)
- [22:12] Routed creative_writing → kimi-2.5@thinkcentre via openclaw
- [22:15] Briefing generated

## Active Context

- Project: Arbiter TUI development
- Branch: main
- Last model output: [summary of last response]
```

---

## Network Architecture

```
┌─────────────────────────────────────────┐
│              Tailscale Mesh             │
│                                         │
│  thinkcentre.tail ◄──► gpd.tail        │
│       100.x.y.z         100.a.b.c      │
│                                         │
│  ┌─────────────┐   ┌─────────────┐     │
│  │ Syncthing   │◄─►│ Syncthing   │     │
│  │ Port 22000  │   │ Port 22000  │     │
│  └─────────────┘   └─────────────┘     │
│                                         │
│  ┌─────────────┐                        │
│  │ Ollama API  │                        │
│  │ Port 11434  │                        │
│  └─────────────┘                        │
│                                         │
│  ┌─────────────┐                        │
│  │ Proton VPN  │                        │
│  │ (outbound)  │                        │
│  └─────────────┘                        │
└─────────────────────────────────────────┘
```

All inter-node communication goes through Tailscale. This means:
- Encrypted by default (WireGuard)
- Works across NAT (no port forwarding needed)
- Stable hostnames (thinkcentre.tail, gpd.tail)
- Works from anywhere (home, work, mobile hotspot)

---

## Security Model

- **No API keys in config files**: Sensitive credentials go in environment variables
  or systemd service files, not in TOML configs that sync via Syncthing.
- **Tailscale ACLs**: Network access between nodes is controlled by Tailscale's
  access control policies.
- **Proton VPN**: Outbound internet traffic from ThinkCentre routes through Proton VPN.
- **Local-first**: Arbiter prefers local model execution over cloud APIs. Cloud is
  the fallback, not the default.

---

## Extensibility

### Adding a New Node

1. Create `config/nodes/<name>.toml` following the schema
2. Ensure the node is on the Tailscale mesh
3. Syncthing propagates the config
4. Arbiter picks it up on next launch or config reload

### Adding a New Task Type

1. Add a `[[rule]]` block to `config/routing.toml`
2. Define task_type, prefer_model, prefer_node, fallback
3. Arbiter picks it up immediately

### Adding a New Model

1. Install the model on the target node: `ollama pull <model>`
2. Add the model tag to the node's `[models].available` list in TOML
3. Optionally create routing rules that reference it

### Adding a New Relay

1. Define the relay in the node's `[cloud_models]` section
2. Reference it in routing rules with the `via` field
3. Implement the relay handler in Phase 2 Router Engine
