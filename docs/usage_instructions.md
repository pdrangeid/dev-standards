# Usage Instructions: dev-standards

## Quick Start

```sh
# Preferred
uv venv && uv pip install -e .[dev]
uv run dev-standards workspace check ~/workspaces/my-effort --debug

# Fallback (traditional venv activated)
dev-standards workspace check ~/workspaces/my-effort --debug
```

## Commands

| Command | Arguments | Description |
|:---|:---|:---|
| `dev-standards workspace new <path>` | `--from workspace.yaml` (required), `--no-commit`, `--fragments-dir`, `--debug` | Validate the yaml, create the folder, `git init`, render, copy `.session/_template.md`, make the first commit |
| `dev-standards workspace render [<path>]` | `--fragments-dir`, `--debug` | Re-render generated files after editing `workspace.yaml`; hand-written `AGENTS.md` sections and unrelated `settings.local.json` keys are preserved |
| `dev-standards workspace check [<path>]` | `--fragments-dir`, `--debug` | Validate the yaml and report drift between it and the rendered files; exits 1 on drift |

`path` defaults to the current directory. Fragments are read from the local `claude/`
directory of an editable install, or from `--fragments-dir` / `$DEV_STANDARDS_CLAUDE_DIR`.
See `README.md` (`## Multi-Repo Workspaces`) for the workflow and what is safe to hand-edit.

## Configuration

Edit `config/config.yaml` to set paths and defaults.
Copy `.env.example` to `.env` and fill in credentials.

## AGENTS.md Modules

`setup-project.sh --modules <list>` (or the interactive menu) composes a new
project's `AGENTS.md` from `claude/base.md` plus any of the modules below,
fetched from `claude/modules/`:

| Module key | What it covers |
|:---|:---|
| `neo4j` | Cypher conventions, MERGE/ON CREATE patterns, node labels, relationship vocabulary |
| `manifest-analyzer` | Manifest-first philosophy, URI convention, UnresolvedAsset, TypeMapper, DataSampler |
| `live-exporter` | Strategic Exporter — driver management, amplifier payload, GraphSchema, Lesson logging |
| `ast-analyzer` | Codebase Graph Analyzer — two-pass parse, entity IDs, `has_label()`, `safe_primitive()` |
| `llm` | Two-pass LLM pipeline design, chunking discipline, config conventions for LLM calls |

See `README.md` for full scaffolding and refresh examples.
