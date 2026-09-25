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
| `dev-standards registry generate [<path>]` | `--llm-cmd`, `--force`, `--debug` | Generate or refresh `<repo>_registry.yaml` at the repo root (no LLM call if the source docs are unchanged) |
| `dev-standards registry add [<path>]` | `--hub`, `--llm-cmd`, `--no-generate`, `--force`, `--debug` | Register a repo in the hub: generate its file if missing, symlink it, rebuild the rollup |
| `dev-standards registry refresh` | `--hub`, `--llm-cmd`, `--force`, `--debug` | Regenerate every linked repo (skipping unchanged), then the rollup; exits 1 if any repo failed |
| `dev-standards registry rollup` | `--hub`, `--debug` | Rebuild the hub's `registry.yaml` from the linked files |
| `dev-standards registry check` | `--hub`, `--debug` | Validate every hub file against the schema and report rollup drift; exits 1 on problems |
| `session-lint <path>...` | `--strict`, `--format text\|json`, `--debug` | Validate session files (frontmatter + `## Ledger`); directories recurse `*.md`, skipping `_template.md`, `specs/`, `archive/`; exits 1 on any error |
| `session-schema export` | `--out` (default `schemas/`), `--debug` | Write `session-header.v1.schema.json` / `session-ledger.v1.schema.json` from the Pydantic models |

`path` defaults to the current directory. Workspace fragments are read from the local
`claude/` directory of an editable install, or from `--fragments-dir` /
`$DEV_STANDARDS_CLAUDE_DIR`. The registry LLM command is `--llm-cmd` /
`$DEV_STANDARDS_REGISTRY_LLM_CMD` (default `claude -p`); the hub is `--hub` /
`$DEV_STANDARDS_REGISTRY_HUB` (default `~/.repository_registry`).
From another repo, run the linter without installing:
`uvx --from git+https://github.com/pdrangeid/dev-standards@develop session-lint .session/`
(or `uvx --from ~/develop/dev-standards ...` for a local checkout).
See `README.md` (`## Multi-Repo Workspaces`, `## Repo Registry`, `## Session Files and session-lint`) for the workflows, and
`docs/registry-schema.md` for the registry file contract.

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
