# FIX-569 · 边界与未决（limitations）

1. **review_r1 本卡不产**：五件套中 review_r1 属独立未参与会话的验收产物（FIX-564 判例：审查后补）。
   本卡交付 run_manifest / test_results / diff_or_evidence_only / limitations 四件 producer 面 +
   审查 receipt 空位如实登记；自称完成不算完成，验收以独立审查 + 集成 SHA 可失败测试为准。

2. **台账行为 diff 自证**：coordination 远端（sparkle-coordination-v2 state.json / fleet.py）本机未
   配置——「V3-FIX-569 OPEN→FIXED@92dc478c」的状态行变更随本证据与分支交付，由合并闭账方落 state
   （U15 同款口径：锁租约 NOT_RUN，diff 自证）。

3. **replacementKey 用 receipt_id 直调锚，非适配器 event_id**：派单建议「replacementKey=适配器
   event_id」以 F03 适配器接线为前提；本卡按派单硬约束不动 proto/WS 面、只挂既有直调面，故取
   receipt_id（同一直调面上「一次回执」的内容寻址身份，语义同构）。适配器 event_id 锚的换装归
   F03 后续卡（契约 owner 面不变）。

4. **U05 节点详情面被排除**：`_CapabilityEvidenceSection` doc 明文「纯静态文本+图标，无动效承载」
   ——按「不放松任何既有门」排除。若后续裁决该节纪律可修订，Stamp 可迁挂（组件零改动）。

5. **动画在航断言为 widget 测试时钟口径**：80ms/60ms/40ms 中间态采样在测试假时钟下确定性成立；
   真机 profile 帧成本归设备面（S01 R1-2 同界：本卡不做每动画帧成本主张）。落定后零调度帧由既有
   S01 套件（transientCallbackCount==0）继续钉。

6. **ProposalEnter 的「纠正换载荷重播一次」是组件语义的正用**：纠正后新 intervention 是新提案，
   播一次入场符合「同 tween 重建不重播（内容刷新由调用方换 key/新实例承担）」的组件契约；
   同 payload 内重建不重播由 AnimatedSwitcher 子树保活保证（R 组同款语义，P 组未单独钉纠正重播，
   如审查需要可补）。

7. **worktree 环境缺口**：首跑需 `flutter pub get` + `make proto-gen`（gen/ gitignored 不入库）；
   分析与测试均在补齐后运行，基线对照干净（补齐前 analyze 的 25 issue 全部为 gen 缺失 URI 错，
   非本卡引入）。
