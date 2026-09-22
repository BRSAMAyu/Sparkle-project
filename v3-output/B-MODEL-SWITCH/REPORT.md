# B-MODEL-SWITCH 收工报告 — BATCH_LLM_PROVIDER 开关（glm_batch 车道可切换 provider）

- Worker：B 纵队（模型切换线）｜worktree：`wt172`｜基线：`5b912dcf`
- 日期：2026-09-22（运行跨夜至 09-23 凌晨）
- 交付物：本报告 + `changes.patch`（11 个 diff 体：10 个修改文件 + 1 个新增测试文件）
- 纪律：零 commit / 零 push；零凭据（.env 未读值未复制；测试全假 key）；未动主仓

---

## ① 路由双处审计结论

**「显式 `queue=` 覆盖 celery 路由表」两处定义 = `backend/app/core/celery_app.py` 的 `task_routes` 表（glm_batch 条目 5 个任务）+ 调用面显式 `queue="glm_batch"` 覆盖（4 个调用位）。审计结论：两处均不改。**

理由：本卡改动在 LLMRouter provider 选择层（队列执行者换了引擎，不换车道），`glm_batch` 队列身份与投递语义零变化。逐位盘点：

| 显式覆盖位 | 任务名 | 与表的关系 |
|---|---|---|
| `app/core/celery_app.py:931`（generate_daily_capsules_for_all 内） | generate_capsules_batch | 表内有同队列条目，冗余且一致 |
| `app/api/v1/capsules.py:431` | generate_capsules_batch | 同上（注释已自述一致性） |
| `app/services/push_strategies/empty_capsule.py:94` | generate_capsules_batch | 同上 |
| `app/services/predictive_service.py:1961` | generate_long_horizon_prediction | **不在表内**，显式覆盖是其唯一路由（表外互补，非分叉） |

锁定措施：新增 `TestBatchQueueRoutingConsistency`（`tests/core/test_batch_llm_provider_switch.py`）——(a) 断言 task_routes 表 5 个 batch 任务 → `settings.GLM_BATCH_QUEUE`；(b) 四个显式位存在且任务名登记在案；(c) 全仓扫描 `queue="glm_batch"` 字面量只出现在四个已审计文件（新位必须登记测试才能合入）；(d) 变量覆盖位（glm_batch_service 统一投递面 `queue=self.queue_name`）源自 `settings.GLM_BATCH_QUEUE`。

## ② 开关与 provider 解析实现

**新 settings**（`app/config/settings.py`，紧邻 MINIMAX 四配置）：

```python
BATCH_LLM_PROVIDER: str = "glm"   # "glm"（默认回滚位）| "minimax"
```

**唯一读取口**（`app/core/llm_router.py` 新增模块函数 `batch_llm_provider()`）：strip/lower 归一，非法/空值安全回退 `"glm"`，绝不抛错。router 与直连车道共用这一个定义。

**裁决点 = GLM_BATCH 池条目注册**（`LLMRouter._load_model_configs`）：
- `minimax_m3_batch`：`BATCH_LLM_PROVIDER=minimax` 且 `MINIMAX_API_KEY` 非空才注册；开关=glm 时 key 即便配置也不注册（info 日志「保留配置不启用」）。
- `qwen3_7_flash_batch`：同一开关裁决 + `DASHSCOPE_API_KEY` key-gate（minimax 档下维持已验证的 M3 置首、Qwen 次位次序）。
- `_tier_mapping[GLM_BATCH]` 的 `or GLM 原链` 兜底逻辑零改动——注册门控自然传导：开关=glm → GLM 原链（与 MM-M3 决策合入前逐位一致）；=minimax 无任何 key → warning + GLM 原链兜底（车道不空转）。
- `LLM_TIER_GLM_BATCH` env 覆盖仍在映射之后生效（运维逃生通道不变）。

**执行面一致性（注册为唯一真源，下游自动跟随，零逻辑改动）**：
- `glm_batch_service._minimax_lane_registered/_active_concurrency_pool/_select_batch_model_key`（注册判定式）→ glm 档自动落 GLM 原链 + zhipu_coding 并发池；
- `capsule_generation_service.ModelSelectionStrategy._minimax_lane_registered` 与执行计划（minimax 档唯一候选、失败不静默偷切 GLM 的既定语义）自动跟随；
- `predictive_service._batch_model_chain`（读 `resolve_candidate_models`）自动跟随；
- `batch_worklane.resolve_selection`（router 真源 `force_tier=GLM_BATCH`）自动跟随。

**一处真实逻辑改动（范围外消费者收编）**：`error_book_service._run_llm_analysis` 的直连 `minimax_provider.analyze` 车道（原key-存在即尝试、绕过 router）加开关门——`batch_llm_provider()=="minimax"` 才尝试，否则直走主 LLM 通道；车道异常降级主通道的既有语义保持。理由：`analyze_error_batch`（glm_batch 队列任务）经 `analyze_and_link` 走这条直连车道；不开门则开关回滚后 error 域残留 MiniMax 调用，违反「开关可回滚」的全链语义。MiniMax OpenAI 兼容通道按卡面指示**复用既有实现**（`minimax_provider` 单例，`{MINIMAX_BASE_URL}` OpenAI 兼容端点），零新增 adapter。

**默认值**：`"glm"`（本卡不切）。主会话冒烟后切 minimax（见 ④）。

## ③ 冲突面声明（对 wt170 / wt171 逐文件）

| 本卡改动文件 | vs wt170（achievement_engine + Alembic + photon 写侧） | vs wt171（两个 event consumer） |
|---|---|---|
| `backend/app/config/settings.py` | 零重叠（仅 BATCH_LLM_PROVIDER 一行块；Alembic 迁移不碰 settings） | 零重叠 |
| `backend/app/core/llm_router.py` | 零重叠（achievement_engine 不 import 路由注册面；无 photon 路径） | 零重叠（event consumer 不消费 LLMRouter 注册） |
| `backend/app/services/error_book_service.py` | 零重叠（仅 `_run_llm_analysis` 门控 + import 行；不碰 achievement/Alembic/photon 写侧） | 零重叠（error_book 非 event consumer 文件） |
| `backend/app/services/glm_batch_service.py` | 零重叠（纯注释同步） | 零重叠 |
| `backend/app/services/predictive_service.py` | 零重叠（纯注释同步） | 零重叠 |
| `backend/app/services/capsule_generation_service.py` | 零重叠（纯注释同步） | 零重叠 |
| `backend/tests/…`（4 个既有测试 helper 钉位 + 1 个新增测试文件） | 零重叠 | 零重叠 |

未触碰：celery 队列/路由表、proto、Alembic、网关、mobile。动到的唯一行为面 = batch 车道 provider 选择 + error 直连车道门控。

## ④ 诚实申报

- **真实 key 冒烟不在本卡内**（按卡面留主会话）。步骤：① 活栈 `.env` 加 `MINIMAX_API_KEY=<真key>` 并设 `BATCH_LLM_PROVIDER=minimax` → ② 重启引擎（LLMRouter 进程启动快照注册，改 settings 必须重启）→ ③ 手动触发一条 batch 任务（如 `POST /api/v1/capsules/generate` 或错题批量分析）→ ④ 验证 MiniMax 侧成功：`minimax_m3_batch` 路由日志 / minimax 并发池活动 / 任务结果落库 → ⑤ 通过后把代码默认（或部署 .env）切 `BATCH_LLM_PROVIDER=minimax` 固化。
- **语义变更申报（合入即生效）**：若活栈 `.env` 已配置 `MINIMAX_API_KEY`，合入本卡后 batch 车道会从「key 即启用 MiniMax」变为「默认 glm 原链」，直到主会话按上述步骤切开关——这是卡面指定的合入位（“默认值保持现状 glm……不在本卡内切”），非静默回归；无 key 环境（本 worktree/测试环境）零变化。
- **既有测试钉位申报**：4 个测试文件的 `_rebuild_router`/lane 用例改为钉 `BATCH_LLM_PROVIDER="minimax"`——它们验证的是 minimax 档契约（MM-M3 已验证语义），并非被本卡"修绿"：断言体零改动，仅快照补开关维度；glm 档契约由新增 `test_batch_llm_provider_switch.py` 独立覆盖。
- 本机 Xcode/cgo 环境问题不涉及（纯 Python 卡）；测试均 `SECRET_KEY=test DATABASE_URL=sqlite` 一次性进程。

## ⑤ 收工核查（回归对比法：基线克隆 vs 改后，同环境同命令）

基线 = `git clone wt172 /tmp/wt172-baseline`（只含 HEAD 5b912dcf，天然基线，未 stash 未 reset）：

| 定向域 | 基线 | 改后 | 新增失败 |
|---|---|---|---|
| 批1：minimax_batch_routing / llm_router_qwen / llm_router_policy / glm_thinking / agent_profiles_catalog / batch_worklane / glm_batch_adaptive | 98 passed | **122 passed**（含新增 24 用例） | 0 |
| 批2：credential_routing / health_tracking / free_tier / deep_analysis_tier / tier_fallback_order / same_tier_fallback / ttft_cfg | 56p/10f | 56p/10f（失败 ID 逐一相同） | 0 |
| 批3：dual_core_router_kill_switch / e07_adaptive / e07_hysteresis / explicit_temperature / o04_entitlement / minimax_provider | 64p/4f | 64p/4f（同上） | 0 |
| 批4：celery_route_beat_hygiene / dispatch_async / beat_guard / error_book_service / subject_normalization / user_service | 51p/5f | 51p/5f（同上） | 0 |

- 批2/3/4 的 19 个失败为**基线既有**（本 worktree 环境无生成代码/无 .env 所致），改后逐一相同，零新增。
- 收集错误（`app.gen` 缺失）：test_capability_lane / error_link_mastery_e2e / error_book_mastery_sync——基线与改后一致的环境性收集错误，非本卡回归；error 直连门控已由新增 `TestErrorBookDirectLaneGating` 单测覆盖（glm 档跳过 / minimax 档调用 / 失败降级三态）。
- 新增测试 24/24 绿（glm 默认零变化×8、minimax 档×6、执行面一致性×3、直连车道门控×3、双处路由一致性×4——执行面覆盖 glm_batch_service / capsule 策略 / batch_worklane 三类消费者随开关切换断言）。

## 收工清理

- [x] `/tmp/wt172-baseline` 克隆与 /tmp 失败清单已删
- [x] 无模拟器/浏览器/常驻进程；无构建产物入树
- [x] worktree 内仅余：6 个 app 修改 + 5 个测试文件 + `v3-output/B-MODEL-SWITCH/`（本报告 + changes.patch）

## 后继（非本卡）

1. 主会话真 key 冒烟 → 切默认（见 ④）。
2. 观察期后若固化 minimax 档，可考虑把 `LLM_PROVIDER` 注释中 batch 语义与 `BATCH_LLM_PROVIDER` 关系补进部署文档。
