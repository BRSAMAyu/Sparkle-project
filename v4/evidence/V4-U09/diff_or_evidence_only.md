# V4-U09 差量与证据说明（diff_or_evidence_only）

## 0. 一句话设计

专注（正念）页保持「当前动作 + 计时 + 退出」三要素不动摇：结算只认实测时长
（估时仅作结果面注脚，U08 actualMinutes 同口径）；中断/失败路径零伪造——
中断不写记录、保存失败不出庆祝面；结束动线把强制长反思（≥5 分钟强制弹
必填复盘框）替换为「记录成果 / 跳过」双一等路径；背景声只接 U14
ambient_enabled 偏好状态（暂停如实暂停、恢复偏好门控），不做新音频机制。

## 1. 行为差量（相对 main@4152266c）

### 验收1：中断计时不假保存；估计和实际分开
- `mindfulness_provider.dart`：`stop()` 新增**重复结算守卫**——结算窗口
  （`isLoggingSession`）内重入直接返回空结果，不产生第二条保存记录
  （弹层确认与返回键并发、双击退出、重开恢复后重复 stop 都不双结算）。
  结算成功 state 整体清空、失败 `isLoggingSession` 复位，正常重试不受影响。
- 中断语义既有行为以测试钉死（正+反）：切后台记录中断事件、杀进程
  **不写任何专注记录**（中断=如实中断）；重开恢复同一会话（`startTime`
  原样保留、实测按墙钟延续）；只有用户主动 stop 才结算，且 `durationMinutes`
  只来自 `elapsedSeconds`——90 分钟实测不会被任务估时 25 顶替
  （突变自证 M2：把估时塞回结算 → 验收1 正例必红）。
- 用户可见面：结束面主行=「实际专注 N 分钟」（实测），注脚=「计划 N 分钟」
  （估时对照），分列展示、绝不互相顶替。

### 验收2：切后台/重开不重置或重复结算
- 计时延续：切后台不重置（墙钟续算）、杀进程重开经 `_restoreSession`
  恢复同一 `startTime` 续算（面2 正例钉死 600s→≥600 且起点毫秒一致）。
- 不重复结算：新增守卫以并发双 `stop()` 钉死（面2 反例；突变自证 M1：
  摘除守卫 → 该测试必红，两次 saveSession）。
- 失败重试恰好一次写入（R2-03 恢复链延伸）：首次保存失败→快照保留→
  重开续结→重试成功→`successfulWrites == 1`（widget 测试覆盖完整
  「失败→重开→重试」生命周期场景）。

### 验收3：无声音动效仍完整可用，失败不显示庆祝
- **失败不庆祝（反例钉）**：`saveSession` 抛异常时——不进入成果面、不出
  现奖励摘要（专注完成/火苗/掌握度）、error snackbar 如实呈现、会话快照
  保留可恢复（R2-03）、intervention 的 `acted` 回执只在真实落库后上报
  （F03：无 committed 回执不触发成功面；基线在保存失败时也上报 acted，
  本卡修正）。突变自证 M3：砍掉失败分支 → 失败测试必红。
- **无声音动效完整可用（正例钉）**：`disableAnimations`（系统减动效）+
  提示音/背景声/场景全关下——专注页渲染、暂停/恢复、退出确认、结算、
  成果/跳过全链路可用；且 `transientCallbackCount == 0`（无任何持续动画：
  火苗走静态支、星空按 N33 口径静止——画面在、循环停）。
- 火苗动画新增减动效静态分支（`context.reduceMotion`，与星空 N33/S01
  同口径），移除唯一一处无视减动效的无限循环动画。
- **接可选声音状态**：会话暂停→`SensoryFeedbackService.pauseAmbient()`；
  恢复→仅当 `isAmbientEnabled()`（U14 独立开关）且场景非「无」时
  `resumeAmbient()`。只消费既有服务状态/API，零新音频机制；S02 音频
  焦点策略不在本卡范围（在航卡）。

### 验收4（objective）：结束可记录成果或跳过，不强制长反思
- 删除强制长反思：基线在 ≥5 分钟会话退出后强制弹 `ReflectionDialog`
  （`barrierDismissible: false` + 卡点字段**必填**才能保存）——已整体移除
  （`reflection_dialog.dart` 删除，唯一调用点替换）。
- 新增 `focus_session_outcome_sheet.dart`：实际分钟主行 + 估时注脚 +
  一句**可选**成果字段 + 「跳过」「记录成果」同权重按钮；
  `barrierDismissible: true`（点空白=跳过，机械上不存在不可关闭 trap）；
  留空点「记录」视同跳过（零输入可离开）；记录写入 Cognitive fragment
  （带溯源头：任务名 + 实测分钟 + 原文，`sourceType: reflection`）；
  记录失败如实报错、sheet 保持打开、跳过始终可用。反例钉：无必填字段、
  留空记录=零写入离开。

### 页面内容（objective）：只保留当前动作、计时、退出
- 正念模式屏既有结构已满足（任务卡=当前动作、翻页钟=计时、暂停+退出），
  本卡零增删主体区块；页面主体零改动（只动了退出动线/火苗动效/暂停的
  ambient 同步）。

### l10n
- `app_zh.arb` / `app_en.arb` 各 +6 键：`focusOutcomeActualMinutes`（含
  placeholders 元数据）、`focusOutcomePlanMinutes`、`focusOutcomeHint`、
  `focusOutcomeFieldLabel`、`focusOutcomeFieldHint`、`focusOutcomeRecord`。
  `flutter gen-l10n` 再生，零既有键改动（L10N-REGEN-PARITY 10195 键
  PASS）；被删组件的旧键按「纯增量」纪律保留未删。

## 2. 红线自检

- RF-06 三冲突面（dashboard_screen / compact_status_bar /
  task_execution_screen）：零 diff（`git status` 全量可查，本卡只触
  `features/focus/` 三个文件 + l10n + 新测试 + 证据）。
- 不造第二权威：结算仍走既有 `focusStatisticsProvider.saveSession` 单链；
  成果记录走既有 `cognitiveProvider.createFragment`；ambient 走既有
  `SensoryFeedbackService`——零新 repository/service/存储/音频机制。
- backend / proto / 迁移 / 路由：零触碰（无 OpenAPI/BA-ROUTES、无
  sync-db 义务；路由表未动——`/focus/mindfulness/:id` 既有路由原样）。
- 参考图未充当批准：无新视觉档，全部既有 DS 组件（GraphiteModalSurface/
  SparkleButton/TextField），UI 消费 core/design 令牌（无新裸色值/裸间距；
  SPACING-RHYTHM 与 UI-TOKENS 守卫 PASS）。
- 已知债务：未动统计模块/排行榜/`card_protocol/`。

## 3. 测试与突变自证

- 新增 11 测（provider 结算 5 + widget 结束动线 5 + 证据采集 1），每验收
  面一正一反；全 focus 套件 19 绿；mobile 全量 3087 passed / ~23 skipped
  （既有 flaky 豁免集）/ 0 failed。
- 突变三连（可失败性亲验，均 +N -1 必红后还原全绿）：
  - M1 摘除 `stop()` 重复结算守卫 → 面2 反例红；
  - M2 结算时长换回任务估时 → 面1 正例红；
  - M3 砍掉保存失败分支（失败也进成果面）→ 失败不庆祝钉红。

## 4. 已知限制与预登记挑战

见 `limitations.md` 与 `review_receipt.json`（6 条挑战点）。
