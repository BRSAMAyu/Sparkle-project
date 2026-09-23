# SIDECAR-JOURNEY · REPORT — Aurora 规划旁路 + fast-track 多轮续聊的真实路径旅程覆盖

- 卡：SIDECAR-JOURNEY（C 纵队 · 北极星评测线；wt190 ORCH-NEIGHBORS 范围外申报的承接）
- Worker worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt196`（基线 `95a0af3a`，含修复 `bef7ae07`）
- 交付物：本报告 + `changes.patch`（3 个新增测试文件，**零产品改动**）
- 日期：2026-09-23

---

## ① 两层测试的设计与断言面

被钉死的对象（wt190 修复，bef7ae07）：`save_session` 恒以 `planning:session:{user_id}:{chat_session_id}` 落键（planning_workflow.py:47,445-450），orchestrator 两处读取方 `_attach_aurora_planning_sidecar`（:427）与 `_fast_track_exam_sprint`（:731）必须带 `user_id` 读同一命名空间。回退 = 真实 Redis 下键恒 miss = 多轮旁路/续聊退化重新开场（wt190 前 9/10 失败的真实产品缺陷）。

### 第一层：单元/集成（真实键语义，调用点粒度）

`backend/tests/orchestration/test_sidecar_fasttrack_multiturn_keys.py`（5 用例）。设计取舍：不重复 `test_orchestrator_process_stream_integration.py` 已覆盖的 process_stream 管线断言，用 `ChatOrchestrator.__new__` 最小实例（只装配 `planning_workflow_manager` + `aurora_runtime_v1`）**直打两个被修调用点**，内存 Redis 桩（同 wt188/wt190 FakeRedis 惯例，无共享桩提取）。

| 用例 | 断言面 |
|---|---|
| `test_planning_session_persists_user_scoped_key_and_multiturn_resume_does_not_reopen` | manager 级三轮：T1 建会话（**精确键形制**：user 域键在、无作用域键不在）→ T2 离题 `{"bypass_planning": True}` 且状态/会话不推进 → T3 续聊命中**同一 planning_session_id**、信息被吸收、回复 ≠ 开场白；全程仅一把 planning:session 键 |
| `test_fast_track_second_turn_continues_session_without_reopening` | **调用点钉 #2**：T1 冲刺开场（内容帧 + 终端 STOP 帧 + `planning_fast_track=exam_sprint`）→ T2 续聊「把节奏调轻一点」必须读回 user 域会话走策略修订（回复 =「我按你的反馈把策略收紧了一版…」、≠ 开场白），会话 `PLANNING→AWAITING_CONFIRM`、planning_session_id 不变、仍只有一把键、`_persist_assistant_message` 恰 2 次 |
| `test_sidecar_attach_hits_user_scoped_key_and_mounts_once` | **调用点钉 #1**：离题轮 sidecar 挂载（`user_context_payload` 与 `state.context_data` 双面）、`source=aurora_decision_loop`、决策 `soft_return_topic`、scaffold 带潜线/开放张力；键命中以精确键形制断言 |
| `test_sidecar_reads_strictly_user_scoped_no_legacy_key_fallback` | 设计钉（wt190 裁决 B「拒绝双键兜底」）：只存在无作用域遗留键时 sidecar **不得读取**——跨租户安全优先 |
| `test_sidecar_and_fast_track_do_not_leak_across_users` | 多租户隔离：非属主同 session_id 既触发不了 sidecar 也续不进 fast-track；属主会话原样 |

### 第二层：旅程（API 级，引擎直调，全桩化）

`backend/tests/northstar_eval/sidecar_journey.py`（脚本，照 `real_drive.py` 风格：结构化证据 + verdict + 诚实边界随证据落盘）+ `test_sidecar_journey.py`（pytest 包装，使其纳入回归可跑集合）。

旅程：同一 user_id + session_id 连续三轮 `ChatRequest → ChatOrchestrator.process_stream`（gRPC API 级，即网关桥的真实入口签名）：

| 轮 | 话术 | 期望 |
|---|---|---|
| T1 `target_open` | 「7天后考计算机网络，没学过，每天2小时」 | fast-track 冲刺开场（Day0 建 target）：内容帧 `planning_fast_track=exam_sprint`、会话直达 `PLANNING`、Sprint Pack `computer_networks@v1` 预填、**user 域键命中**、sidecar 挂载 0 |
| T2 `digression` | 「等等，先帮我查一下这个任务完成没有」 | 规划离题：sidecar **恰挂载 1 次**（决策 `soft_return_topic`，图内可见）+ 通用链作答（桩文本） |
| T3 `return` | 「回到规划，把节奏调轻一点」 | fast-track **续聊**：策略修订回复「我按你的反馈把策略收紧了一版…」、同一 planning_session_id、`AWAITING_CONFIRM`、sidecar 总计仍 1 |

三条卡面断言点全部就地断言（失败抛 `JourneyCheckFailure` 携带观测进 evidence）：
**A1** 第二轮不重复 onboarding/开场（T2 回答 ≠ T1 开场且无 fast-track 元数据；T3 续聊非重开）；**A2** sidecar 全旅程恰出现一次且在 T2；**A3** 回归提问正常回答且会话延续。证据落 `/tmp/sidecar_journey/<run_id>/evidence.json`（默认 tmp，收工自清）。

---

## ② 实现清单（零产品改动）

| 文件 | 性质 | 内容 |
|---|---|---|
| `backend/tests/orchestration/test_sidecar_fasttrack_multiturn_keys.py` | 新增 | 5 用例，自包含（FakeRedis + `__new__` 最小编排器 + bottleneck 确定性 fallback 补丁） |
| `backend/tests/northstar_eval/sidecar_journey.py` | 新增 | 旅程脚本（`python3.11 -m tests.northstar_eval.sidecar_journey`）+ 可导入 `run_journey()`；`_Patches` 退出即还原模块补丁（脚本/pytest 两用） |
| `backend/tests/northstar_eval/test_sidecar_journey.py` | 新增 | pytest 包装：跑 `run_journey`，复钉 A1/A2/A3 + 证据结构契约 |

产品文件零改动（变异验证中短暂改动过 `orchestrator.py`，已 `git checkout --` 还原并核对 status，见验证记录）。

---

## ③ 冲突面声明

本卡 patch 仅含 3 个**新增**测试文件：`backend/tests/orchestration/test_sidecar_fasttrack_multiturn_keys.py`、`backend/tests/northstar_eval/sidecar_journey.py`、`backend/tests/northstar_eval/test_sidecar_journey.py`。逐个兄弟卡声明：

- **wt193（backend loguru 批量，54 个 `backend/app/**` modified + 新增 `tests/unit/test_loguru_exc_info_migration.py`）**：其实测清单（`git status` 核对）不含 `tests/orchestration/`、`tests/northstar_eval/` 任何文件，亦不含 `orchestrator.py`/`planning_workflow.py`；本卡 3 文件为新建且**不含任何 logging 语句** → 行级零重叠，patch apply 无错位风险。
- **wt194（纯研究）**：worktree `git status` 干净，无文件变更 → 零重叠。
- **wt195（mobile galaxy）**：改动域在 `mobile/**`；本卡不触碰 mobile → 零重叠。
- 本卡未触碰：产品代码、`proto/`、SQLC、`planning_workflow.py`、网关、`tests/unit/`、既有任何测试文件。

---

## ④ 诚实申报（mock 边界）

以下行为**本卡测试不可验证**，只能真实 LLM / 真实栈冒烟：

1. **回答质量与文案**：通用链回答是图桩确定性文本；策略修订/冲刺开场的文案为产品确定性模板（这部分是真实的），但 LLM 润色的旁路引导语气（`chat_directive.brief` 如何被 prompt 消化）不在覆盖内。
2. **Aurora 决策智能**：`decision_loop.decide` 为桩（固定 `soft_return_topic`）。sidecar 的**挂载路径、键命中、manifest 后写登记、detour scaffold 张力/潜线构造、apply_detour_decision 状态机**均为真实路径；「LLM 会不会在真实读出下选对动作」不是。
3. **多轮再回归的张力消解**：T3 走的是 fast-track 续聊策略修订；「回归后继续补齐 motivation 张力 → 再离题 → 潜线降权」的更长链路未覆盖。
4. **网关面**：鉴权、限流、WS 帧映射（done 事件）、移动端 done 收尾契约不在引擎直调覆盖内。
5. **确认词路径**：回归话术若含确认词（如「好」「可以」）会触发 `_handle_generating` 计划生成链（需真实 DB 落 Plan/Task）——旅程 T3 话术刻意避开（踩坑记录见验证节）。

**真实 LLM 冒烟申报（留主会话）**：无现成 live 命令（本卡不建 live 传输，无 .env）。建议主会话起栈后按 `sidecar_journey.py` 顶部旅程话术经网关 WS 以**同一 session** 驱动三轮并判定：T2 回答先接住任务查询并自然带回规划（`soft_return_topic` 语气）、T3 直接进入策略确认（不重新开场）、移动端三轮均正常 done 收尾。若需脚本化可立下轮卡：给 sidecar_journey 加 gateway transport。

---

## 验证记录（同环境同命令）

环境：worktree 内拷入主仓 `backend/app/gen/`（gitignored 产物，proto 与基线 diff 为空，md5 惯例同 wt190），留 worktree 随回收、不入 patch。

| 命令（均在 `backend/` 下，`SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" python3.11 -m pytest … --timeout=120`） | 结果 |
|---|---|
| wt190 修的三文件（改动前基线） | **76 passed**（25+33+18，与 wt190 申报一致） |
| 新增单元/集成层 | **5 passed**（2.2s） |
| **变异验证**：单文件还原 wt190 修复（两处 `get_active_session` 去掉 user_id）→ 跑新增层 | **恰 2 个调用点钉变红**（fast-track 续聊钉 + sidecar 挂载钉），3 个设计/隔离钉如预期保持绿 → `git checkout -- orchestrator.py` 还原 → 5 passed；status 前后核对仅 1 文件进出 |
| 旅程脚本 dry-run（`python3.11 -m tests.northstar_eval.sidecar_journey`） | `verdict=pass`，A1/A2/A3 全 true，T1/T2/T3 观测见 evidence（T2 `sidecar_mounts_total=1`、`sidecar_action=soft_return_topic`；T3 策略修订帧 + `AWAITING_CONFIRM`） |
| `tests/orchestration/` 全目录（对比法） | **199 passed, 0 failed**（= 基线 194 + 新增 5，零新增失败，38.9s） |
| `tests/northstar_eval/` 目录（与 wt189 资产共存） | **61 passed**（含本卡包装 1 用例）, 0 failed |

**踩坑记录（对后续旅程测有用）**：回归话术初版「**好**了回到规划，把节奏调轻一点」中的「好」命中 `PLANNING_CONFIRM_PATTERNS`，经 sidecar→fast-track 两次 `process_planning_turn` 直接触发 `_handle_generating` 计划生成链（db=None 下必然失败回退通用链）。已改为无确认词的「回到规划，把节奏调轻一点」。这同时佐证：**含确认词的回归 = 生成计划路径**，是真实用户旅程的另一条分支，留待有 DB 的旅程覆盖。

---

## ⑤ 收工核查

- [x] 禁止 commit/push：未执行（HEAD 仍 `95a0af3a`；`git status` 仅 3 个新增测试文件 + 未跟踪 `v3-output/SIDECAR-JOURNEY/`）
- [x] 零凭据：未读未拷未建 `.env`；测试无任何密钥/密码；Redis 仅以内存桩出现
- [x] tmp 清理：`/tmp/sidecar_journey_dryrun/` 已删；无其他 tmp 产物
- [x] 无遗留进程/模拟器/Docker 变更；全部验证为进程内（sqlite memory + 内存桩），零外部依赖写入
- [x] 变异实验合规：单文件（orchestrator.py）粒度改动 + `git checkout --` 还原，前后 `git status` 比对
- [x] 资源纪律：全程单 pytest 进程定向跑（无宽扫描），最长单命令 38.9s（全目录），无 HEAVY 操作；`grep` 用 `/usr/bin/grep`，命令显式 cd，每命令带 `--timeout`
- [x] `backend/app/gen/`（gitignored）系主仓同基线拷入（proto 与基线 diff 为空佐证有效），留 worktree 随回收，不入 patch
