#!/usr/bin/env python3
"""Surface-ladder ΔE gate — CIEDE2000 check for the 4-level tonal surface ladder.

SPEC v1.0 `v3-output/DL-R3/SPEC.md` §1.2.1/§1.2.2 + ACCEPTANCE A1.6 (R4 P0-2):
  - Ladder: S0 canvas / S1 base / S2 raised / S3 elevated. Owner tokens in
    `mobile/lib/core/design/tokens_v2/theme_manager.dart` (SparkleColors):
    surfaceAmbient / surfacePrimary / surfaceSecondary / surfaceTertiary.
  - Rule 1.2.1 (adjacent discriminability, lower bounds): S0→S1 luminance step
    ≥3%, S1→S2 ≥3%, S2→S3 ≥4%. The SPEC asserts the current (batch-1) LIGHT
    values already satisfy these, and both the §1.2 level table and the A1.6
    anchors are light-only — the bound is therefore GATED on the light ladder
    only; dark adjacent steps are printed informationally without gating.
    Luminance = WCAG relative luminance Y (sRGB linearized, D65), step = |ΔY|
    in percentage points (0–100 scale). Interpretation note: in the CIELAB L*
    reading the light S0→S1 pair is ≈1.4 — below 3 — which would contradict
    the SPEC's own "current values already satisfy" clause; the
    relative-luminance reading is the only one consistent with it and is the
    one pinned here (3.41 / 7.17 / 9.73 at the B2-2 snapshot). (Under the same
    reading the dark ladder measures 0.61/0.57/0.93 pp — another reason the
    bound is a light-table clause, not a universal one.)
  - Rule 1.2.2 (seed snapshot regression anchor): ΔE = CIEDE2000 with the D65
    2° observer (Lab via sRGB linearization). Current S0–S3 must stay within
    ΔE ≤ 2 of the frozen anchor values — anchors are the batch-1 calibrated
    light hexes (0xFFFCF8F3 / 0xFFF8F4EF / 0xFFF1EBE4 / 0xFFE7DED4, A1.6
    verbatim) plus the dark hexes as they stood at the B2-2 merge (snapshot
    baseline, same ≤2 discipline, so a future tonal regeneration cannot drift
    unreviewed in either brightness mode). Deviations are ONLY ever measured
    by this script output — never by eye, never by another tool's ΔE dialect.

Inputs:
  default    parse the current S0–S3 hexes straight from theme_manager.dart
             (last `surface*:` literal inside each SparkleColors.light/.dark
             factory = the normal palette after the CB-safe/high-contrast
             early returns).
  --current  explicit "S0,S1,S2,S3" hex list (the future tonal-pipeline
             output). Accepts 0xFFRRGGBB / RRGGBB / #RRGGBB.

Exit codes: 0 = pass · 1 = violations (or --self-test failure) · 2 =
environment/usage error (missing theme file, unparsable hex, …).

CLI:
  python3 scripts/design/check_surface_ladder_de.py                 # gate
  python3 scripts/design/check_surface_ladder_de.py --mode dark     # dark gate
  python3 scripts/design/check_surface_ladder_de.py --report        # ΔE tables
  python3 scripts/design/check_surface_ladder_de.py --self-test     # Sharma 2005

Read-only scanner: never modifies scanned sources.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_THEME_MANAGER = (
    REPO_ROOT / "mobile/lib/core/design/tokens_v2/theme_manager.dart"
)

# ── frozen anchors (SPEC §1.2 table / ACCEPTANCE A1.6 + B2-2 dark snapshot) ──

LIGHT_ANCHOR = {  # batch-1 calibration = the seed snapshot regression anchor
    "S0": "FCF8F3",  # surfaceAmbient
    "S1": "F8F4EF",  # surfacePrimary
    "S2": "F1EBE4",  # surfaceSecondary
    "S3": "E7DED4",  # surfaceTertiary
}
DARK_ANCHOR = {  # as-frozen-at-B2-2 snapshot of the dark normal palette
    "S0": "0E0E10",
    "S1": "1A1A1E",
    "S2": "222226",
    "S3": "2C2C30",
}
ANCHOR_PROVENANCE = {
    "light": "SPEC v1.0 §1.2 table / ACCEPTANCE A1.6 batch-1 seed anchor",
    "dark": "B2-2 merge-time snapshot of theme_manager dark normal palette",
}

# Rule 1.2.1 adjacent luminance lower bounds (percentage points, 0–100 scale).
LADDER_BOUNDS = {"S0": 3.0, "S1": 3.0, "S2": 4.0}  # bound on S(n) → S(n+1)
DE_THRESHOLD = 2.0  # rule 1.2.2 anchor equivalence

_LEVELS = ("S0", "S1", "S2", "S3")

# ── colorimetry (pure stdlib; D65/2°) ────────────────────────────────────────

# sRGB → XYZ matrix (IEC 61966-2-1, D65), scaled so Y of white = 100.
_M = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)
_WHITE = (95.047, 100.0, 108.883)  # D65 reference white (Xn, Yn, Zn)
_EPS = 216.0 / 24389.0
_KAPPA = 24389.0 / 27.0


def parse_hex(token: str) -> tuple[float, float, float]:
    """0xFFRRGGBB / RRGGBB / #RRGGBB → (r, g, b) in 0–255 floats."""
    t = token.strip().lstrip("#")
    if t.lower().startswith("0x"):
        t = t[2:]
    if len(t) == 8:  # ARGB
        t = t[2:]
    if len(t) != 6:
        raise ValueError(f"unparsable hex: {token!r} (want RRGGBB / 0xFFRRGGBB)")
    return tuple(int(t[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def srgb_to_linear(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rel_luminance(rgb: tuple[float, float, float]) -> float:
    """WCAG relative luminance Y on a 0–1 scale (D65)."""
    lin = [srgb_to_linear(c) for c in rgb]
    return _M[1][0] * lin[0] + _M[1][1] * lin[1] + _M[1][2] * lin[2]


def rgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """sRGB → CIELAB (D65/2°), per SPEC §1.2.2 度量口径."""
    lin = [srgb_to_linear(c) * 100.0 for c in rgb]
    xyz = tuple(sum(_M[r][c] * lin[c] for c in range(3)) for r in range(3))

    def f(t: float) -> float:
        return t ** (1 / 3) if t > _EPS else (_KAPPA * t + 16.0) / 116.0

    fx, fy, fz = (f(xyz[i] / _WHITE[i]) for i in range(3))
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def ciede2000(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
) -> float:
    """CIEDE2000 color difference (kL=kC=kH=1), Sharma et al. 2005 formulation."""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    c_bar = (C1 + C2) / 2.0
    c_bar7 = c_bar**7
    G = 0.5 * (1.0 - math.sqrt(c_bar7 / (c_bar7 + 25.0**7)))
    a1p, a2p = (1.0 + G) * a1, (1.0 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)

    def hp(ap: float, b: float) -> float:
        if ap == 0.0 and b == 0.0:
            return 0.0
        h = math.degrees(math.atan2(b, ap))
        return h + 360.0 if h < 0.0 else h

    h1p, h2p = hp(a1p, b1), hp(a2p, b2)

    dLp = L2 - L1
    dCp = C2p - C1p

    if C1p * C2p == 0.0:
        dhp = 0.0
    else:
        dhp = h2p - h1p
        if dhp > 180.0:
            dhp -= 360.0
        elif dhp < -180.0:
            dhp += 360.0
    dHp = 2.0 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2.0)

    Lbp = (L1 + L2) / 2.0
    Cbp = (C1p + C2p) / 2.0

    if C1p * C2p == 0.0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180.0:
        hbp = (h1p + h2p) / 2.0
    elif h1p + h2p < 360.0:
        hbp = (h1p + h2p + 360.0) / 2.0
    else:
        hbp = (h1p + h2p - 360.0) / 2.0

    T = (
        1.0
        - 0.17 * math.cos(math.radians(hbp - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * hbp))
        + 0.32 * math.cos(math.radians(3.0 * hbp + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * hbp - 63.0))
    )
    d_theta = 30.0 * math.exp(-(((hbp - 275.0) / 25.0) ** 2))
    cbp7 = Cbp**7
    RC = 2.0 * math.sqrt(cbp7 / (cbp7 + 25.0**7))
    SL = 1.0 + 0.015 * (Lbp - 50.0) ** 2 / math.sqrt(20.0 + (Lbp - 50.0) ** 2)
    SC = 1.0 + 0.045 * Cbp
    SH = 1.0 + 0.015 * Cbp * T
    RT = -math.sin(math.radians(2.0 * d_theta)) * RC

    return math.sqrt(
        (dLp / SL) ** 2
        + (dCp / SC) ** 2
        + (dHp / SH) ** 2
        + RT * (dCp / SC) * (dHp / SH)
    )


def delta_e_hex(hex1: str, hex2: str) -> float:
    return ciede2000(rgb_to_lab(parse_hex(hex1)), rgb_to_lab(parse_hex(hex2)))


# ── theme_manager.dart parsing ───────────────────────────────────────────────

_FIELD_RE = {
    "S0": re.compile(r"surfaceAmbient:\s*Color\(0x([0-9A-Fa-f]{8})\)"),
    "S1": re.compile(r"surfacePrimary:\s*Color\(0x([0-9A-Fa-f]{8})\)"),
    "S2": re.compile(r"surfaceSecondary:\s*Color\(0x([0-9A-Fa-f]{8})\)"),
    "S3": re.compile(r"surfaceTertiary:\s*Color\(0x([0-9A-Fa-f]{8})\)"),
}


def read_current_from_theme_manager(path: Path, mode: str) -> dict[str, str]:
    """Last `surface*:` literal per level inside SparkleColors.<mode>() = the
    normal palette (CB-safe / high-contrast variants return earlier)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EnvironmentError(f"cannot read {path}: {exc}") from exc
    factory = f"factory SparkleColors.{mode}("
    start = text.find(factory)
    if start < 0:
        raise EnvironmentError(f"factory not found in {path}: {factory}…)")
    end = text.find("\n  }", start)
    body = text[start : end if end > 0 else len(text)]
    out: dict[str, str] = {}
    for level, rx in _FIELD_RE.items():
        hits = rx.findall(body)
        if not hits:
            raise EnvironmentError(
                f"no {rx.pattern} literal found in {path} SparkleColors.{mode}"
            )
        out[level] = hits[-1][2:]  # drop FF alpha → RRGGBB
    return out


# ── gate ─────────────────────────────────────────────────────────────────────


def run_gate(
    current: dict[str, str],
    anchor: dict[str, str],
    mode: str,
    source: str,
    report: bool,
    de_threshold: float = DE_THRESHOLD,
) -> int:
    print(
        f"[surface-ladder-de] mode={mode}  source={source}\n"
        f"[surface-ladder-de] anchor: {ANCHOR_PROVENANCE[mode]} "
        f"({'/'.join(anchor[l] for l in _LEVELS)})"
    )
    violations: list[str] = []
    rows: list[str] = []

    cur_lab = {l: rgb_to_lab(parse_hex(current[l])) for l in _LEVELS}
    anc_lab = {l: rgb_to_lab(parse_hex(anchor[l])) for l in _LEVELS}

    rows.append(
        f"{'level':<6}{'current':<10}{'anchor':<10}{'Y(rel)':<9}{'L*':<8}"
        f"{'ΔE00(vs anchor)':<17}{'≤%.1f' % de_threshold}"
    )
    for l in _LEVELS:
        de = ciede2000(cur_lab[l], anc_lab[l])
        ok = de <= de_threshold
        if not ok:
            violations.append(
                f"{l} anchor drift: ΔE00={de:.4f} > {de_threshold} "
                f"(current {current[l]} vs anchor {anchor[l]}) — rule 1.2.2 / A1.6"
            )
        rows.append(
            f"{l:<6}{current[l]:<10}{anchor[l]:<10}"
            f"{rel_luminance(parse_hex(current[l])) * 100:<9.2f}"
            f"{cur_lab[l][0]:<8.2f}{de:<17.4f}{'PASS' if ok else 'FAIL'}"
        )

    rows.append("")
    rows.append(f"{'pair':<10}{'ΔE00':<10}{'|ΔY| pp':<10}{'bound':<8}verdict")
    for l in ("S0", "S1", "S2"):
        nxt = _LEVELS[_LEVELS.index(l) + 1]
        de = ciede2000(cur_lab[l], cur_lab[nxt])
        y_step = abs(
            rel_luminance(parse_hex(current[l])) - rel_luminance(parse_hex(current[nxt]))
        ) * 100.0
        if mode == "light":
            # Rule 1.2.1 is a light-table clause (its "current values already
            # satisfy" assertion holds only there); gate it on light only.
            bound = LADDER_BOUNDS[l]
            ok = y_step >= bound
            verdict = f"{'>=' + format(bound, '.0f') + ' pp':<8}{'PASS' if ok else 'FAIL'}"
            if not ok:
                violations.append(
                    f"{l}→{nxt} luminance step {y_step:.2f}pp < {bound:.0f}pp — rule 1.2.1"
                )
        else:
            verdict = f"{'n/a':<8}info"
        rows.append(
            f"{l + '→' + nxt:<10}{de:<10.4f}{y_step:<10.2f}{verdict}"
        )

    if report:  # full pairwise ΔE matrix (current levels × anchor levels)
        rows.append("")
        rows.append("full pairwise ΔE00 (rows=current, cols=anchor):")
        rows.append("      " + "".join(f"{a + '>':<10}" for a in _LEVELS))
        for l in _LEVELS:
            cells = "".join(
                f"{ciede2000(cur_lab[l], anc_lab[a]):<10.4f}" for a in _LEVELS
            )
            rows.append(f"{l + '<':<7}" + cells)

    print("\n".join(rows))

    if violations:
        print(f"\n[surface-ladder-de] FAIL — {len(violations)} violation(s):")
        for v in violations:
            print(f"  - {v}")
        print(
            "Deviation beyond ΔE≤2 needs design review (SPEC §1.2.2); "
            "measurement is ONLY this script's output, never eyeballed."
        )
        return 1
    passed_msg = (
        "ladder steps hold (1.2.1) and anchor regression within "
        f"ΔE≤{de_threshold:g} (1.2.2)"
        if mode == "light"
        else f"anchor regression within ΔE≤{de_threshold:g} (1.2.2); "
        "1.2.1 is a light-table bound, not gated for dark"
    )
    print(f"[surface-ladder-de] PASS — {passed_msg}")
    return 0


# ── self-test: Sharma et al. 2005 supplementary CIEDE2000 test data ─────────

# (L1, a1, b1, L2, a2, b2, published ΔE00) — canonical pairs, 4-dp expected.
_SHARMA_PAIRS = (
    (50.0000, 2.6772, -79.7751, 50.0000, 0.0000, -82.7485, 2.0425),
    (50.0000, 3.1571, -77.2803, 50.0000, 0.0000, -82.7485, 2.8615),
    (50.0000, 2.8361, -74.0200, 50.0000, 0.0000, -82.7485, 3.4412),
    (50.0000, -1.3802, -84.2814, 50.0000, 0.0000, -82.7485, 1.0000),
    (50.0000, 0.0000, 0.0000, 50.0000, -1.0000, 2.0000, 2.3669),
    (50.0000, -1.0000, 2.0000, 50.0000, 0.0000, 0.0000, 2.3669),
    (50.0000, 2.4900, -0.0010, 50.0000, -2.4900, 0.0009, 7.1792),
    (50.0000, 2.4900, -0.0010, 50.0000, -2.4900, 0.0011, 7.2195),
    (50.0000, -0.0010, 2.4900, 50.0000, 0.0009, -2.4900, 4.8045),
    (50.0000, -0.0010, 2.4900, 50.0000, 0.0011, -2.4900, 4.7461),
    (50.0000, 2.5000, 0.0000, 50.0000, 0.0000, -2.5000, 4.3065),
    (50.0000, 2.5000, 0.0000, 73.0000, 25.0000, -18.0000, 27.1492),
    (50.0000, 2.5000, 0.0000, 61.0000, -5.0000, 29.0000, 22.8977),
    (50.0000, 2.5000, 0.0000, 56.0000, -27.0000, -3.0000, 31.9030),
    (50.0000, 2.5000, 0.0000, 58.0000, 24.0000, 15.0000, 19.4535),
    (50.0000, 2.5000, 0.0000, 50.0000, 3.1736, 0.5854, 1.0000),
    (50.0000, 2.5000, 0.0000, 50.0000, 3.2972, 0.0000, 1.0000),
    (50.0000, 2.5000, 0.0000, 50.0000, 1.8634, 0.5757, 1.0000),
    (50.0000, 2.5000, 0.0000, 50.0000, 3.2592, 0.3350, 1.0000),
    (60.2574, -34.0099, 36.2677, 60.4626, -34.1751, 39.4387, 1.2644),
    (63.0109, -31.0961, -5.8663, 62.8187, -29.7946, -4.0864, 1.2630),
    (61.2901, 3.7196, -5.3901, 61.4292, 2.2480, -4.9620, 1.8731),
    (35.0831, -44.1164, 3.7933, 35.0232, -40.0716, 1.5901, 1.8645),
    (22.7233, 20.0904, -46.6940, 23.0331, 14.9730, -42.5619, 2.0373),
    (36.4612, 47.8580, 18.3852, 36.2715, 50.5065, 21.2231, 1.4146),
    (90.8027, -2.0831, 1.4410, 91.1528, -1.6435, 0.0447, 1.4441),
    (90.9257, -0.5406, -0.9208, 88.6381, -0.8985, -0.7239, 1.5381),
    (6.7747, -0.2908, -2.4247, 5.8714, -0.0985, -2.2286, 0.6377),
    (2.0776, 0.0795, -1.1350, 0.9033, -0.0636, -0.5514, 0.9082),
)

_TOL = 1.5e-4  # published to 4 dp


def self_test() -> int:
    failures: list[str] = []

    # 1) CIEDE2000 against the published Sharma supplementary dataset.
    for i, (L1, a1, b1, L2, a2, b2, expected) in enumerate(_SHARMA_PAIRS, 1):
        got = ciede2000((L1, a1, b1), (L2, a2, b2))
        if abs(got - expected) > _TOL:
            failures.append(
                f"pair {i}: ΔE00={got:.6f} expected {expected:.4f} (tol {_TOL})"
            )

    # 2) sRGB → Lab sanity: pure white must land on the Lab achromatic point.
    L, a, b = rgb_to_lab((255.0, 255.0, 255.0))
    if abs(L - 100.0) > _TOL or abs(a) > _TOL or abs(b) > _TOL:
        failures.append(f"white → Lab=({L:.4f},{a:.4f},{b:.4f}), want (100,0,0)")

    # 3) Anchor self-consistency: identical hexes must give ΔE00 = 0.
    for l in _LEVELS:
        if delta_e_hex(LIGHT_ANCHOR[l], LIGHT_ANCHOR[l]) > 1e-12:
            failures.append(f"self-ΔE nonzero for {l}")

    # 4) The B2-2 light snapshot must satisfy its own gate (guards accidental
    #    anchor corruption: an anchor edit breaking the shipped palette fails here).
    if run_gate(dict(LIGHT_ANCHOR), LIGHT_ANCHOR, "light", "self-test", report=False) != 0:
        failures.append("light anchor vs itself does not pass the gate")

    if failures:
        print(f"[surface-ladder-de] SELF-TEST FAIL — {len(failures)} case(s):")
        for f_ in failures:
            print(f"  - {f_}")
        return 1
    print(
        f"[surface-ladder-de] SELF-TEST PASS — {len(_SHARMA_PAIRS)} Sharma-2005 "
        "CIEDE2000 pairs reproduced (tol 1.5e-4); white→Lab(100,0,0); anchor self-gate green"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("light", "dark"),
        default="light",
        help="which brightness ladder to check (default light — the A1.6 anchor)",
    )
    parser.add_argument(
        "--current",
        default=None,
        help="explicit S0,S1,S2,S3 hex list (tonal-pipeline output); "
        "default parses theme_manager.dart",
    )
    parser.add_argument(
        "--theme-manager",
        type=Path,
        default=DEFAULT_THEME_MANAGER,
        help="path to theme_manager.dart for the default current-value source",
    )
    parser.add_argument(
        "--anchor-de",
        type=float,
        default=DE_THRESHOLD,
        help="anchor equivalence threshold, ΔE00 (default 2.0, SPEC §1.2.2)",
    )
    parser.add_argument("--report", action="store_true", help="print full ΔE tables")
    parser.add_argument("--self-test", action="store_true", help="run Sharma-2005 dataset test")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    anchor = LIGHT_ANCHOR if args.mode == "light" else DARK_ANCHOR
    if args.current:
        parts = [p for p in args.current.split(",") if p.strip()]
        if len(parts) != 4:
            print("[surface-ladder-de] FAIL — --current wants exactly 4 hexes: S0,S1,S2,S3", file=sys.stderr)
            return 2
        try:
            for p in parts:
                parse_hex(p)
        except ValueError as exc:
            print(f"[surface-ladder-de] FAIL — {exc}", file=sys.stderr)
            return 2
        current = {l: parse_hex(p) and "%02X%02X%02X" % parse_hex(p) for l, p in zip(_LEVELS, parts)}
        source = "--current"
    else:
        try:
            current = read_current_from_theme_manager(args.theme_manager, args.mode)
        except EnvironmentError as exc:
            print(f"[surface-ladder-de] FAIL — {exc}", file=sys.stderr)
            return 2
        source = str(args.theme_manager.relative_to(REPO_ROOT))
    return run_gate(current, anchor, args.mode, source, args.report, args.anchor_de)


if __name__ == "__main__":
    sys.exit(main())
