---
phase: 08-monorepo-infra-lxc
plan: 02
subsystem: infra

tags: [ansible, proxmox, lxc, postgresql, postgresql-17, debian-12, ufw, pve]

requires:
  - phase: 08-monorepo-infra-lxc
    provides: "Research on Ansible/Proxmox patterns, community.proxmox collection, PGDG PG17 install sequence"

provides:
  - "ansible/playbook.yml: two-play idempotent playbook (LXC creation + PG17 config)"
  - "ansible/inventory.ini: pve02 + poliscope-db host groups"
  - "ansible/group_vars/all.yml: all variables with placeholders (vmid, ip, password, subnet)"
  - "ansible/requirements.yml: Ansible Galaxy collection dependencies"

affects:
  - 08-01-monorepo (needs LXC IP for DATABASE_URL in .env)
  - 09-schema-redesign (LXC PG17 is the target DB for migrations)
  - all future phases (LXC is the persistent DB target)

tech-stack:
  added:
    - community.proxmox (Ansible Galaxy collection)
    - community.postgresql (Ansible Galaxy collection)
    - community.general (Ansible Galaxy collection)
    - ansible.posix (Ansible Galaxy collection)
  patterns:
    - Two-play Ansible playbook pattern (PVE host + LXC host as separate plays)
    - PGDG repository install sequence for PostgreSQL 17 on Debian 12
    - UFW firewall with default deny + per-service allow rules

key-files:
  created:
    - ansible/playbook.yml
    - ansible/inventory.ini
    - ansible/group_vars/all.yml
    - ansible/requirements.yml
  modified: []

key-decisions:
  - "Use community.proxmox.proxmox (not deprecated community.general.proxmox)"
  - "api_password auth by default (simpler for first run), API token documented as comment"
  - "UFW default deny with explicit allow for 22/5432/3000 from LAN only"
  - "scram-sha-256 for pg_hba.conf (PG17 default, do not downgrade to md5)"
  - "python3-psycopg2 installed via apt (required by community.postgresql modules)"

patterns-established:
  - "Pattern: Ansible two-play LXC provisioning — Play 1 on PVE host, Play 2 on LXC target"
  - "Pattern: PGDG key + repo + apt install postgresql-17 (not default Debian repo which gives PG15)"
  - "Pattern: All placeholder values use <PLACEHOLDER> syntax for clarity"

duration: 10min
completed: 2026-03-28
---

# Phase 8 Plan 02: LXC + PostgreSQL 17 Ansible Provisioning Summary

**Idempotent two-play Ansible playbook provisioning Debian 12 LXC on PVE02 with PostgreSQL 17 (PGDG), scram-sha-256 auth, and UFW firewall — awaiting human execution**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-28T13:27:15Z
- **Completed:** 2026-03-28T13:37:00Z
- **Tasks:** 1/2 complete (Task 2 is a human-action checkpoint)
- **Files created:** 4

## Accomplishments

- Four Ansible files created: playbook, inventory, group_vars, requirements
- Playbook uses `community.proxmox.proxmox` (correct, non-deprecated module)
- PostgreSQL 17 install via PGDG repo (bypasses Debian 12 default that ships PG15)
- LXC creation with static IP, 4 vCPU, 4 Go RAM, 100 Go disk, SSH pubkey injection
- UFW firewall: default deny + allow 22 (anywhere), 5432 + 3000 (LAN only)
- All sensitive values are clearly marked placeholders — no hardcoded IPs/passwords
- Playbook is fully idempotent (safe to re-run)

## Task Commits

1. **Task 1: Create Ansible playbook, inventory, and variables** - `00354bf` (feat)
2. **Task 2: Run Ansible playbook on PVE02** - CHECKPOINT — awaiting human execution

**Plan metadata:** (pending — see below)

## Files Created/Modified

- `ansible/playbook.yml` — Two-play idempotent playbook: Play 1 creates LXC on PVE02, Play 2 installs PG17 + configures access + UFW (205 lines)
- `ansible/inventory.ini` — Two host groups: [pve] with pve02, [lxc] with poliscope-db
- `ansible/group_vars/all.yml` — All configurable variables: vmid, IPs, PG credentials, subnet, disk, bridge
- `ansible/requirements.yml` — Four Ansible Galaxy collections: community.proxmox, community.postgresql, community.general, ansible.posix

## Decisions Made

- `community.proxmox.proxmox` module used (not `community.general.proxmox` which is deprecated and removed in community.general 15.0.0)
- API password auth by default for first run — API token method documented in comments as the more secure alternative
- `scram-sha-256` in pg_hba.conf (PG17 default, not md5)
- `python3-psycopg2` installed via apt on LXC (required by community.postgresql modules)
- Template download task uses `creates:` guard for idempotency (shell task with creates path)

## Deviations from Plan

None — plan executed exactly as written. Playbook follows Pattern 7 from research exactly.

## User Setup Required

Task 2 requires manual steps before the Ansible playbook can run. The user must:

1. Edit `ansible/group_vars/all.yml` — fill in `lxc_ip`, `lxc_gw`, `pg_password`, `lan_subnet`, `pve_api_host`, `pve_api_password`
2. Edit `ansible/inventory.ini` — replace `<PVE02_IP>` and `<LXC_IP>` with actual values
3. Verify Debian 12 CT template is present on PVE02 (PVE UI -> local storage -> CT Templates)
4. Run: `cd ansible && ansible-galaxy collection install -r requirements.yml`
5. Run: `ansible-playbook -i inventory.ini playbook.yml`
6. Verify: `psql -h <LXC_IP> -U poliscope -d poliscope -c "SELECT version();"` → should return PostgreSQL 17.x
7. Update root `.env` with `DATABASE_URL` and `NUXT_DATABASE_URL` pointing to LXC IP

## Checkpoint Status

**PAUSED at Task 2 (checkpoint:human-action)** — The Ansible infrastructure code is complete and committed. Execution requires the user to fill in their specific network values (LAN IPs, PVE credentials) and run the playbook against their PVE02 server.

Resume signal: User confirms "done" once `psql` connects successfully from dev machine to LXC.

## Next Phase Readiness

- Ansible playbook ready to execute — no code work remaining for this plan
- Once user completes Task 2: LXC will be running with PG17 accessible at `<LXC_IP>:5432`
- Phase 08-01 (monorepo restructure) can proceed in parallel — it only needs the LXC IP for `.env.example`
- Phase 09 (schema redesign) depends on LXC being up (target for migrations)

---
*Phase: 08-monorepo-infra-lxc*
*Completed: 2026-03-28 (partial — checkpoint at Task 2)*
