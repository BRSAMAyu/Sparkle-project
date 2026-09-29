# FIX-583 limitations（边界、未决与如实登记）

## 1. 挂死 await 的行级定位未取得

Q01 锁快照记录的僵尸末语句 `SELECT user_push_opt_in...` 与当前代码
`start_hybrid_journey` 调用树静态不匹配（全仓该表查询点仅在 push/preference
服务链，不在本链路）。两种可能：(a) 该语句来自同进程并发连接（Q01 栈同时
服务整个集成测试面的轮询/推送请求），快照记录者未区分连接；(b) 存在经动态
分发（服务内部 import / 事件钩子）进入本链路的路径，静态扫描未覆盖。macOS
无 root 无法 py-spy 取栈，行级归因**未决**。本卡的结构定性不依赖它：无论挂
哪个 await，修前形态都是「prep 重活 + 开放请求事务 + agent_runs 行锁绑定在
请求生命周期上」，三件套修复对任意挂点均成立（超时封顶 + 会话解耦 + 僵尸
回收）。真端复测（Q01 栈保持运行）是最终裁决面；若修复后真端仍挂，R1 应
补 py-spy（sudo）取栈定位到行。

## 2. `asyncio.wait_for` 的理论边界

若挂点位于**不可取消**的 await（C 扩展 / shield / 吞 CancelledError 的循环），
`wait_for` 在取消收尾时可能仍不返回——该极端下挂起仍会占住工具自己的那条
池连接。但此时：请求会话零事务零行锁（不钉其他请求）、run 经僵尸启动自检
在用户下次点击时被回收（不钉旅程）。「连接占用」的最终兜底是进程重启 /
连接池回收，超出本卡范围，如实登记。

## 3. 同构暴露面核查结果（非遗留）

`submit_judgment`（段3）核查：全文件唯一 `execute_tool_call` 就是 prep（583 行
一处）；judgment 段的 LLM 起草本就带 `wait_for(_LLM_TIMEOUT_SECONDS=12s)` 显式
超时（`JourneyGenerationError("llm timeout")`），且无工具执行——无「工具账本写
滞留请求事务」形态。本卡的同类暴露面只有 start 链路一处，已全部修复；judgment
段不需同款修法（此前的假设性登记在此更正）。

## 4. 僵尸回收阈值 15min 的取舍

`PREP_ZOMBIE_AFTER_SECONDS = 15 * 60`：prep 正常 4s、显式超时 20s，15min 是
40 倍以上的保守余量——既保证网络抖动/慢检索绝不误伤（对照 MUT-C 反向钉），
又把用户可见解除窗口从全局 sweep 的 6h 缩到「下一次点击」。不做成 settings
旋钮：本卡无调参需求，少一个配置面少一个漂移面。

## 5. 测试面的既知边界

- 回归是 pytest + sqlite（StaticPool）级：sqlite 无真行锁/连接池语义，
  「锁钉死」的 PG 级行为无法在单测层完整复刻——测试钉的是**结构合同**
  （会话归属、调用时刻事务态、超时封顶、补偿终态、幂等语义），真锁图以
  Q01 原证据 + 修复后真端复测为准。
- `test_j06_hybrid_journey.py` 的历史非 black-120 格式保持原样（HEAD 版本
  本就不被当前 black 接受）；本卡只 +3 行并保持文件既有风格，不扩大 footprint。
- proto 生成产物（`backend/app/gen/`）在本 worktree 缺失，为跑测试以
  `PROTO_USE_DOCKER=0 make proto-gen` 本机重建；产物 gitignored，未入库。

## 6. 未做

- 未 push（红线）；未触碰运行中的 Q01 栈（gRPC 50051/8000/8080 保持，供 R1
  复测）；未起真栈做端到端复测（无真模型凭据窗口，pytest 级交付）。
- 网关侧「该路由放长代理超时」的 Q01 备选建议**未采纳**：30s 窗口是合理
  产品口径，修法应让后端在窗口内确定性应答（本卡已做），而非放长超时。
