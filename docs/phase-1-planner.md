# Stage 1 — Foundation & Planner

[← back to roadmap](../ROADMAP.md)

**Goal:** stand up the planner so Hermes reads the architecture, scores task
complexity, and routes to the right tier. Everything downstream depends on this.

**Accent:** 🟦 cyan · **Status:** in progress (~25%)

---

## Tasks

- [x] Architecture schema written (`architecture-schema.json`) incl. provider/key resolution
- [x] `profiles.json` toggle: `default` / `orchestration` / `openrouter_only`
- [ ] LiteLLM proxy running + keys in local `.env` — runbook in `SECRETS_SETUP.md`
- [ ] **Gate A — context sufficiency:** planner asks the human clarifying questions
      (cap 3 rounds) until it has enough to plan. Never sideways-asks another model.
- [ ] **Gate B — complexity scorer:** GLM-5.2 emits an integer 0–10 + justification,
      both logged. Score maps to tier per `rules-and-gates.md`.
- [ ] Fallback chain verified: GLM-5.2 → DeepSeek V4 Flash → Haiku 4.5 → OpenRouter

## Files involved

`architecture-schema.json` · `profiles.json` · `rules-and-gates.md` (Gates A, B) ·
`skill-definitions.json` (planner role) · `litellm-config.yaml` · `SECRETS_SETUP.md`

## Done when

- A trivial task ("generate a title") runs end-to-end: planner scores it ~1–2,
  routes to a simple executor, returns a result.
- Killing GLM mid-call cleanly bounces to DeepSeek V4 Flash with no manual step.
- Every run writes a complexity score + reasoning to the log.

## Notes

Keep LiteLLM's own routing OFF — the planner owns routing. Start in `openrouter_only`
profile if only the OpenRouter key is set, then move to `orchestration` as direct
keys land.
