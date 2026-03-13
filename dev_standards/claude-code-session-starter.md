# Claude Code Session: Build dev-standards Repository
# =====================================================
# Paste this into the Claude Code VSCode sidebar to bootstrap the session.
# This carries forward full context from the setup session in claude.ai.

## Who You Are Working With
Paul Drangeid — graph analytics engineer, building a Python/Neo4j ecosystem
of tools around a manifest-first, knowledge-graph-generation pipeline.
All dev is now in WSL. GitHub for all repos. VSCode + Claude Code extension.

## What Was Just Completed
We spent a full session analyzing three existing projects and building a
comprehensive claude.md standards document. We also built and iterated on
a generic project scaffolding script (setup-project.sh). The session ended
with a decision to build a `dev-standards` repo to centralize and version
those standards so they can be pulled at scaffold time and evolve independently.

## The Ecosystem (know these projects)


### Target Structure
```
dev-standards/
├── scripts/
│   ├── setup-project.sh         # Already built — copy from below
│   └── refresh-claude.sh        # TO BUILD — updates auto-generated claude.md sections
├── claude/
│   ├── HEADER.md                # TO BUILD — auto-gen warning block template
│   ├── base.md                  # TO BUILD — universal Python standards
│   └── modules/
│       ├── neo4j.md             # TO BUILD
│       ├── manifest-analyzer.md # TO BUILD
│       ├── live-exporter.md     # TO BUILD
│       └── ast-analyzer.md      # TO BUILD
└── project-templates/
    ├── pyproject.toml.template  # TO BUILD
    ├── config.yaml.template     # TO BUILD
    └── ARCHITECTURE.md.template # TO BUILD
```

### How claude.md Composition Works
1. `setup-project.sh` fetches `HEADER.md` + `base.md` + requested modules
   from this repo at scaffold time
2. The composed file gets a `## Project-Specific` section appended (empty at first)
3. A Claude Code session then analyzes the actual project and fills in
   `## Project-Specific` based on real code
4. `refresh-claude.sh` can later pull updated base/modules while preserving
   everything below `## Project-Specific`

### The HEADER.md Convention
Every generated claude.md starts with:
```markdown
<!-- AUTO-GENERATED: base@<commit> + modules[<list>] -->
<!-- Do not edit above ## Project-Specific — run refresh-claude.sh to update -->
<!-- dev-standards: https://github.com/pdrangeid/dev-standards -->
```
This lets refresh-claude.sh know which modules to re-pull without asking.

### Priority Order for This Session
1. Split today's claude.md.monolith into the module files — this is the
   primary content, don't rewrite it, just reorganize into the right files
2. Build HEADER.md template and refresh-claude.sh
3. Update setup-project.sh to pull from dev-standards at scaffold time
4. Build project-templates/ files

## Source Material: Today's claude.md
The full claude.md we built is committed in the base of this repo (claude.md)
It should be split as follows:

- base.md          ← "Language & Runtime", "Dependencies", "CLI Conventions",
                      "Logging", "File & Directory Structure", "Documentation Standards",
                      "Error Handling", "What NOT to Do (base rules)"
- neo4j.md         ← "Cypher Generation Standards", all node label / rel type
                      vocabulary, MERGE/ON CREATE/ON MATCH patterns, constraints
- manifest-analyzer.md ← "Manifest-First Philosophy", "URI Convention",
                      "Confidence & Origin Tracking", "UnresolvedAsset Pattern",
                      "Data Models (Pydantic)", "TypeMapper", "DataSampler"
- live-exporter.md ← "Strategic Exporter" section — driver management,
                      config architecture, export profiles, amplifier payload,
                      GraphSchema/SchemaElement, backup/restore, tier detection,
                      Lesson logging protocol
- ast-analyzer.md  ← "Codebase Graph Analyzer" section — two-pass architecture,
                      entity ID convention, node/rel vocabulary, has_label(),
                      safe_primitive(), output package format, git metadata

## Key Decisions Already Made (don't re-litigate)
- Python >= 3.11 across all projects (strategic-exporter needs updating from 3.8)
- uv for venv management, black + ruff for formatting/linting
- typer for all CLIs (argparse is legacy in two projects, migrate when touching)
- rich for all console output — no bare print() for user-facing output
- All project config via YAML + .env — nothing hardcoded
- output/.gitkeep pattern for gitignored output directories
- Lesson logging is a first-class protocol, not optional

