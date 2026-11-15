# Claude Standards: Base Ops Conventions

This file encodes universal patterns and conventions for ops repos in this
ecosystem: repos whose main artifacts are shell scripts, host and network
configuration, and runbooks rather than a Python package. A repo opts in with
`base:ops` in its `AGENTS.md` header (`standards.base: ops` in a workspace).
It is auto-fetched by `refresh-dev-standards.sh`.

---

## Languages & Tooling

- **Bash** for scripts (`#!/usr/bin/env bash`). Assume bash ≥ 4.4 unless a target
  host's notes say otherwise.
- **POSIX `sh`** only for scripts that must run where bash is absent (BusyBox,
  OpenWrt, minimal containers). Give those a `#!/bin/sh` shebang and keep them free
  of bashisms. Say which hosts need this in Project-Specific.
- **Lint**: `shellcheck -x` must be clean for every script. Disable a check only
  inline (`# shellcheck disable=SC2086 # reason`), always with a reason.
- **Format**: `shfmt -i 4 -ci` (4-space indent, indented `case` branches).
- **YAML / JSON config**: 2-space YAML indent; validate with `yamllint` / `jq .`
  where installed before committing.
- **Python is allowed for helpers that outgrow shell** (structured data, APIs,
  anything needing real error handling). Write it as a `uv` script with inline
  dependency metadata (`uv run --script tools/<name>.py`). Once a helper needs
  modules or tests of its own, it belongs in its own repo on the Python base.

---

## Shell Script Conventions

- Start every bash script with `set -euo pipefail`. A script that must tolerate a
  failing command handles it explicitly (`if ! cmd; then …`), never by dropping
  `-e`.
- Every script opens with a header comment: one-line purpose, `Usage:`, flags, and
  what it changes. It also answers `-h` / `--help` with the same text.
- Quote every expansion (`"$var"`, `"$@"`). Use `[[ … ]]` for tests in bash.
  Declare function variables `local`.
- Put logic in functions and end with `main "$@"`, so the script can be sourced in
  tests without running.
- Anything that changes a host takes `--dry-run`. A dry run prints each command it
  would run and changes nothing.
- Scripts are idempotent: a second run with the same inputs changes nothing and
  says so.
- Create temp files with `mktemp` and clean them up with `trap … EXIT`. Never write
  to fixed paths in `/tmp`.
- Never parse `ls` output. Use globs or `find -print0` with `read -r -d ''`.
- Exit non-zero on failure, with a message that names what failed and on which
  host.
- Executable entry points are `chmod +x` and committed that way
  (`git update-index --chmod=+x`). Sourced helpers are not executable.

---

## Output & Logging

- Data goes to stdout; diagnostics, progress and errors go to stderr, so scripts
  compose in pipes.
- Use the same status emoji as the Python standards for human-facing output:
  `✅` success, `🔍` discovery / scanning, `⚠️` warning, `❌` failure.
- Scheduled scripts (cron, systemd timers) log one line per event, as
  `YYYY-MM-DD HH:MM:SS [LEVEL] <script>: <message>`, with `LEVEL` one of `INFO`,
  `WARNING`, `ERROR`. `WARNING` means degraded but the run continues, and `ERROR`
  means a unit of work failed. Each run ends with one `SUMMARY key=value …` line
  carrying its counts and status.
- Never log a secret. Mask tokens and passwords even at debug verbosity.

---

## Error Handling

- Check preconditions up front (required commands with `command -v`, required
  variables, reachable host) and fail before changing anything.
- In a loop over hosts or items, one failure must not abort the rest: record it,
  continue, and report every failure at the end with a non-zero exit.
- Retry only operations that are safe to repeat, with a bounded count and a delay.

---

## File & Directory Structure

```
<repo>/
├── README.md
├── ARCHITECTURE.md              # Hosts, network topology, what runs where
├── AGENTS.md                    # Auto-generated standards + Project-Specific section
├── CLAUDE.md                    # Bridge stub — `@AGENTS.md` import + Claude Code section
├── .env.example                 # Names of required secrets, no values
├── scripts/                     # Executable entry points (shellcheck-clean, +x)
├── lib/                         # Sourced shell helpers (not executable)
├── config/                      # Non-secret config and templates
├── hosts/
│   └── <host>/                  # Per-host config, notes, inventory record
├── runbooks/                    # Step-by-step procedures, one per task
└── backups/                     # Pre-change copies of host files (gitignored)
```

Adapt this to the repo, and record the actual layout in Project-Specific. Keep
anything generated or host-captured that is not reviewed source (backups, exports,
cloned third-party repos) out of git.

---

## Configuration & Secrets

- Hostnames, IPs, ports and paths live in config files (`config/`, `hosts/<host>/`),
  never inline in scripts. Scripts read them through one sourced loader
  (e.g. `lib/config.sh`); nothing else parses config.
- Secrets live only in `.env` / `*.env` files or host-local files outside the repo,
  all gitignored. Always provide `.env.example` with the variable names.
- Never commit private keys, VPN or Tailscale auth keys, API tokens, admin
  passwords or password hashes, even in a private repo. If one is committed, rotate
  it. Removing the commit is not enough.
- Secret files on hosts are mode `600` and owned by the account that reads them.

---

## Documentation Standards

- Every repo must have:
  - `README.md` with a Quick Start showing the most common tasks as exact commands
  - `ARCHITECTURE.md` describing the hosts, the network (subnets, DNS, VPN), and
    what runs where
- `ARCHITECTURE.md` must include a component table: Component | Host | Responsibility
- Every script documents itself in its header comment and `--help`.
- A procedure with more than a couple of manual steps gets a runbook in `runbooks/`:
  purpose, preconditions, steps with exact commands, how to verify, how to roll back.
