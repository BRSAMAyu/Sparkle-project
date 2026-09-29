# FIX-579 limitations — 明示不主张面

1. **不主张全量 perf 阈值治理**：只修两例已证 flaky 断言；同模式候选（7 文件 A 类 +
   B 类 -D 逃生门族 + C 类内存预算）只登记于 perf_threshold_candidates.md，未经 CI
   红绿实证不动。
2. **容差的判别力代价（显式治理取舍）**：以典型 CI 值为基线，CI 侧 ~1.3–1.5x 以内的
   温和回归可能被 1.5x 容差吸收（105000/81496≈1.29、105000/70241≈1.49）；换取的是
   runner 噪声确定性（现状是随机红+人工 rerun）。真回归通常伴随本地余量消耗，本地严格
   界（×1.0 不变）仍是第一道门。
3. **检测面仅 `GITHUB_ACTIONS`**：GitHub 托管 runner 恒注入该变量；自托管 runner 若
   未注入则走本地严格口径（flake 源即托管共享 runner，口径一致）；本地误设该变量会
   放宽（属显式声明行为，非隐匿）。
4. **与 -D 逃生门的叠加语义**：`GALAXY_LAYOUT_100_MS`/`S01_SCROLL_FRAME_US` 等
   `int.fromEnvironment` 覆盖若在 CI 显式传入，容差将乘在该解析值之上
   （`base×1.5`）；当前 CI workflow 未传任何 -D（已核 ci.yml），默认值路径不受影响。
5. **未证 CI 上的行为**：本卡验证面=本地 3 连跑（严格界）、mutation（模拟 CI 参数
   红）、GITHUB_ACTIONS=true 进程级 e2e（检测缺省路径放宽界）；真实托管 runner 上
   的下一次自然运行才能闭掉「CI 稳定绿」最后一环——台账行按修法落地闭 FIXED，
   CI 观察归后续轮次（CI49/50/52 同位置复跑不再红即终证）。
6. **measurement 方法未升级**：本卡不改测量法（Stopwatch 墙钟、无 warm-up/多采样
   中位数），只做环境容差；测量法加固属 perf 测试基建卡范畴。
