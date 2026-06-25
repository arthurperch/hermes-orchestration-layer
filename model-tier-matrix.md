# Model Tier Matrix

Every model in the pool, ranked by role, cost, reasoning depth, speed, and
fallback order.

> ⚠️ **Prices and benchmark scores move weekly.** The numbers below were gathered
> mid-2026 from public leaderboards and vendor pages and are **indicative only**.
> Benchmark scores also depend heavily on the scaffold (e.g. a model + Claude Code
> scores differently than the same model + a custom harness). **Re-verify on your
> own representative tasks before trusting any of this for routing decisions.**

Pricing is **USD per 1M tokens (input / output)** unless noted.

---

## Planner tier (Tier 1) — reasoning + decomposition matters most

| Rank | Model | Price (in/out) | Reasoning | Speed | Why here |
|------|-------|----------------|-----------|-------|----------|
| Primary | **GLM-5.2** | ~1/6 of GPT-5.5; ~$18/mo plan or token-based via Z.ai | Very strong (AIME ~99, GPQA-D ~91) | Fast (~145 tok/s) | Top-4 overall on public boards, 1M context, cheap. Best planning reasoning per dollar. Weakness: peak-hour outages → needs fallback. |
| Fallback 1 | **DeepSeek V4 Flash** | ~$0.14 / $0.28 | Strong | Fast | Independent provider from GLM (different outage windows), extremely cheap. |
| Fallback 2 | **Claude Haiku 4.5** | $1 / $5 | Good | Very fast | Different cloud/region entirely → uncorrelated uptime. Pricier but reliable last resort for planning. |

**Routing note:** GLM and DeepSeek both crash under load at different times — that's
the whole reason they're chained. Haiku is the "both-Chinese-providers-are-down" net.

---

## Executor tier (Tier 2) — routed by complexity score

### Simple (0–3) — cheap + fast, accuracy 70–90% is fine

| Model | Price (in/out) | Best for | Notes |
|-------|----------------|----------|-------|
| **DeepSeek V3 / V3.2** | ~$0.14 / $0.28 | bulk generation, straightforward rewrites, classification | Cheapest high-quality option. Watch Gate F — can loop and inflate per-task cost. |
| **Gemini 3 Flash** | ~$0.50 / $3.00 | fast code completion, simple transforms | ~78% SWE-bench, notably beats Gemini 3 Pro on that bench. Good cheap executor. |
| **Gemini 3.1 Flash-Lite** | ~$0.10 / $0.40 | highest-volume, lowest-stakes | Among cheapest proprietary APIs. Quality varies — keep to trivial work. |

### Medium (4–6) — production work, quality must hold

| Model | Price (in/out) | Best for | Notes |
|-------|----------------|----------|-------|
| **Claude Sonnet 4.6** | $3 / $15 | production code, maintainable output, instruction-following | The reliability workhorse. ~80% everyday-coding. Strong on careful interpretation. |
| **GLM-5.2** | see planner row | code gen at scale, long-context "read whole codebase" | If reliability stabilizes, promote into this tier as a cheaper Sonnet alternative. |

### Hard (7–10) — judgment calls, architecture, high blast radius

| Model | Price (in/out) | Best for | Notes |
|-------|----------------|----------|-------|
| **Claude Opus 4.8** | ~$5 / $25 | complex multi-step reasoning, high-stakes decisions, long-context coherence | Reserve for work that genuinely needs it. Also the Tier-0 Architect model. |
| **GPT-5.4** | ~$2.50 / $15 | collaborative debug partner, omnimodal | Brought in via Gate G when another executor is stuck — reasons on the blocker. |
| **DeepSeek V4 Pro** | cheaper token bill | raw coding execution | Highest LiveCodeBench (~93.5) + Codeforces (~3206), but looping can raise *per-task* cost despite low per-token price. Benchmark before trusting. |

---

## Verifier tier (Tier 3)

| Model | Price (in/out) | Role |
|-------|----------------|------|
| **DeepSeek V3** | ~$0.14 / $0.28 | cheap objective-result review, second-opinion on low-stakes |
| **Claude Sonnet 4.6** | $3 / $15 | second-opinion review on high-stakes output (Gate H) |

---

## Architect tier (Tier 0) — not in hot path

| Model | Price (in/out) | Role |
|-------|----------------|------|
| **Claude Opus 4.8** | ~$5 / $25 | reads benchmark logs, rewrites routing rules. Expensive but runs rarely, so cost is amortized. |
| Fallback | GPT-5.4 / DeepSeek V4 Pro | — |

---

## Failover (any tier)

| Provider | Role | Why last |
|----------|------|----------|
| **OpenRouter** | catch-all access to whatever is available | Convenience markup makes it costlier — only worth it when primary + secondary are both down. |

---

## On the horizon (evaluate later, don't integrate yet)

| Option | What it is | Why wait |
|--------|------------|----------|
| **Sakana Fugu / Fugu Ultra** | A *learned* orchestrator (~0.6B TRINITY coordinator + RL Conductor) that itself routes across GPT/Claude/Gemini, assigning Thinker/Worker/Verifier roles. Fugu Ultra ~$5/$30. | It's a black box — you can't inject your own cost ceilings or see why it routed. It optimizes quality+latency, **not** explicit cost budgets. Test as an *executor* on 20–50 real tasks once your own routing is dialed in. |

---

## Decision heuristics (the short version)

- **Don't run Opus on simple tasks.** That's the entire reason this matrix exists.
- **Chain across independent providers**, not just independent models — outages cluster by provider.
- **Per-token cheap ≠ per-task cheap.** A looping cheap model can cost more than one clean Sonnet pass. Measure per-task.
- **Promote models as they improve.** GLM-5.2 starts as planner; if its uptime stabilizes, it earns an executor slot too.
