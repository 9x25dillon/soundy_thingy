# soundy_thingy

A collection of self-contained, browser-based audio instruments and tools focused on generative sound design, resonance, and ambient synthesis.

All tools are **single-file** (or minimal) and work completely offline when opened directly.

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

## Repository Contents

| File | Description |
|------|-------------|
| `synth.html` | **Main project** — Generative ambient synthesizer (single file) |
| `resonarium-enhanced.html` | Previous full-featured version with multi-layer synthesis, sequencer, cymatics, presets, timer, WAV export |
| `resonarium_engineering_platform.html` | Engineering-focused web instrument (earlier iteration) |
| `resonarium_engineering_platform_bundle.zip` | Zip archive of the engineering platform files |
| `resonarium_cli_engineering.py` | Python CLI companion for editing parameters, presets, and exporting state |
| `resonarium_cli_skeleton.py` | Lighter CLI skeleton for quick scripting / batch preset work |
| `RESONARIUM_ENGINEERING_README.md` | Documentation for the engineering platform |
| `resonarium_fractal_example_state.json` | Example saved state / patch |
| `README.md` | This file |
| `LICENSE` | MIT License |

### Other Tools

- **Python CLIs** (`resonarium_cli_*.py`): Useful for designing patches outside the browser or batch processing. Require `rich` (`pip install rich`).
- **Engineering Platform**: Earlier, more "DAW-like" version with editable tables, snapshots, and analysis tools.

All HTML tools are completely standalone — just open the `.html` file in a browser.

## Quick Start for Other Files

- Open any `*.html` file directly in your browser.
- For the Python CLIs: `python3 resonarium_cli_engineering.py` (after `pip install rich`).

## License

MIT — see [LICENSE](LICENSE) file.

## Contributing

Pull requests welcome! New voices, scales, modulation targets, or visualizer modes are especially appreciated.

---

Made with care for deep listening and generative sound design. 🎵