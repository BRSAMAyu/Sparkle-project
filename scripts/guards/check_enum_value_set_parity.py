#!/usr/bin/env python3
"""Rule ENUM-PARITY: backend StrEnum ↔ mobile Dart enum 值集对账守卫。

背景：B06 实体真源审计（v3/06_agent_fleet/B06_ENTITY_TRUTH_BASELINE.md §4 建议 1）
——proto/DB/身份三块单源治理执行良好，但 backend StrEnum ↔ mobile Dart enum 是
纯手工镜像段，此前无任何常驻守卫覆盖；V3-FIX-259（StreakDayStatus.WEAK 四层断链）
与 V3-FIX-260（AchievementType.PLANNING 单面新增）都是该空档产物。本守卫封堵空档
防再发：本卡不做值修复（修复属 wt539 / FIX-260 后续卡）。

机制：
- 对「双面都存在」的枚举族做值集 diff（FAMILIES 显式映射表，家族真源以 backend
  app/models/ 与 app/core/run_state_machine.py 的 StrEnum 为准）：
  * backend 值集 ⊄ mobile 可解析 wire 值集，且 mobile 无 unknown 哨兵兜底 → FAIL
    （EP001，列出差集）；
  * mobile 有 unknown 哨兵兜底 → 解析不崩，降级 WARN（EP001T，仍应尽快对齐）；
  * mobile 多余值 → WARN（EP002）；
  * 声明了哨兵但 mobile 侧实际不存在该哨兵 → FAIL（EP005，安全网名存实亡）；
  * 单源直通族（如 RunStatus，引擎持有、mobile 字符串直通）在 mobile 出现同名
    Dart enum → FAIL（EP003，第二真源苗头）。
- 已知断链豁免（KNOWN_DRIFT）：显式 allowlist 段，含修复卡号、归属与到期日；
  命中豁免的 FAIL 照常打印（KNOWN-DRIFT 行，绝不静默跳过）；到期后豁免自动失效
  重新变红，提示删豁免或续期。映射完整性问题（EP004）不适用豁免——守卫必须始终
  指向真实代码。
- --self-test：构造临时双面样本红绿自证全部判定路径。

登记：scripts/rule_guard_manifest.tsv（Rule ENUM-PARITY）。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
MOBILE_ROOT = REPO_ROOT / "mobile"
MODELS_DIR = BACKEND_ROOT / "app" / "models"

TODAY = _dt.date.today()

# ---------------------------------------------------------------------------
# 家族映射表：family → backend(class@file) ↔ mobile(enum@file)
# mobile 侧路径相对 MOBILE_ROOT，backend 侧路径相对 BACKEND_ROOT。
# unknown_sentinel：mobile 枚举里的兜底哨兵标识符（execution_intent_model.dart
# 的 unknown 哨兵是仓内范式，B06 正面样例）。
# mode="passthrough"：单源设计族——mobile 不得定义同名镜像 enum（RunStatus：
# 状态机真源在引擎，网关零复制、mobile 只读字符串直通，B06 §1 agent_run 行）。
# ---------------------------------------------------------------------------
FAMILIES: dict[str, dict] = {
    "TaskType": {
        "backend": ("app/models/task.py", "TaskType"),
        "mobile": ("lib/shared/entities/task_model.dart", "TaskType"),
        "mode": "dual",
    },
    "TaskStatus": {
        "backend": ("app/models/task.py", "TaskStatus"),
        "mobile": ("lib/shared/entities/task_model.dart", "TaskStatus"),
        "mode": "dual",
    },
    "SubTaskStatus": {
        "backend": ("app/models/task.py", "SubTaskStatus"),
        "mobile": ("lib/shared/entities/subtask_model.dart", "SubTaskStatus"),
        "mode": "dual",
    },
    "ExecutionIntentStatus": {
        "backend": ("app/models/execution_intent.py", "ExecutionIntentStatus"),
        "mobile": (
            "lib/features/task/data/models/execution_intent_model.dart",
            "ExecutionIntentStatus",
        ),
        "mode": "dual",
        "unknown_sentinel": "unknown",
    },
    "TrustLevel": {
        # backend 名 TrustLevel，mobile 名 ExecutionTrustLevel（同名不同形，映射表钉死）
        "backend": ("app/models/execution_intent.py", "TrustLevel"),
        "mobile": (
            "lib/features/task/data/models/execution_intent_model.dart",
            "ExecutionTrustLevel",
        ),
        "mode": "dual",
        "unknown_sentinel": "unknown",
    },
    "AchievementRarity": {
        "backend": ("app/models/achievement.py", "AchievementRarity"),
        "mobile": ("lib/shared/entities/achievement_model.dart", "AchievementRarity"),
        "mode": "dual",
    },
    "AchievementType": {
        "backend": ("app/models/achievement.py", "AchievementType"),
        "mobile": ("lib/shared/entities/achievement_model.dart", "AchievementType"),
        "mode": "dual",
    },
    "VisualEffectType": {
        "backend": ("app/models/achievement.py", "VisualEffectType"),
        "mobile": ("lib/shared/entities/achievement_model.dart", "VisualEffectType"),
        "mode": "dual",
    },
    "ContractStatus": {
        "backend": ("app/models/achievement.py", "ContractStatus"),
        "mobile": ("lib/shared/entities/achievement_model.dart", "ContractStatus"),
        "mode": "dual",
    },
    "StreakDayStatus": {
        "backend": ("app/models/achievement.py", "StreakDayStatus"),
        "mobile": ("lib/shared/entities/achievement_model.dart", "StreakDayStatus"),
        "mode": "dual",
    },
    "MessageRole": {
        "backend": ("app/models/chat.py", "MessageRole"),
        "mobile": ("lib/features/chat/data/models/chat_message_model.dart", "MessageRole"),
        "mode": "dual",
    },
    "PlanType": {
        # 真源 models/plan.py；backend/app/tools/schemas.py 另有一份工具参数用
        # PlanType/PlanStage（仓内既存副本，当前值集一致）——不在本守卫范围
        "backend": ("app/models/plan.py", "PlanType"),
        "mobile": ("lib/features/plan/data/models/plan_model.dart", "PlanType"),
        "mode": "dual",
    },
    "PlanStage": {
        "backend": ("app/models/plan.py", "PlanStage"),
        "mobile": ("lib/features/plan/data/models/plan_model.dart", "PlanStage"),
        "mode": "dual",
    },
    "PlanPriority": {
        "backend": ("app/models/plan.py", "PlanPriority"),
        "mobile": ("lib/features/plan/data/models/plan_model.dart", "PlanPriority"),
        "mode": "dual",
    },
    "RunStatus": {
        "backend": ("app/core/run_state_machine.py", "RunStatus"),
        "mode": "passthrough",
    },
}

# ---------------------------------------------------------------------------
# 已知断链豁免清单（显式 allowlist——修复落地后必须删除对应条目，不许静默跳过：
# 豁免命中照样打印 KNOWN-DRIFT 行；过期后自动失效重新变红）。
#   expiry：UTC 日期。到期日选官方截止（比赛提交 2026-10-07）：
#   到期未修 = 守卫重新变红，逼一次显式续期决策而非无限期忍耐。
# 只对 EP001（mobile 缺值）生效；映射完整性（EP004）不适用豁免。
# ---------------------------------------------------------------------------
KNOWN_DRIFT: dict[str, dict] = {
    "StreakDayStatus": {
        "fix": "V3-FIX-259",
        "owner": "wt539 在航",
        "expiry": _dt.date(2026, 10, 7),
        "note": "mobile StreakDayStatus 缺 weak（四层断链，台账 V3-FIX-259）",
    },
    "AchievementType": {
        "fix": "V3-FIX-260",
        "owner": "待派",
        "expiry": _dt.date(2026, 10, 7),
        "note": "mobile AchievementType 缺 planning（单面新增，台账 V3-FIX-260）",
    },
}

# ---------------------------------------------------------------------------
# 解析器
# ---------------------------------------------------------------------------

PY_CLASS_RE = re.compile(r"^class\s+(?P<name>\w+)\s*\(\s*(?:enum\.)?StrEnum\s*\)\s*:", re.MULTILINE)
PY_MEMBER_RE = re.compile(
    r"^\s+(?P<member>[A-Z][A-Z0-9_]*)\s*(?::\s*[\w\.]+\s*)?=\s*[\"'](?P<value>[^\"']*)[\"']",
    re.MULTILINE,
)


def extract_python_str_enum(root: Path, rel_path: str, class_name: str) -> dict[str, str] | None:
    """从 Python 源码抽 StrEnum 类的 {member: value}；类不存在返回 None。

    纯文本解析不 import（守卫运行环境不保证 backend 依赖齐全）；遇到类内
    def（如 __new__）或下一个顶层 class 即停，避免把方法体当成员。
    """
    path = root / rel_path
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    for m in PY_CLASS_RE.finditer(text):
        if m.group("name") != class_name:
            continue
        body_start = m.end()
        next_boundary = len(text)
        nxt = PY_CLASS_RE.search(text, body_start)
        if nxt:
            next_boundary = nxt.start()
        body = text[body_start:next_boundary]
        members: dict[str, str] = {}
        for line in body.splitlines():
            if re.match(r"^\s+def\s", line):
                break  # 类内方法（如 __new__）之后不再是成员区
            pm = PY_MEMBER_RE.match(line)
            if pm:
                members[pm.group("member")] = pm.group("value")
        return members
    return None


@dataclass
class DartEnum:
    identifiers: set[str] = field(default_factory=set)
    wire_values: set[str] = field(default_factory=set)


_DART_ENUM_HEAD_RE = r"\benum\s+{name}\s*\{{"
_DART_JSON_VALUE_RE = re.compile(r"@JsonValue\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
_DART_CTOR_ARG_RE = re.compile(r"^\s*(\w+)\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.MULTILINE)
_DART_CASE_RE = re.compile(r"case\s+['\"]([^'\"]+)['\"]")
_DART_FUNC_RET_RE = r"\b{name}\s+\w+\s*\([^)]*\)\s*(?:async\s*)?\{{"


def _brace_span(text: str, open_idx: int) -> tuple[int, int]:
    """返回 (body_start, body_end)，open_idx 指向 '{'。"""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return open_idx + 1, i
    return open_idx + 1, len(text)


def extract_dart_enum(root: Path, rel_path: str, enum_name: str) -> DartEnum | None:
    """抽 Dart enum 的标识符集与可接受 wire 值集；不存在返回 None。

    wire 值集 = @JsonValue 注解值 ∪ enhanced-enum 构造器字符串实参 ∪
    返回该 enum 的解析函数里的 case 字面量；三者全空时回退为标识符本身
    （json_serializable 默认按 name 编解码，如 MessageRole）。
    """
    path = root / rel_path
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    m = re.search(_DART_ENUM_HEAD_RE.format(name=re.escape(enum_name)), text)
    if not m:
        return None
    body_start, body_end = _brace_span(text, m.end() - 1)
    body = text[body_start:body_end]

    # 常量区：enhanced enum 以 ';' 结束常量列表（其后是成员/方法）。
    semi = body.find(";")
    constants = body if semi < 0 else body[:semi]
    constants_no_comments = re.sub(r"//[^\n]*", "", constants)

    result = DartEnum()
    result.wire_values.update(_DART_JSON_VALUE_RE.findall(constants))
    result.wire_values.update(m2.group(2) for m2 in _DART_CTOR_ARG_RE.finditer(constants_no_comments))

    # 标识符：剥掉注解与构造器实参后按行取行首词。
    stripped = _DART_JSON_VALUE_RE.sub("", constants_no_comments)
    stripped = _DART_CTOR_ARG_RE.sub("", stripped)
    for line in stripped.splitlines():
        lm = re.match(r"^\s*([a-zA-Z_]\w*)\s*,?\s*$", line)
        if lm and lm.group(1) not in {"const", "final", "static"}:
            result.identifiers.add(lm.group(1))

    # 解析函数 case 字面量（_parseExecutionStatus 范式；跳过 enum 体内的非常规命中）。
    for fm in re.finditer(_DART_FUNC_RET_RE.format(name=re.escape(enum_name)), text):
        if fm.start() < body_start:
            continue
        f_start, f_end = _brace_span(text, text.find("{", fm.end() - 1))
        result.wire_values.update(_DART_CASE_RE.findall(text[f_start:f_end]))

    # 三形态全空 → json_serializable 默认按标识符编解码（如 MessageRole）。
    if not result.wire_values:
        result.wire_values = set(result.identifiers)
    return result


def inventory_unmapped_backend_enums(backend_root: Path) -> list[str]:
    """盘点 app/models/ 下未进映射表的 StrEnum 类（INFO 展示，便于后续扩表）。"""
    known = {spec["backend"][1] for spec in FAMILIES.values() if "backend" in spec}
    found: list[str] = []
    if not (backend_root / "app" / "models").exists():
        return found
    for py in sorted((backend_root / "app" / "models").rglob("*.py")):
        text = py.read_text(encoding="utf-8")
        for m in PY_CLASS_RE.finditer(text):
            # 名为 StrEnum 的是项目内基类定义本身，不是业务枚举族
            if m.group("name") not in known and m.group("name") != "StrEnum":
                rel = py.relative_to(backend_root)
                found.append(f"{m.group('name')} ({rel})")
    return found


# ---------------------------------------------------------------------------
# 对账
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    family: str
    code: str  # EP001 / EP001T / EP002 / EP003 / EP004 / EP005
    severity: str  # FAIL / WARN
    message: str
    exempt: str | None = None  # 豁免标注（fix 号），非 None 则不影响退出码


def _family_check(
    family: str,
    spec: dict,
    backend_root: Path,
    mobile_root: Path,
    allowlist: dict[str, dict],
    today: _dt.date,
) -> list[Finding]:
    findings: list[Finding] = []
    mode = spec.get("mode", "dual")
    be_path, be_class = spec["backend"]

    def _exempt_if_allowed(f: Finding) -> Finding:
        entry = allowlist.get(family)
        if f.severity == "FAIL" and f.code == "EP001" and entry is not None:
            if today <= entry["expiry"]:
                f.exempt = f"{entry['fix']}（{entry['owner']}，到期 {entry['expiry'].isoformat()}）"
            else:
                f.message += (
                    f"  [豁免已过期 {entry['expiry'].isoformat()}（{entry['fix']}，"
                    f"{entry['owner']}）——修复应已落地，请删豁免条目或显式续期]"
                )
        return f

    py_members = extract_python_str_enum(backend_root, be_path, be_class)
    if py_members is None:
        findings.append(
            Finding(
                family,
                "EP004",
                "FAIL",
                f"映射完整性：backend {be_class} 未找到（{be_path}）——映射表必须指向真实代码，不得豁免",
            )
        )
        return findings
    be_values = set(py_members.values())
    if len(py_members) != len(be_values):
        dupes = sorted(v for v in be_values if list(py_members.values()).count(v) > 1)
        findings.append(
            Finding(
                family,
                "EP004",
                "FAIL",
                f"映射完整性：backend {be_class} 存在重复值 {dupes}——StrEnum 值必须唯一",
            )
        )

    if mode == "passthrough":
        # 在 mobile 全 lib 找同名 enum（单源族出现任何镜像定义即违规）
        mirror = _find_dart_enum_anywhere(mobile_root, be_class)
        if mirror is not None:
            findings.append(
                _exempt_if_allowed(
                    Finding(
                        family,
                        "EP003",
                        "FAIL",
                        f"单源直通族 {family} 在 mobile 出现镜像 enum {be_class}"
                        "——该族真源在 backend（引擎持有/mobile 字符串直通），禁止手工镜像",
                    )
                )
            )
        else:
            findings.append(
                Finding(
                    family,
                    "OK",
                    "PASS",
                    f"单源直通族 {family}（backend {len(be_values)} 值）mobile 无镜像 enum ✓",
                )
            )
        return findings

    mo_rel, mo_class = spec["mobile"]
    dart = extract_dart_enum(mobile_root, mo_rel, mo_class)
    if dart is None:
        findings.append(
            Finding(
                family,
                "EP004",
                "FAIL",
                f"映射完整性：mobile enum {mo_class} 未找到（{mo_rel}）——映射表必须指向真实代码，不得豁免",
            )
        )
        return findings

    sentinel = spec.get("unknown_sentinel")
    has_sentinel = sentinel is not None and sentinel in dart.identifiers
    if sentinel is not None and not has_sentinel:
        findings.append(
            Finding(
                family,
                "EP005",
                "FAIL",
                f"映射表声明 mobile {mo_class} 应有 unknown 哨兵兜底，但实际不存在——安全网失效",
            )
        )

    missing = sorted(be_values - dart.wire_values)
    if missing:
        if has_sentinel:
            findings.append(
                Finding(
                    family,
                    "EP001T",
                    "WARN",
                    f"backend {be_class} 值集 ⊄ mobile {mo_class}：缺 {missing}"
                    f"——mobile unknown 哨兵兜底解析不崩，降级 WARN，仍应尽快对齐",
                )
            )
        else:
            findings.append(
                _exempt_if_allowed(
                    Finding(
                        family,
                        "EP001",
                        "FAIL",
                        f"backend {be_class} 值集 ⊄ mobile {mo_class}：缺 {missing}"
                        f"（mobile 无 unknown 哨兵兜底，下发即解析崩）",
                    )
                )
            )

    extra = sorted(dart.wire_values - be_values)
    if extra:
        findings.append(
            Finding(
                family,
                "EP002",
                "WARN",
                f"mobile {mo_class} 有 backend {be_class} 之外的 wire 值 {extra}",
            )
        )

    if not any(f.code != "OK" for f in findings):
        findings.append(
            Finding(
                family,
                "OK",
                "PASS",
                f"{family}: backend {len(be_values)} 值 = mobile {len(dart.wire_values)} 值对齐 ✓",
            )
        )
    return findings


def _find_dart_enum_anywhere(mobile_root: Path, enum_name: str) -> Path | None:
    if not mobile_root.exists():
        return None
    pat = re.compile(rf"\benum\s+{re.escape(enum_name)}\b")
    for dart in sorted(mobile_root.rglob("*.dart")):
        parts = dart.parts
        if any(p in {"gen", ".dart_tool", "build"} for p in parts):
            continue
        if pat.search(dart.read_text(encoding="utf-8")):
            return dart
    return None


def run_checks(
    backend_root: Path,
    mobile_root: Path,
    families: dict[str, dict] | None = None,
    allowlist: dict[str, dict] | None = None,
    today: _dt.date | None = None,
) -> list[Finding]:
    families = families if families is not None else FAMILIES
    allowlist = allowlist if allowlist is not None else KNOWN_DRIFT
    today = today or TODAY
    findings: list[Finding] = []
    for family in sorted(families):
        findings.extend(_family_check(family, families[family], backend_root, mobile_root, allowlist, today))
    return findings


# ---------------------------------------------------------------------------
# 自证（--self-test）：临时双面样本红绿验证全部判定路径
# ---------------------------------------------------------------------------


def _write_python_enum(root: Path, rel: str, cls: str, members: list[tuple[str, str]]) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f'    {m} = "{v}"' for m, v in members)
    # 同文件多类：追加而非覆盖（fixture 各族共用 a.py）
    with p.open("a", encoding="utf-8") as fh:
        fh.write(f"import enum\n\n\nclass {cls}(enum.StrEnum):\n{body}\n")


def _write_dart_enum(
    root: Path,
    rel: str,
    enum_name: str,
    *,
    json_values: list[str] | None = None,
    ctor: list[tuple[str, str]] | None = None,
    plain: list[str] | None = None,
    sentinel: str | None = None,
    parse_cases: list[str] | None = None,
) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [f"enum {enum_name} {{", ""]
    if json_values:
        for v in json_values:
            lines.append(f"  @JsonValue('{v}')")
            lines.append(f"  {v},")
    if ctor:
        lines[-1] = ""
        for ident, v in ctor:
            lines.append(f"  {ident}('{v}'),")
    if plain:
        for ident in plain:
            lines.append(f"  {ident},")
    if sentinel:
        lines.append(f"  {sentinel},")
    lines.append("}")
    if parse_cases:
        lines.append("")
        lines.append(f"{enum_name} parse{enum_name}(String? value) {{")
        lines.append("  switch (value) {")
        for c in parse_cases:
            lines.append(f"    case '{c}':")
            lines.append(f"      return {enum_name}.{c}Camel;")
        lines.append("    default:")
        if sentinel:
            lines.append(f"      return {enum_name}.{sentinel};")
        lines.append("  }")
        lines.append("}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def self_test() -> int:
    """构造临时双面样本，逐路径断言判定结果；失败打印实录并返回 1。"""
    with tempfile.TemporaryDirectory() as td:
        be = Path(td) / "backend"
        mo = Path(td) / "mobile"
        today = _dt.date(2026, 9, 25)
        expired_allow: dict[str, dict] = {
            "Alpha": {
                "fix": "V3-FIX-XXX",
                "owner": "test",
                "expiry": _dt.date(2026, 1, 1),
                "note": "expired",
            },
        }

        # 用例 1：对齐族 → PASS
        # 用例 2：backend 多值 + mobile 无哨兵 → FAIL EP001（未豁免）
        # 用例 3：backend 多值 + mobile 有哨兵 → WARN EP001T（不 FAIL）
        # 用例 4：mobile 多余 wire 值 → WARN EP002
        # 用例 5：豁免在期 → FAIL 降为 exempt；豁免过期 → 仍 FAIL
        # 用例 6：passthrough 族 mobile 出现镜像 enum → FAIL EP003
        # 用例 7：映射完整性（backend 类缺失）→ FAIL EP004 且不受豁免影响
        families = {
            "Aligned": {
                "backend": ("app/models/a.py", "Aligned"),
                "mobile": ("lib/a.dart", "Aligned"),
                "mode": "dual",
            },
            "Alpha": {
                "backend": ("app/models/a.py", "Alpha"),
                "mobile": ("lib/b.dart", "Alpha"),
                "mode": "dual",
            },
            "Beta": {
                "backend": ("app/models/a.py", "Beta"),
                "mobile": ("lib/c.dart", "Beta"),
                "mode": "dual",
                "unknown_sentinel": "unknown",
            },
            "Gamma": {
                "backend": ("app/models/a.py", "Gamma"),
                "mobile": ("lib/d.dart", "Gamma"),
                "mode": "dual",
            },
            "Delta": {
                "backend": ("app/models/a.py", "Delta"),
                "mobile": ("lib/e.dart", "Delta"),
                "mode": "dual",
            },
            "RunLike": {
                "backend": ("app/models/a.py", "RunLike"),
                "mode": "passthrough",
            },
            "Ghost": {
                "backend": ("app/models/a.py", "NoSuchBackendClass"),
                "mobile": ("lib/f.dart", "Ghost"),
                "mode": "dual",
            },
        }

        def members(prefix: str, values: list[str]) -> list[tuple[str, str]]:
            return [(v.upper(), v) for v in [prefix] + values]

        _write_python_enum(be, "app/models/a.py", "Aligned", [("RED", "red"), ("GREEN", "green")])
        _write_dart_enum(mo, "lib/a.dart", "Aligned", json_values=["red", "green"])

        _write_python_enum(be, "app/models/a.py", "Alpha", members("alpha", ["x1", "x2"]))
        _write_dart_enum(mo, "lib/b.dart", "Alpha", json_values=["alpha", "x1"])

        _write_python_enum(be, "app/models/a.py", "Beta", members("beta", ["y1", "y2"]))
        _write_dart_enum(mo, "lib/c.dart", "Beta", json_values=["beta", "y1"], sentinel="unknown")

        _write_python_enum(be, "app/models/a.py", "Gamma", [("G1", "g1")])
        _write_dart_enum(mo, "lib/d.dart", "Gamma", json_values=["g1", "ghost_extra"])

        _write_python_enum(be, "app/models/a.py", "Delta", [("D1", "d1"), ("D2", "d2")])
        _write_dart_enum(mo, "lib/e.dart", "Delta", json_values=["d1"])

        _write_python_enum(be, "app/models/a.py", "RunLike", [("R1", "r1")])
        _write_dart_enum(mo, "lib/run_like.dart", "RunLike", plain=["r1"])  # 单源族的违例镜像

        # Ghost：backend 类不存在，映射完整性 FAIL；同时挂一份（无效的）豁免验证豁免不覆盖 EP004
        expired_allow["Ghost"] = expired_allow["Alpha"]

        all_findings = run_checks(be, mo, families, expired_allow, today=today)

        def sev_of(findings: list[Finding], family: str, code: str) -> tuple[str, str | None]:
            for f in findings:
                if f.family == family and f.code == code:
                    return f.severity, f.exempt
            return "<absent>", None

        checks: list[tuple[str, bool]] = []

        checks.append(("case1 对齐族 PASS", sev_of(all_findings, "Aligned", "OK")[0] == "PASS"))

        s, ex = sev_of(all_findings, "Alpha", "EP001")
        checks.append(("case2 缺值无哨兵 FAIL", s == "FAIL"))
        checks.append(("case2 未豁免", ex is None))

        s, ex = sev_of(all_findings, "Beta", "EP001T")
        checks.append(("case3 哨兵兜底 WARN 不 FAIL", s == "WARN"))
        checks.append(("case3 Beta 无 FAIL", all(f.severity != "FAIL" for f in all_findings if f.family == "Beta")))

        s, _ = sev_of(all_findings, "Gamma", "EP002")
        checks.append(("case4 mobile 多余值 WARN", s == "WARN"))

        s, ex = sev_of(all_findings, "Delta", "EP001")
        checks.append(("case5a 豁免过期仍 FAIL", s == "FAIL"))
        checks.append(("case5a 过期豁免不标 exempt", ex is None))
        checks.append(
            (
                "case5a 报文带过期提示",
                "豁免已过期" in next(f.message for f in all_findings if f.family == "Alpha" and f.code == "EP001"),
            )
        )

        s, _ = sev_of(all_findings, "RunLike", "EP003")
        checks.append(("case6 passthrough 镜像 FAIL", s == "FAIL"))

        s, ex = sev_of(all_findings, "Ghost", "EP004")
        checks.append(("case7 映射完整性 FAIL", s == "FAIL"))
        checks.append(("case7 EP004 不受豁免", ex is None))

        # 用例 8：在期豁免 → FAIL 带 exempt 标注，exit 语义由调用方按 exempt 过滤
        live_allow = {
            "Delta": {
                "fix": "V3-FIX-YYY",
                "owner": "test",
                "expiry": _dt.date(2027, 1, 1),
                "note": "live",
            },
        }
        live_findings = run_checks(be, mo, families, live_allow, today=today)
        d = next(f for f in live_findings if f.family == "Delta" and f.code == "EP001")
        checks.append(("case5b 在期豁免标注 exempt", d.severity == "FAIL" and d.exempt is not None))

        # 用例 9：哨兵声明但缺失 → FAIL EP005
        _write_dart_enum(mo, "lib/c.dart", "Beta", json_values=["beta", "y1", "y2"])
        no_sent_findings = run_checks(be, mo, families, {}, today=today)
        s, _ = sev_of(no_sent_findings, "Beta", "EP005")
        checks.append(("case9 声明哨兵缺失 FAIL EP005", s == "FAIL"))
        # 同一对齐后 Beta 应无其他 FAIL（y2 已补）
        checks.append(
            ("case9 补值后 Beta 无 EP001", all(f.code != "EP001" for f in no_sent_findings if f.family == "Beta"))
        )

        # 用例 10：passthrough 无镜像 → PASS
        mo_no_mirror = Path(td) / "mobile_clean"
        mo_no_mirror.mkdir()
        clean_findings = run_checks(be, mo_no_mirror, {"RunLike": families["RunLike"]}, {}, today=today)
        checks.append(
            ("case10 passthrough 无镜像 PASS", any(f.code == "OK" and f.severity == "PASS" for f in clean_findings))
        )

        # 解析器回归：真实仓样本形态（enhanced enum 构造器 + JsonValue + parse-case）
        _write_dart_enum(
            mo,
            "lib/real.dart",
            "Real",
            json_values=["a_b"],
            ctor=[("cD", "C_D")],
            sentinel="unknown",
            parse_cases=["e_f"],
        )
        real = extract_dart_enum(mo, "lib/real.dart", "Real")
        checks.append(
            (
                "case11 Dart 解析器三形态",
                real is not None and real.wire_values == {"a_b", "C_D", "e_f"} and "unknown" in real.identifiers,
            )
        )
        py_real = extract_python_str_enum(
            be,
            "app/models/a.py",
            "Aligned",
        )
        checks.append(("case12 Python 解析器", py_real == {"RED": "red", "GREEN": "green"}))

        print("[Rule ENUM-PARITY] SELF-TEST 实录：")
        for label, ok in checks:
            mark = "PASS" if ok else "FAIL"
            print(f"  [{mark}] {label}")
        bad = [label for label, ok in checks if not ok]
        if bad:
            print(f"[Rule ENUM-PARITY] SELF-TEST FAIL ({len(bad)} 项): {bad}")
            return 1
        print(f"[Rule ENUM-PARITY] SELF-TEST PASS ({len(checks)} 项断言全绿)")
        return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true", help="临时双面样本红绿自证后退出")
    parser.add_argument(
        "--family",
        action="append",
        default=[],
        help="只对账指定家族（可多次）；默认全表",
    )
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    families = FAMILIES
    if args.family:
        unknown = [f for f in args.family if f not in FAMILIES]
        if unknown:
            print(f"[Rule ENUM-PARITY] FAIL - 未知家族: {unknown}（可用: {sorted(FAMILIES)}）")
            return 1
        families = {f: FAMILIES[f] for f in args.family}

    findings = run_checks(BACKEND_ROOT, MOBILE_ROOT, families, KNOWN_DRIFT, TODAY)

    fail = 0
    warn = 0
    exempt = 0
    for f in findings:
        if f.exempt:
            exempt += 1
            print(f"[Rule ENUM-PARITY] KNOWN-DRIFT {f.family}: {f.message}  [豁免: {f.exempt}]")
        elif f.code == "OK":
            print(f"[Rule ENUM-PARITY] {f.message}")
        else:
            print(f"[Rule ENUM-PARITY] {f.severity} {f.code} {f.family}: {f.message}")
        if f.severity == "FAIL" and not f.exempt:
            fail += 1
        elif f.severity == "WARN":
            warn += 1

    unmapped = inventory_unmapped_backend_enums(BACKEND_ROOT)
    if unmapped and not args.family:
        print(f"[Rule ENUM-PARITY] INFO 未进映射表的 backend StrEnum（不判失败，扩表候选）: {unmapped}")

    total = len(findings)
    if fail:
        print(f"[Rule ENUM-PARITY] FAIL - {total} 条结果：FAIL={fail} WARN={warn} 豁免={exempt}")
        return 1
    print(
        f"[Rule ENUM-PARITY] PASS - {total} 条结果：FAIL=0 WARN={warn} 豁免={exempt}"
        f"（豁免命中已显式列出，修复落地后删除 KNOWN_DRIFT 条目）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
