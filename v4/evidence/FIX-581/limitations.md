# FIX-581 limitations

- **L1 残留放行带**：0.5%–1.0% 带内的真实微回归在 CI 放行（本地签发机仍拦截）；终证依赖本地签发纪律。
- **L2 单实锚**：系数 2.0 依据唯一硬数据 0.62%；runner 镜像/Flutter 版本漂移若推跨机差过 1.0% 会再红——届时以新实锚重推系数（不改阈值基带）。终证条款=CI54 及后续自然轮 g01/g06/b04 golden 不再红。
- **L3 未观测档**：CI53 因失败中断，任务列表 dusk/quiet 与其他屏档的 CI 差未采样；1.0% 界按余量 61% 吸收。
- **L4 投递修复面**：TestFailure 归属修复覆盖 B04 家族比较器；其他自带比较器（golden_family_drift_guard 家族）若存在同型 throw FlutterError 形态未扫（未发现消费面，非已知缺陷）。
- **L5 lint**：卡内触碰点顺手消 2 个既有 lint（trailing comma）；未做任何无关文件 drive-by。
