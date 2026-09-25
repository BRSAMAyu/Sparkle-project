"""matrix.py 单测（U-09）：三端截图矩阵可执行清单与 diff report 模板。

红测先行记录：本文件先于 matrix.py 实现与 naming.py 的 macos 平台段
落地——
- `macos` 平台段：实现前 screenshot_name(..., 'macos', ...) 抛
  NamingError（红）→ naming.py PLATFORMS 增补后通过（绿）；
- `import matrix`：实现前 ModuleNotFoundError（红）→ 落地后通过（绿）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from visual_baseline.matrix import (  # noqa: E402
    U09_PLATFORMS,
    U09_VIEWPORTS,
    diff_report_template,
    iter_matrix_rows,
    render_matrix_markdown,
)
from visual_baseline.naming import parse_filename, screenshot_name  # noqa: E402
from visual_baseline.states import CANONICAL_STATES  # noqa: E402


class TestMacosPlatformSegment:
    """U-09 三端之 macOS 必须是 canonical 命名合法平台段（原注册表缺）。"""

    def test_macos_screenshot_name_roundtrip(self):
        name = screenshot_name(
            "home", "main", "demo_data", "macos", "1280x800@2.0", "aced25a2"
        )
        assert parse_filename(name)["platform"] == "macos"

    def test_u09_platforms_subset_of_registry(self):
        assert set(U09_PLATFORMS) <= {"android", "web", "ios", "macos"}


class TestMatrixRows:
    def test_rows_cover_all_canonical_states_times_three_platforms(self):
        rows = list(iter_matrix_rows())
        covered = {(r.surface, r.state_id, r.platform) for r in rows}
        for cs in CANONICAL_STATES:
            for platform in U09_PLATFORMS:
                assert (cs.surface, cs.state_id, platform) in covered, (
                    f"{cs.surface}/{cs.state_id} 缺 {platform} 采集行"
                )

    def test_every_row_has_entry_and_assertions(self):
        for row in iter_matrix_rows():
            assert row.entry, "采集入口必须来自 canonical states 注册表"
            assert row.assertions, "断言点必须非空（哪些点必须一致）"

    def test_viewports_match_multiplatform_spec(self):
        assert U09_VIEWPORTS["android"] == ("1080x2400@3.0",)
        assert U09_VIEWPORTS["web"] == ("1280x720@1.0", "360x720@1.0")
        assert U09_VIEWPORTS["macos"] == ("800x600@2.0", "1280x800@2.0")

    def test_row_filename_matches_naming_grammar(self):
        for row in iter_matrix_rows():
            name = screenshot_name(
                row.surface,
                row.state_id,
                row.persona,
                row.platform,
                row.viewport,
                "01234567",
            )
            assert parse_filename(name)["state"] == row.state_id


class TestMarkdownOutputs:
    def test_matrix_markdown_is_executable_checklist(self):
        md = render_matrix_markdown(build_sha8="aced25a2")
        assert "- [ ]" in md, "必须是可勾选清单"
        for platform in U09_PLATFORMS:
            assert platform in md
        assert "aced25a2" in md

    def test_diff_report_template_has_placeholders(self):
        tpl = diff_report_template()
        for token in ("<BUILD_SHA>", "<PLATFORM>", "<SURFACE>", "<STATE>"):
            assert token in tpl, f"diff report 模板缺占位符 {token}"
        assert "允许差异" in tpl, "模板必须携带允许差异 reason 章节"

    def test_markdown_counts_match_rows(self, tmp_path=None):
        rows = list(iter_matrix_rows())
        md = render_matrix_markdown()
        # 每行一个 checkbox（清单可数=矩阵可数，防生成器漏行）
        assert md.count("- [ ]") == len(rows)


@pytest.mark.parametrize("platform", ["android", "web", "macos"])
def test_u09_platform_constants(platform):
    assert platform in U09_PLATFORMS
