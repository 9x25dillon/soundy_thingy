#!/usr/bin/env python3
"""
resonarium_biosentinel_cli.py — Headless controller for the Resonarium
Biosentinel overlay.

Shares seed derivation, PRNG, clamps, and the temporal-trace privacy
guard with the browser app (resonarium-enhanced.html) via natal_seed.py /
natal_seed.js, so the same chart + intention produces the same 64-bit
seed and the same modulation sequence in both environments.

Privacy and safety invariants enforced here:
  * Natal chart data is read only from a local file the user names; it is
    never written into the state file, the temporal trace, or exports.
  * Exports are redacted by default (chart/bedrock keys stripped).
  * All parameters are clamped to the shared safety limits.
  * No network access of any kind.

This tool is an aesthetic/creative instrument. It makes no medical,
diagnostic, or therapeutic claims.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import natal_seed as ns

DEFAULT_STATE_FILE = Path.home() / ".resonarium" / "biosentinel_state.json"
TRACE_MAX_ENTRIES = 1000


# --------------------------------------------------------------- state I/O
def default_state() -> dict:
    return {
        "schema_version": ns.SCHEMA_VERSION,
        "timestamp_utc": ns.utc_now_iso(),
        "natal_seed_intention": "",
        "sentinel": ns.clamp_sentinel_params({}),
        "temporal_trace": [],
    }


def load_state(path: Path) -> dict:
    if not path.exists():
        return default_state()
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        # Safe error path: never dump file contents; start fresh.
        print(f"warning: could not read state file at {path}; "
              "starting from defaults", file=sys.stderr)
        return default_state()
    return normalize_state(raw)


def normalize_state(raw: dict) -> dict:
    """Coerce arbitrary input into a valid, redacted, clamped state."""
    if not isinstance(raw, dict):
        return default_state()
    state = default_state()
    version = raw.get("schema_version")
    if version is not None and version != ns.SCHEMA_VERSION:
        print(f"warning: state schema_version {version!r} != "
              f"{ns.SCHEMA_VERSION}; applying best-effort migration",
              file=sys.stderr)
    raw = ns.redact_state(raw)  # exports/imports never carry chart data
    state["sentinel"] = ns.clamp_sentinel_params(raw.get("sentinel", {}))
    intention = raw.get("natal_seed_intention", "")
    state["natal_seed_intention"] = ns.sanitize_intention(
        intention if isinstance(intention, str) else "")
    seed_hex = raw.get("seed_hex")
    if isinstance(seed_hex, str) and len(seed_hex) == 16:
        state["seed_hex"] = seed_hex
    trace = raw.get("temporal_trace", [])
    if isinstance(trace, list):
        state["temporal_trace"] = [
            e for e in trace
            if isinstance(e, dict)
            and isinstance(e.get("event"), str)
            and isinstance(e.get("timestamp_utc"), str)
            and isinstance(e.get("params"), dict)
            and not set(e["params"]) & ns._TRACE_FORBIDDEN_KEYS
        ][-TRACE_MAX_ENTRIES:]
    return state


def save_state(state: dict, path: Path) -> None:
    state = ns.redact_state(state)
    state["timestamp_utc"] = ns.utc_now_iso()
    state["temporal_trace"] = state.get("temporal_trace", [])[-TRACE_MAX_ENTRIES:]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
    tmp.replace(path)


def append_trace(state: dict, event: str, params: dict | None = None) -> None:
    state.setdefault("temporal_trace", []).append(
        ns.make_trace_entry(event, params))


def read_chart(path: str) -> dict:
    """Load and validate a chart JSON file. Never echoes its contents."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            chart = json.load(f)
    except OSError:
        raise SystemExit(f"error: could not open chart file: {path}")
    except json.JSONDecodeError:
        raise SystemExit("error: chart file is not valid JSON")
    try:
        ns.validate_chart(chart)
    except ns.ChartValidationError as exc:
        raise SystemExit(f"error: invalid chart: {exc}")
    return chart


# ---------------------------------------------------------------- commands
def cmd_seed(args) -> int:
    chart = read_chart(args.chart)
    seed = ns.derive_natal_seed(chart, args.intention or "")
    out = {
        "seed_hex": ns.seed_to_hex(seed),
        "seed_decimal": str(seed),
        "seed_prng32": ns.seed_lower32(seed),
        "intention_len": len(ns.sanitize_intention(args.intention or "")),
        "chart_fields": len(chart),
    }
    print(json.dumps(out, indent=2))
    return 0


def cmd_anchor(args) -> int:
    chart = read_chart(args.chart)
    seed = ns.derive_natal_seed(chart, args.intention or "")
    state = load_state(args.state)
    state["seed_hex"] = ns.seed_to_hex(seed)
    if args.store_intention:
        state["natal_seed_intention"] = ns.sanitize_intention(args.intention or "")
    append_trace(state, "seed_anchor", {
        "seed_hex": state["seed_hex"],
        "intention_len": len(ns.sanitize_intention(args.intention or "")),
        "chart_fields": len(chart),
        "intention_stored": bool(args.store_intention),
    })
    save_state(state, args.state)
    print(json.dumps({"anchored": True, "seed_hex": state["seed_hex"]}, indent=2))
    return 0


def cmd_set(args) -> int:
    state = load_state(args.state)
    before = dict(state["sentinel"])
    requested = {}
    for key in ("n", "k", "perturb", "spread"):
        value = getattr(args, key)
        if value is not None:
            requested[key] = value
    if args.on:
        requested["active"] = True
    elif args.off:
        requested["active"] = False
    merged = dict(before)
    merged.update(requested)
    clamped = ns.clamp_sentinel_params(merged)
    state["sentinel"] = clamped
    changed = {k: clamped[k] for k in clamped if clamped[k] != before.get(k)}
    if "active" in changed:
        append_trace(state, "sentinel_toggle", {"active": clamped["active"]})
    param_changes = {k: v for k, v in changed.items() if k != "active"}
    if param_changes:
        append_trace(state, "param_change", param_changes)
    save_state(state, args.state)
    print(json.dumps({"sentinel": clamped, "changed": changed}, indent=2))
    return 0


def cmd_status(args) -> int:
    state = load_state(args.state)
    out = {
        "schema_version": state["schema_version"],
        "sentinel": state["sentinel"],
        "seed_hex": state.get("seed_hex"),
        "trace_entries": len(state.get("temporal_trace", [])),
        "state_file": str(args.state),
    }
    print(json.dumps(out, indent=2))
    return 0


def cmd_export(args) -> int:
    state = load_state(args.state)
    exported = ns.redact_state(state)
    append_trace(state, "state_export", {"redacted": True})
    save_state(state, args.state)
    text = json.dumps(exported, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"exported redacted state to {args.out}")
    else:
        sys.stdout.write(text)
    return 0


def cmd_import(args) -> int:
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except OSError:
        raise SystemExit(f"error: could not open state file: {args.file}")
    except json.JSONDecodeError:
        raise SystemExit("error: state file is not valid JSON")
    incoming = normalize_state(raw)
    state = load_state(args.state)
    state["sentinel"] = incoming["sentinel"]
    if incoming.get("seed_hex"):
        state["seed_hex"] = incoming["seed_hex"]
    if args.merge_trace:
        state["temporal_trace"] = (
            state.get("temporal_trace", []) + incoming.get("temporal_trace", [])
        )[-TRACE_MAX_ENTRIES:]
    append_trace(state, "state_import", {
        "sentinel": incoming["sentinel"],
        "merged_trace": bool(args.merge_trace),
    })
    save_state(state, args.state)
    print(json.dumps({"imported": True, "sentinel": state["sentinel"]}, indent=2))
    return 0


def cmd_trace(args) -> int:
    state = load_state(args.state)
    entries = state.get("temporal_trace", [])
    if args.clear:
        state["temporal_trace"] = []
        save_state(state, args.state)
        print(f"cleared {len(entries)} trace entries")
        return 0
    entries = entries[-args.limit:] if args.limit else entries
    if args.json:
        print(json.dumps(entries, indent=2))
    else:
        for entry in entries:
            print(f"{entry['timestamp_utc']}  {entry['event']:<18} "
                  f"{json.dumps(entry['params'], sort_keys=True)}")
        if not entries:
            print("(temporal trace is empty)")
    return 0


def cmd_preview(args) -> int:
    """Headless preview: bedrock + sentinel-modulated overlay frequencies.

    Demonstrates natal-bedrock immutability: bedrock values are computed
    once and reported unchanged next to each modulated overlay value.
    """
    chart = read_chart(args.chart)
    seed = ns.derive_natal_seed(chart, args.intention or "")
    state = load_state(args.state)
    sentinel = ns.clamp_sentinel_params(dict(state["sentinel"], active=True))
    bedrock = tuple(ns.bedrock_frequencies(chart))  # immutable baseline
    binaural = ns.binaural_config(chart)
    rand = ns.mulberry32(ns.seed_lower32(seed))
    rows = []
    for step in range(args.steps):
        for idx in range(sentinel["n"]):
            base = bedrock[idx % len(bedrock)]
            mod = ns.modulate_frequency(base, idx, sentinel, rand)
            rows.append({
                "step": step, "voice": idx,
                "bedrock_hz": round(base, 6),
                "overlay_hz": round(mod, 6),
                "deviation_hz": round(mod - base, 6),
            })
    out = {
        "seed_hex": ns.seed_to_hex(seed),
        "sentinel": sentinel,
        "bedrock_hz": [round(f, 6) for f in bedrock],
        "binaural": binaural,
        "voices": rows,
    }
    print(json.dumps(out, indent=2))
    return 0


def cmd_verify(args) -> int:
    """Built-in self-checks (also covered by tests/test_biosentinel.py)."""
    failures = []

    def check(name, cond):
        print(f"  [{'ok' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    print("seed determinism:")
    s1 = ns.derive_natal_seed(ns.TEST_CHART, ns.TEST_INTENTION)
    s2 = ns.derive_natal_seed(dict(ns.TEST_CHART), ns.TEST_INTENTION)
    check("same chart + intention -> same seed", s1 == s2)
    check("different intention -> different seed",
          s1 != ns.derive_natal_seed(ns.TEST_CHART, "other"))
    check("known test vector",
          ns.seed_to_hex(s1) == "86813727ef5b4048")

    print("chart validation:")
    for bad in ({}, {"sun": 1.0}, {"sun": float("nan"), "moon": 1.0, "asc": 2.0}):
        try:
            ns.derive_natal_seed(bad, "")
            check(f"rejects invalid chart {sorted(bad)}", False)
        except ns.ChartValidationError:
            check(f"rejects invalid chart {sorted(bad)}", True)

    print("sanitization:")
    check("control chars stripped",
          ns.sanitize_intention("a\x00b\tc\nd") == "abcd")
    check("length limited",
          len(ns.sanitize_intention("x" * 999)) == ns.MAX_INTENTION_LENGTH)

    print("clamping:")
    clamped = ns.clamp_sentinel_params(
        {"n": 9999, "k": -5, "perturb": 1e9, "spread": 100})
    check("params clamped to limits",
          clamped == {"active": False, "n": 64, "k": 0.0,
                      "perturb": 100.0, "spread": 10.0})
    check("frequency clamp", ns.clamp_frequency(1.0) == ns.FREQ_MIN_HZ
          and ns.clamp_frequency(1e6) == ns.FREQ_MAX_HZ)

    print("bedrock immutability / sentinel-off baseline:")
    bedrock = ns.bedrock_frequencies(ns.TEST_CHART)
    rand = ns.mulberry32(ns.seed_lower32(s1))
    off = {"active": False, "n": 8, "k": 0.7, "perturb": 5.0, "spread": 1.0}
    check("sentinel off returns pure bedrock",
          all(ns.modulate_frequency(f, i, off, rand) == f
              for i, f in enumerate(bedrock)))

    print("privacy:")
    try:
        ns.make_trace_entry("bad", {"sun": 142.73})
        check("trace privacy guard blocks chart keys", False)
    except ValueError:
        check("trace privacy guard blocks chart keys", True)
    redacted = ns.redact_state({"sentinel": {}, "natal_chart": {"sun": 1},
                                "natal_bedrock": [220.0]})
    check("export redaction strips chart data",
          "natal_chart" not in redacted and "natal_bedrock" not in redacted)

    if failures:
        print(f"\n{len(failures)} check(s) FAILED")
        return 1
    print("\nall checks passed")
    return 0


# -------------------------------------------------------------------- main
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resonarium_biosentinel_cli",
        description=("Headless controller for the Resonarium Biosentinel "
                     "overlay. Local-only; no network access; exports are "
                     "redacted of natal data by default."))
    parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE_FILE,
        help=f"state file path (default: {DEFAULT_STATE_FILE})")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("seed", help="derive the 64-bit natal seed")
    p.add_argument("--chart", required=True, help="path to chart JSON file")
    p.add_argument("--intention", default="", help="optional intention phrase")
    p.set_defaults(func=cmd_seed)

    p = sub.add_parser("anchor", help="derive seed and store its digest in state")
    p.add_argument("--chart", required=True)
    p.add_argument("--intention", default="")
    p.add_argument("--store-intention", action="store_true",
                   help="opt in to persisting the sanitized intention phrase")
    p.set_defaults(func=cmd_anchor)

    p = sub.add_parser("set", help="set sentinel parameters (clamped)")
    p.add_argument("--n", type=int, help="ghost voices/rings (0-64)")
    p.add_argument("--k", type=float, help="coupling toward baseline (0-1)")
    p.add_argument("--perturb", type=float, help="max deviation Hz (0-100)")
    p.add_argument("--spread", type=float, help="geometric dispersion (0-10)")
    onoff = p.add_mutually_exclusive_group()
    onoff.add_argument("--on", action="store_true", help="activate sentinel")
    onoff.add_argument("--off", action="store_true", help="deactivate sentinel")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("status", help="print current state summary")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("export", help="export redacted state JSON")
    p.add_argument("--out", help="output file (default: stdout)")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("import", help="import state JSON (redacted + clamped)")
    p.add_argument("file", help="state JSON file to import")
    p.add_argument("--merge-trace", action="store_true",
                   help="append imported temporal trace entries")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("trace", help="print temporal trace log")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true", help="output as JSON array")
    p.add_argument("--clear", action="store_true")
    p.set_defaults(func=cmd_trace)

    p = sub.add_parser("preview",
                       help="headless bedrock + overlay frequency preview")
    p.add_argument("--chart", required=True)
    p.add_argument("--intention", default="")
    p.add_argument("--steps", type=int, default=1)
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("verify", help="run built-in safety/determinism checks")
    p.set_defaults(func=cmd_verify)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
