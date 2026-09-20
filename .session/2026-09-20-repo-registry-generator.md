# Session: Repo registry generator standard

<!-- Fill in before handing to Claude Code -->
Date: 2026-09-20
Repo: dev-standards
Branch: feature/repo-registry-generator
Status: draft

---

## Goal

Define and implement the missing *producer* side of the repo registry: a documented
schema and a `dev-standards`-owned command that generates/refreshes a single repo's
`<repo_with_underscores>_registry.yaml`, plus a mechanism that makes every repo's
registry file discoverable from one place without moving the file out of that repo's
own git history. `dev_standards/workspace/registry.py` already *consumes* registry
files (`lookup_purpose`) for the workspace repo-map; this session builds what writes
them. Deliverable: a generator command/script, a formal schema doc, a decision on the
central discovery layout (`~/.repository_registry/` symlink hub, replacing the current
`registry_dir: ~/Projects` example), a decision on regeneration cadence (weekly job vs.
session-close step), and updated README/tests reflecting all of the above.

---

## Context & Constraints

- **Decision**: The per-repo file contract in `dev_standards/workspace/registry.py`
  (`lookup_purpose`) is locked — do not change it. A per-repo `<repo>_registry.yaml`
  must be a YAML **dict** with a `purpose` key; the aggregate fallback `registry.yaml`
  must be a YAML **list** of dicts each with `repo` and `purpose` keys. Whatever
  generator this session builds must produce files satisfying this exact shape.
- **Decision**: `Workspace._require_absolute` in `dev_standards/workspace/models.py`
  intentionally rejects `~` and relative paths for `repos_root` and `registry_dir` —
  "so the yaml means one thing" regardless of which user/shell renders it. This is
  deliberate, not a bug; do not relax it. (This session's predecessor fixed the
  *template's* hard-coded `/home/pdrangeid/...` example paths to a generic
  `/home/YOUR_USERNAME/...` placeholder — see `project-templates/workspace.yaml.template`
  — the validation rule itself is untouched and correct.)
- **Decision**: No personal directory structure (e.g. `/home/pdrangeid`) in any
  committed template or doc produced by this session. Use placeholders.
- **Out of scope**: Changing `registry.py`'s lookup contract, `render.py`'s repo-map
  logic, or building a graph-derived repo map (explicitly deferred to "later" in the
  workspace-module session below).
- **Out of scope**: Migrating the user's real LifeOS repos' registry data or running
  the generator against them — this session builds the standard and tooling only.
- **Reference files**:
  - `dev_standards/workspace/registry.py` — the consumer contract (read first, in full).
  - `dev_standards/workspace/models.py` — `Workspace.registry_dir`, `_require_absolute`.
  - `project-templates/workspace.yaml.template` — the commented-out
    `registry_dir: /home/YOUR_USERNAME/Projects` example this session should reconsider.
  - `.session/2026-09-20-dev-standards-workspace-module.md` — predecessor session.
    Its "Decisions Made This Session" step 2 explicitly deferred registry generation:
    registry files "are *not* inside the repos. They live beside them in `~/Projects/`
    as `<repo_with_underscores>_registry.yaml`... New optional `registry_dir` key...
    `lifeos-hostops` and `lifeos-logwatch` have no registry file here." That gap is
    this session's subject.
  - `scripts/setup-project.sh`, `scripts/refresh-dev-standards.sh` — existing bash
    tooling style, for comparison against the newer Python `workspace` sub-app when
    deciding where the generator command should live.
  - Two ad hoc scripts the user has been running by hand (pasted below under Specs) —
    not committed anywhere, the actual starting point for this standard.

**Open decisions for the user to confirm before/while building (do not guess silently):**

1. **Cadence** — regenerate registries as a scheduled weekly job across all tracked
   repos, vs. a per-repo session-close step, vs. both (mandatory weekly + optional
   on-demand). Recommendation discussed with the user: weekly job as the source of
   truth, on-demand script available but not mandatory at session close.
2. **Discovery layout** — replace the `registry_dir: ~/Projects` convention with a
   dedicated `~/.repository_registry/` directory of symlinks, one per repo, pointing
   at that repo's own git-tracked `<repo>_registry.yaml`, plus a *generated* rollup
   `~/.repository_registry/registry.yaml` (never hand-edited). This needs **no change**
   to `registry.py` — it already just opens files by name inside whatever `registry_dir`
   points at; a symlink resolves transparently. Confirm the user wants this to replace
   the `~/Projects` example in the template, and whether `~/.repository_registry/`
   itself should be gitignored/untracked (it's machine-local — the real data lives in
   each repo).

---

## Relevant Specs / Schemas / Examples

**Consumer contract, verbatim from `dev_standards/workspace/registry.py`:**

```python
def lookup_purpose(repo_name: str, registry_dir: Path | None) -> str | None:
    """Two layouts, tried in order: per-repo dict, then aggregate list."""
    per_repo = registry_dir / f"{repo_name.replace('-', '_')}_registry.yaml"
    if per_repo.is_file():
        data = _read_yaml(per_repo)
        if isinstance(data, dict) and data.get("purpose"):
            return str(data["purpose"])
    aggregate = registry_dir / "registry.yaml"
    if aggregate.is_file():
        data = _read_yaml(aggregate)
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and entry.get("repo") == repo_name and entry.get("purpose"):
                    return str(entry["purpose"])
    return None
```

**Per-repo entry schema the user has been generating by hand (the starting point —
`purpose` is the only field `registry.py` currently reads; the rest are reserved for
future use and must not break the dict-with-`purpose` contract above):**

```yaml
purpose: '[One-sentence Why]'
interfaces: ['[Functions/CLI/APIs]']
contracts: ['[Data models/Classes/Schemas]']
integration_points:
  env: ['[ENV_VAR names]']
  config: ['[Key names in schemata.yaml or local .yaml]']
  deps: ['[Other LifeOS repos this depends on]']
model_prefs: '[Preferred LLM & Specific task]'
```

**The user's existing ad hoc generator (currently run by hand per repo, output APPENDED
to one shared, untracked `~/Projects/registry.yaml` — this is the append-duplication bug
to fix: rerunning it for the same repo adds a second entry instead of replacing the
first):**

```sh
gemini "Analyze @README.md, @ARCHITECTURE.md, @claude.md, @pyproject.toml, and @docs/usage_instructions.md.

APPEND a new entry to @~/Projects/registry.yaml using this EXACT YAML structure:

- repo: '$(basename "$PWD")'
  purpose: '[One-sentence Why]'
  interfaces: ['[Functions/CLI/APIs]']
  contracts: ['[Data models/Classes/Schemas]']
  integration_points:
    env: ['[ENV_VAR names]']
    config: ['[Key names in schemata.yaml or local .yaml]']
    deps: ['[Other LifeOS repos this depends on]']
  model_prefs: '[Preferred LLM & Specific task]'"
```

**The user's existing rollup/flowchart generator (unchanged in scope for this session,
but its input path must move if Open Decision 2 lands on the symlink hub):**

```sh
gemini "Review the complete @registry.yaml.
Create a master @repo_flowchart.md using Mermaid 'graph TD'.
Rules: group into subgraphs Core_Infrastructure/Data_Pipelines/Interfaces; draw edges
from 'deps'; note shared 'contracts'; no circular logic unless explicit."
```

**Proposed directory layout (pending Open Decision 2):**

```
<any-repo>/<repo_with_underscores>_registry.yaml   # git-tracked in that repo, one dict, overwritten not appended
~/.repository_registry/                            # machine-local, NOT git-tracked
  <repo>_registry.yaml -> <path-to-repo>/<repo>_registry.yaml   (symlink, one per known repo)
  registry.yaml                                     # generated rollup (script-written, never hand-edited)
```

---

## Instructions

1. Read `AGENTS.md`, then `dev_standards/workspace/registry.py` and the
   `registry_dir`/`_require_absolute` handling in `dev_standards/workspace/models.py`
   in full before writing anything.
2. Read `.session/2026-09-20-dev-standards-workspace-module.md`, specifically its
   "Decisions Made This Session" step 2, so the generator you build matches what the
   consumer already expects and doesn't re-litigate settled choices.
3. Get the user's explicit confirmation on the two Open Decisions above (cadence,
   discovery layout) before writing the generator/rollup scripts — these determine
   where files land and how they're wired up. Record their answers under Decisions.
4. Formalize the schema from Relevant Specs into a short `docs/registry-schema.md`:
   mark `purpose` as required/consumed today, the rest as reserved/optional fields not
   yet read by any tool.
5. Decide where the generator command lives — a Python subcommand alongside the
   existing `workspace` sub-app in `dev_standards/` (consistent with where the newer,
   structured tooling lives), or a `scripts/*.sh` file matching `setup-project.sh`'s
   style (consistent with the fact that it shells out to `gemini`, same as the
   existing ad hoc scripts). Make a call, document why, then implement it so that it:
   - overwrites (never appends) `<repo_with_underscores>_registry.yaml` at the target
     repo's own root, computing the filename from `basename "$PWD"` with `-` → `_`;
   - is idempotent — running it twice on an unchanged repo produces no diff.
6. Implement the rollup step per the confirmed Open Decision 2: build/refresh
   `~/.repository_registry/` (symlinks) and its generated `registry.yaml`, sourcing the
   repo list from wherever the user confirms it should come from (a `workspace.yaml`,
   or a separate tracked list — decide and document).
7. Wire up the confirmed cadence (Open Decision 1). If weekly: document the schedule
   (and, if the user wants it set up now rather than just documented, a
   `create_trigger`/cron Routine is a separate, explicit ask — do not set one up
   silently). If session-close: add the step to the relevant `claude/` fragment's
   session-close checklist.
8. Update `README.md` with a new section documenting the schema, the generate command,
   the symlink hub, and the cadence — following the existing "Multi-Repo Workspaces"
   section's style.
9. Add tests mirroring `tests/test_workspace_*.py`'s style: overwrite-not-append
   idempotency, symlink resolution through `registry_dir`, and schema validation
   failures.
10. Append decisions to the section below as they're made and set `Status: complete`
    when done.

---

## Decisions Made This Session

_None yet._
