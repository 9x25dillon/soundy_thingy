# Resonarium Engineering Platform

This build upgrades the original `resonarium-enhanced.html` into a standalone engineering instrument.

## Files

- `resonarium_engineering_platform.html` — browser instrument with live audio, field/spectrogram views, persistence, presets, engineering tables, snapshots, JSON import/export, URL state sharing, and WebM recording.
  Advanced: standing-node visualizations, **multi-dimensional cymatic rendering engine** (Plate 2D, Radial, Interference, Spherical 3D projection), experimental pattern builders, ALIGN, math dimensions (harmonic/Φ/prime/fib/modal), keys (C = Cymatics, M, Shift+S). Real-time particle cymatics driven by active voices + math model.
- `resonarium_cli_engineering.py` — terminal companion for preset design, parameter editing, metrics, and JSON state export/import.

## Web app capabilities

- Full session persistence via `localStorage` under `resonarium.v2`.
- Resonance scenes: Theta Drift, Alpha Focus, Fractal Unfold, Deep Void, Solfeggio Loom, Crystal Lattice.
- EMERGE random-walk nudge for active voices.
- Engineering tab with:
  - Project manifest: title, tags, notes.
  - Live analyzer: active voices, frequency range, max effective beat, gain sum, band counts, risk indicator.
  - Editable parameter tables mirroring the JSON model.
  - Snapshot system stored locally.
  - Design console event log.
- Export/import JSON state.
- Copy/load URL state via `#state=` payload.
- MediaRecorder output capture to `.webm`.
- Keyboard controls:
  - Space: power
  - P: all off
  - E: emerge
  - 1–4: sweeps
  - Q–Y: binaurals
  - A–F: single tones
  - G: engineering view

## CLI quickstart

```bash
python3 -m pip install rich
python3 resonarium_cli_engineering.py
```

Example session:

```text
preset fractal
emerge
set b0 beat 4.5
set title "Fractal Study"
metrics
export fractal-state.json
```

Additional CLI commands:

- compound [on|off|toggle]   set compound on   set master 0.3
- panic / alloff
- title "My Project" | tags "theta, test" | notes "notes here"
- factory / reset   (restore defaults)
- set title "..." also supported

The exported JSON (full v2 schema) can be imported into the web app with **Import** (and vice versa).

## Safety note

This is an audio/synthesis tool, not a medical device. Keep volume low, use headphones carefully for binaural content, and stop listening if anything feels uncomfortable.
