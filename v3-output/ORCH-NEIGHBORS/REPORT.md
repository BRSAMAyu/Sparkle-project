# ORCH-NEIGHBORS 报告：编排相邻域存量 10 败诊断与修复

- Worker：wt190（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt190`，基线 de9b5637）
- 交付：`v3-output/ORCH-NEIGHBORS/changes.patch`（4 文件，+37/−13）+ 本报告
- 纪律：零 commit/push；零凭据
- 结论速览：**10 败 ≠ wt188 的 Redis-NOAUTH 根因**（卡面猜测被证伪）。真根因有两个：
  **R1（9/10）`PlanningWorkflowManager` 会话键读写错位——产品缺陷**（orchestrator 两个读取方不带 `user_id` 读 user 前缀键 → 恒 miss，Aurora 规划旁路 sidecar 与 fast-track 多轮续聊在生产 Redis 下是死码）；**R2（1/10）C-06 语义升级后测试未跟**。修复后 **三文件全绿 + `tests/orchestration/` 全目录 194P/0F**（基线 10F/184P → 零新增零残留）。

---

## 0｜卡面勘误（路径对账）

- 卡面 `process_stream_integration` = `backend/tests/orchestration/test_orchestrator_process_stream_integration.py`（25 用例，6F）；`planning_workflow` = 同目录 `test_planning_workflow.py`（33 用例，3F）；`round1_p2` = 同目录 `test_round1_p2_fixes.py`（18 用例，1F）。与 wt188 报告 §相邻域对比法的 10F 名单逐条一致。

## ① 基线失败清单 + 根因分布

复现命令（同环境同命令，修复前）：

```
cd backend && SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
  python3.11 -m pytest tests/orchestration/<file> -q
→ process_stream: 6 failed, 19 passed ｜ planning_workflow: 3 failed, 30 passed ｜ round1_p2: 1 failed, 17 passed
→ 全目录：10 failed, 184 passed（与 wt188 收工时基线逐条一致，确认纯存量）
```

| # | 测试 | 失败点 | 根因 |
|---|---|---|---|
| 1 | `test_process_stream_fast_tracks_exam_sprint_before_sufficiency` | :710 `assert persisted is not None`（None） | R1+R1'（测试读键也不带 user；另叠终端帧漂移见 :715） |
| 2 | `test_process_stream_modeling_complete_fast_track_returns_launch_route` | :777 `metadata["plan_id"] == ''` | R1'（仅终端帧漂移） |
| 3 | `test_process_stream_planning_bypass_injects_aurora_sidecar_prompt` | :864 `KeyError: 'source'`（sidecar 未挂载） | R1（产品 :425 不带 user 读 → sidecar 恒 miss） |
| 4 | `test_process_stream_planning_sidecar_does_not_reask_resolved_information` | :946 `assert None == 'time_available'` | R1（同上） |
| 5-6 | `test_process_stream_planning_sidecar_supports_wait_and_drop_thread_actions[wait]/[drop_thread]` | :1048 `assert None == 'wait'/'drop_thread'` | R1（同上） |
| 7 | `test_irrelevant_message_during_clarifying_bypasses_without_advancing_state` | :845 `assert None == {'bypass_planning': True}` | R1''（测试用两个不同随机 user_id 建会话/发当轮 → user 前缀键必然 miss） |
| 8 | `test_relevant_message_during_clarifying_advances_turn_counter` | :886-888 同型 | R1''（同上） |
| 9 | `test_exam_sprint_fast_track_single_message_enters_planning_with_pack_prefill` | :921 `assert persisted is not None`（None） | R1'（测试读键不带 user） |
| 10 | `test_rb07_empty_summary_falls_back_to_compression` | :251 `assert '压缩 6 条普通消息。' is None` | R2 |

**根因分布：R1 家族 9/10（其中 4 个纯产品缺陷、3 个测试侧读键同型错、2 个混合），R2 1/10。与 wt188 的 Redis-NOAUTH/fixture 漂移零交集**——wt188 报告 §范围外观察第 2 条「其失败不涉 Redis 认证」与本次诊断吻合；三文件本就全程走内存桩（`_MemoryRedis`/`FakeRedis`/`_PrunerRedis`），环境无关、任何机器确定性复现。

### R1 机制链（单一事实链，两处表现）

`save_session`（planning_workflow.py:445-450）**恒**以 `{user_id}:` 前缀写键：`planning:session:{user_id}:{chat_session_id}`（`create_session` 必填 `user_id`，无任何无前缀写入方）。而 orchestrator 两个读取方：

- `_attach_aurora_planning_sidecar`（:425，现 :427）`get_active_session(session_id)` —— 不带 user → 读 `planning:session::sid`（空 user 槽）→ **结构性 miss**；
- `_fast_track_exam_sprint`（:727，现 :731）同型 miss。

后果（生产语义，非测试artifact）：Aurora 规划旁路 sidecar（离题引导/追问去重/wait/drop_thread）与 exam-sprint fast-track 的多轮续聊判定，**在真实 Redis 下永远找不到既有规划会话**——首轮可用，第二轮起全部退化为「重新开场」。旁证：`tests/unit/test_aurora_runtime_decision_loop.py:1207-1212` 的注释早已记录同一事实链（「suspected product bug in orchestrator.py L415/L710，see V3-FIX-19 report」）并在测试里绕行；V3-FIX-19/REPORT.md:97 有完整同款事实链。**本卡把该「已申报未修」的产品缺陷修掉，旁路测试随之转正。**

R1' 与 R1'' 是同一错位在测试侧的镜像：3 处 `get_active_session(sid)` 读断言不带 user（同型错）；`test_planning_workflow.py` 两个用例用 `session.user_id=str(uuid4())` 与 `turn_user_id=uuid4()` **两个不同随机身份**建/读会话（作者笔误级，意图显然是同一用户）。

另一独立子因（#1/#2 叠加项）：63ca1517（2026-09-23，基线内）给 fast-track 补发**终端 done 标记帧**（空 metadata，移动端 WS done 契约，见 orchestrator.py:816-825 注释），`responses[-1]` 语义从内容帧变为终端帧，两测试未跟进。

### R2 机制链

RB-07 原语义「空 LLM 摘要 → 二层截断，`summary: None`」被 C-06（960bc498，晚于本测试文件最后改动 d3225a61）升级为「回落确定性 compaction，返回 compaction 诚实摘要（`压缩 N 条普通消息。`，conversation_compaction.py:355-362）」。测试仍钉住旧输出形状。**产品是对的**（compaction 摘要比 None 更诚实且中间消息不静默丢——测试的第二断言 kept≥50% 在新路径下依然成立），测试过期。

## ② 修法与裁决链（wt188 同款三候选）

| 候选 | 裁决 | 理由 |
|---|---|---|
| A. 全部按测试过期改测试 | **否** | #3-6 四个用例的失败在产品侧：sidecar 恒 miss 使被测特性（旁路引导）不可达，测试改不动——它们断言的是 sidecar 挂载效果而非读取姿势。git 考古：planning_workflow.py 自初始 commit 1722e6dc 零改动、读写键错位自始存在（clean-slate 仓库无更早历史可归因「回归」）；V3-FIX-19 已按产品缺陷申报。FLEET-BRIEF 语义（诚实性/多轮旅程真）判定：**user 前缀键是正确设计**（session_id 由客户端供给，无 user 隔离则跨用户碰撞），该修的是不带 user 的读取方。 |
| B. 改 `get_active_session` 兜底扫描/双键读 | **否** | 扫描兜底掩盖契约、多租户下有越权读风险；双键读制造双写真相。两调用方作用域内**本就有** `user_id`，补传是零设计变更的最小修复。 |
| C. 产品 2 行补传 user_id + 测试侧读键/身份对齐 + rb07 按 C-06 语义更新（**采纳**） | **是** | 产品侧：仅当「写入了的会话」从不可见变可见，首轮行为与全部既有绿测试不变（全目录 194P 对比法验证）。测试侧：#1/#7-9 改为与写入方一致的读键/同一用户身份（测试意图不变，断言一行未放松）；#1/#2 叠加项按本文件既有惯例（:1308 terminal_frames 过滤法）面向内容帧断言、终端帧单独验 finish 契约；#10 按现行为更新输出形状断言，保留 kept≥50% 核心意图。 |

修法一句话：**orchestrator 两个 `get_active_session` 调用补传作用域内现成的 `user_id`（各+2 行注释）；5 处测试读键/身份对齐写入方；2 处 fast-track 断言改面向内容帧；rb07 摘要断言从钉 `None` 改为钉 C-06 compaction 摘要。**

## ③ 实现清单

| 文件 | 改动 |
|---|---|
| `backend/app/orchestration/orchestrator.py`（+6/−2） | 仅两处：`_attach_aurora_planning_sidecar` 与 `_fast_track_exam_sprint` 的 `get_active_session(session_id)` → `get_active_session(session_id, user_id)`，各带 2 行动机注释。无其他产品改动。 |
| `backend/tests/orchestration/test_orchestrator_process_stream_integration.py`（+15/−3） | #1：读键带 `request.user_id`；metadata 断言面向 `full_text` 内容帧、终端帧验 STOP+session_id。#2：`final_response` 改取内容帧；补终端帧 STOP 断言。其余 23 用例零改动。 |
| `backend/tests/orchestration/test_planning_workflow.py`（+11/−7） | #7/#8：`owner_user_id` 单一身份贯穿 save 与 turn；`get_active_session` 带 user 读。#9：读键带 `user_id`。其余 30 用例零改动。 |
| `backend/tests/orchestration/test_round1_p2_fixes.py`（+5/−1） | #10：`summary is None` → 断言非空且含「压缩」（C-06 compaction 摘要）；kept≥50% 断言原样保留。其余 17 用例零改动。 |

无共享桩提取：三文件各自的内存桩（`_MemoryRedis`/`FakeRedis`/`_PrunerRedis`）本就够用且本次无一需要扩面——本卡未新增任何桩代码（与 wt188 的 FakeRedis 惯例同域但无共享必要，不强行共享）。

## 验证（同环境同命令红→绿 + 对比法）

```
修复前：三文件 6F/19P、3F/30P、1F/17P；全目录 10F/184P
修复后：三文件 25P、33P、18P（全绿）
  全目录 tests/orchestration/：194 passed, 0 failed（=184+10，失败名单逐条消失、零新增）
旁证定向：tests/unit/test_aurora_runtime_decision_loop.py 91 passed（其注释所述疑似缺陷即本次修复项）
```

## ④ 冲突面声明

本卡 patch 触及 4 文件：`backend/app/orchestration/orchestrator.py` + `backend/tests/orchestration/` 下 3 个测试文件。

- **wt178（mobile）**：其 worktree 实测改动全在 `mobile/lib`、`mobile/test` → **零重叠**。
- **wt180（event_bus+网关）**：本卡未触碰 `app/signals/`、event_bus、`backend/gateway/` 任何文件 → **零重叠**。
- **wt187（全仓 loguru 批量）**：其 worktree 当前不存在（已合入/回收）。本卡改动行（2 处 `get_active_session` 调用 + 4 行注释 + 测试断言）**不含任何 logging/loguru 语句**；即便该批后续重放触及同文件其他行，hunk 上下文互不重叠（相距数百行），apply --3way 无错位风险 → **行级零重叠**。
- **wt189（tests/northstar_eval 新增）**：其文件在 `backend/tests/northstar_eval/`（新增目录），与本卡 3 个既有测试文件零交集；orchestrator.py 非其范围 → **零重叠**。
- 本卡未触碰：`planning_workflow.py`（产品）、`context_pruner.py`（产品）、`conversation_compaction.py`、`proto/`、SQLC、`state_manager.py`。

## ⑤ 收工核查

- [x] 禁止 commit/push：未执行（`git status` 仅 4 个 modified 文件 + 未跟踪 `v3-output/ORCH-NEIGHBORS/`）
- [x] 零凭据：报告与 patch 无密码/密钥；`.env` 未读未拷未建（Redis 仅以「存在性」出现在历史申报引用中）
- [x] tmp 清理：`/tmp/orch-neighbors-changes-wt190.patch` 已删（内容即交付 patch）；无其他 tmp 产物
- [x] 无遗留进程/模拟器/Docker 变更；全部测试为进程内（sqlite memory + 内存桩），零外部依赖写入
- [x] `backend/app/gen/`（gitignored）系主仓同基线拷入（md5 逐文件核对一致），留 worktree 随回收，不入 patch
- [x] 资源纪律：全程单 pytest 进程定向跑（无宽扫描），单文件最长 40s，无 HEAVY 操作

## 范围外观察（申报给主会话，未动）

1. **orchestrator.py:425/:727 修复的生产验证建议**：该修复让 sidecar/fast-track 多轮续聊首次真正可达（此前生产即死码）。建议下一轮 C 线旅程测（TOUR/CP-04~08）覆盖「规划中途离题→旁路引导→回到规划」与「考试冲刺第二轮续聊」两条真实用户路径。
2. `tests/unit/test_aurora_runtime_decision_loop.py:1207-1212` 的绕行注释（「suspected product bug」）现已被本次修复证实，可择机把注释改为指向本卡；非必须，未动。
3. `test_orchestrator_process_stream_integration.py` 内 `_MemoryRedis` 缺 `lrem`/`incr` 等方法仅触发降级 warning（spine 信号检查 degraded），不影响断言；若未来有断言依赖 spine 信号，需扩桩。未动。
