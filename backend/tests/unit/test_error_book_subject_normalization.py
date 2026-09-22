"""
Unit: 科目归一化与 BP-6 校验放宽。

BP-6（LOOP1）：错题本科目枚举无大学科目——「离散数学」曾直接 400 /
INVALID_ARGUMENT，agent 工具链把未知科目吞成 math 兜底（LOOP2 证据 C5b）。
本套钉住：枚举扩展 + normalize_subject 归一化面 + 三个调用面的放宽语义。
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from app.schemas.error_book import (
    SUBJECT_TO_SPRINT_PACK,
    ErrorRecordCreate,
    SubjectEnum,
    normalize_subject,
)


class TestSubjectEnumExpansion:
    def test_university_subjects_present(self):
        """任务点名的大学科目必须入枚举（值为稳定 API 契约）。"""
        assert SubjectEnum.DISCRETE_MATH == "discrete_math"
        assert SubjectEnum.LINEAR_ALGEBRA == "linear_algebra"
        assert SubjectEnum.PROBABILITY_STATISTICS == "probability_statistics"
        assert SubjectEnum.DATA_STRUCTURES == "data_structures"
        assert SubjectEnum.ALGORITHMS == "algorithms"
        assert SubjectEnum.COMPUTER_NETWORKS == "computer_networks"
        assert SubjectEnum.OPERATING_SYSTEMS == "operating_systems"
        assert SubjectEnum.CALCULUS == "calculus"
        assert SubjectEnum.DATABASE_SYSTEMS == "database_systems"

    def test_legacy_members_unchanged(self):
        """既有 K12 成员零变化（CRUD/API 零破坏的契约面）。"""
        legacy = {
            "math",
            "physics",
            "chemistry",
            "biology",
            "english",
            "chinese",
            "history",
            "geography",
            "politics",
            "computer",
            "other",
        }
        values = {member.value for member in SubjectEnum}
        assert legacy <= values, f"既有科目缺失: {legacy - values}"
        assert len(values) == len(legacy) + 9

    def test_subject_to_sprint_pack_alignment(self):
        """枚举 → sprint pack 映射与 loader 的 pack key 对齐（归位词典的桥）。"""
        assert SUBJECT_TO_SPRINT_PACK[SubjectEnum.DISCRETE_MATH] == "discrete_mathematics"
        assert SUBJECT_TO_SPRINT_PACK[SubjectEnum.DATA_STRUCTURES] == "data_structures_algorithms"
        assert SUBJECT_TO_SPRINT_PACK[SubjectEnum.COMPUTER_NETWORKS] == "computer_networks"
        assert SUBJECT_TO_SPRINT_PACK[SubjectEnum.OPERATING_SYSTEMS] == "operating_systems"
        assert SUBJECT_TO_SPRINT_PACK[SubjectEnum.LINEAR_ALGEBRA] == "mathematics"
        assert SubjectEnum.ENGLISH not in SUBJECT_TO_SPRINT_PACK


class TestNormalizeSubject:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("离散数学", SubjectEnum.DISCRETE_MATH),
            ("离散", SubjectEnum.DISCRETE_MATH),
            ("Discrete Mathematics", SubjectEnum.DISCRETE_MATH),
            ("discrete-mathematics", SubjectEnum.DISCRETE_MATH),
            ("线代", SubjectEnum.LINEAR_ALGEBRA),
            ("线性代数", SubjectEnum.LINEAR_ALGEBRA),
            ("概率论", SubjectEnum.PROBABILITY_STATISTICS),
            ("概率论与数理统计", SubjectEnum.PROBABILITY_STATISTICS),
            ("高等数学", SubjectEnum.CALCULUS),
            ("高数", SubjectEnum.CALCULUS),
            ("数据结构与算法", SubjectEnum.DATA_STRUCTURES),
            ("计算机网络", SubjectEnum.COMPUTER_NETWORKS),
            ("计网", SubjectEnum.COMPUTER_NETWORKS),
            ("操作系统原理", SubjectEnum.OPERATING_SYSTEMS),
            ("数据库原理", SubjectEnum.DATABASE_SYSTEMS),
            ("math", SubjectEnum.MATH),
            ("MATH", SubjectEnum.MATH),
            ("数学", SubjectEnum.MATH),
            ("computer", SubjectEnum.COMPUTER),
            ("other", SubjectEnum.OTHER),
        ],
    )
    def test_known_aliases(self, raw, expected):
        assert normalize_subject(raw) is expected

    @pytest.mark.parametrize("raw", ["量子物理", "unknown_sub", "", "   ", None])
    def test_unknown_returns_none(self, raw):
        """未识别 → None（不猜；调用方决定兜底语义）。"""
        assert normalize_subject(raw) is None


class TestRelaxedConsumers:
    def test_create_schema_accepts_university_subject(self):
        """ErrorRecordCreate 直接接受新枚举值（BP-6 的 400 场景关闭）。"""
        payload = ErrorRecordCreate(
            question_text="欧拉回路判定",
            subject=SubjectEnum("discrete_math"),
            chapter="欧拉图与哈密顿图",
        )
        assert payload.subject == SubjectEnum.DISCRETE_MATH

    def test_safe_subject_prefers_normalization(self):
        """agent 工具链：中文科目经归一化面，不再误吞成 math/other。"""
        from app.tools.error_tools import _safe_subject

        assert _safe_subject("离散数学") is SubjectEnum.DISCRETE_MATH
        assert _safe_subject("线代") is SubjectEnum.LINEAR_ALGEBRA
        assert _safe_subject("discrete_math") is SubjectEnum.DISCRETE_MATH
        # 真正未识别 → OTHER（诚实的兜底桶，非 math）
        assert _safe_subject("量子物理") is SubjectEnum.OTHER
        # 空值维持既有防御分支语义（调用方已挡空，历史行为不变）
        assert _safe_subject(None) is SubjectEnum.MATH
        assert _safe_subject("") is SubjectEnum.MATH

    def test_grpc_create_conversion_is_relaxed(self):
        """gRPC 创建面的转换语义：未知科目落 OTHER 而非抛 INVALID_ARGUMENT。"""
        # 服务内实现为 normalize_subject(raw) or SubjectEnum.OTHER
        raw_unknown = "量子物理"
        converted = normalize_subject(raw_unknown) or SubjectEnum.OTHER
        assert converted is SubjectEnum.OTHER
        raw_dm = "离散数学"
        converted_dm = normalize_subject(raw_dm) or SubjectEnum.OTHER
        assert converted_dm is SubjectEnum.DISCRETE_MATH
