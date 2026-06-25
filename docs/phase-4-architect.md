# Stage 4 — Architect Self-Tuning

[← back to roadmap](../ROADMAP.md)

**Goal:** the system reads its own benchmark logs, finds where routing was wrong,
proposes one change at a time, sandbox-tests it, and promotes only what improves
quality-per-dollar without dropping the quality floor.

**Accent:** 🟩 emerald · **Status:** queued

---

## Tasks

- [ ] Feed benchmark logs into `self-tuning-logic.py` (`ingest` → split tune/holdout)
- [ ] `diagnose` mis-routing per (task_type, complexity bucket)
- [ ] `propose_changes` — Architect model emits a structured diff with evidence
- [ ] `sandbox_test` each change on the **held-out** set; `decide` enforces the floor
- [ ] `promote` winners via PR against the rule files

## Files involved

`self-tuning-logic.py` · `benchmark-schema.json` · `rules-and-gates.md` ·
`skill-definitions.json`

## Done when

- The Architect runs (nightly or on-demand), proposes ≥ 1 evidence-backed change.
- A proposed change is sandbox-tested and either promoted or rejected with a logged reason.
- No change that drops `quality_pass_rate` below floor is ever promoted.

## Notes

One change at a time, validated on data it did NOT tune on — that's what lets you
attribute a win or regression to a specific edit. Rejected proposals are kept; a
pattern of rejections is a signal a task type needs a human rethink.
