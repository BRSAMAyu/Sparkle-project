# V4-F01 — limitations

## NOT_RUN / 边界如实

1. **截图/设备面 NOT_RUN**——三次尝试用 flutter_tester 真渲染采集三档样面
   PNG（RepaintBoundary.toImage），在 flutter_tester 软渲染环境
   （--enable-software-rendering --skia-deterministic-rendering）下
   `toImage/toByteData` 挂起（每用例 ~10 分钟无返回，人工终止）；按卡面
   「模拟器不在本机 HEAVY 空窗内则不硬跑」授权跳过，改以 30 个组件级
   widget 测试（含真实渲染的渲染盒尺寸断言）作组件面证据。五面
   （首页/卡住 sheet/记忆/长回答/星图）preview 截图与三 profile 切换
   状态流属 **V4-F05（HEAVY）** 范围，本卡不越权代跑。临时采集测试文件
   已删除不入库（一次性脚本纪律）。
2. **golden 基线未建**——三档候选主题没有 golden 锚。候选主题未批准前
   入 golden 库会造成「未批准视觉被基线化」的假象；golden 建议随色板
   批准动作一起落（届时用 b04 harness 模式：env 开关采集，不做常驻比对）。
3. **色板 PROPOSED 状态不因实现而变**——`TOKENS.proposal.json` 的
   status=PROPOSED_NOT_APPROVED 不被本卡改写；色值逐槽转抄 + 派生公式
   见 run_manifest.json palette_provenance。色板批准/选择记录是设计侧
   与 HUMAN_INBOX 的事，本卡只保证「可替换、可回退、对比度已自动测」。
4. **preview 切换无 UI**——编程式入口
   `ThemeManager().setPixelPreviewProfile()` + 持久化已就绪，设置面入口
   与五面 preview 归 V4-F05（卡面锁 style-preview 在 F05）。
5. **features 全量回归未跑**——本卡 diff 不含 features 文件；classic
   路径 41 颜色槽逐槽零差量 + brightness 参数恒等改写有断言背书，
   features 行为输入不变。全量 widget/golden 留给集成 SHA 复验会话按需。
6. **dusk 聊天 user 气泡文本为深墨（#17261C）**——浅蓝 info 气泡上用
   proposal on_accent 深墨（9.25:1），与 classic 深色模式「白字深气泡」
   惯例方向不同，属候选档视觉提案的一部分，未做用户偏好验证。
7. **本机无真实设备/模拟器窗口**——与 B04 同口径：设备视觉验收
   NOT_RUN，不宣称任何真机渲染效果；测试字体为 Ahem 系测试字体，
   非最终字形。
8. **独立审查 PENDING**——见 review_receipt.json，不自称完成。
