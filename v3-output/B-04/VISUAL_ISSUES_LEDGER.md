# B-04 · 首轮视觉问题 Ledger（golden 基线批）

- 基线：`v3-output/B-04/screenshots/`（9 canonical states × 3 viewport 批 = 27 张，build SHA8 `b8c94477`，wt708 全量重采批 2026-09-27 单锚态；前批 `87b5f432`（wt693）26 张 + android home 单面 `e0777bd5`（wt696）已删除并由本批同位替代——25/27 逐字节相同、2 张差全归因（chat android 时间戳噪声、macos 1280x800 home=FIX-376 内容演进），见文末「重采批记录」wt708 段）
- 审查依据：`v3/04_ux/VISUAL_REVIEW_RUBRIC.md`（12 维 0–2 分；A=阻断/误导/不可读/错误主焦点，B=明显降低体验，C=微调）
- 审查方式：逐张真实读图（本会话直接查看 PNG）+ 布局探针（`v3-output/WT401-Q03-VISUAL/layout_probe_b04.json`，27 条：pump_exception=0、截断候选=0）
- 声明：本批为 flutter test golden 路径真实渲染；macos 批存在**环境级字形伪影**（见 ENV-1），文字级审查以 android 批为权威，布局/层级/间距审查两批均有效。

## 评分摘要（12 维 rubric，android 批为主）

| surface/state | Hierarchy | Clarity | Density | Spacing | Typography | Color | Consistency | Affordance | State | Brand | Motion | Platform | 结论 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| onboarding/persona_start | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | n/a | 2 | 过 |
| home/main | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 过（见 B-04-L-01） |
| chat/history_citations | 1 | 2 | 1 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 4 项 B/C（见 L-02/03/04/05） |
| goal/library_main | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | n/a | 1 | 过（见 C-01） |
| task/library_main | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | n/a | 2 | 过（见 C-02） |
| memory/panel_main | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | n/a | 2 | 过 |
| galaxy/tree_expanded | 2 | 1 | 1 | 2 | 1 | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 见 B-04-L-06 |
| profile/main | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | n/a | 2 | 过 |
| settings/main | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | n/a | 2 | 过 |

**首轮结论：核心 9 surfaces 无 A 级（阻断/误导/不可读）issue；B 级 3 项、C 级 4 项、环境限制 2 项，逐条如下。**
（对照 V3 Gate V3-7「核心旅程 A/B=0」：B 级 3 项须在 L2–L5 审查轮内清零后该 Gate 才可判过。）

## B 级（明显降低体验）

### B-04-L-01 · home：叙事区错误文案裸露在 demo 首屏【已收口——V3-FIX-376 补完（wt696）FIXED@e0777bd5+c69f55b7，见 2026-09-25 闭案补记】
- 现象：`home__main__demo_data`（android/macos 两批一致），主叙事句（"早上好，今天先从一小步开始…"）正下方直接渲染「ⓘ 加载失败 轻触重试」。
- rubric：State feedback 1 分——错误态可见性本身诚实，但 demo persona 首屏把「失败」当常态展示，与「今天适合保持节奏」的头部语气冲突，5 秒测试里构成误导性焦点。
- 复现：home__main__demo_data__android__1080x2400@3.0__87b5f432.png 中部（d7a961da 首轮批同位相同）。
- 建议裁决方向：demo 模式下叙事源失败应降级为隐藏/占位（demo 数据永不失败是 demo 契约的一部分），或 demo 数据补齐该 narrative 源。
- 关联：Q03 基线（WT401 evidence C01_home_default.png）同位置同样存在——非本批新引入。
- **2026-09-25 补记（wt693 重采批实拍归因）**：V3-FIX-376（wt686）给 `features/home/presentation/providers/understanding_snapshot_provider.dart` 的 `_fetch` 加了 demo 门控，但 golden home 首屏「Sparkle 对你的理解」回执卡（`UnderstandingSnapshotCard`）实际消费的是**同名双胞胎 provider**——`features/experience/presentation/providers/experience_provider.dart` 的 `understandingSnapshotProvider`（`FutureProvider.autoDispose` → `experienceRepository.getUnderstandingSnapshot()`，**无 demo 分支**）。临时探针实测（B-04 同源泵配方，isDemoMode=true）：该 provider 仍为 AsyncError(DioException 400)，错误卡父链 = CompactErrorCard < Semantics < UnderstandingSnapshotCard。87b5f432 重采 home ×3 批与 d7a961da **逐字节相同**，错误行仍在。FIX-376 收口的是 home understanding panel / chat understanding drawer 消费面（slot 系统内默认折叠，不入 golden 首屏）；本 ledger 面向的 golden 首屏回执卡未修。**L-01 保持开放**，待修面 = experience 孪生 provider（或其 repository 的 demo 分支）。
- **2026-09-25 闭案补记（wt696 · V3-FIX-376 补完 FIXED@e0777bd5+c69f55b7）**：experience 孪生 provider 补同构 demo 门控（isDemoMode 返回内建空快照，卡片空态承载，非 demo 路径零改动）；wt693 临时探针固化为正式测试（`mobile/test/features/experience/presentation/providers/experience_understanding_snapshot_demo_test.dart`，修前 2 红/修后 2 绿）。home android 单面重采 `home__main__demo_data__android__1080x2400@3.0__e0777bd5.png`：亲验读图对照——旧图主叙事句下「ⓘ 加载失败 轻触重试」消失，回执卡以数据态空态承载（兜底叙事+0% 置信 pill）；android manifest 重建 9 条目 verify OK、coverage 9/9、探针 27 条保序换锚（pump_exception=0、截断候选=0）。注：macos 批 home 面仍锚 87b5f432（本批范围只采 android 权威文字面，ENV-1 口径；macos home 面待下轮全量重采顺带换锚，布局两批同源不受影响）。**L-01 关闭**。

### B-04-L-02 · chat：360dp 手机宽下消息列表下方大片死区
- 现象：`chat__history_citations`（android 批），最后一条消息的反馈操作（不是这个方向/更短一点/直接出题/重新校准）与输入坞之间约 40% 屏高的空白，无任何内容或留白设计语言支撑。
- rubric：Hierarchy 1 分 / Density 1 分 / Spacing 1 分。
- 复现：chat__history_citations__demo_data__android__1080x2400@3.0__87b5f432.png 中下部（d7a961da 首轮批同位相同）。
- 建议裁决方向：会话内容不足一屏时列表锚定/留白策略需统一（死区在 macos 批同样存在）。

### B-04-L-03 · chat：桌面宽（1280）下浮动配置胶囊纵向叠在消息区
- 现象：`chat__history_citations`（macos 1280x800 批），「选择计划 / 均衡 / 选择模式 / 引导·自主探索」四组胶囊以垂直栈形态浮在消息区中央偏下，与消息流、模式条（均衡·标准对话·未绑定计划）、底部「当前自我模型」面板三层元素相互叠压，主焦点混乱。
- rubric：Hierarchy 1 分 / Platform fit 1 分。
- 备注：android 批无此栈（胶囊并入模式条），属桌面宽度专属布局问题。字形伪影（ENV-1）不影响该布局判断。
- 复现：chat__history_citations__demo_data__macos__1280x800@2.0__87b5f432.png 中下部（d7a961da 首轮批同位相同）。
- 建议裁决方向：桌面宽度下四组配置应并入模式条或右侧栏，不得浮在消息流上。

## C 级（微调）

### B-04-L-04 · chat：360dp 宽下会话标题截断至「随…」
- 现象：app bar 标题区被 leading 头像 + 4 个动作图标挤压，仅显示首字+省略号。
- 建议：360dp 下动作图标收纳（如溢出菜单），保标题至少 4 字。

### B-04-L-05 · chat：引用条默认折叠且消息正文滚出视野
- 现象：引用卡片（错题本·一元二次方程判别式专题 / 高等数学·第三章）在树内真实渲染（采集测试有 in-tree 断言），但 360x800 首屏仅露出最后一张卡片段 + 「来源摘要」折叠 chip，引用块对比度审查需滚动。
- 建议：含引用块的回复进入视野时默认展开首张引用卡（或消息定位时以引用块为锚点）。

### B-04-L-06 · galaxy：节点标签不可读（需交互才可达）
- 现象：`galaxy__tree_expanded`（android/macos 一致）：统计条（57 节点/95%/60%）、贡献 chips、待审核 pill 渲染良好，但节点树本体以彩色分段 mastery 条呈现，**节点文字标签在无交互（点击/缩放）下不可见**；states 注册表的「节点标签可读」断言在静态基线不可达。
- rubric：Clarity 1 分 / Affordance 1 分。
- 建议：树视图默认展示 top-N 节点标签（或 hover/tap 前提供可读的图例）；真机批次按注册表入口执行「展开演示节点」后再审。

### B-04-C-02 · task：筛选 chip 横向裁切暗示不足
- 现象：任务列表筛选条「已暂停」chip 在 360dp 只露出「已暂…」前缀，横向可滚动但无边缘渐隐/箭头暗示。
- （编号注：B-04-C-01 空缺，为报告中引用编号与图像文件对应保留的容错位，不补占位内容。）

## 环境限制（非产品 issue，golden 环境特有）

### B-04-ENV-1 · macos 批特定字符渲染为实心黑块
- 现象：macOS 目标语义（debugDefaultTargetPlatformOverride=macOS）下，ASCII 数字/Latin 词（7、2、Sparkle）与个别汉字（一、是、时）在**部分文本 span** 中渲染为实心黑块/斜纹块；android 目标全字符正常。
- 定位：flutter_tester 无平台字体，q03 harness 已注册 Arial Unicode + SFNS.ttf 仍复现（SFNS 注册无改善）；真实 macOS 桌面 app（B-03 macos journey 实测）字体栈完整，不受影响。属 flutter_tester 引擎级环境限制，非产品代码缺陷。
- 处置：macos 批用于布局/层级/间距审查；文字级审查以 android 批为权威；真机批次（HUMAN_INBOX）为 macOS 文字审查权威。

### B-04-ENV-2 · 探针 off-bounds 计数在 macos 批口径失真
- 现象：`layout_probe_b04.json` 的 off-bounds 计数沿用 Q03 固定逻辑尺寸（390x844）作界，macos 批（800x600/1280x800）因此计数虚高（数百），仅可做趋势参考。
- 处置：硬信号以 pump_exception=0、截断候选=0 为准；探针尺寸参数化列入 B-04 harness 后续增量（见 REPORT 待办）。

## 与历史基线的一致性
- Q03（WT401）基线的 home 叙事错误态（L-01）、galaxy 首引卡（本批已按注册表入口关闭）等观察与本批吻合；本批无与既有证据矛盾的渲染。

## 重采批记录（wt693 · 2026-09-25 · build SHA8 `87b5f432`）
- 背景：wt686 落地 V3-FIX-376（demo 理解快照错误裸露收口）与 V3-FIX-377（chat fontSize 令牌双态撕裂机械收口，宣称同值零视觉）后，按「B-04 基线 PNG 陈旧待重采」预期执行重采。零产品代码改动，FIX 号不新占。
- 采集：`B04_VISUAL_CAPTURE=true flutter test --update-goldens --dart-define=B04_BUILD_SHA8=87b5f432 --concurrency=1 test/goldens/b04_visual_baseline/` → 27/27 绿；复验（无 --update-goldens）→ 27/27 绿（0.5% 容差比较器）。注：sha8 段只认 `--dart-define`（`String.fromEnvironment`），环境变量不生效。
- 新旧对比（d7a961da → 87b5f432，逐对 sha256）：
  - **26/27 逐字节相同**。
  - 唯一差异 = `chat__history_citations` android 批：diff bbox 59×23px @ app bar 下首消息时间标签（571 像素，占全图 0.022%），内容为「14:06 → 17:35」——**已知噪声类**（demo 消息时间戳，wt667 首轮已登记），远低于 0.5% 容差，非布局/文案回归。
  - **home ×3 批逐字节相同 → V3-FIX-376 在 golden home 首屏零像素效果**：实拍证明 L-01 错误行未消失（同名双 provider 归因见 L-01 补记）。「home 基线陈旧」的预期不成立——基线未陈旧，是缺陷未修到该面。
  - chat macos 两批逐字节相同 → **V3-FIX-377 fontSize 令牌同值零视觉的又一实证**（android 批微差已完全归因时间戳）。
  - 其余面（onboarding/goal/task/memory/galaxy/profile/settings ×3 批）零漂移，无超容差项。
- manifest ×3 重建于 87b5f432（`manifests/manifest_{android__1080x2400@3.0, macos__800x600@2.0, macos__1280x800@2.0}.json`，各 9 条目）→ `verify OK` ×3 → `coverage 9/9`。
- 布局探针 `v3-output/WT401-Q03-VISUAL/layout_probe_b04.json` 随采刷新：27 条全部锚定 87b5f432，pump_exception=0、截断候选=0（与首轮同口径）。
- 旧 d7a961da 批 27 张 PNG 已删除（由 87b5f432 批同位替代；首轮实拍事实以本 ledger 文字记录与 REPORT.md 留痕）。

## 重采批记录（wt708 · 2026-09-27 · build SHA8 `b8c94477` · 全量单锚化）
- 背景：兑现 V3-FIX-376 行尾注「macos 批 home 面仍锚 87b5f432 待下轮全量重采」+ 消解 V3-FIX-395（verify 门以单一 B04_BUILD_SHA8 定位全部 27 张，wt696 单面重采后的 87b5f432/e0777bd5 混锚态使任一单 sha8 全套运行必现 missing-file 挂）。零产品代码改动，FIX 号不新占（395 闭账不新占 407/408）。
- 采集：`B04_VISUAL_CAPTURE=true flutter test --update-goldens test/goldens/b04_visual_baseline/ --dart-define=B04_BUILD_SHA8=b8c94477` → 27/27 采集绿；复验（无 `--update-goldens`）→ **33/33 全绿单锚**（含 6 例比较器带界单测）。旧 27 张（26×87b5f432 + android home×e0777bd5）git rm 同位替代，混锚残留为零。
- 新旧对比（87b5f432/e0777bd5 → b8c94477，逐对 sha256）：**25/27 逐字节相同**；2 张差全归因：
  - `chat__history_citations` android 批：消息时间标签 17:35 → 18:55（亲验读图确认，已知噪声类，wt667 首轮登记）。
  - `home__main` macos 1280x800 批：**V3-FIX-376 home 重做内容演进**——亲验读图对照：旧图主叙事句下「ⓘ 加载失败 轻触重试」（CompactErrorCard）消失，同位 UnderstandingSnapshotCard 空态承载（兜底叙事+「纠正我的理解」+置信 pill），与 wt696 android 批同状；wt702 实测对旧基线 15.24%/624,197px 真差确系内容演进而非渲染管线问题，新基线下归零（verify 单锚直过）。
  - `home__main` macos 800x600 批与 android 批重采输出均逐字节复现旧批（800x600 视口回执卡在折叠线下，可见面零变化）——同一渲染管线 25/27 逐字节复现旧输出，为「非管线问题」的反证。
- manifest ×3 重建于 b8c94477（各 9 条目）→ `verify OK` ×3 → `coverage 9/9` ×3。
- 布局探针 `v3-output/WT401-Q03-VISUAL/layout_probe_b04.json` 随采刷新：27 条全锚 b8c94477、恢复测试执行自然序（android 9 → macos800 9 → macos1280 9；wt696 尾并暂态消除），pump_exception=0、截断候选=0；chat/galaxy/profile/home 面 text_widget_count −5 与窗口内 main 合入的 V3-FIX-384/385/360 同期，对应 PNG 逐字节相同（屏外/语义层 widget 增减，像素面零回归）。
- 全量回归：`flutter test test/goldens/` 84 过 15 skip 0 红；`flutter analyze` No issues found。逐张新旧锚对照表与读图记录见 `v3-output/WT708-REBASE/notes.md`。
- 评分摘要与 L/ENV 各条目判定不受本批影响：本批无新产品缺陷发现；L-01 闭案结论在 macos 1280x800 批同状复核成立（错误行消失）。
