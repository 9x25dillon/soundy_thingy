#!/usr/bin/env node
/**
 * parity_check.cjs — Emit the JS-side cross-platform vectors as JSON.
 * tests/test_biosentinel.py runs this and compares against natal_seed.py.
 *
 * Usage: node parity_check.cjs [chart.json] [intention]
 */
"use strict";
const fs = require("fs");
const path = require("path");
const NS = require(path.join(__dirname, "natal_seed.js"));

// Battery mode: `node parity_check.cjs --battery cases.json` reads
// [{chart, intention}, ...] and emits one result per case — either the
// canonical string + seed, or the validation error the case was rejected with.
// Python owns the case list (tests/test_biosentinel.py), so the two sides
// cannot drift apart by editing only one of them.
//
// This exists because a single fixed TEST_CHART cannot establish
// substrate-independence: it proves the two implementations agree on ONE
// point, which is the weakest possible evidence for a claim quantified over
// all charts. Both divergences found on 2026-08-04 (JS toFixed deferring to
// exponential at 1e21; Array.sort ordering by UTF-16 code unit rather than
// code point) sat outside that single point and survived every green run.
if (process.argv[2] === "--battery") {
  const cases = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
  const out = cases.map((c) => {
    try {
      const s = NS.deriveNatalSeed(c.chart, c.intention || "");
      return { ok: true, canonical: NS.canonicalizeChart(c.chart), seed_hex: NS.seedToHex(s) };
    } catch (e) {
      return { ok: false, error: String(e.message || e) };
    }
  });
  process.stdout.write(JSON.stringify(out) + "\n");
  process.exit(0);
}

let chart = NS.TEST_CHART;
let intention = NS.TEST_INTENTION;
if (process.argv[2]) chart = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
if (process.argv.length > 3) intention = process.argv[3];

const REF_BEDROCK = [190.5, 148.75, 252.625, 366.375];
const seed = NS.deriveNatalSeed(chart, intention);
const rand = NS.createNatalPRNG(seed);
const prng = [];
for (let i = 0; i < 16; i++) prng.push(rand());

const sentinel = NS.clampSentinelParams(
  { active: true, n: 8, k: 0.7, perturb: 5.0, spread: 1.0 });
const bed = NS.bedrockFrequencies(chart);
const rand2 = NS.createNatalPRNG(seed);
const modulated = [];
for (let i = 0; i < 8; i++) {
  modulated.push(NS.modulateFrequency(bed[i % bed.length], i, sentinel, rand2));
}
const offSentinel = NS.clampSentinelParams({ active: false });
const offBaseline = bed.map((f, i) =>
  NS.modulateFrequency(f, i, offSentinel, rand2));

process.stdout.write(JSON.stringify({
  canonical: NS.canonicalizeChart(chart),
  seed_hex: NS.seedToHex(seed),
  seed_prng32: NS.seedLower32(seed),
  prng: prng,
  bedrock: Array.from(bed),
  binaural: NS.binauralConfig(chart),
  modulated: modulated,
  off_equals_bedrock: offBaseline.every((f, i) => f === bed[i]),
  sanitize: NS.sanitizeIntention("  a\u0000 b\tc\nd   e  " + "x".repeat(300)),
  // Fixed reference bedrock: isolates the placement algorithm from the
  // pow()-induced last-bit difference in bedrockFrequencies (transcendentals
  // are not bit-identical across libm). Placement uses only * and /, so on
  // identical input it must agree EXACTLY.
  placement_ref_s0: Array.from(NS.ghostPlacement(REF_BEDROCK, 8, 0.0)),
  placement_ref_s1: Array.from(NS.ghostPlacement(REF_BEDROCK, 12, 1.0)),
  placement_ref_s10: Array.from(NS.ghostPlacement(REF_BEDROCK, 16, 10.0)),
  word: NS.substitutionWord(64),
  sturmian_defect: NS.sturmianDefect(NS.substitutionWord(200)),
  placement_s0: Array.from(NS.ghostPlacement(bed, 8, 0.0)),
  placement_s1: Array.from(NS.ghostPlacement(bed, 12, 1.0)),
  placement_s10: Array.from(NS.ghostPlacement(bed, 16, 10.0)),
  clamped: NS.clampSentinelParams({ n: 9999, k: -5, perturb: 1e9, spread: 100 }),
}) + "\n");
