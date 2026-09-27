# WT768 — mypy 棘轮烧减批十实施记录（基线 91 → 76，净降 15，零新增）

- 分支 `agent/node-b/wt768/mypy10`（base 72f3e2c6 = main），本文件随修复 commit 同提交
- 纪律沿批八/九：真 bug 0 容忍（停手登记制）；cast 0；新增 ignore 0；bare-Any 注解 0；
  只做声明面注解 / 同名异型改名 / 安全收窄；判例沿用（mypy 1.20.2 注解赋值不发生赋值收窄，
  有非 Optional 消费面一律改名）
- 避让在航卡：plan_review_service.py / community.py / guest_seed_service.py（wt767）零触碰

## 1. 基线口径（冷缓存，MYPY_CACHE_DIR 独立）

```
cd backend && MYPY_CACHE_DIR=<独立目录> ./.venv/bin/python -m mypy app --ignore-missing-imports
```

- worktree 冷缓存 **91 errors in 82 files (checked 1384)**；main 同法冷缓存 **91**；
  去行号逐条 diff **空**（/tmp/mypy_main_out.txt vs /tmp/mypy_wt768_out.txt，DIFF-EMPTY 实录）
- 环境注记：worktree 无 .venv（gitignore），`backend/.venv` symlink → 主仓 venv；亲证
  `sys.prefix` 与主仓直呼完全一致（homebrew python 3.11 + mypy 1.20.2 同 site-packages），
  本卡实测口径与任务基线 91 逐数吻合（wt767 notes 所记 202 环境差在本机不复现）
- `backend/app/gen` symlink → 主仓 gen（不入库，沿 wt767 先例）
- 修后冷缓存（独立第三 cache-dir）**76 errors in 67 files**；与基线清单去行号 diff：
  **移除 15 条、新增 0 条**逐条核对

## 2. 选中 16 → 烧减 15（1 处按判例停手，见 §4a）

| # | 文件:行（base） | 错误码 | 修法（分类） |
|---|---|---|---|
| 1 | report_logger.py:16 | arg-type（Path(str\|None)） | `base_dir or os.getenv(...)` 直连调用 RHS 时 mypy 1.20.2 or-join 泄 None（独立 reveal 亲证：直呼 getenv=str、or 式=str\|None）；getenv 提升局部 `env_dir` 再 or——运行逐字节等价（声明面重排） |
| 2 | arbitration_service.py:658 | arg-type（fromisoformat(str\|None)） | 推导已滤 `c.resolved_at` 真值但窄化不跨语句；循环体首加 `if c.resolved_at is None: continue` 收窄——上游过滤下分支不可达（安全收窄） |
| 3 | group_recommendation_service.py:51 | arg-type（dict[Any,int]→dict[UUID,float]） | `_normalize_scores` 参数 dict→`Mapping[UUID, float]`（Mapping 值型协变，int→float、Any 键可过）；纯注解放宽 |
| 4 | community_squad_service.py:117 | arg-type（GroupType vs GroupTypeEnum） | GroupCreate(type=…) 改传 schema 侧 `GroupTypeEnum.SPRINT`（两 StrEnum 逐值对齐 "sprint"，pydantic 校验后等值）；ORM 比较面（:78/:164）保留 models GroupType 不动 |
| 5 | source_state_encoder.py:147 | arg-type（dict 不变型） | `estimate_state_space` 参数改 `Mapping[str, set\|list\|tuple]`（协变承接 dict[str,list[str]] 调用点）；纯注解 |
| 6 | plan_quota_service.py:354 | arg-type（append InstrumentedAttribute） | `conditions` 局部显式注解 `list[ColumnElement[bool] \| InstrumentedAttribute[bool]]`（and_(*conditions) 接受面亲证不变）；纯注解 |
| 7 | plan_feedback_service.py:144 | arg-type（priority str→Literal） | `append_user_feedback` 参数 `priority: Literal["high","normal"]`；唯一调用方 plan_review_service:1911 传二字面量三元——mypy 1.20 三元字面量保型实测通过，零新增；该行不在 wt767 在修改动面 |
| 8 | belief_trace_inspector.py:410 | misc（List[dict\|None]） | 双调 `_loads` 谓词改 walrus 单调（`_loads` 纯 json 解码亲证）；单调次数减半、结果逐值等价 |
| 9 | unified_analysis_service.py:76 | arg-type（tags list[Any\|None]） | `pattern_type = .get(...) or ""` 后同值判断——falsy（None/""）两法均落 tags=None、truthy 逐值相同（安全收窄） |
| 10 | executions.py:424 | arg-type（join list[Any\|None]） | 元素 `str(item.get("label") or "")` 与过滤器同式——过滤保证真值，f-string 输出逐字节等价（安全收窄） |
| 11 | persistence_layer.py:248 | misc（List[dict\|AdaptationRecord]） | hasattr 分派改 `isinstance(record, dict)` 分派（AdaptationRecord 有 to_dict、dict 无，运行分派路径等价） |
| 12 | mode_workflow_config.py:185 | arg-type（str→Literal） | 集合成员 ternary 改保型查表 `_TEAM_COLLABORATION_MODES.get(mode, "auto")`（键=白名单词、值=同名字面量，缺省 auto；运行语义逐值一致） |
| 13 | observability_logger.py:486 + schemas.py:465 | arg-type（event_type str→Literal） | 抽 `ObservabilityEventType` alias：原 9 值 + 既有发射值 expert_selected / expert_invoked / expert_overridden / expert_fallback / user_feedback_bound（event_type= 实参全量 grep 逐值对齐）=14 值；dataclass 字段与 log_event 参数同源 alias。纯声明面——ObservabilityEvent 为 dataclass 无运行校验，Redis 序列化面零变化 |
| 14 | persdyn_attractor_service.py:109 | arg-type（dict.get(str\|None)） | `REFLECTION_VALENCE_MAP` 显式注解 `dict[str \| None, float]`（None 键走缺省 0.4 既有行为，唯一消费点 ：450）；纯注解 |
| 15 | error_book_signal_processor.py:97 | assignment（int += float） | `Counter[str]` → `defaultdict[str, float]`（recency_weight 返回 float；缺键 0.0 起加与 Counter 0 起加数值等价，下游 items/排序取值面同形） |

每处均附中文注释说明等价性论据；无 cast、无 type: ignore、无新增 Any 注解。

## 3. 测试面（SECRET_KEY 一次性 env，worktree 隔离无 .env——wt766 同法）

- tests/unit/services/test_arbitration_service.py + test_belief_trace_inspector.py +
  test_community_squad_mvp.py：**40 passed**（含 MVP 源码导入扫描钉子）
- test_source_state_encoder + test_persdyn_attractor_service +
  orchestration/test_mode_workflow_config + unit/orchestrator/mixins/test_persistence_layer_mixin：**29 passed**
- services/test_unified_analysis_service + services/test_plan_feedback_decision_vocab（覆盖
  append_user_feedback 真调用）+ services/test_error_book_service + test_errorbook_review_500_fix +
  test_evidence_resolve：**59 passed**
- test_community_shared_errors + test_community_study_room + api/test_group_type_official_parity
  （GroupType/GroupTypeEnum 同值对齐钉）+ api/test_executions_api + test_analytics_truth_batch2：**42 passed**
- test_v3_fix287 + test_v3_fix258 + test_v3_fix55_guest_seed_observability +
  orchestration/test_multi_agent_adapter（persistence_layer 消费面）：**18 passed**
- 补充：test_stage33_journey_events（plan_quota 消费面）**4 passed**；
  decision_vocab 复跑 **39 passed**；导入烟测（ReportLogger 实例化 / ObservabilityEvent(event_type="expert_selected") /
  PlanQuotaService / _normalize_scores）全过
- 累计触达 18 个测试文件、**192 passed 0 failed**，零回退

## 4. 停手与顺审观察（台账零新开——无运行级实录不占号）

a) **选中未烧 1 处**：feedback_driven_generation.py:255 record_user_feedback(feedback_type=...)。
   本文件 `FeedbackType`（rating/quality/accuracy/specificity/regeneration_request）与
   review_history_service `FeedbackType = ContentReviewFeedbackType`（satisfied/unsatisfied/...）
   **同名异型且词表不相交**——按判例改名不可行（值不同非注解差），直接传枚举会引入新错；
   维持既有 `.value` 字符串透传（运行行为原样），加注说明后回退。该 mypy 错误保留在基线内。

b) 顺审观察（静态审读级，均**未触碰、不占号**，留待运行级实证后再登记）：
   - `UserStreakStats.last_activity_date: Mapped[date | None]` 套 `DateTime` 列
     （achievement.py:219）——驱动回读实为 datetime，声明漂移；streak_signal_processor:45 将其传
     recency_weight（`_normalize_timestamp` 访 `.tzinfo`，纯 date 将 AttributeError），写入链
     achievement_engine `_coerce_activity_date` 与 guest_seed datetime 混用，未运行级实证；
   - leaderboard_service.py:487 `selectinload(GroupMember)` 套在 `select(User)` 查询上，语义存疑
     （member_contributions 实际来自独立 members 查询），疑死代码或无效 loader，未运行级实证；
   - mypy 剩余 76 条中的 call-arg/attr-defined 族（photons metadata vs extra_data、
     graph_knowledge_service 缺失方法、correction_feedback 关键字不匹配等）存在同名异型/陈旧调用面
     嫌疑，逐条需运行级判定真假，留给后续批次按判例处置。

c) 号位复核：V3-FIX-499 已被 wt767 登记 OPEN（total_days 收口）、500 已被 wt765 登记
   （AURORA_DEFAULT_MODE）、501 已被 wt765 登记（metacog proxy kill switch）——主仓+本分支台账
   grep 实录；本批零新开，无虚占。

## 5. 守卫与产出

- ruff check 17 个触达文件 **All checks passed**（plan_quota_service I001 import 排序随修——
  ruff --fix 自动收口）；新增行最大 108 字符 ≤120（E501 配置 line-length=120 下零告警）
- mypy 复核（ruff 修后）冷缓存仍 **76**，零漂移
- 不 push；主仓只读；docker/运行栈/.env 零触碰；app/gen 与 .venv symlink 不入库
- 产出：v3-output/WT768-MYPY10/notes.md（本文件）
