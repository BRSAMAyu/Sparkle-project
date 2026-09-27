"""V3-FIX-340 处置守卫（wt646）：相似度任务退役 + 画像/缓存任务接线。

裁决=SPLIT：
- 退役（删除）：update_similarities.py 的 tasks.update_all_user_similarities 与
  tasks.update_item_similarities——UserSimilarity/ItemSimilarity 的读面
  （/recommendations/collaborative、/similar-users、/similar-items）已注册且
  网关有代理，但产品面（mobile）零消费者；前者 O(n²) 日算无兑付，后者实现
  本身不落库（原文件 :367-369 自注"省略实际保存代码"）。读面 API 本身不在
  本卡处置范围（V3-FIX-07 R6 留观继续）。
- 接线：tasks.update_user_learning_profiles（UserLearningProfile 唯一写入方，
  活消费链=SeedExtractor._onboarding_seeds）与 tasks.expire_old_recommendation_cache
  （RecommendationCache 活写入方=community 好友/群组推荐缓存）拆分为独立模块
  并接入 include/beat/路由。

本守卫断言退役不可达面清零、接线任务真注册、beat 恰一条：
  - 复活退役任务（或重建同名模块而不接线）→ 红；
  - 拆掉接线模块的 include/beat → 红。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.celery_app import celery_app  # noqa: E402

RETIRED_TASK_NAMES = (
    "tasks.update_all_user_similarities",
    "tasks.update_item_similarities",
)
WIRED_TASK_NAMES = (
    "tasks.update_user_learning_profiles",
    "tasks.expire_old_recommendation_cache",
)
RETIRED_MODULE = "app.tasks.update_similarities"


def test_retired_similarity_module_is_gone() -> None:
    """update_similarities 模块已删除，不可再被 import 复活为隐死代码。"""
    assert importlib.util.find_spec(RETIRED_MODULE) is None, (
        f"{RETIRED_MODULE} 已随 V3-FIX-340 退役删除；如需恢复相似度写入方，"
        "须先落地推荐位消费面并配套测试，不要原样复活死任务"
    )


def test_retired_task_names_absent_from_registry_and_beat() -> None:
    """退役任务名不在 worker 注册表，也不得出现在任何 beat 条目。"""
    for name in RETIRED_TASK_NAMES:
        assert name not in celery_app.tasks, f"退役任务 {name} 重新出现在注册表"
    beat_tasks = {str(entry["task"]) for entry in celery_app.conf.beat_schedule.values()}
    for name in RETIRED_TASK_NAMES:
        assert name not in beat_tasks, f"退役任务 {name} 出现在 beat 计划"


def test_wired_modules_are_in_worker_include() -> None:
    """接线模块已列入 worker include（缺 include=beat 发了也没 worker 能注册执行）。"""
    for module in (
        "app.tasks.learning_profile_refresh",
        "app.tasks.recommendation_cache_cleanup",
    ):
        assert module in celery_app.conf.include, (
            f"V3-FIX-340 接线模块 {module} 不在 celery include：任务将 unregistered"
        )


def test_wired_tasks_are_registered_and_scheduled() -> None:
    """接线任务 import 后真注册（worker 冷启动语义）且 beat 各恰一条。"""
    import importlib

    for module in (
        "app.tasks.learning_profile_refresh",
        "app.tasks.recommendation_cache_cleanup",
    ):
        importlib.import_module(module)
    for name in WIRED_TASK_NAMES:
        assert name in celery_app.tasks, f"V3-FIX-340 接线任务 {name} 未注册"
    for name in WIRED_TASK_NAMES:
        entries = [
            key
            for key, entry in celery_app.conf.beat_schedule.items()
            if str(entry["task"]) == name
        ]
        assert entries, f"接线任务 {name} 无 beat 条目（任务注册但永不调度）"
        assert len(entries) == 1, f"接线任务 {name} 出现多条 beat 条目：{entries}"
