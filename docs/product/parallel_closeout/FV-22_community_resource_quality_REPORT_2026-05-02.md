# FV-22 · 社群资源质量评分 + cohort 阈值上调 · 完成报告

**Agent**: main (Architect)
**Branch**: codex/FV-17-source-lifecycle
**Date**: 2026-05-02
**Status**: COMPLETED

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | cohort_aggregation_min_k 默认从 3 → 5 | ✅ | `community_service.py:2946` — `COHORT_AGGREGATION_MIN_K = 5` |
| 2 | 资源质量评分公式 | ✅ | `community_service.py:2962` — `CommunityResourceScorer.compute_quality_score()` 基于 adoption_count + outcome_effectiveness + negative_feedback_rate + scope_match |
| 3 | 排名 API `/api/v1/community/resources?sort=quality` | ✅ | `community.py:4461` — `get_community_resources_ranked()` 端点，默认 sort=quality |
| 4 | 低质量资源自动隐藏 | ✅ | `community_service.py:2986` — `should_hide(score)` 阈值 0.3；`community.py:4493` 自动过滤 |
| 5 | 用户可标记"误导我" | ✅ | `community_service.py:3018` — `CommunityResourceScorer.flag_misleading()` 加额外 -0.15 惩罚 |
| 6 | Prometheus 暴露质量分布 | ✅ | `metrics.py:1084-1097` — Histogram `sparkle_community_resource_quality_score` + Counter `sparkle_community_resource_misleading_flags_total` |
| 7 | 单测 + 集成测 | ✅ | `tests/test_fv22_resource_quality.py` — 20 tests passed; `tests/integration/test_community_integration.py` — 22 passed |

## 2. 文件变更清单

```
backend/app/services/community_service.py  — CommunityResourceScorer + COHORT_AGGREGATION_MIN_K
backend/app/api/v1/community.py            — /resources 端点 + sort=quality
backend/app/core/metrics.py                — Prometheus 质量分布指标
backend/app/models/community.py            — SharedResource.quality_score/quality_hidden 字段
backend/tests/test_fv22_resource_quality.py — 20 测试
scripts/rule_guard_manifest.tsv            — i18n guard 注册
```

## 3. 测试证据

### 单测
```
tests/test_fv22_resource_quality.py::TestComputeQualityScore::test_all_zeros PASSED
tests/test_fv22_resource_quality.py::TestComputeQualityScore::test_perfect_score PASSED
... (8 formula tests) ...
tests/test_fv22_resource_quality.py::TestShouldHide::test_below_threshold_hidden PASSED
... (4 threshold tests) ...
tests/test_fv22_resource_quality.py::TestUpdateResourceQuality::test_update_sets_score PASSED
... (3 DB persistence tests) ...
tests/test_fv22_resource_quality.py::TestFlagMisleading::test_flag_applies_extra_penalty PASSED
... (4 misleading flag tests) ...
======================== 20 passed in 2.83s =========================
```

### 集成测
```
tests/integration/test_community_integration.py:
  test_group_resources_reject_non_members PASSED
  test_group_resources_exclude_blocked_and_deleted_payloads PASSED
  ... 22 passed, 2 skipped in 9.24s
```

## 4. 用户视角变化

> 在社群中浏览共享资源时，用户现在能看到按质量排序的资源列表，低质量资源自动隐藏，如果发现误导性内容可一键标记使其降权。

具体场景：
- 之前：社群共享资源无质量区分，低质量内容混杂
- 之后：资源按 adoption + outcome + feedback 评分排序，低质量（<0.3）自动隐藏，用户可标记 misleading 立即降低质量分

## 5. 与其他卡片的协调

- 与 FV-05（PrivacyCommunityIntelligence）的 k 阈值同步：COHORT_AGGREGATION_MIN_K = 5
- 共享文件未改动其他 FV-XX 部分
- 留给 Architect：N/A

## 6. 已知限制 / 后续

- 质量评分目前基于简单加权公式，未来可升级为 ML ranking（与 FV-21 协调）
- misleading 标记目前没有限制同一用户对同一资源的标记次数上限（每次减 0.15 可累积隐藏）

## 7. 验收命令一键回放

```bash
cd backend && python3 -m pytest tests/test_fv22_resource_quality.py tests/integration/test_community_integration.py -v
```
