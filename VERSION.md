# Versioning & Release

How builds are numbered, tested, shipped, and backed up. Keep this current — it's
the single place that answers "what's live and when did it change."

---

## Phases (every change goes through these)

```
BUILD  →  TEST  →  PUSH
 local     CI       deploy + tag + backup
```

1. **BUILD** — make changes locally; `docker compose up` to run it.
2. **TEST** — `python mcp-test.py` locally, then CI runs it on push. Red tests block the push.
3. **PUSH** — merge to `main`; CI builds the image and (when a deploy step is enabled)
   ships it; tag the release and snapshot a backup of the previous version.

---

## Version scheme

`vMAJOR.MINOR.PATCH` (semver).
- **MAJOR** — breaking change to the MCP tool contract or backend API.
- **MINOR** — new tool, new profile, new capability (backward-compatible).
- **PATCH** — fixes, doc/config tweaks.

Tag each release: `git tag v0.2.0 && git push --tags`.

---

## Backup before each push (keep the last version safe)

```bash
# snapshot the current main as a compressed backup before deploying the next version
PREV=$(git describe --tags --abbrev=0 2>/dev/null || echo v0.0.0)
git archive --format=zip -o "backups/${PREV}-backup.zip" HEAD
```

- Backups are **compressed** (zip) and kept under `backups/` (gitignored, or pushed to
  object storage — don't bloat the repo).
- Keep at least the **last 3** versions. Prune older ones.

---

## Changelog

### v0.2.0 — MCP layer (current)
- Added MCP server (`hermes_mcp_orchestration.py`): tools `orchestrate_plan`,
  `orchestrate_execute`, `benchmark_log`, `profile_switch`, `orchestration_status`.
- Added Docker + docker-compose, CI (`build-test-deploy`), `mcp-test.py`.
- Added bidirectional Hermes Desktop ↔ syndrax.app setup (`SYNDRAX_MCP_SETUP.md`).
- Date: _fill on tag_.

### v0.1.0 — Architecture & specs
- Tiers, gates A–H, model matrix, compression, benchmark + self-tuning, profiles,
  dashboard spec + design system, deployment, roadmap. Full docs + diagram.

---

## Release checklist

- [ ] `python mcp-test.py` green locally
- [ ] `docker build .` succeeds
- [ ] backup of previous tag written to `backups/`
- [ ] version bumped + changelog entry dated
- [ ] `git tag vX.Y.Z && git push --tags`
- [ ] CI green; deploy step (if enabled) succeeded
- [ ] Hermes Desktop on both machines still connects to the new version
