# Stage 3 — Gates & Micro-Orchestrator

[← back to roadmap](../ROADMAP.md)

**Goal:** the escalation logic. Detect uncertainty/errors, do one local fix or
escalate, collaborate only when stuck, gate high-stakes work behind a human.

**Accent:** 🟪 violet · **Status:** queued

---

## Tasks

- [ ] **Gate C** — output confidence (model self-flags doubt → escalate)
- [ ] **Gate D** — error detection (lint / type-check / schema; fail → fix or escalate)
- [ ] **Gate F** — output sanity (length plausible? catches looping/giving-up)
- [ ] **Gate E** — retry budget (max 2 attempts, then up a tier)
- [ ] **Micro-orchestrator** — one local reroute OR one callback to planner, hard-capped
- [ ] **Gate G** — collaborative debug (second model on the blocker only, when stuck)
- [ ] **Gate H** — human-in-the-loop on high-stakes; pause/resume cleanly
- [ ] Re-run the Stage 2 baseline under full orchestration → compare `quality_per_dollar`

## Files involved

`rules-and-gates.md` (Gates C–H) · `architecture-schema.json` (tier_2_5, tier_3) ·
`benchmark-schema.json` (escalations, retries fields)

## Done when

- A failing executor triggers exactly one local fix, then escalates — no ping-pong.
- A high-stakes task pauses for human approval and resumes after it.
- Full-orchestration run beats the bare baseline on quality-per-dollar (or you learn
  where it doesn't and route those task types down).

## Notes

`max_local_reroutes = 1`, `max_planner_callbacks = 1`. Collaboration (Gate G) is the
most expensive path — it must be earned by an executor's own stuck signal, never
automatic.
