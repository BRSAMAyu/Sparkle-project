# V4-U07 · limitations

## L1 · 验收1/2 为差量举证，非本卡新实现

「200% 长中文/代码/公式不横向破屏」与「reference 点击真来源，未知引用不造超链接」在基线 e50107fe 已由既有栈满足（`sparkle_markdown.dart` 逐字换行+代码卡横滚；`AssistantCitationStrip` resolveRoute 禁用态链路）。本卡交付可失败测试冻结（含判别力对照反例），未改这两条链路的产品码。若后续有人在 sparkle_markdown / citation strip 引入回归，测试会红，但红测不阻止合并（合入门是审查）。

## L2 · 滚动锚的接线级验证深度

`ChatScrollAnchor` 以「chat_screen 同款 reversed ListView + 真实滚动物理」widget 测试驱动，chat_screen 侧接线为 6 处可读 diff（`_scrollToBottom` 门、`_handleScroll` 更新、messages 监听 user/assistant 区分、回横幅/定位回退 force、两处胶囊分支）。未 pump 完整 ChatScreen 做端到端截图级断言——chat_screen 4219 行依赖全 provider 栈，既有测试资产（u02 harness）构建成本高；作为替代，锚行为测试 + 接线 diff 是本卡的证据形态。风险：未来接线被绕过（直接调 `animateTo`）不会红测——已用 grep 钉当前仅 3 处滚动调用点（见 diff_or_evidence_only 红线自证）。

## L3 · 上滑后无「跳最新」显式入口（继承现状）

上滑阅读历史后，新消息不再拉回（卡面要求），且聊天屏现状没有「回到底部」悬浮按钮——用户需手动滑回或发送消息。本卡未新增跳最新按钮（卡面 objective 未列，五 Tab/新组件克制原则）；已预登记为审查挑战 R-1。

## L4 · 快路等待窗口的空白槽

快路轮（deterministic lane）在状态帧到达前的极短窗口（发送→首帧，通常 <100ms）渲染空白槽而非三段胶囊——这是「不展示假阶段」的直接语义后果（展示检索/思考即假进度）。预登记为审查挑战 R-4；若审查要求中性占位，属增量补丁。

## L5 · lane 形态词翻译范围

`deterministic_lane_kind` 只翻译 I09 冻结词表三值（greeting/acknowledgment/farewell）；引擎若在未来扩词表，移动端只显示「即时回复」本体（不臆造标签）——语义安全但新形态词需要一次 l10n 增量（arb+gen×3 再生）。

## L6 · 证据截图为测试环境渲染

`ui/` 两张 PNG 为测试环境真实 Flutter 渲染（Ahem 块状测试字体，F02 pixel_story 判例同形制）：布局、组件层级、禁用态、真实 tap 操作流为真；字形为块状占位，真实文案由 `*_semantics.txt` 语义树逐字承载（「即时回复 · 问候」「前往文档」「模型给出了参考，但上游未提供可解析的来源定位目标。」等）。未在 iOS/Android 真机/模拟器截图（本卡 HEAVY=False、无模拟器槽位授权）。

## L7 · translation / vocabulary 模块的覆盖形态

卡面模块含 translation/vocabulary。本卡未触翻译/词汇专属页面——这两个模块的 chat 呈现共用同一 ChatBubble/SparkleMarkdown/引用链路（MODULE_MATRIX 标注 CONTEXTUAL 嵌入材料面），验收面（缩放不破屏/引用诚实/快慢反馈）随共享栈生效；模块专属差异（如词汇练习卡）归 U10（同模块联合卡）。无独立页面级证据。

## L8 · backend .venv 复用形态

backend 回归锚（I09 49 / I03 77）经 `backend/.venv` 符号链接复用主检出环境（I09 同判例；gitignored 不入库）。`backend/app/gen`、`mobile/lib/gen` 为 gitignored 实体复制。worktree 无 `.env`（守卫脚本注释明示该形态反而避免环境性假红）。

## L9 · 未验证面

- 真机低性能设备上的长对话滚动性能（cacheExtent 600 既有值未调）；
- 暗色模式下 marker 对比度（沿用 DS.textTertiary caption 同款中断标记形制，未单独做对比度测量——F06 为 a11y 对比度权威卡）；
- Web/桌面平台滚动行为（reversed ListView 各平台行为一致性未抽验）。
