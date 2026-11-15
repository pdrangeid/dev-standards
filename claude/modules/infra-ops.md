# Claude Module: Infrastructure Operations

Rules for working on live hosts and networks: change safety, privilege, lockout
prevention, backups, DNS / Pi-hole, and verification. Use it with the `ops` base
in any repo or workspace whose sessions run commands against real machines.
Facts about particular hosts belong in the repo's Project-Specific section (or
the workspace's Notes), not here.

---

## Change Safety

- **Read freely, ask before changing.** Read-only inspection runs without asking:
  `ip addr`, `ip route`, `ss -tlnp`, `systemctl status`, `journalctl`, `cat` of a
  config, `dig`, `pihole status`, `docker ps`. Before any command that changes a
  live host, say what it changes and how to undo it, and wait for a yes. That
  includes:
  - package installs and upgrades
  - `systemctl start|stop|restart|enable|disable`, and reboots
  - network changes: `ip … add|del|set`, `nmcli … modify|up|down`, `netplan apply`,
    `tailscale up|down|set`, `ufw`, `iptables`, `nft`
  - DNS / DHCP changes, including Pi-hole lists and local records
  - `crontab` edits, timer units, `docker compose up|down`
  - `chmod`, `chown` or edits on files outside the repo
- **One host, one change, then verify.** Do not batch changes across hosts until
  the first host is verified.
- **Write the rollback down before the change.** The exact commands that restore
  the previous state go in the session ledger (or the runbook) before you run the
  change.
- Prefer the repo's scripts (with `--dry-run` first) over ad-hoc commands. If you
  run the same ad-hoc command twice, propose a script.

---

## Backups

- Before editing any file on a host, copy it. Inside the repo, use
  `backups/<host>/<path-with-slashes-as-dashes>.<YYYYmmdd-HHMMSS>` (gitignored).
  On the host, use `<file>.bak.<YYYYmmdd-HHMMSS>`.
- Never overwrite or delete an existing backup. Clearing out old backups is the
  user's call.
- For app-managed state (Pi-hole, router UIs, Docker volumes), take the app's own
  export before changing it and record where it went.

---

## Lockout Prevention

Any change that can cut off the access the session is using needs a way back in,
stated before the change. That covers the SSH interface or its address, firewall
rules, routes, the VPN or Tailscale path, and DNS on the host you connect through.

- Name the fallback: a second open session, console / IPMI / KVM, physical access,
  or an automatic revert.
- Prefer commands that revert on their own: `netplan try` over `netplan apply`;
  for firewall changes, schedule the revert first
  (`systemd-run --on-active=5min <restore-command>`, or `at now + 5 minutes`),
  apply, confirm access, then cancel the revert.
- Never take down the interface or VPN path the session is using without the
  user's explicit go-ahead in that same message.
- Before pointing a host at a new resolver, prove it answers: `dig @<server>
  example.com`. A host with broken DNS can't fetch packages or reach git.

---

## Privilege (sudo)

- Use `sudo` for the single command that needs it. Never open a root shell
  (`sudo -i`, `sudo su`, `sudo bash`).
- Never weaken privilege controls to make a task easier: no sudoers or `NOPASSWD`
  edits, no `chmod 777`, no adding users to `docker` / `wheel` / `sudo` groups,
  unless that change is the task and the user asked for it.
- Never store or pass a sudo password: no `echo … | sudo -S`, no password in a
  file, a variable or the command line.
- If sudo needs a password the session can't supply, stop and hand the exact
  command to the user. Appliance OSes often have their own escalation path (a
  vendor task scheduler, a web UI). Record each host's rule in its inventory
  record.

---

## Host Inventory

- Every host the repo manages has an inventory record (`hosts/<host>/README.md`
  or a table in `ARCHITECTURE.md`): hostname, addresses, OS and version, how to
  reach it (SSH alias, Tailscale name), how privilege works there, and which
  services it runs.
- Read a host's record before acting on it. When you learn something it lacks
  (a version, a quirk, a port), update the record in the same session.

---

## DNS & Pi-hole

- **The repo is the source of truth.** Adlists, allow/deny lists, local DNS
  records, CNAMEs and DHCP settings live in version control. A change made in the
  web UI is exported and committed in the same session.
- **Check the version first** (`pihole -v`). The config layout and CLI changed in
  v6: settings moved into `/etc/pihole/pihole.toml` and can be read or set with
  `pihole-FTL --config <key> [value]`. v5 spread them across `setupVars.conf`,
  `custom.list` and dnsmasq drop-ins. Confirm a command with `pihole -h` before
  relying on it.
- **Verify every change by querying the server**, not the client's cache:
  `dig @<pihole-ip> <name>` for a new record, and a known-blocked domain for a
  list change.
- **With more than one Pi-hole**, change one, verify it, then sync or change the
  next. Clients keep a working resolver throughout.
- Keep a fallback resolver until the change is verified, and never leave the
  network with a single resolver that is mid-change.

---

## Verification

- After each change, run the check that proves it worked: the service is
  active, the port answers, the name resolves, the client reconnects. Record it in
  the session ledger as a `check` with the command and result.
- A change with no check, or a failed one, is not done: roll back, or record it
  as a blocker.
