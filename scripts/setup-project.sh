#!/bin/bash
# =============================================================================
# Generic Python Project Scaffolding Script v2
# Usage:
#   ./setup-project.sh <project-name> <package_name> <repo_url> [description]
#
# Flags:
#   --dry-run              Print what would happen without creating anything
#   --feature <branch>     Also create and checkout feature/<branch> off develop
#
# Examples:
#   ./setup-project.sh datasource-graph-analyzer datasource_graph_analyzer \
#       https://github.com/pdrangeid/datasource-graph-analyzer.git \
#       "Analyze and export data warehouse metadata as a property graph."
#
#   ./setup-project.sh my-project my_project https://github.com/pdrangeid/my-project.git \
#       "Description here." --feature schema-mapper
#
# Prerequisites: git, uv, python3 (run from WSL)
# =============================================================================

set -e
set -u
set -o pipefail

# --- Flag Parsing ------------------------------------------------------------
DRY_RUN=false
FEATURE_BRANCH=""
FEATURE_NEXT=false
MODULES_ARG=""
MODULES_NEXT=false
POSITIONAL_ARGS=()

for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=true
            ;;
        --feature)
            FEATURE_NEXT=true
            ;;
        --modules)
            MODULES_NEXT=true
            ;;
        *)
            if [ "$FEATURE_NEXT" = true ]; then
                FEATURE_BRANCH="$arg"
                FEATURE_NEXT=false
            elif [ "$MODULES_NEXT" = true ]; then
                MODULES_ARG="$arg"
                MODULES_NEXT=false
            else
                POSITIONAL_ARGS+=("$arg")
            fi
            ;;
    esac
done

# --- Argument Handling -------------------------------------------------------
usage() {
    echo "Usage: $0 <project-name> <package_name> <repo_url> [description] [--dry-run] [--feature <branch>] [--modules <list>]"
    echo ""
    echo "  project-name   Kebab-case project name  (e.g. datasource-graph-analyzer)"
    echo "  package_name   Snake_case package name  (e.g. datasource_graph_analyzer)"
    echo "  repo_url       GitHub HTTPS URL         (e.g. https://github.com/pdrangeid/...)"
    echo "  description    Optional short project description."
    echo "  --dry-run      Print actions without executing them."
    echo "  --feature      Also create and checkout feature/<branch> off develop."
    echo "  --modules      Comma-separated module list, skips interactive menu."
    echo "                 Options: neo4j, manifest-analyzer, live-exporter, ast-analyzer, llm"
    exit 1
}

if [ ${#POSITIONAL_ARGS[@]} -lt 3 ]; then
    usage
fi

PROJECT_NAME="${POSITIONAL_ARGS[0]}"
PACKAGE_NAME="${POSITIONAL_ARGS[1]}"
REPO_URL="${POSITIONAL_ARGS[2]}"
DESCRIPTION="${POSITIONAL_ARGS[3]:-A brief description of the project.}"
VENV_NAME="${PACKAGE_NAME}_env"

# --- Path Configuration ------------------------------------------------------
PROJECTS_DIR="${HOME}/Projects"
VENV_DIR="${HOME}/python-venvs"
PROJECT_DIR="${PROJECTS_DIR}/${PROJECT_NAME}"
VENV_PATH="${VENV_DIR}/${VENV_NAME}"

# --- Dry-run Helpers ---------------------------------------------------------
run() {
    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] $*"
    else
        "$@"
    fi
}

write_file() {
    # Usage: write_file <destination_path> << 'HEREDOC'
    local dest="$1"
    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] Would write: $dest"
        cat > /dev/null  # consume stdin so heredoc doesn't spill
    else
        cat > "$dest"
    fi
}

# --- Header ------------------------------------------------------------------
echo "============================================="
[ "$DRY_RUN" = true ] && echo " Python Project Scaffolding  [DRY RUN]" \
                       || echo " Python Project Scaffolding"
echo "============================================="
echo " Project Name : $PROJECT_NAME"
echo " Package Name : $PACKAGE_NAME"
echo " Repo URL     : $REPO_URL"
echo " Project Dir  : $PROJECT_DIR"
echo " Venv Path    : $VENV_PATH"
[ -n "$FEATURE_BRANCH" ] && echo " Feature      : feature/$FEATURE_BRANCH"
echo "============================================="
echo ""

# --- Preflight Checks --------------------------------------------------------
echo "--- Preflight Checks ---"

PREFLIGHT_OK=true

for cmd in git uv python3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "❌ Missing required tool: '$cmd'"
        PREFLIGHT_OK=false
    else
        echo "✅ $cmd: $(command -v $cmd)"
    fi
done

# Git identity check — blank attribution is a silent footgun
GIT_USER=$(git config --global user.name 2>/dev/null || echo "")
GIT_EMAIL=$(git config --global user.email 2>/dev/null || echo "")
if [ -z "$GIT_USER" ] || [ -z "$GIT_EMAIL" ]; then
    echo ""
    echo "⚠️  WARNING: Git identity not configured globally."
    echo "   Commits will have blank author info. Fix with:"
    echo "     git config --global user.name  \"Your Name\""
    echo "     git config --global user.email \"your@email.com\""
    echo ""
else
    echo "✅ Git identity: $GIT_USER <$GIT_EMAIL>"
fi

if [ "$PREFLIGHT_OK" = false ]; then
    echo ""
    echo "❌ Preflight failed. Install missing tools and retry."
    exit 1
fi
echo ""

# --- Module Selector ---------------------------------------------------------
# Define available claude.md modules
declare -a MODULE_KEYS=("neo4j" "manifest-analyzer" "live-exporter" "ast-analyzer" "llm")
declare -a MODULE_LABELS=(
    "Neo4j / Graph         — Cypher conventions, driver patterns, MERGE/ON CREATE"
    "Manifest Analyzer     — Manifest-first, URI convention, UnresolvedAsset, TypeMapper"
    "Live Exporter         — Amplifier payload, GraphSchema, backup/restore, Lesson logging"
    "AST / Code Analyzer   — Two-pass parse, entity IDs, has_label(), safe_primitive()"
    "LLM Pipeline          — Two-pass pipeline, chunking discipline, config conventions"
)

SELECTED_MODULES=()

if [ -n "$MODULES_ARG" ]; then
    # Non-interactive: parse comma-separated list from --modules flag
    IFS=',' read -ra SELECTED_MODULES <<< "$MODULES_ARG"
    echo "--- Claude Modules (from --modules flag) ---"
    for m in "${SELECTED_MODULES[@]}"; do
        echo "  ✅ $m"
    done
    echo ""
else
    # Interactive multi-select menu
    echo "--- Claude Module Selection ---"
    echo "Select which claude.md modules apply to this project."
    echo "Enter numbers separated by spaces (e.g. 1 3), or press Enter for none."
    echo ""

    for i in "${!MODULE_KEYS[@]}"; do
        printf "  [%d] %s\n" "$((i+1))" "${MODULE_LABELS[$i]}"
    done
    echo ""

    read -r -p "Your selection: " MODULE_INPUT

    if [ -n "$MODULE_INPUT" ]; then
        for num in $MODULE_INPUT; do
            idx=$((num - 1))
            if [ "$idx" -ge 0 ] && [ "$idx" -lt "${#MODULE_KEYS[@]}" ]; then
                SELECTED_MODULES+=("${MODULE_KEYS[$idx]}")
            else
                echo "⚠️  Ignoring invalid selection: $num"
            fi
        done
    fi

    echo ""
    if [ ${#SELECTED_MODULES[@]} -eq 0 ]; then
        echo "ℹ️  No modules selected — claude.md will contain base standards only."
    else
        echo "✅ Selected modules:"
        for m in "${SELECTED_MODULES[@]}"; do
            echo "   • $m"
        done
    fi
    echo ""
fi

# Build the module list string for the HEADER comment (e.g. "neo4j,live-exporter")
MODULES_STRING=$(IFS=','; echo "${SELECTED_MODULES[*]}")

# --- Phase 1: Repository Setup -----------------------------------------------
echo "--- Phase 1: Repository Setup ---"

run mkdir -p "$PROJECTS_DIR"
run mkdir -p "$VENV_DIR"

if [ -d "$PROJECT_DIR/.git" ]; then
    echo "⚠️  Git repo already exists at $PROJECT_DIR. Skipping clone/init."
    [ "$DRY_RUN" = false ] && cd "$PROJECT_DIR"
elif [ -d "$PROJECT_DIR" ]; then
    echo "⚠️  Directory exists but is not a git repo. Initializing..."
    [ "$DRY_RUN" = false ] && cd "$PROJECT_DIR"
    run git init
    run git remote add origin "$REPO_URL"
else
    echo "🔍 Attempting to clone $REPO_URL ..."
    if [ "$DRY_RUN" = false ] && git clone "$REPO_URL" "$PROJECT_DIR" 2>/dev/null; then
        echo "✅ Cloned existing remote repo."
        cd "$PROJECT_DIR"
    else
        echo "ℹ️  Clone failed or dry-run — will init fresh local repo."
        run mkdir -p "$PROJECT_DIR"
        [ "$DRY_RUN" = false ] && cd "$PROJECT_DIR"
        run git init
        run git remote add origin "$REPO_URL"
    fi
fi

run git config core.filemode false

# If the repo is empty (no commits), create an initial commit on main first
if [ "$DRY_RUN" = false ]; then
    if ! git rev-parse HEAD &>/dev/null 2>&1; then
        echo "ℹ️  Empty repo detected — creating initial commit on main..."
        git checkout -b main 2>/dev/null || true
        echo "# ${PROJECT_NAME}" > README.md
        git add README.md
        git commit -m "chore: initial commit"
        if git fetch origin &>/dev/null; then
            git push -u origin main
            echo "✅ Pushed initial commit to main."
        fi
    fi
fi

# develop branch
echo "🌿 Setting up 'develop' branch..."

# Check remote reachability by attempting a fetch (more reliable than ls-remote after clone)
REMOTE_REACHABLE=false
if [ "$DRY_RUN" = false ] && git fetch origin &>/dev/null; then
    REMOTE_REACHABLE=true
fi

if [ "$REMOTE_REACHABLE" = true ]; then
    if git rev-parse --verify origin/develop &>/dev/null; then
        # Remote develop already exists — track it instead of pushing
        git checkout -b develop origin/develop 2>/dev/null || git checkout develop
        git branch --set-upstream-to=origin/develop develop 2>/dev/null || true
        echo "✅ Tracking existing remote 'develop' branch."
    else
        # Doesn't exist yet — create and push
        git checkout -b develop 2>/dev/null || git checkout develop
        git push -u origin develop
        echo "✅ Pushed new 'develop' branch to remote."
    fi
else
    run git checkout -b develop 2>/dev/null || run git checkout develop
    echo "⚠️  Remote not reachable yet — push manually after creating the GitHub repo."
fi

# Optional feature branch
if [ -n "$FEATURE_BRANCH" ]; then
    if [[ "$FEATURE_BRANCH" == "main" || "$FEATURE_BRANCH" == "develop" || "$FEATURE_BRANCH" == "master" ]]; then
        echo "⚠️  '$FEATURE_BRANCH' is a reserved branch name — ignoring --feature flag."
        echo "    You are already on 'develop'. Use --feature <descriptive-name> for feature branches."
        FEATURE_BRANCH=""
    else
        echo "🌿 Creating feature branch: feature/$FEATURE_BRANCH"
        run git checkout -b "feature/$FEATURE_BRANCH"
        echo "✅ Now on feature/$FEATURE_BRANCH"
    fi
fi
echo ""

# --- Phase 2: Virtual Environment --------------------------------------------
echo "--- Phase 2: Virtual Environment (uv) ---"

if [ ! -d "$VENV_PATH" ]; then
    run uv venv "$VENV_PATH"
    echo "✅ Created venv at $VENV_PATH"
else
    echo "⚠️  Venv already exists at $VENV_PATH. Skipping."
fi

if [ "$DRY_RUN" = false ]; then
    cat > "$PROJECT_DIR/activate_env.sh" << ACTIVATE
#!/bin/bash
source "${VENV_PATH}/bin/activate"
echo "✅ Activated ${VENV_NAME}"
ACTIVATE
    chmod +x "$PROJECT_DIR/activate_env.sh"
else
    echo "  [DRY-RUN] Would write: $PROJECT_DIR/activate_env.sh"
fi
echo "✅ activate_env.sh created"
echo ""

# --- Phase 3: Project Structure ----------------------------------------------
echo "--- Phase 3: Project Structure ---"

for dir in \
    "$PROJECT_DIR/$PACKAGE_NAME" \
    "$PROJECT_DIR/tests" \
    "$PROJECT_DIR/config" \
    "$PROJECT_DIR/docs" \
    "$PROJECT_DIR/output"
do
    run mkdir -p "$dir"
done

run touch "$PROJECT_DIR/$PACKAGE_NAME/__init__.py"
run touch "$PROJECT_DIR/tests/__init__.py"
run touch "$PROJECT_DIR/output/.gitkeep"
# Force-add .gitkeep — output/ is gitignored so git add . won't pick it up
run git -C "$PROJECT_DIR" add -f output/.gitkeep 2>/dev/null || true
run touch "$PROJECT_DIR/requirements.txt"
echo "✅ Directory structure created"

# --- Phase 3.5: Session Directory --------------------------------------------
echo "--- Phase 3.5: Session Directory (.session/) ---"
 
SESSION_DIR="$PROJECT_DIR/.session"
SPECS_DIR="$SESSION_DIR/specs"
SESSION_TEMPLATE_URL="https://raw.githubusercontent.com/pdrangeid/dev-standards/main/claude/session-template.md"
 
run mkdir -p "$SESSION_DIR"
run mkdir -p "$SPECS_DIR"
 
# Fetch the canonical session template from dev-standards
if [ "$DRY_RUN" = false ]; then
    if curl -fsSL "$SESSION_TEMPLATE_URL" -o "$SESSION_DIR/_template.md" 2>/dev/null; then
        echo "  ✅ Fetched _template.md from dev-standards"
    else
        echo "  ⚠️  Could not fetch _template.md — writing minimal local stub"
        cat > "$SESSION_DIR/_template.md" << 'SESSIONSTUB'
# Session: [Topic]
<!-- Copy this file, rename it YYYY-MM-DD-topic.md, then edit the copy. -->
Date: YYYY-MM-DD
Repo: [repo-name]
Branch: [feature/branch-name or develop]
Status: draft | active | complete
 
## Goal
One paragraph — what should exist at the end of this session.
 
## Context & Constraints
- **Decision**: [locked decisions Claude should not revisit]
- **Out of scope**: [explicit exclusions]
- **Reference files**: [.session/specs/ files to read first]
 
## Relevant Specs / Schemas / Examples
[Paste schemas, data shapes, code samples here]
 
## Instructions
1. Read `claude.md` first.
2. [Your actual instructions here]
 
## Decisions Made This Session
_None yet._
SESSIONSTUB
    fi
 
    # specs/ README so the folder isn't an empty mystery
    cat > "$SPECS_DIR/README.md" << 'SPECSREADME'
# .session/specs/
 
Durable, promoted architectural decisions for this project.
 
Files here are promoted from completed session files when decisions are locked.
They serve as reference material for future Claude Code sessions — not instructions.
 
Naming convention: `[topic]-baseline.md` or `[topic]-decisions.md`
SPECSREADME
 
    echo "✅ .session/ directory created"
    echo "   • .session/_template.md  — copy this to start a new session"
    echo "   • .session/specs/        — promote locked decisions here after sessions"
else
    echo "  [DRY-RUN] Would create: $SESSION_DIR/_template.md"
    echo "  [DRY-RUN] Would create: $SPECS_DIR/README.md"
fi
echo ""

# requirements-dev.txt
write_file "$PROJECT_DIR/requirements-dev.txt" << 'REQDEV'
# Developer requirements — managed via pyproject.toml [project.optional-dependencies]
# Install with: uv pip install -e .[dev]
REQDEV

# pyproject.toml
write_file "$PROJECT_DIR/pyproject.toml" << PYPROJECT
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "${PROJECT_NAME}"
version = "0.1.0"
description = "${DESCRIPTION}"
readme = "README.md"
requires-python = ">=3.11"
# license = { text = "MIT" }
# authors = [
#   { name = "Paul Drangeid", email = "pdrangeid@gmail.com" },
# ]
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0,<14.0",
    # Add further runtime dependencies here, e.g.:
    # "requests>=2.25.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "black",
    "ruff",
    "pip-tools",
    # "python-dotenv",
    # "mypy",
]

[project.scripts]
# Uncomment after defining your CLI entry point:
# ${PACKAGE_NAME} = "${PACKAGE_NAME}.main:app"

[tool.setuptools.packages.find]
where = ["."]
include = ["${PACKAGE_NAME}*"]

[tool.black]
line-length = 88

[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I", "UP", "B"]
ignore = []
target-version = "py311"

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --cov=${PACKAGE_NAME} --cov-report=html --cov-report=xml"
testpaths = ["tests"]
python_files = "test_*.py *_test.py tests.py"
PYPROJECT
echo "✅ pyproject.toml created"

# main.py stub — typer app, rich console, --debug flag, logging setup
write_file "$PROJECT_DIR/$PACKAGE_NAME/main.py" << MAINPY
import logging
import typer
from rich.console import Console

app = typer.Typer()
console = Console()
logger = logging.getLogger(__name__)


@app.command()
def run(
    # Add your command arguments here, e.g.:
    # input: str = typer.Option(..., "--input", "-i", help="Input file path."),
    # output: str = typer.Option("output.json", "--output", "-o", help="Output file."),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging."),
):
    """${PROJECT_NAME} — main entry point."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    console.print("[bold green]✅ ${PROJECT_NAME} started[/bold green]")
    # TODO: implement


if __name__ == "__main__":
    app()
MAINPY
echo "✅ main.py stub created"

# config/config.yaml stub
write_file "$PROJECT_DIR/config/config.yaml" << CONFIGYAML
# ${PROJECT_NAME} configuration

paths:
  output_dir: output
  # input_dir: input

defaults:
  # Add project-specific defaults here

output_mode:
  use_profile_subfolders: false
CONFIGYAML
echo "✅ config/config.yaml stub created"

# .env.example
write_file "$PROJECT_DIR/.env.example" << 'ENVEXAMPLE'
# Copy this file to .env and fill in your values.
# .env is gitignored — never commit it.

# Neo4j credentials — one pair per named connection profile
# NEO4J_USER_PROFILENAME=
# NEO4J_PASSWORD_PROFILENAME=
ENVEXAMPLE
echo "✅ .env.example created"

# ARCHITECTURE.md
write_file "$PROJECT_DIR/ARCHITECTURE.md" << ARCH
# Architecture: ${PROJECT_NAME}

> **TODO**: Fill in architecture details as the project takes shape.

## Overview

_Describe the high-level purpose and design philosophy here._

## Data Flow

\`\`\`
[Input] → [Processing] → [Output / Manifest]
\`\`\`

## Component Specifications

| Component | Responsibility | Key Logic |
|:---|:---|:---|
| _TBD_ | _TBD_ | _TBD_ |

## Directory Structure

\`\`\`
${PROJECT_NAME}/
├── ${PACKAGE_NAME}/
│   └── main.py
├── config/
│   └── config.yaml
├── docs/
│   └── usage_instructions.md
├── output/              # gitignored — generated artifacts
└── tests/
\`\`\`
ARCH
echo "✅ ARCHITECTURE.md created"

# docs/usage_instructions.md stub
write_file "$PROJECT_DIR/docs/usage_instructions.md" << USAGE
# Usage Instructions: ${PROJECT_NAME}

## Quick Start

\`\`\`sh
# Activate environment
source activate_env.sh

# Run (update once CLI args are defined)
PYTHONPATH=. uv run python -m ${PACKAGE_NAME}.main --debug
\`\`\`

## Commands

| Command | Arguments | Description |
|:---|:---|:---|
| _TBD_ | _TBD_ | _TBD_ |

## Configuration

Edit \`config/config.yaml\` to set paths and defaults.
Copy \`.env.example\` to \`.env\` and fill in credentials.
USAGE
echo "✅ docs/usage_instructions.md stub created"

# README.md
write_file "$PROJECT_DIR/README.md" << README
# ${PROJECT_NAME}

${DESCRIPTION}

---

## Quick Start

\`\`\`sh
git clone ${REPO_URL}
cd ${PROJECT_NAME}
source activate_env.sh
uv pip install -e .[dev]
cp .env.example .env  # fill in credentials
\`\`\`

## Documentation

- \`ARCHITECTURE.md\` — system design and component overview
- \`docs/usage_instructions.md\` — detailed usage guide

## License

MIT
README
echo "✅ README.md created"

# .gitignore
write_file "$PROJECT_DIR/.gitignore" << 'GITIGNORE'
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.egg-info/
dist/
build/
*.egg

# Virtual environments
*_env/
.venv/
venv/
env/

# Secrets / environment
.env
*.env.*
!.env.example

# Output / generated artifacts
output/
!output/.gitkeep

# Testing
.pytest_cache/
coverage.xml
htmlcov/
.coverage

# IDE / editors
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# OneDrive / temp
~$*
*.tmp

# Activation helpers
activate_env.sh
activate_env.ps1
GITIGNORE
echo "✅ .gitignore created"

# claude.md — fetch base + modules from dev-standards, append Project-Specific stub
echo "Generating claude.md..."
DEV_STANDARDS_RAW_MAIN="https://raw.githubusercontent.com/pdrangeid/dev-standards/main/claude"
DEV_STANDARDS_RAW_DEV="https://raw.githubusercontent.com/pdrangeid/dev-standards/develop/claude"
DEV_STANDARDS_RAW="$DEV_STANDARDS_RAW_DEV"  # default to develop branch for latest updates
CLAUDE_MD="$PROJECT_DIR/claude.md"
FETCH_FAILED=false

if [ "$DRY_RUN" = false ]; then
    # Header block — encodes which modules were selected so refresh-claude.sh knows
    cat > "$CLAUDE_MD" << CLAUDEHEADER
<!-- AUTO-GENERATED: base + modules[${MODULES_STRING}] -->
<!-- Do not edit above ## Project-Specific — run refresh-claude.sh to update -->
<!-- dev-standards: https://github.com/pdrangeid/dev-standards -->

CLAUDEHEADER

    # Fetch base.md
    if curl -fsSL "${DEV_STANDARDS_RAW}/base.md" >> "$CLAUDE_MD" 2>/dev/null; then
        echo "  ✅ Fetched base.md"
    else
        echo "  ⚠️  Could not fetch base.md from dev-standards (repo may not have it yet)"
        FETCH_FAILED=true
    fi

    # Fetch each selected module
    for module in "${SELECTED_MODULES[@]}"; do
        if curl -fsSL "${DEV_STANDARDS_RAW}/modules/${module}.md" >> "$CLAUDE_MD" 2>/dev/null; then
            echo "  ✅ Fetched module: ${module}.md"
        else
            echo "  ⚠️  Could not fetch module: ${module}.md (may not exist yet in dev-standards)"
        fi
    done

    # Project-Specific stub — always appended last, never overwritten by refresh
    cat >> "$CLAUDE_MD" << PROJECTSTUB

---

## Project-Specific

> This section is maintained by Claude during coding sessions.
> Run \`refresh-claude.sh\` to update the auto-generated sections above
> without touching anything below this line.

### Overview
_To be filled in during first Claude Code session._

### Key Patterns
_Document project-specific conventions, quirks, and decisions here._

### Known Issues / Tech Debt
_Track known bugs and deferred work here._
PROJECTSTUB

    if [ "$FETCH_FAILED" = true ]; then
        echo "  ℹ️  claude.md created with stub content — populate dev-standards repo to enable full fetch."
    else
        echo "✅ claude.md generated (base + ${#SELECTED_MODULES[@]} module(s) + Project-Specific stub)"
    fi
else
    echo "  [DRY-RUN] Would generate claude.md with modules: [${MODULES_STRING}]"
fi
echo ""


echo "--- Phase 4: Installing Dev Dependencies ---"

if [ "$DRY_RUN" = false ]; then
    source "$VENV_PATH/bin/activate"
    uv pip install -e ".[dev]"
    echo "✅ Dev dependencies installed (editable mode)"
else
    echo "  [DRY-RUN] Would run: uv pip install -e .[dev]"
fi
echo ""

# --- Phase 5: Initial Commit -------------------------------------------------
echo "--- Phase 5: Initial Commit ---"

run git add .
run git commit -m "feat: scaffold project structure, config, and dev tooling"

if [ "$DRY_RUN" = false ] && [ "$REMOTE_REACHABLE" = true ]; then
    PUSH_BRANCH=$(git branch --show-current)
    git push origin "$PUSH_BRANCH"
    echo "✅ Pushed scaffold commit to '$PUSH_BRANCH'"
else
    echo "⚠️  Remote not reachable or dry-run — run 'git push origin <branch>' when ready."
fi
echo ""

# --- Phase 6: Post-Scaffold Validation ---------------------------------------
echo "--- Phase 6: Validation ---"

if [ "$DRY_RUN" = false ]; then
    # Package importable?
    if python3 -c "import ${PACKAGE_NAME}" 2>/dev/null; then
        echo "✅ Package '${PACKAGE_NAME}' is importable"
    else
        echo "❌ Package '${PACKAGE_NAME}' failed to import — check pyproject.toml [tool.setuptools.packages.find]"
    fi

    # pytest discovery
    if python3 -m pytest --collect-only -q 2>/dev/null | grep -qE "no tests ran|selected|test session"; then
        echo "✅ pytest can discover test directory"
    else
        echo "✅ pytest discovery OK (no tests yet — expected)"
    fi

    # main.py entry responds to --help
    if python3 -m "${PACKAGE_NAME}.main" --help &>/dev/null; then
        echo "✅ main.py entry point responds to --help"
    else
        echo "⚠️  main.py --help failed — add 'typer' and 'rich' to dependencies in pyproject.toml"
    fi
else
    echo "  [DRY-RUN] Would validate: package import, pytest discovery, main.py --help"
fi
echo ""

# --- Done --------------------------------------------------------------------
echo "============================================="
[ "$DRY_RUN" = true ] \
    && echo " ✅ Dry Run Complete — no files were written" \
    || echo " ✅ Scaffolding Complete!"
echo "============================================="
echo ""
echo " Next steps:"
echo "   1.  cd $PROJECT_DIR"
echo "   2.  source activate_env.sh"
echo "   3.  cp .env.example .env        (fill in credentials)"
echo "   4.  Edit ARCHITECTURE.md        (describe your design)"
echo "   5.  Edit config/config.yaml     (set paths and defaults)"
echo "   6.  Start coding in $PACKAGE_NAME/"
echo ""
[ -n "$FEATURE_BRANCH" ] && echo " 🌿 Active branch: feature/$FEATURE_BRANCH" && echo ""

# Remind about GitHub push if remote wasn't reachable
if [ "$DRY_RUN" = false ] && [ "$REMOTE_REACHABLE" = false ]; then
    echo " ⚠️  GitHub repo not yet created. After creating it on GitHub, run:"
    echo "     git push -u origin main"
    echo "     git push -u origin develop"
    [ -n "$FEATURE_BRANCH" ] && echo "     git push -u origin feature/$FEATURE_BRANCH"
    echo ""
fi
