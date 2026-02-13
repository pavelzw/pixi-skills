from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pixi_skills.cli import app

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


class TestInstall:
    def _make_global_skill(self, tmp_path: Path, skill_name: str) -> Path:
        """Create a fake global skill directory as pixi global install would."""
        skill_dir = (
            tmp_path
            / f".pixi/envs/agent-skill-{skill_name}/share/agent-skills/{skill_name}"
        )
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\ndescription: A {skill_name} skill\n---\nBody\n"
        )
        return skill_dir

    def _make_local_skill(
        self, tmp_path: Path, skill_name: str, env: str = "default"
    ) -> Path:
        """Create a fake local skill directory as pixi add would."""
        skill_dir = tmp_path / f".pixi/envs/{env}/share/agent-skills/{skill_name}"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\ndescription: A {skill_name} skill\n---\nBody\n"
        )
        return skill_dir

    def test_install_global(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Pre-create the skill so discovery works after the mocked install
        self._make_global_skill(tmp_path, "my-tool")

        with patch("pixi_skills.cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = runner.invoke(app, ["install", "my-tool", "--backend", "claude"])

        assert result.exit_code == 0
        assert "Successfully installed" in result.output
        assert "Linked" in result.output

        # Verify pixi global install was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[:3] == ["pixi", "global", "install"]
        assert "agent-skill-my-tool" in call_args

        # Verify symlink was created
        symlink = tmp_path / ".claude/skills/my-tool"
        assert symlink.is_symlink()

    def test_install_local(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        self._make_local_skill(tmp_path, "my-tool")

        with patch("pixi_skills.cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = runner.invoke(
                app, ["install", "my-tool", "--local", "--backend", "claude"]
            )

        assert result.exit_code == 0
        assert "Successfully installed" in result.output

        # Verify pixi add was called
        call_args = mock_run.call_args[0][0]
        assert call_args[:2] == ["pixi", "add"]
        assert "agent-skill-my-tool" in call_args

        # Verify symlink was created in the local dir
        symlink = tmp_path / ".claude/skills/my-tool"
        assert symlink.is_symlink()

    def test_install_pixi_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with patch("pixi_skills.cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "package not found"

            result = runner.invoke(
                app, ["install", "nonexistent", "--backend", "claude"]
            )

        assert result.exit_code == 1
        assert "Failed to install" in result.output

    def test_install_custom_channel(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        self._make_global_skill(tmp_path, "my-tool")

        with patch("pixi_skills.cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = runner.invoke(
                app,
                [
                    "install",
                    "my-tool",
                    "--backend",
                    "claude",
                    "--channel",
                    "https://example.com/channel",
                ],
            )

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert "https://example.com/channel" in call_args


class TestUpdate:
    def test_update_global_single(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        with patch("pixi_skills.cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = runner.invoke(app, ["update", "my-tool"])

        assert result.exit_code == 0
        assert "Update complete" in result.output
        call_args = mock_run.call_args[0][0]
        assert call_args == ["pixi", "global", "upgrade", "agent-skill-my-tool"]

    def test_update_global_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create two global skill envs
        for name in ("agent-skill-foo", "agent-skill-bar"):
            (tmp_path / f".pixi/envs/{name}").mkdir(parents=True)

        with patch("pixi_skills.cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        # Should call pixi global upgrade for each agent-skill-* package
        assert mock_run.call_count == 2
        upgraded = {tuple(c[0][0]) for c in mock_run.call_args_list}
        assert ("pixi", "global", "upgrade", "agent-skill-foo") in upgraded
        assert ("pixi", "global", "upgrade", "agent-skill-bar") in upgraded

    def test_update_global_all_no_skills(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        assert "No global agent skills found" in result.output

    def test_update_local_single(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        with patch("pixi_skills.cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = runner.invoke(app, ["update", "my-tool", "--local"])

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert call_args == ["pixi", "update", "agent-skill-my-tool"]

    def test_update_local_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        with patch("pixi_skills.cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = runner.invoke(app, ["update", "--local"])

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert call_args == ["pixi", "update"]

    def test_update_relinks_installed_skill(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create a global skill and a pre-existing symlink for claude backend
        skill_dir = (
            tmp_path / ".pixi/envs/agent-skill-my-tool/share/agent-skills/my-tool"
        )
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: A tool\n---\nBody\n")

        claude_dir = tmp_path / ".claude/skills"
        claude_dir.mkdir(parents=True)
        # Create an old symlink pointing somewhere else
        old_target = tmp_path / "old-location"
        old_target.mkdir()
        (claude_dir / "my-tool").symlink_to(old_target)

        with patch("pixi_skills.cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = runner.invoke(app, ["update", "my-tool"])

        assert result.exit_code == 0
        assert "Re-linked" in result.output
        # Symlink should now point to the discovered skill path
        assert (claude_dir / "my-tool").resolve() == skill_dir.resolve()

    def test_update_relinks_all_skills(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create two global skills
        for name in ("tool-a", "tool-b"):
            skill_dir = (
                tmp_path / f".pixi/envs/agent-skill-{name}/share/agent-skills/{name}"
            )
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\ndescription: {name}\n---\nBody\n"
            )

        # Only tool-a is installed in claude backend
        claude_dir = tmp_path / ".claude/skills"
        claude_dir.mkdir(parents=True)
        old_target = tmp_path / "old"
        old_target.mkdir()
        (claude_dir / "tool-a").symlink_to(old_target)

        with patch("pixi_skills.cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        # tool-a should be re-linked, tool-b should not be re-linked
        assert "Re-linked 'tool-a'" in result.output
        assert "Re-linked 'tool-b'" not in result.output

    def test_update_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        with patch("pixi_skills.cli.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "something went wrong"

            result = runner.invoke(app, ["update", "bad-skill"])

        assert result.exit_code == 1
        assert "Failed to upgrade" in result.output
