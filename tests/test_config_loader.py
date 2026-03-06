"""Tests for Arbiter configuration loading."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from arbiter_core.app import load_nodes, load_routing_rules


def test_load_nodes():
    config_dir = Path(__file__).parent.parent / "config"
    nodes = load_nodes(config_dir)

    assert len(nodes) >= 2, f"Expected at least 2 nodes, got {len(nodes)}"

    names = [n.name for n in nodes]
    assert "thinkcentre" in names, "ThinkCentre node not found"
    assert "gpd-pocket-4" in names, "GPD Pocket 4 node not found"

    tc = next(n for n in nodes if n.name == "thinkcentre")
    assert tc.role == "inference-hub"
    assert tc.hardware.compute_backend == "cpu"
    assert "qwen2.5:7b" in tc.models_available
    assert "phi4:mini" in tc.models_available
    assert "deepseek-r1:14b" in tc.models_available

    gpd = next(n for n in nodes if n.name == "gpd-pocket-4")
    assert gpd.role == "dev-workstation"
    assert gpd.hardware.compute_backend == "vulkan"
    assert gpd.hardware.gpu_arch == "gfx1150"


def test_load_routing_rules():
    config_dir = Path(__file__).parent.parent / "config"
    rules = load_routing_rules(config_dir)

    assert len(rules) >= 6, f"Expected at least 6 rules, got {len(rules)}"

    types = [r.task_type for r in rules]
    expected = ["code_transform", "creative_writing", "deep_reasoning",
                "speed_task", "active_dev", "research"]
    for t in expected:
        assert t in types, f"Missing rule for task type: {t}"

    creative = next(r for r in rules if r.task_type == "creative_writing")
    assert creative.via == "openclaw"
    assert creative.prefer_model == "kimi-2.5"

    deep = next(r for r in rules if r.task_type == "deep_reasoning")
    assert deep.timeout_s == 120


if __name__ == "__main__":
    test_load_nodes()
    print("✓ test_load_nodes passed")
    test_load_routing_rules()
    print("✓ test_load_routing_rules passed")
    print("\nAll tests passed.")
