# WT324 · G-05 模拟器证据债清偿 — REPORT（三卡 DEFERRED 实证 + 问题清单）

- **Worker**: wt324（全舰队唯一 HEAVY 槽位）
- **基线**: main `1c5f2d8d`（已含 wt305 G-03 / wt306 J-03 / wt315 U-05 合入态）
- **Worktree**: `../Sparkle-sysrev/wt324-sim-evidence`（branch `wt324-sim-evidence`）；本卡交付=本报告 + `shots/`（零产品代码改动）
- **环境**: Medium_Phone_API_36.1 无头模拟器；debug APK（`flutter build apk --debug`，JDK17=`/opt/homebrew/opt/openjdk@17`，JDK25 会让 Kotlin 编译器 `JavaVersion.parse("25.0.2")` 崩——见附录 C）；后端三件（gateway:8080 / gRPC:50051 / FastAPI:8000 + db/redis/minio）全程宿主机在跑
- **账号**: `wt324a`（register 带 accepted_tos+accepted_privacy 走通，API 契约验证 PASS）；造数走真实后端 API（无 app 内 mock 路径）

## 一、HEAVY 门与熔断事件（如实记录）

- 开工门：swap free 1282.88M ≥1.2G、load 5.08<8 → 放行。
- **00:50 熔断触发**：swiftshader 软渲染下 qemu 685% CPU，load 16.18/13.95 持续 >12 → 按纪律杀模拟器。
- **处置**：以 `-gpu host` 重启（弃 swiftshader），qemu 降至 15-25%，load 回落 5-7，此后全程合规（每 10 分钟抽查，swap free 1005-1490M）。
- **建议**：后续模拟器卡一律 `-gpu host`；swiftshader 在本机必然触发熔断。

## 二、三卡证据矩阵（缺口项 → 截图 → 判定）

### A. wt305 · G-03 星图（报告 §5 场景序列）

| 缺口项 | 证据 | 判定 |
|---|---|---|
| 进图→工作视野聚焦（SPEC-J 自动聚焦推荐锚） | `G03_after_dismiss_modal.png`、`G03_empty_graph.png`：进图停留在全图概览，无可视聚焦动作/锚高亮 | **FAIL（未触发）**：fresh 用户（全部节点未点亮）进图无工作视野聚焦；wt305 守约「视口空→诚实无锚」或「目标世界模式跳过」可解释，但对新用户即「首眼无引导」，与卡面目标相悖 |
| 平移后锚随相机（真实手势） | 慢速拖拽（500ms/150px，<420px/s fling 阈值）前后对比：`G03_pan_before/after1/after2/dense_after/graphtab.png`：相机确实平移（扇区标签「图论」入画），但视口内节点上**无可辨识的锚点亮/高亮变化** | **UNVERIFIABLE（机制不可视）**：widget 测试已证 `debugSpotlightAnchorId` 会随拖拽重定锚，但真机锁定态节点上锚定视觉不可感知——机制落地≠用户可感知，判 UX 缺口 |
| 点节点→面板首帧身份 | `G03_zoomin_1.png`：点按后预览卡即时出现（节点名「真题演练与错因回看」+已锁定+聚焦/连接/详情按钮，无空转 spinner）；`G03_sheet_loaded.png`：查看详情→详情页首屏即含节点名/扇区/掌握度 | **PASS**（wt305-c「详情触达减一跳」落地有效；加载期 _SheetHeader 未单独捕获——直达详情页未出现可分辨的 loading 中间帧，视为通过） |
| 弱网加载形态 | 未执行（模拟器弱网注入未纳入本轮；断网硬态已覆盖状态面） | **SKIP（如实记录）** |
| 空图/断网状态面 | `G03_offline_status.png`：飞行模式下顶部「你已离线，部分功能可能不可用」横幅 + 缓存图谱正常渲染 + 重进不崩 | **PASS**（诚实离线态；未见 LoadFailed/UsingCache 文案分支——缓存命中路径） |
| 新用户首眼能解释星图？ | `G03_empty_graph.png`：314 节点/尚未点亮/尚未开始 + 「开始你的第一次学习」「还没有点亮掌握记录」引导卡可解释；**但**图谱本体是全局共享知识图谱（DB `knowledge_nodes` 无 owner，两账号返回完全相同的 314 节点已复核），且新用户被一条「我们从 OS.pdf 里找到了 5 颗知识星」弹窗迎接（见 F1） | **PARTIAL**：引导文案可解释；「别人文档的知识星弹窗」+「全局图谱」让首眼归属感成疑（Persona 走查见 §三） |

### B. wt306 · J-03 Today Cockpit（四态/唯一 CTA/真实数据路径）

| 缺口项 | 证据 | 判定 |
|---|---|---|
| no-goal 态 | `J03_state_nogoal_top.png`：eyebrow「现在的指挥台」+「先定下你的第一个目标」+ 主 CTA「和 AI 定目标」+ ghost「我卡住了」+ 5 目标起点 pills | **PASS** |
| fresh 态（真实数据：goal+4 任务 0 完成） | `J03_relaunch_check.png`：headline=具体任务标题「Readiness check」、chip「期末操作系统冲刺 0/4」、CTA「先做这个」 | **PASS（带口径偏差 F-9）**：实现 fresh+nextAction→「先做这个」，wt306 报告口径为 fresh→「安排今天」，二者不一致（代码行为自洽，报告文档需更新） |
| stalled 态（真实数据） | `J03_state_stalled.png`：eyebrow「先解决卡点!」+「卡点在『Readiness check』」+ 主 CTA「解开卡点」+ 次级退化为「查看任务」 | **PASS（带 F-5 卡点误报）**：完成 Readiness check 后瓶颈引擎反而将其命名为卡点——后端误报路径实证（wt306 风险4 成真） |
| active 态 | 完成任务后 cockpit 被 stalled 覆盖（后端瓶颈即时命中），未取得 tasksCompleted>0 且无卡点信号的干净 active 截图 | **FAIL（后端信号干扰，非 app 缺陷）**：与 F-5 同源，待瓶颈误报修复后补证 |
| 首屏唯一 primary CTA | 组件语义层面 widget 测试锁定 + 实测 cockpit 卡内唯一主 CTA 各态均正确切换；**但** `J03_state_nogoal_top.png` 同屏 J-02「完成引导，让 AI 更懂你」卡的「继续引导」为同视觉重量深棕填充大按钮 → 第一眼双填充按钮竞争 | **PARTIAL**（语义唯一 PASS、视觉竞争 FAIL→F-8） |
| stalled 跳转链（chat 携真实 context） | `J03_stuck_jump_chat.png`：点「解开卡点」/瓶颈 prompt 卡 → chat 自动发送「我想换个方式理解Readiness check。请结合这个卡点，帮我调整接下来的学习路径。」；`J03_stuck_recovery_journey.png`：回复后落 J-05 恢复旅程卡（Aurora 正在适应三选项） | **PASS（带 F-6 chat_mode 失效）**：prompt 预填+发送 ✓、恢复旅程闭环 ✓；但 `chat_mode=growth` 被前端静默丢弃（见 F-6），落地为「均衡·标准对话·未绑定计划」 |
| 次要卡默认折叠 | `J03_collapsed_slots.png`：今日简报/多目标看板/考试冲刺/任务面板/动态/工作区卡片全部 64px 折叠头，点开可达 | **PASS** |

### C. wt315 · U-05 三屏 L2

| 缺口项 | 证据 | 判定 |
|---|---|---|
| 首页行动脊柱（唯一 Primary Action，8 次要卡收敛） | `J03_state_nogoal_top.png`+`U05_home_spine_middle.png`：CompactStatusBar→AuroraStatusBand→TodayCockpitCard（唯一主 CTA）→GoalSwitcherBand→DailyContextLine→（瓶颈时）_AttentionSlot→UnderstandingSnapshotCard 顺次实证；重复渲染的双份卡已消失，次要卡仅存折叠槽 | **PASS** |
| 三屏 5 秒测试（人工走查） | 首页 PASS（见上）；Goal 屏不可达（F-7）；Chat 屏见下行 | **PARTIAL** |
| Goal 里程碑条带 _MilestoneStrip + 重新规划/我卡住了恢复动作 | `U05_goal_detail.png`：多目标看板→目标卡→**目标详情加载失败**（404，重试不复权）；重启 app 复现相同 | **FAIL（F-7 blocker 性质）**：current_goal_id 被写入 plan_id，Goal 屏从主入口不可达——该验收项连同「重新规划」端到端一并被阻断 |
| Chat proposal/source/receipt 三件套 | `U05_chat_bottleneck_reply.png`：来源摘要（source 折叠条）✓、确认事实 receipt（45/60/30 分钟）✓、ContextReceiptBar 在场；ActionCard（proposal）本轮未触发 | **PARTIAL** |
| 真机长建议结构化渲染（编号/项目符号/代码块回退三态） | 第一次长编号列表回复渲染即崩（F-1? 见 F-4）；第二次 720 字含标题+项目符号回复以**普通 markdown**渲染（`U05_chat_markdown_long_reply.png`），未呈现序号徽标条目行；代码块回退态未及测试 | **FAIL（F-4 blocker + 正面实证缺失）** |
| 「我卡住了」同款约定（Goal 屏） | Goal 屏不可达（F-7） | **BLOCKED** |

## 三、5-Persona 第一眼走查（基于上表截图，非临床）

1. **小 A（期末冲刺，任务驱动）**：cockpit「先做这个/Readiness check/距截止118天」一眼可执行 PASS；但同屏「继续引导」大按钮构成第二行动焦点。
2. **小 B（迷茫新手，无目标）**：「和 AI 定目标」+5 pills 清晰；进入星图后被「OS.pdf 知识星」弹窗与 314 颗陌生星体击穿归属感（F-1/F-3）。
3. **小 C（卡点焦虑型）**：stalled 态「先解决卡点」+「解开卡点」共情到位；但「卡点在『Readiness check』」指向自己刚完成的任务会引发困惑→怀疑数据（F-5）。
4. **小 D（回顾型，重细节）**：goal 卡「100%」vs cockpit「0/1」vs 任务「1/4」三处口径打架，信任受损（F-9）。
5. **小 E（多任务老手）**：折叠槽收敛干净、lean 可达 PASS；DailyContextLine「Timedpracticeloop」缺空格（文案拼接，F-10 minor）。

## 四、问题清单（只记录不修；分级=blocker/major/minor）

| # | 级别 | 摘要 | 证据/根因 | 建议归属 |
|---|---|---|---|---|
| F-1 | **major（debug-only）** | 星图草稿弹窗 mock 回落：后端已正确返回 `{"drafts":[]}`，debug 构建仍渲染硬编码「OS.pdf 5 颗知识星」+「1 份待审核·5 颗星」常驻徽标 | `mobile/lib/features/galaxy/data/repositories/galaxy_draft_repository.dart:26-33`——空结果与 DioException 都在 `kDebugMode` 下走 `_buildMockBatches()`；截图 `G03_empty_graph.png` | galaxy owner；建议 release 分支删除该分支或改为仅显式 DEMO_MODE |
| F-2 | major | 节点标题/描述泄漏内部命名：「TOUR 专题7-d91d5df0-10-5dc70d: 真题演练与错因回看」直接呈现给用户（详情页大标题、描述、关键词三处） | `G03_sheet_loaded.png`；源为后端任务→知识节点 seed 命名 | backend seed 清洗 + 展示层截断 |
| F-3 | major | fresh 用户进图无 SPEC-J 工作视野聚焦；平移后锚定视觉不可感知（机制在 widget 层已证） | §二.A 前两行截图序列 | G-05 复议：锚定/聚焦在「全部锁定」初始态的产品语义 |
| F-4 | **blocker** | chat 长建议回复渲染崩溃：首次长编号列表回复即触发错误页「哎呀，出错了」`'_elements.contains(element)': is not true`（framework.dart:2168，GlobalKey reparent 冲突形态）；错误边界兜住未杀进程，但该条回复内容丢失 | logcat 摘要见附录 B；`structured_suggestion_body.dart` 本身无 GlobalKey（归属需隔离复现：新组件改变了该消息子树形态，碰撞或在消息列表 key 层） | U-05/chat owner 优先排查；复现 prompt：请 AI 输出>500 字符编号列表 |
| F-5 | major（backend） | 瓶颈误报：完成任务「Readiness check」后 active_bottleneck 立即把它命名为卡点，cockpit 直接转 stalled，掩盖 active 态 | `J03_state_stalled.png` + 任务完成回执（同任务 status COMPLETED）；wt306 风险4 预警成真 | backend growth dashboard 瓶颈推导 |
| F-6 | major | `chat_mode=growth` 全链路无效：`ChatMode.fromApiValue('growth')` 无此值（standard/deep_analysis/study_plan/error_diagnosis/expert_auto/team/expert），orElse 静默回落 standard；三处调用（today_cockpit_card.dart:316、dashboard_screen.dart:379、routes.dart:348 透传）形同虚设，落地「均衡·标准对话·未绑定计划」 | `J03_stuck_jump_chat.png` 底部 mode 条 + 附录 A 代码路径 | chat owner 定义 growth apiValue 或调用侧改用既有 mode；属继承自 dashboard 的存量约定债，J-03 只是照抄 |
| F-7 | **major（阻断验收）** | 多目标看板→目标详情 404：后端 `current_goal_id` 存的是 **plan_id**（ef026203…）而非 goal_id（45a0807b…），app 以其请求 `/experience/goal-detail/{id}` → 404，错误页「目标详情加载失败」重试不复权，重启 app 亦复现；U-05 Goal 屏全部验收项被阻断 | logcat `⛔ Error: 404 …/experience/goal-detail/ef026203-…` + 同日志 settings 返回 `current_goal_id: ef026203-…`；`U05_goal_detail.png` | backend 目标创建/激活链（creation_wizard 落 current_goal_id 时错拿 plan id）；app 侧错误文案可加 404 分支提示 |
| F-8 | minor→major 之间 | 首屏视觉双主 CTA：cockpit「和 AI 定目标」与 J-02「继续引导」同为深棕填充全宽按钮，语义唯一性测试管不住视觉竞争 | `J03_state_nogoal_top.png` | U-01 装饰档位/G-05 一致性：J-02 卡降级为 tonal/ghost |
| F-9 | minor（数据口径） | 进度口径三处打架：多目标看板「100%」vs cockpit chip「0/1」vs 任务面板「完成 0/1」（而任务真相 1/4）；另 cockpit chip 在 1/4 与 0/1 间漂移 | `J03_state_stalled.png` vs 多目标看板截图（对话记录于会话）vs `J03_collapsed_slots.png` | home 各卡真源对齐（wt306 B-02 lineage 延伸） |
| F-10 | minor | DailyContextLine 文案拼接缺空格：「先完成 Timedpracticeloop 打破昨日零记录」 | `U05_home_spine_middle.png` | home 文案模板加空格/走 l10n |
| F-11 | minor | 任务列表「部分数据刷新失败」横幅（transient，与 token 过期窗口重合，同 F-7 根因家族） | 任务列表截图（会话内） | auth 刷新拦截器覆盖面 |

## 五、收工与纪律

- [ ] 杀模拟器、删 `mobile/build`/`.dart_tool`、清 `/tmp/wt324_*`（收工清单执行中）
- [ ] `run_all_rule_guards.sh` exit 0（本卡零代码改动，gen 拷贝为主仓只读解引用）
- [ ] 报告+截图 commit 进分支；`git diff --binary main...HEAD > changes.patch`

## 附录 A：F-6 代码路径

```
today_cockpit_card.dart:316  'chat_mode': 'growth'   （_openStuckChat）
dashboard_screen.dart:379    'chat_mode': 'growth'   （_openBottleneckChat 存量）
app/routes.dart:348          initialChatMode: queryParameters['chat_mode']
chat_screen.dart:1073        setFromApiValue(initialMode)
chat_mode.dart:71            firstWhere(apiValue=='growth', orElse: ChatModeStandard.new)  ← 静默回落
```

## 附录 B：F-4 logcat 摘要（00:01:51 与 00:02:54 两次）

```
event_type: crash, severity: critical, context: flutter_error
error: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 2168
       pos 12: '_elements.contains(element)': is not true.
#2 _InactiveElements.remove (framework.dart:2168)
#3 Element._retakeInactiveElement (framework.dart:4532)
#4 Element.inflateWidget (framework.dart:4572)
#5-#11 SingleChildRenderObjectElement.mount / updateChild 链
#12-#24 ComponentElement.performRebuild / StatefulElement.update / ProxyElement.update
```

## 附录 C：环境修复记录（非产品改动）

1. worktree 缺 gitignored gen 产物 → 主仓只读 `cp -RL`（mobile/lib/gen、backend/app/gen、backend/gateway/gen）。
2. JDK25 构建失败（`What went wrong: 25.0.2` = Kotlin `JavaVersion.parse` 不识别）→ `JAVA_HOME=/opt/homebrew/opt/openjdk@17/...`，构建 92.4s 通过。
3. swiftshader 熔断 → `-gpu host` 重启，后端账号 wt324a 登录态保留（userdata 分区）。
