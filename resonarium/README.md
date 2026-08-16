# Resonarium × Biosentinel

A local-only, natal-geometry-seeded audiovisual instrument with a
toggleable **Sentinel Mode** overlay, plus a headless CLI controller.

> **What this is (and isn't):** a creative instrument for aesthetic
> exploration. It is **not a medical device** and makes no diagnostic,
> therapeutic, or health claims. Visual modulation is hard-capped at
> 2.5 Hz (below the 3–30 Hz photosensitive risk zone) and all audio is
> clamped to 20 Hz – 18 kHz, but if you are sensitive to pulsing sound
> or imagery, don't use it.

## Files

| File | Role |
|---|---|
| `natal_seed.py` / `natal_seed.js` | Shared deterministic core: canonical chart serialization, intention sanitization, SHA-256/64-bit seed derivation, mulberry32 PRNG, safety clamps, trace privacy guard. **Bit-exact across Python and JS.** |
| `resonarium-enhanced.html` | Browser app: natal bedrock oscillators + binaural pair + canvas field, with the Biosentinel Sentinel Mode panel (`n`, `k`, `perturb`, `spread`). Open next to `natal_seed.js`. |
| `resonarium_biosentinel_cli.py` | Headless controller: derive seeds, set params, export/import state, print the Temporal Trace. |
| `state_schema.json` | Versioned shared state schema (`1.0.0`). |
| `parity_check.cjs` | Emits JS-side vectors for the cross-platform parity tests. |
| `tests/test_biosentinel.py` | Verification suite (stdlib `unittest`; Node parity tests skip if `node` is absent). |

## Quick start

```bash
cd resonarium

# Browser: serve locally (or just open the file — it also works on file://)
python3 -m http.server 8000   # then open http://localhost:8000/resonarium-enhanced.html

# CLI: derive a seed
echo '{"sun":142.73,"moon":78.41,"asc":215.92,"mc":312.44,"aspects_sum":1247.8}' > /tmp/chart.json
python3 resonarium_biosentinel_cli.py seed --chart /tmp/chart.json --intention "clarity"
# -> seed_hex 86813727ef5b4048  (the browser shows the identical digest)

# Sentinel control + trace
python3 resonarium_biosentinel_cli.py set --n 16 --k 0.5 --perturb 12 --on
python3 resonarium_biosentinel_cli.py trace
python3 resonarium_biosentinel_cli.py export --out state.json   # redacted by default

# Self-checks and full suite
python3 resonarium_biosentinel_cli.py verify
python3 -m unittest discover -s tests -v
```

In the browser: accept the notice → *Use demo chart* (or paste your own
chart JSON) → *Anchor natal seed* → *Start audio* → enable *Sentinel Mode*.

## Design invariants

- **Natal bedrock is immutable.** Bedrock oscillator frequencies are set
  once at anchor time and never written by any sentinel code path; the
  overlay only adds ghost oscillators/rings around the baseline. Turning
  Sentinel Mode off restores the pure natal output exactly.
- **One hash strategy everywhere.** Seed = first 8 bytes (big-endian) of
  SHA-256 over the canonical UTF-8 string of `chart | intention`. Same
  chart + same intention ⇒ same 64-bit seed in Python and the browser.
- **All Biosentinel randomness is seeded.** A single mulberry32 PRNG,
  seeded from the low 32 bits of the natal seed, drives every entropy
  event; it is re-seeded on each sentinel activation, so a session is a
  deterministic replay.
- **Parameters:** `n` = ghost voices/rings (0–64) · `k` = coupling back
  toward the natal baseline (0–1; 1 = no deviation) · `perturb` = max
  frequency deviation in Hz (0–100) · `spread` = geometric dispersion
  (0–10). All inputs are clamped on every path (UI, CLI, import).

## Privacy & safety

- Raw natal chart data and raw intention text live **in page memory
  only** — never in `localStorage`, the Temporal Trace, console output,
  or exports. Export includes them only via an explicit opt-in checkbox.
- The Temporal Trace enforces a privacy guard that refuses entries
  containing chart/intention/birth-data keys, in both implementations.
- The seed is a one-way digest; natal data cannot be reconstructed from it.
- **No network access:** the CLI is pure stdlib file I/O, and the HTML
  ships a `default-src 'none'; connect-src 'none'` CSP. The test suite
  scans all shipped files for network tokens.
- Error messages are generic and never echo chart contents.

## State sync (CLI ⇄ browser)

Both sides speak `state_schema.json`. The CLI writes
`~/.resonarium/biosentinel_state.json` (override with `--state`);
`export`/`import` on either side moves the same redacted JSON across.
Browser tabs additionally sync live via the `storage` event.
