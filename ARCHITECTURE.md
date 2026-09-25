# Architecture: dev-standards

dev-standards is a scaffolding and standards repo. Its original deliverables are two bash
scripts plus modular `AGENTS.md` content (`claude/`); the `workspace` module adds a Python
CLI that scaffolds multi-repo Claude Code workspaces from the same fragment library, the
`registry` module generates per-repo registry files, and `session_schema` defines and lints
the `.session/` file format (see ADR-0001).

## Overview

Standards live as markdown fragments in `claude/` (`base.md` + `modules/*.md`). Two consumers
compose them:

- **Shell scripts** (`setup-project.sh`, `refresh-dev-standards.sh`) `curl` the fragments from
  GitHub and write a project's `AGENTS.md` (auto-generated block above `## Project-Specific`).
- **`dev-standards workspace`** reads the same fragments from a local checkout and writes a
  workspace's `AGENTS.md` (marker-delimited generated regions; hand-written text preserved).

The two share content, not transport — core improvements reach workspaces on the next
`workspace render`, exactly as they reach projects on the next refresh.

## Data Flow (workspace)

```
workspace.yaml ──load/validate──▶ Workspace (pydantic)
                                       │
claude/base.md ──────────┐             ▼
claude/modules/<m>.md ───┼─▶ compose ─▶ plan_render(ws, root) ──▶ {relpath: content}
claude/modules/workspace.md ┘             ▲                          │
existing AGENTS.md, settings.local.json ──┘ (read, to preserve)      ├─▶ apply_plan (render, new)
                                                                     └─▶ diff_plan  (check)
```

`render` and `check` are built on the same plan, so a render followed by a check cannot
disagree, and a second render is a no-op.

## Data Flow (session files)

```
.session/<id>.md ──parse──▶ frontmatter ─safe_load─▶ SessionHeader ─┐
                    └────▶ ## Ledger fence ─safe_load─▶ SessionLedger ┼─▶ lint rules ─▶ LintIssue[]
models.py ──export──▶ schemas/*.v1.schema.json ──▶ external consumers (shape/enums only)
```

## Component Specifications

| Component | Responsibility | Key Logic |
|:---|:---|:---|
| `scripts/setup-project.sh` | Scaffold a new project | Fetch base + modules, write `AGENTS.md`, create `.session/` |
| `scripts/refresh-dev-standards.sh` | Update a project's `AGENTS.md` and `.session/` scaffold | Split on `## Project-Specific`; legacy `claude.md` migration; templates fetched before any write, replaced if different; `index.md` / `archive/` created only if missing |
| `claude/` | Fragment library | `base.md`, `modules/*.md`, session and ADR templates |
| `dev_standards/main.py` | CLI entry point | Typer app; registers the `workspace` and `registry` sub-apps (`session-lint` / `session-schema` are separate console scripts) |
| `workspace/models.py` | Validate `workspace.yaml` | Pydantic; absolute `repos_root`, `graph.database` (default `neo4j`) vs. informational `graph.profile`, `allow_writes` needs `read_only: false`, repo dirs exist, pinned MCP version; `KNOWN_SERVERS` env/tool contract |
| `workspace/fragments.py` | Compose standards | Resolve `claude/` (option → `$DEV_STANDARDS_CLAUDE_DIR` → checkout); base + modules; workspace rules |
| `workspace/registry.py` | Repo descriptions | `<repo>_registry.yaml` then aggregate `registry.yaml`, field `purpose` |
| `workspace/render.py` | Desired-state engine | Pure plan; marker-region merge; `settings.json` / `settings.local.json` merges; `.session/` scaffold (templates owned, ADR index + archive create-only); plan → apply / diff |
| `workspace/cli.py` | `workspace new/render/check` | `new` validates first, then git init, render, commit |
| `registry/models.py` | Registry file schema | Pydantic `RepoEntry` (`repo`, `purpose` required); lenient list coercion; deterministic YAML |
| `registry/generate.py` | Produce one repo's registry file | Prompt on stdin to an LLM CLI run from an empty temp dir; validate before write; `generated_from` hash skips unchanged repos |
| `registry/hub.py` | Machine-local hub | One symlink per repo in `~/.repository_registry/`; generated `registry.yaml` rollup; conflict guards |
| `registry/cli.py` | `registry generate/add/refresh/rollup/check` | `refresh` continues past per-repo failures, exits 1 on any |
| `session_schema/models.py` | Session-file schema (source of truth) | Pydantic `SessionHeader` / `SessionLedger`; `extra="forbid"`; cross-field rules as model validators |
| `session_schema/parse.py` | Locate frontmatter + ledger | Fence-aware line scan (quoted examples ignored), then `yaml.safe_load`; `yaml.compose` for error line numbers |
| `session_schema/lint.py` | `validate_session` | Model errors + filename/id, ledger placement, status-vs-ledger rules, legacy warnings |
| `session_schema/export.py` | Published JSON Schemas | `model_json_schema()` + `$id` and a "necessary but not sufficient" description; drift-tested |
| `session_schema/cli.py` | `session-lint`, `session-schema export` | Separate console scripts; rich table plus a plain `SUMMARY` log line |

## Directory Structure

```
dev-standards/
├── dev_standards/
│   ├── main.py
│   ├── workspace/           # models, fragments, registry (consumer), render, cli
│   ├── registry/            # models, generate, hub, cli (the producer side)
│   └── session_schema/      # models, parse, lint, export, cli
├── schemas/                 # generated session JSON Schemas (committed, drift-tested)
├── claude/                  # fragment library (base, modules/, templates)
├── scripts/                 # setup-project.sh, refresh-dev-standards.sh
├── project-templates/       # pyproject / config / ARCHITECTURE / workspace.yaml templates
├── docs/
│   ├── usage_instructions.md
│   └── registry-schema.md
└── tests/                   # workspace, registry and session-schema tests; fixtures/sessions/
```
