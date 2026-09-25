from pathlib import Path

from pytest_mock import MockerFixture

from pixi_skills.selector import select_skills_interactively
from pixi_skills.skill import Scope, Skill


class TestSelectSkillsInteractively:
    def test_empty_skills_list(self) -> None:
        result = select_skills_interactively([], None)
        assert result == []

    def test_empty_skills_list_with_installed(self) -> None:
        result = select_skills_interactively([], {"some-skill": Path("/some-skill")})
        assert result == []

    def test_none_installed_defaults_to_empty(self) -> None:
        result = select_skills_interactively([], None)
        assert result == []

    def test_returns_none_when_cancelled(self, mocker: MockerFixture) -> None:
        mock_checkbox = mocker.patch("pixi_skills.selector.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = None
        skills = [Skill(Scope.LOCAL, "skill-a", "A", Path("/a"))]

        assert select_skills_interactively(skills) is None

    def test_all_checked_when_no_installed(self, mocker: MockerFixture) -> None:
        """When installed is empty (first use), all skills should be pre-checked."""
        mock_checkbox = mocker.patch("pixi_skills.selector.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = []

        skills = [
            Skill(scope=Scope.LOCAL, name="skill-a", description="A", path=Path("/a")),
            Skill(scope=Scope.LOCAL, name="skill-b", description="B", path=Path("/b")),
        ]
        select_skills_interactively(skills, installed={})

        choices = mock_checkbox.call_args.kwargs["choices"]
        assert all(c.checked for c in choices)

    def test_only_installed_checked_when_some_installed(
        self, mocker: MockerFixture
    ) -> None:
        """When some skills are installed, only those should be pre-checked."""
        mock_checkbox = mocker.patch("pixi_skills.selector.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = []

        path_a = Path("/a").resolve()
        path_b = Path("/b").resolve()
        skills = [
            Skill(scope=Scope.LOCAL, name="skill-a", description="A", path=path_a),
            Skill(scope=Scope.LOCAL, name="skill-b", description="B", path=path_b),
        ]
        select_skills_interactively(skills, installed={"skill-a": path_a})

        choices = mock_checkbox.call_args.kwargs["choices"]
        choices_by_checked = {c.value: c.checked for c in choices}
        assert choices_by_checked[str(path_a)] is True
        assert choices_by_checked[str(path_b)] is False

    def test_ambiguous_names_include_environment_and_select_installed_source(
        self, mocker: MockerFixture
    ) -> None:
        mock_checkbox = mocker.patch("pixi_skills.selector.questionary.checkbox")
        path_a = Path("/env-a/shared").resolve()
        path_b = Path("/env-b/shared").resolve()
        skills = [
            Skill(
                Scope.GLOBAL,
                "shared",
                "From A",
                path_a,
                environment="env-a",
            ),
            Skill(
                Scope.GLOBAL,
                "shared",
                "From B",
                path_b,
                environment="env-b",
            ),
        ]
        mock_checkbox.return_value.ask.return_value = [str(path_b)]

        selected = select_skills_interactively(skills, installed={"shared": path_b})

        choices = mock_checkbox.call_args.kwargs["choices"]
        assert [choice.title for choice in choices] == [
            "shared (env-a) (From A)",
            "shared (env-b) (From B)",
        ]
        assert [choice.checked for choice in choices] == [False, True]
        assert selected is not None
        assert selected[0] is skills[1]

    def test_rejects_multiple_sources_for_same_skill(
        self, mocker: MockerFixture
    ) -> None:
        mock_checkbox = mocker.patch("pixi_skills.selector.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = []
        path_a = Path("/a")
        path_b = Path("/b")
        skills = [
            Skill(Scope.GLOBAL, "shared", "A", path_a, environment="env-a"),
            Skill(Scope.GLOBAL, "shared", "B", path_b, environment="env-b"),
        ]

        select_skills_interactively(skills, installed={})

        choices = mock_checkbox.call_args.kwargs["choices"]
        assert [choice.checked for choice in choices] == [False, False]
        validate = mock_checkbox.call_args.kwargs["validate"]
        assert validate([str(path_a)]) is True
        assert validate([str(path_a), str(path_b)]) == (
            "Select at most one source for each skill: shared"
        )
