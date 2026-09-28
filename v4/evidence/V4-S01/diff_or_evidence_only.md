# V4-S01 — diff_or_evidence_only

## 结论一句话

语义乐谱的四个动效面按「既有已满足面差量举证 + 缺失面最小增量落地」完成：按压面把 SparklePressable 的 100ms 字面量对齐乐谱 80ms 并补 reduce-motion 静态分支；提案出现/回执替换/证据印章三行乐谱此前无任何实现，新增 `core/design/semantic_motion.dart`（乐谱→机器预算表，motion-policy 锁面唯一权威，带窗口校验）与 `semantic_motion_widgets.dart`（全 implicit 一次性动画组件族，同 key 重投不重播、取消无成功载体、零粒子零声触）；23 个新测试每验收面一正一反 + 控制组探针活性，`flutter analyze` 零 issue，design 域 237/237；降低动态等价以「动画落定终态 vs 静态分支原始 RGBA 逐字节相等（PNG 字节级同哈希）+ 语义 label 逐字相等」落证。

## 差量明细（相对 base d57a7aa8 = 开卡时 main HEAD）

产品码（2 新 + 1 改；RF-06 冲突面三文件、`app/routes.dart`、backend/、proto/、tokens_v2、gen 产物零触碰）：

- `mobile/lib/core/design/semantic_motion.dart`（新，+121/−0）—
  **语义乐谱预算表（motion-policy 唯一权威）**：五行乐谱 → 五槽预算
  （press 80ms / proposalEnter 200ms∈[160,220] / receiptReplace 160ms /
  evidenceStamp 160ms / milestone 650ms≤650），窗口表逐行引用
  MOTION_AUDIO_HAPTICS.md 原文；`validateAgainstScore()` 任何偏离窗口的
  预算改动具名显形（「预算可测」的机器面）。口径协调不另立：reduce-motion
  判定指向 F06 MediaQuery 双源口径；低刺激令牌收缩仍归 U02
  `resolveSparkleMotionTokens`（正交）；成功声/触归 F03 适配器（doc 注记）。
  里程碑 650ms 与 PixelSuccessBadge 既有 `milestoneMax ?? 650ms` 同源（F06 已落）。
- `mobile/lib/core/design/widgets/semantic_motion_widgets.dart`（新，+175/−0）—
  三个缺失乐谱行的组件实现：`SparkleProposalEnter`（提案出现：200ms 纸面
  抬起 10dp+淡入，一次性 implicit，无完成回调——取消即卸载，不残留在航态）、
  `SparkleReceiptSwap`（回执替换：replacementKey 锚定（建议=event_id），key
  变化播一次 160ms 淡入；**同 key 重投（恢复重放）不重播**；首挂载不播
  （初始内容非回执）；取消/错误内容 = 普通替换、树中无成功徽章载体）、
  `SparkleEvidenceStamp`（证据印章：160ms 1.12→1.00 压印+淡入，零粒子零声
  触，文字不说已掌握）。族纪律：全 implicit（源码棘轮测试禁
  repeat/AnimationController）、reduce-motion 静态分支（不装动画壳直落
  终态，不通配 Duration.zero）、预算只取权威表。
- `mobile/lib/core/design/components/atoms/sparkle_pressable.dart`（改，+54/−43）—
  按压面对齐：100ms 字面量 → `kSparkleSemanticMotionBudgets.press`（80ms，
  乐谱「80ms轻压」）；新增 reduce-motion 静态分支——减弱动效不装
  AnimatedScale 壳（按压反馈由 InkWell highlight 即时承载，即时状态不是
  动画，等价信息不丢失）；结构重组为先建 material 再选壳，非 reduce-motion
  路径行为仅节奏 100→80ms 一处变化（scale 0.97/曲线/回调链逐字节等价）。

测试（2 新文件，23 用例；每验收面一正一反 + 控制组探针活性）：

- `test/core/design/semantic_motion_s01_test.dart`（22）— A± 预算窗口校验
  （默认零违例 / 变异预算具名判负×3）；B±/B- 按压 80ms 在航可测（40ms 处
  scale∈(0.97,1.0)）+ 静态分支无动画壳仍可点 + 常规壳在场控制组；C±/C-
  提案 enter 首帧 0→在航→落定 + 静态分支首帧完整零壳零 ticker + 常规首帧
  <1 控制组；D+×4 回执（首挂载不播/key 变化播一次/同 key 重投下一帧即
  终态/取消无成功载体/静态即时替换）；E±/E- 印章在航→全尺寸落定零粒子 +
  静态分支 + 控制组；F+×2/F- settle 后零 ticker（追加三帧仍 0）+ repeat
  探针判 ≥1 + 新表面源码棘轮；G+/G- 60 行语义族列表滚帧 18711us<70000us
  且 settle 后零 ticker + repeat 行控制组；H+/H- 动画 57.4us vs 静态基线
  28.4us 同批对照双<门 + 基线零 ticker 控制组。
- `test/core/design/semantic_motion_s01_evidence_test.dart`（1）— 证据采集
  （env 门控落盘，常规跑零副作用恒执行真实断言）：动画落定终态与
  reduce-motion 静态分支**原始 RGBA 逐字节相等**机器断言（降低动态=等价
  信息不丢失的像素级证据）+ 两变体三 label 语义逐字相等；落盘 PNG×2
  （两文件 sha256 相同：a37b9544…）+ 语义 txt。

## 验收逐条自证（卡面原文 → 机器证据）

1. **「无后台无限动画和全屏粒子」** — F+：S01 全部新面（组件族+按压面）
   pumpAndSettle 后 `transientCallbackCount == 0` 且追加 3 空转帧仍 0；
   `GlobalParticleCounter.currentCount == 0`（新面零粒子占用）；源码棘轮：
   两新文件剥注释后禁 `.repeat(` 与 `AnimationController`。反方向：F-
   repeat 探针同法判 ≥1、B-/C-/E-/G- 控制组证明各断言非恒真。既有 48 文件
   repeat 清点与清尾归 U15「长尾家族清点」（卡面任务分工），本卡不冒充
   全 app 达成（limitations #1 有完整清单口径）。
2. **「cancel/replay不重播成功；enter/state/milestone预算可测」** —
   预算可测：A+ 默认预算逐槽过 `validateAgainstScore`（enter 200∈[160,220]、
   state/stamp=160、press=80、milestone=650≤650，与 PixelSuccessBadge 既有
   650ms 同源）；A- 变异预算（200/300/900）具名判负×3。replay：D+ 同 key
   重投（恢复重放场景）下一帧即终态、动画不重启；cancel：D+ 换取消内容 =
   普通替换、`PixelSuccessBadge` findsNothing、零残留 ticker。声/触面的
   成功去重（E1 门 + event_id 抑制）已在 F03 适配器落地并有既有套件
   （test/core/experience/ 2 文件全绿），本卡为运动面补充、未重复造轮子。
3. **「profile下帧时间与baseline对照」** — H+：同一 harness 逐帧墙钟，
   动画路 avg 57.4us/帧 vs reduce-motion 静态基线 avg 28.4us/帧（末次运行
   实录；三次运行区间 51–59us / 27–31us），双 < 33334us 门（env
   S01_FRAME_US 可放宽、门不删）；G+ 滚动含语义族 60 行列表 avg
   18711us < 70000us 且 settle 后零 ticker（**不给滚动正文降帧**：入场一次
   性动画落定后正文不再被本面锁帧）。口径边界：flutter test 无真帧调度，
   本对照为测试环境 CPU 代理；真机 profile 模式帧统计 → NOT_RUN（无设备，
   limitations #2）。

## 红线自证（diff 逐面）

- **RF-06 冲突面零触碰**：`git diff d57a7aa8 --name-only` = 3 产品码 +
  2 测试（全为新面/DS 层）；dashboard_screen / compact_status_bar /
  task_execution_screen 零命中；backend/、proto/、迁移、gen/ 零命中。
- **l10n 零触碰**：本卡无文案面（组件族无文字）；pub get 引发的 l10n
  再生成漂移已 `git checkout` 还原，arb/生成物零 diff。
- **不另立第二权威**：预算表是 motion-policy 唯一权威且唯一消费点为
  SparklePressable 与组件族；reduce-motion 判定全走 `context.reduceMotion`
  （F06 口径），零 `platformDispatcher` 直读新增；粒子预算继续走既有
  GlobalParticleCounter（新面零占用）；成功声/触继续走 F03 出口。
- **降低动态=等价信息不丢失**：RGBA 逐字节相等 + 语义 label 逐字相等
  （证据测试恒执行，非仅落盘模式）。
- **classic 零差量声明**：本卡零新增像素组件调用点；SparklePressable 属
  classic/像素档共用 DS 原子，节奏 100→80ms 与静态分支为两侧同益面。

## 复跑清单（全绿实录见 run_manifest.json / test_results.json）

`flutter analyze --no-pub`（No issues found!）；新套 23/23；
`flutter test test/core/design/` 237/237；消费面 5 套 56/56；
`flutter test test/performance/` 19/19（首试 1 败为墙钟 bench 环境抖动，
复跑全绿，bench 面不含本卡文件）；home 域 106/106。
