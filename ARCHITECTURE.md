# Hermes Orchestration Layer — Full Architecture

One consolidated document. Everything from the repo, in reading order. Copy it
whole, paste it anywhere, hand it to Hermes.

---

## 1. What this is

A self-tuning, multi-model orchestration system. It routes engineering and
knowledge-work tasks across a pool of LLMs **by complexity and cost**, with fallback
chains, validation gates, optional per-layer compression, and a benchmark-driven loop
that rewrites its own routing rules over time.

**Core bet:** keep the intelligence in the *routing layer*, not any single model.
Cheap models do cheap work; expensive models are reserved for work that needs them;
the system measures itself and improves.

**Objective function:**
> Minimize cost **subject to** quality thresholds. Not cost alone, not quality alone.
> A cheap answer that corrupts data costs more than a costly correct one. Cost is
> optimized only *within* per-task-type quality floors.

Primary metric: **quality_per_dollar**. Secondary: latency, escalation rate, human-
intervention rate.

---

## 2. The tiers

| Tier | Role | Job | Default model | Hot path? |
|------|------|-----|---------------|-----------|
| 0 | **Architect / Manager** | Reads benchmarks, rewrites routing rules | Opus 4.8 | No — runs occasionally |
| 1 | **Planner / Meta-Orchestrator** | Clarify → score complexity → emit plan | GLM-5.2 | Yes |
| 2 | **Executors / Workers** | Do the work, routed by complexity | DeepSeek V3 → Sonnet → Opus/GPT | Yes |
| 2.5 | **Micro-Orchestrator** | One local fix or escalate, no loops | Haiku 4.5 | On failure |
| 3 | **Verifier** | Validate output (lint, type, second opinion) | DeepSeek / Sonnet | Conditional |
| F | **Failover** | Catch-all when a provider is down | OpenRouter | On outage |

**Executor routing by complexity score:**

| Score | Band | Executors | Validation |
|-------|------|-----------|------------|
| 0–3 | simple | DeepSeek V3 / Gemini 3 Flash | light (lint/type) |
| 4–6 | medium | Sonnet 4.6 / GLM-5.2 | standard |
| 7–10 | hard | Opus 4.8 / GPT-5.4 (collab) | strict + human gate |

**Micro-Orchestrator limits:** `max_local_reroutes = 1`, `max_planner_callbacks = 1`.
Two failures, then escalate — never ping-pong.

---

## 3. Request lifecycle

```
You → Planner (GLM-5.2)
        ├─ Gate A: enough context? ─ no ─► ask YOU (not another AI), loop (cap 3)
        └─ yes ► Gate B: score complexity 0–10 ► emit machine-readable plan
                    │
                    ▼
              Executor (chosen by score)
                    │
              Micro-Orchestrator watches
                    ├─ Gates C/D/F pass ─► Verifier ─► Gate H (human if high-stakes) ─► commit
                    ├─ local-fixable fail ─► one fixer shot (Gate E budget)
                    └─ bigger than expected ─► callback to Planner → re-plan
```

Simple task → scored low → cheap executor → fast, no Opus, no waste.
Hard task → scored high → strong executor + collab + human gate → validated hard.

---

## 4. The 8 decision gates

Governing principle: **escalate on signal of quality, never on cost alone.**

- **Gate A — Context Sufficiency** (Planner). Not enough info → ask the *human* one
  question, loop (cap 3). Never sideways-ask another model (prevents AI-to-AI
  hallucination loops).
- **Gate B — Complexity → Tier** (Planner). Emit integer 0–10 + justification (both
  logged) from: files/systems touched, reasoning depth, blast radius if wrong, novelty.
- **Gate C — Output Confidence** (Micro-Orch). Model self-flags doubt / confidence
  below 0.7 → escalate (Gate G) or one local fix.
- **Gate D — Error Detection** (objective). Linter / type-check / schema / smoke test.
  Fail → don't reason about broken output; fix or escalate.
- **Gate E — Retry Budget**. < 2 attempts → one more local shot. Budget spent →
  escalate one tier (sunk cost justifies the stronger model).
- **Gate F — Output Sanity**. Length plausible for the task? Catches silent
  give-up/looping (where cheap-model per-task cost balloons).
- **Gate G — Collaborative Debug**. Only when an executor is *stuck* on a medium/hard
  task → pull a second model onto the **blocker only**, joint conclusion, re-run C/D/F.
  Most expensive path; must be earned by the executor's own stuck signal. Cap 2 exchanges.
- **Gate H — Human-in-the-Loop** (Verifier). High-stakes (irreversible, account-level,
  money, prod data) → pause cleanly, surface output + reasoning, wait for approval.
  Budget-cap failures also route here — never silently return a weak answer.

---

## 5. Model tier matrix (indicative — verify pricing, it moves weekly)

Pricing = USD per 1M tokens (in / out). Benchmark scores depend on scaffold.

**Planner:** GLM-5.2 (primary; strong reasoning, cheap, ~1M ctx, ~145 tok/s; weakness:
peak-hour outages) → DeepSeek V4 Flash (~$0.14/$0.28; independent provider) → Haiku 4.5
($1/$5; different cloud, uncorrelated uptime).

**Executors — simple:** DeepSeek V3 (~$0.14/$0.28; watch Gate F looping) · Gemini 3
Flash (~$0.50/$3) · Gemini 3.1 Flash-Lite (~$0.10/$0.40).
**medium:** Sonnet 4.6 ($3/$15; reliability workhorse) · GLM-5.2.
**hard:** Opus 4.8 (~$5/$25) · GPT-5.4 (~$2.50/$15; collab partner) · DeepSeek V4 Pro
(top LiveCodeBench but looping can raise per-task cost).

**Verifier:** DeepSeek V3 · Sonnet 4.6.  **Architect:** Opus 4.8 · GPT-5.4.
**Failover:** OpenRouter (markup → last resort; also the testing key).

Heuristics: don't run Opus on simple tasks · chain across *independent providers* (outages
cluster by provider) · per-token cheap ≠ per-task cheap (measure per-task) · promote
models as they improve (GLM starts as planner; earns an executor slot if uptime stabilizes).

---

## 6. Provider + API-key resolution

Calls go through a **self-hosted LiteLLM proxy** — one endpoint, many providers, a
**dumb pipe** (its own routing/fallback OFF; the Gates decide). Direct provider keys
first; anything uncovered or failing falls through to OpenRouter.

```
Hermes → LiteLLM proxy (VPS, routing OFF)
   ├─ ANTHROPIC_API_KEY  → Claude Opus / Sonnet / Haiku
   ├─ DEEPSEEK_API_KEY   → DeepSeek V3 / V4 Flash / V4 Pro
   ├─ ZAI_API_KEY        → GLM-5.2 (planner)
   ├─ OPENAI_API_KEY     → GPT-5.4
   ├─ GOOGLE_API_KEY     → Gemini 3 Flash / Flash-Lite
   └─ (any miss / failure) → OPENROUTER_API_KEY  (failover + testing)
```

**Resolution rule:** model → provider → that provider's key env var → read at runtime
from `.env` / AWS Secrets Manager. If the key is unset or the call fails/rate-limits,
LiteLLM routes the same request via OpenRouter. You never edit Hermes code to switch
providers — only `.env` keys and `profiles.json` chains. **5 direct keys + 1 OpenRouter
key** cover the whole system. Keys are referenced by env-var name only; real values
never touch the repo (`.env` is gitignored; prod uses AWS Secrets Manager).

---

## 7. Profiles (the on/off toggle)

Hermes reads `profiles.json` at the top of each cycle (git pull → load `active_profile`).
Flip one field to switch the whole system.

- **default** — bare Hermes, single model, no tiers/gates/logging. For trivial work.
- **orchestration** — full tier system, gates, benchmark logging, Architect loop.
- **openrouter_only** — everything via OpenRouter (one key); cheap to stand up for
  testing, swap to `orchestration` as direct keys land.

Edit in the GitHub web UI or the dashboard; both machines pick up the change next cycle.
Each profile can carry its own tier chains, models, gates, compression toggles, accent
color, and **its own memory store**.

---

## 8. Compression (optional, per-layer, stakes-aware)

Cut token spend on parts that don't need full fidelity — never letting saved tokens buy
a quality regression.

Modes: **lossless** (dedup, strip boilerplate, reference-by-ID, diff-not-whole-file;
safe to default on) · **lossy** (small model summarizes; opt-in per layer only) · **off**.

| Layer | Default | Mode | Risk to watch |
|-------|---------|------|---------------|
| planner | on | lossy | losing a stated constraint |
| executor | on | lossless | over-trimming a file it needs in full |
| micro_orch | on | lossy | dropping the stack detail that pinpoints the cause |
| verifier | **off** | off | summary hides the bug |
| architect | on | lossy | outlier hidden in aggregates |
| handoff | on | lossless | next agent missing source it needed |

Four rules: **lossless-first** · **stakes override** (high-stakes forces OFF at executor
+ verifier) · **verifier defaults OFF** · **benchmarked like everything else** (Architect
auto-disables compression at any layer where it drops quality_pass_rate). Floor:
`min_tokens_to_compress = 2000` (lossy costs a small-model call; `tokens_saved` is logged
net of it and can go negative).

---

## 9. Benchmark + self-tuning loop

**Log one record per task** (task_id, predicted vs actual complexity, models_used,
cost, quality_score, escalations, retries, fallbacks, compression fields, feedback).
This is the fuel.

**Lab protocol:** run the same tasks through strategies — `single_cheap`, `single_strong`,
`fixed_route`, `full_cascade` — across a difficulty ladder (≥20 tasks each at trivial /
medium / hard). Quality rubric defined per task type (not a vibe). Headline metric:
**quality_per_dollar, gated by quality_pass_rate**.

**Architect cycle** (`self-tuning-logic.py`, nightly or on-demand):
1. Ingest logs; split tune / held-out sets (never validate on what you tuned on).
2. Diagnose mis-routing per (task_type, complexity bucket).
3. Architect model proposes a structured diff with evidence.
4. Sandbox-test each change, one at a time, on the held-out set.
5. `decide()` — **hard gate**: never promote anything that drops quality_pass_rate
   below floor, no matter the savings. Promote real quality_per_dollar wins via PR.

---

## 10. Self-teaching planner loop (future, scaffolded)

Each tier reports gaps upward (`feedback`: bottleneck / missing_context / skill_gap /
suggestion). The Architect clusters recurring gaps and **grows the planner's skills** —
and prunes skills that never fire.

```
executor/verifier hits a gap → logs feedback
   → Architect clusters (synthesize_skills) → adds a planner question
   → skill-definitions.json: planner.learned_questions[]  (+ prune dead ones)
   → planner system prompt regenerated from skills
   → next similar task: planner asks the right question up front
```

Scaffolded now (feedback fields, `synthesize_skills`, `learned_questions` slot); wired
after Stages 1–4 produce the data it runs on. It's a wiring job, not a redesign.

---

## 11. The dashboard (syndrax.app)

A self-hosted, two-person Claude/GPT-style workspace wrapped around the orchestration
layer. Dark, glassy, sound-aware.

**Pages:** Login (Cloudflare Access) · Home/Cockpit (glassy chat + live feed + Plan
Console) · Plan Console · Profiles · Connections/Repos · Live Canvas · Sessions ·
Benchmark · Architecture · Settings.

**Key features:**
- **Glassy chat** — bold white text, multi-color collapsible code blocks, per-message
  model badge + cost chip.
- **Plan Console — confirm before run** — the orchestrator's plan shown visually (tier
  path, complexity, est. cost, gates that will fire) with color + motion; Confirm /
  Modify / Cancel; optional quick collaboration with a smarter model; Dry-run switch.
- **Profiles with per-profile memory** — clone the default template, customize, push;
  separate memory per profile; export/import as JSON.
- **Connections/Repos** — card grid; OAuth to GitHub / Vercel / Railway; push, deploy,
  add/remove visually.
- **Live Canvas + Element Inspector** — host HTML/image, live-edit, **click a DOM
  element to send its reference to the AI**.
- **Live orchestration feed** — both users watch the same decision stream (WebSocket).

**Extras:** spend HUD · diff viewer (per-hunk approve/reject) · provider health panel ·
⌘K command palette · run timeline · side-by-side model compare · notifications · audit
trail · accent-per-profile.

---

## 12. Design system + sound

Near-black base, **bold white** lettering, **transparent grey glass** cards over a slow-
drifting **hexagon field** with small white shapes. Color = information: each tier/profile
owns an accent (cyan / amber / violet / emerald / rose / blue). Type: Space Grotesk
(display) · Inter (body) · JetBrains Mono (code). Glassmorphism: backdrop-blur, 1px
hairline, inner top-highlight.

**Sound** (subtle, short, toggleable, off-by-default until opted in): neutral click =
soft tick · approve = rising two-note chime · return = quiet tick · blocked = low muted
thud · cancel = downward blip · result = gentle ping · AI↔AI handshake (serious/collab) =
distinct two-tone exchange · error = dull double thud. Each cue < ~400ms, capped volume,
debounced, mute honored. Reduced-motion disables all drift/pulse.

---

## 13. Deployment (syndrax.app, existing stack)

```
Namecheap (registrar) → Cloudflare (DNS + Access/Zero-Trust)
   syndrax.app      → Vercel  (new project; copy the syndrax.io connection profile)
   api.syndrax.app  → Railway (new service; same account/setup as Syndrax)
   prod secrets    → AWS Secrets Manager
```

DNS: CNAME `syndrax.app` → Vercel, `api.syndrax.app` → Railway (cleanest — platforms manage
certs/IPs; Cloudflare proxy adds WAF). Security: Cloudflare Access mirroring the **same
Zero-Trust policy as Syndrax Sync**, locked to two identities; GitHub OAuth inside for
per-user identity + connections. Deploy on push to `main` (same shape as syndrax.io).
Open question: fork an open-source agent dashboard as the base, or build custom (Cline's
open SDK is one verified base option).

---

## 14. Roadmap (stages)

1. **Foundation & Planner** 🟦 — read architecture, score complexity, route; LiteLLM +
   keys; Gates A/B; fallback chain. *(in progress)*
2. **Benchmark Baseline** 🟨 — log per task; run the ladder; compute metrics.
3. **Gates & Micro-Orchestrator** 🟪 — Gates C/D/E/F/G/H; re-run under full orchestration.
4. **Architect Self-Tuning** 🟩 — diagnose, propose one change, sandbox-test, promote.
5. **Compression A/B** 🟥 — off first; A/B one layer at a time; keep only where it helps.
6. **Shared Controlplane Dashboard** 🟦 — backend, Cloudflare login, glassy chat, Plan
   Console, profiles/repos/canvas, ship on syndrax.app.
✨ **Future — Self-Teaching Planner Loop** — feedback → grow/prune planner skills.

Compression stays OFF until baseline numbers exist. Build polish (hexagons, sounds,
glass) on top of a working core — don't front-load it.

---

## 15. File index

| File | Purpose |
|------|---------|
| `README.md` | entry point / index |
| `roadmap.html` · `ROADMAP.md` | visual + markdown build tracker |
| `DASHBOARD_SPEC.md` · `DESIGN_SYSTEM.md` · `dashboard-preview.html` | the dashboard |
| `architecture-schema.json` | machine-readable source of truth |
| `orchestration-flowchart.md` | Mermaid diagrams |
| `rules-and-gates.md` | the 8 gates |
| `compression-rules.md` | per-layer compression |
| `model-tier-matrix.md` | model rankings |
| `skill-definitions.json` | role → capability → task-type |
| `benchmark-schema.json` · `benchmark-template.md` | log format + lab protocol |
| `self-tuning-logic.py` | Architect loop + self-teaching planner |
| `profiles.json` · `litellm-config.yaml` · `.env.template` · `.gitignore` | runtime config |
| `API_KEY_HIERARCHY.md` · `SECRETS_SETUP.md` | keys |
| `DEPLOYMENT.md` | hosting on syndrax.app |
| `docs/` | one spec page per stage |

> Living document. `md_files_are_plans_not_contracts` · `code_is_truth`. Hermes can read
> these, propose edits, and open PRs.
