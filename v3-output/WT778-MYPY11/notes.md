# WT778 — mypy 棘轮烧减批十一实施记录（基线 76 → 61，净降 15，零新增）

- 分支 `agent/node-b/wt778/mypy11`（base **2113c04a** = 建 worktree 时 main tip；任务派发时引用的
  bb9c2d94 与 2f81182d 均为其祖先，其间仅 v3/.sparkle_v3_fleet_state.json 状态文件差），本文件随修复
  commit 同提交
- 纪律沿批八/九/十：真 bug 0 容忍（停手登记制）；cast 0；新增 ignore 0；bare-Any 注解 0；
  只做声明面注解 / 同名异型改名 / 安全收窄；判例沿用 wt768（mypy 1.20.2 注解赋值不收窄、
  有非 Optional 消费面一律改名、不可达分支守卫安全收窄）
- 避让在航卡：wt777（plan_review_service.py + leaderboard_service.py，后者经 worktree
  wt777-499probe `git status` 实录在改）零触碰；两文件在本批基线 76 条中本就无条目

## 1. 基线口径（冷缓存，MYPY_CACHE_DIR 独立）

```
cd backend && MYPY_CACHE_DIR=<独立目录> ./.venv/bin/python -m mypy app --ignore-missing-imports
```

- worktree 冷缓存 **76 errors in 67 files (checked 1387)**；main（同仓 checkout @bb9c2d94 时点）
  同法冷缓存 **76 errors in 67 files (checked 1387)**；去行号逐条 diff **空**
  （/tmp/mypy_wt778_main.txt vs /tmp/mypy_wt778_base.txt，DIFF-EMPTY 实录）
- 环境注记：worktree 无 .venv（gitignore），`backend/.venv` symlink → 主仓 venv；
  `sys.prefix` = homebrew python 3.11 与主仓一致，mypy 同 mypy 1.20.2 同 site-packages；
  `backend/app/gen` symlink → 主仓 gen（不入库，沿 wt767/wt768 先例）
- 修后冷缓存（独立第三 cache-dir /tmp/mypy_wt778_after_cache）**61 errors in 56 files**；
  与基线清单去行号 comm 核对：**移除 15 条、新增 0 条**

## 2. 选中 15 处 → 烧减 15（全部成立，无停手项）

| # | 文件:行（base） | 错误码 | 修法（分类） |
|---|---|---|---|
| 1 | core/intervention_lifecycle.py:321 | arg-type（int(int\|float\|None)） | 函数首加 `if hours is None: return DEFAULT`——原 int(None) 抛 TypeError 被 except 捕获后返 DEFAULT，显式提前逐值等价（安全收窄） |
| 2 | orchestration/executor.py:1687 | arg-type（sleep(float\|None)） | `if not should_retry:` → `if not should_retry or delay is None:`——retry_decision 契约「True 必伴非 None delay」（failure_semantics.py:363 docstring+实现两路 False 均 None），delay None 分支按契约不可达，守卫与 not should_retry 同走死信 break；附中文注释指明契约出处（安全收窄） |
| 3 | services/progress_narrative_service.py:1238 | arg-type（int(Any\|None)） | `_weekly_style_variant` 内提取 `raw_variant` + `if raw_variant is not None:` 包裹原 try/except——键缺失时原 int(None) TypeError 落 except → None，显式跳过后 latest_variant 同为 None（安全收窄） |
| 4 | services/aurora_control_surface_service.py:587 | arg-type（int(Any\|None)） | exam_countdown 面板 `days_left` 同构：显式 `days_left_int: int \| None = None` 初始化 + None 守卫包裹 try/except，None 路径落点逐值等价（安全收窄） |
| 5 | services/aurora_control_surface_service.py:753 | arg-type（append(Any\|None)→list[str]） | `facet_summary is not None` 守卫后再 append——summary 缺失时原 append(None) 必被 `_clean_evidence_chain` 的 `_strip`（`str(x or "")`，None→""→falsy 被滤）丢弃，显式不追加过滤结果逐值等价；非 None 值（含非 str truthy 值）原样透传 _strip 不变（安全收窄） |
| 6 | services/analytics/ope_gatekeeper.py:220 | arg-type（float(Any\|None)） | `_labeled_point` 内 `raw_total_reward` 提取 + None 守卫直接 `return None`——原 float(None) TypeError 落 except → None，逐值等价（安全收窄） |
| 7 | services/checkpoint_nudge_service.py:1211 | arg-type（int(Any\|None)） | `_normalize_checkpoints` 循环内 `if day is None: continue`——原 int(None) TypeError 落 except → continue，逐值等价（安全收窄） |
| 8 | tools/metadata.py:154 | arg-type（ToolEffect(Any\|None)） | `getattr(tool, "effect", None)` 缺省改 `""`——EnumType 按值查找对 None 与 "" 同样抛 ValueError（两者均非成员值），fail-closed 产 issue 的行为逐字节不变；attr 存在时缺省值不参与（声明面缺省改写） |
| 9 | tools/metadata.py:160 | arg-type（ToolRiskLevel(Any\|None)） | 同 #8，risk 侧同构（声明面缺省改写） |
| 10 | services/galaxy/outcome_absorption_service.py:395 | func-returns-value | `seen.add(nid)` 借位推导式改显式循环（首见加入并保留/重复跳过）——dedupe 保序逐值等价，set.add 语句化以静态表达无返回值（等价改写，沿 wt768 #8 walrus 先例） |
| 11 | services/agent_stats_service.py:151 | operator（int < Callable） | 同名异型改名：SQL label `'count'` → `'execution_count'`（`.label()`、`desc()`、`row.` 三处同步原子改名）——Row 是 tuple 子类，`row.count` 撞 `tuple.count` 方法遮蔽列值，改名后属性访问不再撞方法名；行值/排序/输出 dict 键 `'count'` 全部不变（同名异型改名） |
| 12 | orchestration/summarization_worker.py:153 | arg-type（_generate_summary(Any\|None)→str） | `_generate_summary` 参数 `user_id: str` → `str \| None`——全函数体仅两处 loguru `logger.warning(..., user_id, ...)` 消费（loguru 对 None 兼容），纯声明面放宽；调用方 `task.get("user_id")` 直接过（声明面注解） |
| 13 | services/group_file_service.py:244 | arg-type（经声明面放宽烧 material_retrieval_tools.py:78） | `list_accessible_files(group_ids=)` 参数 `list[UUID \| str] \| None` → `Sequence[UUID \| str] \| None`——Sequence 只读协变承接 list[str] 调用点；值仅透传 `list_accessible_group_ids(requested_group_ids: Sequence[...])`，无原地变更；既有调用方全部兼容（纯注解放宽） |
| 14 | services/friend_match_service.py:297 | arg-type（UserBrief status str→UserStatusEnum） | `status=user.status.value` → `status=UserStatusEnum(user.status.value)`——ORM models.UserStatus 与 schemas.community.UserStatusEnum 为同值 StrEnum（online/offline/invisible 逐值对齐），pydantic 终存枚举与原 str 校验后等值；沿 wt768 #4 判例（声明面枚举侧传递） |
| 15 | services/exam_sprint_intake_service.py:528 | arg-type（TaskType\|None→TaskType） | `coerce_task_type(...)` 补 `default=TaskType.LEARNING` 选中单参重载（返回 TaskType 非 TaskType\|None）——`_task_type_for_day_spec` 只产 learning/training/error_fix 三词、经 TASK_TYPE_ALIAS_MAP 全部命中合法 TaskType，default 分支不可达（声明面重载选择） |

每处均附中文注释说明等价性论据；无 cast、无 type: ignore、无新增 Any 注解。

## 3. 测试面（SECRET_KEY 一次性 env，worktree 隔离无 .env——wt766/wt768 同法）

- tests/unit/test_aurora_control_surface_service + test_ope_gatekeeper +
  test_progress_narrative_service + services/galaxy/test_outcome_absorption：**27 passed**
- tests/unit/test_checkpoint_nudge_{lagging_local,p3b,trigger_day_local} +
  test_failure_semantics + test_executor_tool_locale_signature：**58 passed**
- tests/contract/test_intervention_lifecycle_contract +
  services/test_intervention_lifecycle_service +
  unit/test_intervention_lifecycle_migration_sqlite + unit/test_agent_stats_unwired_truth：**97 passed**
- tests/unit/test_exam_sprint_intake_service：**11 passed**
- tests/services/test_friend_match_public_candidates_cohort_filter +
  unit/test_weekly_growth_narrative_task + tools/test_growth_tools（material_retrieval 消费面）：**21 passed**
- tests/api/test_community_group_file_sharing_api（group_file Sequence 放宽消费面）+
  unit/test_x09_failure_recovery（executor 死信路径）+
  unit/test_v3_fix335_plan_checkpoint_resume（checkpoint_nudge send_nudge 生产链路）：**38 passed**
- 累计触达 16 个测试文件、**252 passed 0 failed**，零回退；14 个触达模块 `import` 烟测全过

## 4. 停手与顺审观察（台账零虚占）

a) **真 bug 登记 1 处（V3-FIX-529，本批唯一台账新开，529 号 grep 复核空闲）**：
   summarization_worker.py:324 `_write_log` 向 redis `rpush("logs:summarization", ..., ex=86400)`
   传 `ex=`，redis-py 7.4.0 `ListCommands.rpush(name, *values)` 无 **kwargs——每次调用即抛
   TypeError，被 `except (TypeError, redis.RedisError): pass` 吞掉；「24h 过期摘要日志队列」
   自上线起零写入，且全仓无 `logs:summarization` 消费方（grep 实录），功能三重死亡。
   修复属行为变更类（补 expire/改 pipeline/删功能三选一），不在声明面授权内 → 停手登记
   不修；mypy 该条 call-arg 正是此 bug 的静态画像，故本批**未烧**此条（基线 76 中保留，
   计入修后 61）。
   注：任务派发时「真 bug 预占 510 起——500-509 已占」口径已过期，主干并发登记已用至 528
   （wt775/wt780/wt781），本批取 529。

b) 顺审观察（静态审读级，均**未触碰、不占号**）：
   - checkpoint_nudge_service.py:132 `int(getattr(checkpoint,"day",0) or (checkpoint.get("day") ...))`
     dict 型 checkpoint 缺 day 键时 int(None) TypeError 裸抛（无 try/except）——唯一生产调用方
     ：1267 的 checkpoint 载荷是否全量带 day 未运行级实证，不动；
   - planning.py:1147 / persistence.py:280 / exam_sprint_dashboard_service.py:111 三条
     str→Literal 族：反序列化边界 str 透传进 pydantic Literal 字段，任何查表/守卫改写都会把
     「非法值 ValidationError」变「静默落缺省」，验证语义不可保等价 → 全部回避未选；
   - document_service.py:678 `int(payload.get("rating"))`：payload 缺 rating 时 TypeError 裸抛，
     下行已对非法值 raise ValueError——TypeError/ValueError 取舍属行为决策，不动；
   - main.py:269 UserService(None) / community_signal_bridge.py:616 NotificationService.create(None)
     ：两处 None 均为带注释的刻意降级设计，放宽构造签名将在 service 内部 self.db 消费面级联
     产生新 mypy 错误，违背零新增 → 回避未选。

## 5. 交付

- 触达 13 个 app 文件 +65/-25 行；ruff 全绿；新增行行长 ≤120（存量超 120 行 39 处未触碰，
  awk 实录逐条比对不在本批改动行）；v3-output/WT778-MYPY11/notes.md 随 commit 入库；
  不 push；不碰运行栈/docker/.env
