"""
Arbiter OS — Skill Plugin Loader

Skills are composed workflows using tools + models. Defined in YAML.
Boo2's format: name, tools, workflow steps with tool/route references.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SkillStep:
    """One step in a skill workflow."""
    name: str
    description: str = ""
    tool: str = ""        # tool:action reference (e.g. "code:execute")
    route: str = ""       # task_type for model routing (e.g. "deep_reasoning")
    command: str = ""     # for code execution steps
    prompt: str = ""      # for model routing steps
    path: str = ""        # for file write steps
    content: str = ""     # for file write steps
    output_var: str = ""  # variable name to store output


@dataclass
class SkillInput:
    """An input parameter for a skill."""
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    example: str = ""


@dataclass
class Skill:
    """A loaded skill plugin."""
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    requires_tools: list[str] = field(default_factory=list)
    requires_network: bool = False
    requires_gpu: bool = False
    workflow: list[SkillStep] = field(default_factory=list)
    inputs: list[SkillInput] = field(default_factory=list)
    source_path: str = ""


def load_skill(path: Path) -> Skill:
    """Load a skill from a YAML file."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    skill = Skill(
        name=data.get("name", path.stem),
        version=data.get("version", "0.1.0"),
        description=data.get("description", ""),
        author=data.get("author", ""),
        requires_tools=data.get("requires_tools", []),
        requires_network=data.get("requires", {}).get("network", False),
        requires_gpu=data.get("requires", {}).get("gpu", False),
        source_path=str(path),
    )

    # Parse workflow steps
    for step_data in data.get("workflow", []):
        step = SkillStep(
            name=step_data.get("step", ""),
            description=step_data.get("description", ""),
            tool=step_data.get("tool", ""),
            route=step_data.get("route", ""),
            command=step_data.get("command", ""),
            prompt=step_data.get("prompt", ""),
            path=step_data.get("path", ""),
            content=step_data.get("content", ""),
            output_var=step_data.get("output_var", ""),
        )
        skill.workflow.append(step)

    # Parse inputs
    for input_name, input_data in data.get("inputs", {}).items():
        inp = SkillInput(
            name=input_name,
            type=input_data.get("type", "string"),
            description=input_data.get("description", ""),
            required=input_data.get("required", True),
            example=input_data.get("example", ""),
        )
        skill.inputs.append(inp)

    return skill


def load_all_skills(skills_dir: Path) -> list[Skill]:
    """Load all skill YAML files from a directory."""
    if not skills_dir.exists():
        return []

    skills = []
    for yaml_file in sorted(skills_dir.glob("*.yaml")):
        try:
            skill = load_skill(yaml_file)
            skills.append(skill)
        except Exception as e:
            print(f"Warning: failed to load skill {yaml_file}: {e}")

    return skills
