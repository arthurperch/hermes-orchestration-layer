# Rules and Gates

Every decision point in the orchestration, spelled out. One gate per section:
**what fires it, what it checks, where it routes.** These are the rules the
Architect (Tier 0) is allowed to tune over time based on benchmark data.

> Governing principle: **escalate on signal of quality, never on cost alone.**
> You move work up a tier because something is *uncertain or broken*, not because
> a model is cheap.

---

## Gate A — Context Sufficiency

**Where:** Tier 1 (Planner), before anything else.
**Fires when:** every incoming task.
**Checks:** does the planner have enough information to commit to a plan without
guessing? Missing inputs, ambiguous scope, undefined success criteria.

**Routes:**
- Insufficient → ask the **human** one clarifying question, then loop. Do **not**
  route sideways to another model to "fill in the blanks" — that is how AI-to-AI
  hallucination loops start.
- Sufficient → proceed to Gate B.

**Rule:** the planner asks the human, not another AI, when context is thin. Cap
clarifying rounds (default 3) before forcing a best-effort plan with assumptions
logged.

---

## Gate B — Complexity → Tier

**Where:** Tier 1 (Planner).
**Fires when:** context is sufficient.
**Checks:** the planner emits an integer complexity score 0–10 based on:
- number of files / systems touched
- reasoning depth required (lookup vs. architecture)
- blast radius if wrong (cosmetic vs. data-corrupting)
- novelty (boilerplate vs. unsolved)

**Routes by score:**

| Score | Tier | Executors | Validation |
|-------|------|-----------|------------|
| 0–3 | simple | DeepSeek V3 / Gemini Flash | light (lint/type only) |
| 4–6 | medium | Sonnet 4.6 / GLM-5.2 | standard |
| 7–10 | hard | Opus 4.8 / GPT-5.4 collab | strict + human gate |

**Rule:** the score and its justification are **logged** so the Architect can later
compare predicted complexity against what actually happened.

---

## Gate C — Output Confidence

**Where:** Tier 2.5 (Micro-Orchestrator), after executor returns.
**Fires when:** any executor produces output.
**Checks:** did the model self-flag uncertainty? Caveats like "I'm unsure about
this edge case," hedged language, or an explicit confidence field below threshold
(default 0.7).

**Routes:**
- Low confidence → trigger Gate G (collaborative debug) or one local fixer shot.
- Confident → continue to Gate D.

**Rule:** a model flagging its own doubt is the cheapest, highest-value escalation
signal you have. Honor it.

---

## Gate D — Error Detection (objective)

**Where:** Tier 2.5 → Tier 3.
**Fires when:** output is code or structured data.
**Checks:** run it through objective tooling — linter, type-checker, schema
validator, a smoke test. No model opinion involved.

**Routes:**
- Fails syntax/type → do **not** spend more tokens reasoning about a broken
  result. Local fixer shot (Gate E budget), then escalate.
- Passes → continue.

**Rule:** objective checks are free and deterministic. Always run them before any
model-based review.

---

## Gate E — Retry Budget

**Where:** Tier 2.5.
**Fires when:** an executor fails Gate C or D.
**Checks:** how many attempts has this executor had on this task?

**Routes:**
- Attempts < budget (default 2) → one more local shot.
- Budget exhausted → escalate one tier. The cost of the failed attempts is already
  sunk, which *justifies* paying for the stronger model now.

**Rule:** hard cap. `max_local_reroutes = 1`, `max_planner_callbacks = 1`. Two
failures, then up — never ping-pong.

---

## Gate F — Output Sanity

**Where:** Tier 2.5.
**Fires when:** any executor returns.
**Checks:** is the output length plausible for the task? Suspiciously short for a
complex ask, or impossibly long and repetitive (a looping model)?

**Routes:**
- Implausible → flag as uncertain, treat like a Gate C failure.
- Plausible → continue.

**Rule:** catches the silent failure mode where a model "completes" but actually
gave up or looped. (DeepSeek's per-task cost can balloon here from looping — this
gate is the guard.)

---

## Gate G — Collaborative Debug Trigger

**Where:** Tier 2.5.
**Fires when:** an executor is **stuck** (low confidence + failed local fix) on a
**medium/hard** task.
**Checks:** is this worth a second expensive model, or just a cheap fixer?

**Routes:**
- Hard / high-stakes + stuck → bring in a second model (e.g. Sonnet stuck → GPT-5.4).
  They reason **together on the specific blocker only**, not the whole task. Reach a
  joint conclusion, then re-run Gates C/D/F.
- Simple → one local fixer shot instead. Do not pay for collaboration.

**Rule:** collaboration is **opt-in by the executor's own stuck signal**, never
automatic. This is the most expensive path; it must be earned. Cap the back-and-forth
(default 2 exchanges).

---

## Gate H — Human-in-the-Loop

**Where:** Tier 3 (Verifier), before commit.
**Fires when:** task is flagged high-stakes (irreversible action, account-level
risk, anything touching production data or money).
**Checks:** has a human approved this specific output?

**Routes:**
- High-stakes → **pause cleanly**, surface the output + the plan's reasoning, wait
  for human approval. Resume on approval.
- Low-stakes → auto-commit.

**Rule:** the system pauses and waits — it does not silently push high-stakes
output. Budget-limit failures also route here: never silently return a weak answer
after hitting a cap; summarize what was done, flag what needs review, hand to human.

---

## Cross-cutting rules

1. **Every plan and every escalation is logged** (see `benchmark-schema.json`).
   Unlogged decisions can't be tuned.
2. **Fallback chains bounce between independent providers** so one outage never
   stalls a tier. Failover (OpenRouter) is last because of its cost penalty.
3. **`code_is_truth`** — when generated code and a planning doc disagree, the
   working code wins. Docs are plans, not contracts.
4. **No platform-evasion logic lives here.** This layer routes work between models;
   it is domain-agnostic. Task-specific compliance belongs in the task's own spec,
   not the orchestrator.
5. **Thresholds in this file are defaults, not law.** The Architect proposes
   changes; changes are sandbox-tested against the benchmark before promotion.
