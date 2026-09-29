# V4-Q06 · 差量或仅证据（diff_or_evidence_only）

**kind=verification · 基线 f13a21ef（S 线 4/4 全收点）· 零产品码改动**

## 1. 差量清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `mobile/test/core/experience/sensory_matrix_q06_test.dart` | 新增（测试） | 矩阵全量测套件：乐谱 9 行 × 6 态 = 54 格逐格一测 + 4 补充用例（M-R2-C2b widget 级 + 验收①聚合 3 用例），58 用例全绿 |
| `v4/evidence/V4-Q06/*` | 新增（证据） | 五件套 + artifacts_sha256.txt + raw/ 原始运行记录 |

**产品码 diff = 0 行**；`pubspec.lock` 零改动（零新增依赖）；生成物（gen/）零重生成；无一次性脚本入库（探针全部内联于测试文件：platform 通道记录器、触觉通道/感官出口替身、事件构造器——随仓受测试治理）。

## 2. 仅证据部分（仓库已满足乐谱行为面，按 no_duplicate_rule 做差量举证）

本卡不重写 S01/S02/S03 已钉面，矩阵测试**只消费**既有一线权威：

- **F03 适配器**（`experience_feedback_adapter.dart`）：事件语义路由（成功面孔封闭集 task/goal/plan；memory→高亮；run/intervention→中性；E1/E2 门；event_id 去重）；
- **S03 触觉锁面**（`semantic_haptics.dart`）：封闭四槽/相位放行表/六抑制原因/能力探测/去重窗；
- **S02 音频面**（`audio_focus_controller.dart` + `sensory_feedback_service.dart` + `audio_asset_gate.dart`）：焦点状态机/提示音抑制/诚实降级位/缺省关/资产门；
- **S01 动效面**（`semantic_motion.dart` + `semantic_motion_widgets.dart`）：预算表↔乐谱窗口校验/静态分支；
- **F02 像素族**（`pixel_state.dart`）：状态徽章语义（成功/失败/冲突/未知）。

### 矩阵结论（模拟器层 54/54；逐格证据见 test_results.json）

| 乐谱行 | enabled | disabled | replay | background | unsupported | permission |
|---|---|---|---|---|---|---|
| R1 按压/选择 | PASS | PASS | PASS | PASS¹ | PASS | PASS² |
| R2 提案出现 | PASS | PASS | PASS | PASS¹ | PASS | PASS |
| R3 写入提交成功 | PASS | PASS | PASS | PASS¹ | PASS | PASS |
| R4 仅记忆已保存 | PASS | PASS | PASS | PASS¹ | PASS | PASS |
| R5 证据已登记 | PASS | PASS | PASS | PASS¹ | PASS | PASS |
| R6 独立检验通过 | PASS | PASS | PASS | PASS¹ | PASS | PASS |
| R7 冲突/未知/失败 | PASS | PASS | PASS | PASS¹ | PASS | PASS |
| R8 深任务进行中 | PASS | PASS | PASS | PASS¹ | PASS | PASS |
| R9 长期回归 | PASS | PASS | PASS | PASS | PASS | PASS |

全部 PASS 均为**模拟器层**（调用级/语义级/widget 级）。真机硬件面一律 DEVICE_UNVERIFIED（见 limitations L1–L5），不写成舒适度已通过。

¹ C4 列：既有装饰停止面（生命周期→在航动画停/恢复；BGM 暂停语义；STOPPED_BY_USER 不自续）调用级 PASS；**experience 事件链的应用可见性门 = GAP_INTEGRATION**——适配器 `present()` 无可见性入参、生产 WS 事件源未接线（S03-L5/D01/B05/FIX-569 登记过的 contract-owner 面）。该 9 格不能对「事件链后台行为」签 PASS，缺口如实登记；接线后本矩阵测试零改动可按真实流量复验。

² 真机/系统层子面（OS 触觉总开关、马达存在性）= DEVICE_UNVERIFIED。

## 3. 验收三条逐条

1. **静音/无触觉/减少动态所有任务同样可完成** — 达成（模拟器层）。C2 列 9 格：决策/文案/徽章与 enabled 逐字段全同（含全真实出口链格 M-R3-C2：SensoryFeedbackSink 真实现 + 偏好关 → 物理通道 0 调用）；减少动态静态分支信息等价（M-R2-C2b/M-R5-C5 widget 级；成功/失败/冲突/未知徽章语义两态同可达）。
2. **replay 不重播；仅真实 commit 用 success** — 达成（模拟器层）。C3 列 9 格 replaySuppressed 恒无庆祝且文案仍恢复（文本状态仍恢复）；触觉第二防线（isReplay/去重窗/相位门）独立可失败；E1 反例钉死「无回执 success 形状 → 解析拒收 → 绝不庆祝」；R6-C3 双向锚（同 event_id 抑制、新 event_id 放行）证明「仅真实 commit」。
3. **DEVICE_UNVERIFIED 不写成体验舒适度已通过** — 达成（口径纪律）。全部真机面（触感舒适度/扬声器听感/OS 中断事件源/系统触觉总开关/Android<30 平台效果）只签调用级并显式标注；本卡全文无任何「舒适/自然/已验证」的硬件体验表述。

## 4. 反例可失败性（控制组纪律）

矩阵断言的非恒真性由既有 S 线反例钉保证（偏好关 0 调用 vs 偏好开 1 调用同探针；dedupedWithinWindow/platformUnsupported/userPreferenceOff/nativeFeedbackAlready/phaseNotHapticEligible 各具名抑制原因一正一反；E1 拒收 vs 合法 committed 放行同构造器）。本卡新增 58 用例首跑曾 15 败 + 1 败，均为测试装置缺陷（通道记录器跨用例泄漏计数；构造器 `??` 吞掉显式 null 回执），修复装置后 58/58——非产品码缺陷、非删断言凑绿，原始过程记录在 raw/（最终态 machine JSONL 为最终文件状态的复跑）。
