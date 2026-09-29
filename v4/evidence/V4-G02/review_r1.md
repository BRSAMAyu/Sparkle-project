# V4-G02 · R1 独立审查 receipt

- 审查会话：R1（未参与实现；worktree wtG02，分支 agent/v4/g02）
- 审查对象：`96f8d1bb`（交付链 b3eeac17 → 96f8d1bb → 58fa3ac3，base f64d8590）
- 审查日期：2026-09-29
- 探针还原：三个 mutation（M1/M2/M3）全部 `git checkout --` 还原；审查全程结束工作树 clean（`git status --short` 零输出）。

## VERDICT: PASS_WITH_CHALLENGES

十靶全打。红线零 diff 成立；数值证据独立复算全量命中；三 mutation 有牙；四条预登记挑战三条裁成立、一条（挑战②）附等价迁移建议。无阻塞缺陷；4 项 info 见下。

---

## 编号发现

### R1-1 [info] 守卫测试浅档流式码面模型与实际码面不一致（证据表 stream 列同源）
- file:line: `mobile/test/widget/v4_g02_family_contrast_guard_test.dart:84-91`
- 事实：守卫把流式码面建为「浅档 `chatBubbleOtherText@6%` 叠气泡面 / 深档 surfaceTertiary」；但实际 `_StreamingBubble` 已无条件 `DS.surfaceTertiary`（`chat_screen.dart:4044`），`ink@6%` 公式在现行 lib 零消费点。
- 复算：证据表 `streamCode_fixed` 列（14.04/11.32/8.33/13.23）与守卫模型公式逐值吻合（12/12 命中，含 classic=light 档）；实际码面对应 `settledCode` 列（13.49/10.25/8.33/12.48）——实际面由守卫「落定代码块」对覆盖，无未覆盖面；两口径最低值同为 dusk 8.33:1=阈值 1.85 倍，「流式/落定差」实际为 0（优于表载 ≤1.07）。
- 结论：产品码无缺陷、验收结论稳健；属守卫注释/模型陈旧（测试保真度），建议后续会话把 streamingCodeFace 收敛为 `DS.surfaceTertiary` 与码面一致。不改判。

### R1-2 [info] DL-SPEC 棘轮对「repeat 语义回退」无牙（活钉才是真牙）
- file:line: `scripts/guards/check_dl_spec_ratchet.py:208-209,240-244`
- 复现（M2 变异）：把 `agent_avatar_stack.dart` 的 else-if repeat 挪入 reduce-motion 分支（语义=恢复无条件起表，`.repeat(reverse: true)` 出现次数不变 1）→ `python3 scripts/guards/check_dl_spec_ratchet.py` 仍 PASS（53/56）；同状态下 `flutter test …golden_semantic --plain-name 活钉 --timeout 30s` 红（+0 -1）。还原后活钉绿。
- 结论：交付自述的牙是「活钉+控制组」（准确）；棘轮只对 repeat 计数增减有牙（逐文件钉、+1 即红，M2v2 口径核实）。守卫牙边界澄清，非缺陷。

### R1-3 [info] isLast 登记项方向描述有误（实际：连接线恒渲染/末节点悬挂，非「不渲染」）
- file:line: `mobile/lib/features/chat/presentation/widgets/collaboration_timeline.dart:160,168,203,349`
- 事实：`_buildTimelineItem` 持正确参数但 `_buildTimelineNode(step)` 不传参；节点内 `if (!isLast)` 解析到外层 `bool get isLast => false`（:349）→ `!false` 恒 true → 连接线对**每个**节点（含末节点）都渲染（末节点悬挂 40px 线）。基线 `f64d8590` 同构（:167,193,338）——确系既有问题。
- 结论：「登记不修、留行为卡」处置正当（超风格面）；仅证据描述极性写反，建议行为卡引用时以本条为准。

### R1-4 [info] D3 排除链最弱两档复算偏差 ≤0.07（结论不受影响）
- 事实：neutralOutline 2.26 / neutral500 2.85 / neutral600 5.18 三档与证据表精确命中；borderSubtle/border 两档 R1 复算 1.16/1.22 vs 表载 1.22/1.29（疑 alpha 合成舍入口径差）。两档均远低于 3.0 阈，排除结论稳健。守卫 5/5 亲跑绿；M1 变异（描边回退 borderSubtle）→ 4 个卡住 sheet 语义钉全红（widget 级真牙在 golden 钉，守卫为公式级配对）。

---

## 十靶核验记录

1. **F566/provider 零 diff（红线）**：`git diff f64d8590..58fa3ac3 -- mobile/lib/features/chat/presentation/providers/ mobile/test/unit/chat_f566_retry_reuse_path_test.dart` 零输出；chat 家族 36 文件改动全部落 presentation/ + data 层唯一 message_notification_service（纯字号令牌化，逐行核）。chat_f566 两测亲跑 5/5。
2. **流式对比衰减独立复算**：以 `pixel_preview_theme.dart`/`theme_manager.dart` 锚值 + 独立 Python WCAG 实现（复刻 Color.lerp gamma 线性），四档×5 列 12/12 精确命中（quiet oldDark 1.13✓→实际码面 12.48；dusk 最低 8.33=1.85×阈✓；classic 行=light 档 1.94✓）。
3. **D3 描边排除链**：亲验 5 档（见 R1-4）；neutral600 四档 5.18/10.36/4.75/12.20 独立复算全 ≥3.0；borderStrong 1.67/neutralOutline 2.68 亦不足佐证成立。
4. **D4 repeat 降级**：9 处逐一核（8 chat + aurora 打字点），全部 S01 判例等价（停表+静态终态/相位冻结，正常路径 repeat 保留）；三棘轮亲跑 PASS（persistentRepeatLoop=53/56、spacingHalfStep=1590/1623、UI-TOKENS 213/275+557/727）；活钉 pumpAndSettle+控制组（scale 偏离 1.0 实测断言）均非恒真。
5. **D5 自纠**：`_ShimmerRow` List.generate(4)+Padding 持排布、`_ShimmerDot` 即单点槽（静态分支单 Container 8×8）✓；96f8d1bb 回环 diff 核实；棘轮暴露机制亲证（M3：槽内注入 `EdgeInsets.only(right: 6)` → `status_awareness_bar.dart: spacingHalfStep 29 > baseline 28 (+1)` FAIL，exit 1）。
6. **挑战① golden Linux 跳过**：`_goldenCapable` 仅包裹 7 处 `matchesGoldenFile`，全部语义钉（白面字面量零命中/QuietChip 描边槽/toneOnTint 四档/结构在场/reduce-motion 活钉+控制组）在门外全平台照跑；wt296 判例有档（V4-F06/limitations）。语义文件亲跑两遍 27/27=确定性。裁：不构成「CI 可失败」缩水。
7. **挑战②③**：② toneOnTint 挂 DS 层、值源 `_theme` 唯一，与 brandPrimaryDeep（`theme_manager.dart:927`，lerp 派生）同律成立；按 batch3「派生上收」方向最终宜迁 SparkleColors——等价迁移建议非缺陷。③ textTertiary 转发定标槽：233 消费点/103 文件；新旧值四对独立复算全部改善方向（2.42→4.59 / 2.45→4.75 / 3.79→4.57 / 3.92→5.08，旧派生实际低于 4.5 阈）；B2-3a 自动测（semantic_color_names/u02_rubric）+core/design+aurora 286 亲跑全绿背书充分。
8. **mutation 独立 ×3**：M1（D3 border→borderSubtle）=卡住语义钉 4 红；M2（repeat 语义回退）=活钉红（棘轮无牙发现见 R1-2）；M3（D5 槽内半步字面量）=spacing 棘轮逐文件红。全部还原。
9. **回归抽半**：亲跑批——329（chat+G02 两测+recovery）全绿、286（core/design+aurora）全绿、golden 27×2、守卫 5、f566 5、analyze No issues、UI-TOKENS/DL-SPEC/SPACING 三棘轮亲跑 PASS；artifacts_sha256 32 项抽验 3/3 命中、25 张 golden 实存。
10. **登记项处置**：isLast 既有问题成立、不修正当（方向描述见 R1-3）；websocket 离线队列契约测单跑×3 全绿（+24×3）+329 批亲跑绿——「时序 flake 非回归」采信（该测属 data 层，本卡零改动亦核）。

## 命令与 exit code 清单

| cmd | exit | 结果 |
|---|---|---|
| git diff f64d8590..58fa3ac3 -- providers/ + chat_f566 unit 测 | 0 | 零输出（红线） |
| flutter test chat_f566 两测 --concurrency=1 | 0 | 5/5 |
| flutter test v4_g02_family_contrast_guard_test --concurrency=1 | 0 | 5/5 |
| flutter test v4_g02_family_golden_semantic_test ×2 --concurrency=1 | 0 | 27/27 ×2（确定性） |
| flutter test test/core/design test/features/aurora --concurrency=1 | 0 | 286/286 |
| flutter test chat+G02+recovery 329 批 --concurrency=1 | 0 | 329/329 |
| flutter test websocket_chat_service_v2_test ×3 --concurrency=1 | 0 | +24 ×3 |
| flutter analyze --no-pub | 0 | No issues found! |
| python3 scripts/guards/check_dl_spec_ratchet.py | 0 | 53/56 |
| python3 scripts/guards/check_spacing_rhythm_ratchet.py | 0 | 1590/1623 |
| python3 scripts/guards/check_ui_design_tokens_ratchet.py | 0 | 213/275, 557/727 |
| M1 变异→golden --plain-name 卡住 | 非0（4 fail） | 红→还原 |
| M2 变异→golden --plain-name 活钉 --timeout 30s | 非0（1 fail） | 红→还原 |
| M2 变异→check_dl_spec_ratchet.py | 0（无牙，R1-2） | 记录 |
| M3 变异→check_spacing_rhythm_ratchet.py | 1 | 逐文件 +1 红→还原 |
| 独立复算探针（python3 /tmp/v4g02_review/*.py） | 0 | 12/12+5 档+4 对命中 |

## 资源红线

全部 flutter test 带 `--concurrency=1` 错峰；无并行大批。
