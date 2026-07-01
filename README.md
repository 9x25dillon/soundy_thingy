# soundy_thingy

A fully client-side generative ambient synthesizer that runs in any modern browser.

**synth.html** — a single, self-contained HTML file (~37 KB) that generates evolving, musical, never-repeating ambient drones and melodic sequences using only the Web Audio API. No dependencies, no build step, no network calls. Just open the file.

## Features

- **Generative Engine**: Press play and let it compose. Uses a seeded PRNG for reproducible yet endlessly varying music.
- **6 Voice Types**:
  - Pad (rich, detuned, shimmering)
  - Pluck (Karplus-Strong style)
  - Bass (sub + drive)
  - Bell (FM metallic)
  - Drone (sustaining with breath and movement)
  - Noise-wash (textural)
- **Extensible Architecture**:
  - Add new voices, LFO targets, scales, or geometric pentatonics with tiny registry edits.
- **Scales & Geometry**:
  - 14+ scales (major, minor, dorian, phrygian, lydian, pentatonics, hirajoshi, insen, etc.)
  - Geometric pentatonics (circle of fifths, golden spiral, pentagram, equilateral, etc.)
- **Modulation Matrix**: Route LFOs (sine, triangle, saw, square, random, smooth random) to any parameter, FX, density, etc.
- **FX Chain**: Ping-pong delay (tempo-syncable), procedural reverb, chorus, drive, stereo widener, master lowpass + limiter.
- **Mood Macros**: Warm, Calm, Glass, Dark, Bright — instantly reshape the character.
- **Visualizer**: Spectrum, oscilloscope, and orbit view (shows geometric shapes when active).
- **Transport**: Tempo, density, swing, root note, full generative scheduler with look-ahead timing.
- **Persistence & Sharing**:
  - Autosaves to localStorage.
  - Shareable URL hashes that restore the exact patch.
- **Presets**: Factory presets + ability to save/load your own.
- **Keyboard Shortcuts**: Space (play/stop), R (randomize), M (panic), etc.
- **Mobile Friendly**: Touch-friendly controls, responsive layout.
- **Offline Ready**: Works completely from `file://` with WiFi off.

## Quick Start

1. Open `synth.html` in any modern browser (Chrome, Firefox, Safari, Edge).
2. Click the "Click or tap anywhere to begin" scrim (required for audio unlock).
3. Press the big **PLAY** button.
4. Tweak knobs, change scale/geometry/mood, or just let it run.

That's it. No installation. No accounts.

## Controls

- **Transport bar**: Tempo, Density, Root, Scale, Geometry (overrides scale), Mood
- **Voices panel**: Add, enable/disable, adjust level/pan/probability, edit voice-specific params
- **Modulation**: LFOs + matrix for routing modulation
- **FX**: Delay, Reverb, etc.
- **Visualizer**: Click tabs to switch modes
- **Randomize**: Re-roll the generative seed
- **Share**: Copy a link that restores the exact sound

## Extensibility

The code is deliberately modular:

```js
// Add a new voice (one-liner in registry)
App.Voices.registry['myvoice'] = { ... }

// Add a new scale
App.Scales.registry['myScale'] = { id: 'myScale', label: 'My Scale', intervals: [0,2,3,7,9] }

// Add a geometric pattern
App.Geometry.registry['myGeom'] = { id: 'myGeom', label: 'My Geom', generate: (root) => [...] }
```

Everything auto-wires into the UI.

## Technical Details

- Pure Web Audio API (no Tone.js or external libs)
- Procedural reverb impulse response generated in-browser
- Look-ahead scheduler for rock-solid timing
- All state is plain JSON (easy to serialize/extend)
- Seeded PRNG for deterministic generative output
- Fully offline capable

## License

MIT — see [LICENSE](LICENSE) file.

## Repository Contents

This repo contains the full Resonarium project:

- **synth.html** — The main generative ambient synthesizer (see above)
- **resonarium-enhanced.html** — Previous full-featured version with multi-layer synthesis, sequencer, cymatics, etc.
- **resonarium_cli_engineering.py** + **resonarium_cli_skeleton.py** — Python CLI tools for parameter editing and preset design
- **resonarium_engineering_platform.html** + bundle — Earlier engineering-focused web instrument
- Supporting files: state examples, documentation, etc.

## Contributing

Pull requests are welcome! Especially new voices, scales, geometries, or visualizer modes for synth.html.

---

Made with care for people who want beautiful ambient sound without complexity. Open the file and disappear into the sound. 🎵