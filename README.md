# pixi-skills

[![CI](https://img.shields.io/github/actions/workflow/status/pavelzw/pixi-skills/ci.yml?style=flat-square&branch=main)](https://github.com/pavelzw/pixi-skills/actions/workflows/ci.yml)
[![conda-forge](https://img.shields.io/conda/vn/conda-forge/pixi-skills?logoColor=white&logo=conda-forge&style=flat-square)](https://prefix.dev/channels/conda-forge/packages/pixi-skills)
[![pypi-version](https://img.shields.io/pypi/v/pixi-skills.svg?logo=pypi&logoColor=white&style=flat-square)](https://pypi.org/project/pixi-skills)
[![python-version](https://img.shields.io/pypi/pyversions/pixi-skills?logoColor=white&logo=python&style=flat-square)](https://pypi.org/project/pixi-skills)
[![conda-forge](https://img.shields.io/badge/prefix.dev%2Fskill--forge-F7CC49?style=flat-square)](https://prefix.dev/channels/skill-forge)
[![pixi-skills](https://img.shields.io/badge/pavelzw%2Fskill--forge-181717?style=flat-square&logo=github)](https://github.com/pavelzw/skill-forge)

Manage and install coding agent skills across multiple LLM backends using [pixi](https://pixi.sh).

pixi-skills discovers skills packaged in pixi environments and lets you install them into the configuration directories of various coding agents via symlinks.

For more background on why distributing agent skills through package managers makes sense, check out the blog post [Managing Agent Skills with Your Package Manager](https://pavel.pink/blog/pixi-skills).

## Installation

```bash
pixi global install pixi-skills
# or use without installing
pixi exec pixi-skills
```

## Concepts

### Skills

A skill is a directory containing a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: my-skill
description: "Does something useful for the agent"
---

Skill instructions go here as Markdown.
The agent reads this file to understand what the skill does.
```

The `name` field is optional and defaults to the directory name.
The `description` field is required.

A collection of ready-to-use skills is available at [skill-forge](https://prefix.dev/channels/skill-forge) ([source](https://github.com/pavelzw/skill-forge)).

### Scopes

- **Local** skills are discovered from the current project's pixi environment at `.pixi/envs/<env>/share/agent-skills/`.
- **Global** skills are discovered from globally installed pixi packages at `~/.pixi/envs/agent-skill-*/share/agent-skills/`.

### Supported backends

| Backend | Local directory | Global directory |
|---------|----------------|-----------------|
| Claude | `.claude/skills/` | `~/.claude/skills/` |
| Cline | `.agents/skills/` | `~/.agents/skills/` |
| Codex | `.codex/skills/` | `~/.codex/skills/` |
| Copilot | `.github/skills/` | `~/.github/skills/` |
| Crush | `.crush/skills/` | `~/.crush/skills/` |
| Cursor | `.cursor/skills/` | `~/.cursor/skills/` |
| Gemini | `.gemini/skills/` | `~/.gemini/skills/` |
| Kilo Code | `.kilocode/skills/` | `~/.kilocode/skills/` |
| Kiro | `.kiro/skills/` | `~/.kiro/skills/` |
| Opencode | `.opencode/skills/` | `~/.opencode/skills/` |
| Qoder | `.qoder/skills/` | `~/.qoder/skills/` |
| Roo Code | `.roo/skills/` | `~/.roo/skills/` |
| Trae | `.trae/skills/` | `~/.trae/skills/` |
| Windsurf | `.windsurf/skills/` | `~/.codeium/windsurf/skills/` |

Skills are installed as relative symlinks for portability.

## Usage

### List available skills

```bash
# List all local and global skills
pixi-skills list

# List only local skills
pixi-skills list --scope local

# List skills from a specific pixi environment
pixi-skills list --env myenv
```

### Manage skills interactively

```bash
# Interactive mode - prompts for backend and scope
pixi-skills manage

# Specify backend and scope directly
pixi-skills manage --backend claude --scope local
```

This opens an interactive checkbox selector where you can choose which skills to install or uninstall.

### Show installed skills

```bash
# Show installed skills across all backends
pixi-skills status

# Show installed skills for a specific backend
pixi-skills status --backend claude
```

## Development

This project is managed by [pixi](https://pixi.sh).

```bash
git clone https://github.com/pavelzw/pixi-skills
cd pixi-skills

pixi run pre-commit-install
pixi run postinstall
pixi run test
```
