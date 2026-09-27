# WT701 — CI 后端 shard 顺序污染第二轮根因（V3-FIX-393）

分支 `agent/node-b/wt701/shardleak`（base main@1d6c5ba5）。第九次尝试 36309295601 shard1+shard3 两红，
同指纹第八次已现；第一轮 4678ea41（conftest 补 `_available_models` 还原）不足。

## 0. 环境

- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt701-shardleak`，backend/.venv → 主仓 venv 符号链接，
  `backend/app/gen` 按先例 `cp -RL` 自主仓（不入库）。
- 两个口径：
  - **本地口径**：worktree 补拷主仓未入库 `backend/.env`（真实 LLM key，模型池 api_key 非空）。
  - **CI 口径**：移走 .env。CI（ci.yml）仅注入 `DATABASE_URL/REDIS_URL/TESTING/COVERAGE_FILE` 与
    `GITHUB_TOKEN`，**无任何 LLM key**——`llm_router` 池 api_key 全空。
- 分片清单：`scripts/ci/backend_tests_shards.txt`（1466 行；shard1 =88-544、shard3 =1005-1466），CI 以
  `backend_test_shards.py emit` 原序展开、单 pytest 进程 `pytest -v <files...>` 执行。
  目标位置：`test_capability_selection_policy.py` = shard1 :205（emit 序 :205）；`test_dashboard_service.py`
  = shard3 :99（emit 序 :99）。

## 1. shard1 根因：非「未还原的泄漏全局」，是被测断言的环境依赖

### 1.1 复现红（真实运行）

- 本地口径单文件（修前基线确认）：`pytest tests/unit/test_capability_selection_policy.py` → **8 passed**；
  双文件混跑 dashboard 在前 → capability 目标用例红（提示 dashboard 家族有可迁移态，后证与本卡 shard1 无关）。
- **CI 口径隔离（无 .env，未带任何前缀）**：目标用例单跑即红——
  `AssertionError: assert 'plus' == 'standard'`（`1 failed in 0.74s`）。
  机理：无 key → 池内模型按 V3-FIX-333 宣称态全 `not_configured`（`_BLOCKED_AVAILABILITY` 成员）→
  `_choose_model_in_tiers` 在 fast（被用例 block）/standard 两层均无 available 候选 → 落
  `_FALLBACK_TIER_ORDER` plus 层 `dashscope_chat` → `preferred_model_tier='plus'`。
- **CI 口径全前缀（修前，p204 + 目标）**：`4 failed, 1680 passed, 64 skipped, 6 errors`，目标在失败集
  （`backend/tests/unit/test_capability_selection_policy.py .....F..`）。其余 3F6E 为 postgres 依赖集成面
  （ltm_e2e/shop_acceptance/mimo_integration），本地环境既有，与本卡无关。
- 本地口径 p204（带 .env，含第九次已入库的 4678ea41 还原 fixture）：`6 failed, 1687 passed, 6 errors`，
  **目标文件 `........` 8/8 绿**——即「红前缀二分找污染者」在本地口径不可复现（污染者不存在），红线只在
  CI 口径成立。

### 1.2 定性

该用例的绿在 CI 从来不是「无泄漏」的绿：CI 恒无 key，纯池基线下断言恒假。历史绿依赖**前序测试把带 key 的
模型配置泄进进程级单例**的偶然掩盖；第八次清单重生成（e67f868a，剔 1 文件+纳入 30+ 新文件、LPT 重排）挪走/
错位了那个注入者，红即暴露；第九次 4678ea41 把「还原」做对后，注入通道被正确切断，用例回到环境依赖本色。
「残余泄漏全局」假设被证伪：`_available_models`/`_model_health` 已还原（4678ea41 在案），p204 本地口径绿、
CI 口径红与「还原是否补全」无关，与「池里有没有 key」完全相关。

### 1.3 修复（测试侧密封化，零产品码）

`test_selector_records_in_band_model_fallback_when_fast_model_is_blocked(monkeypatch)`：自备确定性 keyed 池
（blocked 清单 4 个 fast + standard 一档 `dashscope_standard_thinking`，`ModelTier`/`ModelProvider` 枚举构造
`ModelConfig`），`monkeypatch.setattr(llm_router, "_available_models", {...})`。对齐同族先例
`tests/services/test_capability_claims_realism.py:240-258`（同读 `_models()` 的注册表面）。用例断言零改动
（standard/in-band reason/full satisfaction 全保留），monkeypatch 用例后原位还原，conftest 还原 fixture
先建后拆不受扰（`test_capability_claims_realism` 同款共存先例）。

> 方法论坑实录（任务书预警命中）：池条目构造必须用枚举——`ModelProvider` 在 `app.core.llm_router` 而非
> `agent_profiles`（首版 import 错位即 ImportError）。

## 2. shard3 根因：`_spine_orchestrator` 进程级模块单例泄漏

### 2.1 泄漏全局

`app/signals/spine_orchestrator.py:5137` `_spine_orchestrator: SpineOrchestrator | None`；
`:5140 get_spine_orchestrator()` 首触构造永驻；`:5150 reset_spine_orchestrator()` **全库（app+tests）零调用**。
dashboard `_get_spine_status`（dashboard_service.py:393-415）函数内 import 工厂并构造；
`test_get_spine_status_returns_none_on_exception` 只 patch `SpineOrchestrator` **类**——单例已存在时工厂直返
既有实例、不再走被 patch 的构造 → `RuntimeError` 侧不触发 → `get_status_band_summary` 空态返缺省
→ `band_status='sensing'` 载荷（CI 指纹：期望 None 实得 sensing）。

### 2.2 二分路径（前缀文件数 K → dashboard 目标结果；均为单 pytest 进程、清单原序）

| K   | 结果 | 备注 |
|-----|------|------|
| 98  | 红   | 本地口径全前缀，CI 指纹复现（`.......F.`） |
| 49  | 绿   | |
| 74  | 红   | |
| 62  | 绿   | |
| 68  | 红   | |
| 65  | 绿   | |
| 67  | 红   | 最小红前缀 |
| 66  | 绿   | → 污染者 = 第 67 个文件 |

**污染者 = `backend/tests/integration/test_phase5_orchestrator_north_star_acceptance.py`**（shard3 :67）。
该文件自身零 spine 字面引用；它进程级安装 sys.modules stub（文件头自述「进程内不回收」）并驱动编排全流程，
经 `app/orchestration/session_state_mixin.py:690`（celery 任务面 `app/core/celery_tasks.py:2918` 等同族）首触
`get_spine_orchestrator(...)` 构造单例。**金丝雀实证**：p67 前缀 + 临时金丝雀用例（检查
`_spine_orchestrator`，用后即删未入库）→ `WT701_CANARY _spine_orchestrator = SpineOrchestrator`，单例跨文件
残留坐实；同 run 的 LATENCY 迹线可见 phase5 用例内 `spine_pipeline=2362ms`（首触现场）。

### 2.3 修复（conftest 快照还原，沿既有判例）

`backend/tests/conftest.py` 新增 autouse fixture `_restore_spine_orchestrator_singleton`：每用例前快照
`_spine_orchestrator`、用例后原位恢复（与 `_restore_llm_global_health_state` 同款；进程首触前恒 None →
还原即「未构造」态，工厂下次按需重建，消费面语义零改动）。

## 3. 修后验证（真实运行，全部贴自本次执行）

| # | 口径 | 命令形状 | 结果 |
|---|------|----------|------|
| V1 | CI（无 .env） | `pytest tests/unit/test_capability_selection_policy.py` | **8 passed** |
| V2 | CI | `pytest tests/services/test_dashboard_service.py` | **9 passed** |
| V3 | CI，shard3 红前缀 | p67 前缀 + dashboard 文件 | dashboard `.........` **9/9 绿**；总量 11F→10F（少的就是目标），余 10F+23E 与修前失败集逐一同名（postgres 依赖集成面，既有） |
| V4 | CI，shard1 红前缀 | p204 前缀 + capability 文件 | 目标文件 `........` **8/8 绿**；总量 4F→3F，余 3F6E 逐一同名既有 |
| V5 | 本地（.env），shard3 原复现口径 | p98 全前缀 + dashboard 文件 | dashboard `.........` **9/9 绿**（修前同口径红）；20F→19F 差即目标 |
| V6 | 本地 | 双文件单跑 | **17 passed** |
| V7 | 影响面 | 全部 spine 单例消费文件（nudge_channel_delivery/wt360/achievement_event_consumer/v343_l3_closure/spine pipeline/wt422/signal_spine） | **53+10+960 passed**，零破坏 |
| V8 | 门禁 | `bash scripts/ci/mypy_ratchet.sh` | `mypy errors: 159 / baseline: 380`，棘轮过（任务书口径 mypy 基线 159 一致） |
| V9 | 门禁 | `ruff check` 触达 2 文件 | 仅 `I001`（conftest import 块）——主仓同源既有（main 上同报），本卡零新增 |

## 4. 台账与产物

- `v3/06_agent_fleet/DYNAMIC_ISSUES.md` 追加 **V3-FIX-393**（7 列 8 裸管）；
  `python3 scripts/devtools/ledger_union_merge.py --verify` → `verify 通过：292 行 V3-FIX 行 … ID 无重号，
  状态枚举合法`。
- 改动面（`git status`）：`backend/tests/conftest.py`、
  `backend/tests/unit/test_capability_selection_policy.py`、本台账、本 notes。gen 与 .env 不入库。

## 5. 遗留与移交

- shard1 的「key 注入掩盖」通道本体（第八次前哪只测试注入、现落何片）未逐只考古——修复后目标用例不再依赖
  任何注入，考古无行为意义；若夜间全量漂移网（清单头「迹象 6」另卡）再报 shard1 同位红，按本 notes §1.2
  口径直接查环境密钥面。
- `reset_spine_orchestrator` 全库零调用本身无害（还原 fixture 承担隔离），未新增调用面。
