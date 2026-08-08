# Usage Instructions: dev-standards

## Quick Start

```sh
# Activate environment
source activate_env.sh

# Run (update once CLI args are defined)
PYTHONPATH=. uv run python -m dev_Standards.main --debug
```

## Commands

| Command | Arguments | Description |
|:---|:---|:---|
| _TBD_ | _TBD_ | _TBD_ |

## Configuration

Edit `config/config.yaml` to set paths and defaults.
Copy `.env.example` to `.env` and fill in credentials.

## claude.md Modules

`setup-project.sh --modules <list>` (or the interactive menu) composes a new
project's `claude.md` from `claude/base.md` plus any of the modules below,
fetched from `claude/modules/`:

| Module key | What it covers |
|:---|:---|
| `neo4j` | Cypher conventions, MERGE/ON CREATE patterns, node labels, relationship vocabulary |
| `manifest-analyzer` | Manifest-first philosophy, URI convention, UnresolvedAsset, TypeMapper, DataSampler |
| `live-exporter` | Strategic Exporter — driver management, amplifier payload, GraphSchema, Lesson logging |
| `ast-analyzer` | Codebase Graph Analyzer — two-pass parse, entity IDs, `has_label()`, `safe_primitive()` |
| `llm` | Two-pass LLM pipeline design, chunking discipline, config conventions for LLM calls |

See `README.md` for full scaffolding and refresh examples.
