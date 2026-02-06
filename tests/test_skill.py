import warnings
from pathlib import Path

import pytest

from pixi_skills.skill import (
    Scope,
    Skill,
    discover_global_skills,
    discover_local_skills,
    parse_skill_md,
)

# --- Scope ordering ---


class TestScope:
    def test_local_less_than_global(self) -> None:
        assert Scope.LOCAL < Scope.GLOBAL

    def test_global_greater_than_local(self) -> None:
        assert Scope.GLOBAL > Scope.LOCAL

    def test_equal(self) -> None:
        assert Scope.LOCAL == Scope.LOCAL
        assert Scope.GLOBAL == Scope.GLOBAL

    def test_le_ge(self) -> None:
        assert Scope.LOCAL <= Scope.GLOBAL
        assert Scope.LOCAL <= Scope.LOCAL
        assert Scope.GLOBAL >= Scope.LOCAL
        assert Scope.GLOBAL >= Scope.GLOBAL


# --- parse_skill_md ---


class TestParseSkillMd:
    def test_basic(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text('---\nname: my-skill\ndescription: "A test skill"\n---\nBody\n')
        name, desc = parse_skill_md(md)
        assert name == "my-skill"
        assert desc == "A test skill"

    def test_unquoted_description(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text("---\nname: foo\ndescription: some desc\n---\nBody\n")
        name, desc = parse_skill_md(md)
        assert name == "foo"
        assert desc == "some desc"

    def test_single_quoted_description(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text("---\nname: foo\ndescription: 'single quoted'\n---\nBody\n")
        name, desc = parse_skill_md(md)
        assert desc == "single quoted"

    def test_name_optional(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text("---\ndescription: no name\n---\nBody\n")
        name, desc = parse_skill_md(md)
        assert name is None
        assert desc == "no name"

    def test_multiline_description_pipe(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text("---\ndescription: |\n  line1\n  line2\n---\nBody\n")
        name, desc = parse_skill_md(md)
        assert desc == ""

    def test_multiline_description_folded(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text("---\ndescription: >\n  line1\n  line2\n---\nBody\n")
        name, desc = parse_skill_md(md)
        assert desc == ""

    def test_missing_frontmatter(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text("no frontmatter here\n")
        with pytest.raises(ValueError, match="must start with YAML frontmatter"):
            parse_skill_md(md)

    def test_missing_end_marker(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text("---\nname: foo\ndescription: bar\n")
        with pytest.raises(ValueError, match="Invalid YAML frontmatter"):
            parse_skill_md(md)

    def test_missing_description(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text("---\nname: foo\n---\nBody\n")
        with pytest.raises(ValueError, match="Missing 'description'"):
            parse_skill_md(md)

    def test_quoted_name(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text('---\nname: "quoted-name"\ndescription: desc\n---\nBody\n')
        name, desc = parse_skill_md(md)
        assert name == "quoted-name"


# --- Skill dataclass ---


class TestSkill:
    def test_from_directory(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\ndescription: hello\n---\nBody\n")
        skill = Skill.from_directory(skill_dir, Scope.LOCAL)
        assert skill.name == "my-skill"
        assert skill.description == "hello"
        assert skill.scope == Scope.LOCAL
        assert skill.path == skill_dir

    def test_from_directory_with_name_override(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "dir-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: custom-name\ndescription: desc\n---\nBody\n"
        )
        skill = Skill.from_directory(skill_dir, Scope.GLOBAL)
        assert skill.name == "custom-name"

    def test_from_directory_no_skill_md(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "empty"
        skill_dir.mkdir()
        with pytest.raises(ValueError, match="No SKILL.md found"):
            Skill.from_directory(skill_dir, Scope.LOCAL)

    def test_ordering(self, tmp_path: Path) -> None:
        a = Skill(Scope.LOCAL, "alpha", "desc", tmp_path)
        b = Skill(Scope.LOCAL, "beta", "desc", tmp_path)
        c = Skill(Scope.GLOBAL, "alpha", "desc", tmp_path)
        assert sorted([c, b, a]) == [a, b, c]

    def test_frozen(self, tmp_path: Path) -> None:
        skill = Skill(Scope.LOCAL, "test", "desc", tmp_path)
        with pytest.raises(AttributeError):
            skill.name = "other"  # type: ignore[misc]


# --- Skill discovery ---


class TestDiscoverLocalSkills:
    def test_discovers_skills(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skill_dir = tmp_path / ".pixi/envs/default/share/agent-skills/my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: local skill\n---\n")
        monkeypatch.chdir(tmp_path)

        skills = discover_local_skills("default")
        assert len(skills) == 1
        assert skills[0].name == "my-skill"
        assert skills[0].scope == Scope.LOCAL

    def test_empty_when_no_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert discover_local_skills("default") == []

    def test_skips_invalid_skills(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        base = tmp_path / ".pixi/envs/default/share/agent-skills"
        # valid skill
        valid = base / "valid"
        valid.mkdir(parents=True)
        (valid / "SKILL.md").write_text("---\ndescription: good\n---\n")
        # invalid skill (no description)
        invalid = base / "invalid"
        invalid.mkdir(parents=True)
        (invalid / "SKILL.md").write_text("---\nname: bad\n---\n")

        monkeypatch.chdir(tmp_path)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            skills = discover_local_skills("default")
        assert len(skills) == 1
        assert skills[0].name == "valid"
        assert len(w) == 1

    def test_custom_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        skill_dir = tmp_path / ".pixi/envs/myenv/share/agent-skills/s1"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: env skill\n---\n")
        monkeypatch.chdir(tmp_path)

        skills = discover_local_skills("myenv")
        assert len(skills) == 1

    def test_skips_dirs_without_skill_md(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        base = tmp_path / ".pixi/envs/default/share/agent-skills/no-md"
        base.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        assert discover_local_skills("default") == []


class TestDiscoverGlobalSkills:
    def test_discovers_skills(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skill_dir = tmp_path / ".pixi/envs/agent-skill-typst/share/agent-skills/typst"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: typst skill\n---\n")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        skills = discover_global_skills()
        assert len(skills) == 1
        assert skills[0].name == "typst"
        assert skills[0].scope == Scope.GLOBAL

    def test_empty_when_no_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert discover_global_skills() == []

    def test_skips_non_agent_skill_envs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # This env doesn't match the agent-skill-* pattern
        skill_dir = tmp_path / ".pixi/envs/other-env/share/agent-skills/s1"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: other\n---\n")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        assert discover_global_skills() == []
