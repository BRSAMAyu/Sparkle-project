# FIX-581 G 系 golden 比较器一致性审计（2026-09-30，@291618e4）

| 家族 | 文件 | 策略 | CI 风险 | 处置 |
|---|---|---|---|---|
| B04 容差家族 | b04_visual_baseline_capture / g01_four_style / g06_four_style | B04TolerantGoldenComparator 0.5% 带界 | g01 已红（CI53）；g06 在银行 | **本修覆盖**（effectiveTolerance 环境感知） |
| Linux 显式跳过 | v4_g02_family_golden_semantic（`_goldenCapable=!Platform.isLinux`）/ chat_golden / p2_07_i18n | skip: Platform.isLinux | 无 | 维持（签发机单侧覆盖，卡面登记口径） |
| env 门控 | emotion / notification / i18n_p208 / dashboard_golden | _enable* env 旗标，默认 skip 自述 | 无 | 维持 |
| 零 golden | g03（两测试文件 matchesGoldenFile=0）/ g05 家族测试 | 语义钉/对比度守卫 | 无 | 不适用 |

**兜底扫描**：全 mobile/test 含 matchesGoldenFile 且无任何保护（Platform/skip/Comparator/_enable/env）的文件 = **0**。
三口径并存裁定（Q08 侦察 §一）：B04 容差家族经本修升级为环境感知单标准；Linux-skip 与 env-gated 为签发机单侧覆盖的显式登记口径，不产生 CI 风险，维持不动（Q08 类裁决时可依本审计收口）。
