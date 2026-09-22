"""B1-B / S2 例5：默认模板名禁英文直出（AUDIT S2 / V16「14-Day Exam Prep」）。

场景包 name/description 与 exam sprint 保底包名是**内置默认模板**（会直接成为
用户可见的计划名/选择卡文案），不是 demo 数据——按 SPEC DL §6.2 X1/X7 在源头中文化。
"""

from app.scenario_packs.exam_prep_14d import load_exam_prep_14d_manifest


class TestScenarioPackNamesChinese:
    def test_exam_prep_pack_name_is_chinese(self):
        manifest = load_exam_prep_14d_manifest()
        assert manifest.name == "14 天考试冲刺"
        assert not any(
            ch.isascii() and ch.isalpha() for ch in manifest.name
        ), f"pack name 仍含英文字面量: {manifest.name}"

    def test_exam_prep_pack_description_is_chinese(self):
        manifest = load_exam_prep_14d_manifest()
        assert manifest.description
        assert not any(
            ch.isascii() and ch.isalpha() for ch in manifest.description
        ), f"pack description 仍含英文字面量: {manifest.description}"

    def test_pack_id_unchanged(self):
        """id 是机器标识，必须保持不变（词典化只动展示名）。"""
        manifest = load_exam_prep_14d_manifest()
        assert manifest.id == "exam_prep_14d@v1.0"
