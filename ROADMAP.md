# Build Roadmap

Where the Hermes orchestration build stands, by stage. Each stage links to its
full spec in `docs/`. For the visual version (color-coded stages, live progress
bars), open **`roadmap.html`**.

> Status keys: ✅ done · ◐ in progress · ◯ queued · ⛔ blocked
> Update the percentages as you go — this is a living tracker.

**Overall:** `███░░░░░░░░░░░░░░░░░` 15% — MCP server + backend built, pushed, tests green.

---

## 🟦 Stage 1 — Foundation & Planner
`████████████░░░░░░░░` 60% · [full spec →](docs/phase-1-planner.md)

The planner reads the architecture, scores complexity, and routes. Nothing works
until this does.

- ✅ Architecture schema + provider/key resolution written
- ✅ `profiles.json` toggle (default / orchestration / openrouter_only)
- ✅ `mcp-requirements.txt` installed — all deps confirmed present
- ✅ `mcp-test.py` passes — 8/8 green (mock backend)
- ✅ `orchestration_backend.py` built — FastAPI, all 5 endpoints (`/v1/plan`, `/v1/execute`, `/v1/benchmark`, `/v1/profile`, `/v1/status`), Gates A/B/C/D/H implemented, tier routing per `rules-and-gates.md`
- ✅ `mcp-test.py` passes against real backend — 8/8 green (live localhost)
- ✅ Repo pushed to github.com/arthurperch/hermes-orchestration-layer
- ◐ `hermes_mcp_orchestration.py --dev` server check (orchestration_backend on localhost)
- ◐ LiteLLM proxy stood up + keys in `.env` (`SECRETS_SETUP.md`)
- ◯ Gate A — context sufficiency (planner asks human until satisfied)
- ◯ Gate B — complexity scorer (GLM-5.2 emits 0–10 + logs it)
- ◯ Fallback chain verified (GLM → DeepSeek V4 Flash → Haiku → OpenRouter)

---

## 🟨 Stage 2 — Benchmark Baseline
`░░░░░░░░░░░░░░░░░░░░` 0% · [full spec →](docs/phase-2-benchmark.md)

Measure before tuning. No baseline = no way to know if orchestration helps.

- ◯ `benchmark_logs/` writing one record per task (`benchmark-schema.json`)
- ◯ Run the difficulty ladder: 20+ trivial / medium / hard tasks
- ◯ Compute metrics: quality_per_dollar, pass_rate, complexity_error
- ◯ Lock baseline numbers for comparison

---

## 🟪 Stage 3 — Gates & Micro-Orchestrator
`░░░░░░░░░░░░░░░░░░░░` 0% · [full spec →](docs/phase-3-gates.md)

The escalation logic — confidence, errors, retries, collaboration, human gates.

- ◯ Gates C / D / F (confidence, lint+type, output sanity)
- ◯ Gate E retry budget + micro-orchestrator (one local fix or escalate)
- ◯ Gate G collaborative debug (only when an executor is stuck)
- ◯ Gate H human-in-the-loop on high-stakes
- ◯ Re-run baseline under full orchestration → compare quality_per_dollar

---

## 🟩 Stage 4 — Architect Self-Tuning
`░░░░░░░░░░░░░░░░░░░░` 0% · [full spec →](docs/phase-4-architect.md)

The system reads its own benchmark logs and rewrites its routing rules.

- ◯ Feed logs to `self-tuning-logic.py`
- ◯ Diagnose mis-routing, propose one change at a time
- ◯ Sandbox-test on a held-out set (hard quality floor)
- ◯ Promote winning changes via PR

---

## 🟥 Stage 5 — Compression A/B *(optional)*
`░░░░░░░░░░░░░░░░░░░░` 0% · [full spec →](docs/phase-5-compression.md)

Token savings per layer — but only where it doesn't cost quality.

- ◯ Keep compression OFF; capture baseline first
- ◯ A/B one layer at a time (start with `handoff` lossless)
- ◯ Keep only where quality_delta ≥ 0 AND tokens_saved > 0

---

## 🟦 Stage 6 — Shared Controlplane Dashboard
`░░░░░░░░░░░░░░░░░░░░` 0% · [full spec →](docs/phase-6-dashboard.md)

The shared cockpit on **syndrax.app** — both you and Danish, live.

- ◯ FastAPI backend + WebSocket live feed
- ◯ React frontend on syndrax.app (split-view: logs + tabs)
- ◯ GitHub OAuth, locked to two users
- ◯ Profile editor + architecture viewer + benchmark table

---

## ✨ Future — Self-Teaching Planner Loop
`░░░░░░░░░░░░░░░░░░░░` planned · [full spec →](docs/future-self-teaching-loop.md)

Each tier feeds gaps back up; the planner grows its own skills and prunes dead ones.

- ✅ `feedback` fields in the benchmark schema
- ✅ `synthesize_skills` + `learned_questions` scaffolding in place
- ◯ Cluster recurring skill gaps → add planner questions
- ◯ Regenerate planner prompt from skills; prune skills that never fire
