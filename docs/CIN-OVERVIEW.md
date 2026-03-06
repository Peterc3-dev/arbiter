# CIN — Centralized Inference Network

## Concept

CIN is a personal multi-machine AI infrastructure. It's the network that Arbiter manages.

The core idea: instead of relying on a single machine or a single cloud API, distribute AI
capabilities across multiple nodes — each optimized for different workloads — and use a smart
routing layer (Arbiter) to direct tasks to the best available resource.

---

## Why CIN?

### The Problem

Modern AI workflows involve multiple models, tools, and interfaces:

- **Local models** (Ollama) for privacy, speed, and zero-cost inference
- **Cloud models** (Claude, Kimi 2.5) for capability beyond what local hardware can run
- **AI tools** (Claude Code) for agentic development work
- **Multiple machines** with different hardware capabilities

Without coordination, you end up manually deciding which model to use, which machine to
run it on, and manually transferring context between them. This is friction that compounds.

### The Solution

CIN + Arbiter creates a unified layer:

1. **All nodes visible**: See every machine, model, and service in one TUI
2. **Automatic routing**: Describe the task, Arbiter picks the best model and node
3. **Context flows**: Briefings and session history follow you across nodes
4. **Fallback resilience**: If a model or node is down, the next best option takes over

---

## Current CIN Topology

### ThinkCentre M70q Gen 5 — "The Hub"

**Role**: Always-on inference hub. Runs 24/7 as the persistent backbone of CIN.

**What it does:**
- Runs Ollama with three local models for different task profiles
- Hosts OpenClaw with Kimi 2.5 relay for cloud model access
- Serves as the Syncthing hub for file synchronization
- Runs Proton VPN for privacy on outbound connections
- Provides SSH access for remote execution from any CIN node

**What it doesn't do:**
- No GPU acceleration (CPU-only inference)
- Not used for active development (that's the GPD's role)

**Key specs**: Intel Core i5-13500T, 16GB RAM, CachyOS, CPU compute backend.

### GPD Pocket 4 — "The Blade"

**Role**: Active development workstation. Where hands-on work happens.

**What it does:**
- Runs Claude Code for agentic software development
- Provides AMD iGPU for future Vulkan-accelerated inference
- Portable — goes wherever Boo goes

**What it doesn't do (yet):**
- Not currently running local models (migrated to ThinkCentre)
- GPU inference requires Vulkan path (ROCm doesn't support gfx1150 natively)

**Key specs**: AMD Ryzen AI 9 HX 370, 32GB RAM, AMD Radeon 890M iGPU, CachyOS,
Vulkan compute backend.

---

## Infrastructure Services

| Service | Purpose | Runs On |
|---------|---------|---------|
| **Tailscale** | Secure WireGuard mesh VPN connecting all CIN nodes | All nodes |
| **Syncthing** | Peer-to-peer file synchronization for config and context | All nodes |
| **SSH** | Remote shell access between nodes | All nodes |
| **Ollama** | Local LLM serving (REST API on port 11434) | ThinkCentre |
| **OpenClaw** | Browser-based relay for cloud models (Kimi 2.5) | ThinkCentre |
| **Proton VPN** | Outbound traffic privacy | ThinkCentre |
| **Claude Code** | Agentic AI development tool | GPD Pocket 4 |

All services run as persistent systemd units for reliability across reboots.

---

## Model Inventory

### Local Models (Ollama)

| Model | Parameters | Role | Speed | Node |
|-------|-----------|------|-------|------|
| **qwen2.5:7b** | 7B | Daily driver — general purpose | Medium | ThinkCentre |
| **phi4:mini** | ~3.8B | Speed tasks — low latency | Fast | ThinkCentre |
| **deepseek-r1:14b** | 14B | Deep reasoning — complex analysis | Slow | ThinkCentre |

### Cloud Models (Relayed)

| Model | Provider | Relay | Role | Node |
|-------|----------|-------|------|------|
| **Kimi 2.5** | Moonshot | OpenClaw | Creative, idiomatic, voice work | ThinkCentre |
| **Claude Opus** | Anthropic | API | Research, complex tasks | Cloud |

### Routing Philosophy

The model routing rules encode a specific philosophy about where different kinds of
intelligence live:

- **Transformation** (code refactoring, formatting) → Local 7B model. These tasks are
  mechanical — a 7B model handles them well at zero cost and with full privacy.
- **Creative/idiomatic** (writing with voice, personality) → Kimi 2.5 (cloud). These
  tasks benefit from the larger model's cultural and linguistic range.
- **Deep reasoning** (math, logic, multi-step) → 14B model with extended timeout. Trading
  speed for depth.
- **Speed** (quick lookups, simple generation) → Smallest local model. Latency matters
  more than capability.
- **Active development** → Claude Code. Purpose-built for agentic coding.
- **Research** → Cloud model with web access. Needs current information.

---

## Expanding CIN

### Adding a New Node

Any machine that can:
1. Run Tailscale (join the mesh)
2. Run Syncthing (receive config sync)
3. Run Python 3.11+ (launch Arbiter TUI)

...can join CIN. Create a TOML node config, drop it in `config/nodes/`, and Syncthing
propagates it to every other node.

### Future Node Concepts

- **GPU inference node**: Dedicated machine with NVIDIA GPU for CUDA-accelerated local
  models. Would enable running 30B+ parameter models locally.
- **Inference appliance**: GPD Pocket 4 repurposed as a Vulkan-accelerated inference
  endpoint, accessible over Tailscale from any other node.
- **Mobile node**: Phone or tablet running a lightweight Arbiter client that can submit
  tasks to CIN remotely.
