from pathlib import Path

import pytest
from typer.testing import CliRunner

from pixi_skills.cli import app
from pixi_skills.skill import Skill

runner = CliRunner()


class TestVersion:
    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "pixi-skills" in result.output

    def test_short_version_flag(self) -> None:
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert "pixi-skills" in result.output


class TestList:
    def test_list_no_skills(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "no local skills found" in result.output.lower()

    def test_list_local_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skill_dir = tmp_path / ".pixi/envs/default/share/agent-skills/test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: A test\n---\nBody\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = runner.invoke(app, ["list", "--scope", "local"])
        assert result.exit_code == 0
        assert "test-skill" in result.output

    def test_list_global_scope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = runner.invoke(app, ["list", "--scope", "global"])
        assert result.exit_code == 0

    def test_list_disambiguates_same_named_global_skills(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for env in ["env-a", "env-b"]:
            skill_dir = tmp_path / f".pixi/envs/{env}/share/agent-skills/shared"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: shared\ndescription: from {env}\n---\n"
            )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = runner.invoke(app, ["list", "--scope", "global"])

        assert result.exit_code == 0
        assert "shared (env-a)" in result.output
        assert "shared (env-b)" in result.output

    def test_list_env_with_global_scope_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["list", "--scope", "global", "--env", "custom"])
        assert result.exit_code == 1

    def test_list_custom_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skill_dir = tmp_path / ".pixi/envs/myenv/share/agent-skills/env-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: env\n---\nBody\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = runner.invoke(app, ["list", "--env", "myenv"])
        assert result.exit_code == 0
        assert "env-skill" in result.output


class TestStatus:
    def test_status_no_installed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        # All backends should be listed
        assert "claude" in result.output

    def test_status_specific_backend(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = runner.invoke(app, ["status", "--backend", "claude"])
        assert result.exit_code == 0
        assert "claude" in result.output

    def test_status_shows_installed_skill(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create a skill source directory
        skill_src = tmp_path / "skill-source"
        skill_src.mkdir()
        (skill_src / "SKILL.md").write_text("---\ndescription: x\n---\n")

        # Install it as a symlink in the Claude backend local dir
        claude_dir = tmp_path / ".claude" / "skills"
        claude_dir.mkdir(parents=True)
        (claude_dir / "my-skill").symlink_to(skill_src)

        result = runner.invoke(app, ["status", "--backend", "claude"])
        assert result.exit_code == 0
        assert "my-skill" in result.output


class TestManage:
    def test_manage_env_with_global_scope_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["manage", "--backend", "claude", "--scope", "global", "--env", "x"]
        )
        assert result.exit_code == 1

    def test_manage_no_skills_available(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = runner.invoke(
            app, ["manage", "--backend", "claude", "--scope", "local"]
        )
        assert result.exit_code == 1
        assert "no local skills available" in result.output.lower()

    def test_manage_switches_between_same_named_global_skills(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skill_dirs = {}
        for env in ["env-a", "env-b"]:
            skill_dir = tmp_path / f".pixi/envs/{env}/share/agent-skills/shared"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: shared\ndescription: from {env}\n---\n"
            )
            skill_dirs[env] = skill_dir

        installed_dir = tmp_path / ".claude/skills"
        installed_dir.mkdir(parents=True)
        installed_skill = installed_dir / "shared"
        installed_skill.symlink_to(skill_dirs["env-a"])

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        def select_env_b(
            skills: list[Skill], installed: dict[str, Path]
        ) -> list[Skill]:
            assert installed == {"shared": skill_dirs["env-a"].resolve()}
            return [skill for skill in skills if skill.environment == "env-b"]

        monkeypatch.setattr("pixi_skills.cli.select_skills_interactively", select_env_b)

        result = runner.invoke(
            app, ["manage", "--backend", "claude", "--scope", "global"]
        )

        assert result.exit_code == 0
        assert installed_skill.resolve() == skill_dirs["env-b"].resolve()
