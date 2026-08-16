/**
 * natal_seed.js — Browser/Node natal-geometry seed derivation and shared
 * Biosentinel math. Byte-for-byte compatible with natal_seed.py.
 *
 * Hash strategy (single strategy across both environments):
 *   SHA-256 over the UTF-8 canonical string, truncated to the first
 *   8 bytes, interpreted big-endian as an unsigned 64-bit BigInt.
 *
 * A small pure-JS SHA-256 is bundled so derivation is synchronous and
 * works on file:// with no Web Crypto or network dependency.
 *
 * Privacy: the seed is a one-way digest; raw chart data and raw intention
 * text are never logged or stored by anything in this module.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api; // Node (parity tests)
  } else {
    root.NatalSeed = api; // Browser global
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const SCHEMA_VERSION = "1.0.0";

  const CANONICAL_CHART_KEYS = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
    "asc", "mc", "true_node", "chiron",
    "aspects_sum", "house_cusps_hash",
  ];

  const LONGITUDE_KEYS = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
    "asc", "mc", "true_node", "chiron",
  ];

  const MAX_INTENTION_LENGTH = 256;
  const MIN_LONGITUDE_FIELDS = 3;

  // Above this magnitude toFixed(6) defers to ToString(x) per ECMA-262 and
  // emits "1e+21", while Python's ".6f" emits the full decimal expansion —
  // two canonical strings, two seeds. Mirrored in natal_seed.py.
  const FORMAT_DOMAIN_LIMIT = 1e21;

  // --- Safety limits (mirrored in natal_seed.py) ---
  const FREQ_MIN_HZ = 20.0;
  const FREQ_MAX_HZ = 18000.0;
  const VISUAL_MODULATION_MAX_HZ = 2.5; // below 3-30 Hz photosensitive zone

  const SENTINEL_LIMITS = {
    n: [0, 64],
    k: [0.0, 1.0],
    perturb: [0.0, 100.0],
    spread: [0.0, 10.0],
  };

  const SENTINEL_DEFAULTS = { active: false, n: 8, k: 0.7, perturb: 5.0, spread: 1.0 };

  class ChartValidationError extends Error {
    constructor(message) {
      super(message);
      this.name = "ChartValidationError";
    }
  }

  // ---------------------------------------------------------------- SHA-256
  // Compact pure-JS SHA-256 (FIPS 180-4), returns Uint8Array(32).
  const SHA256_K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);

  function sha256Bytes(msgBytes) {
    const H = new Uint32Array([
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ]);
    const len = msgBytes.length;
    const bitLenHi = Math.floor(len / 0x20000000);
    const bitLenLo = (len << 3) >>> 0;
    const padded = new Uint8Array((((len + 8) >> 6) + 1) << 6);
    padded.set(msgBytes);
    padded[len] = 0x80;
    const dv = new DataView(padded.buffer);
    dv.setUint32(padded.length - 8, bitLenHi, false);
    dv.setUint32(padded.length - 4, bitLenLo, false);

    const w = new Uint32Array(64);
    for (let off = 0; off < padded.length; off += 64) {
      for (let i = 0; i < 16; i++) w[i] = dv.getUint32(off + i * 4, false);
      for (let i = 16; i < 64; i++) {
        const s0 = ((w[i - 15] >>> 7) | (w[i - 15] << 25)) ^
                   ((w[i - 15] >>> 18) | (w[i - 15] << 14)) ^ (w[i - 15] >>> 3);
        const s1 = ((w[i - 2] >>> 17) | (w[i - 2] << 15)) ^
                   ((w[i - 2] >>> 19) | (w[i - 2] << 13)) ^ (w[i - 2] >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
      }
      let [a, b, c, d, e, f, g, h] = H;
      for (let i = 0; i < 64; i++) {
        const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^
                   ((e >>> 25) | (e << 7));
        const ch = (e & f) ^ (~e & g);
        const t1 = (h + S1 + ch + SHA256_K[i] + w[i]) >>> 0;
        const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^
                   ((a >>> 22) | (a << 10));
        const maj = (a & b) ^ (a & c) ^ (b & c);
        const t2 = (S0 + maj) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0;
        d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      H[0] = (H[0] + a) >>> 0; H[1] = (H[1] + b) >>> 0;
      H[2] = (H[2] + c) >>> 0; H[3] = (H[3] + d) >>> 0;
      H[4] = (H[4] + e) >>> 0; H[5] = (H[5] + f) >>> 0;
      H[6] = (H[6] + g) >>> 0; H[7] = (H[7] + h) >>> 0;
    }
    const out = new Uint8Array(32);
    const outDv = new DataView(out.buffer);
    for (let i = 0; i < 8; i++) outDv.setUint32(i * 4, H[i], false);
    return out;
  }

  function utf8Encode(str) {
    if (typeof TextEncoder !== "undefined") return new TextEncoder().encode(str);
    // Minimal UTF-8 fallback
    const bytes = [];
    for (const ch of str) {
      const cp = ch.codePointAt(0);
      if (cp < 0x80) bytes.push(cp);
      else if (cp < 0x800) bytes.push(0xc0 | (cp >> 6), 0x80 | (cp & 63));
      else if (cp < 0x10000) {
        bytes.push(0xe0 | (cp >> 12), 0x80 | ((cp >> 6) & 63), 0x80 | (cp & 63));
      } else {
        bytes.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 63),
                   0x80 | ((cp >> 6) & 63), 0x80 | (cp & 63));
      }
    }
    return new Uint8Array(bytes);
  }

  // ------------------------------------------------------------- Seed layer
  function sanitizeIntention(intention) {
    if (!intention) return "";
    let cleaned = "";
    for (const ch of String(intention)) {
      const code = ch.codePointAt(0);
      if (code >= 32 && code !== 127) cleaned += ch;
    }
    cleaned = cleaned.replace(/ +/g, " ").replace(/^ +| +$/g, "");
    return Array.from(cleaned).slice(0, MAX_INTENTION_LENGTH).join("");
  }

  function validateChart(chart) {
    if (typeof chart !== "object" || chart === null || Array.isArray(chart) ||
        Object.keys(chart).length === 0) {
      throw new ChartValidationError("chart is empty or not an object");
    }
    let longitudeCount = 0;
    for (const [key, value] of Object.entries(chart)) {
      if (typeof value === "boolean" || value === null ||
          typeof value === "object") {
        throw new ChartValidationError(
          `chart field '${key}' must be a finite number or string`);
      }
      if (typeof value === "number") {
        if (!Number.isFinite(value)) {
          throw new ChartValidationError(
            `chart field '${key}' must be a finite number`);
        }
        // Cross-substrate domain bound — see FORMAT_DOMAIN_LIMIT. Finiteness
        // alone did not catch this, because 1e21 is perfectly finite.
        if (Math.abs(value) >= FORMAT_DOMAIN_LIMIT) {
          throw new ChartValidationError(
            `chart field '${key}' is outside the cross-substrate domain ` +
            "(|value| must be < 1e21)");
        }
        if (LONGITUDE_KEYS.includes(key)) longitudeCount += 1;
      }
    }
    if (longitudeCount < MIN_LONGITUDE_FIELDS) {
      throw new ChartValidationError(
        `chart needs at least ${MIN_LONGITUDE_FIELDS} planetary/angle ` +
        "longitude fields");
    }
  }

  function formatValue(value) {
    if (typeof value === "number") {
      // Mirrors natal_seed.py._format_value: the domain check lives here as
      // well as in validateChart, because canonicalizeChart() is public and
      // callable without validating — and it is the canonical STRING, not the
      // seed, that has to be substrate-identical.
      if (Math.abs(value) >= FORMAT_DOMAIN_LIMIT) {
        throw new ChartValidationError(
          "value is outside the cross-substrate domain (|value| must be < 1e21)");
      }
      return (value + 0).toFixed(6);
    }
    return String(value);
  }

  /**
   * Compare two strings by Unicode code point, reproducing Python's `sorted()`
   * on str. Spreading a string iterates code points (surrogate pairs come out
   * whole), so this is lexicographic on code points with the shorter string
   * first on a common prefix — exactly Python's rule.
   */
  function compareCodePoints(a, b) {
    const A = [...a];
    const B = [...b];
    const n = Math.min(A.length, B.length);
    for (let i = 0; i < n; i++) {
      const d = A[i].codePointAt(0) - B[i].codePointAt(0);
      if (d !== 0) return d;
    }
    return A.length - B.length;
  }

  function canonicalizeChart(chart) {
    const parts = [];
    const seen = new Set();
    for (const key of CANONICAL_CHART_KEYS) {
      if (key in chart) {
        parts.push(`${key}:${formatValue(chart[key])}`);
        seen.add(key);
      }
    }
    // MUST be code-point order, to match Python's sorted(). The default
    // Array.prototype.sort compares UTF-16 code UNITS, which disagrees with
    // code-point order for anything outside the BMP: "😀" (U+1F600) sorts
    // before "�" in JS (lead surrogate 0xD83D < 0xFFFD) and after it in
    // Python. Different key order, different canonical string, different seed.
    const extras = Object.keys(chart)
      .filter((k) => !seen.has(k))
      .sort(compareCodePoints);
    for (const key of extras) parts.push(`${key}:${formatValue(chart[key])}`);
    return parts.join("|");
  }

  /** Deterministic unsigned 64-bit seed as BigInt. */
  function deriveNatalSeed(chart, intention = "") {
    validateChart(chart);
    let raw = canonicalizeChart(chart);
    const cleaned = sanitizeIntention(intention);
    if (cleaned) raw += `|intention:${cleaned}`;
    const digest = sha256Bytes(utf8Encode(raw));
    let seed = 0n;
    for (let i = 0; i < 8; i++) seed = (seed << 8n) | BigInt(digest[i]);
    return seed;
  }

  function seedToHex(seed) {
    return seed.toString(16).padStart(16, "0");
  }

  /** The 32-bit PRNG seed: lower 32 bits of the 64-bit seed. */
  function seedLower32(seed) {
    return Number(seed & 0xffffffffn);
  }

  // ------------------------------------------------------------------ PRNG
  /** mulberry32 — all Biosentinel randomness flows through this. */
  function mulberry32(a) {
    return function () {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function createNatalPRNG(seedBigInt) {
    return mulberry32(seedLower32(seedBigInt));
  }

  // -------------------------------------------------------------- Safety
  function clamp(value, lo, hi) {
    return Math.max(lo, Math.min(hi, value));
  }

  function clampFrequency(hz) {
    return clamp(hz, FREQ_MIN_HZ, FREQ_MAX_HZ);
  }

  function clampVisualModulationHz(hz) {
    return clamp(hz, 0, VISUAL_MODULATION_MAX_HZ);
  }

  function clampSentinelParams(params) {
    const out = Object.assign({}, SENTINEL_DEFAULTS);
    if (typeof params !== "object" || params === null) return out;
    if ("active" in params) out.active = Boolean(params.active);
    for (const key of ["n", "k", "perturb", "spread"]) {
      if (key in params) {
        const value = Number(params[key]);
        if (!Number.isFinite(value)) continue;
        const [lo, hi] = SENTINEL_LIMITS[key];
        out[key] = key === "n" ? Math.round(clamp(value, lo, hi))
                               : clamp(value, lo, hi);
      }
    }
    return out;
  }

  // -------------------------------------------------- Bedrock + modulation
  /** Immutable natal bedrock frequencies (110-440 Hz) from longitudes. */
  function bedrockFrequencies(chart) {
    validateChart(chart);
    const freqs = [];
    for (const key of LONGITUDE_KEYS) {
      if (key in chart && typeof chart[key] === "number") {
        const lon = ((chart[key] % 360) + 360) % 360;
        freqs.push(clampFrequency(110.0 * Math.pow(2.0, lon / 180.0)));
      }
    }
    return Object.freeze(freqs);
  }

  function binauralConfig(chart) {
    validateChart(chart);
    const ascRaw = "asc" in chart ? chart.asc : (chart.sun || 0);
    const asc = ((Number(ascRaw) % 360) + 360) % 360;
    const aspects = Number(chart.aspects_sum || 0);
    return Object.freeze({
      carrier_hz: clampFrequency(180.0 + (asc / 360.0) * 120.0),
      beat_hz: 4.0 + (Math.abs(aspects) % 8.0),
    });
  }

  /**
   * Sentinel overlay modulation. Never mutates baseHz — returns a new
   * overlay frequency. Consumes exactly one PRNG value per active call
   * (parity-critical with natal_seed.py).
   */
  function modulateFrequency(baseHz, voiceIndex, sentinel, rand) {
    if (!sentinel.active) return clampFrequency(baseHz);
    const rawOffset = (rand() - 0.5) * 2.0 * sentinel.perturb;
    const n = Math.max(sentinel.n | 0, 1);
    const spreadFactor = 1.0 + (voiceIndex / n) * sentinel.spread;
    const damped = rawOffset * spreadFactor * (1.0 - sentinel.k);
    return clampFrequency(baseHz + damped);
  }

  // -------------------------------------------------------- Temporal trace
  const TRACE_FORBIDDEN_KEYS = new Set([
    ...CANONICAL_CHART_KEYS,
    "chart", "natal_chart", "natal_bedrock", "intention", "intention_text",
    "birth_time", "birth_date", "birth_location", "lat", "lon",
    "latitude", "longitude",
  ]);

  /** Build a trace entry; throws if params contain natal/intention data. */
  function makeTraceEntry(event, params) {
    const p = Object.assign({}, params || {});
    const leaked = Object.keys(p).filter((k) => TRACE_FORBIDDEN_KEYS.has(k));
    if (leaked.length > 0) {
      throw new Error(
        "temporal trace privacy guard: refused to log natal/intention " +
        `fields: ${leaked.sort().join(", ")}`);
    }
    return {
      event: String(event),
      timestamp_utc: new Date().toISOString(),
      params: p,
    };
  }

  /** Copy of state with natal chart data removed (default export path). */
  function redactState(state) {
    const out = {};
    for (const [k, v] of Object.entries(state)) {
      if (k === "natal_chart" || k === "chart" || k === "natal_bedrock") continue;
      out[k] = v;
    }
    return out;
  }


  // --- Substitution-ordered ghost placement ---------------------------------
  // The ghost bank was a PERIODIC index map (bedrock[i % len]). A substitution
  // order makes it a 1-D quasiperiodic lattice: the Fibonacci word is Pisot
  // (eigenvalues tau, -1/tau), so the frequency set has pure point diffraction
  // with tau-power peak ratios. Mirrors natal_seed.py exactly.
  //
  // Invariants: bedrock is read, never written; every output passes
  // clampFrequency; spread = 0 reproduces the legacy placement bit-for-bit.
  const FIBONACCI_RULES = { L: "LS", S: "L" };
  const TAU = (1.0 + Math.sqrt(5)) / 2.0;

  function substitutionWord(length, rules, seed) {
    rules = rules || FIBONACCI_RULES;
    let s = seed || "L";
    const want = Math.max(length, 1);
    while (s.length < want) {
      let next = "";
      for (const c of s) next += rules[c];
      s = next;
    }
    return s.slice(0, want);
  }

  function factorComplexity(word, n) {
    if (n <= 0 || n > word.length) return 0;
    const set = new Set();
    for (let i = 0; i + n <= word.length; i++) set.add(word.slice(i, i + n));
    return set.size;
  }

  function sturmianDefect(word, nmax) {
    nmax = nmax || 6;
    if (word.length < nmax + 2) return nmax;
    let d = 0;
    for (let n = 1; n <= nmax; n++) d += Math.abs(factorComplexity(word, n) - (n + 1));
    return d / nmax;
  }

  function ghostPlacement(bedrock, n, spread, word) {
    n = Math.max(n | 0, 0);
    if (n === 0 || !bedrock || bedrock.length === 0) return [];
    word = word || substitutionWord(n);
    const rL = 1.0 + 0.04 * Number(spread);
    const rS = 1.0 + 0.04 * Number(spread) / TAU;
    const ratios = [1.0];
    for (let j = 0; j < n - 1; j++) {
      ratios.push(ratios[j] * (word[j % word.length] === "L" ? rL : rS));
    }
    const mid = ratios[Math.floor(n / 2)];
    const out = [];
    for (let i = 0; i < n; i++) {
      out.push(clampFrequency(bedrock[i % bedrock.length] * ratios[i] / mid));
    }
    return out;
  }

  // --- Shared cross-platform test vector ---
  const TEST_CHART = Object.freeze({
    sun: 142.73, moon: 78.41, asc: 215.92, mc: 312.44, aspects_sum: 1247.8,
  });
  const TEST_INTENTION = "clarity";

  return {
    SCHEMA_VERSION,
    CANONICAL_CHART_KEYS,
    LONGITUDE_KEYS,
    MAX_INTENTION_LENGTH,
    MIN_LONGITUDE_FIELDS,
    FREQ_MIN_HZ,
    FREQ_MAX_HZ,
    VISUAL_MODULATION_MAX_HZ,
    SENTINEL_LIMITS,
    SENTINEL_DEFAULTS,
    ChartValidationError,
    sanitizeIntention,
    validateChart,
    canonicalizeChart,
    deriveNatalSeed,
    seedToHex,
    seedLower32,
    mulberry32,
    createNatalPRNG,
    clamp,
    clampFrequency,
    clampVisualModulationHz,
    clampSentinelParams,
    bedrockFrequencies,
    binauralConfig,
    modulateFrequency,
    substitutionWord,
    factorComplexity,
    sturmianDefect,
    ghostPlacement,
    makeTraceEntry,
    redactState,
    TEST_CHART,
    TEST_INTENTION,
  };
});
