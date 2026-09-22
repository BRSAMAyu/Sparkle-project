"""B1-B / S2 例1：达标线拼接禁机话直出（AUDIT S2 / SPEC DL §6.4）。

`experience_readouts._criterion_label` 曾把结构化达标线拼成
「图论概念梳理完成 >= 1boolean」直出给用户。修复后：
- unit=boolean 走整句人话模板「完成「{title}」即达标」；
- 已知数值 unit 映射为中文单位词（percent/count/days/time）；
- 未知 unit 不再拼接英文枚举后缀（结构化值经 payload 透传，端侧词典兜底）；
- payload 同步下传 threshold/unit 等结构化字段（呈现层可二次人话化）。
"""

from app.api.v1.experience_readouts import _criteria_payload, _criterion_label


class TestCriterionLabelHumanized:
    def test_boolean_unit_uses_whole_sentence_template(self):
        """『>= 1boolean』机话必须消失（AUDIT S2 原始反例）。"""
        label = _criterion_label(
            {"title": "图论概念梳理完成", "threshold": "1", "unit": "boolean"}
        )
        assert label == "完成「图论概念梳理完成」即达标"
        assert ">=" not in label
        assert "boolean" not in label

    def test_count_unit_maps_to_ci(self):
        label = _criterion_label(
            {"title": "错题重做", "threshold": "3", "unit": "count"}
        )
        assert label == "错题重做 ≥ 3 次"
        assert "count" not in label

    def test_days_unit_maps_to_tian(self):
        label = _criterion_label(
            {"title": "连续打卡", "threshold": 30, "unit": "days"}
        )
        assert label == "连续打卡 ≥ 30 天"

    def test_percent_unit_maps_to_percent_sign(self):
        label = _criterion_label(
            {"metric": "exam_score", "threshold": 90, "unit": "percent"}
        )
        assert label == "exam_score ≥ 90%"

    def test_time_unit_renders_threshold_without_unit_suffix(self):
        label = _criterion_label(
            {"title": "早起", "threshold": "07:00", "unit": "time"}
        )
        assert "07:00" in label
        assert "time" not in label.replace("07:00", "")

    def test_unknown_unit_does_not_concatenate_enum(self):
        """未知 unit 禁止「>= 1weird」式拼接；枚举原值走结构化透传。"""
        label = _criterion_label(
            {"title": "练习", "threshold": "1", "unit": "weird"}
        )
        assert label == "练习 ≥ 1"
        assert "weird" not in label

    def test_missing_threshold_returns_title_only(self):
        assert _criterion_label({"title": "只有标题"}) == "只有标题"

    def test_plain_string_passthrough(self):
        assert _criterion_label("核心科目达到目标分数线") == "核心科目达到目标分数线"


class TestCriteriaPayloadStructured:
    def test_payload_keeps_label_and_passes_structured_fields(self):
        payload = _criteria_payload(
            [{"title": "图论概念梳理完成", "threshold": "1", "unit": "boolean"}]
        )
        assert len(payload) == 1
        item = payload[0]
        assert item["label"] == "完成「图论概念梳理完成」即达标"
        assert item["threshold"] == "1"
        assert item["unit"] == "boolean"

    def test_payload_defaults_status_and_source(self):
        payload = _criteria_payload([{"title": "X", "threshold": 1, "unit": "count"}])
        assert payload[0]["status"] == "pending"
        assert payload[0]["source"] == "goal"

    def test_payload_skips_empty_labels(self):
        assert _criteria_payload([{"threshold": 1, "unit": "count"}, "  "]) == []

    def test_mobile_readable_line_never_sees_machine_suffix(self):
        """渲染契约：任何产出的 label 都不得含「>=」机话模式。"""
        raw = [
            {"title": "A", "threshold": "1", "unit": "boolean"},
            {"title": "B", "threshold": "2", "unit": "count"},
            {"title": "C", "threshold": 90, "unit": "percent"},
            {"title": "D", "threshold": 1, "unit": "hyperreal"},
        ]
        for item in _criteria_payload(raw):
            assert ">=" not in item["label"], item["label"]
