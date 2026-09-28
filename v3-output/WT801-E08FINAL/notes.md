# WT801 notes — E-08 验收级真模型复测（调用计数与实录）

> Worker wt801 ｜ 2026-09-28 ｜ worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt801-e08final` @ `cdc547be`（branch `agent/node-b/wt801/e08final`）
> 运行栈（只消费，零改动零重启）：引擎 gRPC :50051（PID 77460，2026-09-28 09:55:27 启，cwd=`/Users/brsama/code/GitHub/Sparkle-project/backend`）+ uvicorn :8000（PID 77527，09:55:33 启）+ 网关 :8080；sparkle_redis/db/minio 三容器 healthy（25h+）。栈代码 = 主干 `cdc547be`（轮#299 二次滚启激活 wt798 集成 + V3-FIX-507 接线）。
> 口径：与 wt372 基线（`a1418084`，2026-09-25，104 条）同构——引擎直连（gRPC StreamChat :50051 + :8000 guest JWT），同 harness（`scripts/devtools/bench_ai_stack_l0_l3.py`）、同 104 条语料、同切片。网关不进口径。

## 1. 真模型调用计数（硬预算 ≤150）

| 臂 | 调用数 | 留痕 |
|---|---|---|
| ① wt372 同构全量（L0-L3 26×4） | **104** | `raw-e08final.jsonl` 104 行，request_id 全部 `wt801-e08-e08final-*`；DB token_usage 归因 104/104 |
| ① 被杀孤儿（后台进程 50min 处 SIGKILL，L3-26 在途） | **+1** | DB 行 `wt801-e08-e08final-l3-26-d4fb97`（03:03:44Z，0 token 计量，客户端未落 raw）；resume 后 L3-26 重跑成功 |
| ② Q-06 缩减切片（free 车道，--reps 1 --limit 10 × 4 层） | **40** | `WT801-Q06-RETEST/raw-bench.jsonl`，request_id 全部 `wt801q06-*` |
| ③ keyless 首帧探针 | **0** | 24 样本均为 >2000 字符确定性校验拒收，LLM 零消耗（`evidence/ack_probe/`） |
| **合计** | **145 / 150** | 余量 5，未超预算 |

辅助面如实声明：L3 各条的隐藏辅助调用（Layer3 分类/sufficiency/HyDE/planning）与 wt372 同为 token_usage 计量盲区，无法逐条计数（E-01 C5 既有登记）；主生成面以上表 145 条为准。失败不重试：① 臂 0 error；② 臂错误如实落 raw。

## 2. 账号与环境实录

- 新建 bench guest（约束「新建 guest/bench 用户」）：① 臂 `wt801_e08_bench`（user_id `76c6fe42-a45e-4f41-88ca-cb344e2ef894`，DB 亲证 105 条 token_usage 全归因该用户）；② 臂 `wt801_q06_bench_free`/`wt801_q06_bench_pro`（本切片 40 条全 free 车道）；③ 臂 `wt801_e08_probe`。未触碰 ns001 与 `/tmp/northstar_ns001_real_drive_state.json`。
- harness 适配（最小 diff，默认行为不变，见 commit）：`bench_ai_stack_l0_l3.py` 与 `q06_perf_bench.py` 增加 guest / request 前缀 / q06 backend-root 与 gRPC 目标的环境变量覆盖。**测量逻辑零改动**；q06 从 wt406 专用（:50061）改为可指向常驻栈（:50051）。
- 已知模板瑕疵：`summary.md` 头两行（引擎 commit `0e4087ec`、guest 名）是 wt372 时代的硬编码模板文本——① 臂实际 guest 为 `wt801_e08_bench`（DB 亲证）、栈代码为 `cdc547be`。以本目录 notes/report 为准。
- summarize 首跑未带 E08_BENCH_GUEST 环境变量致模板 guest 名显示为默认值；数据文件（raw/csv/facts/issues）不受影响。

## 3. 运行实录

- ① 全量：10:11-11:02 串行 104 条（后台进程 50min 处被 SIGKILL，exit 137，已落 103 条；11:00 resume 补 L3-26 + enrich 104/104）。逐条 ttft/total 见 raw-e08final.jsonl。
- ③ keyless 探针：24 样本，first_frame_received 24/24，first_frame_is_early_ack_true 24/24，first_frame_stage_intake 24/24，t_ack mean 35.9ms / tail p50 36.9ms / p95 55.6ms；finish=ERROR(INVALID_ARGUMENT) 24/24（设计内拒收）。
- ② Q-06 缩减切片：启动 11:1x，`--layers L0,L1,L2,L3 --reps 1 --limit 10`，全部 free 车道（pro 车道证据由①臂 26 条 pro 承接，如实披露）。

## 4. 观察与诚实声明

- 103 对同 qid ack 配对中 102 对改善、1 对变慢：L0-01（353ms→400ms）——该条是全新 guest 的第一条请求，疑似冷启动（新建用户首查 bootstrap），仍 <500ms，不构成回归证据。
- E08-ISS-FALLBACK **换标签未解决**：修后 18 行 `no_generation_model` 中 7 行带 token（L3-06/08/15/18/21/23/26，与修前 7 条 default 带 token 完全同 qid 集）——多代理流计量错挂的本质缺陷原样持续，仅显式标记名从 `default` 换成 `no_generation_model`（`METERING_MODEL_NO_GENERATION`，V3-FIX-80 波次引入），summarize 不再将其计为 fallback，自动 issues 表面变干净。成本仍被低估（7 条计 $0）。同一缺陷，不占新号。
- tier 塌缩（E08-ISS-TIER-COLLAPSE）**实resolved**：修后计量分布 dashscope_fast 68 / dashscope_chat(plus) 12 / qwen3_8_max 5 / dashscope_standard_thinking 1——wt380 三因修复 + 507 接线后分层车道真实存在。副作用如实报告：deep/pro 臂真实打到 max/plus，L2 total p95 49.5→65.4s、L3 total p50 28.8→68.5s、成本 $0.0117→$0.1269——「分层成本/质量账本」恢复的同时深档延迟上行，是路由修正的真实 trade-off，不是退化事故。
- 动态 issues 对比含口径成分：8→3 的下降中，L2-FEEDBACK/L3-ACK/ERROR 为真实解决，FALLBACK 为换标签（见上），TIER-COLLAPSE 为真实解决。
- 未重启/未改运行栈；未改台账/tasks.json；未 push。
