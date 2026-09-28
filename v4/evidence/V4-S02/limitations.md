# V4-S02 · 已知限制

## L1 · 真机扬声器听感 DEVICE_UNVERIFIED
全部证据为模拟器**调用级**（平台接口假体逐调用记账 / SystemSound 通道计数）。真扬声器上的实际响度、duck 听感、fade 曲线听感未实测。卡验收3 明示「模拟器只认调用与录制证据，未测真扬声器标未验证」；真机面归 **Q06**。**不冒充已验证**。

## L2 · 系统来电/音频中断的 OS 事件源未接线（状态机就绪，事件源归真机面）
`AudioFocusController.beginCallInterruption()/endCallInterruption()` 提供完整迁移与恢复语义（Android 瞬时焦点失而复得惯例 / iOS interruption-shouldResume 惯例的调用级实现 + 多抢占并存裁决 + 单测钉死），但本机未接入真实 OS 来电事件——仓库无 telephony/audio-session 类插件（pubspec 实证），硬规则 7 要求新平台通道先查先例并经裁决，本卡不擅自引依赖。真机接线与听感验证归 Q06（其卡片可直呼本控制器 API，零重构）。恢复语义本身已按「模拟器证据口径」钉死。

## L3 · 耳机拔出 OS 事件未接（同上）
`handleHeadphoneUnplugged()` → STOPPED_BY_USER 不自续的状态迁移 + 服务面 stop/resume 拒绝自续均已调用级钉死；真实耳机拔出事件（Bluetooth 变更/wired unplug）需平台事件源，同 L2 归 Q06。

## L4 · 两处默认值的用户可见行为变更（V4 规格，如实登记）
按 MOTION §声音设计「默认环境声与提示音关闭」+ 卡验收1「未明确点播无声音」：
- 提示音开关缺省 true→false（原 V3 行为，p2_10 断言已按新规格更新并留锚点注释——非删断言凑绿，反例面由 s02 新测钉死）；
- 背景声键未落时缺省由「继承提示音开关」（U14 机制）收紧为绝对 false（更强保护，U14 测试原断言仍过 + 新增收紧用例）。
从未显式点播过的存量用户升级后将听不到操作提示音（显式开启即恢复；偏好持久化不丢数据）。这是 V4 规格的目标行为，非回归；如产品侧要差异化灰度，走既有 off/shadow 开关面另行裁决（rollback 字段口径）。

## L5 · SceneAudioScope 的路由进入自动播放语义未改
`task_routes/focus_routes` 的 `useSavedAmbient: true` 在用户显式开启背景声且选过场景时，进入任务/专注路由会播放环境床——这是用户显式配置后的「开始专注」触发（U14 语义「播放仍只由用户显式选场景/开始专注触发」），不是「未明确点播」。默认关闭后，未点播用户进入这些路由**无声**（本卡验收1达标）；点播用户的行为保持 V3 惯例未重写。

## L6 · TTS 与短提示音不构成互斥
MOTION 的回录约束只落在「录音/背景床」面；TTS duck 只压低环境床，提示音照常（状态机 `promptsSuppressed` 仅录音/通话为真）。若产品侧要求 TTS 期间全静默提示音，属规格变更，另行裁决。

## L7 · 模型用量不可精确归因
实现经 ZCode 代理会话（GLM-5.3-Flash）；宿主未暴露 token 计数接口，run_manifest 如实登记 NOT_EXPOSED，不伪造数字。

## L8 · q03 探针 JSON 的运行时刷新
q03 harness 测试会按需刷新 `v3-output/WT401-Q03-VISUAL/` 下探针 JSON 的时钟类字段（测试自落盘机制）。本卡运行后已 `git checkout` 还原，不携带非本卡漂移入提交（该目录归 Q03 所有）。

## L9 · 本地 main 领先本分支基线
作业期间本机 main 由他机推进（dce840da → b5872ce4，fleet 心跳/state 提交族）。本分支不追不并不 push；集成时按台账以 dce840da 为本卡基线，冲突预期为零（触达面无交集）。

## L10 · sfx 音量在 native SystemSound fallback 路径不生效（平台限制，一审 COND-3 登记补缺）
提示音音量的合成点（`spec.volume × sfxVolume`）只进 AudioPlayer pool 路径——真机/profile 的生产路径，调用级钉 0.22×用户音量。debug 期 native fallback（iOS/Android 模拟器稳定性考量）与播放失败诚实降级两条路径走 `SystemSound.play`，**系统点击无音量参数**（平台限制），sfx 音量在这两条路径不生效。不影响触觉与任务流；R1-C6 已在 review_receipt.json 披露，本条为 limitations 登记补缺。

