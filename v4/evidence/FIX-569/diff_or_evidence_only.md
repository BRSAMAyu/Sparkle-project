# FIX-569 · 三 S01 implicit 一次性组件产品接线（diff 与证据）

> 分支 `fix/v4/f569-implicit-motion-wiring`（base main@8b03350b = 派单提交）；实现头 **92dc478c**；
> 未 push。台账 V3-FIX-569：**OPEN → FIXED@92dc478c**（coordination 远端本机未配置，diff 自证，U15 判例）。

## 移交令与裁决回顾

S01 一审移交（diff:108）：三个 implicit 组件零产品调用点，「V4 收口前不得无主」。Q05 侦察三-b 两案呈报，
leader 2026-09-30 裁决：**接线**（F03 链低成本样本先行），删除会使乐谱三行永久无实现。侦察实录点名
「F03 R1 低成本样本 = intervention 卡」点位。本卡按贴合度最小接线：每组件**一处**真实产品消费点，不铺开。

## 三接线位（file:line）

### 1. SparkleProposalEnter × 卡住 sheet intervention 提案卡
`mobile/lib/features/recovery/presentation/widgets/stuck_journey_sheet.dart:210`

- 选位：SCREEN_FAMILIES L7「卡住sheet先输入原因，再一个决策问题和提案」——`_ReadyPane` 的
  `_InterventionCard` 就是该提案卡（侦察与派单双点名）。abstain（无提案）时组件结构性缺席（P- 钉）。
- 语义：挂载一次性 200ms 纸面抬起（预算单源）；同 payload 重建不重播（回答问题/纠正 ack 不重播）；
  纠正换载荷经 AnimatedSwitcher 换代 = 新提案播一次；sheet 关闭即卸载零残留；reduce-motion 静态分支。

### 2. SparkleReceiptSwap × recovery 校准区 committed 相
`mobile/lib/features/recovery/presentation/widgets/recovery_calibration_section.dart:120`（key helper :77）

- 选位：派单指名「成功面孔徽章换装处」——本区 committed 相是全产品唯一成功徽章消费面
  （PixelStateBadge(success) → PixelSuccessBadge）。相体包在恒挂载替换壳内：confirming→committed
  回执落场 = replacementKey 变化 → 一次 160ms 淡入；**这正是乐谱「写入提交成功」行成立的唯一一刻**。
- 锚：`_receiptSwapKey` = receipt_id（适配器 event_id 的直调面等价物——**不动 proto/WS 面，事件源
  契约归 F03 后续**，派单明令本次只挂既有直调面）。无回执 = 空串哨兵；有回执缺 id（契约漂移）= 稳定
  常量，不造 id。
- 语义保持：首挂载不播（恢复重放直接进 committed 相 = 直落终态，文本状态仍恢复）；同 key 重投不重播；
  conflict/unknown/输入相树中零成功徽章（各相自带门零放松）；取消回输入相零回执零徽章（R 组反例钉）。
- 结构变化仅一层壳，八个相体 widget 逐字节未动。

### 3. SparkleEvidenceStamp × D-07 证据洞察卡类型印章行
`mobile/lib/features/insights/presentation/widgets/evidence_insight_card.dart:43`

- 选位：SCREEN_FAMILIES L16「像素印章标记类型，不给 AI 推断盖认证章」——卡头 kind 印章行就是该面：
  封闭词表类型（阻力模式/有帮助的应对/目标进展）图标+标题，卡挂载（feed 就绪）播一次 160ms 压印。
- 备选面排除有据：U05 节点详情 `_CapabilityEvidenceSection` doc 明文呈现纪律「纯静态文本+图标，
  无动效承载」——既有门不放松（本卡硬约束），故不落该面；`evidence.registered` 适配器路由（:55/:255）
  是纯 Dart 决策面、尚无 widget 消费者（F03 后续），本次不可挂。
- 文字纪律：全卡无「已掌握/认证」措辞（E+ 断言钉死）；零粒子零声触（组件内置）。

## 微测（mobile/test/core/design/semantic_motion_wiring_f569_test.dart，10 例）

FIX-565 同律「接线必须带覆盖」：每接线一正一反 + reduce-motion 三格（即 Q06 抽样 2 格）。
正例全部在航可测（80ms/60ms/40ms 中间态采样），反例含 abstain 缺席、门拒时序、取消、同 key 重投。
详见 test_results.json。

## mutation 自验 ×3

| mutation | 摘除 | 结果 |
|---|---|---|
| M1 | stuck_journey_sheet.dart 摘 ProposalEnter 包裹 | P 组 +1 −2 RED |
| M2 | recovery_calibration_section.dart 摘 Swap 壳 | R 组 +4 −1 RED（R+ 壳断言判负） |
| M3 | evidence_insight_card.dart 摘 Stamp 包裹 | E 组 +0 −2 RED |

验后逐字节还原，全量复跑 10/10 绿——探针判别力成立（非恒真）。

## 回归

`test/core/design/` 271/271（含既有 S01 套件）｜`test/features/recovery/ + insights/` 67/67｜
`test/features/home/` 113/113｜U15 棘轮 14/14（复跑数 48 ≤ 基线 49，零新增）｜
`flutter analyze --no-pub` 零 issue。
