# Pitfalls Research

**Domain:** Universal parliamentary database expansion — adding multi-source ingestion to existing Nuxt 4 + PostgreSQL app
**Researched:** 2026-03-28
**Confidence:** HIGH (schema/migration/FTS), MEDIUM (French data specifics), LOW (senat cross-referencing)

---

## Critical Pitfalls

### Pitfall 1: Monorepo Migration Breaks Nuxt Module Resolution

**What goes wrong:**
Nuxt in a pnpm monorepo resolves workspace package imports transitively, generating relative paths in `.nuxt/dev/index.mjs` instead of preserving the package name. Shared packages (e.g., `@poliscope/db`, `@poliscope/types`) become invisible to Nuxt's build pipeline, causing `Cannot find module` errors at runtime or build time — even if TypeScript resolves them fine in the IDE.

**Why it happens:**
Nuxt's Vite bundler performs its own dependency scanning before Node resolution. When a package is workspace-local (symlinked by pnpm), Nuxt may fail to treat it as an external and instead tries to bundle or resolve it differently. The `shamefully-hoist` flag in `.npmrc` changes the entire hoisting behavior for the workspace, making it an all-or-nothing switch with side effects across all packages.

**How to avoid:**
- Add workspace packages to `nuxt.config.ts` under `vite.optimizeDeps.include` or `build.transpile` as needed
- Never use `shamefully-hoist=true` — use explicit `hoist-pattern[]` entries in `.npmrc` instead
- Disable `typescript.includeWorkspace` in Nuxt's tsconfig for type checking to avoid cascading TS errors
- Test the Nuxt app build (not just `dev`) immediately after moving any file into a shared package

**Warning signs:**
- `dev` mode works but `nuxt build` fails
- TypeScript shows no errors but runtime throws module not found
- Changing a shared package requires restarting the TS server in VS Code

**Phase to address:** Monorepo foundation phase — must be validated before any shared code is extracted.

---

### Pitfall 2: Schema Migration Locks Existing Tables or Silently Drops Data

**What goes wrong:**
Adding 10+ tables, modifying existing columns, and creating FK relationships between old and new tables can produce blocking DDL operations. `ALTER TABLE` to add a NOT NULL column without a default will fail if any rows exist. Adding an index without `CONCURRENTLY` takes an exclusive lock, making the app unresponsive during migration. Drizzle's `push` command (used in dev) bypasses the migration log — running it on a staging DB that already has prod data can silently drop and recreate constraints.

**Why it happens:**
Developers use `drizzle-kit push` in development, form a habit, then accidentally run it on a shared environment. Drizzle's `generate` + `migrate` flow is correct for production but requires discipline. The transition from 5 tables to ~15 tables via a single migration file is also risky — one failing statement aborts everything.

**How to avoid:**
- Never use `drizzle-kit push` outside of a clean local dev DB — enforce this as a rule
- Split the schema migration into incremental migration files (one file per logical group: deputies extensions, then amendments table, then questions, etc.)
- For adding NOT NULL columns to existing tables: use a two-step migration (add nullable → backfill → add NOT NULL constraint)
- Use `CREATE INDEX CONCURRENTLY` for all new indexes on existing tables — wrap in a separate migration since it cannot run inside a transaction
- Always wrap FK additions in explicit transactions with rollback tested
- Test migrations on a DB snapshot restored from prod before running on prod

**Warning signs:**
- Migration takes longer than 30 seconds on small tables (lock contention)
- `drizzle-kit generate` shows a drop + recreate for a table you only added columns to
- `__drizzle_migrations` table is missing (means push was used instead of migrate)

**Phase to address:** Schema design phase — migration strategy must be defined before any schema changes are written.

---

### Pitfall 3: Deputy ID Mismatch Across Sources (Silent Data Corruption)

**What goes wrong:**
The existing system already uses a fallback from `official_id` (DILA href ID like `795746`) to normalized name matching. When adding new data sources (amendments from data.assemblee-nationale.fr, questions from nosdeputes.fr, bills from Tricoteuses), each source uses a different ID scheme:
- DILA debates: numeric fiche ID from href (`/fiches_id/795746.asp`)
- AN open data acteurs: `PA` prefixed IDs (`PA795746`)
- nosdeputes.fr: slug-based (`francois-hollande`)
- Tricoteuses cleaned data: `PA` prefixed matching AN open data
- Sénat: completely separate `LA`/`PO` prefixed IDs with no overlap

If the deputy resolution logic silently falls back to name matching and gets a false positive (two deputies with similar names, or a minister who is not a deputy), FK links are wrong but no error is raised. This creates referential corruption that is invisible until a UI bug surfaces.

**Why it happens:**
Name normalization is lossy. "M. François Bayrou" in a debate transcript, "Bayrou, François" in an amendment form, and `francois-bayrou` as a slug all normalize differently. The current `normalize_name` strips accents and punctuation but doesn't handle compound surnames, particules ("de", "du"), or title prefixes consistently across sources.

**How to avoid:**
- Use `PA` IDs as the single canonical deputy identifier — populate `official_id` from AN open data first
- When ingesting from sources that lack `PA` IDs, map through a pre-built cross-reference table (slug → PA ID from nosdeputes API, numeric fiche ID → PA ID from DILA href)
- Track match confidence in the ingestion stats: if name-match rate exceeds 30% for a source, flag as suspect
- Never silently drop unmatched records — log them to a `ingestion_warnings` table with source, record ID, and match attempt data
- Reject false senator/deputy cross-links — Sénat IDs will never appear as AN deputies; add a source validation step

**Warning signs:**
- `deputy_unmatched` stat in ingestion logs is above 20% for any source
- Same `deputy_id` linked to contradictory political groups across different record types
- A "deputy" with amendments for bills they never participated in

**Phase to address:** Data ingestion phase — cross-reference table must exist before any non-DILA source is ingested.

---

### Pitfall 4: TAZ Archive Format Breaks on Outer/Inner Tar Variations

**What goes wrong:**
DILA `.taz` archives are not standard gzip-compressed tarballs. They are LZW-compressed (`compress` format) tar archives. Python's `tarfile` module handles some variants but not all — specifically, some archives may have a different inner structure (flat tar vs. nested tar) or use a compression variant that differs between years. The existing script assumes `outer tar → inner tar → CRI_*.xml`, but a small percentage of archives deviate from this (e.g., `AAA_*.xml` only, no CRI, or flat structure with XML at root level).

**Why it happens:**
DILA does not document the archive structure formally. The format has been reverse-engineered by the community. Historical archives (pre-2019) use a different layout than current ones, and edge cases (extraordinary sessions, committee hearings) may use non-standard naming.

**How to avoid:**
- Do not assume the double-tar structure — probe the archive structure first and handle both flat and nested cases
- When `tarfile.open` fails, log the exact error and archive URL — do not silently skip
- Build a test suite against at least 5 archives from different years (2019, 2021, 2023, 2024, 2025) before scaling ingestion
- Add an integrity check: count of CRI files found per year should be stable; large deviations indicate format change

**Warning signs:**
- `No CRI XML found in ...` warnings appearing for more than 5% of archives in a year
- `tarfile.TarError` exceptions with "not a gzip file" (LZW not supported natively — needs `unlzw3`)
- Ingestion stats show zero interventions for an entire year

**Phase to address:** Ingestion foundation phase — validate archive structure against multiple years before building the full pipeline.

---

### Pitfall 5: Cross-Type FTS Returns Noise at Scale (200K+ Records)

**What goes wrong:**
The current FTS index `to_tsvector('french', content)` on `interventions` works for single-table search. When extending to cover amendments, questions, and bills via `UNION ALL` across 4-5 tables, query performance degrades non-linearly: each table requires its own sequential GIN scan, and ranking across different content types becomes meaningless (a 3-word amendment matching all terms ranks equal to a 2000-word debate speech).

GIN indexes do not store weight labels — any `ts_rank` using weights requires a table recheck (row fetch after index scan), multiplying I/O at 200K+ rows.

**Why it happens:**
Developers add FTS to each table independently, then try to union them at query time. This works in development with < 1000 rows but degrades in production. The `to_tsvector()` call in an index definition (functional index) is not stored as a column — it is recomputed for ranking, defeating the index for scoring.

**How to avoid:**
- Use a persistent `search_vector tsvector` column on each table, populated by trigger on INSERT/UPDATE
- For cross-type search: use a single `search_index` materialized view or a dedicated search table with `(record_type, record_id, search_vector, weight_class)` — refresh on schedule
- Use `setweight` to differentiate content types before ranking (amendment titles get 'A', full text gets 'C')
- Benchmark with `EXPLAIN ANALYZE` on realistic data size (use `pg_restore` from a prod dump) before declaring FTS "done"

**Warning signs:**
- FTS queries take > 200ms in dev with < 1000 rows (means no index being used)
- Search results include short procedural items ranked above substantive content
- Adding a new document type requires touching the FTS query in multiple places

**Phase to address:** FTS phase — design the search index schema before writing the first cross-type query.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `drizzle-kit push` in staging | Faster schema iteration | Bypasses migration log, risks data loss on prod | Never on shared environments |
| Name-only deputy matching | Works without pre-built cross-reference | Silent false positives accumulate, corrupt FK links | Never as primary strategy |
| `to_tsvector()` functional index without stored column | No trigger needed | No ranking, row recheck at scale | Dev/prototype only |
| Single-process sequential ingestion | Simple to implement | 200K records takes hours, no resume on failure | Initial seed only; add checkpointing before scale |
| Hard-coding legislature=17 in ingestion scripts | Works now | Scripts break at next legislature transition | Acceptable for MVP; add `LEGISLATURE` config var |
| Monorepo without a shared `db` package | Less refactoring now | Ingestion scripts and Nuxt server share no types, drift over time | Only if ingestion remains Python-only permanently |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| DILA open data | Polling the directory listing by scraping `href` attributes in HTML | Parse the listing HTML defensively — structure is not formal, can change; add fallback to known filename pattern `AN_YYYYNNN.taz` |
| AN open data XML | Assuming `PA` prefix on all actor IDs | Verify: some actor files use `PO` for organizations, not deputies — filter on `<typeLibelle>` = "Député" |
| nosdeputes.fr API | Calling `/seances/json` for legislature 17 | API returns empty for legislature 17 as of 2026-03 (confirmed in existing code comment) — use DILA as primary source |
| Tricoteuses data | Treating cleaned JSON as canonical | Tricoteuses is a community project with lag; some fields (group names, constituency) may be stale by weeks |
| Sénat data | Assuming Sénat IDs can cross-reference AN deputies | Sénat senators and AN deputies are different people; only cross-link via bill/law reference numbers, never by person ID |
| PostgreSQL on LXC | Opening port 5432 directly on LXC IP | Use Proxmox internal network + UNIX socket or stunnel; never expose 5432 to the internet even on a "private" network |
| Drizzle migrate | Running `drizzle-kit migrate` without testing on a DB snapshot | Always test on a restored snapshot first; `__drizzle_migrations` entries cannot be easily rolled back |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| INSERT row-by-row in ingestion loop | Ingestion of 1000 debates takes > 10 minutes | Use `COPY` or batch INSERT (1000 rows/transaction) | ~10K rows |
| GIN index rebuild on large text column | `CREATE INDEX` blocks table for minutes | Use `CREATE INDEX CONCURRENTLY` in a separate migration | > 50K rows |
| Loading all deputies into memory for name matching | Acceptable at 577 deputies; breaks at 577 deputies + all senators + historical | Current design (dict cache) is fine for deputies-only; add pagination if extending to all actors | > 5K actors |
| Fetching taz files synchronously, one at a time | Full historical ingest takes hours | Add async batch fetching (httpx async client, 5 concurrent) with rate limiting | > 100 files |
| UNION ALL across 5 FTS-indexed tables per search request | Search latency > 500ms | Build unified search index (materialized view or dedicated table) | > 50K total records |
| Recomputing `to_tsvector` at query time for ranking | Fast for exact match, slow for ranked results | Store `search_vector` column, update via trigger | > 10K rows with ranking |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing PostgreSQL port 5432 on LXC network interface | Direct DB access from any host on the Proxmox bridge network | Bind PostgreSQL to `127.0.0.1` only; app connects via UNIX socket or SSH tunnel |
| Storing `DATABASE_URL` with password in `.env` committed to git | Credential leak | Add `.env` to `.gitignore` at monorepo root AND in each package; use `.env.example` instead |
| No auth on ingestion script runner (if exposed as API endpoint) | Unauthorized triggering of expensive re-ingestion | Ingestion scripts are CLI-only; never expose as HTTP endpoint without auth |
| Using `trust` auth in `pg_hba.conf` for LXC-to-LXC connections | Any process on the Proxmox host can connect without password | Use `scram-sha-256` for all non-socket connections, even internal ones |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing "aucun résultat" when FTS query is empty or too short | User confusion — they searched and got nothing | Validate minimum query length (3 chars) client-side; show helpful message not empty state |
| Mixing result types in search without type labels | User cannot tell if a result is a debate, an amendment, or a question | Always show `type_badge` (Débat, Amendement, Question) prominently on each result card |
| Displaying raw amendment numbering (e.g., `AN5L17BTC0631P0D1N000160`) as title | Opaque for non-experts | Always derive human-readable title: "Amendement n°160 — article X du PLF 2025" |
| Paginating ingestion errors to the user | Users see "données incomplètes" with no context | Distinguish between "data not yet ingested" and "data source error" in UI messaging |
| Cross-legislature data mixing in search results | 16th legislature results appearing alongside 17th | Always default-filter by current legislature (17); make legislature filter explicit and visible |

---

## "Looks Done But Isn't" Checklist

- [ ] **Monorepo migration:** Shared packages build correctly AND Nuxt `nuxt build` succeeds (not just `nuxt dev`)
- [ ] **Schema migration:** All migrations run on a fresh DB AND on a DB snapshot with existing prod data — both must succeed
- [ ] **Deputy resolution:** Match rate logged per ingestion run; unmatched deputies stored in `ingestion_warnings`, not silently discarded
- [ ] **TAZ ingestion:** Tested against archives from at least 3 different years, not just the latest
- [ ] **FTS:** `EXPLAIN ANALYZE` confirms GIN index is used (not `Seq Scan`) on realistic data volume
- [ ] **Cross-type search:** Ranking across document types validated manually — short amendments should not outrank full debate speeches
- [ ] **LXC PostgreSQL:** `pg_hba.conf` does not use `trust`; port 5432 not reachable from outside the Proxmox internal bridge
- [ ] **Incremental ingestion:** Script can be re-run without duplicating existing records (idempotence tested)
- [ ] **Legislature filter:** All queries and search results default to legislature=17 unless explicitly overridden

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Monorepo migration broke Nuxt build | MEDIUM | Revert to single-app structure; migrate shared code back into `server/`; re-attempt monorepo with explicit `build.transpile` |
| Bad migration corrupted existing data | HIGH | Restore from pre-migration DB snapshot; split migration into smaller files; re-run |
| Deputy ID corruption (false positive name matches) | HIGH | Truncate affected junction tables; rebuild from source files using ID-first matching only; audit via `SELECT deputy_id, COUNT(DISTINCT political_group)` |
| FTS index not used at scale | MEDIUM | `DROP INDEX` functional index; add stored `search_vector` column; create proper GIN index; update triggers |
| nosdeputes.fr API returns empty (already documented) | LOW | Already handled in existing code — fall back to DILA; no recovery needed |
| Sénat IDs accidentally linked to AN deputies | MEDIUM | Add source validation constraint; clean up via `DELETE FROM` where source='senat' AND table='interventions' |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Monorepo Nuxt module resolution | Phase: Monorepo foundation | `pnpm run build` succeeds from monorepo root |
| Schema migration locks / data loss | Phase: Schema design | Migration tested on prod snapshot; no `push` in CI |
| Deputy ID mismatch (silent corruption) | Phase: Cross-reference table (before non-DILA ingestion) | Match rate > 80% by ID (not name) for all sources |
| TAZ archive format variations | Phase: Ingestion foundation | Zero `No CRI XML found` warnings on historical archives |
| Cross-type FTS noise at scale | Phase: FTS design | `EXPLAIN ANALYZE` shows GIN index scan, not Seq Scan |
| LXC PostgreSQL exposure | Phase: Infrastructure provisioning | `nmap -p 5432 <proxmox-bridge-ip>` returns filtered |
| Legislature data mixing | Phase: API layer design | All queries have `WHERE legislature = $1` enforced |

---

## Sources

- [data.assemblee-nationale.fr — FAQ and format documentation](https://data.assemblee-nationale.fr/foire-aux-questions)
- [DILA Python TAZ parsing community thread](https://www.developpez.net/forums/d2088566/autres-langages/python/general-python/lire-archive-taz-url/)
- [nosdeputes.fr API documentation — legislature 17 empty data confirmed](https://github.com/regardscitoyens/nosdeputes.fr/blob/master/doc/api.md)
- [PostgreSQL GIN index internals](https://pganalyze.com/blog/gin-index)
- [PostgreSQL COPY vs INSERT performance benchmarks](https://www.tigerdata.com/learn/testing-postgres-ingest-insert-vs-batch-insert-vs-copy)
- [Multi-table FTS with materialized views](https://thoughtbot.com/blog/implementing-multi-table-full-text-search-with-postgres)
- [Persistent tsvector columns for FTS performance](https://danielabaron.me/blog/speed-up-pg-fts-with-persistent-ts-vectors/)
- [Drizzle zero-downtime migrations](https://ecosire.com/blog/drizzle-migrations-zero-downtime)
- [Drizzle migration discussion — push vs migrate](https://github.com/drizzle-team/drizzle-orm/discussions/2624)
- [Nuxt pnpm monorepo path resolution issue](https://github.com/nuxt/nuxt/issues/33826)
- [Proxmox LXC PostgreSQL authentication issues](https://github.com/community-scripts/ProxmoxVE/issues/343)
- [Tricoteuses GitLab — cleaned AN data](https://git.en-root.org/tricoteuses)
- Existing Poliscope codebase: `scripts/ingest_debates.py` (first-hand evidence of DILA format, name matching, nosdeputes empty API)

---
*Pitfalls research for: Poliscope — Universal parliamentary database expansion*
*Researched: 2026-03-28*
