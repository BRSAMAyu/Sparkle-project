# Rule AR - CL Component Quality Assessment Matrix Governance

1. 所有 Aurora 持续学习组件必须显式声明 `ID1 / ST1 / DP1 / SM1` 四个 SQAM 维度。
2. 每个组件必须至少有一个对应的 Stage guard，并由 `scripts/stage32/run_sqam_suite.sh` 收敛执行。
3. SQAM guard failure 视为 block 级，不得合并。
4. 运行时告警必须复用既有 Prometheus 指标；无法表达的维度只能做代理告警，不得偷偷新增高基数指标。
5. PII 脱敏、格式校验、差分隐私工具函数属于 SQAM 范畴，不得以后补为由跳过。
6. Kill switch 必须能按组件独立关闭，不得把一个 CL 组件故障扩散到其他组件。
7. 新增 CL 组件必须先提交 SQAM 规格与 guard，再进入 merge。
8. 跨用户聚合产物必须使用 `laplace_noise(..., epsilon<=0.3)` 或经 Rule Z 允许的哈希/HMAC 处理；单用户自查保持精确。
