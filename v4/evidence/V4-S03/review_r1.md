# V4-S03 独立审查 receipt（R1 · wtS03R1）

- **审查会话**：wtS03R1（未参与 S03 实现的独立会话）
- **审查基线**：agent/v4/s03 实现 commit `17490a3a`（base `c3baf168`）；证据 commit `334c70e4`；审查时工作树干净
- **裁决**：**PASS_WITH_CHALLENGES**（CH-1 一项非阻断挑战，闭圈路径见下；无阻断证据）
- **卡面**：normal 风险 / independent_reviewers=1 / required_locks=haptic-policy；本 receipt 即 1 份独立审查
- **证据完整性**：`artifacts_sha256.txt` 五件对账 `shasum -a 256 -c` 全 OK

## 一、预登记挑战 R1-C1~C5 逐项独立下判

### C1 派发器非第二震动路径 — 防守成立

- diff 锚定亲验：`git diff c3baf168..17490a3a | grep "^+" | grep "HapticFeedback\."` —— 产品码内官方 API 直引**仅锁面枚举 7 行**（`SparkleHapticPattern` 构造表，semantic_haptics.dart:126–145 diff 行号）；`experience_feedback_adapter.dart` 零直调；其余命中均为注释与测试 mock 字符串。
- 物理出口收敛：唯一执行点 `HapticFeedbackChannel.play`（semantic_haptics.dart:315）→ `pattern.play()`；声侧 `SensoryFeedbackService.emit(…, enableHaptic: false)` —— 该参数为既有面（sensory_feedback_service.dart:367/373，`enableHaptic && isHapticEnabled()` 短路），本卡未改该文件（diffstat 三文件核）。
- 既有直调面（V3 服务 :791–824、galaxy_accessibility_service.dart :125–185）不在 diff 内、不在 V4 语义面，按卡 rollback 条款保留——与「diff 内恰一处」口径一致。
- **CH-1（唯一挑战）**：锁面源内声明「第二处直调 `HapticFeedback.*` 的新增即违锁（源码棘轮测试钉死）」（semantic_haptics.dart 库头注释）**超出棘轮实际覆盖**——G3 棘轮（测试 :441–450）只扫描 `semantic_haptics.dart` 本文件（禁 `Future.delayed`/`SystemSound`/原始通道字符串）；未来他文件新增第二处直调**不会被任何测试或守卫捕获**（亲核：`grep -rln HapticFeedback mobile/test scripts` 无全仓扫描面；rule_guard_manifest.tsv 无 haptic 守卫）。当前 diff 干净故非阻断，但「钉死」一词与机制不符。**闭圈路径二选一**：(a) 全仓棘轮——新增守卫/测试 grep `mobile/lib` 白名单外 `HapticFeedback.` 直引（允许表：semantic_haptics.dart、sensory_feedback_service.dart、galaxy_accessibility_service.dart），或 (b) 改库头注释为与 G3 实际范围一致的表述（如「锁面文件内钉死 + 全仓收敛靠审查」）。整改跟随后续卡即可，不阻断 S03 销账裁决。

### C2 successNotification Android<30 无效果是否假反馈 — 防守成立（非阻断）

- 乐谱原文裁决：`v4/02_design/MOTION_AUDIO_HAPTICS.md` 触觉节「使用系统语义/能力探测；不支持则不震，不能拿蜂鸣替代」+ 事件行「写入提交成功｜系统success一次｜有对应committed回执且非重放」——successNotification 是「系统success」的官方语义载体；Android API<30 平台自身无效果属平台策略，与「不支持则不震、不蜂鸣替代」同向，limitations L1 已如实登记。无替代刺激冒充反馈，文本仍是信息载体——不构成假反馈。
- mediumImpact V3 路径未动亲验：`sensory_feedback_service.dart:806`（success→mediumImpact）在位，该文件不在 diff；升格差异只作用于 V4 语义面。
- 观察记 Q06：真机能力矩阵应含 Android API<30 设备的 success 触觉决策点（升格在该档位=静默，与 V3 mediumImpact 有感差异），决策权在真机面证据。

### C3 默认出口改动不破 F03 — 防守成立

- 亲跑 `flutter test test/core/experience/` = **19/19 绿**（15 适配器注入型 + 4 badge widget；自述「19 注入型用例」措辞略松——4 例为 badge 面非注入型，实体无差）。
- 亲跑 H 组 4 通道级钉全绿；声侧等价亲验：`enableHaptic:false` 在 :373 短路于 `isHapticEnabled()` 之前，音频路径逐参数不变；触侧由服务内 V3 映射（原 mediumImpact）换为锁面语义槽 = 卡面声明的「触侧升格」，非回归。
- 追加亲跑 `test/core/services/ + test/core/design/` = **359/359 绿**（98+261，含本卡 22）。

### C4 去重窗 500ms 取值 — 防守成立

- 契约参数化亲验：`kSparkleHapticDedupeWindow` 常量 + 构造参数 `dedupeWindow` 可注入（semantic_haptics.dart:331 附近），改值=改契约已在常量 doc 声明；乐谱未给窗值，500ms 为实现者择值但被测试互钉。
- 边界与语义亲验：窗内 499ms 抑制 / 恰 500ms 放行（严格 `<`，F 组两钉）；跨槽不合并（F3 精确序列断言 `[selectionClick, successNotification]`）；仅放行占用窗（A2 钉被抑制调用不占窗）。

### C5 nativeHandled 非死代码 — 防守成立（按 L4 登记）

- 位面钉死亲验：E 组一正一反（:294–322）+ 具名抑制 `nativeFeedbackAlready` 计数可观测。
- 生产接线为空属实：`grep -rn nativeHandled mobile/lib` 排除测试与定义文件后零命中——当前 F03 出口恒传 false。判定**非死代码**：它是请求契约位（已测、可达、可观测），且 L4 已如实登记「调用点纪律 + 去重窗兜底、不冒充全 app 双震清零」；F03 sink 接口暂无 nativeHandled 形参属 L4 调用点审计面，非本卡缺陷。

## 二、最重靶：去重窗行为（mutation 亲放，4/4 杀死）

| # | mutation（亲改亲跑亲还原，每轮后 `git status` 干净） | 预期 | 实测 |
|---|---|---|---|
| M1 | dispatch 内 `withinWindow` 短路为 false（拆窗） | F 组窗内反例钉红 | **红** @ test:364（`second.allowed isFalse` 失败） |
| M2 | `HapticFeedbackChannel.play` 追加 `Future.delayed(100ms, pattern.play)` 组合脉冲 | G3 棘轮红 | **红** @ test:447（禁 `Future.delayed`） |
| M3 | 映射表 success→mediumImpact（错槽语义） | 映射+通道形状双红 | **5 红**（G1 逐键断言 + H 组通道形状钉） |
| M4 | 相位门条件短路 `if (false && …)`（pending/unknown 放行） | C 组+H 未知钉红 | **3 红**（pending×槽 / unknown×槽 / H-版本未知通道级） |

断言强度核：跨槽不合并用**精确序列**断言非计数；窗外再发在恰 500ms 边界放行（去重≠禁震双向钉）；窗口状态仅放行时写入。

## 三、官方 API 恰一枚映射 — 成立

- 表结构钉亲验：G1 逐键 containsPair + 「无两槽共用一枚」断言（测试 :404–422）；G 相位表 pending/unknown 不在任何放行集（结构性反例）。
- M2/M3 mutation 证明棘轮与映射双活：注入组合脉冲→棘轮红；换映射→5 红。
- 封闭性：`SparkleHapticPattern` 七元 = Flutter `HapticFeedback` 官方 API 面；锁面文件无 `SystemSound`/原始通道字符串（棘轮+亲 grep 双证）。

## 四、关闭偏好零调用 — 成立

- U14 权威单源亲验：`SensoryFeedbackService.isHapticEnabled`（:248）读同键 `sensory_feedback.haptic_enabled`（:179）；派发器默认读取器直连该静态方法（semantic_haptics.dart:337），无第二键、无第二权威。
- 关→0 开→1 反例对亲跑：A 组两例 + H4 通道级（视觉照常 presentSuccess、hapticCount==0、suppressedBy=1）；`setHapticEnabled` 翻转即生效（A2 尾段）。
- 注记（非本卡缺陷）：该键默认 `?? true`（V3/U14 既有语义，「无用户同意」分支绑定 U14 权威的开启态）；S03 按 no_duplicate_rule 不重写偏好面，语义归属 U14/设置线，建议舰队层显式确认 consent 默认口径一次。

## 五、方法通道 mock 集成 — 成立

- H 组 4 钉亲跑全绿：committed→**恰一次** `HapticFeedback.vibrate:HapticFeedbackType.successNotification`（精确串断言）；同 event 重播→0 新增；版本未知→0；偏好关→0。
- mock 形状一致性亲验：mock 挂在 `SystemChannels.platform` 真方法通道上（非替身 SparkleHapticChannel），记录串与 Flutter SDK `HapticFeedback.successNotification` 的真实通道载荷同形——这是「模拟器只认调用证据」的正确强口径。

## 六、测试质量与数字 — 成立

- 22 计数分解亲验：A2+B2+C4+D2+E2+F3+G3+H4 = 22，与 test_results.json 分解一致。
- 回归亲跑抽验（多于一）：experience 19 / services 98 / design 261 全绿；`flutter analyze --no-pub` = No issues found!；`bash scripts/run_all_rule_guards.sh` = **88 规则全过**（既有 WARN=7 ENUM-PARITY 宽免面，非本卡新增）。
- 零 l10n/backend/proto 亲验：diff 仅 3 文件（1 新锁面 + 1 适配器改 + 1 新测试），无 arb/gen/迁移/backend/proto 触碰；触觉无文案面，不支持=静默保持文本。
- 证据口径诚实：run_manifest 如实登记 lock 租约 NOT_RUN（远端未配置+冲突面自证）、flaky 历史（首试 H 组 3 败=装置缺陷）、token 计数 NOT_EXPOSED 如实、DEVICE_UNVERIFIED 分层结论；卡验收 3 两层结论分开出具成立。

## 七、合并落差 — 零冲突

- 亲验：merge-base(HEAD, origin/main) = `c3baf168`（本卡开卡基线）；双方改动文件交集 = **空**（`comm -12` 零行）；`git merge-tree --write-tree HEAD origin/main` exit 0、零冲突标记。origin/main 已推进至 `c5978b29`（含 S02R1 派整改等 state 提交），与 S03 三文件零交集——「与在航 S02 零文件交集」结构性成立。

## 八、裁决与整改项

**PASS_WITH_CHALLENGES**。五项预登记防守全部成立；四个 mutation 全杀死；全部可复现数字亲跑复现；合并面零冲突。唯一挑战：

- **CH-1（非阻断）**：G3 棘轮为文件内范围，锁面库头「第二处直调即违锁钉死」表述超出机制。闭圈二选一：(a) 补全仓白名单棘轮（守卫或测试）；(b) 订正库头注释表述。随后续触觉相关卡落地即可，不阻断销账。

**非阻断观察**：O1) Android API<30 的 success 触觉静默差异进 Q06 真机矩阵决策点；O2)「无用户同意」绑定 U14 默认开语义，建议舰队层确认一次 consent 默认口径（U14/设置线权威）；O3) 自述「19 注入型用例」实为 15 注入 + 4 badge（措辞）。

复现命令锚：本文各节命令均可原样执行；mutation 已全部还原（`git status` 干净），实现 commit 零触碰。
