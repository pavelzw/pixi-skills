from pathlib import Path

from pytest_mock import MockerFixture

from pixi_skills.selector import select_skills_interactively
from pixi_skills.skill import Scope, Skill


class TestSelectSkillsInteractively:
    def test_empty_skills_list(self) -> None:
        result = select_skills_interactively([], None)
        assert result == []

    def test_empty_skills_list_with_installed(self) -> None:
        result = select_skills_interactively([], {"some-skill"})
        assert result == []

    def test_none_installed_defaults_to_empty(self) -> None:
        result = select_skills_interactively([], None)
        assert result == []

    def test_all_checked_when_no_installed(self, mocker: MockerFixture) -> None:
        """When installed is empty (first use), all skills should be pre-checked."""
        mock_checkbox = mocker.patch("pixi_skills.selector.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = []

        skills = [
            Skill(scope=Scope.LOCAL, name="skill-a", description="A", path=Path("/a")),
            Skill(scope=Scope.LOCAL, name="skill-b", description="B", path=Path("/b")),
        ]
        select_skills_interactively(skills, installed=set())

        choices = mock_checkbox.call_args.kwargs["choices"]
        assert all(c.checked for c in choices)

    def test_only_installed_checked_when_some_installed(
        self, mocker: MockerFixture
    ) -> None:
        """When some skills are installed, only those should be pre-checked."""
        mock_checkbox = mocker.patch("pixi_skills.selector.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = []

        skills = [
            Skill(scope=Scope.LOCAL, name="skill-a", description="A", path=Path("/a")),
            Skill(scope=Scope.LOCAL, name="skill-b", description="B", path=Path("/b")),
        ]
        select_skills_interactively(skills, installed={"skill-a"})

        choices = mock_checkbox.call_args.kwargs["choices"]
        choices_by_checked = {c.value.name: c.checked for c in choices}
        assert choices_by_checked["skill-a"] is True
        assert choices_by_checked["skill-b"] is False
