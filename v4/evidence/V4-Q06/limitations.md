# V4-Q06 · 已知限制

## L1 · 无物理设备：真机硬件面全量 DEVICE_UNVERIFIED（卡面边界如实标注）

本机（darwin 25.6.0 arm64）**无任何物理 iOS/Android 设备接入**（`xcrun simctl` 仅 iOS 模拟器镜像；无 adb 设备）。因此：

- **触感舒适度**（强度感知/时延/「拒绝每步都震」的克制主观感）——未测。S03-L1 的真机面归口由本卡承接，本卡同样无真机可测，继续向后顺延；任何「触感好/自然」的表述仍无证据位。
- **真扬声器听感**（提示音响度/双音柔和度/duck 与 fade 听感）——未测。S02-L1 同口径顺延。
- **真实 OS 音频中断事件源**（系统来电、耳机拔出的平台事件接线）——未接。S02-L2/L3：状态机迁移与恢复语义调用级 PASS（本矩阵 M-R9-C4 复验），但仓库无 telephony/audio-session 类插件，接线归平台通道 owner；「来电后恢复播放」在真机上的实际行为=DEVICE_UNVERIFIED。
- **iOS/Android 模拟器 App 安装运行面**——NOT_RUN（如实登记，非冒充）：本卡全部可验证面（决策/门控/通道调用）在 flutter test 层已全覆盖且模拟器上同样只有调用级可观测（模拟器无震动马达、无听感判断位、事件生产链未接线无可跑流量）；叠加 HEAVY 磁盘约束（数据卷余 6.7Gi）与无新可证增量面，未执行模拟器构建安装。若审查判「模拟器 App 层必须跑」，属 L3 补测面，本矩阵套件可原样作为复验工具。

## L2 · C4 列（background）事件链可见性门 = GAP_INTEGRATION（缺口登记，不伪造 PASS）

MOTION 核心合同要求适配器「按当前用户偏好、平台能力、**应用可见性**和证据新鲜度选模态」，乐谱同步与安全行要求「foreground→background 立即停止装饰」。现状：

- **既有装饰停止面 = PASS**（调用级）：`AnimationLifecycleMixin` 生命周期回调暂停/恢复在航动画控制器（M-R1-C4 widget 级实测）；BGM 服务生命周期观察者暂停/恢复（bgm_service.dart `_BgmLifecycleObserver`，源码锚）；音频焦点 STOPPED_BY_USER 不自续（M-R9-C4）。
- **缺口**：`ExperienceFeedbackAdapter.present()` 无可见性入参；`SensoryFeedbackService.emit()` 无可见性门；环境床无 App 级生命周期观察者（仅 BGM 有）。当前无实际后果的唯一原因是**生产事件源未接线**（适配器现网零流量，S03-L5/D01/B05/FIX-569 登记过的 contract-owner 面）。
- **归属**：接线（事件源 + 可见性门）归集成链 owner 单独合并（契约面纪律）；本卡为验证卡不越权补实现。9 个 C4 格逐格标注 GAP_INTEGRATION；矩阵套件接线后零改动可复验。

## L3 · 模拟器层证据口径（与 S 线同口径）

「0 次/恰一次/抑制原因」类数字全部是 flutter test 内注入记录器与 `SystemChannels.platform` mock 的通道调用实录（可失败可复现），不是真机振动/发声实录。`SensoryFeedbackService` 在 debug+移动目标下的 native SystemSound fallback 路径使提示音证据为「通道调用计数」而非资产播放听感（S02-L10 同口径：sfx 音量在该路径不生效，平台限制）。

## L4 · 平台策略注记（非本环境可测，不绕过）

Android API<30 的 success/warning notification 触觉由平台设计为无效果（SDK 文档明示）；iOS<10 impact 生成器同理。本卡不蜂鸣替代、不做版本分叉（S03-L1 注记顺延）；「supported 平台上低版本系统实际无感」属平台行为，真机面实测时按 OS 版本分层记录。

## L5 · 偏好缺省变更的用户可见影响（S02-L4 顺延确认，非本卡变更）

提示音缺省关/背景声缺省绝对关为 S02 按 V4 规格落地的行为差量；本矩阵 M-R9-C1/C6 复验其在回归进入面的表现（未点播零自动播放）。存量用户升级后听不到操作提示音（显式开启即恢复）——归属 S02 已登记面，本卡无新变更。

## L6 · main 漂移与租约

- 作业期间本机 main 由他机推进（f13a21ef → 04b97fbe，U02 收口族）。本分支不追不并不 push（卡面明令「不要 push」）；触达面 = 1 新测试文件 + 证据目录，与他卡在航面零交集，冲突预期为零。
- `sparkle-coordination-v2` 私有远端未配置于本机（git remote 仅 origin，S01/S02/S03 同状），qa-sensory 锁租约登记 NOT_RUN；冲突面以 diff 自证。

## L7 · 模型用量不可精确归因

实现经 ZCode 代理会话（GLM-5.3-Flash）；宿主未暴露 token 计数接口，run_manifest 如实登记 NOT_EXPOSED，不伪造数字。

## L8 · 证据文件为最终文件状态复跑

矩阵套件首跑后修复了两处测试装置缺陷（通道记录器跨用例计数泄漏；事件构造器 receiptRef 哨兵语义），其间一次尾逗号风格修复（dart fix，零断言变化）。raw/matrix_machine.jsonl 为**最终文件状态**的复跑实录（58/58，exit 0）；修复过程对本卡结论无影响（全部为装置侧），如实登记避免「挑跑次」质疑。
