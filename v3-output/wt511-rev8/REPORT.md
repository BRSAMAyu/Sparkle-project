# wt511 独立审查报告 — 审查轮 8（wt467..wt510 单日 30+ 卡集成窗 backend/gateway/mobile 产品码改动）

- 审查人：wt511（独立会话，未参与窗口内任何实现）
- 审查基座：worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt511-rev8`，分支 `wt511-rev8`，base = main HEAD `67d0e09f`
- 审查窗口：`310d6b22..67d0e09f`（轮 7A 权威覆盖至 wt466 集成基座 310d6b22 → 当前 main 头；125 commits，产品码 diff：backend/app 78 文件 + gateway 3 + mobile/lib 21（不含 gen/l10n 纯删除面），累计 +2561/−12951 其中大头为 l10n 死键收割纯删除）
- 方法：按风险域逐对象读 diff + 读当前完整实现；疑点写探针测试跑真实代码（backend venv + sqlite 内存库 / go test / 移动 Flutter test），只有探针红的记 finding，绿记「已验证」。探针为临时文件（`backend/tests/unit/test_wt511_probe_*.py`），结论留痕于本报告后已删除，未提交。
- 既知假红族（llm_router/adaptive_replanning/bert/P0/macos journey）未作为本轮信号。

## 总 verdict

**fix-required（窄）**：2 个 finding——2×P3，均探针实录红：

1. **V3-FIX-231（P3）**：visual-elements 发布闸旗与 /release-flags 契约旗**双权威脑裂**（wt483 卡 A 五旗权威 vs wt489 FIX-182 独立开关，互不联动）。
2. **V3-FIX-232（P3）**：截断族判定缺口——`finish_reason="content_filter"`（provider 内容审查截断）与 `"stop"` 同判完成，部分回答照常冒充完整轮落库（FIX-166 卡自述「provider 授权截断同族保守语义」的未竟面）。

窗口主线交付全部经探针/测试验证成立、无回归：wt492 cohort 隔离四处补齐、wt482/489 发布闸挂载语义（组注册级依赖先于端点鉴权，FastAPI 依赖序实测成立）、wt487/494/499/507 时区族列级定钟（FocusSession 墙钟/StudyRecord+Task.completed_at UTC/due_date 本地日历三种钟抽查全对位）、wt502 向量 stamp 全写入面收口、wt481 同事务收编 8/8、wt476 语义缓存两道门改判、wt478 三卡、wt504/505 质量烧减抽验零语义漂移。两项 P3 建议开修复卡，不阻塞集成。

## Finding 列表（已按 V3-FIX-231/232 登记 DYNAMIC_ISSUES.md 表尾）

### V3-FIX-231 · P3 · visual-elements 发布闸与 /release-flags 契约旗双权威脑裂

- 位置：`backend/app/api/v1/router.py:138-147`（`_require_visual_elements_enabled` 读 `settings.ENABLE_VISUAL_ELEMENTS`）与 `:320-325`（组注册级依赖）；`backend/app/config/settings.py:147`（`RELEASE_ENABLE_VISUAL_ELEMENTS`，wt483 卡 A 五旗权威）与 `:1169`（`ENABLE_VISUAL_ELEMENTS`，wt489 FIX-182 新增独立开关）；`backend/app/config/release_flags.py:16-23`（契约键集冻结含 `visual_elements`，值取自 RELEASE 权威）
- 复现探针（实录红 ×2，真实 api_router 全挂载 + TestClient）：
  1. `RELEASE_ENABLE_VISUAL_ELEMENTS=True` + `ENABLE_VISUAL_ELEMENTS=False` → `release_flags_response()["visual_elements"]==True` 而 `GET /api/v1/visual-elements/config` → **403 FEATURE_DISABLED**（契约声称开启、端点全关）；
  2. 反向：`ENABLE_VISUAL_ELEMENTS=True` + `RELEASE_ENABLE_VISUAL_ELEMENTS=False` → 深链越闸撞鉴权 401（端点活）而契约 `visual_elements==False`（实际暴露、契约声称关闭）。
- 危害：发布 rollout 只会翻五旗契约面（`/release-flags` 是移动端 provider 解码面、也是运维口径）→ 翻了不生效（8 条 visual-elements 路由仍 403）；反向翻 `ENABLE_VISUAL_ELEMENTS` 则 LABS 面静默暴露而契约/监控面仍报 false。违反 `release_flags.py` 模块自述的单一权威纪律（「禁止双权威脑裂」恰是该模块立卡动机）。两旗默认均 False，故当前默认态无实际暴露，P3 不升级。
- 建议修法：二选一收口——①闸改读五旗权威（`Depends(require_release_flag("RELEASE_ENABLE_VISUAL_ELEMENTS"))`，与 shop/inventory 同形，删 `ENABLE_VISUAL_ELEMENTS`）；②闸保持独立开关则把 `visual_elements` 键从契约键集摘除（连带契约快照与 `test_release_flag_authority` 对齐）。修后以本探针两条断言作回归锁。

### V3-FIX-232 · P3 · 截断族缺口：finish_reason="content_filter" 与 "stop" 同判完成

- 位置：`backend/app/services/llm_service.py:1726`（`_stream_truncated = (not _saw_finish_reason) or _finish_reason_value == "length"`）；落库/路由面 `backend/app/api/v1/chat.py:840-852`（仅 stream_interrupted 分支不落库）
- 复现探针（实录红）：脚本化 provider 流 `[text("部分回答"), finish_reason="content_filter"]` → `chat_stream_with_tools` **无 `stream_truncated` 产出**（探针实录）→ REST /stream 面 done `completed=true`、部分（被审查掐断的）回答照常落库为完整轮。
- 危害：与 FIX-155/160/166 同族「部分内容冒充完整答案」，且违反 FIX-166 卡面自述语义（「provider 授权截断同族保守语义」「截断族=缺哨兵∪length」——content_filter 亦属 provider 授权的不完整收尾）。窗口内部署 provider 集（DeepSeek/Qwen/GLM/MiMo）在敏感内容上会发射该 finish_reason，非纯理论形态。`/ws/chat` 轨道共用同一生产者（generation_node 同族分支），一并受影响。
- 对照（同探针组，绿）：首帧 EOF（空流）→ 截断正确；usage 尾帧（choices 空）不作完成哨兵 → 截断正确；usage+`stop` → 不误标 → 完成正确。判定函数是共享单点，收口一处即全轨道生效。
- 建议修法：截断值面从单值等值改集合判定 `{"length", "content_filter"}`，`truncation_reason` 加 `content_filter_truncated` 亚型区分观测面；`test_v3_fix166_length_truncation_family.py` 同族补两态锁；docstring 契约声明同步。

## 逐域 verdict 与已验证清单

### 1. 身份/权限面（最高）

| 对象 | verdict | 证据 |
|---|---|---|
| wt492 V3-FIX-20 cohort 隔离（`community_service.py` 四面+豁免） | **approve** | 探针组 7/7 绿（两用户/两群隔离、词表钉、statement capture、成员豁免、计数不错位）。逐面核对：`search_groups`（:554 谓词+`my_role IS NOT NULL` 豁免）、`count_public_groups`（:628 同谓词同豁免、`community.py:1938` 传 `current_user.id`）、`get_public_group_tags`（:675 无豁免，防标签回流）、推荐召回（`group_recommendation_service.py:390`）。谓词锚=活跃 OWNER 的 `registration_source`（`not_deleted_filter` 全程在位，软删成员不洗白）；全仓 `is_public` 公开群查询面 grep 仅此四处，无漏网发现面。两 API 调用方（:1873/:1928）均传 user_id。边界保持（feed 关系 scope/群内关系面/直接 ID 访问）与 FIX-08 测试守护一致，属登记内设计决策 |
| wt482/489 发布闸（router 依赖 vs 鉴权语义） | **fix-required（窄）→ V3-FIX-231**；闸机制本身 approve | FastAPI 依赖序实测：组注册级 `dependencies=[Depends(...)]` 先于端点 `get_current_user` 生效（`test_visual_elements_gate` 3/3、`test_shop_entry_gate` 4/4：无鉴权深链 403 FEATURE_DISABLED 而非 401，即闸先于鉴权）；fail-closed（未知旗/缺省=False 视同关）；组作用域守卫通过（leaderboards/self-anchor 不波及，T36 教训落实为组注册级而非前缀级）；`test_release_flag_authority` 15/15。唯一缺陷=双旗脑裂，见 V3-FIX-231 |
| FIX-217 executor 身份链现状 | **approve（latent-only，处置正确）** | `error_handler.py:31/:185` `user_id: str = None` 缺省仍在（wt504 有意不修），但三个生产调用点 `chat.py:798/:928/:960` 全部显式传 `str(current_user.id)`；executor 侧 `uuid.UUID(str(user_id))`（executor.py:582/:625）对 None 硬抛=fail-closed；`AgentToolCall.user_id` 等值过滤与 `_load_run_row → get_run(user_id=...)` 归属校验在位。无 None 可达路径，V3-FIX-217 行继续 OPEN 合理 |

### 2. 数据正确性

| 对象 | verdict | 证据 |
|---|---|---|
| wt487/494/499/507 时区族列级定钟 | **approve** | 三列锚定实证：①`FocusSession.start_time`=用户本地**墙钟 naive**（mobile 全部生产者 `DateTime.now()` 本地→`toIso8601String()` 无时区后缀→Pydantic naive→`_to_utc_naive` 原样透传，`focus_service.py:50-52`）；②`StudyRecord.created_at`/`Task.completed_at`=**UTC naive**（BaseModel `default=_utcnow`）；③`Task.due_date`=本地日历 Date。抽查全部窗口端点列钟匹配：statistics overview（due_date 本地日+FocusSession `local_midnight_wall`）、daily trend（StudyRecord/Task.completed_at 走 `local_midnight_as_utc_naive` 窗口+`local_date` 应用层分桶）、experience_readouts 7d 专注窗（wall）、dashboard_router `_wall_lookback`（wall+新用户注册时刻同钟换算）、predictive 两处（wall）、struggle 混合窗分列（Task.created_at/updated_at 走 UTC 换算、FocusSession 走 wall、due_date 比本地日）。FIX-197 SSOT 两调用方（`experience_readouts.py:309`/`goal_router.py:494`）共用 `_user_local_today`（push_preference.timezone 标量直查防 lazy-load，Asia/Shanghai 回落）。同族余量已登记 V3-FIX-221（P4，非本轮重复计）。钟族测试 67 绿 |
| wt502 V3-FIX-215 向量 stamp | **approve** | E-05 契约面（KnowledgeNode/DocumentChunk，唯二带 `embedding_model/embedding_dim` 列且读侧 `_embedding_version_filter` 生效的模型）写入点全量 grep：8 处全部已 stamp（celery_app:245、celery_tasks:115、galaxy_service:3588、expansion:418、knowledge_integration:290、seed_library×3）。`cognitive_service:212`/`scene_consolidation:330` 写的 CognitiveFragment/EpisodicMemory **无 stamp 列**且不在版本过滤读面=契约面外，非遗漏。hasattr 静默 no-op 风险面核查通过 |
| wt481 V3-FIX-40 同事务收编 | **approve** | 收编点 8/8：plan_state_service 5（:203/:322/:363/:399/:621）、notification_service 2（:280/:395）、persona_service 1（:198），与卡面「8 处内部 commit」逐一对应；executor 打点含嵌套恢复（`previous_tx_guard`，executor.py:745-750）；owned 会话同打点语义正确；锁测 6/6 绿（真实服务非桩 commit）。残余 P3-7（断言语义/reversible 元数据/_resume_or_replay 信任）承原行在案 |

### 3. 流与缓存

| 对象 | verdict | 证据 |
|---|---|---|
| wt476 V3-FIX-169 缓存门（gateway） | **approve** | gate1 `callerExtraContextCount` 在网关注入前快照（判据还原为「调用方携带编排面 extra_context」原义，注入 map 继续供 scope/引擎载荷=键值契约不变）；gate2 历史视图剔除窗口只裁**本轮已持久化的尾条同文 user 消息**（`last.Role=="user" && last.Content==input.Message` 仅末元素），截断轮（FIX-155 出口）永不入缓存有守卫位。三探针红→绿（B：首轮带 session_id 必中缓存、engine call=0；C：空 session_id 后续轮命中；guard：截断轮不投喂）+ 全 gateway `go test ./...` 全绿。观察（不立 finding）：false-trim 需「上轮同文+本轮 save 失败」双条件，届时网关确无上下文可依，语义可辩护 |
| wt478 FIX-165/166/167 边界 | **fix-required（窄）→ V3-FIX-232；其余 approve** | FIX-165 类名消毒映射+结构化留痕（`_sterilized_error_class_label`，wt468 实录红的 165 三测随套件 20 绿）；FIX-166 截断族单点判定（llm_service:1726）覆盖 REST+/ws 双轨道，tool_call_end 截断轮抑制在位；FIX-167 单/双引号并集提取（fix53 SSE 套件 4 绿）。边界探针：首帧 EOF 绿、usage 尾帧绿、usage+stop 绿；content_filter 缺口红 → V3-FIX-232 |

### 4. 质量烧减语义安全

| 对象 | verdict | 证据 |
|---|---|---|
| wt505 UNAWAITED_FUTURES 34→0 | **approve** | 全量 diff 逐 hunk 核对：34 处全部为「裸 fire-and-forget future → `unawaited()` 显式包裹」，**零处 `await X` 改 `unawaited(X)`**（jpush/firebase/sync_engine/session_refresh/auth_provider 等；jpush getRegistrationID `.then` 链仅外层包裹+缩进，回调体零改动）。unawaited 不吞错（unhandled error 仍走 zone handler），行为零变化成立 |
| wt504 mypy 1095→1041 | **approve** | 抽验 10 处（multi_dimensional_learner×2、execution_tracer replay 签名重排、cache set ttl、circuit_breaker `_result_window`、collaboration_workflows categorization、enhanced_orchestrator active_tasks/active_plans、orchestrator dual_core_context、age_client/learner select_route）：全部为 `T = None → T \| None = None` 与容器 var 注解，零逻辑/零 await 语义改动、零 `# type: ignore` 新增；error_handler 两处身份参数有意绕行登记 217 的纪律执行到位。触达测试 60 绿 |
| FIX-183 transparency 孤儿屏删除 | **approve** | 状态层（TransparencyPreferences/Notifier）先行拆出至 `transparency_preferences.dart`，屏体删除后 `transparency_settings_screen` 全仓仅存文档性注释引用，零悬空 import；mobile auth+触达面 59 绿 |

## 探针清单（结论留痕，文件已删未提交）

1. `backend/tests/unit/test_wt511_probe_ve_splitbrain.py` — V3-FIX-231 双向脑裂，2 红（finding 证据）。
2. `backend/tests/unit/test_wt511_probe_trunc_family.py` — P1 首帧 EOF/P2 usage 尾帧/P3 usage+stop 绿，P4 content_filter 红（finding 证据）。

## 测试与守卫记录（本轮实跑）

- backend：cohort 7/7、release_flag_authority 15/15、visual_elements_gate 3/3、shop_entry_gate 4/4、钟族（grep 触达 15 文件）67 绿、FIX-40 6/6、FIX-155/166/167+fix53 SSE 20/20、四域合并复跑 55/55、wt504/40 触达 60 绿。
- gateway：`go test ./...` 全包 ok（handler 30.3s 含缓存门三探针）。
- mobile：`flutter test test/features/auth` 59 绿（FIX-17/205 身份面）。
- 本轮全部为审查性运行，产品码零改动；docs 面=本报告+台账两行+本文件。
