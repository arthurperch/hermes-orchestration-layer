# Stage 2 — Benchmark Baseline

[← back to roadmap](../ROADMAP.md)

**Goal:** measure the system before tuning it. Without a baseline you can't prove
orchestration (or compression) helps.

**Accent:** 🟨 amber · **Status:** queued

---

## Tasks

- [ ] `benchmark_logs/` writes one JSON record per task, matching `benchmark-schema.json`
- [ ] Run the difficulty ladder: ≥ 20 tasks each at trivial (0–3), medium (4–6), hard (7–10)
- [ ] Run them through the baseline strategies (`single_cheap`, `single_strong`,
      `fixed_route`, `full_cascade`) — same tasks across strategies
- [ ] Compute the metrics table: `quality_per_dollar`, `quality_pass_rate`,
      `complexity_estimation_error`, `escalation_rate`, latency

## Files involved

`benchmark-schema.json` · `benchmark-template.md` (protocol + quality rubric)

## Done when

- You have a metrics table per strategy per difficulty.
- `quality_per_dollar` and `quality_pass_rate` are recorded for the baseline.
- You can answer: does `full_cascade` beat `single_strong` on cost while holding quality?

## Notes

Define the quality rubric per task type up front (see `benchmark-template.md`) so
`quality_score` isn't a vibe. Compression stays OFF for this whole stage — baseline
must be clean.
