# FIX-581 verification

## 修法（F579 kCiPerfTolerance 同型混合式）
- `kCiGoldenToleranceScale = 2.0`：CI 界 = 基带 0.005 × 2.0 = **1.0%**
- 推导：下界 scale≥1.24（0.62% 实锚）；1.5 余量仅 21% 且 dusk/quiet 暗档未观测；2.0 余量 61%，CI 粗门仍拦 ≥1.0% 布局崩坏（V3-FIX-383 判例 49% 量级）
- 检测：`GITHUB_ACTIONS` env（`b04RunningOnCi`）+ `ciEnvironment` 参数注入（机制测试模拟）；本地口径 `localTolerance` 缺省 0.005 逐字节不变
- 落点：`B04TolerantGoldenComparator.effectiveTolerance`——**一处基建层，B04 家族全覆盖**（b04/g01/g06 三消费面同享）

## 附带真修复：失败投递归属（CI53 dusk 异常破案）
- 原代码 `throw FlutterError(error)` 穿透 SDK `binding.runAsync` 的 reportError 通道（只 `on TestFailure catch`）→ 失败被吞进框架异常队列、`expectLater` 正常返回、错误被**下一轮迭代**的 `takeException()` 错位取走
- CI53 实证：paperDay golden 失败挂上「PixelPreviewProfile.dusk 任务列表异常」reason——dusk 本体无异常，纯投递错位
- 修复：改抛 `TestFailure` → 失败落在自己的 expectLater await 上；机制测试钉死（超带失败 takeException 保持 null + thrown isNot FlutterError）
- M2 mutation：回退 FlutterError 形态 → 红（错位归属断言命中）→ 还原绿

## mutation 双向
- M1：拔除 CI 分支恒本地口径 → 「CI 语义 0.62% 判过」红 → 还原绿
- M2：见上

## dusk 定性结论
**良性假象**（投递错位），非 dusk 档真实泵挂；无产品码缺陷。

## 本地口径零变化实证
- g01 golden ×3 连跑全绿（阈值行为与修前一致）
- 机制钉：`localTolerance=0.005` 常量钉死 + 同帧 0.62% 本地语义仍判挂（机制级红线实证）
- GITHUB_ACTIONS=true 进程级 e2e：真实检测路径执行且 g01 全绿
