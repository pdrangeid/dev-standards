# Repo Registry Schema

Every repo describes itself in one small YAML file so tools (today: the workspace
repo-map) can show what each repo is for without opening it. This document is the
contract; `dev_standards/registry/models.py` enforces it and
`dev_standards/workspace/registry.py` (`lookup_purpose`) consumes it.

## Per-repo file

- **Name:** `<repo_with_underscores>_registry.yaml` — the repo directory name with
  `-` replaced by `_` (`lifeos-core` → `lifeos_core_registry.yaml`).
- **Location:** the repo's own root, git-tracked in that repo.
- **Shape:** a single YAML **mapping** (never a list, never appended to).

| Field | Required | Type | Read by any tool today? |
|:---|:---|:---|:---|
| `repo` | yes | string, the repo directory name | Yes — the rollup keys on it |
| `purpose` | yes | non-empty string, one sentence: why the repo exists | Yes — workspace repo-map |
| `interfaces` | no | list of strings: public functions, CLI commands, APIs | Reserved |
| `contracts` | no | list of strings: data models, classes, schemas defined or shared | Reserved |
| `integration_points.env` | no | list of environment variable names | Reserved |
| `integration_points.config` | no | list of config key names | Reserved |
| `integration_points.deps` | no | list of other repos this one depends on | Reserved |
| `model_prefs` | no | string: preferred LLM and the task it is used for | Reserved |
| `generated_from` | no | `sha256:<hex>` written by the generator | Generator only |

Unknown keys are rejected. Reserved fields must never break the
"mapping with a `purpose`" rule that `lookup_purpose` depends on.

```yaml
repo: my-repo
purpose: Why this repo exists, in one sentence.
interfaces:
- my-repo run
contracts:
- ExtractionPayload
integration_points:
  env:
  - MY_REPO_TOKEN
  config:
  - retrieval.max_items
  deps:
  - shared-kernel
model_prefs: None
generated_from: sha256:0000000000000000000000000000000000000000000000000000000000000000
```

## Rollup: `registry.yaml`

A single YAML **list** of mappings, each with at least `repo` and `purpose` — the
aggregate fallback `lookup_purpose` tries when no per-repo file matches. It is
**generated** by `dev-standards registry rollup` (sorted by `repo`, without
`generated_from`) and must never be hand-edited.

## The hub: `~/.repository_registry/`

A machine-local directory (not git-tracked; the real data lives in each repo):

```
~/.repository_registry/
  <name>_registry.yaml -> <repo>/<name>_registry.yaml    one symlink per registered repo
  registry.yaml                                           generated rollup
```

Point a workspace at it with `registry_dir: /home/YOUR_USERNAME/.repository_registry`
in `workspace.yaml`. The path must be absolute — `~` is deliberately rejected so the
yaml means one thing for every user and shell. `lookup_purpose` needs no changes: it
opens `<name>_registry.yaml` inside `registry_dir`, and symlinks resolve transparently.
The hub's symlinks are also the list of repos that `refresh` regenerates.

## How files are generated

`dev-standards registry generate` sends the repo's `README.md`, `ARCHITECTURE.md`,
`AGENTS.md` (or legacy `claude.md`), `pyproject.toml` and `docs/usage_instructions.md`
to an LLM and validates its answer against this schema before writing. `repo` is always
set from the directory name, never taken from the model.

The file is **overwritten**, never appended to. An LLM will not phrase things the same
way twice, so idempotency comes from `generated_from`: a hash of the source docs plus
the prompt version. If it matches, the LLM is not called and the file is not touched.
Consequently a hand edit survives until one of the source docs changes, at which point
the file is regenerated.
