# Benchmark Template & Test Harness

How to measure the orchestration so the Architect (Tier 0) can improve it. The
record format is in `benchmark-schema.json`; this file is the **methodology** —
what to run, how to score quality, and how to read the results.

> The whole self-tuning system is only as good as this log. Garbage in → the
> Architect tunes toward the wrong thing. Be disciplined about logging every task.

---

## The lab protocol

Run the **same objective tasks** through **different orchestration strategies** and
compare cost, quality, and latency. Start easy, then escalate difficulty — a clean
benchmark on cost *and* performance.

### Strategies to compare (the baselines)

| Strategy | Description | Why test it |
|----------|-------------|-------------|
| `single_cheap` | DeepSeek V3 only, no orchestration | floor on cost, ceiling on failure rate |
| `single_strong` | Opus 4.8 only, no orchestration | ceiling on quality, ceiling on cost |
| `fixed_route` | static complexity→model map, no micro-orchestrator | does dynamic routing actually beat a static table? |
| `full_cascade` | the whole system: planner + micro-orchestrator + verifier + gates | the candidate. Does the extra latency buy enough quality/savings? |
| `learned_router` *(later)* | Sakana Fugu as executor | benchmark only after the above are dialed in |

### Task difficulty ladder

1. **Trivial (0–3):** generate a title, transform a CSV column, write a 10-line script.
2. **Medium (4–6):** refactor a module, integrate an API, build a spreadsheet model.
3. **Hard (7–10):** design a subsystem, debug a cross-file circular dependency,
   provision multi-server infra.

Run ≥ 20 tasks per difficulty per strategy (50+ is better). Same tasks across
strategies — that's what makes the comparison valid.

---

## Quality rubric (define per task type — don't hand-wave it)

`quality_score` is 0–1. Concrete rubrics so it's not a vibe:

| Task type | quality_score = 1.0 means | hard floor (`quality_thresholds_met`) |
|-----------|---------------------------|----------------------------------------|
| code_generation | passes all tests + lint + type-check, idiomatic | tests pass, no type errors |
| code_refactor | behavior preserved, structure improved, tests green | no behavior change, tests green |
| debugging | root cause fixed, regression test added | bug no longer reproduces |
| data_transformation | 100% rows correct vs gold | ≥ 99% rows correct |
| api_integration | works against live endpoint, errors handled | happy path works |
| document_generation | accurate, complete, well-structured | factually correct, no fabrication |
| automation_scripting | runs clean, idempotent, handles failure | runs without crashing |

**Rule:** for high-stakes task types, `quality_thresholds_met = false` should be
treated as a **failure regardless of cost savings.** That's the guardrail the whole
objective function depends on.

---

## What to compute from the log

Per strategy, per difficulty:

```
avg_cost_per_task          = mean(cost_usd)
quality_pass_rate          = % where quality_thresholds_met == true
avg_quality_score          = mean(quality_score)
quality_per_dollar         = avg_quality_score / avg_cost_per_task   ← the headline
avg_latency                = mean(latency_ms_total)
escalation_rate            = % tasks with ≥1 escalation
human_intervention_rate    = % tasks with human_touched == true
complexity_estimation_error= mean(abs(complexity_predicted - complexity_actual))
fallback_rate              = % tasks with fallbacks_triggered > 0
```

**The headline metric is `quality_per_dollar`, gated by `quality_pass_rate`.**
A strategy that's cheap but drops below your pass-rate floor is disqualified, no
matter how good its cost looks.

---

## Reading the results

- **`full_cascade` should beat `single_strong` on cost** while staying within a
  point or two on quality. If it doesn't, the orchestration overhead isn't paying
  for itself — simplify.
- **`full_cascade` should beat `single_cheap` on quality** by enough to justify the
  cost gap. If a bare cheap model is nearly as good, you're over-engineering that
  task type — route it down.
- **`fixed_route` vs `full_cascade`:** if dynamic routing + micro-orchestration
  barely beats a static table, the dynamic machinery may not be worth its latency
  for that workload. Keep it only where it earns its keep.
- **High `complexity_estimation_error`:** the planner is mis-scoring. Feed these
  cases to the Architect to recalibrate Gate B.

---

## Blank record (copy per task)

```json
{
  "task_id": "",
  "timestamp": "",
  "task_type": "",
  "task_summary": "",
  "complexity_predicted": 0,
  "complexity_actual": 0,
  "models_used": [],
  "cost_usd": 0.0,
  "latency_ms_total": 0,
  "escalations": [],
  "retries": 0,
  "fallbacks_triggered": 0,
  "human_touched": false,
  "collaborative_debug_used": false,
  "compression_used": { "planner": false, "executor": false, "micro_orch": false, "verifier": false, "architect": false, "handoff": false },
  "compression_ratio": 1.0,
  "tokens_saved": 0,
  "quality_score": 0.0,
  "quality_thresholds_met": false,
  "outcome": "",
  "notes": ""
}
```

---

## Compression A/B protocol

Compression (`compression-rules.md`) is benchmarked the same way as routing: prove
it helps before trusting it. Test **one layer at a time**, compression-off vs
compression-on, on the **same tasks**.

### How to run it

1. **Baseline first.** Run the difficulty ladder with `compression.enabled = false`
   everywhere. This is your reference for both cost and quality.
2. **One layer at a time.** Enable compression on a single layer (start with the
   safest: `handoff` or `executor` in `lossless`). Re-run the **same** tasks.
3. **Compare** the on vs off runs for that layer:

```
tokens_saved_pct   = mean(tokens_saved) / mean(original_tokens)   ← the benefit
cost_delta         = avg_cost(on) - avg_cost(off)                  ← should be negative
quality_delta      = quality_pass_rate(on) - quality_pass_rate(off)
latency_delta      = avg_latency(on) - avg_latency(off)            ← lossy adds a call
```

4. **Decision (hard floor applies):**
   - `quality_delta < 0` on that layer for a task type → **keep compression OFF
     there.** No token saving justifies a quality drop. The Architect enforces this
     automatically.
   - `quality_delta ≈ 0` and `cost_delta < 0` → **keep it on.** Free savings.
   - `tokens_saved` trending **negative** (compression call cost more than it saved)
     → layer is below the useful threshold for this workload → **off.**
5. **Then test lossy.** Only after lossless is proven safe on a layer, A/B the same
   layer in `lossy` mode. Lossy carries real risk — watch `quality_delta` closely,
   especially on `planner` (dropping a stated constraint) and `micro_orch` (dropping
   the stack detail that pinpoints a cause).

### What to watch per layer

| Layer | A/B priority | The specific risk to watch in `quality_delta` |
|-------|--------------|-----------------------------------------------|
| handoff (lossless) | test first — safest | next agent missing source it needed |
| executor (lossless) | test early | over-trimmed file the model needed in full |
| architect (lossy) | low risk | outlier pattern hidden in aggregates |
| planner (lossy) | higher risk | a constraint the user mentioned in passing |
| micro_orch (lossy) | higher risk | stack detail that pinpoints the failure |
| verifier | **don't** — keep off | summarized artifact hides the bug |

### Rule

Never enable compression on more than one new layer between benchmark runs. If you
flip three at once and quality drops, you can't tell which layer did it — same
discipline as the routing-change rule in `self-tuning-logic.py`.

---

## Cadence

1. Run the ladder against all baseline strategies → record everything.
2. Compute the metrics table above.
3. Hand the log to the Architect (`self-tuning-logic.py`).
4. Architect proposes rule/threshold changes → sandbox-test on a **held-out** task
   set (never the set it tuned on).
5. Promote only changes that improve `quality_per_dollar` without dropping
   `quality_pass_rate`. Re-baseline. Repeat.
