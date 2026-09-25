# dev-standards

Centralized Python project scaffolding and Claude Code collaboration standards
for the graph analytics ecosystem. Provides:

- **`setup-project.sh`** — scaffold a new Python project (repo, venv, structure, `AGENTS.md`)
- **`refresh-dev-standards.sh`** — pull updated standards into an existing project's `AGENTS.md` (and self-migrate legacy `claude.md` projects on first run)
- **`claude/`** — modular `AGENTS.md` content (base + project-type modules)
- **`project-templates/`** — reusable config and architecture stubs

---

## Recommended Setup (One-Time)

Clone this repo locally so you always have the scripts at hand:

```sh
git clone --depth 1 https://github.com/pdrangeid/dev-standards.git ~/dev-standards
chmod +x ~/dev-standards/scripts/setup-project.sh
chmod +x ~/dev-standards/scripts/refresh-dev-standards.sh
```

Add aliases to `~/.bashrc` (or `~/.zshrc`) so the scripts auto-update before every run:

```sh
alias scaffold="git -C ~/dev-standards pull --quiet && ~/dev-standards/scripts/setup-project.sh"
alias refresh-standards="git -C ~/dev-standards pull --quiet && ~/dev-standards/scripts/refresh-dev-standards.sh"
```

Then reload:

```sh
source ~/.bashrc
```

---

## Scaffolding a New Project

```sh
scaffold <project-name> <package_name> <repo_url> ["Description"] [--modules <list>] [--feature <branch>] [--dry-run]
```

**Example — interactive module selection:**
```sh
scaffold datasource-graph-analyzer datasource_graph_analyzer \
    https://github.com/pdrangeid/datasource-graph-analyzer.git \
    "Analyze and export data warehouse metadata as a property graph."
```

**Example — non-interactive with modules pre-selected:**
```sh
scaffold my-project my_project https://github.com/pdrangeid/my-project.git \
    "Description here." --modules neo4j,manifest-analyzer
```

**Example — scaffold + create a feature branch:**
```sh
scaffold my-project my_project https://github.com/pdrangeid/my-project.git \
    --modules neo4j --feature schema-mapper
```

### Available Modules

When prompted (or via `--modules`), select which standards modules apply to your project:

| Module key | What it covers |
|:---|:---|
| `neo4j` | Cypher conventions, MERGE/ON CREATE patterns, node labels, relationship vocabulary |
| `manifest-analyzer` | Manifest-first philosophy, URI convention, UnresolvedAsset, TypeMapper, DataSampler |
| `live-exporter` | Strategic Exporter — driver management, amplifier payload, GraphSchema, Lesson logging |
| `ast-analyzer` | Codebase Graph Analyzer — two-pass parse, entity IDs, `has_label()`, `safe_primitive()` |
| `llm` | Two-pass LLM pipeline design, chunking discipline, config conventions for LLM calls |

Each selected module is fetched from this repo and composed into the project's `AGENTS.md`
alongside the universal `base.md` standards.

### What Gets Created

```
<project-name>/
├── pyproject.toml           # Python >= 3.11, black, ruff, pytest-cov configured
├── README.md
├── ARCHITECTURE.md          # Structured stub
├── .gitignore
├── .env.example
├── activate_env.sh          # Source to activate the uv venv
├── AGENTS.md                # Auto-generated: base + your selected modules + Project-Specific stub
├── CLAUDE.md                # Bridge stub — `@AGENTS.md` import + Claude Code section
├── config/
│   └── config.yaml
├── docs/
│   └── usage_instructions.md
├── <package_name>/
│   ├── __init__.py
│   └── main.py              # typer app + rich console + --debug flag
├── output/
│   └── .gitkeep             # gitignored output dir, tracked stub
└── tests/
    └── __init__.py
```

A virtual environment is created at `~/python-venvs/<package_name>_env` and dev
dependencies are installed in editable mode.

---

## Refreshing Standards in an Existing Project

After standards in this repo are updated, sync any project's `AGENTS.md`:

```sh
cd ~/Projects/my-project
refresh-standards
```

Or for a project in a non-standard location:

```sh
refresh-standards --agents-md /path/to/AGENTS.md
```

`refresh-dev-standards.sh` reads the `<!-- AUTO-GENERATED: base + modules[...] -->` header
written by `setup-project.sh`, re-fetches those exact modules, and replaces
everything above `## Project-Specific` — leaving your project-specific notes untouched.

### Migrating an Older Project (`claude.md` → `AGENTS.md`)

Projects scaffolded before this repo switched to `AGENTS.md` still have a `claude.md`.
Running `refresh-dev-standards.sh` against one of these projects detects the legacy
file automatically and migrates it in place — no separate command needed:

```sh
cd ~/Projects/my-older-project
refresh-standards
```

This converts `claude.md` → `AGENTS.md` (preserving `## Project-Specific` byte-for-byte)
and creates a `CLAUDE.md` bridge stub for Claude Code, without touching any hand-authored
content already in `CLAUDE.md`. The migration only runs once — subsequent runs take the
normal refresh path.

---

## Multi-Repo Workspaces

A **workspace** is a git-initialized folder (no remote needed) that lets one Claude Code
session work across several repos with shared graph access and one session protocol. It is
generated from a single `workspace.yaml`; nothing else is hand-maintained.

```sh
# Preferred
uv run dev-standards workspace new ~/workspaces/my-effort --from workspace.yaml
uv run dev-standards workspace render ~/workspaces/my-effort
uv run dev-standards workspace check ~/workspaces/my-effort

# Fallback (venv activated)
dev-standards workspace check ~/workspaces/my-effort
```

The commands need a dev-standards checkout installed editable
(`uv pip install -e .[dev]`) because the workspace `AGENTS.md` is composed from the local
`claude/` fragments. Point elsewhere with `--fragments-dir` or `DEV_STANDARDS_CLAUDE_DIR`.

### Creating a workspace

1. Copy [project-templates/workspace.yaml.template](project-templates/workspace.yaml.template)
   somewhere and edit it: `repos_root` (absolute, no `~`), the `repos` list, `graph.database`,
   and the MCP server.
2. `dev-standards workspace new <path> --from workspace.yaml` validates the yaml (every repo
   directory must exist), then creates the folder, runs `git init`, renders everything, copies
   `.session/_template.md`, and makes the first commit (`--no-commit` to skip it).
3. Copy `.env.example` to `.env` and fill in the Neo4j credentials. `.env` is gitignored.
4. Start Claude Code in the workspace folder. `.mcp.json` launches the pinned Neo4j MCP server
   with `NEO4J_MCP_READ_ONLY=true`, and `.claude/settings.json` denies its `write-cypher` tool.

### Adding a repo

Edit `workspace.yaml` (add an entry under `repos:`), then run `dev-standards workspace render`.
The repo map in `AGENTS.md` and `permissions.additionalDirectories` in
`.claude/settings.local.json` update; nothing else needs touching. `check` exits non-zero
when the rendered files have drifted from the yaml, so it is safe to run in CI or by hand.

### What is safe to hand-edit

| File | Ownership | Hand-editing |
|---|---|---|
| `workspace.yaml` | You (source of truth, committed) | Yes — then `render` |
| `AGENTS.md` | Marker regions generated; rest is yours | Only **outside** `<!-- BEGIN/END GENERATED: name -->` regions (e.g. `## Notes`); edits inside regions are overwritten |
| `CLAUDE.md`, `.mcp.json`, `.claude/settings.json`, `.env.example` | Fully generated, overwritten every render | No |
| `.claude/settings.local.json` | Merged (gitignored, machine-specific) | Yes — only `permissions.additionalDirectories` is replaced; other keys survive |
| `.gitignore` | Required lines appended if missing | Yes — nothing is removed |
| `.session/*` | Yours after creation | Yes — render never touches it |
| `.env` | Yours (gitignored, holds credentials) | Yes |

`AGENTS.md` uses these regions: `header`, `standards` (base + selected modules, from `claude/`),
`workspace-rules` (from `claude/modules/workspace.md`), and `repo-map`. Each repo's
`role` in the map comes from its registry YAML `purpose` (when `registry_dir` is set), else
the `role` field in `workspace.yaml`. If a region's markers are damaged, `render` refuses to
write rather than guess. Do not run `refresh-dev-standards.sh` on a workspace — it manages
project `AGENTS.md` files, and a workspace is refreshed with `render`.

`.mcp.json` embeds the absolute workspace path (for `--env-file`), so it changes when the
workspace is re-rendered on another machine — commit the result or leave it, as you prefer.

---

## Repo Registry

Each repo describes itself in a small git-tracked file, `<repo_with_underscores>_registry.yaml`,
at its root (`purpose`, `interfaces`, `contracts`, `integration_points`, `model_prefs`). A
machine-local **hub**, `~/.repository_registry/`, holds one symlink per repo plus a generated
rollup, so every repo's registry is discoverable from one place without moving the file out of
that repo's git history. The workspace repo-map reads `purpose` from it. The full schema is in
[docs/registry-schema.md](docs/registry-schema.md).

```sh
# Preferred
uv run dev-standards registry add ~/develop/my-repo      # generate its file, link it, rebuild rollup
uv run dev-standards registry generate ~/develop/my-repo # regenerate one repo's file on demand
uv run dev-standards registry refresh                    # regenerate every linked repo, then the rollup
uv run dev-standards registry check                      # validate the hub; exit 1 on problems

# Fallback (venv activated)
dev-standards registry refresh --debug
```

Point a workspace at the hub with `registry_dir: /home/YOUR_USERNAME/.repository_registry` in
`workspace.yaml` (absolute path; `~` is rejected on purpose).

Ad hoc tools that want the whole ecosystem at once (for example a Mermaid flowchart script)
should read the hub's generated `~/.repository_registry/registry.yaml` instead of a hand-appended file.

### How generation works

- **An LLM describes the repo; it never edits files.** `generate` sends the repo's `README.md`,
  `ARCHITECTURE.md`, `AGENTS.md` (or legacy `claude.md`), `pyproject.toml` and
  `docs/usage_instructions.md` to an LLM command on stdin, validates the reply against the schema,
  and only then writes. A failed or malformed reply never touches an existing file.
- **Overwrite, never append.** Re-running replaces the repo's single file.
- **No-op when nothing changed.** The file records `generated_from`, a hash of the source docs and
  the prompt version. If it still matches, the LLM is not called and nothing is written, so
  `refresh` is cheap and a second run produces no diff. `--force` regenerates anyway. A hand edit
  survives until one of the source docs changes.
- **LLM command.** Default `claude -p`. Override with `--llm-cmd` or
  `$DEV_STANDARDS_REGISTRY_LLM_CMD` — any CLI that reads a prompt on stdin and prints the answer,
  e.g. `gemini --skip-trust -p "Respond to the request above."`. It runs from an empty temp
  directory, never from the repo, so repo-local tool config is not loaded.
- **Hub location.** `~/.repository_registry/`, or `--hub` / `$DEV_STANDARDS_REGISTRY_HUB`. The hub
  is machine-local and never git-tracked; `registry add` is how a repo joins it, and the linked
  repos are what `refresh` iterates.

### Cadence

**Weekly `dev-standards registry refresh` is the source of truth**; `generate` / `add` are
available on demand but nothing requires running them at session close. Because unchanged repos
are skipped without an LLM call, a weekly run only pays for repos whose docs changed. `refresh`
keeps going if one repo fails, reports the failures, and exits 1 so a scheduler can alert.

This repo documents the schedule but does not install it. When you schedule it, run it under the
`run_uv_script.sh` wrapper so its log carries the `>>> Executing` / `<<< Finished rc=` markers the
Logging Contract requires; `refresh` emits the plain `SUMMARY action=refresh ...` line that
contract asks for alongside its console output.

---

## Session Files and `session-lint`

Every `.session/YYYY-MM-DD-topic.md` file carries YAML frontmatter (`schema_version: 1`, `id`,
`title`, `status`, `created`, `repos`, `branch`, `links`) and one `## Ledger` section holding a
single ` ```yaml session-ledger ` block: `runs`, `outcome`, `decisions`, `questions`,
`findings`, `checks`, `debt`, `blockers`, `produced`. The template is
[claude/session-template.md](claude/session-template.md); the rules (item IDs, qualified
cross-file refs, links pointing backward in time) are in `claude/base.md` under
Session Management, and the rationale is
[ADR-0001](.session/specs/adr/0001-governed-graph-extractable-session-files.md).

```sh
# From any repo (preferred) — exit 1 on any error
uvx --from git+https://github.com/pdrangeid/dev-standards@develop session-lint .session/

# No GitHub access: a local checkout
uvx --from ~/develop/dev-standards session-lint .session/

# Inside this repo
uv run session-lint .session/ --strict --format json
uv run session-schema export --out schemas/   # regenerate the JSON Schemas after a model change
```

- A directory is linted recursively (`*.md`), skipping `_template.md`, `specs/` and `archive/`.
- Files with no frontmatter are **legacy**: reported as `info`, or as errors with `--strict`.
- Warnings (a leftover `Status:` line, the old "Decisions Made This Session" heading, `active`
  with no runs) never fail the run.
- The Pydantic models in `dev_standards/session_schema/models.py` are the source of truth.
  `schemas/session-header.v1.schema.json` and `schemas/session-ledger.v1.schema.json` are
  generated from them and committed; a test fails if they drift. External consumers (e.g.
  `codebase-graph-analyzer`) validate against those files, but the JSON Schema captures shape
  and enums only — cross-field rules are enforced by `session-lint` alone.

---

## Repository Structure

```
dev-standards/
├── dev_standards/
│   ├── main.py              # typer app; `workspace` and `registry` sub-apps are registered here
│   ├── workspace/           # `dev-standards workspace` new / render / check
│   ├── registry/            # `dev-standards registry` generate / add / refresh / rollup / check
│   └── session_schema/      # `session-lint` and `session-schema export`
├── schemas/                 # generated session-{header,ledger}.v1.schema.json (committed)
├── docs/
│   └── registry-schema.md   # the registry file contract
├── scripts/
│   ├── setup-project.sh          # New project scaffolding
│   └── refresh-dev-standards.sh  # Update auto-generated AGENTS.md sections (+ claude.md migration)
├── claude/
│   ├── HEADER.md            # Auto-gen comment block template
│   ├── base.md              # Universal Python standards (always included)
│   ├── session-template.md  # Copied to .session/_template.md in new projects
│   ├── adr-template.md      # Copied to .session/specs/adr/_template.md in new projects
│   ├── adr-index-template.md # Copied to .session/specs/adr/index.md in new projects
│   └── modules/
│       ├── neo4j.md
│       ├── manifest-analyzer.md
│       ├── live-exporter.md
│       ├── ast-analyzer.md
│       ├── llm.md
│       └── workspace.md     # Workspace rules; rendered by `dev-standards workspace`, not in the setup menu
└── project-templates/
    ├── pyproject.toml.template
    ├── config.yaml.template
    ├── workspace.yaml.template
    └── ARCHITECTURE.md.template
```

---

## One-Off Use (No Local Clone)

If you just want to scaffold once without cloning:

```sh
curl -fsSL https://raw.githubusercontent.com/pdrangeid/dev-standards/main/scripts/setup-project.sh \
    -o /tmp/setup-project.sh
# Inspect it first:
# cat /tmp/setup-project.sh
bash /tmp/setup-project.sh my-project my_project \
    https://github.com/pdrangeid/my-project.git "Description here."
```

---

## License

MIT
