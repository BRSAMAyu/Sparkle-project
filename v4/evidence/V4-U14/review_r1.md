# V4-U14 · 一审 receipt（独立审查 wtU14R1）

- 审查对象：`agent/v4/u14` @ `7a16956e`（基线 `9b5e614d`，4 commits，审查起点工作树 clean）
- 审查者：wtU14R1（未参与 U14 实现）；宿主 darwin arm64，flutter 3.41.3 stable
- 方法：只读 + 亲跑测试 + 亲构造 probe（已删）+ 3 组 mutation（已还原）+ merge-tree 亲验
- **裁决：PASS_WITH_CHALLENGES**（放行；挑战项见 §7，不阻断，建议登记后续）

## 1. 预登记挑战逐项独立裁决

### R1-C1 背景声独立·向后兼容对照表 — PASS（亲构造复验）
临时 probe（4 例全绿，审查后已删）逐行验证升级对照表：
- sound=off + 已存 rain 场景、无 ambient 键 → `isAmbientEnabled()` 继承 **false** → `playAmbient` 门拒绝，静音（升级前基线门 `isSoundEnabled()` 同为 false，9b5e614d 版 line 451）→ 升级前后行为等价，**「老用户不被升级悄悄打开」成立**；
- sound=on + 无键 → 继承 true（行为不变）；
- 显式 ambient 键优先于继承（任一方向）；
- `setAmbientEnabled(false)` 停播且保留已存场景；`setAmbientEnabled(true)` 不自动续播（`currentScene` 保持 none，probe 亲证）。
代码锚：`sensory_feedback_service.dart:264-277`（继承）、`:496`（新门）。

### R1-C2 快路径不校验快照新鲜度 — PASS（接受实现方立场）
裁决依据：id 即对象身份；内容新鲜度归执行屏既有机制与任务域——`task_execution_screen.dart:168-178`（进场加载执行状态/模板）、`:213-228`（5s 轮询）；被远端改写/删除时首个服务端写动作显式报错（`:186-199` AppFeedback.error），离线写另有 TaskOfflineQueue 诚实入队语义（N35），**非静默假成功**。闸若自查会给应用内路径引入网络依赖并制造第二个任务新鲜度权威。已删深链的核心风险面（渲染错误任务/空白）由闸的 404/本地解析路径关闭（mutation 钉死，见 §3）。

### R1-C3 404 判定字符串耦合 — PASS（今日成立；附后续建议）
全链路亲核（非只看客户端）：
1. backend `app/api/v1/tasks.py:240` `NotFoundError(message="Task not found")`（英文，含 'not found'）；
2. `app/main.py:1089` SparkleException handler 将 message 放入响应体 `message` 字段；
3. 网关 `cmd/server/setup.go:1013` ReverseProxy 仅 Rewrite 头（XFF/XFH），**body 原样透传**；
4. 客户端 `task_repository.dart:296-313` `data['detail']`(null)→`data['message']`="Task not found"→`throw Exception(...)`；
5. `error_lexicon.dart:148` 模式 `'not found'` 命中 → `UiErrorCategory.notFound`。
脆弱点确认：`_handleDioError` 丢弃 HTTP 状态码，纯文本判定；若后端消息改为 NotFoundError 默认中文「没有找到相关内容」（无 'not found'）则落「暂时无法确认」面——**诚实保守侧，不误判已删除**，可接受。建议后续卡：客户端错误类型化携带 status（TypedUiError），消除文本嗅探（lexicon 条款既定方向）。

### R1-C4 「选中但置灰」pill 诚实性 — PASS（实现方方案更诚实）
pill 显示 `_ambientScene`（来自持久化 `getSavedAmbientScene()`），置灰（`onTap: _sensoryReady && _ambientEnabled`）表达当前不播。卡验收 1 要求「偏好重开保持」→ 持久化场景必须存活；若关闭时清除显示选中，UI 将与持久层不一致（重开后凭空恢复），反而更不诚实。probe row4 亲证：停用保留场景、重开不自动续播。

### R1-C5 全库 isSoundEnabled 漏改点 — PASS（亲 grep）
`grep -rn isSoundEnabled lib/`：定义（service:245）、ambient 继承（:268，有意）、emit 提示音门（:372，应保留）、设置屏读提示音开关（unified_settings_screen.dart:182）。**无第三处门控背景声**。背景声播放全量经 `playAmbient`（scene_audio_scope.dart:93、focus_timer_tool.dart:325/382/552），统一被 `isAmbientEnabled()` 门。

## 2. no_duplicate 差量抽查（2/4 项）
- **F05 主题 preview flag 门** ✓：`app_constants.dart:44 enableStylePreview = false` 默认门 + `style_preview_page.dart:45` 零差量返回 + profile 入口——确实已存在；本卡 diff 无任何 style_preview/profile 文件。EVIDENCE_ONLY 成立。
- **F06 减少动态叠加律** ✓：`app/app.dart:136-139` `composeDisableAnimations(system: mediaQuery.disableAnimations, inApp: accessibility.reduceMotion)` + 权威实现 `accessibility_provider.dart` + `accessibility_composition_test.dart` 4 例——确实已存在；本卡零触碰。EVIDENCE_ONLY 成立。

## 3. 深链闸 mutation 抽查（可证伪性亲证，均已还原）
| Mutation | 结果 |
|---|---|
| M1：404 case 改落 `_markUnreachable` | gate 测 **2 红**（「反·已删对象」+「已删面出口」）✓ |
| M2：快路径改走仓储 getTask | 快路径测 **红**（`getTaskCalls==0` 被破）✓ |
| M3：设置屏降级提示行 `if (false && _audioDegraded)` | 「反·降级位诚实提示行」**红** ✓ |

行为面核验：已删任务统一「内容已删除或不存在」面不空白（body/主动作/回首页出口四键断言）；出口 `go` 不入返回栈；可重试面语义 = lexicon `uiErrorMessage` 类别词条 + 重试回环（测试钉）；判定单源走 `error_lexicon.dart`（闸内零私有映射，亲读）。loading 中间态不预渲染任务。

## 4. 音频诚实降级与行为变更断言
- 诚实呈现：`sensory-audio-degraded-notice` 提示行 + 文案逐字断言（mutation M3 可红），非静默成功 ✓。
- 任务流不受影响：`emit` 全路径不向调用方抛（`_playSound` catch 吞 + unawaited）；降级位只门 `soundAllowed`（:372），haptic/视觉独立（专项测钉）✓。
- 阈值置位不逐事件重试：`_audioPlaybackFailureStreak >= 2` 置位（:757-764，catch 内唯一新增分支；L2 已如实披露故障注入面未测——机制面以 `debugSetAudioPlaybackDegraded` 驱动，代码路径非死代码，亲读确认）。
- 显式重试清位：`setSoundEnabled(true)` 清降级位（service :309-315 + 测）✓。
- 「关提示音不连带停背景声」行为变更：偏好级正反测钉（关提示音背景声偏好不动 / 反演对称）；运行时停止行为的变更 = diff 删除行（基线 `_setSoundEnabled(false)` 含 `_ambientPlayer?.stop()`+`_currentScene=none`，head 已无），单测环境 AudioPlayer 通道不可观测——与 L1/L5 披露一致，如实 ✓。

## 5. 测试质量与数字
- **新测实数 21（9+3+2+5+2），证据自报 19 为簿记错误**：test_results.json 自列 breakdown 求和即 21；「19=9+3+7」口径将 gate(5)+settings(2) 合并为 7。少报非夸大，本 receipt 以 **21** 为准（erratum）。
- 21 例亲跑全绿（测试强制 `Locale('zh')`，中文逐字断言有效；`i18n_test_helper.dart:14`）。
- 受影响域批亲跑：sensory/settings/lexicon 批 +49 绿；全量两轮见下。
- **全量亲跑两轮**：轮1（含审查 probe，-2）；轮2 净树 `flutter test` → **+2967 passed, ~23 skipped, -3**，3 败全在 `test/performance/widget_bench_test.dart`（构建<16ms / 重建<5ms / 100 项滚动 60fps 计时基线）；该文件单跑 **+9 全绿** → 全量并发下机器负载型 flaky，与 U14 触碰面（settings/gate/l10n）无关。2967+3=**2970** 与证据 claimed 2970/23 精确吻合 → **分母核实**。
- arb：diff 恰 +9 新键 + `sensorySoundSubtitle` 文案订正（均与声明一致）+ 1 处纯格式尾逗号（learningSourceCompactLabel）；**零删键**；`flutter gen-l10n` 再生后 `git status mobile/lib/l10n/` 零 diff → **零漂移亲证**。

## 6. 合并落差（main 已前进至 dc991183，领先 41 commits）
- `git merge-tree HEAD main`：冲突恰 5 个 l10n 文件（app_zh.arb / app_en.arb / 3 生成文件）——与 L9 预告的「arb 并集 + gen-l10n 再生 ×3」机械解一致；`v4/04_tasks/tasks.json` 本轮自动合并（无冲突）。
- **RF-06 三文件零触碰亲核**：merge 输出 grep dashboard_screen / compact_status_bar / task_execution_screen 零出现；且 `git diff 9b5e614d..main` 对 U14 任一代码触碰文件（sensory service / settings screen / task_routes / voice provider / pubspec）均为空 → 双向无交集。

## 7. 挑战（非阻断，建议登记后续卡/台账）
- **CH-1 路由接线无测试钉**：`task_routes.dart` 改经闸无任何自动化锚定（full_route_coverage_test.dart:234 只查路径存在；gate 测试直泵 widget 不走路由）。若集成合并还原接线，无测试变红。建议：补一例路由级断言（route.pageBuilder 产物含 gate）。
- **CH-2 playAmbient 状态残留（先于本卡的潜在缺陷，release-only）**：`playAmbient` 在 ambient 门**之前**写 `_currentScene = scene`（service :489 vs 门 :496）：player 非空且开关关闭时，被拒调用留下 currentScene=场景但未播；`setAmbientEnabled(true)` 不复位 → 用户显式重选**同场景**被 `scene == _currentScene` 早退吞掉（设置 pill `autoplay:true` 路径亲核）。**基线同构**（基线门 `isSoundEnabled` 位于同一位置，同残留学生），非本卡引入；debug 构造 probe 无法复现，因 `_ambientPlayer` 仅由 `_playSound` 懒初始化（`init()` 全库无生产调用点；debug 走 SystemSound 早退不触发）→ 生产 release（播放过任一提示音后）可达。建议后续卡：门拒绝时回滚 `_currentScene = previousScene`。
- **CH-3 证据簿记**：新测计数 19→实 21（§5 定案）；`run_manifest.json` 的 `artifacts_sha256.limitations.md`（ca0f17…）未随 `7a16956e` 追加 L9 后刷新（现为 8da8b3…；2e3aaea8 时点哈希核对一致，L9 提交信息已自述增量——非伪造，哈希锚失同步而已）。
- **CH-4 轻微**：降级恢复路径仅「提示音开关 off→on 往返」（无专用重试控件，诚实提示行已足额）；auth 类异常并入 offline 可重试面（L4 已披露，其「不建第二认证权威」论证成立，接受）。

## 8. 验收对照（卡 acceptance 三条）
1. 「偏好重开保持；系统减少动态具有约束力」→ 重开保持测 + probe row4；F06 叠加律 EVIDENCE_ONLY 亲验（§2）✓
2. 「录音/声音权限拒绝只降该能力不堵目标」→ voice 3 测（授权/本次拒绝/永久拒绝+reset）+ 既有权限引导对话亲验（voice_input_button.dart:103/116）；音频诚实降级不堵任务流（§4）✓
3. 「通知落真实对象，已删对象提示而非空白」→ 任务深链族主导航目标亲核（push_navigation_service.dart:97/184/229、notification_service.dart:422 均落 `/tasks/:id/execute`）→ 闸解析落真实对象；404 确证已删面 mutation 钉死 ✓

## 9. 结论
**PASS_WITH_CHALLENGES**。四验收面全部成立，mutation 可证伪，分母与合并落差亲验吻合，限制披露（L1-L9）如实。CH-1/CH-2 建议立后续卡；CH-3 erratum 以本 receipt 为准（新测 21）。S02/S03→Q06 链解锁键放行，按验收模型走独立审查 + 集成 SHA 可失败测试流程。

审查者模型：GLM（account:bigmodel-individual-coding-plan / GLM-5.3-Flash）｜临时探针与 mutation 均已还原/删除，receipt 提交后分支仅余本审查增量。
