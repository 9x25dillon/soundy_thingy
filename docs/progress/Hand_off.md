# Hand_off — Resonarium Console, session of 2026-08-20

## Where the work is

**Canonical repo: `/home/kill/soundy_thingy`** (`github.com/9x25dillon/soundy_thingy`).
Not `astro-aae`. `/home/kill/astro-aae/resonarium/` is a larger LOCAL-ONLY superset —
24 files, 16 instruments, its own `serve.py` that vendors three.js/p5/Tone and rewrites
CDN refs at serve time — kept out of git deliberately via `.git/info/exclude` because
`astro_caster` is public. See its `LOCAL.md`. A session was lost to this ambiguity; check
`git remote -v` before building on any Resonarium copy.

Branch **`unified-console`**, two commits:

| commit | state |
|---|---|
| `039c41f` Make the derivation chain the thing you look at | **pushed** |
| `7057de1` Raise the aspects as interference, not as harmony | **NOT pushed** |

No PR is open. `resonarium.yml` triggers on push-to-main and on pull_request, so **CI has
never run against this branch.** That matters more than usual: CI installs Node explicitly
so the cross-language parity tests cannot skip themselves, and it runs Python 3.10–3.14.
Local verification was one interpreter. Opening a PR is the cheapest way to get the matrix.

Local state at handoff: 71 tests, 0 skips, offline audit clean, working tree clean.
A `python3 -m http.server 8777` may still be serving `/home/kill/soundy_thingy`.

## What was built

`resonarium/resonarium_console.html` — single page, ~2800 lines, sole dependency is
`natal_seed.js` beside it. Strict CSP, zero network.

1. **The derivation chain made visible.** canonical string → SHA-256 → uint64 → mulberry32
   state, as four live steps. Bedrock table shows each longitude, its derived Hz, its note.
2. **Seed sigil.** Deterministic glyph from the 64 bits — 16 nibbles as 16 radii, chords
   stepped by nibble value, rim marks from the Fibonacci word. Identity check by eye.
3. **Five views:** Field, Lattice, Cymatic, Spectrum, Sigil. Lattice was the point — the
   Fibonacci-word quasiperiodic ghost placement was doing real Pisot work and was invisible.
4. **Codex.** ~34 entries; every parameter carries an info mark giving formula, domain, a
   value computed live from current state, and why the limit is where it is.
5. **Aspect layer as interference** (second commit). Added to `natal_seed.py` AND
   `natal_seed.js` with parity vectors in `parity_check.cjs` and 21 tests.

## The aspect layer, and why it is shaped this way

The bedrock map (`110 · 2^(lon/180)`) already makes 180° of arc exactly one octave, so an
aspect angle **is** an interval: 1° = 20/3 cents. Square → 600¢ (tritone), trine → 800¢,
opposition → 1200¢ (octave). No tuning table needed. This relationship existed in the code
and was unused — the whole aspect structure was collapsed into `aspects_sum`, one scalar.

**The user redirected mid-build: this is not about music.** The interval is scaffolding.
The payload is interference — beating, nodal structure, the geometric space to explore.
Direction going forward is tones/nodes/emergent phenomena, NOT harmony, arrangement, or
anything Suno-adjacent. Suno was explicitly ruled out.

So: each aspect becomes a voice at the interval frequency, split into two partials offset
by its **orb**. Exact aspect → pure tone. Wide aspect → shimmer. The rhythm is chart
geometry; there is no clock or tempo anywhere in the engine. Three routings, chosen because
they are physically different phenomena, not presets:

- **monaural** — both partials to both ears, beats in the air, survives speakers
- **binaural** — hard-panned; does not exist acoustically, needs headphones
- **isochronic** — one tone, amplitude gated by an LFO on the gain param, works anywhere

Aspect strength also weights bedrock **gain only, never frequency** — same invariant the
sentinel is held to. Cymatic modes now take degree from aspect angle and pulse from orb,
so the nodal figure is chart-derived rather than PRNG output.

## Invariants — do not break these

- **Bedrock frequencies are frozen at anchor.** Nothing may write them. Gain may be
  weighted; frequency may not. `modulateFrequency` returns a value rather than mutating
  one, which makes this structural rather than a thing to remember.
- **One draw per element per event.** Parity holds only because of this. Note the nuance:
  variable draw count breaks *cross-language* reproducibility, not single-implementation
  determinism — relevant below.
- **Cymatic mode assignment uses its own generator** seeded from the same seed, never the
  sentinel stream. Sharing it would make the draw count depend on which view is open.
- **`Math.random` appears exactly once**, in the Random chart button. It invents a chart to
  explore; it is not part of any derivation, and the comment says so.
- **Reference vector:** TEST_CHART + `"clarity"` → `86813727ef5b4048`. The page self-checks
  this at startup and shows it in the header badge.
- **`natal_seed.{js,py}` must change together**, plus parity vectors and tests. Non-negotiable.

## Gotchas that cost time

**`norm360` and the modulo trap.** JS `((x % 360) + 360) % 360` perturbs values *already in
range*: 78.41 → 438.41 → 78.41000000000003. That last-bit shift propagated into orb,
strength and beat_hz and broke bit-exact parity (JS `5.969999999999914` vs Python
`5.969999999999999`). Fixed by adding 360 only when the remainder is negative, which is
precisely Python's float `%`. **The older `bedrockFrequencies` still uses the bad form** —
harmless there because it goes through `pow()` and is compared with `abs_tol=1e-9` anyway,
but do not copy that pattern into anything held to exact parity.

**Test fixtures and demo fixtures have opposite requirements.** `ASPECT_REF` (in
`parity_check.cjs` and `test_biosentinel.py`, duplicated verbatim like `REF_BEDROCK`) has
every aspect **exact** so all nine types are hit with orb 0. That is correct for asserting
geometry and useless for hearing it — orb 0 means no beating at all. `FULL_CHART` in the
console is deliberately 1.4–5.9° off exact so the field arrives with beats spread
0.30–4.20 Hz. Do not unify them.

**Headless Chromium does not run `requestAnimationFrame`** under `--virtual-time-budget`.
Any rAF-driven readout (telemetry, HUD) reads stale in a headless drive and will report
false failures. Codex live values are computed on click and are trustworthy there. Audio
needs `--autoplay-policy=no-user-gesture-required`.

**Autoplay.** `AudioContext` cannot start without a user gesture. Any "the app plays it for
them" flow needs a gesture designed in as the unlock.

## The Astra Arcana seam — read this before integrating

`astra_arcana` is a module of **`astro_caster`** = `/home/kill/astro-aae`. It is far
further along than `docs/archive/ASTRA_ARCANA_PLAN.md` suggests: `backend/tarot.py`,
`tarot_data.py`, `tarot_models.py`, `tarot_prompts.py`, `arcana_calendar.py`, a `parity/`
fixture dir, and four test modules already exist. Recent history is at "session 33".
Handoff convention there is `docs/progress/Hand_off.md` — this file mirrors it.

**There are now two independent SHA-256 seed derivations in this ecosystem.**

| | Resonarium `natal_seed` | Arcana `tarot.py` |
|---|---|---|
| input | canonical chart string + intention | joined parts string |
| digest | SHA-256, first 8 bytes BE → uint64 | SHA-256 hexdigest |
| generator | mulberry32 | Python `random.Random` |
| cross-language | **bit-exact JS ⇄ Python, CI-enforced** | Python only |

This is **not** a defect and should not be "fixed" reflexively. `tarot.py` is explicit that
existing seeds must stay reproducible, and `_default_seed` is already a pure function of
`(natal signature, resolved local date, spread, source system)` — which is good design.
Two things to know:

1. `random.Random` is Mersenne Twister and is **not reproducible outside Python.** If
   Arcana ever needs a client-side or JS-side draw — offline PWA, browser preview, shared
   reading link that regenerates locally — that is a dead end, and `natal_seed`'s
   mulberry32 is the drop-in with parity already proven and tested.
2. `weighted_draw` guarantees no duplicate cards. If that is implemented by redrawing on
   collision, the draw count varies with outcome. **Harmless today** (single Python
   implementation, same seed → same redraws → same result). It becomes fatal the moment a
   second implementation exists. Fisher-Yates is the fixed-draw alternative.

**The real tie-ins, in order of how buildable they are:**

- **Sigil.** The plan's Self-Expression Studio lists "personal sigils" and "draw your
  Ascendant mask as a sigil" as *prompt generation*. A working deterministic sigil renderer
  now exists (`paintSigil` in the console, seed-only input). That is a finished feature
  sitting in the wrong repo.
- **Audio.** "Ritual playlist concepts" and "audio-guided daily ritual" are roadmap items.
  The console is chart-derived audio with zero marginal cost and no stored assets.
- **Aspects.** `astro_caster` computes aspects properly via Swiss Ephemeris and its
  `ChartResponse` already carries them. `detectAspects` re-derives them from longitudes.
  **Decide which is authoritative** rather than letting both run. Swiss Ephemeris should
  win on correctness; `detectAspects` earns its place only where a browser has longitudes
  and no backend.
- **The seam is architectural:** `astro_caster` owns ephemeris (birth data → longitudes),
  `natal_seed` owns the digest, Resonarium renders. Birth data must not cross that line —
  Resonarium takes the reduced form on purpose, and that is a privacy asset for a paid
  product, not a gap.

## Product context

$10/mo subscription, subscriber-specific chart-derived soundtrack, played by the app.
Framed by the user as promoting healing "from a frequencial holistic iota against other
signals." **Flag, unresolved:** the repo says in three places — README, entry gate, and the
codex — "not a medical device, makes no diagnostic, therapeutic, or health claims of any
kind." Marketing that says healing contradicts shipped copy, and health claims on a paid
product carry different exposure than on free art. Wellness/experiential framing resolves
it without losing rhetorical force. Raised once; the user's call.

**Pin the engine version before taking payment.** If a subscriber's soundtrack changes
because the synthesis improved, that is a support ticket. Determinism becomes a contract
the moment money is attached.

## Open decisions

- Open the PR for `unified-console` to get the CI matrix? (recommended, and push `7057de1`)
- Transits as a modulation layer — architecturally this is the sentinel pattern one level
  up: natal frozen, transits drift, seed never changes, so identity survives while the
  piece is never the same twice. Needs `astro_caster` for ephemeris on a cadence.
- Sidereal is an ayanamsa offset (~24°) applied before derivation. Same engine, second
  tuning, a toggle rather than a rewrite.
- `ASPECT_VOICE_CAP` is 24. A dense chart hits 50+ aspects, which is 100+ oscillators
  sharing a fixed budget. Selection is by strength so it is deterministic. Lift if wanted.

## Other sessions

A peer session `astro-aae-05` was sent a briefing covering the seed contract, the reference
vector, the two canonicalization traps (1e21 `toFixed`/`%.6f`; UTF-16 code-unit vs
code-point sorting), draw-count discipline, and modulo bias on card index. Cross-session
messages do not return, so whether it acted on any of it is unknown — check its transcript.
