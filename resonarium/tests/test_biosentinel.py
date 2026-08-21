"""
Verification suite for the Resonarium <-> Biosentinel integration.

Runs with stdlib only:
    python3 -m unittest discover -s resonarium/tests -v
(also pytest-compatible). The Node parity tests skip automatically when
node is unavailable.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import natal_seed as ns  # noqa: E402

CLI = ROOT / "resonarium_biosentinel_cli.py"
NODE = shutil.which("node")


def run_cli(args, state: Path):
    return subprocess.run(
        [sys.executable, str(CLI), "--state", str(state), *args],
        capture_output=True, text=True, cwd=str(ROOT))


class TestSeedDeterminism(unittest.TestCase):
    def test_same_inputs_same_seed(self):
        s1 = ns.derive_natal_seed(ns.TEST_CHART, ns.TEST_INTENTION)
        s2 = ns.derive_natal_seed(dict(ns.TEST_CHART), ns.TEST_INTENTION)
        self.assertEqual(s1, s2)

    def test_known_vector(self):
        seed = ns.derive_natal_seed(ns.TEST_CHART, ns.TEST_INTENTION)
        self.assertEqual(ns.seed_to_hex(seed), "86813727ef5b4048")

    def test_intention_changes_seed(self):
        self.assertNotEqual(
            ns.derive_natal_seed(ns.TEST_CHART, "clarity"),
            ns.derive_natal_seed(ns.TEST_CHART, "focus"))

    def test_key_order_irrelevant(self):
        reordered = dict(reversed(list(ns.TEST_CHART.items())))
        self.assertEqual(ns.derive_natal_seed(ns.TEST_CHART, ""),
                         ns.derive_natal_seed(reordered, ""))

    def test_extra_keys_deterministic(self):
        chart = dict(ns.TEST_CHART, zeta=1.5, alpha=2.5)
        self.assertEqual(ns.derive_natal_seed(chart, ""),
                         ns.derive_natal_seed(dict(chart), ""))


class TestSanitization(unittest.TestCase):
    def test_control_chars_stripped(self):
        self.assertEqual(ns.sanitize_intention("a\x00b\tc\nd\x7fe"), "abcde")

    def test_length_limit(self):
        self.assertEqual(len(ns.sanitize_intention("x" * 1000)),
                         ns.MAX_INTENTION_LENGTH)

    def test_space_collapse_and_trim(self):
        self.assertEqual(ns.sanitize_intention("  a   b  "), "a b")

    def test_empty(self):
        self.assertEqual(ns.sanitize_intention(None), "")
        self.assertEqual(ns.sanitize_intention(""), "")


class TestChartValidation(unittest.TestCase):
    def test_rejects_empty(self):
        for bad in ({}, None, [], "chart"):
            with self.assertRaises(ns.ChartValidationError):
                ns.validate_chart(bad)  # type: ignore[arg-type]

    def test_rejects_incomplete(self):
        with self.assertRaises(ns.ChartValidationError):
            ns.validate_chart({"sun": 1.0, "moon": 2.0})

    def test_rejects_non_finite(self):
        with self.assertRaises(ns.ChartValidationError):
            ns.validate_chart({"sun": float("nan"), "moon": 1.0, "asc": 2.0})

    def test_rejects_nested(self):
        with self.assertRaises(ns.ChartValidationError):
            ns.validate_chart({"sun": 1.0, "moon": 2.0, "asc": {"deg": 3}})

    def test_accepts_minimal(self):
        ns.validate_chart({"sun": 1.0, "moon": 2.0, "asc": 3.0})


class TestClamping(unittest.TestCase):
    def test_sentinel_params_clamped(self):
        clamped = ns.clamp_sentinel_params(
            {"n": 9999, "k": -5, "perturb": 1e9, "spread": 100, "active": 1})
        self.assertEqual(clamped, {"active": True, "n": 64, "k": 0.0,
                                   "perturb": 100.0, "spread": 10.0})

    def test_defaults_on_garbage(self):
        self.assertEqual(ns.clamp_sentinel_params({"n": "wat", "k": None}),
                         ns.SENTINEL_DEFAULTS)
        self.assertEqual(ns.clamp_sentinel_params(None), ns.SENTINEL_DEFAULTS)

    def test_frequency_clamp(self):
        self.assertEqual(ns.clamp_frequency(0.1), ns.FREQ_MIN_HZ)
        self.assertEqual(ns.clamp_frequency(1e9), ns.FREQ_MAX_HZ)
        self.assertEqual(ns.clamp_frequency(440.0), 440.0)

    def test_visual_modulation_ceiling_below_risk_zone(self):
        self.assertLess(ns.VISUAL_MODULATION_MAX_HZ, 3.0)

    def test_modulated_output_always_in_range(self):
        seed = ns.derive_natal_seed(ns.TEST_CHART)
        rand = ns.mulberry32(ns.seed_lower32(seed))
        sentinel = {"active": True, "n": 64, "k": 0.0,
                    "perturb": 100.0, "spread": 10.0}
        for i in range(512):
            f = ns.modulate_frequency(25.0, i % 64, sentinel, rand)
            self.assertGreaterEqual(f, ns.FREQ_MIN_HZ)
            self.assertLessEqual(f, ns.FREQ_MAX_HZ)


class TestBaselinePurity(unittest.TestCase):
    """Sentinel off => output identical to natal bedrock, PRNG untouched."""

    def test_off_returns_exact_bedrock(self):
        bedrock = ns.bedrock_frequencies(ns.TEST_CHART)
        rand = ns.mulberry32(1234)
        off = dict(ns.SENTINEL_DEFAULTS)
        for i, f in enumerate(bedrock):
            self.assertEqual(ns.modulate_frequency(f, i, off, rand), f)
        # PRNG must not have been consumed while inactive.
        self.assertEqual(rand(), ns.mulberry32(1234)())

    def test_bedrock_derivation_pure(self):
        chart = dict(ns.TEST_CHART)
        b1 = ns.bedrock_frequencies(chart)
        b2 = ns.bedrock_frequencies(chart)
        self.assertEqual(b1, b2)
        self.assertEqual(chart, ns.TEST_CHART)  # input never mutated


class TestTemporalTrace(unittest.TestCase):
    def test_entries_are_valid_json(self):
        entry = ns.make_trace_entry("param_change", {"n": 8, "k": 0.7})
        parsed = json.loads(json.dumps(entry))
        self.assertEqual(set(parsed), {"event", "timestamp_utc", "params"})

    def test_privacy_guard(self):
        for leak in ({"sun": 1.0}, {"chart": {}}, {"intention": "x"},
                     {"birth_time": "12:00"}, {"natal_bedrock": []}):
            with self.assertRaises(ValueError):
                ns.make_trace_entry("event", leak)

    def test_redact_state(self):
        state = {"sentinel": {}, "natal_chart": {"sun": 1},
                 "chart": {}, "natal_bedrock": [220.0], "seed_hex": "ab"}
        redacted = ns.redact_state(state)
        self.assertEqual(set(redacted), {"sentinel", "seed_hex"})


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.state = self.dir / "state.json"
        self.chart_file = self.dir / "chart.json"
        self.chart_file.write_text(json.dumps(ns.TEST_CHART))

    def test_seed_command_deterministic(self):
        outs = [run_cli(["seed", "--chart", str(self.chart_file),
                         "--intention", "clarity"], self.state).stdout
                for _ in range(2)]
        self.assertEqual(outs[0], outs[1])
        self.assertEqual(json.loads(outs[0])["seed_hex"], "86813727ef5b4048")

    def test_set_clamps_and_traces(self):
        result = run_cli(["set", "--n", "9999", "--k", "-2", "--on"], self.state)
        self.assertEqual(result.returncode, 0)
        out = json.loads(result.stdout)
        self.assertEqual(out["sentinel"]["n"], 64)
        self.assertEqual(out["sentinel"]["k"], 0.0)
        trace = json.loads(run_cli(["trace", "--json"], self.state).stdout)
        events = [e["event"] for e in trace]
        self.assertIn("sentinel_toggle", events)
        self.assertIn("param_change", events)
        for entry in trace:
            self.assertEqual(set(entry), {"event", "timestamp_utc", "params"})

    def test_export_redacted_by_default(self):
        run_cli(["anchor", "--chart", str(self.chart_file)], self.state)
        exported = json.loads(run_cli(["export"], self.state).stdout)
        for forbidden in ("natal_chart", "chart", "natal_bedrock"):
            self.assertNotIn(forbidden, exported)
        # even a hand-tampered state file gets redacted on the way out
        tampered = json.loads(self.state.read_text())
        tampered["natal_chart"] = dict(ns.TEST_CHART)
        self.state.write_text(json.dumps(tampered))
        exported = json.loads(run_cli(["export"], self.state).stdout)
        self.assertNotIn("natal_chart", exported)

    def test_import_clamps_and_strips(self):
        payload = self.dir / "incoming.json"
        payload.write_text(json.dumps({
            "schema_version": "1.0.0",
            "sentinel": {"active": True, "n": 500, "k": 2, "perturb": -1,
                         "spread": 99},
            "natal_chart": {"sun": 1.0},
            "temporal_trace": [],
        }))
        result = run_cli(["import", str(payload)], self.state)
        out = json.loads(result.stdout)
        self.assertEqual(out["sentinel"],
                         {"active": True, "n": 64, "k": 1.0,
                          "perturb": 0.0, "spread": 10.0})
        stored = json.loads(self.state.read_text())
        self.assertNotIn("natal_chart", stored)

    def test_verify_command(self):
        result = run_cli(["verify"], self.state)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_preview_bedrock_immutable(self):
        result = run_cli(["preview", "--chart", str(self.chart_file),
                          "--intention", "clarity", "--steps", "2"], self.state)
        out = json.loads(result.stdout)
        bedrock = out["bedrock_hz"]
        for voice in out["voices"]:
            self.assertEqual(voice["bedrock_hz"],
                             bedrock[voice["voice"] % len(bedrock)])


@unittest.skipUnless(NODE, "node not available")
class TestBrowserParity(unittest.TestCase):
    """The success criterion: identical seed + PRNG stream + modulation
    across the Python CLI and the browser JS implementation."""

    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [NODE, str(ROOT / "parity_check.cjs")],
            capture_output=True, text=True, cwd=str(ROOT))
        assert result.returncode == 0, result.stderr
        cls.js = json.loads(result.stdout)

    def test_canonical_string(self):
        self.assertEqual(self.js["canonical"],
                         ns.canonicalize_chart(ns.TEST_CHART))

    def test_seed_identical(self):
        seed = ns.derive_natal_seed(ns.TEST_CHART, ns.TEST_INTENTION)
        self.assertEqual(self.js["seed_hex"], ns.seed_to_hex(seed))
        self.assertEqual(self.js["seed_prng32"], ns.seed_lower32(seed))

    def test_prng_stream_identical(self):
        seed = ns.derive_natal_seed(ns.TEST_CHART, ns.TEST_INTENTION)
        rand = ns.mulberry32(ns.seed_lower32(seed))
        py = [rand() for _ in range(16)]
        self.assertEqual(self.js["prng"], py)  # exact float equality

    def test_bedrock_and_modulation_match(self):
        seed = ns.derive_natal_seed(ns.TEST_CHART, ns.TEST_INTENTION)
        bedrock = ns.bedrock_frequencies(ns.TEST_CHART)
        for js_f, py_f in zip(self.js["bedrock"], bedrock, strict=True):
            self.assertTrue(math.isclose(js_f, py_f, abs_tol=1e-9))
        sentinel = ns.clamp_sentinel_params(
            {"active": True, "n": 8, "k": 0.7, "perturb": 5.0, "spread": 1.0})
        rand = ns.mulberry32(ns.seed_lower32(seed))
        for i, js_f in enumerate(self.js["modulated"]):
            py_f = ns.modulate_frequency(
                bedrock[i % len(bedrock)], i, sentinel, rand)
            self.assertTrue(math.isclose(js_f, py_f, abs_tol=1e-9))

    def test_placement_bit_exact_on_identical_input(self):
        """Placement uses only * and /, so given the SAME bedrock it must agree
        exactly. The full chain does not, because bedrock_frequencies uses
        pow() and transcendentals are not bit-identical across libm — that
        boundary is pre-existing and is covered by tolerance below."""
        REF = [190.5, 148.75, 252.625, 366.375]
        for key, n, sp in [("placement_ref_s0", 8, 0.0),
                           ("placement_ref_s1", 12, 1.0),
                           ("placement_ref_s10", 16, 10.0)]:
            self.assertEqual(self.js[key], ns.ghost_placement(REF, n, sp), key)

    def test_placement_full_chain_within_tolerance(self):
        bed = ns.bedrock_frequencies(ns.TEST_CHART)
        for key, n, sp in [("placement_s0", 8, 0.0), ("placement_s1", 12, 1.0),
                           ("placement_s10", 16, 10.0)]:
            for a, b in zip(self.js[key], ns.ghost_placement(bed, n, sp),
                            strict=True):
                self.assertTrue(math.isclose(a, b, abs_tol=1e-9), key)

    def test_word_and_defect_parity(self):
        self.assertEqual(self.js["word"], ns.substitution_word(64))
        self.assertEqual(float(self.js["sturmian_defect"]),
                         ns.sturmian_defect(ns.substitution_word(200)))

    def test_js_off_baseline_pure(self):
        self.assertTrue(self.js["off_equals_bedrock"])

    def test_sanitize_and_clamp_parity(self):
        expected = ns.sanitize_intention("  a\x00 b\tc\nd   e  " + "x" * 300)
        self.assertEqual(self.js["sanitize"], expected)
        self.assertEqual(
            self.js["clamped"],
            ns.clamp_sentinel_params(
                {"n": 9999, "k": -5, "perturb": 1e9, "spread": 100}))


class TestSubstitutionPlacement(unittest.TestCase):
    """Ghost bank as a substitution-ordered quasiperiodic lattice."""

    REF = [190.5, 148.75, 252.625, 366.375]

    def test_word_is_sturmian(self):
        self.assertEqual(ns.sturmian_defect(ns.substitution_word(200)), 0.0)
        w = ns.substitution_word(200)
        for n in range(1, 7):
            self.assertEqual(ns.factor_complexity(w, n), n + 1)

    def test_spread_zero_reproduces_legacy_placement(self):
        """spread = 0 must be bit-identical to the former bedrock cycling."""
        bed = ns.bedrock_frequencies(ns.TEST_CHART)
        legacy = [ns.clamp_frequency(bed[i % len(bed)]) for i in range(16)]
        self.assertEqual(ns.ghost_placement(bed, 16, 0.0), legacy)

    def test_all_outputs_clamped(self):
        for sp in (0.0, 1.0, 5.0, 10.0):
            for f in ns.ghost_placement(self.REF, 64, sp):
                self.assertGreaterEqual(f, ns.FREQ_MIN_HZ)
                self.assertLessEqual(f, ns.FREQ_MAX_HZ)

    def test_bedrock_never_mutated(self):
        bed = list(self.REF)
        ns.ghost_placement(bed, 32, 7.0)
        self.assertEqual(bed, self.REF)

    def test_degenerate_inputs(self):
        self.assertEqual(ns.ghost_placement(self.REF, 0, 1.0), [])
        self.assertEqual(ns.ghost_placement([], 8, 1.0), [])


class TestNoNetworkCalls(unittest.TestCase):
    """No code path in the shipped files may reach the network."""

    FORBIDDEN = ["fetch(", "XMLHttpRequest", "WebSocket", "EventSource",
                 "sendBeacon", "importScripts", "http://", "https://",
                 "urllib", "requests.", "socket.", "aiohttp"]
    ALLOWED_URL_PREFIXES = [
        "http://json-schema.org",            # schema $id only, never fetched
        "https://claude.ai",                 # commit trailer in comments
    ]

    def scan(self, path: Path):
        text = path.read_text(encoding="utf-8")
        hits = []
        for lineno, line in enumerate(text.splitlines(), 1):
            for token in self.FORBIDDEN:
                if token in line:
                    if token in ("http://", "https://") and any(
                            p in line for p in self.ALLOWED_URL_PREFIXES):
                        continue
                    hits.append(f"{path.name}:{lineno}: {token}")
        return hits

    # Vendored third-party code is exempt from the token scan and pinned by hash
    # instead: it is not ours to rewrite, and a minified bundle mentions URLs in its
    # licence header without ever fetching anything.
    VENDORED = {"vendor/three.min.js"}
    SCANNED_SUFFIXES = (".py", ".js", ".cjs", ".html", ".json")

    def shipped(self):
        """Every file this directory ships, discovered rather than recited.

        The list used to be hard-coded, and a file reached the directory that the list
        did not name — `resonarium_hologram_cymatic_nodal_4D.html`, which pulled three.js
        from cdnjs and fonts from Google. The suite stayed green while a shipped
        instrument announced the reader's IP to two companies on every launch. A test
        that enumerates cannot be outrun by a new file the way a test that recites can.
        """
        out = []
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith(("tests/", ".git/", "__pycache__/")):
                continue
            if rel in self.VENDORED or path.suffix.lower() not in self.SCANNED_SUFFIXES:
                continue
            out.append(path)
        return out

    def test_no_network_tokens(self):
        scanned = self.shipped()
        self.assertGreaterEqual(len(scanned), 5,
                                "file discovery found suspiciously few files")
        hits = []
        for path in scanned:
            hits += self.scan(path)
        self.assertEqual(hits, [])

    def test_vendored_code_is_pinned_by_hash(self):
        """Exempting a file from the scan is only safe if it cannot change unnoticed."""
        import hashlib
        expected = {"vendor/three.min.js": "74782bdbcf6518f7745ed77035968fca"}
        for rel in sorted(self.VENDORED):
            path = ROOT / rel
            self.assertTrue(path.exists(), f"{rel} is exempted from the scan but missing")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest[:32], expected[rel],
                             f"{rel} changed; re-audit it before updating this hash")

    def test_html_has_lockdown_csp(self):
        html = (ROOT / "resonarium-enhanced.html").read_text(encoding="utf-8")
        self.assertIn("connect-src 'none'", html)
        self.assertIn("default-src 'none'", html)


# --------------------------------------------------------------------------
# Cross-substrate domain — the seed's ABSOLUTE-level invariance claim
# --------------------------------------------------------------------------
#
# Borrowed method, from the invariance-group framework in the substrate-comm
# work: *levels are verified, not asserted.* There, a renderer declares an
# invariance group and the harness samples random elements of it, demanding
# zero bit-error; one counterexample demotes the renderer.
#
# The seed pipeline sits at the bottom of that hierarchy — its invariance group
# is {id} alone (ABSOLUTE). For a hash that is correct and deliberate: we WANT
# no two distinct charts to collide. But ABSOLUTE is also the most fragile
# level there is, because every representational detail is load-bearing, and
# "bit-exact across Python and JS" is a claim quantified over ALL charts while
# TestBrowserParity only ever evidenced ONE.
#
# Two real divergences lived in that gap and survived every green run
# (found 2026-08-04):
#
#   1. |value| >= 1e21 — ECMA-262 makes toFixed() defer to ToString(), so JS
#      emitted "1e+21" where Python emitted the full decimal expansion.
#      Seeds 0x8624dc5976199acd (py) vs 0xa92d292aa0cd8803 (js).
#   2. Chart keys outside the BMP — Array.prototype.sort orders by UTF-16 code
#      UNIT, Python's sorted() by code POINT, so "😀" and "�" came out in
#      opposite order. Seeds 0x3fc7be78418c6fca vs 0x5cdbf5512214e514.
#
# Neither was caught by the finiteness check, because 1e21 is finite and an
# emoji is a perfectly good dict key.
BATTERY = [
    # (name, chart, intention)
    ("baseline", {"sun": 142.73, "moon": 78.41, "asc": 215.92, "mc": 312.44}, "clarity"),
    ("negative-zero", {"sun": -0.0, "moon": 78.41, "asc": 215.92, "mc": 0.0}, ""),
    ("subnormal-rounding", {"sun": 2.6755e-7, "moon": 78.41, "asc": 215.92, "mc": 1.0000005}, ""),
    ("float-repr-trap", {"sun": 0.1 + 0.2, "moon": 78.41, "asc": 215.92, "mc": 1.005}, ""),
    ("large-but-in-domain", {"sun": 142.73, "moon": 78.41, "asc": 215.92, "aspects_sum": 9.99e20}, ""),
    ("astral-plane-keys", {"sun": 142.73, "moon": 78.41, "asc": 215.92, "�": 1.0, "\U0001F600": 2.0}, ""),
    ("bmp-boundary-keys", {"sun": 142.73, "moon": 78.41, "asc": 215.92, "￿": 1.0, "\U00010000": 2.0}, ""),
    ("string-values", {"sun": 142.73, "moon": 78.41, "asc": 215.92, "note": "z\U0001F600"}, ""),
    ("unicode-intention", {"sun": 142.73, "moon": 78.41, "asc": 215.92}, "ясность 😀"),
    # Rejected identically on both sides — the declared domain boundary.
    ("out-of-domain-high", {"sun": 142.73, "moon": 78.41, "asc": 215.92, "aspects_sum": 1e21}, ""),
    ("out-of-domain-low", {"sun": 142.73, "moon": 78.41, "asc": 215.92, "aspects_sum": -1e21}, ""),
]


@unittest.skipIf(NODE is None, "node not available")
class TestCrossSubstrateDomain(unittest.TestCase):
    """Every chart in BATTERY must seed identically in Python and JS, or be
    rejected identically by both. One counterexample demotes the claim."""

    @classmethod
    def setUpClass(cls):
        cases = [{"chart": c, "intention": i} for _, c, i in BATTERY]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as fh:
            json.dump(cases, fh, ensure_ascii=False)
            path = fh.name
        result = subprocess.run(
            [NODE, str(ROOT / "parity_check.cjs"), "--battery", path],
            capture_output=True, text=True, cwd=str(ROOT))
        assert result.returncode == 0, result.stderr
        cls.js = json.loads(result.stdout)
        Path(path).unlink(missing_ok=True)

    def test_battery_agrees_case_by_case(self):
        self.assertEqual(len(self.js), len(BATTERY), "battery length drifted")
        for (name, chart, intention), js in zip(BATTERY, self.js, strict=True):
            with self.subTest(case=name):
                try:
                    seed = ns.derive_natal_seed(chart, intention)
                except ns.ChartValidationError:
                    self.assertFalse(
                        js["ok"],
                        f"{name}: Python rejected the chart but JS accepted it "
                        f"and produced seed {js.get('seed_hex')}")
                    continue
                self.assertTrue(
                    js["ok"],
                    f"{name}: Python produced a seed but JS rejected it "
                    f"({js.get('error')})")
                self.assertEqual(js["canonical"], ns.canonicalize_chart(chart),
                                 f"{name}: canonical string diverged")
                self.assertEqual(js["seed_hex"], ns.seed_to_hex(seed),
                                 f"{name}: SEED DIVERGED across substrates")

    def test_canonicalize_alone_is_guarded(self):
        """The guard must live in the formatter, not only in derive_natal_seed.

        canonicalize_chart is public and callable without validating, and it is
        the canonical STRING that has to be substrate-identical — the seed is
        just its digest. Guarding only the derive path left
        canonicalize_chart({'sun': 1e21}) returning the full decimal expansion
        in Python and "1e+21" in JS.
        """
        with self.assertRaises(ns.ChartValidationError):
            ns.canonicalize_chart({"sun": ns.FORMAT_DOMAIN_LIMIT})
        js = subprocess.run(
            [NODE, "-e",
             "const N=require('./natal_seed.js');"
             "try{N.canonicalizeChart({sun:1e21});console.log('ACCEPTED');}"
             "catch(e){console.log('REJECTED');}"],
            capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(js.stdout.strip(), "REJECTED",
                         "JS canonicalizeChart accepted an out-of-domain value")

    def test_domain_limit_is_the_documented_toFixed_threshold(self):
        """The bound is not arbitrary: it is exactly where ECMA-262 changes
        toFixed's behaviour. Just inside must work; at the limit must reject."""
        base = {"sun": 142.73, "moon": 78.41, "asc": 215.92}
        ns.derive_natal_seed({**base, "aspects_sum": 9.99e20})  # must not raise
        with self.assertRaises(ns.ChartValidationError):
            ns.derive_natal_seed({**base, "aspects_sum": ns.FORMAT_DOMAIN_LIMIT})


if __name__ == "__main__":
    unittest.main(verbosity=2)


# Duplicated verbatim in parity_check.cjs, the same way REF_BEDROCK is: the
# two sides must not be able to drift by editing only one file.
ASPECT_REF = {
    "sun": 10.0, "pluto": 10.0, "neptune": 40.0, "jupiter": 55.0, "moon": 70.0,
    "mercury": 100.0, "venus": 130.0, "saturn": 145.0, "uranus": 160.0,
    "mars": 190.0, "asc": 283.0, "mc": 12.5,
}


class TestAspectGeometry(unittest.TestCase):
    """Aspect angles as intervals, and the weighting they drive."""

    def test_cents_are_exact_intervals(self):
        # 180 degrees == one octave, so 1 degree == 20/3 cents exactly.
        self.assertEqual(ns.aspect_cents(0.0), 0.0)
        self.assertEqual(ns.aspect_cents(60.0), 400.0)    # major third
        self.assertEqual(ns.aspect_cents(90.0), 600.0)    # tritone
        self.assertEqual(ns.aspect_cents(120.0), 800.0)   # minor sixth
        self.assertEqual(ns.aspect_cents(180.0), 1200.0)  # octave

    def test_ratio_matches_bedrock_mapping(self):
        """An aspect's ratio must equal the ratio the bedrock map would give
        two bodies that far apart — otherwise the interval layer and the
        bedrock layer are speaking different tunings."""
        for angle in (0.0, 30.0, 60.0, 90.0, 120.0, 180.0):
            direct = ns.aspect_ratio(angle)
            via_bedrock = (110.0 * 2.0 ** (angle / 180.0)) / 110.0
            self.assertTrue(math.isclose(direct, via_bedrock, rel_tol=1e-12))

    def test_separation_handles_negative_and_wrapped(self):
        self.assertEqual(ns.separation(10.0, 370.0), 0.0)
        self.assertEqual(ns.separation(-10.0, 350.0), 0.0)
        self.assertEqual(ns.separation(-90.0, 90.0), 180.0)
        self.assertEqual(ns.separation(359.5, 0.5), 1.0)
        self.assertEqual(ns.separation(0.0, 181.0), 179.0)
        for a in (-720.0, -5.5, 0.0, 123.4, 400.0):
            for b in (-360.0, 17.25, 200.0, 719.9):
                self.assertTrue(0.0 <= ns.separation(a, b) <= 180.0)

    def test_every_aspect_type_is_reachable(self):
        found = {a["aspect"] for a in ns.detect_aspects(ASPECT_REF, 1.0)}
        expected = {t["name"] for t in ns.ASPECT_TYPES}
        self.assertEqual(found, expected)

    def test_exact_aspect_has_full_strength(self):
        aspects = ns.detect_aspects(ASPECT_REF, 1.0)
        exact = [a for a in aspects if a["orb"] == 0.0]
        self.assertTrue(exact)
        for a in exact:
            self.assertEqual(a["strength"], 1.0)

    def test_strength_falls_off_with_orb(self):
        aspects = {(a["a"], a["b"]): a for a in ns.detect_aspects(ASPECT_REF)}
        # mc is 2.5 deg from a conjunction with sun (orb limit 8).
        conj = aspects[("sun", "mc")]
        self.assertEqual(conj["aspect"], "conjunction")
        self.assertTrue(math.isclose(conj["strength"], 1.0 - 2.5 / 8.0))

    def test_pairs_walked_in_canonical_order(self):
        aspects = ns.detect_aspects(ASPECT_REF)
        order = [k for k in ns.LONGITUDE_KEYS if k in ASPECT_REF]
        seen = [(order.index(a["a"]), order.index(a["b"])) for a in aspects]
        self.assertEqual(seen, sorted(seen))
        for i, j in seen:
            self.assertLess(i, j)

    def test_orb_scale_is_clamped(self):
        lo, hi = ns.ORB_SCALE_LIMITS
        wide = ns.detect_aspects(ASPECT_REF, 1e9)
        self.assertEqual(wide, ns.detect_aspects(ASPECT_REF, hi))
        narrow = ns.detect_aspects(ASPECT_REF, -5.0)
        self.assertEqual(narrow, ns.detect_aspects(ASPECT_REF, lo))

    def test_wider_orb_never_loses_an_aspect(self):
        pairs = lambda sc: {(a["a"], a["b"]) for a in ns.detect_aspects(ASPECT_REF, sc)}
        self.assertTrue(pairs(1.0) <= pairs(2.0) <= pairs(3.0))

    def test_weights_bounded_and_unaspected_at_floor(self):
        aspects = ns.detect_aspects(ASPECT_REF)
        w = ns.aspect_weights(ASPECT_REF, aspects)
        self.assertEqual(set(w), {k for k in ns.LONGITUDE_KEYS if k in ASPECT_REF})
        for v in w.values():
            self.assertTrue(0.35 <= v <= 1.0)
        self.assertTrue(math.isclose(max(w.values()), 1.0))
        # A body with no aspects at all sits exactly at the floor.
        lonely = {"sun": 0.0, "moon": 7.0, "asc": 200.0, "mc": 111.3}
        la = ns.detect_aspects(lonely)
        lw = ns.aspect_weights(lonely, la)
        unaspected = {a for k in lonely for a in [k]} - {
            x for a in la for x in (a["a"], a["b"])}
        for k in unaspected:
            self.assertEqual(lw[k], 0.35)

    def test_voice_plan_respects_clamps_and_budget(self):
        aspects = ns.detect_aspects(ASPECT_REF)
        keys = [k for k in ns.LONGITUDE_KEYS if k in ASPECT_REF]
        bed = ns.bedrock_frequencies(ASPECT_REF)
        plan = ns.aspect_voice_plan(bed, keys, aspects)
        self.assertEqual(len(plan), len(aspects))
        for v in plan:
            self.assertTrue(ns.FREQ_MIN_HZ <= v["root_hz"] <= ns.FREQ_MAX_HZ)
            self.assertTrue(ns.FREQ_MIN_HZ <= v["partner_hz"] <= ns.FREQ_MAX_HZ)
            self.assertTrue(0.0 <= v["beat_hz"] <= ns.ASPECT_BEAT_MAX_HZ)
            self.assertGreaterEqual(v["gain"], 0.0)
        # Total gain cannot exceed the budget however many aspects there are.
        self.assertLessEqual(sum(v["gain"] for v in plan), ns.ASPECT_GAIN_TOTAL + 1e-12)

    def test_voice_plan_interval_is_the_aspect(self):
        aspects = ns.detect_aspects(ASPECT_REF)
        keys = [k for k in ns.LONGITUDE_KEYS if k in ASPECT_REF]
        bed = ns.bedrock_frequencies(ASPECT_REF)
        for v, a in zip(ns.aspect_voice_plan(bed, keys, aspects), aspects, strict=True):
            if v["partner_hz"] in (ns.FREQ_MIN_HZ, ns.FREQ_MAX_HZ):
                continue  # clamped, ratio no longer meaningful
            self.assertTrue(math.isclose(
                v["partner_hz"] / v["root_hz"], ns.aspect_ratio(a["angle"]),
                rel_tol=1e-12))

    def test_bedrock_untouched_by_aspect_layer(self):
        """The aspect layer reads bedrock and must never write it — the same
        invariant the sentinel overlay is held to."""
        bed = ns.bedrock_frequencies(ASPECT_REF)
        before = list(bed)
        keys = [k for k in ns.LONGITUDE_KEYS if k in ASPECT_REF]
        aspects = ns.detect_aspects(ASPECT_REF)
        ns.aspect_voice_plan(bed, keys, aspects)
        ns.aspect_weights(ASPECT_REF, aspects)
        self.assertEqual(list(bed), before)

    def test_chartless_input_rejected(self):
        with self.assertRaises(ns.ChartValidationError):
            ns.detect_aspects({"sun": 1.0})


@unittest.skipUnless(NODE, "node not available")
class TestAspectParity(unittest.TestCase):
    """The aspect layer must agree across substrates as tightly as the seed
    does. detect_aspects and aspect_weights are arithmetic-only, so they are
    held to exact equality; anything through pow() gets the same tolerance
    already applied to bedrock derivation."""

    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [NODE, str(ROOT / "parity_check.cjs")],
            capture_output=True, text=True, cwd=str(ROOT))
        assert result.returncode == 0, result.stderr
        cls.js = json.loads(result.stdout)

    def test_detect_aspects_bit_exact(self):
        for key, scale in (("aspects_s1", 1.0), ("aspects_s25", 2.5)):
            py = ns.detect_aspects(ASPECT_REF, scale)
            self.assertEqual(len(self.js[key]), len(py), key)
            for j, p in zip(self.js[key], py, strict=True):
                self.assertEqual(j, p, key)

    def test_weights_bit_exact(self):
        py = ns.aspect_weights(ASPECT_REF, ns.detect_aspects(ASPECT_REF, 1.0))
        self.assertEqual(self.js["aspect_weights"], py)

    def test_cents_bit_exact(self):
        py = [ns.aspect_cents(t["angle"]) for t in ns.ASPECT_TYPES]
        self.assertEqual(self.js["aspect_cents"], py)

    def test_separation_bit_exact_including_negatives(self):
        pairs = [(10, 370), (-10, 350), (-90, 90), (359.5, 0.5), (0, 180), (0, 181)]
        py = [ns.separation(a, b) for a, b in pairs]
        self.assertEqual(self.js["separations"], py)

    def test_ratios_within_tolerance(self):
        py = [ns.aspect_ratio(t["angle"]) for t in ns.ASPECT_TYPES]
        for j, p in zip(self.js["aspect_ratios"], py, strict=True):
            self.assertTrue(math.isclose(j, p, abs_tol=1e-12))

    def test_voice_plan_parity(self):
        REF = [190.5, 148.75, 252.625, 366.375]
        py = ns.aspect_voice_plan(REF, ["sun", "moon", "asc", "mc"],
                                  ns.detect_aspects(ns.TEST_CHART, 1.0))
        js = self.js["aspect_plan_ref"]
        self.assertEqual(len(js), len(py))
        for j, p in zip(js, py, strict=True):
            # Arithmetic-only fields: exact.
            for field in ("a", "b", "aspect", "harmony", "cents", "beat_hz",
                          "gain", "root_hz"):
                self.assertEqual(j[field], p[field], field)
            # partner_hz goes through pow(): tolerance.
            self.assertTrue(math.isclose(j["partner_hz"], p["partner_hz"],
                                         abs_tol=1e-9))

    def test_voice_plan_full_chain_within_tolerance(self):
        keys = [k for k in ns.LONGITUDE_KEYS if k in ASPECT_REF]
        py = ns.aspect_voice_plan(ns.bedrock_frequencies(ASPECT_REF), keys,
                                  ns.detect_aspects(ASPECT_REF, 1.0))
        for j, p in zip(self.js["aspect_plan_full"], py, strict=True):
            self.assertEqual(j["aspect"], p["aspect"])
            self.assertTrue(math.isclose(j["root_hz"], p["root_hz"], abs_tol=1e-9))
            self.assertTrue(math.isclose(j["partner_hz"], p["partner_hz"], abs_tol=1e-9))
