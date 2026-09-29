# V4-U06 预备侦察报告（scout, 2026-09-30, main@1095525a, 只读取证零改动）

> 用途：U06（HEAVY, ui-onboarding 锁, deps F04✓U01✓）派单直接引用。来源：只读侦察 agent 全文归档（未独立审查——侦察产物非验收证据，U06 实现时逐条亲验）。

## 一、验收面拆解（要点）
- 验收①「真实UI注册/升级不落意外我的页」：
  - 升级腿缺陷已定位：`guest_upgrade_screen.dart:74/:127` 邮箱/社交两条 upgrade 成功显式 `context.go('/profile')`——现码即红的天然反例（FIX-541 直接实现面），最小增量=改落点+裁决。
  - 注册腿：register 成功无显式导航，落点靠 `routes.dart:206-212` redirect（pending??'/home'）；wt802 实测 6/7 落「我的」与静态语义不符——**须先复现冻结反例**（J02 驱动 `j02_fastpath_journey_test.dart:707-739` 已内置 post_register_landing 取证）。
  - 可失败测试：a) guest_upgrade 两腿断言目标路由≠/profile（现码红）；b) J02 驱动落点断言收紧（FIX-536 预登记方向）；c) routes redirect 纯函数一正一反。
- 验收②「首卡与确认文案、DB同一次receipt一致」：首卡=J-04 FirstActionCard（`first_action_card.dart:332` 起；approve 幂等 `first_action_repository.dart:242-247`→`action_proposals.py:230-241`）；读面 `GET /journey/first-action`（含 receipt）。**纯增量=确认后 receipt 可见反馈面**（现仅 invalidate 无反馈）；反馈必须投影同一 GET 读面禁止本地拼装；与 FIX-567 触发链 W2 合并落点（见二）。
- 验收③「guest示例不污染真实长期记忆；无API旁路冒充首程」：三只既有锚（`test_j02_seed_memory_namespace.py:64-68`/`test_guest_upgrade_seed_statistics_cleanup.py`/`test_guest_seed_example_marker.py`）；增量=身份切换隔离断言到 U06 语义级（auth_provider.dart:317-318 清除链）+"无API旁路"=必须真实 UI 动作（非 provider 直捅），I01 走既有 `api_endpoints.dart:251` 零新端点。

## 二、FIX-567 触发链 bootstrap（最重发现）
- 缺口本质：后端闭环已齐（I01 聚合后落账 episode_resume.py:114-116+latest 翻转）；移动端唯一 I01 调用点（`episode_resume_provider.dart:104`）又以"latest 已是 resume_view"为前置门——鸡生蛋。
- **Bootstrap 机理**：服务端对 context_receipt_ref 只校验 scheme 不校验角色（`episode_resume_service.py:140-148`）→ 首条 I01 携带任一既有 `context_selection://` ref（当前实际只有 chat_context）成功聚合即产出首条 resume_view 回执 → U01 消费环自持。
- 推荐接线 W2（首卡 approve 成功→一次性 I01[taskId=新任务, ref=latest 回执]→invalidate contextReceiptProvider→latest 翻转→回 /home 接续条浮现）——字面命中验收②。
- 契约硬约束：复用 `episodeResumeTask`+`EpisodeResumeViewData.tryParse` 抽共享 fetch（禁平行解析器）；零新端点零 proto；**不放松 U01 角色门**（provider :95 门与 `episode_resume_provider_test.dart:162` 反例原样保留——bootstrap 是独立一次性生产触发非门旁路）；B05§2 服务端已满足客户端不预造；mode off→无回执→接续条诚实缺席；404 跨用户不泄露（episode_resume.py:111-113）。
- 备选 W1（dashboard 一次性 bootstrap，每会话一次请求须 one-shot 诚实失败）/W3（modeling finish 后，任务未必已建过早不推荐）/W4（/tasks 次级入口，超 U06 modules 留后续卡）。

## 三、可复用测试资产（摘要）
Mobile：`dashboard_test_harness.dart`（791 行整屏泵制）、`episode_resume_provider_test.dart`（9 测含角色门反例）、`today_cockpit_resume_integration_test.dart`（7 测）、register 族（f539/o3/a5/first_run）、auth 身份隔离五件（n4_session_user_state_isolation 等）、persona_onboarding 族、first_action_card 族+u02 fixture、`dashboard_conversion_cards_visibility_test.dart`、E2E `j02_fastpath_journey_test.dart`（536/541 落点取证已内置）+`j02_driver_contract_test.dart`、F04 shell 29 测。
Backend：`test_episode_resume_api.py`（含 :232 latest 翻转）、`test_context_selection_receipt_wiring.py`、`test_episode_resume_view_contract.py`、记忆隔离三锚、首链路（j04_first_action_chain/action_proposals 幂等 receipt/first_action_edit_atomicity/learning_journey_api 跨用户 404）。

## 四、风险与边界
- U06×Q01：文件零冲突（Q01 verification 零写）；资源真实冲突（Q01 工作集 2.9G+CoreSimulator 6.4G+swap 95%）——**U06 等 Q01 闭后再占模拟器**；Q01 证据录修前落点行为，U06 diff 叙证须写明时序；runbook §3 R7+驱动断言回填属 U06 变更面同锁申报。
- U06×RF-06（slsjz 线只读）：核心文件族零直接重叠；两处擦边避让——①`task_execution_screen.dart:301`（firstTaskCompleted 挂点）保持只读；②确认反馈/receipt 可见面勿挂 `dashboard_screen.dart:1160` 高危区，沿 `today_cockpit_card.dart` 卡内组合模式；首卡语义以 SP main J-02 修后（含 FIX-540）为准不回退 RF-06 基线。
- stop_conditions 高危两条：①身份边界清除链（只清 guest 侧不伤真实数据，N-4 夹具举证）+反馈可溯源同一次服务端 receipt（本地拼装=假成功）；②资源被占/模拟器不可用→BLOCKED_EXPLICIT 附证据，不降级为纯 widget 蒙混 UI 真实验收。

## 起跑建议摘要
先复现注册腿落点冻结反例（J02 驱动现成）→改 guest_upgrade 两处落点→裁决落点回填 routes redirect+驱动断言→W2 接线（抽共享 fetch）→测试全走第三节夹具→两文件只读避让 RF-06。
