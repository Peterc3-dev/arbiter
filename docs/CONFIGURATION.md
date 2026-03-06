# Arbiter Configuration Reference

Complete reference for all TOML configuration files used by Arbiter.

---

## Directory Structure

```
config/
├── routing.toml          # Task routing rules
└── nodes/                # One TOML per CIN node
    ├── thinkcentre.toml
    ├── gpd-pocket-4.toml
    └── <your-node>.toml  # Add new nodes here
```

---

## Node Configuration Schema

File location: `config/nodes/<name>.toml`

### `[node]` — Node Identity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique short name. Used in routing rules to reference this node. |
| `hostname` | string | yes | Tailscale hostname (e.g., `thinkcentre.tail`). Used for SSH and API access. |
| `role` | string | yes | Semantic role descriptor. Examples: `inference-hub`, `dev-workstation`, `gpu-node`. |
| `description` | string | no | Human-readable description of this node's purpose. |

### `[hardware]` — Hardware Profile

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cpu` | string | yes | CPU model string (informational + used in health display). |
| `ram_gb` | integer | yes | Total RAM in gigabytes. |
| `gpu` | string | yes | GPU model string, or `"none"` if no discrete/integrated GPU. |
| `gpu_arch` | string | no | GPU microarchitecture code. Critical for compute backend selection. Example: `gfx1150` for RDNA 3.5. |
| `compute_backend` | string | yes | Primary compute acceleration path. One of: `cpu`, `vulkan`, `rocm`, `cuda`. |
| `compute_notes` | string | no | Freeform notes about compute limitations or requirements. |

**Compute backend selection guide:**

| GPU Vendor | Architecture | Recommended Backend | Notes |
|-----------|-------------|-------------------|-------|
| None | — | `cpu` | CPU-only inference via Ollama |
| AMD | gfx1150 (RDNA 3.5) | `vulkan` | ROCm has no native gfx1150 support. Use `OLLAMA_VULKAN=1` |
| AMD | gfx1100 (RDNA 3) | `rocm` | Native ROCm support |
| AMD | gfx900+ (Vega+) | `rocm` | Native ROCm support |
| NVIDIA | Any CUDA-capable | `cuda` | Native CUDA support via Ollama |
| Intel | Arc | `vulkan` | Experimental support |

### `[models]` — Local Model Inventory

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `available` | array of strings | yes | Ollama model tags installed on this node. Empty array `[]` if none. |
| `default` | string | no | Default model tag when no specific preference is given. |
| `ollama_api` | string | no | Ollama API endpoint URL. Default: `http://localhost:11434`. |
| `notes` | string | no | Freeform notes about model setup or limitations. |

### `[cloud_models]` — Cloud Model Relays

Each cloud model is defined as an inline table:

```toml
[cloud_models]
kimi_2_5 = { name = "Kimi 2.5", relay = "openclaw", status = "active" }
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name of the cloud model |
| `relay` | string | Relay mechanism: `openclaw`, `api`, `browser` |
| `status` | string | Current status: `active`, `inactive`, `error` |

### `[tools]` — Non-Model AI Tools

Boolean flags for tools available on this node:

```toml
[tools]
claude_code = true
```

### `[services]` — Network Services

Boolean flags for infrastructure services running on this node:

```toml
[services]
tailscale = true
syncthing = true
ssh = true
openclaw = true
proton_vpn = true
```

---

## Routing Rules Schema

File location: `config/routing.toml`

Each routing rule is a `[[rule]]` TOML array entry:

```toml
[[rule]]
task_type = "code_transform"
description = "Refactoring, formatting, linting, code translation"
prefer_model = "qwen2.5:7b"
prefer_node = "thinkcentre"
via = ""
timeout_s = 60
fallback = ["phi4:mini@thinkcentre"]
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_type` | string | yes | Unique identifier for this task category. Used in `route <task_type>` command. |
| `description` | string | no | Human-readable description of what this task type covers. |
| `prefer_model` | string | yes | Preferred model tag or name for this task type. |
| `prefer_node` | string | yes | Preferred CIN node name (must match a `[node].name` in a node config). Use `"cloud"` for cloud-only models. |
| `via` | string | no | Relay mechanism for cloud models. Values: `openclaw`, `api`. Empty string or omitted for direct Ollama access. |
| `timeout_s` | integer | no | Timeout in seconds for this task type. Default: 60. Increase for heavy models like deepseek-r1. |
| `fallback` | array of strings | no | Ordered fallback chain. Format: `"model@node"`. Arbiter walks this list if primary is unavailable. |

### Current Task Types

| Task Type | Description | Default Path |
|-----------|-------------|-------------|
| `code_transform` | Refactoring, formatting, linting, code translation | qwen2.5:7b @ thinkcentre |
| `creative_writing` | Voice, personality, idiomatic text, marketing copy | kimi-2.5 @ thinkcentre via openclaw |
| `deep_reasoning` | Complex logic, math, multi-step analysis | deepseek-r1:14b @ thinkcentre |
| `speed_task` | Quick lookups, simple generation, low-latency | phi4:mini @ thinkcentre |
| `active_dev` | Coding sessions, project scaffolding, agentic work | claude-code @ gpd-pocket-4 |
| `research` | Web research, current events, documentation | claude-opus @ cloud via api |

### Adding Custom Task Types

Define any task type you want. The `task_type` string is arbitrary — just make sure your
`route` commands use the same string.

```toml
[[rule]]
task_type = "bug_bounty"
description = "Vulnerability analysis, security research, recon"
prefer_model = "deepseek-r1:14b"
prefer_node = "thinkcentre"
timeout_s = 180
fallback = ["qwen2.5:7b@thinkcentre"]
```

---

## Environment Variables

These are **not** stored in TOML files for security reasons.

| Variable | Description | Where Set |
|----------|-------------|-----------|
| `OLLAMA_VULKAN` | Set to `1` to enable Vulkan compute in Ollama | Node's shell profile or systemd unit |
| `MOONSHOT_API_KEY` | API key for Kimi 2.5 via Moonshot | ThinkCentre's OpenClaw config |
| `ANTHROPIC_API_KEY` | API key for Claude API access | Environment or `.env` file |
