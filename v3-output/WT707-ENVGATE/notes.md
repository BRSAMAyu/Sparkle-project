# WT707-ENVGATE — V3-FIX-189 conversational_extractor 收进 stage19 三态门（闭账实录）

- 卡：V3-FIX-189（P3，wt695 日终盘点 A1 队列项；wt486 同族扫描判可机械修，同 186 先例）
- 分支：`agent/node-b/wt707/envgate`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt707-envgate`）
- 修复 commit：`197e9876`（fix commit）；台账/产出 commit 见分支尾
- 基点：main `79a0b53a`

## 1. 问题定位（先 find 后动手）

- 直读点：`backend/app/services/evidence/conversational_extractor.py:45-49`——
  `llm_enabled` 判据 `bool(settings.SPARKLE_LLM_EXTRACTOR_ENABLED) and not bool(SPARKLE_LLM_EXTRACTOR_DRY_RUN_ENABLED)`，
  只读 legacy bool，不读 `AURORA_STAGE19_LLM_EXTRACTOR_MODE`（settings.py:340，默认 `live`）。
- 统一入口：`backend/app/core/kill_switch.py` `resolve_settings_mode`（V3-FIX-21 判据唯一化）——
  tri-state 设置在场即唯一判据，legacy bool 仅属性缺席时兜底；binding 权威
  `AuroraStage19KillSwitchService.BINDINGS["llm_extractor_enabled"]`（legacy_bool_attr 即本 legacy bool）。
- 消费面盘点（grep 全仓）：
  - 唯一不传参消费点 `backend/app/services/chat_signal_collector.py:221`
    `ConversationalEvidenceExtractor()`——即本车道的行为面入口（`_persist_conversational_evidence`），
    该链路无 fetch 级二道闸 → `__init__` 的 settings 层判据就是实际权威；
  - `signal_inventory.py:46` 及全部测试传显式 `llm_enabled=False/True`，不受本修影响；
  - 同族 stage19 消费 `llm_extractor_service.py:50` / `working_memory_pipeline_service.py:39`
    走 async `get_feature_mode`（含 Redis 覆盖），另一车道，不在本卡且不受影响。
- 先例复刻：`b65dffee`（V3-FIX-186）同构修法——直读点改
  `resolve_settings_mode(<StageKillSwitchService>.BINDINGS[...])` + `is_enabled_mode`。

## 2. 修法（读法统一，DRY_RUN 合取语义保留）

- 判据改为：
  `is_enabled_mode(resolve_settings_mode(BINDINGS["llm_extractor_enabled"])) and not DRY_RUN`。
- 三态语义与 stage19 对齐：`off`/`shadow`/`live` 均为权威判据；`is_enabled_mode`
  对 `shadow`/`live` 放行（`off` 断车道）；legacy bool 只在 tri-state 属性缺席时兜底。
- DRY_RUN 位置不动：合取末位压倒任何 mode（true → 规则车道），与修前 legacy bool 位次等价。

## 3. wt486 OPEN 注记三项裁决（随修落地，已写台账闭账注记）

1. **legacy-false-only 翻转面（真钱车道）**：mode 默认 live，仅设
   `SPARKLE_LLM_EXTRACTOR_ENABLED=false` 未设三态的仓外存量部署会从「extractor 关」
   翻回「开」。迁移盘查复核：全仓 grep 无 `.env` 实例入库；`.env.example`/
   `.env.production.example`/`backend/.env.example` 三处默认 `true` 与 mode 默认
   `live` 同向 → 默认部署行为口径零变化；翻转面仅限仓外显式 legacy-only=false
   部署，**上线前须盘查生产 env**（如实登记，不掩盖、不擅改默认）。
2. **取时语义**：同步 `__init__` 构造期冻结 settings 层三态（186 同口径）；
   Redis 运行期覆盖由治理面 `read_mode` 承接；本车道消费链无二道闸，
   settings 层 off 即实际断车道——此为 186 先例已接受的同步面口径，如实留记。
3. **DRY_RUN 合取次序**：DRY_RUN 压倒 mode（不恢复 LLM 车道），与修前语义等价；
   测试 `test_conversational_extractor_dry_run_overrides_mode` 钉死。

## 4. 红→绿实录（真实运行）

环境：隔离 worktree 无 `.env`（DBGUARD 守卫口径，测试落 sqlite）；`SECRET_KEY` env 注入；
解释器 = 主仓 `backend/.venv`（worktree 不带 venv）。

红（修前，`tests/unit/test_chat_signal_collector.py`）：

```
FAILED tests/unit/test_chat_signal_collector.py::test_conversational_extractor_stage19_off_cuts_llm_lane
FAILED tests/unit/test_chat_signal_collector.py::test_conversational_extractor_stage19_live_overrides_legacy_false
FAILED tests/unit/test_chat_signal_collector.py::test_conversational_extractor_shadow_mode_keeps_llm_lane
FAILED tests/unit/test_chat_signal_collector.py::test_conversational_extractor_stage19_off_returns_rule_fallback_without_llm_call
4 failed, 15 passed in 0.74s
```

关键红实录：`stage19 off + legacy True` → `assert extractor.llm_enabled is False` 得
`assert True is False`（off 被劫持）；行为面 `extract()` 在 off 下仍调
`safe_llm_json_call` → `AssertionError: stage19 off must not call the LLM lane`。
对偶红：`mode live/shadow + legacy False` → `False`（legacy 单权威劫持 tri-state）。
三态「未配置」态（delattr mode → legacy 兜底）双向断言修前修后均绿（语义本就一致）。

绿（修后同文件）：

```
19 passed in 0.66s
```

基线 13 + 新增 6：off 断车道、live 不被 legacy 劫持、shadow 放行、
tri-state 缺席 legacy 兜底（false→关/true→开）、DRY_RUN 压倒 mode、
off 行为面零 LLM 调用。

## 5. 既有测试面与门禁

- 邻域 92 passed（14.30s）：`test_chat_signal_collector` + `test_chat_signal_collector_profile_loop`
  + `test_stage19_kill_switch` + `test_kill_switch_core` + `test_nbp1_ws_turn_memory_capture`
  + `test_memory_inferred_write_lane` + `test_a04_joint_factor_projection`；
  另 working memory 同 binding 族 5 passed；`test_belief_shadow_real_redis` 1 skipped
  （隔离环境无真 Redis，守卫口径跳过，非本修引入）。
- mypy：`mypy app --ignore-missing-imports` → 修后 `159 errors in 129 files`，
  stash 对照修前同 `159`——**159=159 零漂移**（触达文件零 mypy 错误）。
  注：台账/任务引「当前合并态 158」为异环境（venv/mypy 版本）数字，本工作区
  实测基线即 159，按同环境前后对照口径零回涨。
- ruff + black：触达 2 文件（`conversational_extractor.py`、`test_chat_signal_collector.py`）
  全过、零重排。

## 6. 边界声明

- 不改认证/授权；不动 `gen/`（主仓拷贝不入库）；无新文档目录登记需求（本 notes 即产出）。
- 不 push；commit 全在 `agent/node-b/wt707/envgate`。
- 无新发现需登记（V3-FIX-405 未消耗）：`scripts/check_aurora_config_consistency.py:45`
  对本 legacy bool 的一致性守卫与本修无冲突（legacy bool 属性仍在 settings，仅判据旁路）。
