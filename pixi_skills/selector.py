from collections import Counter
from pathlib import Path

import questionary
from prompt_toolkit.styles import Style

from pixi_skills.skill import Skill

# Custom style matching the desired look
CUSTOM_STYLE = Style(
    [
        ("qmark", "fg:ansimagenta bold"),  # Diamond question mark
        ("question", "bold"),  # Question text
        ("pointer", "fg:ansimagenta bold"),  # Pointer arrow
        (
            "highlighted",
            "fg:ansimagenta bold underline",
        ),  # Currently highlighted - magenta text with underline
        ("selected", "noreverse"),  # Selected item - no text color change
        ("checkbox", "fg:ansigray"),  # Unselected checkbox
        ("checkbox-selected", "fg:ansigreen bold"),  # Selected checkbox (green)
        ("text", "fg:ansigray"),  # Dimmed non-highlighted text
        ("instruction", "fg:ansigray"),  # Instructions
    ]
)


def select_skills_interactively(
    skills: list[Skill], installed: dict[str, Path] | None = None
) -> list[Skill] | None:
    """Run the interactive skill selector and return selected skills.

    Args:
        skills: List of available skills to choose from.
        installed: Mapping of installed skill names to their source paths.

    Returns:
        List of selected skills, or None if the user cancelled.
    """
    if not skills:
        return []

    if installed is None:
        installed = {}

    sorted_skills = sorted(skills)
    ambiguous_names = {
        name
        for name, count in Counter(skill.name for skill in skills).items()
        if count > 1
    }
    skills_by_value: dict[str, Skill] = {}

    choices = []
    for skill in sorted_skills:
        value = str(skill.path)
        skills_by_value[value] = skill
        if installed:
            checked = installed.get(skill.name) == skill.path.resolve()
        else:
            checked = skill.name not in ambiguous_names
        choices.append(
            questionary.Choice(
                title=(
                    f"{skill.display_name(disambiguate=skill.name in ambiguous_names)} "
                    f"({skill.description})"
                ),
                value=value,
                checked=checked,
            )
        )

    def validate_selection(selected: list[str]) -> bool | str:
        duplicate_names = sorted(
            name
            for name, count in Counter(
                skills_by_value[value].name for value in selected
            ).items()
            if count > 1
        )
        if duplicate_names:
            names = ", ".join(duplicate_names)
            return f"Select at most one source for each skill: {names}"
        return True

    selected_values = questionary.checkbox(
        "Select skills to install",
        choices=choices,
        style=CUSTOM_STYLE,
        qmark="◆",
        pointer=">",
        instruction="(space select, enter confirm, ↑↓ move, a toggle all)",
        validate=validate_selection,
    ).ask()

    # Questionary's safe ``ask`` method catches Ctrl-C and returns None.
    if selected_values is None:
        return None
    return [skills_by_value[value] for value in selected_values]
