import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

from pixi_skills.skill import Scope, Skill


class BackendName(str, Enum):
    """Available backend names."""

    CLAUDE = "claude"
    CODEX = "codex"
    COPILOT = "copilot"
    CRUSH = "crush"
    CURSOR = "cursor"
    GEMINI = "gemini"
    OPENCODE = "opencode"


class Backend(ABC):
    """Abstract base class for LLM agent backends."""

    name: str

    @abstractmethod
    def get_skills_dir(self, scope: Scope) -> Path:
        """Get the directory where skills should be installed for this backend."""
        ...

    def get_installed_skills(self, scope: Scope) -> list[tuple[str, Path]]:
        """Get list of installed skill names and their symlink targets."""
        skills_dir = self.get_skills_dir(scope)
        if not skills_dir.exists():
            return []

        result = []
        for item in skills_dir.iterdir():
            if item.is_symlink():
                result.append((item.name, item.resolve()))
        return result

    def install(self, skill: Skill) -> Path:
        """Install a skill by creating a relative symlink.

        Returns the path to the created symlink. Raises ValueError if scope mismatch.
        """
        skills_dir = self.get_skills_dir(skill.scope)
        skills_dir.mkdir(parents=True, exist_ok=True)

        symlink_path = skills_dir / skill.name
        if symlink_path.exists():
            if symlink_path.is_symlink():
                if symlink_path.resolve() == skill.path.resolve():
                    return symlink_path  # Already installed
                symlink_path.unlink()  # Replace existing symlink
            else:
                raise ValueError(
                    f"Cannot install: {symlink_path} exists and is not a symlink"
                )

        # Create relative symlink for portability
        relative_target = os.path.relpath(skill.path, symlink_path.parent)
        symlink_path.symlink_to(relative_target)
        return symlink_path

    def uninstall(self, skill_name: str, scope: Scope) -> bool:
        """Uninstall a skill by removing its symlink.

        Returns True if uninstalled, False if not found.
        """
        skills_dir = self.get_skills_dir(scope)
        symlink_path = skills_dir / skill_name

        if symlink_path.is_symlink():
            symlink_path.unlink()
            return True
        return False

    def is_installed(self, skill: Skill) -> bool:
        """Check if a skill is installed."""
        skills_dir = self.get_skills_dir(skill.scope)
        symlink_path = skills_dir / skill.name
        return (
            symlink_path.is_symlink() and symlink_path.resolve() == skill.path.resolve()
        )


class ClaudeBackend(Backend):
    """Backend for Claude Code."""

    name = "claude"

    def get_skills_dir(self, scope: Scope) -> Path:
        if scope == Scope.LOCAL:
            return Path(".claude/skills")
        else:
            return Path.home() / ".claude/skills"


class CrushBackend(Backend):
    """Backend for Crush."""

    name = "crush"

    def get_skills_dir(self, scope: Scope) -> Path:
        if scope == Scope.LOCAL:
            return Path(".crush/skills")
        else:
            return Path.home() / ".crush/skills"


class CursorBackend(Backend):
    """Backend for Cursor."""

    name = "cursor"

    def get_skills_dir(self, scope: Scope) -> Path:
        if scope == Scope.LOCAL:
            return Path(".cursor/skills")
        else:
            return Path.home() / ".cursor/skills"


class CodexBackend(Backend):
    """Backend for Codex."""

    name = "codex"

    def get_skills_dir(self, scope: Scope) -> Path:
        if scope == Scope.LOCAL:
            return Path(".codex/skills")
        else:
            return Path.home() / ".codex/skills"


class CopilotBackend(Backend):
    """Backend for GitHub Copilot."""

    name = "copilot"

    def get_skills_dir(self, scope: Scope) -> Path:
        if scope == Scope.LOCAL:
            return Path(".github/skills")
        else:
            return Path.home() / ".github/skills"


class GeminiBackend(Backend):
    """Backend for Gemini."""

    name = "gemini"

    def get_skills_dir(self, scope: Scope) -> Path:
        if scope == Scope.LOCAL:
            return Path(".gemini/skills")
        else:
            return Path.home() / ".gemini/skills"


class OpencodeBackend(Backend):
    """Backend for Opencode."""

    name = "opencode"

    def get_skills_dir(self, scope: Scope) -> Path:
        if scope == Scope.LOCAL:
            return Path(".opencode/skills")
        else:
            return Path.home() / ".opencode/skills"


# Registry of available backends
BACKENDS: dict[BackendName, type[Backend]] = {
    BackendName.CLAUDE: ClaudeBackend,
    BackendName.CODEX: CodexBackend,
    BackendName.COPILOT: CopilotBackend,
    BackendName.CRUSH: CrushBackend,
    BackendName.CURSOR: CursorBackend,
    BackendName.GEMINI: GeminiBackend,
    BackendName.OPENCODE: OpencodeBackend,
}


def get_backend(name: BackendName) -> Backend:
    """Get a backend instance by name."""
    return BACKENDS[name]()


def get_all_backends() -> list[Backend]:
    """Get all available backend instances."""
    return [backend_cls() for backend_cls in BACKENDS.values()]
