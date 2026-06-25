# Stage 5 — Compression A/B *(optional)*

[← back to roadmap](../ROADMAP.md)

**Goal:** cut token spend per layer with compression — but only where it doesn't
cost quality. Proven the same way as routing: A/B, one layer at a time.

**Accent:** 🟥 rose · **Status:** queued (do after baseline is solid)

---

## Tasks

- [ ] Confirm baseline ran with compression OFF everywhere
- [ ] Enable one layer, `lossless` first (start with `handoff`), re-run same tasks
- [ ] Compare on/off: `tokens_saved`, `cost_delta`, `quality_delta`, `latency_delta`
- [ ] Keep ON only where `quality_delta ≥ 0` AND `tokens_saved > 0`
- [ ] Only after lossless is proven safe on a layer, A/B that layer in `lossy`

## Files involved

`compression-rules.md` · `architecture-schema.json` (compression block) ·
`benchmark-schema.json` (compression_used, compression_ratio, tokens_saved) ·
`benchmark-template.md` (compression A/B protocol)

## Done when

- Each enabled layer has on-vs-off numbers proving it helps.
- Verifier compression stays OFF (correctness needs full fidelity).
- High-stakes tasks force compression off automatically (stakes override).

## Notes

Never flip more than one new layer between runs — if quality drops you won't know
which layer did it. `tokens_saved` is logged net of the compression call, so it can
go negative; a negative trend at a layer means disable it there.
