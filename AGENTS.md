## Package management

This repository is using the pixi package manager. The full documentation for pixi can be found at https://pixi.prefix.dev/latest/llms-full.txt or with `pixi --help`.
If you change `pixi.toml`, please run `pixi lock` afterwards.

In case you want to run any commands (like `pytest`), prepend them with `pixi run`.

## Code Standards

### Required Before Each Commit

- To ensure that our code-formatting is in line with the standards we follow, run `pixi run pre-commit-run` before committing any changes.
