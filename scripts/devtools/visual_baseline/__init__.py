"""visual_baseline: V3 视觉基线 harness（B-04）。

职责（见 v3-output/B-04/REPORT.md 与 HARNESS 章节）：
- canonical 截图命名规范（surface/state/persona/platform/viewport/build SHA）；
- manifest 生成与校验（相对路径 + sha256，截图 PNG 本身不入 git）；
- 轻量 diff 辅助（纯 stdlib PNG 指纹，不要求像素一致）；
- 9 surfaces canonical states 注册表（后续 UI 卡按表复现）。
"""

from .naming import (
    PLATFORMS,
    SCREENSHOT_SUFFIX,
    SEGMENT_RE,
    parse_filename,
    screenshot_name,
    validate_segment,
)
from .states import CANONICAL_STATES, SURFACES, canonical_state_for, iter_state_rows

__all__ = [
    "PLATFORMS",
    "SCREENSHOT_SUFFIX",
    "SEGMENT_RE",
    "parse_filename",
    "screenshot_name",
    "validate_segment",
    "CANONICAL_STATES",
    "SURFACES",
    "canonical_state_for",
    "iter_state_rows",
]
