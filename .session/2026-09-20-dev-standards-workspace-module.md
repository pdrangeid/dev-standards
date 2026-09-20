# Session Handoff: dev-standards workspace module

- **Date:** 2026-09-20
- **Status:** active
- **Origin surface:** claude.ai web chat (strategy discussion)
- **Target surface:** Claude Code in `dev-standards` on `cranston-llm`
- **Repos in scope:** `dev-standards` (implementation). Read-only reference: the existing `lifeos-logwatch-hostops-refactor` workspace folder, which becomes the first instance.

---

## Goal

Add a `workspace` module to `dev-standards` that scaffolds and maintains multi-repo Claude Code working folders from a single `workspace.yaml`. One command creates a new workspace, and a second command re-renders it after `workspace.yaml` changes. The rendered output is: a git-initialized folder with `CLAUDE.md` (→ `AGENTS.md`), a workspace `AGENTS.md` composed from the core dev-standards fragments plus a new workspace fragment, `.mcp.json`, `.claude/settings.json`, `.claude/settings.local.json`, `.env.example`, `.gitignore`, and `.session/` with the handoff template. Adding a repo to a workspace means editing `workspace.yaml` and re-rendering; nothing else is hand-edited. The deliverable is working and tested in `dev-standards`, and it has been used to regenerate the existing logwatch/hostops workspace.

## Context & Constraints

**Locked decisions:**
- **Composition, not a fork.** The workspace `AGENTS.md` is built by the existing dev-standards claude.md composition mechanism, core fragments plus a new `workspace` fragment. Core improvements must flow into workspaces on re-render. Do not build a parallel templating system if the existing one can do this.
- **Every workspace is a git repo** (local, no remote required), so handoffs and decisions reach the codebase graph via codebase-graph-analyzer.
- **`CLAUDE.md` is one line:** `@AGENTS.md`.
- **Sub-repo AGENTS.md files are read lazily**, by instruction, not `@`-imported: before reading or changing code in repo X, read `X/AGENTS.md`.
- **Precedence:** a repo's own AGENTS.md governs code inside that repo; the workspace AGENTS.md governs cross-repo coordination, graph access, and session protocol.
- **Commit trailer:** every commit made from a workspace session, in any repo, carries `Session: <handoff-file-stem>`.
- **Decision writeback:** a decision that affects a specific repo is recorded in that repo's AGENTS.md as well as the workspace handoff.
- **Graph access:** ad-hoc Cypher is read-only; graph writes happen only through pipeline tools. Enforced in layers: read-only credentials or server flag where supported, plus a Claude Code permission `deny` on the MCP write tool.
- **No secrets in committed files.** Credentials live in `.env`, which is gitignored; `.env.example` is committed.
- **`workspace.yaml` is the single source of truth** for the repo list, graph target, and MCP servers.
- **Render ownership:**
  - Fully generated, overwritten on every render: `CLAUDE.md`, `.mcp.json`, `.claude/settings.json`.
  - Merge-rendered: `.claude/settings.local.json`. Only `permissions.additionalDirectories` is replaced; all other keys are preserved.
  - Marker-delimited: `AGENTS.md`. Only the regions between `<!-- BEGIN GENERATED: ... -->` and `<!-- END GENERATED: ... -->` are replaced; hand-written sections are preserved.
  - Never touched after creation: `.session/*`.
- **Tracked vs untracked:** `.claude/settings.local.json` holds machine-specific absolute paths and is gitignored. `workspace.yaml` is committed, so a workspace can be re-rendered on another machine.

**Out of scope:**
- Generating the repo map from a graph query. Later, once the intent layer exists. For now, use each repo's registry YAML if present, else the `role` field in `workspace.yaml`.
- Remote MCP connector setup for claude.ai.
- Changes to any LifeOS repo's code.

**Reference files (inspect first):**
- `dev-standards`: the existing claude.md/AGENTS.md composition code and fragment layout, `.session/_template.md`, and any existing CLI entry point.
- LifeOS repo registry YAML files (confirm location and schema).
- Existing workspace: `/home/pdrangeid/workspaces/lifeos-logwatch-hostops-refactor/` (confirm path; the current `.env` reference misspells it as `workstpaces`).

## Relevant Specs / Schemas / Examples

**`workspace.yaml` (source of truth):**

```yaml
name: lifeos-logwatch-hostops-refactor
description: Align lifeos-logwatch with lifeos-hostops; fix cranston-llm telemetry gap
repos_root: /home/pdrangeid/develop        # absolute; no ~
repos:
  - name: lifeos-hostops
    role: Central job orchestration; pushes collection tasks to hosts   # fallback if no registry YAML
  - name: lifeos-logwatch
  - name: lifeos-envprofiler
  - name: lifeos-core
  - name: codebase-graph-analyzer
  - name: dev-standards
graph:
  database: lifeos-kg
  read_only: true
mcp:
  servers:
    - name: neo4j
      package: <confirm: package name + pinned version>
      env_file: .env
      write_tool: <confirm: e.g. write_neo4j_cypher>   # gets a permissions deny rule
standards:
  fragments: [core, python, neo4j, workspace]         # names per existing composition mechanism
```

Validate with a Pydantic model: fail if a repo dir doesn't exist, if `repos_root` is relative, or if `graph.database` is empty.

**Rendered `CLAUDE.md`:**

```
@AGENTS.md
```

**Rendered `AGENTS.md` (skeleton):**

```markdown
# Workspace: {{ name }}
{{ description }}

<!-- BEGIN GENERATED: standards -->
... composed core dev-standards fragments ...
<!-- END GENERATED: standards -->

<!-- BEGIN GENERATED: workspace-rules -->
## Precedence
A repo's own AGENTS.md governs code inside that repo. This file governs cross-repo coordination, graph access, and session protocol.

## Working in a repo
Before reading or changing code in any repo below, read `<repo>/AGENTS.md` and follow it.

## Graph access
Database: `{{ graph.database }}`. Ad-hoc Cypher is read-only. Graph writes happen only by running pipeline tools.

## Session protocol
- Handoffs live in `.session/` (template: `.session/_template.md`).
- Every commit, in any repo, includes the trailer `Session: <handoff-file-stem>`.
- A decision that affects one repo is also recorded in that repo's AGENTS.md.
- Append decisions to the active handoff's "Decisions Made This Session" as they are made.
<!-- END GENERATED: workspace-rules -->

<!-- BEGIN GENERATED: repo-map -->
## Repos
| Repo | Path | Role |
|---|---|---|
| lifeos-hostops | /home/pdrangeid/develop/lifeos-hostops | ... |
<!-- END GENERATED: repo-map -->

## Notes
(hand-written; preserved on re-render)
```

**Rendered `.mcp.json` (no secrets):**

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "uvx",
      "args": ["--env-file", "<abs workspace path>/.env", "<package>@<version>"],
      "env": {
        "NEO4J_DATABASE": "lifeos-kg"
      }
    }
  }
}
```

Keep exactly one env var naming scheme, the one the chosen server actually reads (confirm from its docs); the current config duplicates `NEO4J_*` and `NEO4J_MCP_*`. Add the server's read-only flag if it has one.

**Rendered `.claude/settings.json` (committed):**

```json
{
  "enableAllProjectMcpServers": true,
  "permissions": {
    "deny": ["mcp__neo4j__<write_tool>"]
  }
}
```

**Merge-rendered `.claude/settings.local.json` (gitignored):**

```json
{
  "permissions": {
    "additionalDirectories": [
      "/home/pdrangeid/develop/lifeos-hostops",
      "/home/pdrangeid/develop/lifeos-logwatch"
    ]
  }
}
```

**`.env.example`:**

```
NEO4J_URI=
NEO4J_USERNAME=
NEO4J_PASSWORD=
```

**`.gitignore`:**

```
.env
.claude/settings.local.json
```

**CLI shape (adapt to the existing dev-standards entry point, if any):**

```
dev-standards workspace new <path> --from workspace.yaml   # create folder, git init, render, copy .session/_template.md
dev-standards workspace render [<path>]                    # re-render after editing workspace.yaml
dev-standards workspace check [<path>]                     # validate yaml; report drift between yaml and rendered files
```

## Instructions

1. Read `dev-standards/AGENTS.md`, the existing composition code, fragment layout, CLI entry point, and `.session/_template.md`. Summarize how composition works today before writing any code.
2. Locate the LifeOS repo registry YAML convention (path and schema) and decide how the repo-map reads `role` from it, falling back to `workspace.yaml`. Record the decision.
3. Confirm the Neo4j MCP server package in use, its pinned version, the env var names it reads, whether it has a read-only flag, and its write tool's exact name. Record the findings.
4. Add the `workspace` fragment to the fragment library with the workspace-rules content above.
5. Implement the Pydantic model for `workspace.yaml` with the validations listed.
6. Implement `render`: generated files, merge for `settings.local.json`, and marker-region replacement for `AGENTS.md`. Make it idempotent: two consecutive renders produce no diff.
7. Implement `new` (git init, render, copy the session template, initial commit) and `check` (validation plus drift report).
8. Add tests covering idempotency, preservation of hand-written AGENTS.md sections, preservation of unrelated `settings.local.json` keys, and validation failures.
9. Write a `workspace.yaml` for the existing `lifeos-logwatch-hostops-refactor` folder with the repos listed above, then render it. Confirm it fixes the known config issues: the database is `lifeos-kg`, all six repos are present with absolute paths, the `workstpaces` typo is gone, there is a single env var scheme, the version is pinned, the write tool is denied, and the `neo4j-cypher` name mismatch is removed.
10. `git init` the existing workspace if it isn't a repo already, and commit the rendered result with `Session: 2026-09-20-workspace-module`.
11. Note in the logwatch/hostops workspace's `AGENTS.md` Notes section that the session must read `llmadmin`'s crontab via `sudo crontab -l -u llmadmin`, or run as `llmadmin`.
12. Document the module in the dev-standards README, covering creating a workspace, adding a repo, and what is and isn't safe to hand-edit.
13. Append decisions to the section below and set Status to `complete`.

## Decisions Made This Session
### How composition worked before this session (step 1)
- There was **no Python composition code**. Composition is bash: `setup-project.sh` and
  `refresh-dev-standards.sh` `curl` `claude/base.md` + `claude/modules/<m>.md` from GitHub raw
  (`develop` branch), prefix an `<!-- AUTO-GENERATED: base + modules[...] -->` header, and append
  a `## Project-Specific` stub. Refresh splits on `## Project-Specific`.
- The only CLI in Python was a vestigial typer stub (`dev_standards/main.py`, one `run` command),
  and `pyproject.toml` was broken on Linux (`dev_Standards` casing).
- There is no `core`/`python` fragment split: `base.md` is core + Python; modules are `neo4j`,
  `llm`, `live-exporter`, `manifest-analyzer`, `ast-analyzer`.

### Decisions
- **Composition is reimplemented in Python over the same fragment files** (`dev_standards/workspace/fragments.py`),
  read from a local checkout rather than GitHub. The bash mechanism cannot do marker regions or
  templating, and cannot be reused from Python; the *content* (base.md + modules) is shared, so
  core improvements still flow into workspaces on re-render. The checkout must be installed
  editable; `--fragments-dir` / `DEV_STANDARDS_CLAUDE_DIR` override.
- **Fragment names:** `standards.modules: [neo4j]` replaces the handoff's `standards.fragments:
  [core, python, neo4j, workspace]`. `base` (= core + python) and `workspace` are implicit and
  rejected if listed.
- **Workspace fragment** lives at `claude/modules/workspace.md` (not in `setup-project.sh`'s
  hardcoded module menu, so it is not offered for normal projects). One placeholder,
  `{{ graph_database }}`, is substituted at render time.
- **Title/description are a generated `header` region** (the handoff skeleton had them outside
  any region, which would leave `name`/`description` edits in `workspace.yaml` unpropagated).
  Four regions: `header`, `standards`, `workspace-rules`, `repo-map`. A missing region is
  inserted before `## Notes`; malformed markers make render refuse to write.
- **Registry YAML (step 2):** files are *not* inside the repos. They live beside them in
  `~/Projects/` as `<repo_with_underscores>_registry.yaml` (single mapping) plus an aggregate
  `registry.yaml` (list). The field is `purpose`, not `role`. New optional `registry_dir` key in
  `workspace.yaml`; lookup order: per-repo file, aggregate, then `role` from the yaml, else
  "(no description)". `lifeos-hostops` and `lifeos-logwatch` have no registry file here.
- **Neo4j MCP (step 3), verified against PyPI + github.com/neo4j/mcp v1.6.0 `config.go`:**
  package `neo4j-mcp-server`, latest and pinned `1.6.0` (the existing configs were unpinned).
  Canonical env vars are `NEO4J_MCP_URI/USERNAME/PASSWORD/DATABASE/READ_ONLY/TELEMETRY`; the
  un-prefixed `NEO4J_*` names are legacy aliases (the source of the current duplicated
  schemes). Read-only flag: `NEO4J_MCP_READ_ONLY=true`, which disables the write tool. Tools:
  `get-schema`, `read-cypher`, `write-cypher`, `list-gds-procedures` — the write tool is
  `write-cypher`, so the deny rule is `mcp__neo4j__write-cypher` (not `write_neo4j_cypher`; that
  is the older `mcp-neo4j-cypher` package). `uvx --env-file <f> neo4j-mcp-server@1.6.0` was
  run with dummy credentials: it starts, honours the env, and fails only on connectivity.
  One scheme is emitted: `.env` and `.env.example` use `NEO4J_MCP_*`; `.mcp.json` env has
  DATABASE, READ_ONLY and TELEMETRY only.
- **MCP model:** `package` and `version` are separate fields; `version` must be an exact pin.
  `KNOWN_SERVERS` in `models.py` holds the env/tool contract per package; an unknown package
  renders only its explicit `env` and no deny rule unless `write_tool` is given.
- **`graph.read_only: false`** drops the server flag but the write-tool deny stays — the
  locked decision is that writes go only through pipeline tools.
- **File ownership additions:** `.env.example` is fully generated; `.gitignore` gets missing
  required lines appended and nothing removed; `.session/*` is created by `new` only.
- **`.mcp.json` embeds the absolute workspace path** (per the handoff), so re-rendering on
  another machine changes a committed file. Left as specified; a relative `.env` would avoid it
  but is unverified against Claude Code's MCP working directory.
- **Fixed `pyproject.toml`** (Next Step 1): package name/casing `dev_standards`, added
  `dev-standards` script entry point, `pydantic` and `pyyaml` dependencies, and a bugbear
  setting so ruff accepts the standard `typer.Option` defaults. The `rich<14` pin is untouched.

### Verification
- 37 tests pass (models, render, CLI) with coverage on; ruff and black clean. A deliberate
  non-determinism mutation made 4 tests fail, confirming the idempotency tests bite.
- End-to-end: `workspace new` against 4 real repos in `~/develop` with the real registry dir
  produced a committed workspace with zero drift on `check`.

### Blocked — steps 9, 10, 11 (not done)
This session ran on **pmd-office**, not `cranston-llm`. `/home/pdrangeid/workspaces/` (and the
`workstpaces` variant) does not exist here, and neither `lifeos-hostops` nor `lifeos-logwatch`
is under `~/develop` or `~/Projects`, so `load_workspace` correctly refuses the yaml. The
handoff's `.env`/existing-config fixes (database, `workstpaces` typo, single scheme, pin, deny,
`neo4j-cypher` mismatch) are all produced by the render, but have not been applied to the real
folder. `project-templates/workspace.yaml.template` holds the ready yaml. To finish on
cranston-llm: pull this branch, `uv pip install -e .[dev]`, copy the template to the workspace
folder as `workspace.yaml` (adjust `repos_root`/`registry_dir`), move the existing folder aside
or run `render` in it, `git init` if needed, commit with trailer
`Session: 2026-09-20-workspace-module`, and add the `sudo crontab -l -u llmadmin` note (step 11)
under `## Notes` in that workspace's `AGENTS.md`.
