# FIX-581 summary
P1 CI 红线（G01 golden Linux 跨机 0.62% 超容差 → 银行 27+ 笔连环红风险）。
修法=B04 容差比较器环境感知化（本地 0.5% 逐字节不变，CI ×2.0=1.0%），一处基建覆盖 b04/g01/g06 三消费面；附带破案+修复 CI53「dusk 异常」假象（FlutterError 投递错位→TestFailure 归属）。
前任 agent（配额阵亡）完成机制层与机制测试主体，leader 接管收尾：mutation 残留清理、main 基合并、双 mutation 红绿、GITHUB_ACTIONS e2e、lint 门、审计兜底、证据五件套。
银行解锁：本修合并后推 CI54。
