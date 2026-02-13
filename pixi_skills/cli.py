import subprocess
from importlib.metadata import version
from typing import Annotated

import questionary
import typer
from rich.console import Console
from rich.table import Table

from pixi_skills.backend import BackendName, get_all_backends, get_backend
from pixi_skills.selector import CUSTOM_STYLE, select_skills_interactively
from pixi_skills.skill import (
    Scope,
    discover_global_skill_packages,
    discover_global_skills,
    discover_local_skills,
)


def _version_callback(value: bool) -> None:
    if value:
        print(f"pixi-skills {version('pixi-skills')}")
        raise typer.Exit()


app = typer.Typer(
    name="pixi-skills",
    help="Manage agent skills for LLM agents like Claude and Codex.",
)
console = Console()


def _print_skills_table(title: str, skills: list) -> None:
    """Print a table of skills."""
    if not skills:
        console.print(f"[dim]No {title.lower()} found.[/dim]")
        return

    table = Table(title=title)
    table.add_column("Name", style="cyan")
    table.add_column("Description", max_width=60, no_wrap=True)
    table.add_column("Path", style="dim")

    for skill in sorted(skills):
        table.add_row(
            skill.name,
            skill.description,
            str(skill.path),
        )

    console.print(table)


@app.callback()
def main(
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    pass


@app.command("list")
def list_skills(
    scope: Annotated[
        Scope | None,
        typer.Option(
            "--scope",
            "-s",
            help="Filter by scope.",
        ),
    ] = None,
    env: Annotated[
        str,
        typer.Option(
            "--env",
            "-e",
            help="Pixi environment to search for local skills.",
        ),
    ] = "default",
) -> None:
    """List all available skills."""
    # Validate --env is only used with local scope
    if scope == Scope.GLOBAL and env != "default":
        console.print("[red]--env can only be used with local scope[/red]")
        raise typer.Exit(1)

    # If a non-default environment is specified without an explicit scope,
    # implicitly restrict the scope to LOCAL so that global skills are not
    # listed alongside local skills that use the custom environment.
    if env != "default" and scope is None:
        scope = Scope.LOCAL
    scopes: list[Scope] = [scope] if scope else [Scope.LOCAL, Scope.GLOBAL]

    for s in scopes:
        if s == Scope.LOCAL:
            skills = discover_local_skills(env)
        else:
            skills = discover_global_skills()
        _print_skills_table(f"{s.value.capitalize()} Skills", skills)


def _prompt_for_scope() -> Scope:
    """Prompt the user to select a scope."""
    result = questionary.select(
        "Select scope",
        choices=[
            questionary.Choice(title=Scope.LOCAL.value, value=Scope.LOCAL),
            questionary.Choice(title=Scope.GLOBAL.value, value=Scope.GLOBAL),
        ],
        style=CUSTOM_STYLE,
        qmark="◆",
        pointer=">",
    ).ask()

    if result is None:
        raise typer.Exit(0)
    return result


def _prompt_for_backend() -> BackendName:
    """Prompt the user to select a backend."""
    result = questionary.select(
        "Select backend",
        choices=[questionary.Choice(title=b.value, value=b) for b in BackendName],
        style=CUSTOM_STYLE,
        qmark="◆",
        pointer=">",
    ).ask()

    if result is None:
        raise typer.Exit(0)
    return result


@app.command("manage")
def manage_skills(
    backend: Annotated[
        BackendName | None,
        typer.Option(
            "--backend",
            "-b",
            help="Backend to manage skills for.",
        ),
    ] = None,
    scope: Annotated[
        Scope | None,
        typer.Option(
            "--scope",
            "-s",
            help="Scope to manage.",
        ),
    ] = None,
    env: Annotated[
        str,
        typer.Option(
            "--env",
            "-e",
            help="Pixi environment to search for local skills.",
        ),
    ] = "default",
) -> None:
    """Interactively manage installed skills for a backend.

    Select skills to install them, unselect to uninstall them.
    """
    # Validate --env is only used with local scope
    if scope == Scope.GLOBAL and env != "default":
        console.print("[red]--env can only be used with local scope[/red]")
        raise typer.Exit(1)

    # Prompt for missing options
    if backend is None:
        backend = _prompt_for_backend()
    if scope is None:
        if env != "default":
            console.print("Using the local scope as environment was requested")
            scope = Scope.LOCAL
        else:
            scope = _prompt_for_scope()

    backend_instance = get_backend(backend)
    skills_dir = backend_instance.get_skills_dir(scope)
    console.print(f"Managing [cyan]{skills_dir}[/cyan]\n")

    # Get available skills for this scope (env only applies to local)
    if scope == Scope.LOCAL:
        available_skills = discover_local_skills(env)
    else:
        available_skills = discover_global_skills()
    if not available_skills:
        console.print(f"[yellow]No {scope.value} skills available.[/yellow]")
        raise typer.Exit(1)

    # Get currently installed skills
    installed_names = {name for name, _ in backend_instance.get_installed_skills(scope)}

    # Show interactive selector with installed skills pre-selected
    selected = select_skills_interactively(available_skills, installed_names)
    if selected is None:
        # cancelled by user
        raise typer.Exit(0)

    selected_names = {s.name for s in selected}

    # Determine what to install and uninstall
    to_install = [s for s in selected if s.name not in installed_names]
    to_uninstall = [name for name in installed_names if name not in selected_names]

    if not to_install and not to_uninstall:
        console.print("[dim]No changes.[/dim]")
        return

    # Install new skills
    for skill in to_install:
        try:
            symlink_path = backend_instance.install(skill)
            console.print(f"[green]Installed '{skill.name}' at {symlink_path}[/green]")
        except ValueError as e:
            console.print(f"[red]Failed to install '{skill.name}': {e}[/red]")

    # Uninstall removed skills
    for name in to_uninstall:
        if backend_instance.uninstall(name, scope):
            console.print(f"[yellow]Uninstalled '{name}'[/yellow]")
        else:
            console.print(f"[red]Failed to uninstall '{name}'[/red]")


@app.command("status")
def status(
    backend: Annotated[
        BackendName | None,
        typer.Option(
            "--backend",
            "-b",
            help="Filter by backend.",
        ),
    ] = None,
) -> None:
    """Show installed skills for all or a specific backend."""
    backends = [get_backend(backend)] if backend else get_all_backends()

    for b in backends:
        console.print(f"\n[bold]{b.name}[/bold]")

        for scope in Scope:
            installed = b.get_installed_skills(scope)
            if installed:
                table = Table(title=f"{scope.value.capitalize()} Skills")
                table.add_column("Name", style="cyan")
                table.add_column("Target Path", style="dim")

                for name, target in sorted(installed):
                    table.add_row(name, str(target))

                console.print(table)
            else:
                console.print(f"  [dim]No {scope.value} skills installed[/dim]")


@app.command("install")
def install_skill(
    skill_name: Annotated[
        str,
        typer.Argument(help="Name of the skill to install."),
    ],
    local: Annotated[
        bool,
        typer.Option(
            "--local",
            "-l",
            help="Install locally into the current project instead of globally.",
        ),
    ] = False,
    backend: Annotated[
        BackendName | None,
        typer.Option(
            "--backend",
            "-b",
            help="Backend to link the skill for.",
        ),
    ] = None,
    channel: Annotated[
        str,
        typer.Option(
            "--channel",
            "-c",
            help="Channel to install the skill from.",
        ),
    ] = "https://prefix.dev/skill-forge",
) -> None:
    """Install a skill and link it for the selected backend.

    By default, installs the skill globally using pixi global install.
    Use --local to add it as a dependency to the current project instead.
    """
    package_name = f"agent-skill-{skill_name}"

    if local:
        console.print(
            f"[cyan]Adding {package_name} from {channel} to the current project...[/cyan]"
        )
        result = subprocess.run(
            ["pixi", "add", "--channel", channel, package_name],
            capture_output=True,
            text=True,
        )
    else:
        console.print(
            f"[cyan]Installing {package_name} globally from {channel}...[/cyan]"
        )
        result = subprocess.run(
            ["pixi", "global", "install", "-c", channel, package_name],
            capture_output=True,
            text=True,
        )

    if result.returncode != 0:
        console.print(f"[red]Failed to install {package_name}:[/red]")
        if result.stderr:
            console.print(f"[red]{result.stderr.strip()}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Successfully installed {package_name}[/green]")

    # Discover the newly installed skill and link it
    if local:
        skills = discover_local_skills("default")
    else:
        skills = discover_global_skills()

    matching = [s for s in skills if s.name == skill_name]
    if not matching:
        console.print(
            f"[yellow]Skill installed but could not find '{skill_name}' "
            f"in discovered skills to link.[/yellow]"
        )
        raise typer.Exit(0)

    skill = matching[0]

    # Prompt for backend if not specified
    if backend is None:
        backend = _prompt_for_backend()

    backend_instance = get_backend(backend)
    try:
        symlink_path = backend_instance.install(skill)
        console.print(
            f"[green]Linked '{skill_name}' for {backend.value} at {symlink_path}[/green]"
        )
    except ValueError as e:
        console.print(f"[red]Failed to link '{skill_name}': {e}[/red]")
        raise typer.Exit(1)


@app.command("update")
def update_skill(
    skill_name: Annotated[
        str | None,
        typer.Argument(help="Name of the skill to update. If omitted, updates all."),
    ] = None,
    local: Annotated[
        bool,
        typer.Option(
            "--local",
            "-l",
            help="Update locally installed skills instead of global ones.",
        ),
    ] = False,
) -> None:
    """Update installed skills to their latest versions.

    By default, updates globally installed skills using pixi global upgrade.
    Use --local to update local project dependencies instead.
    """
    if local:
        if skill_name:
            console.print(
                f"[cyan]Updating agent-skill-{skill_name} in the current project...[/cyan]"
            )
            result = subprocess.run(
                ["pixi", "update", f"agent-skill-{skill_name}"],
                capture_output=True,
                text=True,
            )
        else:
            console.print(
                "[cyan]Updating all packages in the current project...[/cyan]"
            )
            result = subprocess.run(
                ["pixi", "update"],
                capture_output=True,
                text=True,
            )
    else:
        if skill_name:
            packages = [f"agent-skill-{skill_name}"]
        else:
            packages = discover_global_skill_packages()
            if not packages:
                console.print(
                    "[yellow]No global agent skills found to update.[/yellow]"
                )
                return

        failed = False
        for package_name in packages:
            console.print(f"[cyan]Upgrading {package_name} globally...[/cyan]")
            result = subprocess.run(
                ["pixi", "global", "upgrade", package_name],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                console.print(f"[red]Failed to upgrade {package_name}:[/red]")
                if result.stderr:
                    console.print(f"[red]{result.stderr.strip()}[/red]")
                failed = True
            else:
                console.print(f"[green]Upgraded {package_name}[/green]")

        if failed:
            raise typer.Exit(1)

    console.print("[green]Update complete.[/green]")

    # Re-link updated skills so symlinks point to the (possibly new) paths
    if local:
        skills = discover_local_skills("default")
    else:
        skills = discover_global_skills()

    # If a specific skill was requested, only re-link that one
    if skill_name:
        skills = [s for s in skills if s.name == skill_name]

    if not skills:
        return

    scope = Scope.LOCAL if local else Scope.GLOBAL
    for backend_instance in get_all_backends():
        installed = {name for name, _ in backend_instance.get_installed_skills(scope)}
        for skill in skills:
            if skill.name in installed:
                try:
                    symlink_path = backend_instance.install(skill)
                    console.print(
                        f"[green]Re-linked '{skill.name}' for "
                        f"{backend_instance.name} at {symlink_path}[/green]"
                    )
                except ValueError as e:
                    console.print(
                        f"[red]Failed to re-link '{skill.name}' for "
                        f"{backend_instance.name}: {e}[/red]"
                    )


if __name__ == "__main__":
    app()
