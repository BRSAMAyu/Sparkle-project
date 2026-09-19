# M-01 REVIEW_RECEIPT_2 — 第二路 Reviewer（DeepAudit 深层审计）

- reviewer: R2（DeepAudit；M-01 risk=high 需 2 Reviewer 之路 2）
- date: 2026-09-19
- 对象: wt2 未 commit 改动（11 文件 +1430/-4，基线 2f52a972）+ v3-output/M-01/
- 方式: 代码审读（全量 diff + 冲突/记忆/任务全链路）+ 定向 pytest 实跑 + 自写一次性探针（2 项，跑后即删）+ dev PG 只读 SELECT 抽样 + patch 完整性核对
- 禁改 Worker 代码 / 禁 alembic / dev PG 未写：均遵守（alembic_version 复核仍为 ent01_20260919）

## 0. 实跑记录

| 项 | 结果 |
|---|---|
| Worker 四套新测试（21 项） | 21 passed（复现 Worker 自报） |
| 存量回归 test_memory_service.py + test_conflict_resolver_service.py | 16 passed |
| R2 探针 A（apply_live_decision 终态改写/链历史覆盖） | **复现缺陷**（见 F2） |
| R2 探针 B（bump_memory_epoch 并发丢增量，逐句重放其 SELECT→python+1→commit 序列） | **复现缺陷**（见 F3） |
| changes.patch vs git diff HEAD | 逐字节一致 |
| dev PG | 只读；236 live episodic（184 direct_capture + 52 inferred_extraction），0 revoked/retracted/archived |

## 1. 五焦点结论摘要

焦点1（状态机）：derive_status 纯派生 + 生命周期列只置不清 → 优先级链在**读侧**无非法状态；但**写侧**存在终态改写与链历史覆盖（F2，探针实证）。upsert_preference 守卫原子性合格（FOR UPDATE 先于判定，R1 已验红绿；R2 复核代码确认锁序正确）。
焦点2（回填边界伤害）：**live 数据大规模误分类成立**（F1，dev DB 实证）。
焦点3（守卫绕过面）：版本链域字段（replaced_by_id / superseded_by_id）全仓只有 guarded 的两个写入点，未发现第三条绕过路径；剩余面为 by-design 的用户仲裁与 by-precedence 安全的 decay 批写（详见 §3）。
焦点4（epoch）：并发丢增量实证（F3）；「先 supersede 后 revoke」终态确定（REVOKED，优先级保证）；但 epoch 覆盖漏了第 5 条破坏性入口 arbitrate_unresolved_conflict（F4）。
焦点5（lane_priority 委托）：fail-closed（导入/注册表漂移在变更前抛出，无半写）；未登记 lane 落最低档与 resolver 一致；无 fail-open 面。残留：KeyError 不在 best-effort 捕获集，属设计选择（变更点不吞错），可接受。

## 2. 发现（分级）

### F1｜P1（确认，live 数据实证）——m01a 回填把机器写入行批量标成 FACT，FACT 分区 ~99% 非用户陈述

- **执行链**：orchestrator（`app/orchestration/orchestrator.py:1171`，source_type=chat_turn，confidence 硬编码 0.78，未传 source_lane → 默认 direct_capture）等机器写方 → `create_episodic_memory(source_lane="direct_capture")` → m01a 回填 `CASE WHEN source_lane IN ('direct_capture','user_confirmed') THEN 'FACT'` → 机器观察事件落 FACT；本卡 `GET /memory/episodic` / export 序列化直接对外返回 `epistemic_class: "FACT"`。
- **dev PG 实证**（只读）：184 direct_capture 行中 chat_turn=164、analysis=9、reflection=6、error_analysis=2、practice_outcome=2、user_registered=1——除 user_registered 外全部为机器写入；chat_turn 166 行仅 **8 个不同 summary**（"completed 操作系统 - 死锁处理机制" 单条事件重复 148 次，semantic_key 内嵌 evidence_id 导致无去重）。即回填后 FACT 分区 ≈183/184 是系统观察（契约自己定义 OBSERVATION = "behavioral/system observations"）而非用户陈述事实。
- **为何隐蔽**：Worker 与 R1 都把「lane 冒领」记为抽象风险（REPORT §6.1），但未量化 live 数据——实际上这不是边角，是 FACT 分区的主体；且 "completed ..." 完成事件按契约语义是教科书式 OBSERVATION。
- **触发/潜伏期**：迁移 apply 即固化；本卡 API 已开始对外暴露该标签；M-04 仲裁接线 / M-07 上下文按 epistemic_class 分区消费后危害兑现（AI 观察事件享受事实档信任与展示）。
- **影响面**：当前 dev 236 行中 184 行；后续每次 chat_turn 写入持续增量。
- **修复建议（最小）**：迁移未在任何环境 apply（dev 仍 ent01）——现在改回填 CASE 零成本：FACT 仅限 `source_lane IN (explicit lanes) AND source_type IN (用户陈述集)`，机器写行落 NULL（读侧按 lane 派生，行为不变）或 HYPOTHESIS；把「写方 lane 治理」留在 M-04（Worker 已划界），但回填不应替机器行做升档裁决——这恰是本卡自己「未登记 lane 保守 HYPOTHESIS」原则应延伸而未延伸之处。
- **验证**：改后在 dev 快照重放回填 SQL，断言 chat_turn/analysis 行非 FACT。

### F2｜P2（探针实证）——apply_live_decision 无生命周期过滤、无行锁：改写已撤销行 + 静默重指 supersede 链

- **机制**：`conflict_resolver_service._load_records`（:510）仅按 id+user 过滤（对比读路径 `load_conflicting_records` 过滤 retracted/revoked/deleted —— 读过滤、写不过滤的 TOCTOU）；循环（:274-282）无条件覆写 `retracted_at` 并重指 `superseded_by_id`。
- **探针 A 实证**：(a) 已被 W_old supersede 的 loser 再次败于 W_new → 链指针被静默改指 W_new，与 W_old 的历史关系无审计丢失；(b) 用户已 revoke 的行被写入 retracted_at+superseded_by_id——derive_status 靠优先级仍报 revoked（无非法状态），但链图路由穿过硬删记录；(c) 重复投递/重放同一冲突任务时非幂等（每次重指）。
- **并发**：`_load_records` 无 FOR UPDATE，两个并发冲突应用对同一 loser 最后提交者胜出（supersede 链 last-write-wins）。
- **触发条件**：同一 semantic_key 先后两次冲突（正常累积即可触发 a）；用户删除与冲突应用竞态（触发 b）；celery 重试（触发 c）。
- **修复建议**：_load_records 加生命周期过滤（revoked/archived 跳过；已 superseded 保留首链指针、仅记审计），加 with_for_update。
- **验证**：探针 A 改后应失败（断言不再覆写）。

### F3｜P2（探针实证）——bump_memory_epoch 读-改-写无锁，并发丢增量，epoch 契约对 M-07 失真

- **机制**：`memory_service.bump_memory_epoch`（:1509）SELECT（无 FOR UPDATE）→ python 侧 +1 → commit；无 `SET memory_epoch = memory_epoch + 1`、无乐观版本。
- **探针 B 实证**：两入口并发（逐句重放其语句序列，双 SELECT 先于任一 commit——即生产中两个删除/撤回入口竞态的真实窗口）→ 两次 bump 均返回 2，终值 2（应为 3）。注：首次自然 gather 未交错得 3，说明窗口需要真实并发交错，Postgres 下两请求/任务间必然存在。
- **后果**：M-07 消费者在 bump1 后刷新到 N+1，bump2 的破坏性变更塌缩进同一 N+1 → **过期上下文被当作新鲜继续服务**。这是缓存失效计数器的一类经典失效，且 epoch 目前无消费者、修法极廉。
- **次生**：懒建 settings 行的并发撞 unique（IntegrityError ∈ NON_CRITICAL_SERVICE_ERRORS 被吞）会把共享 session 留在 aborted 事务态——`revoke_inferred_memories` 多用户循环中后续用户的 bump 全部 PendingRollbackError 被吞，epoch 覆盖静默缺失（主路径不崩，承诺仍守，但覆盖面缩水）。
- **修复建议**：原子 `UPDATE ... SET memory_epoch = memory_epoch + 1 ...`（懒建用 INSERT ON CONFLICT DO UPDATE）；捕获后先 rollback 再继续循环。

### F4｜P2 latent（结构性）——epoch 契约漏第 5 条破坏性入口：arbitrate_unresolved_conflict

- 用户仲裁（:397）经 `_retract_if_present`（:521）retract 败者（读路径全部排除）却**不 bump epoch**；四入口清单（retract/revoke/correction:reject/revoke_inferred_bulk）不含它。M-07 接线后，仲裁删除的内容会从 stale 缓存继续外泄。
- 次要不一致：仲裁败者只得 retracted_at（终态 RETRACTED），自动路径得 supersede 链（SUPERSEDED）——区分「被替换/被撤回」的消费者会把用户仲裁的败者误读为撤回。
- 修复：仲裁入口补 best-effort bump + 可选 superseded_by_id=winner。

### F5｜P3（部署窗口）——新代码 + 旧 schema：episodic 治理/导出读接口 500

- `record.epistemic_class` 为映射列，SELECT 自动带上；在未跑 m01a 的库上 `GET /memory/episodic`、export 直接 UndefinedColumn。REPORT 的「在跑旧代码零感知」只覆盖旧代码+新 schema 方向。需 schema-先于-代码（或同发）的发布序，建议在 M-01 合入说明中显式钉住。

### F6｜P3（边界澄清）——守卫的 "explicit" 判据是「非 ai_inferred」而非「人类」

- `chat_signal_collector`（规则抽取用户原话，source_type="chat_preference"）经 set_explicit_preferences 落链头并获事实档；后续 ai_inferred 写被守卫挡在其外。用户原话≈显式，可辩护；但「机器 vs 人类」边界在 M-04 文档中应显式声明，避免未来把守卫语义误读为挡一切自动化写。
- 反向边角：显式路径若携带 ai_inferred 型 evidence_ref 会被误判 INFERRED 而遭误拦（当前调用方无此形态，守卫判定次序 source_type 优先所致）。

### F7｜P3（可观测性）——episodic 侧守卫跳过无指标

- `blocked_inferred_over_fact` 有 MEMORY_WRITE_TOTAL 指标；`epistemic_guard_skipped_loser_ids` 仅 warning 日志 + decision metadata，无计数指标，长期运行无法量化越权尝试频率。

## 3. 焦点3 细节：未发现第三条绕过路径（证据）

- `replaced_by_id` 全仓唯一写点 = upsert_preference（guarded，FOR UPDATE 原子）。
- `superseded_by_id` 全仓唯一写点 = apply_live_decision（guarded；其自身缺陷见 F2，但非绕过）。
- 其余生命周期写入面：`_apply_retraction`/`revoke_episodic_memory`（用户/管理动作，最高权限 by design）、`arbitrate_unresolved_conflict._retract_if_present`（人类仲裁，by design，但见 F4）、`run_decay_job`（批量 archived_at，未过滤已撤销行——凭优先级无害，仅语义噪音）、`resolve_commitment`（resolved_at，合法终态）、`context_pack` 批量 last_consumed_at（非生命周期域）。未来绕过风险主要来自 M-04 新调用方直接 ORM 写链域——建议在契约模块暴露唯一写原语并在 code review 守卫清单登记。

## 4. 与 R1 的关系

R1 验收的核心（漏洞红绿复现、契约自洽、测试、patch、dev PG 未动）全部成立，R2 复跑一致。R2 新增的四项实质发现（F1-F4）均属「离开开发者机器后才兑现」的深层缺陷，其中 F1 在迁移未 apply 前修复零成本、apply 后需矫正性迁移。

## VERDICT

发现 7 项（P1×1、P2×3、P3×3），无 P0。最危险一条：m01a 回填将把 dev 库 184 行机器写入（含 148 行同一完成事件的重复记录）固化为 FACT 档——FACT 分区 ~99% 非用户陈述，且经本卡 API 直接对外暴露，M-04/M-07 接线后 AI 观察事件将享受事实级信任。守卫本体（推断不覆盖事实）经 R1/R2 双路确认有效且原子。F1/F3 在迁移与契约未发布前修复成本近零，发布后翻倍——要求返修这两处最小改动（回填 CASE 收紧 + epoch 原子自增），F2/F4 可随 M-04 一并治理但应在任务卡登记。

**VERDICT: CHANGES**
