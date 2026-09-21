"""B-04 视觉基线截图命名规范。

canonical 文件名（GBNF）::

    <surface>__<state>__<persona>__<platform>__<viewport>__<sha8>.png

- 分隔符为**双下划线** `__`；各段自身只允许单下划线（`[a-z0-9_]+` 且不得含 `__`），
  因此 `split("__")` 无歧义。
- ``sha8`` = 构建 HEAD 的 git SHA 前 8 位十六进制。
- 示例::

    home__main__demo_data__android__412x916@2.6__aced25a2.png

设计动机：manifest 记录的每条目都要求可从文件名自证
（surface/state/persona/platform/viewport/build_sha8），文件即事实源，
manifest 负责补 sha256/bytes/captured_at 并供 verify 校验。
"""

from __future__ import annotations

import re

# 9 个 canonical surfaces（v3/04_ux 与任务卡 B-04 定义）
SURFACES = frozenset(
    {
        "onboarding",
        "home",
        "chat",
        "goal",
        "task",
        "memory",
        "galaxy",
        "profile",
        "settings",
    }
)

# 采集平台：Android 为本机 canonical 端；web 可选补充；iOS 本机不可采（平台限制，登记不采）。
PLATFORMS = frozenset({"android", "web", "ios"})

# 演示 persona：demo_data=演示账号（只读）；new_user=新注册号（onboarding/空态）。
PERSONAS = frozenset({"demo_data", "new_user", "guest"})

SCREENSHOT_SUFFIX = ".png"

# 单段字符集：小写字母/数字/单下划线，不得以下划线开头或结尾，不得含双下划线。
SEGMENT_RE = re.compile(r"^[a-z0-9]([a-z0-9_]*[a-z0-9])?$")
# sha8：8 位十六进制。
SHA8_RE = re.compile(r"^[0-9a-f]{8}$")
# viewport：宽x高@缩放（如 412x916@2.6）；也允许纯分辨率 412x916。
VIEWPORT_RE = re.compile(r"^[0-9]+x[0-9]+(@[0-9]+\.[0-9]+)?$")

NAMED_PARTS = ("surface", "state", "persona", "platform", "viewport", "sha8")


class NamingError(ValueError):
    """文件名/字段不符合 canonical 命名规范。"""


def validate_segment(part: str, value: str) -> str:
    """校验单段命名并原样返回；不合法抛 :class:`NamingError`。"""
    if not SEGMENT_RE.match(value) or "__" in value:
        raise NamingError(
            f"invalid {part} {value!r}: must match [a-z0-9](_?[a-z0-9])* and not contain '__'"
        )
    return value


def validate_sha8(sha8: str) -> str:
    if not SHA8_RE.match(sha8):
        raise NamingError(f"invalid sha8 {sha8!r}: expect 8 lowercase hex chars")
    return sha8


def validate_viewport(viewport: str) -> str:
    if not VIEWPORT_RE.match(viewport):
        raise NamingError(
            f"invalid viewport {viewport!r}: expect like '412x916' or '412x916@2.6'"
        )
    return viewport


def build_sha8(full_sha: str) -> str:
    """从完整 git SHA 取 canonical 前 8 位（小写）。"""
    full = (full_sha or "").strip().lower()
    if not re.match(r"^[0-9a-f]{8,40}$", full):
        raise NamingError(f"invalid full git sha {full_sha!r}")
    return full[:8]


def screenshot_name(
    surface: str,
    state: str,
    persona: str,
    platform: str,
    viewport: str,
    sha8: str,
) -> str:
    """构造 canonical 截图文件名；任何段不合法即抛 :class:`NamingError`。"""
    validate_segment("surface", surface)
    if surface not in SURFACES:
        raise NamingError(f"unknown surface {surface!r}: not one of {sorted(SURFACES)}")
    validate_segment("state", state)
    if persona not in PERSONAS:
        raise NamingError(f"unknown persona {persona!r}: not one of {sorted(PERSONAS)}")
    if platform not in PLATFORMS:
        raise NamingError(f"unknown platform {platform!r}: not one of {sorted(PLATFORMS)}")
    validate_viewport(viewport)
    validate_sha8(sha8)
    return (
        f"{surface}__{state}__{persona}__{platform}__{viewport}__{sha8}"
        f"{SCREENSHOT_SUFFIX}"
    )


def parse_filename(filename: str) -> dict[str, str]:
    """解析 canonical 截图文件名为字段 dict；不合法抛 :class:`NamingError`。"""
    if not filename.endswith(SCREENSHOT_SUFFIX):
        raise NamingError(f"not a canonical screenshot name: {filename!r}")
    stem = filename[: -len(SCREENSHOT_SUFFIX)]
    parts = stem.split("__")
    if len(parts) != len(NAMED_PARTS):
        raise NamingError(
            f"expect 6 '__'-separated parts, got {len(parts)} in {filename!r}"
        )
    fields = dict(zip(NAMED_PARTS, parts))
    # 复用 screenshot_name 的校验逻辑（构造一次即完成全字段验证）。
    screenshot_name(
        fields["surface"],
        fields["state"],
        fields["persona"],
        fields["platform"],
        fields["viewport"],
        fields["sha8"],
    )
    return fields
