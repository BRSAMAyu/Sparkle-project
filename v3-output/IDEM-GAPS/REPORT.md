# IDEM-GAPS 收卡报告 —— EVENT-ACK-2 登记的两处低危幂等缺口收口

- **Worker**：C 纵队 wt171 ｜ **基线**：a5786869 ｜ **日期**：2026-09-23
- **交付物**：本报告 + `changes.patch`（同目录）。零 commit、零 push、零凭据。

---

## ① 修法与键选型裁决

### 缺口 A（achievement 碎片重复）→ 已修，一行键补齐

**修法**：`_handle_achievement_unlocked` 调 `create_fragment` 时传入
`source_event_id=f"achievement_unlock:{achievement_id}"`。

**为何 `achievement_id` 是「同一次发生」标识**（逐点裁决）：

1. `achievement.unlocked` 在全库**只有唯一发布点** `AchievementEngine._broadcast_unlock_signals`
   （`achievement_engine.py:1590` 附近；task_event_consumer / spine_orchestrator 中的同名串均为消费/信号侧，非发布）。该发布只在 `_unlock_achievement` 内触发。
2. `_unlock_achievement` 的解锁路径是**每用户每成就至多一次**：`SELECT ... FOR UPDATE` 行锁后
   `if user_achievement and user_achievement.unlocked_at is not None: return None`
   （`achievement_engine.py:1446`）——同一用户对同一成就**不存在第二次合法发生**。
   因此卡片担心的「用户+成就类型把不同次发生误判成重复」在此键上不成立：不同次发生
   （不同成就）键必不同；同键必是同一次发生的重投递。
3. 总线侧重投递的三条路径均被此键覆盖：失败 requeue（`_original_message_id` 保 id 但
   失败时不写 done 标记 → 必然重放整 handler）、XAUTOCLAIM 空闲回收（默认 5s idle）、
   消费进程在「碎片已 commit 但 handler 未完成」窗口崩溃后重claim。三者下事件 payload
   逐字段相同，`(user_id, source_event_id)` 查重（`cognitive_service.create_fragment`
   既有幂等门，本卡未改动该函数）即命中既有碎片。
4. 键格式 `achievement_unlock:{achievement_id}` 遵循库内既有 `<source>:<key>` 约定
   （`behavior_auto:*`、`reflection_auto:*`、`capsule_feedback:*` 等），避免与其他
   source 的键空间碰撞。

**诚实边界（预存，不在本卡面）**：`create_fragment` 的查重是 read-then-insert，
无 DB unique 约束兜底，真正并发双消费的极窄竞态仍可双建——与 EVENT-ACK-2 登记
「并发竞态无 unique 约束兜底——预存现状」同性质，本卡不扩面。

### 缺口 B（plan_health 冷却提醒重复）→ 已修（裁决：修，不维持现状）

**裁决理由**：调研确认真实重复窗口存在且修法足够小，复杂度 < 收益，故不申报维持现状。
窗口为：冷却提醒 enqueue（纯 Redis，必成功）之后 handler 内任一点失败/崩溃
（如 bridge rollback 链路抛出、进程在 XACK 前被杀）→ 事件重投递 → 整 handler 重放
→ 提醒双发。总线重试是热重试（requeue 即刻重投、至多 3 次）+ XAUTOCLAIM 5s idle，
重投递窗口为秒~分钟级。

**修法（最小诚实面，两处小改）**：

1. `SystemUpdateService.enqueue` 增加可选参数 `dedup_key: str | None = None`、
   `dedup_ttl_seconds: int = 600`：传键时先 `SET system_updates:dedup:{user}:{key} 1 NX EX 600`，
   未抢到即判重跳过（返回 False）；不传键行为与旧版完全一致（全库 30+ 调用点零影响）。
   存储侧天然查重，无新表、无 schema 变更、无扫描。
2. 消费点（plan_health 冷却提醒分支）传
   `dedup_key=f"plan_health_cooldown:{plan_id}:{signature or f'{severity}|{action_taken}'}"`。

**TTL=600s 的两侧界证明**（为何不会误吞合法提醒）：

- 下界：600s ≫ 热重试 + 5s idle 重投递窗口（秒~分钟级）→ 重投递必落在去重窗口内，不双发；
- 上界：600s ≪ 发布侧同签名冷却（`PlanHealthSignalService.COOLDOWNS`：warning 2h / critical 12h）
  → 合法重发（同签名）最早也距上次 2h，标记早已过期，不被抑制；
- signature 含 severity（`severity|action|reasons`），severity 升级（warning→critical）
  键必变，升级路径不受去重影响；
- 「不同日」性质由 TTL 过期结构性保证：次日合法重发距上次 ≥2h ≫ 600s。

**刻意不做**（防过度工程）：不给 InterventionRecord 桥的第二个 enqueue 加键（EVENT-ACK-2
已判定其有近期 PENDING 去重门，大体安全，卡片明示不动）；不把 SET NX + LPUSH 做成
Lua 原子（极端窗口下宁丢一条 best-effort 提醒，不产生重复打扰，与该面低危定位一致，
已在代码注释言明）；不改 enqueue 为强一致接口。

## ② 实现清单

| 文件 | 改动 |
|---|---|
| `backend/app/services/achievement_event_consumer.py` | `create_fragment` 调用补 `source_event_id="achievement_unlock:{achievement_id}"` + 裁决注释（+6 行） |
| `backend/app/services/system_update_service.py` | `enqueue` 增可选 `dedup_key`/`dedup_ttl_seconds`（默认 600s），SET NX EX 标记门；`DEFAULT_DEDUP_TTL_SECONDS=600` 带两侧界注释 |
| `backend/app/services/plan_health_event_consumer.py` | 冷却提醒 enqueue 传 `dedup_key=plan_health_cooldown:{plan_id}:{signature|回退}` + 裁决注释 |
| `backend/tests/unit/test_achievement_event_consumer.py` | 新增 `test_unlock_redelivery_creates_single_fragment_per_occurrence`：同事件投两次→恰 1 条碎片（断言 source_event_id/内容/tags）；不同成就→共 2 条；真实 CognitiveService + sqlite（StaticPool）+ embedding/prefs/spine/event_bus 打桩 |
| `backend/tests/unit/test_plan_health_cooldown_dedup.py`（新文件） | 3 测试：服务面 dedup 语义（同键窗口内不双发、跨用户隔离、TTL≤600、无键旧行为不变、过期可再发）；消费面端到端（fakeredis 真去重：同事件重投→1 条、不同 plan→2 条、标记过期→3 条）；键构造（signature 缺失回退 `severity|action` 仍幂等） |

**变异验证（防假绿，单文件粒度改+还原）**：

- A：删去 `source_event_id` 行 → 新测试 FAIL（重投递双建碎片）→ 还原 → PASS。
- B：剥掉消费点 `dedup_key` 参数 → 2 个消费面测试 FAIL（提醒双发）→ 还原 → PASS。

## ③ 冲突面声明

本卡改动面共 5 文件（上表），逐卡核对：

- **wt166（exam_sprint_intake_service）**：其域为 `exam_sprint_intake*` 相关服务与测试；
  本卡 5 文件无一与其文件面相交。零重叠。
- **wt167（mobile 小队）**：其域在 `mobile/`（Flutter/Dart）；本卡全部改动在
  `backend/app/services/` 与 `backend/tests/unit/`。零重叠。
- **wt170（achievement_engine.py + Alembic 迁移 + photon 写侧）**：**特别注意**——
  本卡与 wt170 同在 achievement 域但文件面零重叠：本卡读过 `achievement_engine.py`
  以做键选型裁决，但**未改该文件一行**（wt170 属地）；本卡的
  `achievement_event_consumer.py`（消费侧）不在 wt170 申报面（engine + 迁移 + photon
  写侧）内；本卡无迁移、无 photon 面。合入顺序无依赖：本卡对 engine 无任何假设变更，
  仅依赖其「每用户每成就至多解锁一次」的现行行为（1446 行已解锁短路），若 wt170
  未来改该语义需回头复核本卡键选型（已在本报告①留裁决链）。
- 另：`system_update_service.enqueue` 为共享服务，本卡改动为**纯增量可选参数**，
  全库 30+ 既有调用点（achievement_engine、memory_jobs、cognitive_service、
  orchestration 等）签名兼容零行为变化；相关域回归（memory_service、error_replan_bridge、
  cognitive_service_regression 等）见④，零失败。

## ④ 回归与诚实申报

**对比法基线（改前，a5786869 原样）**：7 个相关域测试文件
（achievement_event_consumer / plan_health_signal_service / event_ack2_reliability /
memory_service / error_replan_bridge / cognitive_service_regression /
achievement_event_publishers）= **54 passed, 0 failed**。

**改后同集 + 新增 4 测试** = **58 passed, 0 failed**。零新增失败、零残留。
环境：`SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" python3.11 -m pytest`，
串行单 pytest 进程（LIGHT 面）。

**诚实申报**：

1. 本 worktree 无 `backend/app/gen/`（gitignore 产物，新 worktree 天然缺失），
   `test_event_ack2_reliability.py` / `test_error_replan_bridge.py` 因 import 链
   （task_service → `app.gen.sparkle...`）收集失败。处置：从主仓拷贝 gen 产物入本
   worktree（gitignored，不进 patch/不 commit，纯测试环境物）。gen 内容为主仓 HEAD
   生成物，与基线 a5786869 的 proto 可能存在极小版本差；两文件测的是 consumer raise
   语义与总线行为，非 proto 契约面，风险可忽略。基线与改后同条件，对比法依然成立。
2. lint：ruff 对 5 个触碰文件全绿（含修复我新文件的 I001 排序）；black 状态与基线逐文件
   持平（`achievement_event_consumer.py`、`plan_health_event_consumer.py`、
   `test_achievement_event_consumer.py` 基线即不满足 black——预存，本卡未恶化；
   black diff 不含本卡任何新增 hunk；`system_update_service.py` 基线与改后均 clean；
   新文件 `test_plan_health_cooldown_dedup.py` black clean）。
3. B 未选择「维持现状」：窗口真实存在（enqueue 成功后的 handler 失败/崩溃重放），
   且修法仅 ~12 行服务侧 + ~8 行消费侧；若后续判定 600s 去重窗口需调整，
   `DEFAULT_DEDUP_TTL_SECONDS` 单点可调。
4. A 的并发竞态（read-then-insert 无 unique 兜底）为预存面，本卡未加约束——与
   EVENT-ACK-2 对 engine 侧的登记保持同一口径，避免为 low-priority 面引入迁移。
5. 本卡未跑全库 pytest（纪律禁止宽扫描）；对比集为两 consumer 域 + enqueue 共享服务
   的直接消费域，属合理回归面。

## ⑤ 收工核查清单

- [x] 改动仅在本 worktree（wt171）；主仓只读未触碰
- [x] 变更面 = 5 文件（3 代码 + 2 测试），`git status` 与申报逐一对齐，无计划外文件
- [x] 零 commit / 零 push；交付物 = 本 REPORT.md + changes.patch
- [x] 零凭据入库；测试走 sqlite memory + fakeredis，无真实 Redis/PG/LLM 依赖
- [x] 单 pytest 进程串行；未跑全库；HEAVY=0
- [x] 变异实验均为单文件粒度并即时还原（A、B 各一次，均验证后还原）
- [x] /tmp 自产物已清（idemgaps_lint/、idemgaps_a/b_backup.py）；worktree 内无构建产物
- [x] `backend/app/gen/`（gitignored 测试环境物）留在 worktree，不入 patch、不入库
