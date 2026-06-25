# Future — Self-Teaching Planner Loop

[← back to roadmap](../ROADMAP.md)

**Goal:** close the loop so the system improves *itself*. Each tier reports gaps
back up; the Architect clusters them and grows the planner's skill set — and prunes
skills that never fire. The planner gets smarter over time instead of only having
its routing thresholds nudged.

**Accent:** ✨ gradient · **Status:** planned (scaffolding in place)

---

## The loop

```
executor/verifier hits a gap
        │  (logs feedback: bottleneck / missing_context / skill_gap / suggestion)
        ▼
Architect clusters recurring gaps  (synthesize_skills)
        │
        ▼
adds a planner question  ──►  skill-definitions.json: planner.learned_questions[]
        │                      (and prunes questions that never change an outcome)
        ▼
planner system prompt regenerated from skills
        │
        ▼
next similar task: planner asks the right question up front
```

## What's already scaffolded

- [x] `feedback` object in `benchmark-schema.json` (from_tier, bottleneck,
      missing_context, skill_gap, suggestion)
- [x] `synthesize_skills` + `apply_skill_proposals` in `self-tuning-logic.py`
- [x] `planner.learned_questions[]` slot in `skill-definitions.json`

## What's left to build

- [ ] Tiers actually populate `feedback` when they hit a gap (small change in Hermes)
- [ ] Clustering of recurring suggestions (threshold ≥ 3 → propose)
- [ ] Regenerate the planner's system prompt from `learned_questions`
- [ ] Prune logic: drop learned questions that never affected an outcome
- [ ] Sandbox-test each skill change before promoting (same floor as routing changes)

## Done when

- After a run of refactor tasks that kept hitting circular-import surprises, the
  planner *automatically* starts asking about cross-module dependencies up front —
  without anyone editing the prompt by hand.
- Dead skills disappear on their own, keeping the planner lean.

## Why this is "future"

It's complexity-creep before there's a baseline. Build Stages 1–4 first; the feedback
data those stages produce is the fuel this loop runs on. The hooks are already in the
files so it's a wiring job, not a redesign, when you're ready.
