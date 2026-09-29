# V4-S02 · 二审 receipt（wtS02R2）

- **审查人**：wtS02R2（独立会话，未参与 S02 实现、一审与整改）
- **日期**：2026-09-29
- **对象**：分支 `agent/v4/s02` @ a2487510（R2 基线 = 整改 commit ef0901a5；链 a305303c→d4db2c76→f89968a6→6f8009a7→ef0901a5→a2487510），工作树仅含本审查临时探针（用后即删，删后 `git status` 已确认 clean）
- **性质**：只读审查 + 临时探针/mutation 各一次（均即用即还原/删除）；未 push、未动实现与整改 commit
- **高风险口径**：2 份独立审查之第 2 份（R1 = review_r1.md APPROVE_WITH_CONDITIONS）；本 receipt 不销卡——集成仍需集成 SHA 可失败复验

---

## 裁决：APPROVE（一审三 conditions 全部清偿，S02 实现面达标）

D1/D2 修复语义亲读 + 探针复放 + mutation 复放全部吻合整改自述；抽验面（C2/C4）与归位语义、回归数字、合并落差均维持或通过。一审 D2 措辞「零写穿 prefs」按面拆分后有一处**非阻塞观察**（O-1，见下），不构成新 condition：运行态错位（一审 D2 核心缺陷）已在**全部调用面**消除，残留的仅是 `setAmbientScene` 自身既存的 persist-first 契约（先于本卡存在、属偏好语义、无验收违反、自愈）。

---

## 一审 conditions 逐条复核

### COND-1（D1）→ **清偿**

- **修复亲读**：`_applyAudioFocusDecision` 的 `stoppedByUser` 分支补 `_currentScene = AmbientScene.none`（sensory_feedback_service.dart:270）。「只清运行态不动持久化」亲核：该分支（:263-275）全部语句为 `_currentScene`/`_ambientPausedByFocus`/`_currentAmbientOutputVolume` 赋值 + `_fadeAmbientTo`/`player.stop()`，**零 prefs 触碰**（`_saveAmbientScene`/`_getPrefs`/`setInt` 均不在内）——与 `stopAmbient`（:644-652，同样不写 prefs）同口径。
- **探针复放（PASS）**：`setAmbientEnabled(true)`→init→`playAmbient(rain)`（played=true）→`handleHeadphoneUnplugged()`→再 `playAmbient(rain)` → **played=true、currentScene=rain、state=userPlaying**（一审实录 played=false，缺陷消除）。下游一致性顺带核：清空后 `resumeAmbient`（:657）与 `_applyAmbientOutputVolume`（:301）的 none 早返使停止态更收敛，无新缺口。
- **可失败钉**：耳机测末尾原无断言的 `playAmbient(rain)` 补为三钉断言（played/currentScene/state，s02_test:301-305）；原「与实现不符」注释已同步修正。

### COND-2（D2）→ **清偿（附观察 O-1）**

- **修复亲读**：`playAmbient` 的 `_currentScene = scene` 与 `await _saveAmbientScene(scene)` 移到 `beginUserPlaybackSession()` 获批**之后**（:619-625）；被拒路径（:621-623）裸 return——运行态、prefs、播放器、fade 全零触碰。`previousScene` 捕获（:586）仍在门前，仅获批后消费（:628），无语义漂移。资产门（:600）与 `isAmbientEnabled`（:611）的拒绝路径同样变为零残留（整改前这四处都会先行改写 `_currentScene`/prefs）——修复方向严格收敛。
- **探针复放（直呼面，PASS）**：rain 播放中→`beginRecording()`→直呼 `playAmbient(ocean)` 被拒→**currentScene=rain、prefs=rain、played=false**；`endRecording()`→resume 落账且 currentScene=rain——「场景态与实际音轨」全链一致。
- **探针复放（一审原形 setAmbientScene 面，PASS）**：同场景改走 `setAmbientScene(ocean, autoplay:true)`（R1 探针原路径）→ currentScene=**rain**（一审实录 ocean，运行态错位消除）、resume 落账后 currentScene=rain 与物理音轨一致；prefs 被写为 ocean——见 O-1。
- **mutation 复放（恰 3 红，与整改自述逐一映射）**：`git checkout ef0901a5^ -- mobile/lib/core/services/sensory_feedback_service.dart` 后跑两 s02 套件 → **35 绿 + 3 红**：①耳机测 played Expected true/Actual false（=D1 探针）②D2 正测 currentScene Expected rain/Actual ocean（=D2 探针）③D2 反例钉 played=false（=被拒残留吞重选下游）。还原后两套件 38 全绿。
- **O-1（观察，非阻塞）**：`setAmbientScene` 在进入 `playAmbient` **之前**无条件 `_saveAmbientScene(scene)`（:430——该 API 的既存契约，`autoplay:false` 模式即靠它实现「只存偏好不播放」；统一设置屏 :483 走此面）。故「录音中经设置屏改选场景」时偏好仍会被持久化（用户显式选择的记录，语义上属偏好而非播放残留；重开不自动续播不受影响；录音结束后重选即自愈，且与 `autoplay:false` 面行为一致）。整改自述「拒绝路径零残留零写穿 prefs」在 `playAmbient` 直呼面（焦点计时器×3、scene_audio_scope，4 处生产调用点）**精确成立**；本观察仅对该句的覆盖面做拆分澄清，不要求整改。

### COND-3（C6 登记）→ **清偿**

- limitations.md 新增 **L10**：如实登记 sfx 音量仅生效于 pool 路径（生产面，`spec.volume × sfxVolume` 合成点），native SystemSound fallback 与播放失败降级两路径不生效（`SystemSound.play` 无音量参数，平台限制）；与 review_receipt.json R1-C6 披露闭环。
- 次级建议采纳核：`kTtsAmbientDuckFactor` 值锚测试落地（audio_focus_controller_s02_test.dart 新增 `expect(kTtsAmbientDuckFactor, 0.25)`，字面量钉死）。

---

## 一审 C1-C6 抽验（R2 指定 C2/C4）

| # | 抽验 | 下判 | 独立证据 |
|---|------|------|----------|
| C2 | 资产门账本恰等 | **维持成立** | 独立重数 `mobile/assets/asset_ledger.json`（49 entries）：APPROVED∩ship∩**音频**（kind=sfx/ambient）= **33**（28 sfx + 5 ambient），与 `kLicensedAudioAssets`（gate :26-62，33 键）双向差集为**空**（脚本逐键 diff：ledger−gate=∅、gate−ledger=∅）。恰等第 34 条 `audio/bgm/bgm_catalog.json` 为 **kind=config**（打包面配置，非音频，归 S04 release-surface 守卫），不入本门口径。PROPOSED 音频 10 条（curated BGM）全数不在门集合；守卫 V4S04-ASSETS 输出 ledger=49 approved=38 proposed=11（含 1 proposed icon，与 R1 一致） |
| C4 | 录音三入口单点 | **维持成立** | `AudioRecorder`（record 插件）全仓唯一实例化点 = audio_recording_service.dart:25（其余 `Record()`/`endRecording()` 命中为 PictureRecorder 渲染与生成模型，非麦克风）；三 UI 入口 voice_input_button.dart:54 / voice_input_provider.dart:22 / unified_omni_bar.dart:59 全部实例化 `AudioRecordingService`；`beginRecording` 在 `_recorder.startStream` 成功后（:114→:117）；`endRecording` 单点在 `_cleanupSession`（:326←:315），覆盖 stop/cancel/错误/完成出口（:102/:160/:202/:211/:287） |

C1/C3/C5 未指定抽验，一审证据面复核未发现翻案线索；整改未触及其对象文件（整改 diff 仅 4 文件：服务 + 两测试 + limitations）。

## playAmbient(none) 归位语义（二审追加靶）

- **原缺陷确认**：整改前 `playAmbient` 先置 `_currentScene = scene` 后 `path==null` 早返——置 none 态却不停旧轨，语义不完整。
- **归位后**：none 路径 = `_saveAmbientScene(none)` + `stopAmbient()`（:589-596），与 `setAmbientScene` none 分支（:437-440）及 focus_timer `_selectAmbient` 的 none 处理同语义；`stopAmbient` 内 `endUserPlaybackSession` 对 stoppedByUser 早返（controller :174）、对 idle 同态不发射——与既有状态机兼容。stop 路径不经会话审批（停止非点播）语义自洽。
- **生产无此调用面（亲验）**：`playAmbient` 生产调用点全仓 4 处——scene_audio_scope.dart:93（`_ambientActivated = scene != none` 门控，none 走 :102 `stopAmbient`）、focus_timer_tool.dart:325/:552（`_ambientScene != AmbientScene.none` 内联守卫）、:382（if/else none→stopAmbient）。**无任何生产路径向 playAmbient 传 none**；该分支为消费镜像归位 + 测试可达面，兼容性成立。

## 回归与数字（亲跑）

| 项 | 自述 | 亲验 |
|----|------|------|
| +3 净增（D2 探针 2 + duck 值锚 1） | 40→43 | 逐文件 grep 计数：focus 23（22+1 值锚）、s02 服务 15（13+2）、资产门 5 ⇒ 43 ✓；整改 commit 删行 grep `^-` 含 expect/test 命中 = **0**（未删改既有断言，仅换注释+补断言）✓ |
| 受影响面 75 | 全绿 | 亲跑 **77 全绿 0 failed**（超集）：6 服务文件 67（23+15+5+10+6+8）+ widget 10（sfx 2/bgm 2/ambient toggle 2/no_fake_confirm 1/accessibility_settings 3）。自述分母 75 中「a11y 焦点面 2」无法逐文件钉定（无害分母歧义，我的批次为其超集） |
| 录音消费方 8/8 | 绿 | audio_recording_service_test + voice_input_provider_u14 + u07_evidence_capture 亲跑 **8/8 绿** ✓ |
| flutter analyze | 零 issue | 亲跑 No issues found!（探针在场时 2 issues 均指向探针文件自身，删探针后复跑为零——基线干净）✓ |
| 88 守卫 | 全过 | `bash scripts/run_all_rule_guards.sh` → **all rule guards passed (88 rules)**；抽一：V4S04-ASSETS PASS（ledger=49 approved=38 proposed=11，proposed 全隔离于发布面）✓ |
| mutation 自验 | 3 红映射探针 | 复放吻合（见 COND-2），38 = 35+3 与自述计数一致 ✓ |

分母口径注：`test_results.json` 仍记录 f89968a6 时点（40 新测），未随整改刷为 43——+3 增量由本 receipt 与 review_state 链承载（与「receipt 原文未动」同一存证惯例），非矛盾。

## 合并落差（终验）

- 本机 main = e2c2372c（**3bd1cec6 为其祖先**，`git merge-base --is-ancestor` 通过——main 在派单所述 3bd1cec6 之后又推进）。
- S02 diff（dce840da..HEAD，25 文件）× main 推进（dce840da..e2c2372c，80 文件）交集 = **l10n 五件 + v4/04_tasks/tasks.json 共 6 文件**；`git merge-tree` 0 冲突 hunk（双方皆纯增量/异区域）。
- **S03 在航 sensory 文件零交集声明终验**：main 推进文件清单 grep `sensory|audio_focus|audio_asset|s02` = **零命中**——S02 的 3 个核心服务文件与全部 s02 测试文件在 main 侧无人触碰，集成时预期无竞争。

## 结论

**APPROVE。** 一审 COND-1/2/3 全部清偿且整改本身经 mutation 恰红复放钉死；S02 三验收面的实现与证据在二审下维持成立（高风险卡 R1+R2 两份独立审查齐）。销卡仍按流程待集成 SHA 可失败复验（AGENTS.md 验收模型），非本卡缺陷。观察 O-1（setAmbientScene persist-first 契约的面拆分澄清）与 a11y 分母歧义均不阻塞；若后续 Q06 真机接线引入 OS 事件源，建议在彼处补真机面中断实测（limitations L2/L3 DEVICE_UNVERIFIED 已预留）。

---

### 附：本审查命令锚

```
git -C wtS02 log --oneline -6 / status                      # 链与干净树
# D1/D2 探针（临时文件，已删）：复用 s02 平台假体跑 PROBE-A/B/C
#   A: 耳机拔出→同场景重选 played=true；B: setAmbientScene(ocean,autoplay) 被拒 scene=rain/prefs=ocean
#   C: 直呼 playAmbient(ocean) 被拒 scene=rain/prefs=rain；endRecording→resume+scene=rain
cd mobile && git checkout ef0901a5^ -- lib/core/services/sensory_feedback_service.dart \
  && flutter test test/core/services/sensory_feedback_service_s02_test.dart test/core/services/audio_focus_controller_s02_test.dart   # 35+3 红
cd mobile && git checkout HEAD -- lib/core/services/sensory_feedback_service.dart                                    # 还原
python3 - <<'PY'  # C2 独立重数（33=33 双向空差集；第34条 kind=config）
...  # 见 receipt 正文；对 assets/asset_ledger.json × lib/core/services/audio_asset_gate.dart
PY
cd mobile && flutter test <11 文件批>                        # 77 全绿（正文清单）
cd mobile && flutter test audio_recording/voice_input_u14/u07 批   # 8/8
cd mobile && flutter analyze --no-pub                        # 零 issue
bash scripts/run_all_rule_guards.sh                          # 88 全过
git merge-tree $(git merge-base HEAD main) HEAD main | grep -c '^<<<<<<<'   # 0
git diff --name-only dce840da..main | grep -E 'sensory|audio_focus|audio_asset|s02'   # 零命中
```
