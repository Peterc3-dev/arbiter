# Arbiter Development Phases

Detailed breakdown of each development phase with implementation notes,
acceptance criteria, and technical considerations.

---

## Phase 0 — Scaffold ✅

**Status**: Complete

**Delivered:**
- Python project with `pyproject.toml` and `textual` dependency
- TUI skeleton: title bar, topology panel, context thread, command input
- Phosphor green aesthetic (CSS theming in Textual)
- TOML config loading for nodes and routing rules
- Command system: help, topology, rules, route, briefing, health, ctx, clear
- Event logging with color-coded categories
- `run.sh` launcher script

**Key decisions made:**
- Textual over curses/blessed: better widget system, CSS styling, async-native
- TOML over YAML/JSON: human-readable, git-friendly, stdlib support in 3.11+
- Single-file TUI (`app.py`): keeps Phase 0 simple, will decompose in Phase 1

---

## Phase 1 — Topology Awareness

**Goal**: Replace static config display with live system data.

### 1.1 Health Polling

**Implementation**: Async SSH commands over Tailscale.

```python
# Pseudocode for health check
async def poll_node(node: NodeInfo) -> HealthSnapshot:
    ssh = f"ssh {node.hostname}"
    cpu = await ssh_exec(ssh, "grep 'cpu ' /proc/stat")
    mem = await ssh_exec(ssh, "free -m | grep Mem")
    temp = await ssh_exec(ssh, "cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null")
    return HealthSnapshot(cpu_percent, ram_used, ram_total, temp_c)
```

**Refresh strategy:**
- Poll every 30 seconds by default (configurable in TOML)
- Show "stale" indicator if last poll > 2 minutes ago
- Show "unreachable" if SSH fails
- Non-blocking: TUI remains responsive during polls

### 1.2 Model Inventory

**Implementation**: Query Ollama REST API on each node.

```
GET http://{node.ollama_api}/api/tags  → list of installed models
GET http://{node.ollama_api}/api/ps    → currently loaded models
```

This gives us:
- Which models are installed vs. what the TOML says should be there
- Which models are currently loaded in memory (warm) vs. cold
- Model sizes and quantization info

### 1.3 Service Status

**Implementation**: Mix of SSH probes and API checks.

| Service | Check Method |
|---------|-------------|
| Tailscale | `tailscale status --json` (look for peer online status) |
| Syncthing | `curl http://localhost:8384/rest/system/status` |
| Ollama | `curl http://localhost:11434/api/tags` |
| OpenClaw | Process check: `pgrep -f openclaw` |
| Proton VPN | `protonvpn-cli status` or IP check |

### 1.4 TUI Updates

- Topology panel refreshes reactively when health data arrives
- Add color-coded health indicators: green (healthy), yellow (warning), red (critical)
- Add load bars for CPU and RAM
- Add model load status (warm/cold) indicators

**Acceptance criteria:**
- [ ] Health metrics update in TUI without manual refresh
- [ ] Unreachable nodes clearly indicated
- [ ] Model inventory matches reality (not just config)
- [ ] All service statuses checked and displayed

---

## Phase 2 — Router Engine

**Goal**: Execute tasks through the routing system.

### 2.1 Task Execution

**Ollama direct execution:**

```python
async def execute_ollama(node: NodeInfo, model: str, prompt: str) -> str:
    url = f"{node.models.ollama_api}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    response = await httpx.post(url, json=payload)
    return response.json()["response"]
```

**OpenClaw relay execution (Kimi 2.5):**
- Phase 2 will define the protocol for sending prompts through OpenClaw
- OpenClaw runs on ThinkCentre with Chrome browser relay
- Arbiter sends task via local socket or file-based protocol
- OpenClaw forwards to Kimi 2.5 via Moonshot API
- Response flows back through the same channel

**Claude Code handoff:**
- Generate a briefing file with task context
- Place in a known directory that Claude Code can access
- Signal Claude Code (mechanism TBD — could be file watch, could be CLI)

### 2.2 Fallback Logic

```python
async def route_task(task_type: str, prompt: str) -> RouteResult:
    rule = find_rule(task_type)

    # Try primary
    node = get_node(rule.prefer_node)
    if node and node.online:
        try:
            result = await execute(node, rule.prefer_model, prompt, rule.timeout_s)
            return RouteResult(success=True, result=result, path="primary")
        except (TimeoutError, ConnectionError):
            pass

    # Walk fallback chain
    for fallback in rule.fallback:
        model, node_name = fallback.split("@")
        node = get_node(node_name)
        if node and node.online:
            try:
                result = await execute(node, model, prompt, rule.timeout_s)
                return RouteResult(success=True, result=result, path=f"fallback:{fallback}")
            except (TimeoutError, ConnectionError):
                continue

    return RouteResult(success=False, error="All routes exhausted")
```

### 2.3 Response Rendering

- Stream responses token-by-token in the TUI context panel
- Show routing metadata: model used, node, latency, token count
- Log complete interaction to Context Thread

**Acceptance criteria:**
- [ ] `route code_transform "refactor this function"` actually calls Ollama
- [ ] Fallback triggers automatically when primary node is down
- [ ] Timeout kills hung requests and tries fallback
- [ ] Response streams into TUI in real-time
- [ ] All routing decisions logged with timing data

---

## Phase 3 — Context Thread

**Goal**: Persistent, synced context that flows between sessions and nodes.

### 3.1 Context File Format

Markdown with YAML frontmatter. Human-readable AND machine-parseable.

```markdown
---
type: session
id: sess_20260305_221500
created: 2026-03-05T22:15:00
node: thinkcentre
models_used: [qwen2.5:7b, kimi-2.5]
task_types: [code_transform, creative_writing]
---

## Session Summary

Active development on Arbiter Phase 2 router engine.

## Events

| Time | Type | Model | Tokens | Latency |
|------|------|-------|--------|---------|
| 22:15 | code_transform | qwen2.5:7b | 847 | 2.3s |
| 22:18 | creative_writing | kimi-2.5 | 1203 | 4.1s |

## Context Payload

[Structured context that can be injected into model prompts]
```

### 3.2 Briefing Generation

Compatible with the `/briefing` slash command protocol in Claude Code:

```markdown
---
type: briefing
generated: 2026-03-05T22:30:00
generator: arbiter-v0.1
---

# Briefing

## Active Work
- Project: Arbiter Phase 2
- Last action: Router engine fallback logic implementation
- Status: In progress

## CIN State
- thinkcentre: online, 3 models loaded
- gpd-pocket-4: online, Claude Code active

## Recent Routing
- 5 tasks routed in this session
- Primary path success rate: 80%
- 1 fallback triggered (thinkcentre timeout)

## Key Context
[Relevant excerpts from recent model interactions]
```

### 3.3 Sync Strategy

- Context files stored in `~/.config/arbiter/context/`
- This directory is a Syncthing shared folder across all CIN nodes
- Conflict resolution: last-write-wins with backup of conflicts
- Pruning: sessions older than 30 days archived, older than 90 days deleted

**Acceptance criteria:**
- [ ] Context files generated automatically during routing
- [ ] `briefing` command produces `/briefing`-compatible output
- [ ] Context syncs to all nodes within 60 seconds
- [ ] Old context is pruned automatically
- [ ] Context can be injected into routed prompts

---

## Phase 4 — Agent Liaison

**Goal**: Multi-agent coordination.

### 4.1 Boo2 (Kimi 2.5) Integration

- Formalize the OpenClaw relay protocol
- Define input/output format for Kimi tasks
- Handle Kimi-specific quirks (reasoning mode toggle, role specification)

### 4.2 Claude Code Handoff

- Bidirectional: Arbiter → Claude Code (task dispatch) and Claude Code → Arbiter (results)
- Use the `/briefing` protocol as the handoff format
- Claude Code watches a directory for new briefings

### 4.3 Task Decomposition

- Given a complex task, break it into subtasks
- Route each subtask independently (possibly in parallel)
- Aggregate results into a coherent response
- Example: "Research X, then write a summary in my voice"
  → research subtask → claude-opus
  → writing subtask → kimi-2.5 (with research results as context)

### 4.4 Feedback Loop

- Log: task_type, model, node, prompt_tokens, completion_tokens, latency, quality_score
- Quality score: manual rating (1-5) initially, automated metrics later
- Use feedback data to refine routing rules over time
- Surface patterns: "deepseek-r1 is faster than expected on code_transform"

**Acceptance criteria:**
- [ ] Boo2 receives and responds to tasks through Arbiter
- [ ] Claude Code consumes Arbiter briefings automatically
- [ ] Complex tasks decompose into subtask chains
- [ ] Feedback log captures routing performance data
- [ ] Routing rules can be tuned based on feedback data
