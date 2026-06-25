# Design System — Controlplane Dashboard

The look, feel, and sound of syndrax.app. Dark, glassy, bold white type, animated
hexagon field, subtle audio feedback. Previewed in `dashboard-preview.html`.

---

## Direction

A calm, technical command surface — near-black depth, **bold white** lettering,
**transparent grey glass** cards floating over a slow-drifting **hexagon field**
with small white shapes. Color is used sparingly and meaningfully: each
orchestration tier (and each profile) owns an accent, so color *is* information.
Glass + motion + sound make approvals feel physical without getting loud.

---

## Color tokens

```
--bg-0:        #07090F   /* deepest base */
--bg-1:        #0B0E17   /* panel base */
--hex-line:    rgba(255,255,255,0.05)   /* hexagon field strokes */
--shape:       rgba(255,255,255,0.06)   /* drifting mini shapes */

--glass:       rgba(255,255,255,0.045)  /* card fill */
--glass-edge:  rgba(255,255,255,0.10)   /* 1px hairline border */
--glass-blur:  18px                     /* backdrop-filter blur */

--text:        #F5F8FF   /* bold white body */
--text-dim:    #9AA6BC
--text-mute:   #5B6679

/* tier / profile accents (color = meaning, reused from the orchestration layer) */
--ac-planner:  #22D3EE   /* cyan   */
--ac-bench:    #F5B544   /* amber  */
--ac-gates:    #A78BFA   /* violet */
--ac-architect:#34D399   /* emerald*/
--ac-compress: #FB7185   /* rose   */
--ac-dash:     #60A5FA   /* blue   */
--ok:          #34D399
--warn:        #F5B544
--blocked:     #F0556B
```

**Cards:** `background: var(--glass)` + `backdrop-filter: blur(var(--glass-blur))` +
`1px solid var(--glass-edge)` + soft inner top-highlight. Transparent grey, never solid.

---

## Typography

- **Display / headings:** a modern grotesk — **Space Grotesk** (or Geist) — heavy
  weight, tight tracking, **white**. This carries the "bold white, modern" feel.
- **Body / UI:** Inter, 400–500, `--text`.
- **Code / data:** JetBrains Mono. Code blocks are the "multi-font, multi-color"
  surface: syntax-highlighted, language-tagged, collapsible.
- Scale runs a touch larger than default for readability (base 16–17px).

---

## Motion

- **Hexagon field:** a tiled hex grid, hairline strokes, drifting very slowly with
  a faint parallax; occasional cell "pulses" softly when activity happens.
- **Mini shapes:** small white triangles/dots floating upward at low opacity, slow.
- **Glass cards:** lift + brighten edge on hover; content fades/slides in on mount.
- **Plan Console:** the tier path draws in left-to-right with the active tier glowing
  in its accent; a confirmed plan does a single satisfying "lock-in" pulse.
- **Reduced motion:** all drift/pulse animations disabled under
  `prefers-reduced-motion`. Non-negotiable.

---

## Sound design

Subtle, short, **toggleable** (global mute + volume in Settings; off-by-default until
the user opts in). Built with the Web Audio API or short samples. Sound is feedback,
never decoration — one cue per meaningful event.

| Event | Cue | Character |
|-------|-----|-----------|
| Button click (neutral) | soft tick | very short, low |
| **Approve / confirm** | rising two-note chime | bright, affirming |
| **Return / back** | single soft tick | quiet, lower than confirm |
| **Blocked** | low muted thud | heavy, brief, no sparkle |
| **Cancel** | short downward blip | dry, dismissive |
| **Result ready** | gentle ping | pleasant, clear |
| **AI ↔ AI handshake** (serious tasks / collaboration kicked off) | distinct two-tone "exchange" | two voices answering each other — signals model-to-model work |
| Error / failure | dull double thud | unmistakable but not alarming |

**Rules:** keep every cue under ~400ms, cap volume, debounce rapid clicks, and always
honor the mute toggle. Loud or frequent sound reads as a toy — restraint keeps it premium.

---

## Chat overlay

- Glassy transparent panel, **white** lettering for normal text.
- Code: syntax-highlighted, multi-color, collapsible blocks with a language label and
  copy button.
- Message groups collapse; each AI message carries a small badge (which tier/model)
  and a cost chip.
- The **Plan Console** can surface inline as a compact card, expandable to the full
  visual plan with the confirm / modify / cancel controls (each wired to its sound).

---

## Accessibility floor (build to it quietly)

Responsive to mobile, visible keyboard focus rings (in the active accent), reduced
motion respected, sound fully optional, contrast kept high (bold white on near-black
is already strong — keep dim text above WCAG AA).

---

## One-line summary for the builder

Near-black + bold white + transparent grey glass, hex field drifting behind, accent
colors that mean something, and short tasteful sounds on the actions that matter.
