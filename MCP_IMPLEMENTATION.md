# MCP Implementation — Hermes Build Runbook

**Hermes: here's what we've got, in order. Do these top to bottom.** Everything else in
the repo is already built — this is the glue that lets Hermes Desktop (both machines)
and syndrax.app call the orchestration layer. Goal: quick, effective, easy.

> Read alongside `SYNDRAX_MCP_SETUP.md` (the config + bidirectional flow) and
> `hermes_mcp_orchestration.py` (the server scaffold you're finishing).

---

## What you're building (one line)

An MCP server that exposes the orchestration backend's tiers/gates as 5 tools, runnable
locally, in Docker, and deployed to syndrax.app — callable from Hermes Desktop and the
dashboard both.

The 5 tools (already scaffolded in `hermes_mcp_orchestration.py`):
`orchestrate_plan` · `orchestrate_execute` · `benchmark_log` · `profile_switch` ·
`orchestration_status`.

---

## Order of operations

### Phase 1 — Local (today)
- [ ] `pip install -r mcp-requirements.txt`
- [ ] `python mcp-test.py` → all green (uses a mock backend, no real models)
- [ ] Implement the real backend endpoints the server calls (the tier logic):
      `POST /v1/plan`, `POST /v1/execute`, `POST /v1/benchmark`, `POST /v1/profile`,
      `GET /v1/status`. Source of truth = `architecture-schema.json` + `rules-and-gates.md`.
- [ ] `python hermes_mcp_orchestration.py --dev` and hit it from Hermes Desktop (stdio
      config in `SYNDRAX_MCP_SETUP.md`, section A, with `SYNDRAX_ENV=dev`).

### Phase 2 — Docker (validate the container)
- [ ] `docker build -t syndrax-mcp:latest .`
- [ ] `docker compose up` (brings up the MCP server; uncomment LiteLLM if you want the
      model layer too)
- [ ] Re-run the Hermes Desktop check against the container.

### Phase 3 — Ship to syndrax.app
- [ ] `git push origin main` → CI (`.github/workflows/deploy.yml`) runs `mcp-test.py`,
      builds the image; enable one deploy step (Railway recommended) + add its secret.
- [ ] Point Hermes Desktop at prod (`SYNDRAX_ENV=prod`,
      `SYNDRAX_API_ENDPOINT=https://api.syndrax.app`).
- [ ] Wire the dashboard backend to run the server in SSE mode (`TRANSPORT=sse`).
- [ ] Tag the release + back up the previous version (`VERSION.md`).

---

## File checklist (what's in this repo for the MCP layer)

| File | Role |
|------|------|
| `hermes_mcp_orchestration.py` | the MCP server (finish the backend it calls) |
| `mcp-requirements.txt` | deps |
| `mcp-test.py` | smoke tests; CI gate |
| `Dockerfile` | container image |
| `docker-compose.yml` | local dev (caps included) |
| `.dockerignore` | lean images |
| `.github/workflows/deploy.yml` | build → test → deploy |
| `VERSION.md` | versioning + backups |
| `SYNDRAX_MCP_SETUP.md` | config + bidirectional flow + AWS cost guardrails |

---

## Success criteria

- [ ] `mcp-test.py` passes locally and in CI.
- [ ] Docker image builds; `docker compose up` runs clean.
- [ ] Hermes Desktop shows the tools (`@syndrax`) and `orchestrate_plan` returns a plan.
- [ ] `git push` → CI green → deployed.
- [ ] Prod endpoint works from Hermes Desktop; dashboard hits the same tools.
- [ ] Both machines (Oleg + Danish) use the same config → shared backend, shared
      benchmark log, synced profiles.

---

## Guardrails (don't skip)

- **Keys never in the repo.** Server reads `SYNDRAX_API_KEY` from env / Secrets Manager.
- **Confirm-before-run.** `orchestrate_execute` requires `confirm=true`; high-stakes
  still pauses at Gate H.
- **AWS cost caps.** If AWS is used, set the limits in `SYNDRAX_MCP_SETUP.md` §C — no
  unbounded autoscale, budget alarm on. Railway (flat-rate) is the default.
- **Backup before each push** (`VERSION.md`).

---

## If something breaks

- Server won't start → run with `--dev`, check `mcp-server.log`.
- Tools not visible in Hermes → restart Hermes Desktop, check its MCP logs.
- Backend timeouts → bump `timeout` in config; confirm `GET /v1/status` is up.
- CI red → read the Actions log, fix, re-push (deploy is blocked until green).
