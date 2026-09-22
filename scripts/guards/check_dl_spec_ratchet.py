#!/usr/bin/env python3
"""DL-SPEC ratchet guard — machine-check arm of the unified design language SPEC v0.9.

Implements the「立即生效」machine-check clauses from `v3-output/DL-R3/ACCEPTANCE.md`
(one dimension per clause, plus the G1 duration/curve ratchets requested for the
batch-2 token migration gate). Companion to the existing UX-COMP / UI-TOKENS
ratchet guards, which are left untouched:

  dim id              clause   pattern / method
  ------------------- -------- --------------------------------------------------
  competitionNarrative A0.1    品类空位|无人占位|四合一.*事实  in docs/competition/ (zero-tolerance)
  colorsDotNative      A1.2    \\bColors\\.(?!white|black|transparent) in features (ratchet)
  coldColorLiteral     A1.3    0xFFRRGGBB with cold hue (165°–310°, sat/val floor),
                               features non-galaxy files, heuristic (ratchet)
  dsAccentAlias        A1.5    \\bDS\\.accent\\b repo-wide (ratchet; SPEC §1.4.2)
  offLadderDuration    A2.1    Duration(milliseconds: N), N ∉ ladder whitelist,
                               features (ratchet; new files zero-tolerance)
  bannedCurve          A2.2    Curves.elasticOut|bounceOut|elasticInOut repo-wide (ratchet)
  breathingController  A2.3    createBreathingController refs (ratchet; motion.dart
                               definition is the pinned baseline)
  confettiPerFile      A2.6    SparkleConfetti( per-file ≤1 (ratchet)
  particleBypass       A2.7    files containing particle-emission constructor calls but
                               no GlobalParticleCounter reference (ratchet; A2.7 bypass)
  textHardcodedZh      A3.2    Text('…中文…') literal in features (zero-tolerance; HEAD=0)
  gradientLiteral      A5.3    LinearGradient(|RadialGradient( in features (ratchet)
  dsGradientApiCalls   A5.3    \\bDS\\.<gradientApi>\\b refs repo mobile/lib (ratchet; SPEC §5.3
                               "ratchet 口径新维度" — DS gradient-API family, the blind
                               spot raw gradientLiteral cannot see)
  dsAccentGradientForbidden A1.5 \\bDS\\.accentGradient\\b refs (ratchet; the full-strength
                               brandSecondary gradient, alias family of the retired
                               DS.accent — SPEC §1.4.2)
  errorCopyOops        A6.6    Oops|something went wrong in mobile/lib (ratchet to zero)

Ratchet discipline (same as UX-COMP): per-file counts frozen in
`dl_spec_ratchet_baseline.json` — a file exceeding its baseline count, or a NEW
file exceeding the dimension's new-file allowance (0 everywhere except
confettiPerFile where mounting exactly 1 is legal), fails. Counts may only go
down; after a migration batch lowers counts run `--update-baseline` (refuses to
raise totals unless `--allow-raise` is passed — ACCEPTANCE A9.3).

CLI:
  python3 scripts/guards/check_dl_spec_ratchet.py                 # guard run
  python3 scripts/guards/check_dl_spec_ratchet.py --update-baseline
  python3 scripts/guards/check_dl_spec_ratchet.py --self-test     # end-to-end
                                                           # fixture test (<2s)

Read-only scanner: never modifies scanned sources. Exit 0 pass / 1 violations.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = Path(__file__).resolve().parent / "dl_spec_ratchet_baseline.json"

MOBILE_LIB_REL = "mobile/lib"
FEATURES_REL = "mobile/lib/features"
COMPETITION_REL = "docs/competition"

GENERATED_SUFFIXES = (".g.dart", ".freezed.dart")

_COMMENT_RE = re.compile(r"^\s*(?://|/\*|\*|///)")

# A2.1 duration ladder (SPEC §2.1 five-level ladder exploded to allowed ms values)
DURATION_WHITELIST = {50, 80, 100, 120, 150, 200, 250, 300, 320, 350, 400, 450, 480, 500, 600, 650, 700}

# A2.7 particle plumbing that IS the gate itself (exempt from bypass dim)
PARTICLE_INFRA_FILES = {
    "mobile/lib/core/design/widgets/global_particle_counter.dart",
    "mobile/lib/core/services/particle_pool.dart",
}


def _is_cold_color(hex6: str) -> bool:
    """A1.3 heuristic: blue/cyan/purple hue band with a saturation floor so
    warm neutrals (the batch-1 palette) and near-grays never trip it."""
    r, g, b = (int(hex6[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    hue_deg = h * 360
    return s >= 0.15 and l >= 0.10 and 165 <= hue_deg <= 310


class Dimension:
    def __init__(
        self,
        dim_id: str,
        clause: str,
        scope: str,
        counter,
        new_file_allowance: int = 0,
        zero_tolerance: bool = False,
        exempt_files: set[str] | None = None,
        file_filter=None,
    ):
        self.id = dim_id
        self.clause = clause
        self.scope = scope  # "mobile-lib" | "features" | "competition"
        self.counter = counter  # Callable[[Path, list[str]], int] -> count
        self.new_file_allowance = new_file_allowance
        self.zero_tolerance = zero_tolerance  # failing counts fail regardless of baseline wiring
        self.exempt_files = exempt_files or set()
        self.file_filter = file_filter  # Optional[Callable[[Path], bool]]


# ── per-dimension counters (line-based, comment lines skipped, like UX-COMP) ──

def _count_regex(pattern: re.Pattern[str]):
    def counter(_path: Path, lines: list[str]) -> int:
        return sum(len(pattern.findall(ln)) for ln in lines)

    return counter


_P_COMPETITION = re.compile(r"品类空位|无人占位|四合一.*事实")
_P_COLORS_DOT = re.compile(r"\bColors\.(?!white|black|transparent)")  # ACCEPTANCE A1.2 verbatim
_P_DS_ACCENT = re.compile(r"\bDS\.accent\b")
_OFF_LADDER_RE = re.compile(r"\bDuration\(\s*milliseconds:\s*(\d+)")


def _count_off_ladder(_path: Path, lines: list[str]) -> int:
    return sum(
        1
        for ln in lines
        for m in _OFF_LADDER_RE.finditer(ln)
        if int(m.group(1)) not in DURATION_WHITELIST
    )


_P_BANNED_CURVE = re.compile(r"\bCurves\.(?:elasticOut|bounceOut|elasticInOut)\b")
_P_BREATHING = re.compile(r"\bcreateBreathingController\b")
_P_CONFETTI = re.compile(r"\bSparkleConfetti\(")
_P_GRADIENT = re.compile(r"\b(?:LinearGradient|RadialGradient)\(")
# DS gradient-API family (design_system.dart `// Gradients` block + role/task
# helpers). Deliberately name-enumerated, not `\bDS\.\w*Gradient\b`, so a future
# getter must be added here consciously. Definitions inside design_system.dart
# itself (`static LinearGradient get accentGradient`) carry no `DS.` prefix and
# never match.
_P_DS_GRADIENT_API = re.compile(
    r"\bDS\.(?:"
    r"secondaryGradientDark|secondaryGradient|"  # longest first (trailing \b)
    r"primaryGradient|accentGradient|infoGradient|warningGradient|"
    r"successGradient|errorGradient|cardGradientNeutral|deepSpaceGradient|"
    r"flameGradient|pageGradientForRole|getTaskGradient"
    r")\b"
)
_P_DS_ACCENT_GRADIENT = re.compile(r"\bDS\.accentGradient\b")
_P_ERROR_OOPS = re.compile(r"Oops|something went wrong")
_P_TEXT_ZH = re.compile(r"\bText\(\s*(['\"])(?:(?!\1).)*[\u4e00-\u9fff](?:(?!\1).)*\1")
_D_HEX_COLOR = re.compile(r"\b0xFF([0-9A-Fa-f]{6})\b")
_D_PARTICLE_CTOR = re.compile(r"\b\w*Particle\w*\s*\(")
_D_PARTICLE_GATE = re.compile(r"\bGlobalParticleCounter\b")


def _count_cold(_path: Path, lines: list[str]) -> int:
    return sum(
        1
        for ln in lines
        for m in _D_HEX_COLOR.finditer(ln)
        if _is_cold_color(m.group(1))
    )


def _count_particle_bypass(path: Path, lines: list[str]) -> int:
    """A2.7: emission constructor calls in a file that never routes through the
    GlobalParticleCounter gate. A compliant file (any GlobalParticleCounter ref)
    counts 0; a bypassing file is pinned at its emission-call count."""
    text = "\n".join(lines)
    if _D_PARTICLE_GATE.search(text):
        return 0
    return len(_D_PARTICLE_CTOR.findall(text))


def _non_galaxy(path: Path) -> bool:
    return "galaxy" not in path.as_posix()


DIMENSIONS: list[Dimension] = [
    Dimension("competitionNarrative", "A0.1", "competition", _count_regex(_P_COMPETITION), zero_tolerance=True),
    Dimension("colorsDotNative", "A1.2", "features", _count_regex(_P_COLORS_DOT)),
    Dimension("coldColorLiteral", "A1.3", "features", _count_cold, file_filter=_non_galaxy),
    Dimension("dsAccentAlias", "A1.5", "mobile-lib", _count_regex(_P_DS_ACCENT)),
    Dimension("offLadderDuration", "A2.1", "features", _count_off_ladder),
    Dimension("bannedCurve", "A2.2", "mobile-lib", _count_regex(_P_BANNED_CURVE)),
    Dimension("breathingController", "A2.3", "mobile-lib", _count_regex(_P_BREATHING)),
    Dimension("confettiPerFile", "A2.6", "mobile-lib", _count_regex(_P_CONFETTI), new_file_allowance=1),
    Dimension("particleBypass", "A2.7", "mobile-lib", _count_particle_bypass, exempt_files=PARTICLE_INFRA_FILES),
    Dimension("textHardcodedZh", "A3.2", "features", _count_regex(_P_TEXT_ZH), zero_tolerance=True),
    Dimension("gradientLiteral", "A5.3", "features", _count_regex(_P_GRADIENT)),
    Dimension("dsGradientApiCalls", "A5.3", "mobile-lib", _count_regex(_P_DS_GRADIENT_API)),
    Dimension("dsAccentGradientForbidden", "A1.5", "mobile-lib", _count_regex(_P_DS_ACCENT_GRADIENT)),
    Dimension("errorCopyOops", "A6.6", "mobile-lib", _count_regex(_P_ERROR_OOPS)),
]

DIM_IDS = [d.id for d in DIMENSIONS]


def _scope_root(repo_root: Path, scope: str) -> Path:
    if scope == "features":
        return repo_root / FEATURES_REL
    if scope == "competition":
        return repo_root / COMPETITION_REL
    return repo_root / MOBILE_LIB_REL


def _iter_scope_files(root: Path, dim: Dimension, repo_root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        files = [root]
    else:
        suffixes = ("*.md",) if dim.scope == "competition" else ("*.dart",)
        files = sorted(f for s in suffixes for f in root.rglob(s))
    out = []
    for f in files:
        if dim.scope != "competition" and f.name.endswith(GENERATED_SUFFIXES):
            continue
        if _rel_from_root(f, repo_root) in dim.exempt_files:
            continue
        if dim.file_filter and not dim.file_filter(f):
            continue
        out.append(f)
    return out


def _rel_from_root(path: Path, repo_root: Path) -> str:
    """Stable baseline key: path relative to the scan root (mobile/lib/…, docs/competition/…)."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _code_lines(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    if path.suffix == ".md":
        return text.splitlines()  # prose: every line counts
    return [ln for ln in text.splitlines() if not _COMMENT_RE.match(ln)]


def scan(repo_root: Path) -> dict[str, dict[str, int]]:
    """Per-file per-dimension counts for every dimension with any hits."""
    cache: dict[Path, list[str]] = {}
    result: dict[str, dict[str, int]] = {}
    for dim in DIMENSIONS:
        root = _scope_root(repo_root, dim.scope)
        for f in _iter_scope_files(root, dim, repo_root):
            if f not in cache:
                cache[f] = _code_lines(f)
            n = dim.counter(f, cache[f])
            if n:
                result.setdefault(_rel_from_root(f, repo_root), {})[dim.id] = n
    return result


def totals(counts: dict[str, dict[str, int]]) -> dict[str, int]:
    return {d: sum(c.get(d, 0) for c in counts.values()) for d in DIM_IDS}


def compare(
    current: dict[str, dict[str, int]], baseline_files: dict[str, dict[str, int]]
) -> list[str]:
    violations: list[str] = []
    for rel, c in sorted(current.items()):
        b = baseline_files.get(rel)
        if b is None:
            over = {
                d: c[d]
                for d in c
                if c[d] > _dim(d).new_file_allowance
            }
            if over:
                summary = ", ".join(f"{k}={v}" for k, v in sorted(over.items()))
                violations.append(f"NEW FILE {rel}: {summary}")
            continue
        for d in sorted(set(c) | set(b)):
            now, base = c.get(d, 0), b.get(d, 0)
            if now > base:
                tag = " [zero-tolerance clause]" if _dim(d).zero_tolerance else ""
                violations.append(f"{rel}: {d} {now} > baseline {base} (+{now - base}){tag}")
    return violations


_DIM_INDEX = {d.id: d for d in DIMENSIONS}


def _dim(dim_id: str) -> Dimension:
    return _DIM_INDEX[dim_id]


def update_baseline(repo_root: Path, baseline_path: Path, allow_raise: bool) -> int:
    current = scan(repo_root)
    current_totals = totals(current)
    old_totals = None
    if baseline_path.exists():
        old = json.loads(baseline_path.read_text(encoding="utf-8"))
        old_totals = totals(old.get("files", {}))
        raised = [d for d in DIM_IDS if current_totals[d] > old_totals[d]]
        if raised and not allow_raise:
            detail = ", ".join(f"{d}: {old_totals[d]} -> {current_totals[d]}" for d in raised)
            print(
                f"[dl-spec-ratchet] REFUSED — --update-baseline would RAISE totals ({detail}). "
                "Baselines only go down (ACCEPTANCE A9.3). Fix the code or pass --allow-raise."
            )
            print(
                "[dl-spec-ratchet] note: onboarding a NEW dimension legitimately grows its "
                "own total from 0; that is the one sanctioned --allow-raise use — verify "
                "no PRE-EXISTING dim's total moved, then re-run with --allow-raise."
            )
            return 1
        if raised and allow_raise:
            detail = ", ".join(f"{d}: {old_totals[d]} -> {current_totals[d]}" for d in raised)
            print(f"[dl-spec-ratchet] ALLOW-RAISE used — totals that rose: {detail}")
    payload = {
        "comment": (
            "Frozen ratchet baseline for check_dl_spec_ratchet.py (DL-R3 SPEC v0.9 "
            "immediately-effective clauses; dsGradientApiCalls/dsAccentGradientForbidden "
            "added by DS-GRADIENT @wt134 covering the DS gradient-API blind spot). Only "
            "lower via --update-baseline after a migration batch; never raise."
        ),
        "files": current,
    }
    baseline_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    arrow = f"{old_totals} -> " if old_totals else ""
    print(f"[dl-spec-ratchet] baseline updated: {arrow}{current_totals}")
    return 0


def run_guard(repo_root: Path, baseline_path: Path) -> int:
    if not baseline_path.exists():
        print(f"[dl-spec-ratchet] FAIL — baseline missing: {baseline_path}")
        return 1
    current = scan(repo_root)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")).get("files", {})
    violations = compare(current, baseline)
    if violations:
        print(
            f"[dl-spec-ratchet] FAIL — {len(violations)} ratchet violation(s); "
            "design-language debt may only decrease (v3-output/DL-R3/SPEC.md §9)"
        )
        for v in violations:
            print(f"  {v}")
        print(
            "\nAction: consume core/design tokens (SparkleColors/typo/motion ladder, "
            "SemanticPill, SparkleConfetti, GlobalParticleCounter). If a migration batch "
            "legitimately LOWERED counts, refresh baseline via:"
        )
        print("  python3 scripts/guards/check_dl_spec_ratchet.py --update-baseline")
        return 1
    ct = totals(current)
    bt = totals(baseline)
    print(
        "[dl-spec-ratchet] PASS — ratchet holds: "
        + ", ".join(f"{d}={ct[d]}/{bt[d]}" for d in DIM_IDS)
        + f" ({len(current)} files with debt)"
    )
    return 0


# ── self-test: end-to-end fixtures proving the guard catches violations ──────

def self_test() -> int:
    failures: list[str] = []

    def make_fixture() -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="dlspec-selftest-"))
        (tmp / "mobile/lib/features/demo/presentation").mkdir(parents=True)
        (tmp / "mobile/lib/core/design").mkdir(parents=True)
        (tmp / "docs/competition").mkdir(parents=True)
        return tmp

    def write_baseline(tmp: Path, files: dict) -> Path:
        bp = tmp / "baseline.json"
        bp.write_text(json.dumps({"files": files}, ensure_ascii=False), encoding="utf-8")
        return bp

    # Case 1 — clean fixture matching baseline: must PASS.
    tmp = make_fixture()
    try:
        (tmp / "mobile/lib/features/demo/presentation/ok_screen.dart").write_text(
            "class _X extends StatelessWidget {\n"
            "  // Color(0xFF5B7CFA) comment only\n"
            "  final d = Duration(milliseconds: 250);\n"
            "  final g = LinearGradient(colors: [])\n"
            "}\n",
            encoding="utf-8",
        )
        bp = write_baseline(
            tmp,
            {
                "mobile/lib/features/demo/presentation/ok_screen.dart": {
                    "gradientLiteral": 1,
                    "offLadderDuration": 0,
                    "coldColorLiteral": 0,
                }
            },
        )
        if run_guard(tmp, bp) != 0:
            failures.append("case1 clean fixture should PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Case 2 — new file stacking six violations: must FAIL with each dim named.
    tmp = make_fixture()
    try:
        bp = write_baseline(tmp, {})
        (
            tmp / "mobile/lib/features/demo/presentation/bad_screen.dart"
        ).write_text(
            "class _QuickActionPill extends StatelessWidget {\n"
            "  final a = Color(0xFF5B7CFA);            // coldColorLiteral\n"
            "  final b = Colors.teal;                  // colorsDotNative\n"
            "  final c = DS.accent;                    // dsAccentAlias\n"
            "  final d = Duration(milliseconds: 260);  // offLadderDuration\n"
            "  final e = Curves.elasticOut;            // bannedCurve\n"
            "  final f = Text('今日无任务');             // textHardcodedZh\n"
            "}\n",
            encoding="utf-8",
        )
        out: list[str] = []

        def run_capture() -> int:
            import contextlib
            import io

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = run_guard(tmp, bp)
            out.append(buf.getvalue())
            return code

        if run_capture() != 1:
            failures.append("case2 stacked-violation file should FAIL")
        for needle in (
            "coldColorLiteral",
            "colorsDotNative",
            "dsAccentAlias",
            "offLadderDuration",
            "bannedCurve",
            "textHardcodedZh",
        ):
            if needle not in out[0]:
                failures.append(f"case2 should flag {needle}")
        # A2.3 breathing call in a new file
        (tmp / "mobile/lib/core/design/breath_user.dart").write_text(
            "final c = AnimationSystem.createBreathingController(this);\n",
            encoding="utf-8",
        )
        out.clear()
        if run_capture() != 1 or "breathingController" not in out[0]:
            failures.append("case2b breathing call in new file should FAIL")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Case 3 — ratchet raise on a pinned file + zero-tolerance + allowance edges.
    tmp = make_fixture()
    try:
        pinned = "mobile/lib/features/demo/presentation/legacy_screen.dart"
        f = tmp / pinned
        f.write_text("final g = RadialGradient(radius: 1);\n", encoding="utf-8")
        bp = write_baseline(tmp, {pinned: {"gradientLiteral": 1}})
        f.write_text(
            "final g = RadialGradient(radius: 1);\n"
            "final h = LinearGradient(colors: []);\n",
            encoding="utf-8",
        )
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1 or "gradientLiteral 2 > baseline 1" not in buf.getvalue():
            failures.append("case3a pinned-file raise should FAIL")

        # zero-tolerance: one competition hit fails with baseline absent (count 1 > 0)
        (tmp / "docs/competition/story.md").write_text(
            "我们验证过的品类空位\n", encoding="utf-8"
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1 or "competitionNarrative" not in buf.getvalue():
            failures.append("case3b competition narrative hit should FAIL")

        # confetti allowance: new file with 1 mount passes, 2 fails
        # (restore the pinned file to its baseline content first)
        f.write_text("final g = RadialGradient(radius: 1);\n", encoding="utf-8")
        (tmp / "docs/competition/story.md").write_text("方向假设表述\n", encoding="utf-8")
        conf = tmp / "mobile/lib/features/demo/presentation/celebrate_screen.dart"
        conf.write_text("final c = SparkleConfetti(key: k);\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 0:
            failures.append("case3c new file with 1 confetti should PASS")
        conf.write_text(
            "final c = SparkleConfetti(key: k);\n"
            "final d = SparkleConfetti(key: j);\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1 or "confettiPerFile=2" not in buf.getvalue():
            failures.append("case3d new file with 2 confetti should FAIL")

        # particle bypass: emission ctor without GlobalParticleCounter fails;
        # adding the gate reference clears it (confetti file restored to legal 1)
        conf.write_text("final c = SparkleConfetti(key: k);\n", encoding="utf-8")
        part = tmp / "mobile/lib/features/demo/presentation/spark_layer.dart"
        part.write_text("final p = BlueParticle(count: 9);\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1 or "particleBypass=1" not in buf.getvalue():
            failures.append("case3e particle bypass should FAIL")
        part.write_text(
            "final p = BlueParticle(count: 9);\n"
            "if (GlobalParticleCounter.tryAddParticles(9)) {}\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 0:
            failures.append("case3f gated particle file should PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Case 4 — DS gradient-API dims: accent alias-family ban + family ratchet.
    tmp = make_fixture()
    try:
        import contextlib
        import io

        (tmp / "mobile/lib/core/design/widgets").mkdir(parents=True)
        pinned = "mobile/lib/core/design/widgets/legacy_widget.dart"
        f = tmp / pinned
        f.write_text("final g = DS.accentGradient;\n", encoding="utf-8")
        bp = write_baseline(
            tmp,
            {pinned: {"dsGradientApiCalls": 1, "dsAccentGradientForbidden": 1}},
        )

        def run_capture4() -> tuple[int, str]:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = run_guard(tmp, bp)
            return code, buf.getvalue()

        # a) any DS gradient API in a NEW file: allowance 0 → family dim fires
        new_f = tmp / "mobile/lib/features/demo/presentation/g_new_screen.dart"
        new_f.write_text("final g = DS.infoGradient;\n", encoding="utf-8")
        code, out = run_capture4()
        if code != 1 or "dsGradientApiCalls" not in out:
            failures.append("case4a new-file DS gradient API should FAIL")
        if "dsAccentGradientForbidden" in out:
            failures.append("case4a infoGradient must not trip the accent ban")
        new_f.unlink()

        # b) DS.accentGradient in a NEW file: BOTH the family dim and the
        #    accent alias-family ban fire (the gradientLiteral blind spot).
        new_f.write_text("final g = DS.accentGradient;\n", encoding="utf-8")
        code, out = run_capture4()
        if code != 1 or "dsAccentGradientForbidden" not in out or "dsGradientApiCalls" not in out:
            failures.append("case4b new-file accentGradient should FAIL both dims")
        new_f.unlink()

        # c) pinned file raising its family count: ratchet refuses.
        f.write_text(
            "final g = DS.accentGradient;\n"
            "final h = DS.secondaryGradientDark;\n",
            encoding="utf-8",
        )
        code, out = run_capture4()
        if code != 1 or "dsGradientApiCalls 2 > baseline 1" not in out:
            failures.append("case4c pinned-file gradient-API raise should FAIL")

        # d) restore pinned content: PASS (forbidden stays at its pin).
        f.write_text("final g = DS.accentGradient;\n", encoding="utf-8")
        code, out = run_capture4()
        if code != 0:
            failures.append("case4d restored pinned file should PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print(f"[dl-spec-ratchet] SELF-TEST FAIL — {len(failures)} case(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("[dl-spec-ratchet] SELF-TEST PASS — clean PASS, stacked violations, "
          "ratchet raise, zero-tolerance, confetti allowance, particle bypass, "
          "DS gradient-API dims all behave")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="rewrite baseline JSON from current counts (only after a batch LOWERED counts)",
    )
    parser.add_argument(
        "--allow-raise",
        action="store_true",
        help="with --update-baseline, permit raising totals (should never be needed)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="override scan root (self-tests / fixtures only)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="override baseline path (self-tests / fixtures only)",
    )
    parser.add_argument("--self-test", action="store_true", help="run end-to-end fixture tests")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    repo_root = (args.repo_root or REPO_ROOT).resolve()
    baseline_path = args.baseline or BASELINE_PATH
    if args.update_baseline:
        return update_baseline(repo_root, baseline_path, args.allow_raise)
    return run_guard(repo_root, baseline_path)


if __name__ == "__main__":
    sys.exit(main())
