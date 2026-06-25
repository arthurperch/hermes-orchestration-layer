# Compression Rules

Optional, per-layer context compression. Toggle it on/off at each layer. The point
is to cut token spend on the parts of a request that don't need full fidelity —
without ever letting saved tokens buy a quality regression.

> Config block lives in `architecture-schema.json` → `compression`.
> Tracking fields live in `benchmark-schema.json` → `compression_used`,
> `compression_ratio`, `tokens_saved`. This file is the **why and how.**

---

## The core idea

Most of a request's tokens are low-value: repeated boilerplate, whole files when a
diff would do, long clarifying dialogues, raw logs. Compression squeezes those
before they hit the next model. But compression is **lossy at some layers**, so the
toggle is **stakes-aware**, not a dumb switch.

Two kinds:

| Mode | What it does | Risk | Default use |
|------|--------------|------|-------------|
| **lossless** | dedup, strip boilerplate, reference-by-ID, send a **diff** not the whole file | low — no meaning dropped | safe to default on |
| **lossy** | a small model **summarizes/distills** the context | real — detail is gone | opt-in per layer only |
| **off** | pass context through untouched | none | high-fidelity layers |

---

## The config (mirror of the schema block)

```yaml
compression:
  enabled: true            # master switch
  default_mode: lossless   # lossless | lossy | off
  min_tokens_to_compress: 2000   # below this, compressing is pure overhead
  stakes_override: true    # high-stakes forces OFF, ignores layer toggles
  layers:
    planner:    { enabled: true,  mode: lossy }     # squash clarifying Q&A into a tight spec
    executor:   { enabled: true,  mode: lossless }  # dedup, snippet+summary, diff-only
    micro_orch: { enabled: true,  mode: lossy }     # distill a failure to "what broke + why"
    verifier:   { enabled: false, mode: off }       # needs full fidelity — default OFF
    architect:  { enabled: true,  mode: lossy }     # feed aggregates, not raw logs
    handoff:    { enabled: true,  mode: lossless }  # inter-agent payloads: IDs + summaries
```

---

## The four rules that keep it safe

### Rule 1 — Lossless-first
Default to safe transforms (dedup, boilerplate strip, reference-by-ID, diff-only).
**Lossy summarization is opt-in per layer, never the global default.** If you're
unsure about a layer, leave it on `lossless` or `off`.

### Rule 2 — Stakes override wins
When a task is flagged high-stakes (Gate H — irreversible action, account-level
risk, money, production data), compression is **forced OFF at the executor and
verifier**, no matter what the layer toggles say. You never want a summarized
high-stakes edge case, or a diff-only view hiding the one line that matters.

### Rule 3 — Verifier defaults OFF
The verifier checks correctness. Give it the real artifact, not a summary. Turn
verifier compression on **only** for cheap, low-stakes review where a missed detail
costs nothing.

### Rule 4 — It's benchmarked like everything else
Every record logs `compression_used`, `compression_ratio`, `tokens_saved`. If
enabling compression at a layer drops `quality_pass_rate` for a task type, the
Architect **auto-disables it there**. Same hard floor as all routing: tokens saved
can never override a quality regression.

---

## Per-layer detail

| Layer | Default | Mode | What gets compressed | Watch for |
|-------|---------|------|----------------------|-----------|
| **planner** | on | lossy | the back-and-forth clarifying dialogue → one tight spec | losing a constraint the user stated in passing |
| **executor** | on | lossless | whole files → diffs; repeated context → reference-by-ID; long tool output → snippet + summary | over-trimming a file the model actually needs to see in full |
| **micro_orch** | on | lossy | a failure trace → "what broke + why" in 1–2 lines | dropping the stack detail that pinpoints the cause |
| **verifier** | **off** | off | nothing by default | only enable for low-stakes review |
| **architect** | on | lossy | raw benchmark rows → aggregates/trends | hiding an outlier pattern in the averages |
| **handoff** | on | lossless | inter-agent payloads → IDs + summaries, not raw blobs | passing a summary where the next agent needs the source |

---

## The honest caveat (why `min_tokens_to_compress` exists)

Lossy compression usually costs **an extra small-model call** to do the summarizing.
So it's only a net win when the downstream token savings beat that call cost. For
short contexts the math is negative — you'd spend a call to save fewer tokens than
the call cost. Hence the floor: **below `min_tokens_to_compress` (default 2000),
don't compress.** `tokens_saved` in the log is recorded **net of** the compression
call, so it can go negative — and a pattern of negative savings at a layer is a
signal for the Architect to disable it.

---

## Quick decision guide

- High-stakes task? → compression off where it matters, automatically. Don't think about it.
- Short context (< 2k tokens)? → off, not worth the call.
- Passing code between agents? → lossless (diff/reference), never lossy.
- Feeding the Architect months of logs? → lossy aggregates are perfect.
- Not sure? → `lossless` or `off`, and let the benchmark tell you if lossy is safe to turn on.
