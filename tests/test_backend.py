from pathlib import Path

import pytest

from pixi_skills.backend import (
    BACKENDS,
    Backend,
    BackendName,
    ClaudeBackend,
    CodexBackend,
    CopilotBackend,
    CrushBackend,
    CursorBackend,
    GeminiBackend,
    OpencodeBackend,
    WindsurfBackend,
    get_all_backends,
    get_backend,
)
from pixi_skills.skill import Scope, Skill

SetupFixture = tuple[Backend, Skill, Path]


# --- Backend registry ---


class TestBackendRegistry:
    def test_get_backend(self) -> None:
        backend = get_backend(BackendName.CLAUDE)
        assert isinstance(backend, ClaudeBackend)

    def test_get_all_backends(self) -> None:
        backends = get_all_backends()
        assert len(backends) == len(BACKENDS)

    def test_all_backend_names_registered(self) -> None:
        for name in BackendName:
            assert name in BACKENDS


# --- get_skills_dir ---


@pytest.mark.parametrize(
    "backend_cls,local_dir,global_suffix",
    [
        (ClaudeBackend, ".claude/skills", ".claude/skills"),
        (CrushBackend, ".crush/skills", ".crush/skills"),
        (CursorBackend, ".cursor/skills", ".cursor/skills"),
        (CodexBackend, ".codex/skills", ".codex/skills"),
        (CopilotBackend, ".github/skills", ".github/skills"),
        (GeminiBackend, ".gemini/skills", ".gemini/skills"),
        (OpencodeBackend, ".opencode/skills", ".opencode/skills"),
        (WindsurfBackend, ".windsurf/skills", ".codeium/windsurf/skills"),
    ],
)
class TestGetSkillsDir:
    def test_local(
        self, backend_cls: type[Backend], local_dir: str, global_suffix: str
    ) -> None:
        backend = backend_cls()
        assert backend.get_skills_dir(Scope.LOCAL) == Path(local_dir)

    def test_global(
        self, backend_cls: type[Backend], local_dir: str, global_suffix: str
    ) -> None:
        backend = backend_cls()
        assert backend.get_skills_dir(Scope.GLOBAL) == Path.home() / global_suffix


# --- Install / Uninstall / is_installed ---


class TestBackendInstallation:
    @pytest.fixture()
    def setup(self, tmp_path: Path) -> SetupFixture:
        """Create a fake skill and a backend that uses tmp_path."""
        skill_dir = tmp_path / "skills-source" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: test\n---\n")
        skill = Skill(Scope.LOCAL, "my-skill", "test", skill_dir)

        # Patch ClaudeBackend to use tmp_path
        install_dir = tmp_path / "install"

        class TmpBackend(ClaudeBackend):
            def get_skills_dir(self, scope: Scope) -> Path:
                return install_dir

        backend = TmpBackend()
        return backend, skill, install_dir

    def test_install_creates_symlink(self, setup: SetupFixture) -> None:
        backend, skill, install_dir = setup
        result = backend.install(skill)
        assert result == install_dir / "my-skill"
        assert result.is_symlink()
        assert result.resolve() == skill.path.resolve()

    def test_install_idempotent(self, setup: SetupFixture) -> None:
        backend, skill, install_dir = setup
        first = backend.install(skill)
        second = backend.install(skill)
        assert first == second

    def test_install_replaces_different_symlink(
        self, setup: SetupFixture, tmp_path: Path
    ) -> None:
        backend, skill, install_dir = setup
        install_dir.mkdir(parents=True, exist_ok=True)
        # Point at a real but different directory so .exists() returns True
        other = tmp_path / "other-skill"
        other.mkdir()
        existing = install_dir / "my-skill"
        existing.symlink_to(other)

        result = backend.install(skill)
        assert result.resolve() == skill.path.resolve()

    def test_install_fails_on_regular_file(self, setup: SetupFixture) -> None:
        backend, skill, install_dir = setup
        install_dir.mkdir(parents=True, exist_ok=True)
        (install_dir / "my-skill").write_text("not a symlink")

        with pytest.raises(ValueError, match="exists and is not a symlink"):
            backend.install(skill)

    def test_uninstall(self, setup: SetupFixture) -> None:
        backend, skill, install_dir = setup
        backend.install(skill)
        assert backend.uninstall("my-skill", Scope.LOCAL)
        assert not (install_dir / "my-skill").exists()

    def test_uninstall_not_found(self, setup: SetupFixture) -> None:
        backend, skill, install_dir = setup
        assert not backend.uninstall("nonexistent", Scope.LOCAL)

    def test_is_installed(self, setup: SetupFixture) -> None:
        backend, skill, install_dir = setup
        assert not backend.is_installed(skill)
        backend.install(skill)
        assert backend.is_installed(skill)

    def test_get_installed_skills(self, setup: SetupFixture) -> None:
        backend, skill, install_dir = setup
        assert backend.get_installed_skills(Scope.LOCAL) == []

        backend.install(skill)
        installed = backend.get_installed_skills(Scope.LOCAL)
        assert len(installed) == 1
        assert installed[0][0] == "my-skill"
        assert installed[0][1] == skill.path.resolve()

    def test_install_creates_relative_symlink(self, setup: SetupFixture) -> None:
        backend, skill, install_dir = setup
        result = backend.install(skill)
        # The raw symlink target should be relative, not absolute
        raw_target = result.readlink()
        assert not raw_target.is_absolute()
