# WT652-PARTIAL1 · PARTIAL 模块族首批深查（round-1 审计轴）

- 会话：wt652｜日期：2026-09-25｜基线：main@f55b7ab2｜分支：agent/node-b/wt652/partial1（worktree，未 push，零产品代码改动）
- 上游输入：v3-output/WT639-B01/lifecycle.md（759 模块四态清点，55 PARTIAL）
- 方法：按风险序（对外宣称面大 > 数据写入 > 纯内部）取 10 个 PARTIAL 逐个四问深查：①可达部分宣称什么 ②不可达部分是什么 ③宣称与实现是否诚实 ④测试在测哪面。全部证据本会话开文件亲证（含 backend/app、backend/gateway、mobile/lib、tests/）。
- 判定口径：**诚实 PARTIAL**=可达面兑现其宣称、缺口仅在测试/消费方（合理分期）；**不诚实 PARTIAL**=可达面（或 docstring/端点面）宣称了不可达面/空转面的能力（FIX-330「有表无写入方」同形态）。

## 判定分布

| # | 模块 | 入口（lifecycle 证据） | 判定 | 处置 | 登记 |
|---|---|---|---|---|---|
| 1 | fme_kill_switch_service | api:app/api/v1/goal_intent.py:31 | **不诚实**（半假开关） | 如实化 | V3-FIX-345 |
| 2 | permission_service | api:app/api/v1/auth.py:60 | **不诚实**（统一权限宣称 vs 零 enforcement 面） | 如实化或接线 | V3-FIX-346 |
| 3 | push_feedback_service | api:app/api/v1/push_interaction.py:18 | **不诚实**（写入机制真实但结构性零到达） | 随 FIX-337 裁决 | 既有 V3-FIX-337，不重登 |
| 4 | audit_service | api:app/api/v1/audit.py:17 | **不诚实**（审核台零进料） | 如实化或接线 | V3-FIX-347 |
| 5 | model_fallback_service | agents:app/agents/graph/nodes/review_nodes.py:49 | **不诚实**（降级决策从不执行） | 接线或如实化 | V3-FIX-348 |
| 6 | suggestion_service | api:app/api/v1/suggestions.py:8 | 诚实（分期合理），价值存疑 | 下线裁决或接线+中文化 | — |
| 7 | task_recommendation_service | api:app/api/v1/tasks.py:522 | 诚实（分期合理），无消费方 | 接线或下线裁决 | — |
| 8 | next_step_service | api:app/api/v1/tasks.py:1465 | 诚实（全链接线） | 补测试 | — |
| 9 | leaderboard_self_anchor_service | api:app/api/v1/leaderboards.py:24 | 诚实（全链接线，D-COMM-1 落地） | 补测试 | — |
| 10 | understanding_benchmark_service | services:app/services/understanding_benchmark_evaluator.py:11 | 判定修正：PARTIAL→**DEAD**（双死岛确认） | 随 rule-bj 族裁决 | lifecycle §2.1 已注记，不重登 |

分布：不诚实 5（其中 1 项既有 FIX-337 覆盖）｜诚实 4｜判定修正 1。新登记 V3-FIX-345～348。

---

## 1. fme_kill_switch_service — 不诚实 PARTIAL（半假开关）

- **可达面宣称**：Tri-state（off/shadow/live）kill switch 治理面。`goal_first_minute` 半边真实：POST /goals/analyze-intent（goal_intent.py:127-187）以 `get_feature_mode("goal_first_minute")` 门控（goal_intent.py:133），off 返 disabled、shadow 只记日志、live 返分析——三态语义如实执行。全链通：mobile goal_intent_service.dart:25 → gateway proxy_routes.go:479（O10 回归测试钉死）→ router.py:201。默认 shadow（settings.py:469）为诚实分期。
- **不可达部分**：`task_card_protocol_v2` 绑定（fme_kill_switch_service.py:45-50）**零读者**——全仓除服务自身外无任何代码读该 mode；TaskCardProtocol 真实渲染链（GET /tasks/{id}/card-protocol，tasks.py:621-648 + mobile interactive_task_card.dart:187）不查开关。且 `set_feature_mode`/`summary`（fme_kill_switch_service.py:61-74）零生产调用方（memory_admin.py 的 set_feature_mode 全部作用于 AuroraStage* 服务）——FME 两开关均无运行时翻转 API，只能改 env。
- **诚实性**：docstring（:27-29）宣称「Two features registered … task_card_protocol_v2 — render TaskCardProtocol fields in expanded card」——第二个开关 gates nothing，属 FIX-341「假开关」的模块内同形态：宣称的治理能力无兑现路径。
- **测试在测哪面**：零测试（tests/ 无 fme_kill_switch/FME_TASK_CARD 引用；/goals/analyze-intent 亦无端点测试）——三态分支逻辑零覆盖。
- **处置**：如实化——删除 task_card_protocol_v2 死绑定或把 reader 接进 card-protocol 端点；开关翻转面（API 或 env-only）在 docstring 里如实标注。**已登记 V3-FIX-345。**

## 2. permission_service — 不诚实 PARTIAL（统一权限宣称 vs 零 enforcement 面）

- **可达面宣称**：docstring「统一权限检查和管理 / 权限检查装饰器 / 资源访问控制」。可达部分仅 `get_role_permissions(GroupRole.MEMBER)`（permission_service.py:153-156）被 auth.py:125-130 用于注册时把权限清单写进审计元数据与 user.registered 事件（auth.py:419,430）——**该清单写出去后零下游消费**（grep default_community_permissions 全仓仅 auth.py），是 write-only 遥测，不是授权。
- **不可达部分**：全部 enforcement 机械——check_permission/check_permissions/get_member_role/is_admin/is_owner/can_mute_user/can_kick_user（:158-310）+ require_permission/require_admin/require_owner 三装饰器（:317-419）**零调用方**（装饰器唯一出现处是其自身 docstring 示例）。装饰器还带潜在 bug：`kwargs.get('current_user', {}).get('id')`（:332）对 ORM User 对象必 AttributeError——因从不被调用而从未暴露。
- **诚实性**：宣称「统一」为假——真实群权限 enforcement 内联在 community_service.py:455-457（自算 operator/target 角色判禁言/踢人，与本模块 can_mute_user 逻辑重复）。模块既不统一也不检查，是死掉的平行实现。
- **测试在测哪面**：零直接测试（test_p04_auto_execution_permissions.py 测的是 ActionPermissionService，另一模块）。
- **处置**：如实化（删死 enforcement 面+改 docstring 为「角色权限映射常量」）或接线（community 迁到统一装饰器，顺带修 :332 取参 bug）。**已登记 V3-FIX-346。**

## 3. push_feedback_service — 不诚实 PARTIAL（既有 V3-FIX-337 覆盖，不重登）

- **可达面宣称**：「处理推送交互并更新推断偏好」——process_interaction（push_feedback_service.py:40-65）机制真实且重：更新 PushHistory.interaction_type/status（:67-90）、Redis 交互流水（:129-152）、回填 ignored（:104-127）、经 ProfileWriteService.update_inferred_preference 写 push_receptivity/inactive_push_hours/curiosity_push_receptivity（:57-64,176-203）、同步 PushPreference.consecutive_ignores（:92-102）。
- **不可达部分**：整条写入链的触发端点 POST /push/interaction（push_interaction.py:33）结构性零到达——gateway 无 /push 代理组、NoRoute 白名单仅 /api/v1/auth/*（=FIX-337），mobile notification_service.dart:367 catch 吞错。生产环境上述所有写入**一次都未发生**（FIX-330「有写入机制、无到达触发」同形态）。
- **诚实性**：不诚实，但归属 FIX-337 链路断登记，本轮不重登新号。
- **测试在测哪面**：tests/api/test_push_interaction_api.py:58-91 三测全在测**网关不可达面**（进程内 TestClient 直挂 router）——契约形状测试（:58 甚至验证与 mobile 契约对齐）给出假信心：契约对齐了，到达路径不存在。
- **处置**：随 FIX-337 裁决（补网关 /push 组即整链激活，写入面无需改）；或连同 mobile 回执发送一并下线。

## 4. audit_service — 不诚实 PARTIAL（审核台零进料）

- **可达面宣称**：名为 AuditService，实为**头像审核服务**（get_pending_avatars/approve_avatar/reject_avatar，audit_service.py:14-79）。三端点真实可达：/audit/avatars(+/{user_id}/approve|reject)（audit.py:70-107，get_current_active_superuser 门）、gateway 代理 /audit（proxy_routes.go:1257）——admin 操作还带 @audit_admin_action(category="avatar_moderation") 审计（audit.py:72,89,102），治理姿态完整。
- **不可达/空转部分**：审核队列**结构性零进料**——全仓（backend/app Python + gateway Go 两侧）无任何写入方将 avatar_status 置 PENDING（PENDING 仅出现在 audit_service 自己的 3 处读取，audit_service.py:18,26,56）；用户头像更新路径直设 APPROVED 绕过审核（users.py:200-202：`avatar_url` 更新即 `pending_avatar_url=None; avatar_status=APPROVED`）。故 get_pending_avatars 恒返回 []，approve/reject 实践恒 404（「没有找到待审核的用户」）。
- **诚实性**：宣称「头像需审核」（端点存在+审计分类+待审核字段 pending_avatar_url 全套语义，models/user.py:71）大于实现（零进料+自动通过旁路）。内容安全治理面若被审计方当真即为虚报。
- **测试在测哪面**：零直接测试（test_admin_audit.py/test_security_audit_insert.py 测 admin_audit 中间件，非本模块）。
- **处置**：如实化（声明头像免审直通，删三端点与 PENDING 语义）或接线（上传置 PENDING 走审核）。**已登记 V3-FIX-347。**

## 5. model_fallback_service — 不诚实 PARTIAL（降级决策从不执行）

- **可达面宣称**：docstring 四条：「1.追踪模型在审查中的表现 2.检测持续审查失败 3.**触发模型切换** 4.管理模型降级策略」。接线真实存在于 chat 审查链：review_nodes.py:565 record_performance、:671/:688 should_fallback 均被调用（惰性 import :49）。
- **不可达部分**：决策产物**零下游消费**——fallback 触发后只 log warning + 把模型名写进 review_context["fallback_model"]/context_data["suggested_model"]（review_nodes.py:671-693），全仓无任何读取方（state.py:95 声明 `fallback_model: str | None  # 建议降级的生成模型` 无人读；generation 节点不读 suggested_model）——**「触发模型切换」从未发生**，模型不会被切换。另 `_get_fallback_model`（review_nodes.py:253-283）定义后零调用；服务为进程内单例（model_fallback_service.py:501-509），重启丢统计、多 worker 各记各账，「持续失败检测」仅单进程窗口有效。
- **诚实性**：4 条宣称中核心卖点（3）不成立：检测在测、切换没切。韧性宣称（「质量问题自动切更强模型重新生成」，:264-270 还会给用户流发「切换到更强大的模型重新生成…」delta）与实现不符——该 delta 只在 should_fallback 命中时发送，而命中后的「切换」只是记一个无人读的建议键。
- **测试在测哪面**：零测试（test_llm_timeout_fallback/test_retrieval_fallback 等均其他机制；test_capability_selection_policy 的 model_fallbacks 是 fallback_plan 另一套）。
- **处置**：接线（generation 侧消费 suggested_model 使切换真实发生）或如实化（docstring/用户文案降级为「记录与建议，不自动切换」+删 _get_fallback_model 死助手）。**已登记 V3-FIX-348。**

## 6. suggestion_service — 诚实 PARTIAL（分期合理；价值裁决候选）

- **可达面宣称**：Vision Item 3「输入时实时意图预测」。GET /suggestions 全链通：router.py:184、gateway proxy_routes.go:427-430；实现为规则+历史启发式，AI 部分诚实标注 placeholder（suggestion_service.py:77 TRACKED(TD-008)）。
- **不可达/缺口部分**：①零客户端消费——mobile 只调 /tasks/suggestions（IntelligentTaskService，api_endpoints.dart:114），全 GET /suggestions 无 caller；②规则关键词全英文（:27-35 "create"/"plan"/"review"/"analy"/"trans"/"spr"/"b"），对中文输入结构性不匹配，即使接线也几乎恒走 "Ask about 'X'" 兜底（:78-83）；③personalized 面依赖 user:{id}:recent_queries，唯一写点是本模块自身（:116,132）——自 feeding，无外部史。
- **诚实性**：诚实——docstring 未夸大（自认 heuristic），端点兑现「返回建议」。不诚实的是产品价值：宣称 Vision 能力但无消费方+英文规则对中文产品无效。
- **测试在测哪面**：零（test_proactive_suggestion_*.py 三文件 import 的是 proactive_suggestion_service，另一模块，test_proactive_suggestion_feedback.py:51 亲证）。
- **处置**：下线裁决（零消费方）或接线+中文化重写。不登记 FIX（无虚假宣称机制）。

## 7. task_recommendation_service — 诚实 PARTIAL（分期合理；无消费方）

- **可达面宣称**：「基于用户偏好和知识图谱」的个性化任务推荐。GET /tasks/recommendations/micro（tasks.py:513-536）真实消费 PersonalizationEngine + KnowledgeNode/UserNodeStatus（task_recommendation_service.py:46-87），gateway 代理在位（proxy_routes.go:128）。
- **不可达/缺口部分**：mobile 零调用（grep tasks/recommendations 空，mobile 侧 recommendations 命中均为 community/friends）。另注意：响应侧 `estimated_minutes <= 15` 过滤（tasks.py:534-535）与 profile.preferred_task_duration（engine.py:472，focus_duration 派生）耦合——无 context 参数且 micro_task_friendly=False 时 duration 不压到 15，端点可恒返 []；上下文参数文档已声明，属可用性缺陷非虚称。
- **诚实性**：诚实——实现与宣称一致，缺的是消费方与测试。
- **测试在测哪面**：零。
- **处置**：接线（mobile 碎片时间入口消费）或下线裁决。不登记 FIX。

## 8. next_step_service — 诚实 PARTIAL（全链接线）

- **可达面宣称**：任务完成后建议下一步动作，LLM 3s 超时+规则兜底（next_step_service.py:59-68），docstring 如实。
- **可达性**：全链真实：tasks.py:1462-1467 完成流调用 → 响应 next_actions（tasks.py:1527-1529）→ mobile task_completion_result.dart:21 解析 next_actions。
- **诚实性**：诚实——宣称与实现一致（异常兜底宽 except 是延迟护栏设计，可接受）。
- **测试在测哪面**：零专属测试（lifecycle 0f/0r 亲证）。疲劳比/兜底分支零覆盖。
- **处置**：补测试即可（分期合理，唯一欠账是测试）。

## 9. leaderboard_self_anchor_service — 诚实 PARTIAL（全链接线，D-COMM-1 落地）

- **可达面宣称**：「自我 7 日锚视图」（D-COMM-1 裁决落地，docstring :1-21 明诺 D20 诚实数据：空窗补零不内插、has_any_data 语义、UTC 落日）。实现与承诺一致：_day_index 防御未来/乱序（:44-50）、状态过滤防 abandon 双计（:71-72 与 docstring :10-12 对应）、真零语义（:101）。
- **可达性**：全链真实：GET /leaderboards/self-anchor（leaderboards.py:276-296）→ gateway proxy_routes.go:1067 → mobile LeaderboardRoutes.selfAnchor（leaderboard_routes.dart:13-18）← sprint_screen.dart:64 入口。
- **诚实性**：诚实——docstring 语义承诺逐条可在实现中对上。
- **测试在测哪面**：零（find tests 无 self_anchor 文件）。
- **处置**：补测试（补零/真零/窗口边界是高价值单测点）。

## 10. understanding_benchmark_service — 判定修正：PARTIAL→DEAD（双死岛确认）

- **四问**：①「可达面」=唯一生产消费方 understanding_benchmark_evaluator.py:11——但该消费方是 rule-bj DEAD（lifecycle §2.1 :49 已注记「同族 service 亦零外部消费（双死岛）」）；②不可达部分=全部（fixture 驱动的 benchmark harness，:51-107，无运行时触发路径）；③诚实性=N/A（无对外宣称面，纯内部评估资产）；④测试=零。
- **判定**：生产消费净额=0，lifecycle 的 PARTIAL 判据「仅同层互调」在消费方自身 DEAD 时失效——应修正为 **DEAD**。
- **处置**：随 rule-bj v1 未接线族裁决一并处置（下线，或作为理解力 benchmark 资产迁 scripts/devtools/ 并在台账显式登记）。不新登记 FIX（lifecycle §2.1 已在账注记）。

---

## 本轮新登记汇总（台账 v3/06_agent_fleet/DYNAMIC_ISSUES.md）

| 号 | 一句话 |
|---|---|
| V3-FIX-345 | fme_kill_switch_service 的 task_card_protocol_v2 假开关：零读者+无运行时翻转面，宣称治理两特性实只治理一 |
| V3-FIX-346 | permission_service「统一权限检查」宣称 vs 零 enforcement 面（真 enforcement 内联重复于 community_service.py:455-457），可达消费仅注册元数据 write-only |
| V3-FIX-347 | audit_service（头像审核）审核台结构性零进料：无 PENDING 写入方+users.py:200-202 自动通过旁路，approve/reject 实践恒 404 |
| V3-FIX-348 | model_fallback_service 降级决策零下游消费：宣称「触发模型切换」实只写无人读的建议键（state.py:95 死字段+_get_fallback_model 死助手+进程内单例） |

不重登：push_feedback_service（=V3-FIX-337 链路断的下沉证据，测试在测不可达面一节并入 337 语境）、understanding_benchmark_service（lifecycle §2.1 双死岛已注记）。

## Top 3 风险

1. **model_fallback_service（FIX-348）**：chat 主链审查失败路径给用户发「切换到更强大的模型重新生成…」系统 delta（review_nodes.py:267-273）但切换从不发生——用户可见承诺与运行时行为直接矛盾，且零测试掩盖。
2. **permission_service（FIX-346）**：权限治理宣称面（统一检查+装饰器+30 项权限枚举）全为死代码，真实群管授权散落内联——安全治理审计若以本模块为准会得出错误结论；未来若有人「接线」装饰器还会踩 :332 的 ORM 取参必崩 bug。
3. **audit_service（FIX-347）**：内容安全治理姿态（审核端点+审计分类+pending 字段全套）建立在零进料队列上——头像实际免审直通（users.py:200-202），若产品宣称「头像需审核」即为合规虚报。

## 对 lifecycle 本身的反馈（供 round-2）

- PARTIAL 判据「仅同层互调」未给消费方自身的活性打折：understanding_benchmark_service 型「消费方已死」的 PARTIAL 应降 DEAD（本轮 1 例）。
- 机械索引的测试计数按「import 服务模块」统计，会漏「经 API 层间接测到」的面（push_feedback_service 0f/0r 但有 API 测试 3 测）——测试在测哪面的四问仍需人工，机械数只能作粗筛。
- 诚实 4 例（suggestion/task_recommendation/next_step/self_anchor）的共同缺口是零测试而非断链，适合打包一张「PARTIAL 族补测试」卡，不必逐模块开卡。
