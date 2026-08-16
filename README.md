# soundy_thingy

A collection of self-contained, browser-based audio instruments and tools focused on generative sound design, resonance, and ambient synthesis.

Most tools are **single-file** and work completely offline when opened directly — see
[Offline behaviour](#offline-behaviour) for the one exception.

## Main Project

**synth.html** — A fully client-side generative ambient synthesizer.

A polished, playable instrument that generates evolving, musical, never-repeating ambient drones and melodic sequences using only the Web Audio API.

- Zero dependencies, zero build step, zero network calls.
- Open the file and it just works (even from `file://` or USB drive).
- ~37 KB total.

### Key Features

- **Generative Engine**: Press play and let it compose. Uses a seeded PRNG for reproducible yet endlessly varying music.
- **6 Voice Types**: Pad, Pluck, Bass, Bell, Drone, Noise-wash.
- **Extensible Architecture**: Add new voices, LFO targets, scales, or geometric pentatonics with tiny registry edits.
- **Scales & Geometry**: 14+ scales + geometric pentatonics (circle of fifths, golden spiral, pentagram, equilateral, etc.).
- **Modulation Matrix**: Route LFOs (including random/smooth random) to parameters, FX, density, etc.
- **FX Chain**: Ping-pong delay (tempo-sync), procedural reverb, chorus, drive, stereo widener + limiter.
- **Mood Macros**: Warm / Calm / Glass / Dark / Bright — instantly reshape the character.
- **Visualizer**: Spectrum, oscilloscope, and orbit view (with geometry polygons).
- **Transport**: Tempo, density, swing, root note, full generative scheduler with look-ahead timing.
- **Persistence & Sharing**: localStorage + shareable URL hashes.
- **Presets**: Factory presets + ability to save/load your own.
- **Keyboard Shortcuts**: Space (play/stop), R (randomize), M (panic), etc.
- **Mobile Friendly**: Touch-friendly controls, responsive layout.
- **Offline Ready**: Works completely from `file://` with WiFi off.

## Quick Start (synth.html)

1. Open `synth.html` in any modern browser.
2. Click the scrim to unlock audio.
3. Press **PLAY**.
4. Explore or let it run.

## Controls Overview

- **Transport**: Tempo, Density, Root note, Scale, Geometry, Mood
- **Voices panel**: Add/edit voices and their parameters
- **Modulation**: LFOs + routing matrix
- **FX panel**: Delay, Reverb, etc.
- **Visualizer**: Switch between spectrum / scope / orbit
- **Randomize** / **Share** buttons

## Extensibility

Everything is designed to be easy to extend:

```js
// New voice
App.Voices.registry['myvoice'] = { ... }

// New scale
App.Scales.registry['myScale'] = { ... }

// New geometric pattern
App.Geometry.registry['myGeom'] = { ... }
```

## Technical Details

- Pure Web Audio API
- Procedural reverb (no external IR files)
- Look-ahead scheduler for timing accuracy
- Seeded PRNG for deterministic generative output
- Fully offline + `file://` compatible

## Resonarium × Biosentinel — `resonarium/`

The actively maintained instrument, kept in its own directory. It is a
natal-geometry-seeded audiovisual instrument with a toggleable Sentinel Mode overlay and
a headless CLI controller, and its distinguishing property is that the Python and
JavaScript halves agree **bit for bit**: the same chart and intention produce the same
64-bit seed, the same PRNG stream, and the same placements in the browser and in the
terminal. A cross-language parity suite asserts that rather than assuming it.

```bash
cd resonarium
python3 -m unittest discover -s tests        # 49 tests, stdlib only
python3 resonarium_biosentinel_cli.py verify

# same seed from either side
echo '{"sun":142.73,"moon":78.41,"asc":215.92,"mc":312.44,"aspects_sum":1247.8}' > /tmp/chart.json
python3 resonarium_biosentinel_cli.py seed --chart /tmp/chart.json --intention "clarity"
```

See [`resonarium/README.md`](resonarium/README.md) for the full description, the safety
notes, and the state schema. Node is optional — the parity tests skip without it.

**Not a medical device.** It makes no diagnostic, therapeutic or health claims. Visual
modulation is hard-capped below the photosensitive risk band and audio is clamped, but
if you are sensitive to pulsing sound or imagery, don't use it.

## Repository Contents

The root holds the synthesizer and an **earlier snapshot** of the Resonarium work.
`resonarium/` holds the current version. Where a filename appears in both places, the
copy under `resonarium/` is the newer one.

| File | Description |
|------|-------------|
| `synth.html` | **Main project** — Generative ambient synthesizer (single file) |
| `resonarium/` | **Current Resonarium × Biosentinel** — instrument, CLI, shared seed core, schema, tests |
| `resonarium-enhanced.html` | Earlier snapshot of the instrument. Superseded by `resonarium/resonarium-enhanced.html` |
| `resonarium_engineering_platform.html` | Engineering-focused web instrument (earlier iteration) |
| `resonarium_engineering_platform_bundle.zip` | Zip of the engineering platform files. Duplicates source already in this repo |
| `resonarium_cli_engineering.py` | Python CLI for editing parameters, presets, and exporting state |
| `resonarium_cli_skeleton.py` | Lighter CLI skeleton for quick scripting / batch preset work |
| `RESONARIUM_ENGINEERING_README.md` | Documentation for the engineering platform |
| `resonarium_fractal_example_state.json` | Example saved state / patch |
| `README.md` | This file |
| `LICENSE` | MIT License |

### Other Tools

- **Python CLIs** (`resonarium_cli_*.py`): Useful for designing patches outside the browser or batch processing. Require `rich` (`pip install rich`).
- **Engineering Platform**: Earlier, more "DAW-like" version with editable tables, snapshots, and analysis tools.

## Offline behaviour

Every file here opens from `file://` with the network off, and makes **zero** off-host
requests. That is checked on every push, twice: once by the test suite's own scan and
once by an independent audit job, so weakening the test cannot also switch off the thing
the test was guarding.

`resonarium_hologram_cymatic_nodal_4D.html` used to be the exception — it pulled three.js
from cdnjs and two typefaces from Google, so it would not render offline and announced
your IP address to Cloudflare and Google on every launch. three.js r134 is now vendored
into `resonarium/vendor/` (MIT, byte-identical to upstream, pinned by SHA-256 and checked
in CI), and the webfont links are gone: every `font-family` in that file already declared
`system-ui` / `monospace` fallbacks, so the typeface changes and nothing else does.

Verified in a real browser rather than by grep — `THREE.REVISION === 134` resolving from
`vendor/`, with no requests leaving the machine.

## Quick Start for Other Files

- Open any `*.html` file directly in your browser.
- For the Python CLIs: `python3 resonarium_cli_engineering.py` (after `pip install rich`).

## License

MIT — see [LICENSE](LICENSE) file.

## Contributing

Pull requests welcome! New voices, scales, modulation targets, or visualizer modes are especially appreciated.

---

Made with care for deep listening and generative sound design. 🎵