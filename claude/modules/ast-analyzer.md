# Claude Module: Codebase Graph Analyzer (AST Analyzer)

Conventions for the codebase-graph-analyzer — the most AST-heavy project in the ecosystem.
It produces the same JSON manifest → graph pipeline as the datasource-analyzer, but the
extraction layer is Python AST rather than SQL parsing.

---

## Two-Pass Analysis Architecture

The analyzer uses a deliberate two-pass design — preserve this, it exists to solve forward-reference problems:

- **Pass 1 — Symbol Discovery** (`_discover_python_symbols`): Walk all `.py` files first using a lightweight `SymbolVisitor`. Catalog every `Function` and `Class` into `global_entities` with minimal properties (name, lineNumber, docString). No relationships created yet.
- **Pass 2 — Full Parse & Connect** (`_parse_python_file` via `PythonVisitor`): Re-walk every file with full context. Now that `global_entities` is populated, `visit_ImportFrom` can resolve internal imports to real entity IDs rather than falling back to `ExternalModule`.

This is why `analyze()` calls `find_files([".py"])` separately before the full `find_files(all_extensions)` pass. Don't collapse these into a single pass.

---

## Entity ID Convention

Different from the datasource URI convention — uses `::` as separator:
```
{project_name}/{relative/path/to/file.py}::{SymbolName}
```
Examples:
- `my_project/src/utils.py::parse_config`  → Function node
- `my_project/src/models.py::UserModel`     → Class node
- `my_project/src/main.py`                  → File node (no `::`)
- `my_project/src/`                         → Directory node (trailing `/`)
- `my_project/`                             → ProjectRoot directory node

Use `_get_entity_id(name, file_path)` — never construct these strings manually.

---

## Node Type Vocabulary

```
PythonFile, ConfigFile, MarkdownDocument, TextDocument, EnvironmentFile
Class, Function, Variable
ExternalModule, ExternalFunction, ExternalClass
FileDirectory (+ ProjectRoot multi-label for root dir)
TopLevelStatement (+ MainBlock multi-label for if __name__ == "__main__")
YamlKey, YamlValue
Heading, EnvironmentVariable
```

---

## Relationship Type Vocabulary

```
CONTAINS_CLASS, CONTAINS_FUNCTION, CONTAINS_TOPLEVEL
DEFINES_VARIABLE, USES_VARIABLE
CODE_IMPORTS, CODE_CALLS, CODE_INHERITS_FROM
CODE_HAS_VALUE, CONTAINS_KEY
CODE_DOC_CONTAINS_HEADING
CODEFILE_CONTAINED_IN   (file → directory)
CODEFOLDER_CONTAINED_IN (directory → parent directory)
CODEPROJECT_HAS_ROOT    (CodeProject → ProjectRoot)
```
Note the `CODE_` prefix convention for cross-entity semantic relationships (calls, imports, inheritance) vs bare verbs for structural containment.

---

## `_add_relationship` Signature

```python
_add_relationship(source_label, target_label, source_id, target_id, rel_type, properties=None)
```
Both `source_label` and `target_label` are required — look them up via `_get_label_by_id(id)` when not immediately known. This is different from the datasource-analyzer which infers labels.

---

## Multi-Label Nodes

Some nodes carry multiple labels as a Python list rather than a string:
```python
{"id": dir_id, "type": ["FileDirectory", "ProjectRoot"], ...}  # root directory
{"id": stmt_id, "type": "TopLevelStatement", ...}              # normal top-level
# MainBlock gets labels added dynamically: labeltype=["TopLevelStatement","MainBlock"]
```
Use `has_label(entity, label)` helper — never do `entity["type"] == label` directly, it breaks on list types.

---

## `safe_primitive()` — Always Use for Property Values

Neo4j cannot store `dict` or `list` as node properties. Always wrap uncertain values:
```python
def safe_primitive(val):
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    return val
```
Apply before setting `codeContent`, `moduleMetadata`, `decorators`, `parameters` etc. as node properties.

---

## Output Package Format

The codebase analyzer outputs two JSON files with a specific envelope structure (not a raw manifest):
```json
{
  "package_schema_version": "1.0",
  "schema_version": "1.0",
  "ingestion_type": "python_codebase_analysis_nodes",
  "group_identifier": "{project_name}_codebase_analysis_{timestamp}",
  "uid": "{project_name}_codebase_analysis_nodes_{timestamp}",
  "generation_timestamp": "ISO8601",
  "project_version": "git_tag_or_hash",
  "branch": "git_branch",
  "project_name": "my_project",
  "data_parts": [
    {
      "content_type": "codebase_graph_nodes",
      "payload": { "nodes": [...] }
    }
  ]
}
```
The relationships package adds `"dependsOn": nodes_group_id` to link the packages. Always populate `project_version` and `branch` from git — warn if unavailable but don't fail.

---

## Git Metadata

```python
branch, version = get_git_branch_and_version(repo_path)
```
- Prefers tag (`git describe --tags --always`), falls back to commit hash
- Returns `(None, None)` gracefully if not a git repo — warn with `⚠️` but continue with `"unknown"`
- Always attach `projectName`, `projectVersion`, `projectBranch` to every node before output

---

## Configuration

- Config in `config/config.yaml`, loaded via `config.py` `get_config(cli_args)`
- CLI args take precedence over YAML — `get_config()` merges them correctly
- Key config paths: `codebase_root` (target project to analyze), `output_dir`
- Output always written to: `{codebase_root}/output/codebase_analysis/{project_name}/`
- File discovery controlled by `include_file_extensions`, `exclude_paths`, `special_file_names` from YAML — never hardcode these in logic
- `check_for_hardcoded_secrets` and `check_for_best_practices` flags exist in config — these features are planned/partial, don't remove the config keys

---

## Import Resolution Strategy

`visit_ImportFrom` uses a two-guess resolution strategy before falling back to `ExternalModule`:
1. Guess: `{project_name}/{relative_path_as_module}.py::{alias}` — file-level module
2. Guess: `{project_name}/{relative_path_as_package}/__init__.py::{alias}` — package-level module

Relative imports (`from . import x`, `from .. import y`) traverse upward from `file_path.parent` by `node.level - 1` levels. Absolute imports resolve from `project_root`. Log all resolution attempts at `DEBUG` level with clear SUCCESS/FAILURE markers.

---

## Order Index

Every entity that represents a sequential code construct tracks its position within its file:
```python
order_index = self.analyzer.get_next_order_index(file_path)
```
This is a per-file monotonically incrementing counter stored in `self.order_indices`. Always set it on Variable, Function, Class, TopLevelStatement, YamlKey, YamlValue nodes. It enables reconstructing code order from the graph.

---

## Known Issues / Tech Debt

- `analyze()` references `my_project_name` and `analyzer` as bare names — these are only defined in the `__main__` block and will `NameError` if `analyze()` is called as a library method. The `CODEPROJECT_HAS_ROOT` relationship creation inside `analyze()` needs to be refactored.
- `config.py` uses `print()` for YAML load confirmation — should use `logger.info()` to match logging conventions.
- `_parse_yaml_file` opens the file twice (once at the top, once inside the try block) — minor redundancy.
- `argparse` is used instead of `typer` — this project predates the typer convention. New CLI additions should use `typer` to align with the ecosystem.

---

## What NOT to Do (AST Analyzer)

- **Don't** collapse the two-pass analysis into one — Pass 1 symbol discovery is required for correct import resolution in Pass 2
- **Don't** do `entity["type"] == "SomeLabel"` directly — use `has_label(entity, label)` to handle multi-label list types
- **Don't** set raw `dict` or `list` values as node properties — always run through `safe_primitive()`
- **Don't** construct entity IDs manually — always use `_get_entity_id(name, file_path)`
- **Don't** skip `order_index` on sequential entities — it's how code order is reconstructable from the graph
- **Don't** hardcode `include_file_extensions` or `exclude_paths` in logic — read from config
