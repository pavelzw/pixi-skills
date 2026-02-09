import dataclasses
import re
import warnings
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml


class Scope(StrEnum):
    """Scope of a skill - local or global.

    Ordered by definition order (LOCAL < GLOBAL).
    """

    def __lt__(self, other: "Scope") -> bool:  # type: ignore[invalid-method-override, override]
        if not isinstance(other, Scope):
            return NotImplemented
        members = list(Scope)
        return members.index(self) < members.index(other)

    def __le__(self, other: "Scope") -> bool:  # type: ignore[invalid-method-override, override]
        if not isinstance(other, Scope):
            return NotImplemented
        return self == other or self < other

    def __gt__(self, other: "Scope") -> bool:  # type: ignore[invalid-method-override, override]
        if not isinstance(other, Scope):
            return NotImplemented
        return other < self

    def __ge__(self, other: "Scope") -> bool:  # type: ignore[invalid-method-override, override]
        if not isinstance(other, Scope):
            return NotImplemented
        return self == other or self > other

    LOCAL = "local"
    GLOBAL = "global"


@dataclass(frozen=True, order=True)
class Skill:
    """Represents an agent skill discovered from the filesystem.

    Ordered by (scope, name).
    """

    scope: Scope
    name: str
    description: str = dataclasses.field(compare=False)
    path: Path = dataclasses.field(compare=False)

    @classmethod
    def from_directory(cls, path: Path, scope: Scope) -> "Skill":
        """Load a skill from a directory containing SKILL.md."""
        skill_md = path / "SKILL.md"
        if not skill_md.exists():
            raise ValueError(f"No SKILL.md found in {path}")

        name, description = parse_skill_md(skill_md)
        # Use directory name as skill name if not specified in frontmatter
        if name is None:
            name = path.name
        return cls(scope=scope, name=name, description=description, path=path)


def parse_skill_md(skill_md: Path) -> tuple[str | None, str]:
    """Parse SKILL.md to extract name and description from YAML frontmatter.

    Name is optional and can be derived from the directory name.
    """
    content = skill_md.read_text()

    # Check for YAML frontmatter
    if not content.startswith("---"):
        raise ValueError(f"SKILL.md must start with YAML frontmatter: {skill_md}")

    # Find the end of frontmatter
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        raise ValueError(f"Invalid YAML frontmatter in {skill_md}")

    frontmatter = content[3 : 3 + end_match.start()]

    data = yaml.safe_load(frontmatter)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML frontmatter in {skill_md}")

    name = data.get("name")
    if name is not None:
        name = str(name)

    description = data.get("description")
    if description is None:
        raise ValueError(f"Missing 'description' in SKILL.md frontmatter: {skill_md}")

    return name, str(description)


def discover_local_skills(env: str) -> list[Skill]:
    """Discover local skills from the pixi environment.

    Args:
        env: The pixi environment name to search in.
    """
    skills = []
    local_base = Path(f".pixi/envs/{env}/share/agent-skills")
    if local_base.exists():
        for skill_dir in local_base.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                try:
                    skills.append(Skill.from_directory(skill_dir, Scope.LOCAL))
                except ValueError as e:
                    warnings.warn(f"Skipping invalid skill at {skill_dir}: {e}")
    return skills


def discover_global_skills() -> list[Skill]:
    """Discover global skills from ~/.pixi/envs/agent-skill-*/share/agent-skills/*."""
    skills = []
    global_pixi = Path.home() / ".pixi/envs"
    if global_pixi.exists():
        for skill_dir in global_pixi.glob("agent-skill-*/share/agent-skills/*"):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                try:
                    skills.append(Skill.from_directory(skill_dir, Scope.GLOBAL))
                except ValueError as e:
                    warnings.warn(f"Skipping invalid skill at {skill_dir}: {e}")
    return skills
