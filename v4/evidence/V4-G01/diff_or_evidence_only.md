# V4-G01 — diff_or_evidence_only

## 结论一句话

首页/目标/任务/日历家族（home/goal/task/plan/calendar）按「F05 判例确定性面走查 → 就地修 → 每风格 golden+语义钉+状态面」完成四风格商业化打磨：走查实修 13 处风格面缺陷（前任 10 + 续跑 3），家族五模块 `Color(0x…)` 字面量清零、内容面 `Colors.*` 字面量仅剩 4 处登记不修（lerp 派生基料，修则破坏 classic 发布面零差量）+ 7 处范围外（visual_elements 装饰层，非家族触达面）；对比度四风格 15 对逐对复算 ≥4.5:1、大字/图形线 ≥3:1；200% 文本零溢出（task_card 元数据 Row+Spacer→Expanded(Wrap) 判例）；reduce-motion 等价按 S01 双源判例落地三面（SparkleConfetti/post_exam_review 内联覆盖层新钉 E±）；22 个 G01 测试（20 前任 + 2 续跑）每面带控制组探针；四风格确定性 golden 8 张零漂移（续跑修复为输出字节等值令牌化，golden 无需重签）；analyze 零 issue；家族模块 + core/design 回归全绿；repeat 棘轮 48→48 只降不升；RF-06 三高危文件零触碰。

## 走查缺陷清单（四风格 × 逐面；✅=已修 / 📋=登记不修 / ⛔=范围外）

### A. 前任已修（本卡 dirty 继承，10 处缺陷 / 8 文件）

| # | 面 | 风格缺陷（走查实证） | 修复 |
|---|---|---|---|
| A1 | plan/learning_portfolio_screen | **15 枚屏私有 classic-only 字面量**（`_portfolio*` 自然系色板）：dusk 深底下面板仍钉浅色纸、quiet/paperDay 脱档 | 全部收敛 DS 令牌派生（success/warning/info 6% 淡彩叠 surfaceSecondary、borderSubtle、textPrimary、successAccent 药丸、warning chip），四档同语义自适应，零字面量残留 |
| A2 | plan/post_exam_review_screen | 六枚 classic-only 高饱和纸屑字面量（7C3AED/0EA5E9/F59E0B/10B981/EC4899/6366F1）+ `Colors.black@8%` 面纱 | 六槽 task 角色色（唯一令牌真源）+ DS.neutral900 派生面纱，四档自适应 |
| A3 | plan/post_exam_review_screen | reduce-motion 下两段隐式动画照播（违反 S01 判例） | `context.reduceMotion` 双源判定，纸屑/卡片 scale 直落静止终态（settled=1），不制造动画帧；常规路径逐字节等价 |
| A4 | plan/learning_path_progress_bar | 目标节点星标钉 `Colors.white@90%`：quiet/paperDay 浅彩段与 dusk 亮 accent 段 <3:1 | `DS.onColor` 按节点色自动取对侧墨，四档任意 reveal 段 ≥3:1 图形线 |
| A5 | task/task_card | 顶部高光 sheen 钉 `Colors.white` 字面量 | `context.colors.rimLight` 高光槽（浅档/深档派生），零字面量 |
| A6 | task/task_card | **200% 文本横向溢出 25px**（classic 实证）：元数据行 Row+Spacer 大字阶溢出 | Expanded(Wrap)：100% 排布不变（左组贴左、日期贴右），200% 换行展开不截断不溢出（sweep 测 200% × 四档零溢出钉） |
| A7 | task/task_feedback_dialog | 连续里程碑卡 classic-only 橙系字面量（FFF3E0/FFE0B2/FFB74D/FF7043/8D4E1D）：dusk 深底下刺眼、quiet/paperDay 脱档 | semanticWarning 派生（12%/20% 淡彩渐变 + 45% 描边 + textPrimary 字），四档自适应 |
| A8 | task/task_detail_screen | accent 渐变容器图标钉 `Colors.white`：dusk 亮 accent 上 <3:1 | `colorScheme.onPrimary` 唯一槽（对比度安全墨装配），四档自适应 |
| A9 | goal/goal_created_dialog | accent 渐变圆图标钉 `Colors.white`：dusk 亮 accent 上 <3:1（同 A8 判例） | `colorScheme.onPrimary` 唯一槽 |
| A10 | core-design/sparkle_confetti | reduce-motion 下 ConfettiWidget 照常挂载播粒（违反 S01 判例） | 静态分支：减弱动效视觉层整体缺席（静止终态=粒子已落出屏）；控制器生命周期/粒子预算记账/感官反馈/onComplete 时序保持既有路径；sweep 钉 E±（ConfettiWidget 缺席/在场控制组） |

### B. 续跑补修（本会话，3 处缺陷 / 1 文件 + 1 钉文件）

| # | 面 | 风格缺陷（续跑走查实证） | 修复 |
|---|---|---|---|
| B1 | home/predicted_intent_card（dashboard 预测卡）×3 处 | 暗分支面纱钉 `Colors.white.withValues(alpha: 0.03~0.04)`——双源模式中暗支旁路令牌（明支走 DS.surface*） | `context.colors.rimLight.withValues(alpha: 同值)`：rimLight 全档 RGB 同为纯白（0xFFFFFF），alpha 覆盖后输出**字节等值**（task_card A5 同判例）；golden 复跑零漂移实证 |
| B2 | plan/post_exam_review_screen_test | A3 的新 reduce-motion 分支无直接钉（screen 级），S01 判例要求等价可证 | 新增 2 钉：E+ disableAnimations 下提交复盘→纸屑覆盖层首帧即静止终态、泵进 1000ms 位置零位移；E- 常规路径控制组泵进位移（探针判别力） |

### C. 登记不修（📋 内容面 4 处 / 1 文件）

| # | 面 | 现状 | 不修理由 |
|---|---|---|---|
| C1 | home/weather_presentation ×4 | `blend(Colors.white, accent, isDark ? …)`——highlight 为 Color.lerp **派生基料**（非终态面纱/surface） | ①isDark 双分支已覆盖四档（dusk 亮 tint / 浅档淡 tint），走查四档零异常零对比度失败；②SparkleColors 无纯白语义槽（palette 源内 `chatBubbleUserText: Colors.white` 同先例），任何现有令牌（rimLight 带 alpha 0.2~1.0）混入 lerp 都会改变 classic-light 发布面输出——违反「classic 发布默认锚点零差量」（sweep 语义钉同口径）；③登记待 token 白槽提案（Q08 类发布面决策），不在 G01 顺手改语义槽清单 |

### D. 范围外（⛔ 7 处 / 3 文件，非家族触达面）

`home/presentation/widgets/layers/`（background_layer 3 / effect_layer 2 / particle_layer 2）的 `Colors.white` 装饰画笔：全仓唯一消费点 = `visual_elements/presentation/widgets/visual_element_preview_dialog.dart`（U15 冻结面：模块外消费=U11 成就分享卡 1 处），**不在家族任何屏的默认渲染树**；且 alpha ≤5%（mesh/glow）或 U-01 已钉（vignette「值逐位相等」）。效果层子感知装饰，无风格专属缺陷；家族 golden/走查零命中。

## 验收逐条自证（卡面原文 → 机器证据）

1. **「家族内零风格专属缺陷」** —
   - 令牌外颜色：`grep 'Color(0x'` × 五模块 = **0**（A1 前清零 + 本卡保持）；内容面 `Colors.*` 残余 = 4（C1 登记不修）+ 7（D 范围外），逐处具名归档。
   - 对比度：`g01_family_contrast_test.dart` F06 判例同口径 **15 对正文 ≥4.5:1**（classic 深/浅画布 4 对 + 三像素档画布/次级面 6 对 + on-accent 墨 3 对 + 档案药丸/chip 容器对 2 对）+ E- 禁用灰判负（探针判别力）+ E2+ 四档 brandPrimary 大字/图形线 ≥3:1；A4/A8/A9 三处 <3:1 实证修复。
   - 文本截断：task_card A6 200% 判例 + sweep「200% 文本 × 四档」钉（零溢出 + 主文案完整在场）。
   - 布局破碎：sweep 六面（dashboard/任务列表/目标详情/档案+冲刺卡/日历）× 四档零异常零溢出泵制。
2. **「四风格各有确定性 golden+语义钉且 CI 可失败」** —
   - golden：`test/goldens/g01_four_style/` dashboard+任务列表 × classic/paperDay/dusk/quiet = 8 张，B04 容差比较器（0.5% 带界，无 skip 门，常态比对路径保证 CI 可失败）；续跑修复后复跑**零漂移**（B1 输出等值设计），基线无需重签。
   - 语义钉：sweep 17 测——简报/主行动/目标上下文（dashboard）、seed 任务/空态文案/失败重试（任务列表）、目标标题（目标详情）、掌握度药丸/18%/空态/错误信息（档案）、剩余天数（冲刺卡）、改期按钮 key（日历密集信息面）、像素档挂载+亮度合同（paperDay/quiet 钉浅、dusk 钉暗、classic 无像素扩展）。
3. **「既有功能测试全绿+analyze 零+repeat 棘轮只降不升」** —
   - analyze：`flutter analyze` = **No issues found!**（续跑清掉前任遗留 2 条 info：redundant_argument_values + unnecessary_import）。
   - 回归：家族五模块 home+goal 133 / task+calendar 106 / plan 66、core/design 281、post_exam_review 5（含 2 新钉）——分批 `--concurrency=1` 全绿；全量单批结果见 test_results.json（资源红线：子集先行、错峰全量、并发=1）。
   - repeat 棘轮：`git grep -l '\.repeat(' -- 'lib/*.dart'` base 57edc4e4 = **48** → 头 = **48**（零新增零漂移；≤48 达标。U15 记 49 为其清点口径含 1 个其后他卡已移除文件，S01 自述同为 48，双判例可互证）。

## 走查分母与覆盖面（scope_and_denominator）

- **逐面 × 四风格泵制面（10 面/组件族）**：dashboard_screen（RF-06 面，harness 只读泵制：内容/加载/部分/失败 4 态）、task_list_screen（内容/空/失败/200% 4 态）、goal_detail_screen（内容/失败）、learning_portfolio_screen（内容/空/加载/失败）、exam_sprint_dashboard_card、post_exam_review_screen（reduce-motion E±）、task_card（200% 判例载体）、calendar_stats_screen（密集信息面：月历+agenda+改期入口）、sparkle_confetti（E±）、goal_created_dialog/task_detail/task_feedback_dialog/learning_path_progress_bar（走查缺陷修复载体，既有功能测试+analyze 覆盖）。
- **未逐泵长尾（17 屏）**：plan CRUD/sprint 序列（plan_create/edit/detail/history、sprint_*5 屏、diagnostic_quiz、growth）、home 长尾（notification_list/openclaw_hub/task_monitor/weather_guide）、task 长尾（task_create/reminder_settings/execution/deep_link_gate）、calendar/daily_detail——同令牌管线无私有色板（五模块 `Color(0x` = 0 实证），风格面缺陷风险以 Q05 三端重卡审查兜底（no_duplicate_rule 分工）。登记为 limitations §1.1 与挑战 CH-1。

## RF-06 高危面叙证（path_policy 要求）

`git diff --name-only | grep -E 'dashboard_screen|compact_status_bar|task_execution_screen'` = **零命中**。三文件零触碰；dashboard_screen 仅经 `dashboard_test_harness` 只读泵制（走查+golden），零产品码差量。修正一处前任注释误标：task_detail_screen 注释自称「RF-06 面触达」，实际 RF-06 三文件不含 task_detail_screen，已就地改为准确表述（行为零变化）。锁 `ui-polish-g01`：sparkle-coordination-v2 私有远端未配置于本机，租约 NOT_RUN，冲突面以 diff 自证（S01 同口径）。

## 工具链与环境事实

Flutter 3.41.3 stable / darwin 25.6.0 arm64；worktree wtG01 直连主仓分支 `agent/v4/g01`（base=57edc4e4）；`mobile/lib/gen` 为 gitignored 实体目录已补位（S01 同口径）；跑测前 df=37Gi 可用、swap=0（资源双红线全程遵守：`--concurrency=1`、子集先行错峰全量、mobile/build 用后即清 125M）。
