# V4-S02 · 一审 receipt（wtS02R1）

- **审查人**：wtS02R1（独立会话，未参与 S02 实现）
- **日期**：2026-09-29
- **对象**：分支 `agent/v4/s02` @ f89968a6（基线 dce840da；实现 a305303c + 测试 d4db2c76 + 证据 f89968a6），工作树干净（复核 `git status` → clean）
- **性质**：只读审查 + 临时探针（用后即删，已确认 `git status` 无残留）；未 push、未动实现 commit
- **高风险口径**：2 份独立审查之第 1 份；本 receipt 不销卡，集成需 R2 + 集成 SHA 可失败复验

---

## 裁决：APPROVE_WITH_CONDITIONS

三个验收面全部亲验达标、证据诚实（DEVICE_UNVERIFIED 不冒充）、无第二权威；但探针实证 **2 处 S02 新增集成面缺陷**（D1/D2，均为潜伏触发面、失效方向 fail-safe），合并前应修复或钉为已知债。无阻断性伪造/越权/凑绿证据，故不 FAIL；缺陷未修前不应视为可直通集成，故不裸 APPROVE。

### Conditions（合并/集成前）

- **COND-1（D1，应修）**：焦点监听面 `stoppedByUser` 分支（sensory_feedback_service.dart:263-271）停播放器但不清 `_currentScene`，而 `playAmbient` 有同场景早返（:578）——耳机拔出后用户**显式重选同一场景被静默吞掉**，「唯一再播路径 = 用户显式点播」对同场景重选不成立。修复建议：该分支清 `_currentScene = AmbientScene.none`（或早返处对 `stoppedByUser` 放行并重开会话）。修后把 s02 服务面耳机测末尾那句**无断言**的 `playAmbient(rain)`（sensory_feedback_service_s02_test.dart:299-300，现注释声称「currentScene 已是 rain→none 由 stop 清空」与实现不符）补成可失败断言。
- **COND-2（D2，应修或钉已知债）**：录音抢占中用户改选场景：`playAmbient` 在询问 `beginUserPlaybackSession` **之前**已改写并持久化 `_currentScene`（:582-583）；会话被拒后物理播放器仍载旧音轨，`endRecording` 恢复的是**旧场景**（探针实录：currentScene=ocean 而 resume 的是 rain 音轨；且 prefs 已被写成 ocean，影响重开缺省）。低频但用户可感（听错音轨）。
- **COND-3（登记补缺）**：C6 边界（sfx 音量在 native SystemSound fallback 路径与播放失败降级路径不生效——`SystemSound.play` 无音量参数）在 review_receipt.json R1-C6 defense 有披露，但 limitations.md **未登记**；补一条 limitation。次级建议：×0.25 字面量无一测试钉死（duck 断言全部对常量自比，M2 常量改 0.5 全绿；M2b 拆 duck 语义则红 ×3）——spec 未规定 0.25，可不改，但建议一处字面量锚。

---

## 预登记 R1-C1~C6 逐项独立下判

| # | 挑战 | 下判 | 独立证据（可复现） |
|---|------|------|--------------------|
| C1 | 默认断言更新是否删断言凑绿 | **成立（非凑绿）** | V4 规格原文要求默认关：`v4/02_design/MOTION_AUDIO_HAPTICS.md:25`「默认环境声与提示音关闭，用户点播后尊重当前会话偏好；重开App不自行续播」。p2_10 改动保留并加强往返断言 + 反例面（显式开启→发声）由 s02 新测钉死（sensory_feedback_service_s02_test.dart:163-170）；sound-budget 测试前置显式开启是前提修正非删断言。亲跑 60 全绿 |
| C2 | 资产门是否第二权威 | **成立（非第二权威）** | 独立重算账本 `mobile/assets/asset_ledger.json`：APPROVED∩ship∩audio=33（28 sfx+5 ambient，proposed=11 含 10 bgm_track+1 icon），与 `kLicensedAudioAssets`（gate L26-62）恰好相等。对账测试读账本原文双向比对（audio_asset_gate_s02_test.dart:28-59）；M3 mutation：门注入 ghost 键 `audio/ui/ghost_asset.ogg` → 「反演·门→账本」测试**红**（亲跑 1 failed）。PROPOSED 反例钉亲验 |
| C3 | 来电/耳机无 OS 事件源是否空转冒充 | **成立（未冒充）** | pubspec/lock 无 telephony/audio_session 插件（grep 实证）；limitations L2/L3 如实 DEVICE_UNVERIFIED；状态迁移全部调用级可失败钉死（22 测亲跑全绿）。Q06 可零重构直呼 API 属实（`beginCallInterruption`/`handleHeadphoneUnplugged` 公开面） |
| C4 | 录音三入口覆盖 | **成立** | `AudioRecordingService` 是 record 插件唯一消费点；三 UI 入口（voice_input_button.dart:54 / voice_input_provider.dart:22 / unified_omni_bar.dart:59）全部实例化它。`beginRecording` 在真实开流成功后（audio_recording_service.dart:117）；`endRecording` 单点在 `_cleanupSession`（:326），覆盖 stop/cancel/错误/完成全部出口（:102/160/202/211/287）。其余 grep 命中为照片/通知权限，非麦克风 |
| C5 | ambient 缺省 false 是否破坏 U14 | **成立（语义保真）** | U14 测试亲跑 10/10 绿；显式键优先 + 开启不自动续播原样；被替换的仅「键未落继承提示音开关」→ 绝对 false（保护方向不变更强，新增收紧用例 u14_test:56-62）。存量影响已登记 limitations L4，且 `isSoundEnabled` 消费面仅设置屏（grep 实证，无其他行为面被翻转波及） |
| C6 | sfx 音量是否只是加键/native fallback 失效 | **成立（边界如实，登记缺位→COND-3）** | 亲读 `_playSound`：合成点 `spec.volume × sfxVolume`（:866-868）只进 pool 路径（:891-894，生产路径）；native fallback（:873-878）与播放失败降级（:915-918）走 `SystemSound.play` 无音量参数。s02 新测钉 pool 路径 0.22×0.5=0.11（:321-334）亲跑绿 |

## 状态机行为（最重靶）抽验

- **迁移矩阵**：IDLE⇄USER_PLAYING、TTS duck/解除（含「恢复目标依赖 duck 而 TTS 先结束」次序，focus_test:110-119）、录音抢占/恢复（含无会话不造会话）、来电抢占/恢复（含多抢占并存只结束其一仍暂停，focus_test:181-201）、耳机拔出 STOPPED_BY_USER 不自续反例钉（focus_test:222-244：endTts/endCall 逐一到达仍停在 STOPPED_BY_USER，唯一再播=显式点播）——22 测亲跑全绿。
- **mutation 抽验 ≥2（亲跑）**：
  - M1 拆录音抑制（emit 移除 `!promptsSuppressed`）→ 服务面「录音抢占期间 emit 零播放调用」**红**（1 failed）✓
  - M2（对照）duck 常量 0.25→0.5 → **全绿**（×0.25 字面量无钉，见 COND-3）
  - M2b 拆 duck 语义（ducked 系数→1）→ **红 ×3**（controller duck 断言 + 服务面 duck 压低/复原 + 不越权放大）✓
  - M3 资产门私货 → **红** ✓

## 默认关闭 + 不自续

- 会话态不持久化声明**核**：audio_focus_controller.dart / audio_asset_gate.dart 零 prefs 写入（grep 实证）；唯一新持久键 `sensory_feedback.sfx_volume`（用户偏好，正当）。重开 = 新进程恒 IDLE。
- 「重开不自续」e2e 断言强度**足**：s02 服务面 dispose+debugReset+重 init 后零播放调用 + 焦点 IDLE + 显式点播对照（:172-197）；debugReset 为测试专用冷启动等价近似，可接受（进程内状态无任何持久化恢复路径已核）。

## 两默认值翻转

- V4 规格依据**核**：MOTION_AUDIO_HAPTICS.md:25 明文「默认环境声与提示音关闭」——两翻转（sound true→false；ambient 继承→绝对 false）均为规格落地，diff_or_evidence_only.md + limitations L4 如实登记存量用户影响。
- 测试面非凑绿（见 C1）；波及面仅设置屏（grep 实证）。

## 测试数字与守卫（抽批亲跑）

| 项 | 自述 | 亲验 |
|----|------|------|
| 新测 40 = 22+5+13 | ✓ | 逐文件 grep 计数 22/5/13 ✓；三文件亲跑全绿 |
| 更新套件 u14=10 / p2_10=6 / ambient toggle=2 | ✓ | 计数与亲跑 ✓（60 = 40+10+6+2+2，8 文件批自述 68 含 sensory_feedback_service_test.dart 8 测，本次未单列、无矛盾） |
| 域全量 core/services+widget+features/user = 663/4skip | ✓ | 亲跑 **663 passed, 4 skipped, 0 failed**（分毫不差） |
| 录音消费方回归 | ✓ | audio_recording_service_test + voice_input_provider_u14 + u07_evidence_capture 亲跑 8/8 绿 |
| flutter analyze | 零 issue | 亲跑 No issues found! ✓ |
| SPACING 现场修 | 改基栅格未刷基线 | 亲跑 check_spacing_rhythm_ratchet.py **PASS（ratchet holds: 1592/1623）**；settings L744 实为 DS.spacing12 ✓ |
| 全量 3119/23skip | 抽批覆盖 | 未整跑全量（抽批口径：60+663/4+8 全绿 + analyze + 守卫）；分母声明与批次明细自洽，无不可信迹象 |

## 合并落差（main 已推进）

- 本机 main = c3b05e7a（含 c3baf168 P01 收口 + S02 派单 state）；origin/main = afdb5754。
- 文件交集（S02 diff dce840da..HEAD × main 推进 dce840da..c3b05e7a）：**l10n 五件（arb×2+gen×3）+ v4/04_tasks/tasks.json** 共 6 文件——U11 亦加了 l10n 键。`git merge-tree` 对两 tip 均 **0 冲突 hunk**（双方皆纯增量/异区域），合并风险低；集成时按台账以最新集成 SHA 复跑 l10n 相关测试一次即可。

## 证据五件套与卡面核对

- 五件套齐（diff_or_evidence_only / run_manifest / test_results / review_receipt / limitations），与本卡 `outputs` 要求一一对应；卡验收 3 口径（模拟器只认调用级证据 + 未测真扬声器标未验证）在 limitations L1-L3 贯彻，无冒充。
- 分支 tasks.json 状态 PENDING→in_progress/REVIEW_READY 与派单 state 提交（main dc38df74）一致。
- run_manifest 如实登记：locks 租约 NOT_RUN（远端未配置，自证冲突面）、token NOT_EXPOSED、批次 9 的一次 load 假红归因——均符合「不伪造」纪律。

## 缺陷实证（探针实录，探针已删）

> 探针 = 复用被测套件同一平台假体（audioplayers 平台接口记账），跑毕即删，未留痕。

- **D1**：`setAmbientEnabled(true)` → `playAmbient(rain)`（played=true）→ `handleHeadphoneUnplugged()`（stop 落账）→ 再 `playAmbient(rain)` → **played=false**，state=stoppedByUser，currentScene 仍=rain。换场景（ocean）可播 → 缺陷严格限于同场景重选被 ：578 早返吞掉。
- **D2**：`playAmbient(rain)` → `beginRecording()`（pause 落账）→ `setAmbientScene(ocean, autoplay:true)`（会话被拒、currentScene=ocean、prefs=ocean，无播放）→ `endRecording()` → **resume 落账**（恢复物理 rain 音轨）而 currentScene=ocean。

两缺陷现状不可达（无 OS 事件源/用户恰好录音中换场景），失效方向为「该响不响/响错轨」而非「不该响乱响」——不违反卡验收 1/2 的任何禁止面；但因属 S02 自增集成面且 Q06 接线即触发，列 CONDITIONS。

## 结论

APPROVE_WITH_CONDITIONS。三 conditions 清偿后本卡实现面具备 R2 审查条件；R2 重点建议：独立复验 D1/D2 是否已修 + 全量分母亲跑。

---

### 附：本审查命令锚

```
git -C wtS02 status / log                                    # 干净树 + 三 commit 链
cd mobile && flutter test <7 文件批>                          # 60 全绿
cd mobile && flutter test test/core/services/ test/widget/ test/features/user/   # 663/4skip
cd mobile && flutter analyze --no-pub                        # 零 issue
python3 scripts/guards/check_spacing_rhythm_ratchet.py       # PASS
git merge-tree $(git merge-base HEAD main) HEAD main | grep -c '^<<<<<<<'   # 0
# mutations：M1/M2/M2b/M3 逐个 apply→test→revert（见上文明细）
# 探针：临时 test 文件复用 s02 假体跑 D1/D2 → 实录 → 删除
```
