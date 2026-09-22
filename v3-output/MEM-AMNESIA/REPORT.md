# MEM-AMNESIA：跨会话记忆失忆修复报告

> 2026-09-22 ｜ Worker：wt97（wt97-v3，基于 main@fdd827ee）｜ 交付：`changes.patch` + 本报告
> 证据基线：`v3-output/NORTHSTAR-LOOP1/REPORT.md` BP-2 + `evidence/`（B1、C2、C7a、D2、probe-gp07、gp-07-*-rejudged）

---

## 1. 根因一句话

**用户在 Day0 对话中明示的备考事实（科目/截止/弱点/目标/时间约束）被记忆写入管道的三道门禁逐级吞掉，从未进入跨会话 episodic 存储；召回侧本身没有断。**

## 2. 断点定位（file:line，修复前坐标）

沿「chat 消息 → 事实抽取 → episodic 写入 → 下次会话注入」全链路实测（含对 B1 原句的离线复算）：

| # | 断点 | 位置 | 机制 |
|---|---|---|---|
| ① | 「N 天后」不可解析 | `backend/app/services/commitment_parser.py:84`（`parse_commitment_due_at`） | 只有「N 天内」分支，无「N 天后/天后/天以后」；B1 首句「离散数学期末考试在 7 天后」due_at=None → `_looks_like_commitment` 判假、extract_candidate 对 commitment+due_at None 整条放弃 |
| ② | 单句候选置信不过 L1 直写门 | `backend/app/services/memory_inferred_write_lane.py:509`（`MEMORY_INFERRED_MIN_CONFIDENCE=0.9`，config/settings.py:858） | 规则启发式对 B1 中段弱点句只给 0.79（无时间锚不加时序分）；fallback 直写路径按 below_threshold 丢弃。实测复算：`extract_candidate` 产出 subject=self, confidence=0.79 |
| ③ | working-memory live 路径永不固化单次声明 | `backend/app/services/working_memory_consolidation_service.py:69`（`should_consolidate`，修复前行号） | 默认 `AURORA_STAGE19_WORKING_MEMORY_MODE=live`（settings.py:252），候选只进 session 级 Redis 工作记忆（`working_memory_pipeline_service.py:62-77`）；提升需 commitment+due_at、显式「记住」口令、或 mention_count≥3 且跨度≥60s。onboarding 一次性声明三者全不满足 → 随会话消亡 |
| ④ | 同轮多事实互撞 | `backend/app/services/memory_inferred_write_lane.py:627-630`（`_is_duplicate`，修复前行号） | 去重条件为 `evidence_token 相同 OR semantic_key 相同`——Day0「一句一事实」的多句声明共享同一 turn token，第一条写完后其余全部误判 duplicate |

**链路事实**：turn-end 直采（`orchestrator.py:1096` `_write_turn_end_episodic_memory`）只覆盖 task_completed/aurora/error 三类事件；普通聊天轮 fallback 到 `MemoryInferredWriteLaneService.enqueue_from_chat_turn`（orchestrator.py:1160-1172）——链路存在、是同步外的 fire-and-forget 后台任务（非 celery），但候选如上被吞。episodic 快照只剩 1 条 task_outcome（C4e 任务完成直采）与证据完全吻合。

**召回侧无罪**：`orchestration/context_builder.py:664` `list_recent_episodic(user, limit=12)` 按用户跨 session 拉取（无 source_lane 限制），prefilter（memory_retrieval_prefilter）对三条明示事实实测全放行，confidence 0.92 在 correction/importance/confidence 排序下进 top-5。D2 证据里系统说出「只记得你刚完成 Day1 复习任务」恰恰证明召回在读——只是 episodic 里只有那一条 task_outcome 可读。

## 3. 修法（最小侵入，四文件 + 一测试）

1. **`commitment_parser.py:128`**：`parse_commitment_due_at` 增加 `(\d+)\s*天(?:以后|后)` 分支（与既有「N 天内」同构，18:00 默认时刻、naive UTC）。断点①通。
2. **`memory_inferred_write_lane.py`**：
   - 新增明示事实模式面（`:113-117`）：exam（要求 `parse_commitment_due_at` 可解析，防泛考试句误捕）/ weakness（要求学习科目词共现）/ goal / constraint（每天…N 分钟）四类，确定性正则、零 LLM；
   - 新增 `extract_declared_fact_candidates`（`:449`）：逐句扫描（与只挑最佳一句的 `extract_candidate` 互补），同句多信号取最高优先类，confidence 固定 0.92 直写档（与显式记忆口令同级待遇：用户自我陈述的关键事实是最高优先捕获信号），exam 类 subject=commitment+due_at，`declared_fact=True` 标记（dataclass 新字段 `:141`，默认 False，既有构造方零感知）；
   - goal 类排除请求句（「请帮我建立目标」是请求不是事实）；
   - `process_chat_turn` 接线（`:288` 抽取、`:309` 传入 WM live 分支、`:318` fallback 分支直写 L1）；
   - `_is_duplicate`（`:626`）：`declared_fact` 候选只按 semantic_key 去重（同句同键），其余候选维持「一轮一条 OR 同键」既有单写语义不变。断点②④通。
3. **`working_memory_pipeline_service.py:34,62,90`**：接受 `declared_candidates`；明示事实 upsert 进工作记忆后**即时**经 `promote_entry_now`（`working_memory_consolidation_service.py:79`，respect `consolidation_enabled` kill-switch）提升 L1——不再等 mention_count≥3。`_consolidate_entry` 重建候选时透传 `declared_fact` 标记（`:198`，否则重建体落回旧去重语义）。断点③通。
4. 全程复用既有写入链：RuleY 校验、rate limit、用户记忆开关（enabled/allow_episodic/allow_inferred_episodic）、semantic_key 去重、冲突裁决（ConflictResolver）、M-02 五分类存储门（实测三条 verdicts=event/store/store，无一被 veto）、SceneConsolidation——**没有绕过任何一道既有治理面**。

不碰面声明：未动 task/home/goal 文件（wt90）；未动 memory 展示/渲染文案（wt93；`prompts.py` 的【近期相关记忆】渲染层零改动）；未动 FIX-49 kill-switch 语义与 O-07 预算面；**未新增任何 LLM 调用点**（明示事实抽取是纯确定性正则；既有 `llm_extractor`/storage-gate semantic 分支原样未动，不存在绕过 P2DISPATCH 的新直发点）。

## 4. 红→绿证明

新测试 `backend/tests/unit/test_memory_declared_fact_capture.py`（18 项，以 B1 验收原句为夹具，冻结时钟 2026-09-21 周一）：

- **红基线（修复前）**：`14 failed, 3 passed`。14 红覆盖：N天后不可解析（3）、明示事实候选不产出/置信不过门/负样本守卫（9）、fallback 与 live 两形态 episodic 零写入（2）。3 个「vacuous pass」为护栏断言（幂等/用户关闭记忆），修复后才承载实际语义。
- **绿（修复后）**：`18 passed`，含两条全链路证明：
  - **写入腿**：`process_chat_turn` 两形态（working-memory 关闭 fallback / 默认 live）各写 ≥2 条 episodic，exam 行带 due_at（2026-09-28 18:00 UTC）；
  - **召回腿**：Day1 新 session 的 `ContextPackBuilder.build` 中，与追问相关的弱点事实 surface 进 prompt 面（`pack.episodic_memories`），考试/约束事实仍在 `list_recent_episodic` 召回候选集——M-05 selfcheck 按本轮 query 相关性降档非相关记忆属既定反过度-personalized 设计（探针实测 3 行全部通过法律 prefilter，query 相关行 surface）。
- 幂等专测：同事实重复对话/重复轮次 → semantic_key 零重复、行数不增（fallback 与 live 双形态均锁）。

既有回归（全部以进程内哑值 `SECRET_KEY=test` 运行，worktree 无 .env）：

| 套件 | 结果 |
|---|---|
| 新增测试 | 18/18 |
| 核心记忆链（inferred_write_lane / queue / chinese_commitment / working_memory_consolidation / rejection_guard / revival_capture / commitment_parser / subject_type / conflict_resolver×2 / declared_fact） | **134 passed** + 1 个既有失败（见下） |
| 存储门/预筛/selfcheck/排名/读取（storage_gate×2 / retrieval_prefilter / prefilter_integration / selfcheck_wiring / selfcheck / past_session_ranking / service_reads） | **137 passed** |
| reflection_kill_switch / revival_slim_grounding / context_cache_versioning | **37 passed** |
| RB06 wiring / context_source_contract / context_hard_filter / context_pack_conflicts | **22 passed** + 1 个既有失败 |
| memory 家族扫（naturalization / conversation_prompt / preference_decay / api / daily_summary / episodic_gov / epistemic / eval / invalidation / jobs / provenance / rank_policy / settings_api） | **94 passed** + 6 个既有失败/收集错 |
| lint | ruff 全绿；black 对新增代码 120 列合规（不重排仓库既有未格式化行） |

**既有失败（均已在干净基线 `/tmp/wt97-memamnesia-baseline`（HEAD fdd827ee）复跑证实与本卡无关）**：
1. `test_memory_inferred_write_lane.py::test_two_consecutive_sessions_prompt_includes_inferred_memory`——断言已消失的旧渲染头「## 跨会话记忆 [L2 引导]」（现为【近期相关记忆】自然段渲染，commit f01f4ae8 一带改动）；属 prompt 渲染/展示面（wt93 领域）。注：该测试所在路径（app/core/context_pack 直连召回）在无 embedding provider 时 semantic gating 报 WARNING 且不 surface，为独立既有问题，建议 wt93 或后续卡跟进。
2. `tests/core/test_rb06_followup_no_midstream_commit.py::test_persist_assistant_message_uses_flush_not_commit`——persistence_layer 源码断言，与本卡四文件零交集。
3. `test_memory_admin_api`(4)、`test_memory_working_memory_api`(1)、`test_focus_service_memory`(收集错)——同为 HEAD 原状。

## 5. 召回效果验证方案（需主会话在活栈复跑）

单测已锁「入库 + 召回候选 + prompt 面 surface」三级；**GP-04/GP-07 级验证必须真栈复跑 LOOP1**：

1. `make dev-up && make grpc-server && make gateway-dev` 起活栈（新账号）；
2. 复跑驱动器 `backend/tests/northstar_eval/real_drive.py --phase setup → day0`（B1 原句自动重放）；
3. 断言 `/memory/episodic` 出现 ≥3 条 `source_lane=inferred_extraction` 记录（考试+due_at、弱点、165 分钟约束），而不再是仅 1 条 task_outcome；
4. `--phase day1` 复跑 C2 追问 → 判定回答应包含「图论」且**不再出现**「没有完整记录」anti-recall 标记（rejudge v2 规则）；GP-07 followup 应引用弱点事实而非泛讲；
5. 对照：同一账号 24h 后再问（模拟真实 Day2+）验证记忆跨多日存续（decay 30d / due_at+7d 窗口内）。

已知残余（如实陈述，未在本卡修）：
- 弱点/考试事实若在**同轮**被改述（「7 天后」→「还有 3 天」），semantic_key 不同会新增一条记录，旧记录不自动 supersede（既有 inferred lane 同语义；冲突裁决按需可作后续卡）；
- 「纠正类」明示事实（BP-3 领域）未纳入本卡——它与 WS 会话状态推进耦合，需要独立修；
- M-05 selfcheck 对同主题多条事实有 prompt 面去重/相关性降档：多事实同轮全量召回取决于 query 相关性，属反过度-personalized 既定设计。

## 6. 幂等 / 预算面声明

- **幂等**：同一事实重复对话 → 同句同 semantic_key（sha1(normalized)）→ L1 去重跳过；同 turn 重放 → 同键命中；live 路径重复提升 → 去重返回 None 无副作用。fallback 与 live 双形态均有专测锁定。
- **预算面**：零新增 LLM 调用、零新增投递点、零 celery 任务；明示事实抽取为同步内确定性正则（微秒级），写入仍走 turn-end 后台收尾，不占最终帧延迟。
- **Kill-switch 尊重**：`working_memory_enabled`（off 时走 fallback 直写）、`consolidation_enabled`（off 时明示事实不提升，仅留 session 级）、用户记忆开关（enabled/allow_episodic/allow_inferred_episodic，专测锁定）、M-02 存储门（原样评估新记录）——全部既有开关语义不变。

## 7. 收工核查声明

- [x] 修改仅在本 worktree（wt97）内；主仓只读未动
- [x] 无 .env 创建/复制；测试全部进程内哑值（`SECRET_KEY=test`）
- [x] 交付物：`v3-output/MEM-AMNESIA/changes.patch`（5 文件：4 改 1 增，+222/−37）+ 本报告
- [x] /tmp 探针/基线清理：`/tmp/test_dbg_live.py`、`tests/unit/test_zz_dbg_live.py`、`tests/unit/test_zz_recall_probe.py`、`tests/unit/test_zz_dbg2.py`、`/tmp/memdbg.out` 已删；`/tmp/wt97-memamnesia-baseline` 基线克隆已删
- [x] 无模拟器/浏览器/Gradle 启动（LIGHT 任务）；无独立端口进程残留
- [x] `backend/app/gen/` 生成物为 gitignore 内本地构建产物（`make proto-gen` 产物，不入 patch）
- [x] 未 commit / 未 push
