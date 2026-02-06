from pixi_skills.selector import select_skills_interactively


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
