import questionary
from prompt_toolkit.styles import Style

from pixi_skills.skill import Skill

# Custom style matching the desired look
CUSTOM_STYLE = Style(
    [
        ("qmark", "fg:ansimagenta bold"),  # Diamond question mark
        ("question", "bold"),  # Question text
        ("pointer", "fg:ansimagenta bold"),  # Pointer arrow
        ("highlighted", "noreverse fg:ansiwhite"),  # Currently highlighted - bright
        ("selected", "noreverse"),  # Selected item - no text color change
        ("checkbox", "fg:ansigray"),  # Unselected checkbox
        ("checkbox-selected", "fg:ansigreen bold"),  # Selected checkbox (green)
        ("text", "fg:ansigray"),  # Dimmed non-highlighted text
        ("instruction", "fg:ansigray"),  # Instructions
    ]
)


def select_skills_interactively(
    skills: list[Skill], installed: set[str] | None = None
) -> list[Skill] | None:
    """Run the interactive skill selector and return selected skills.

    Args:
        skills: List of available skills to choose from.
        installed: Set of skill names that are currently installed (pre-selected).

    Returns:
        List of selected skills, or None if the user cancelled.
    """
    if not skills:
        return []

    if installed is None:
        installed = set()

    sorted_skills = sorted(skills)

    choices = [
        questionary.Choice(
            title=f"{skill.name} ({skill.description})",
            value=skill,
            checked=(not installed) or (skill.name in installed),
        )
        for skill in sorted_skills
    ]

    selected = questionary.checkbox(
        "Select skills to install",
        choices=choices,
        style=CUSTOM_STYLE,
        qmark="◆",
        pointer=">",
        instruction="(space select, enter confirm, ↑↓ move, a toggle all)",
    ).ask()

    return selected
