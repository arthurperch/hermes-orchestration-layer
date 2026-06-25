# Hermes Orchestration Layer

A self-tuning, multi-model orchestration system. It routes engineering and
knowledge-work tasks across a pool of LLMs by **complexity and cost**, with
fallback chains, validation gates, optional per-layer compression, and a
benchmark-driven loop that rewrites its own routing rules over time.

The core bet: keep the intelligence in the **routing layer**, not any single
model. Cheap models do cheap work; expensive models are reserved for work that
needs them; the system measures itself and improves.

> **New here? Read in this order:** this README → `roadmap.html` (where the build
> stands) → `architecture-schema.json` (the source of truth) → `SECRETS_SETUP.md`
> (the one manual step) → start building Stage 1.

---

## The objective

> **Minimize cost subject to quality thresholds.** Not cost alone, not quality
> alone. A cheap answer that corrupts data costs more than a costly correct one.
> Cost is optimized only *within* per-task-type quality floors.

---

## The tiers

| Tier | Role | Default model | Hot path? |
|------|------|---------------|-----------|
| 0 | **Architect** — rewrites routing from benchmarks | Opus 4.8 | no |
| 1 | **Planner** — scores complexity, routes | GLM-5.2 | yes |
| 2 | **Executors** — do the work, by complexity | DeepSeek V3 → Sonnet → Opus/GPT | yes |
| 2.5 | **Micro-Orchestrator** — one local fix or escalate | Haiku | on failure |
| 3 | **Verifier** — validates output | DeepSeek / Sonnet | conditional |
| F | **Failover** — catch-all | OpenRouter | on outage |

Calls go through a self-hosted **LiteLLM proxy** (its own routing OFF — the Gates
decide). Direct provider keys first; anything uncovered falls through to OpenRouter.

---

## File directory — what each thing is

### Start / operate
| File | What it's for |
|------|---------------|
| `README.md` | you are here — the index |
| `roadmap.html` | **visual build tracker** — color-coded stages, progress bars (open in browser) |
| `ROADMAP.md` | same roadmap, GitHub-rendered, links to `docs/` |
| `SECRETS_SETUP.md` | the one manual step: get keys → `.env` → start proxy → hand to Hermes |
| `API_KEY_HIERARCHY.md` | which key powers which model, and the failover order |
| `DEPLOYMENT.md` | hosting on syndrax.app — Namecheap/Cloudflare/Vercel/Railway/AWS |
| `ARCHITECTURE.md` | the whole system in one document (read or copy end-to-end) |
| `architecture-diagram.png` / `.svg` | the system as one labeled visual |

### Connect Hermes Desktop (the MCP layer)
| File | What it's for |
|------|---------------|
| `MCP_IMPLEMENTATION.md` | Hermes' ordered build runbook for the MCP server |
| `SYNDRAX_MCP_SETUP.md` | bidirectional Hermes Desktop ↔ syndrax.app + AWS cost guardrails |
| `hermes_mcp_orchestration.py` | the MCP server (5 tools wrapping the backend) |
| `mcp-requirements.txt` · `mcp-test.py` | deps + CI smoke tests |
| `Dockerfile` · `docker-compose.yml` · `.dockerignore` | containerize + local dev |
| `.github/workflows/deploy.yml` | build → test → deploy |
| `VERSION.md` | versioning, build phases, backups |

### The dashboard (Stage 6 vision)
| File | What it's for |
|------|---------------|
| `DASHBOARD_SPEC.md` | full product spec: pages, features, plan-console, profiles, repos, canvas |
| `DESIGN_SYSTEM.md` | dark/glass visual language + sound design map |
| `dashboard-preview.html` | **visual preview** — open in a browser, click buttons for sound |

### The architecture (source of truth)
| File | What it's for |
|------|---------------|
| `architecture-schema.json` | machine-readable: tiers, fallbacks, providers/keys, compression config |
| `orchestration-flowchart.md` | 4 Mermaid diagrams of the request lifecycle |
| `rules-and-gates.md` | the 8 decision gates A–H, one per section |
| `compression-rules.md` | per-layer compression toggles + safety rules |
| `model-tier-matrix.md` | every model ranked by cost/depth/speed (verify pricing) |
| `skill-definitions.json` | role → capability → task-type mapping (+ planner learned skills) |

### Measure & improve
| File | What it's for |
|------|---------------|
| `benchmark-schema.json` | the per-task log format (incl. compression + feedback fields) |
| `benchmark-template.md` | lab protocol, quality rubric, compression A/B testing |
| `self-tuning-logic.py` | the Architect loop + self-teaching planner logic |

### Config (runtime)
| File | What it's for |
|------|---------------|
| `profiles.json` | flip between bare Hermes / full orchestration / openrouter-only |
| `litellm-config.yaml` | the proxy config (env-var keys, routing OFF) |
| `.env.template` | copy to `.env`, fill keys locally (gitignored) |
| `.gitignore` | keeps secrets and local artifacts out of git |
| `docs/` | full spec for each build stage (linked from the roadmap) |

---

## How a request flows

```
You → Planner (GLM-5.2)
        ├─ enough context? ─ no ─► ask you, loop
        └─ yes ► score 0–10 ► route by complexity
                    │
              Executor (cheap → strong by score)
                    │
              Micro-Orchestrator watches
                    ├─ pass ─► Verifier ─► done
                    ├─ local-fixable fail ─► one fix
                    └─ bigger than expected ─► re-plan
```

Simple task → scored low → cheap executor → fast, no Opus, no waste.
Hard task → scored high → strong executor + collab + human gate → validated hard.

---

## Quick start

1. **Get the repo** (Danish pushes it; you pull it).
2. **Keys:** follow `SECRETS_SETUP.md` — copy `.env.template` → `.env`, paste keys,
   confirm `git check-ignore .env` prints `.env`.
3. **Proxy:** `litellm --config litellm-config.yaml`.
4. **Profile:** start in `openrouter_only` if you only have the OpenRouter key, else
   `orchestration`. Set in `profiles.json` / `HERMES_ACTIVE_PROFILE`.
5. **Build Stage 1** (`docs/phase-1-planner.md`): wire the planner, leave compression OFF.
6. **Track it** in `roadmap.html`; update the percentages as you go.

---

## Status

See `roadmap.html` for the live tracker. In short: **specs complete, Stage 1
(planner) starting.** Compression stays OFF until baseline numbers exist. The
self-teaching planner loop is scaffolded but built last.

> Living document: Hermes can read these files, propose edits, and open PRs.
> `md_files_are_plans_not_contracts` · `code_is_truth`.
