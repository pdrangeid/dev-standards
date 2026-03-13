# dev-standards

Centralized Python project scaffolding and Claude Code collaboration standards
for the graph analytics ecosystem. Provides:

- **`setup-project.sh`** — scaffold a new Python project (repo, venv, structure, `claude.md`)
- **`refresh-claude.sh`** — pull updated standards into an existing project's `claude.md`
- **`claude/`** — modular `claude.md` content (base + project-type modules)
- **`project-templates/`** — reusable config and architecture stubs

---

## Recommended Setup (One-Time)

Clone this repo locally so you always have the scripts at hand:

```sh
git clone --depth 1 https://github.com/pdrangeid/dev-standards.git ~/dev-standards
chmod +x ~/dev-standards/scripts/setup-project.sh
```

Add aliases to `~/.bashrc` (or `~/.zshrc`) so the scripts auto-update before every run:

```sh
alias scaffold="git -C ~/dev-standards pull --quiet && ~/dev-standards/scripts/setup-project.sh"
alias refresh-claude="git -C ~/dev-standards pull --quiet && ~/dev-standards/scripts/refresh-claude.sh"
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

Each selected module is fetched from this repo and composed into the project's `claude.md`
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
├── claude.md                # Auto-generated: base + your selected modules + Project-Specific stub
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

After standards in this repo are updated, sync any project's `claude.md`:

```sh
cd ~/Projects/my-project
refresh-claude
```

Or for a project in a non-standard location:

```sh
refresh-claude --claude-md /path/to/claude.md
```

`refresh-claude.sh` reads the `<!-- AUTO-GENERATED: base + modules[...] -->` header
written by `setup-project.sh`, re-fetches those exact modules, and replaces
everything above `## Project-Specific` — leaving your project-specific notes untouched.

---

## Repository Structure

```
dev-standards/
├── scripts/
│   ├── setup-project.sh     # New project scaffolding
│   └── refresh-claude.sh    # Update auto-generated claude.md sections
├── claude/
│   ├── HEADER.md            # Auto-gen comment block template
│   ├── base.md              # Universal Python standards (always included)
│   └── modules/
│       ├── neo4j.md
│       ├── manifest-analyzer.md
│       ├── live-exporter.md
│       └── ast-analyzer.md
└── project-templates/
    ├── pyproject.toml.template
    ├── config.yaml.template
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
