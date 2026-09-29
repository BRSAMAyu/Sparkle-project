# V4-S03 — limitations

## L1 · 真机触感舒适度 DEVICE_UNVERIFIED（卡验收 3 的第二层结论）

本环境无 iOS/Android 物理设备接入。模拟器/测试环境证据只覆盖**调用级**（通道调用计数、模式选择、门控分支），真机触感的舒适度、强度感知、时延与「拒绝每步都震」的主观克制感均未测。全量真机能力矩阵与舒适度判据归 V4-Q06；在此之前任何「触感好/自然」的表述都没有证据位。平台自身行为注记：notification 触觉在 Android API<30 由平台设计为无效果（SDK 文档明示），iOS<10 的 impact 生成器同理——这些是平台策略，不是本卡可测或应绕过的面（不蜂鸣替代）。

## L2 · 硬件/系统能力探测边界

`resolveSparkleHapticCapability` 只能判定**平台目标**（iOS/Android 支持，桌面/web 不支持），不能探测：系统级「触觉反馈」总开关（Android 设置项/ iOS 系统触觉）、硬件震动器存在性（无马达设备）。这两层由 OS 在引擎内执行调用时自行 no-op——本卡诚实口径：应用层门=偏好+平台目标；系统层尊重=调用即尊重（系统关则系统不震），模拟器证据不覆盖该层。macOS 触控板 haptic（NSHapticFeedbackManager）按保守侧判不支持，留真机面证实后再入表。

## L3 · V3 路径保留（非本卡改写面）

V3 `SensoryFeedbackService` 的 UI 词表触觉映射（含成就 epic/legendary 双脉冲=自定义组合脉冲）按卡 rollback 条款「保留 V3 路径与数据向后兼容」原样保留——V3 已 DONE 快照继承，V4 不重写。该双脉冲与新锁面「不造自定义震动语言」的张力登记在案：V4 语义面（experience_event 呈现链）已全部经锁面；V3 词表面是否收敛归后续 V4 收口裁决（需动 V3 行为的证据与授权，本卡不越权）。在航 S02 与本卡零文件交集；其合并后如触及 sensory_feedback_service 音频区，与本卡无冲突（触侧出口已在适配器分离）。

## L4 · nativeHandled 为调用点纪律 + 去重窗兜底（非全 app 双震清零声明）

「native已有反馈避免双震」的机制=请求位（具名抑制 nativeFeedbackAlready，E 组钉死）+ 同槽 500ms 去重窗（系统兜底）。当前生产消费面（F03 适配器默认出口）不落在原生触觉控件上，恒传 false。**尚未**对全 app 的 Material 控件调用点（enableFeedback 按钮、选择器滚轮、CupertinoSwitch、文本选择等）做逐一「已有系统触觉处不叠加」审计——那是对既有 V3 调用点的行为审计面，不在本卡触达范围；去重窗保证即使漏标，同槽短窗叠加也不会双震。本卡不冒充「全 app 双震已清零」。

## L5 · F03 事件源接线仍空（继承自 F03 的集成链事实）

适配器是唯一事件入口，但生产 WS 侧事件源（ExperienceEventFrame proto 增量下发）尚未接线——这是 D01/B05 limitations 登记过的 contract-owner 面（FIX-569 所在集成链）。本卡触侧升格只改变「出口之后」的路径；「入口之前」无生产流量 = 本卡门控在现网只被测试流量 exercised。集成后 Q06 全感官矩阵按真实流量复验。

## L6 · 证据口径

「2 次/0 次/恰一次」类数字均为 flutter test 内 SystemChannels.platform mock 的通道调用实录（可失败可复现），不是真机振动实录；跑分/时长类数字本卡不产（无性能面主张）。worktree 治理：gen 目录为复制件（gitignored），q03 harness 运行再生的 v3-output probe JSON 已还原——本卡 diff 恒为 2 新文件 + 1 适配器触侧出口改。
