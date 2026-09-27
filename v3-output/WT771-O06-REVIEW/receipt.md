# WT771-O06-REVIEW — 卡 O-06（Kill Switch / Release / Rollback 统一操作面）独立审查 receipt

- Reviewer: wt771（独立会话，未参与 O-06 实现）｜ 日期: 2026-09-28
- 审查对象: wt765 交付 commit `1ca6c2dc`（已在 main，随轮#259 集成 b129040c）
- 集成 HEAD（所有复跑所在）: main `b129040c`
- 审查 worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt771-o06rev`，分支 `agent/node-b/wt771/o06rev`（自主线仓 worktree add，主仓全程只读；不 push）
- 环境: macOS/arm64，Python 3.11.15（主线仓 backend/.venv），fakeredis 2.38.0 / pytest 9.0.2 / redis-py 7.4.0；测试口径 `DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v ENVIRONMENT=local`
- 真栈对象: 本机 docker `sparkle_redis`（redis-stack-server 7.4.0，127.0.0.1:6379，口令取自主线仓 backend/.env，不入库本 receipt）

## 结论：**PARTIAL**

核心面（注册表/受控翻转/回滚史/release manifest/internal API/文档/38 测试）质量过关、全部关键验收独立复跑通过；但交付的 `scripts/ops_rollback_smoke.py` 在 **`--redis-url` 真栈模式有实锤缺陷**：交付版在该模式下回滚必炸且回滚失败时**把旗滞留在 shadow**（本审查对本地 sparkle_redis 运行级实录，含事故与恢复全过程，见 §4.3）。该缺陷一行可修，本 receipt 附 reviewer 补丁（worktree 内提交，**未入 main**）。

### 销账建议（给协调方）

1. **核心面可销**：注册表 + API + manifest + 文档 + 38 用例按 DONE 计，前提是下条随后落地。
2. **强制跟进小修（建议预占 V3-FIX-502，号段 grep 复核空闲）**：`ops_rollback_smoke.py` 的 `aioredis.from_url(...)` 补 `decode_responses=True`（与 cache.py:73 生产客户端同构），并把翻转→回滚包进 try/except：异常时尝试恢复 baseline + 显式非零退出，绝不滞留翻转旗。修法与证据见本 receipt §4.3/§6；可直接采纳本 worktree 的 reviewer patch（1 行实质改动）。
3. 502 落地后 O-06 卡即可整体销账，无需重审（本 receipt 已含补丁后绿实录）；若协调方选择把 patch 直接合入 main，则升级为 APPROVE。
4. V3-FIX-501（5 proxy 绕核心）/V3-FIX-500（AURORA_DEFAULT_MODE 零读者）登记复核无误，维持 OPEN。

## 1. 卡面对账（Work / Acceptance / Forbidden 逐条）

| 卡面条目 | 对账结论 | 依据 |
|---|---|---|
| Work1 注册新 flags，清理未受控 live 实验 | **达成（诚实形态）** | 未造新旗；`CAPABILITY_SPECS` 64 行全部指向既有绑定（惰性走径，零复制定义）；补注册 `AURORA_META_LEARNING_ROUTING_PARAMS_MODE="off"`（settings.py:418）——**等价性本审查独立核实**：META_LEARNING_BINDING fallback_mode="off"（routing_parameter_registry.py:32），改前 getattr 缺席→fallback off，改后默认 "off"→normalize off，逐字同值零行为变化；两处「未受控实验」如实登记 501/500 不顺手修 |
| Work2 per-capability rollback | **达成** | 回滚史栈（LPUSH/LTRIM 20/TTL 30d）+ 步进恢复（§3 语义审查通过）；语义与核心 write_mode 同一出口 |
| Work3 release manifest（model/config/migration） | **达成** | 只读装配；五旗走 `release_flags_response()` 冻结键集；migration 双侧对账 fail-soft |
| Acceptance: shadow/live 切换不丢用户 state | **通过** | 结构论证成立（写键=prefix+redis_key，全仓唯一性有测试钉住）+ 单测/API 测试哨兵键 + smoke 第 4 检查，三面同证 |
| Acceptance: rollback smoke 通过 | **通过（含保留意见）** | in-process 冒烟 exit 0 四检查全 PASS（本审查复跑）；真栈面按补丁后 PASS——**交付版真栈模式 FAIL，见 §4.3 事故** |
| Acceptance: flag 状态可观测 | **通过** | GET /capabilities 全量 64 + capability_id 与 KILL_SWITCH_MODE (stage,feature) 标签逐字对齐（有测试钉住）；读路径 Redis 缺席降级不 5xx |
| Forbidden #1 不重建权威真源 | **未违反** | resolve_binding 返回**原绑定对象**（isinstance KillSwitchBinding 校验，非副本）；模式判定仍走 kill_switch.read_mode/write_mode；manifest 是投影非真源 |
| Forbidden #2 不用 mock 冒充真实行为 | **未违反** | fakeredis 仅用于进程内测试面且如实标注；manifest 缺数据源→null+error 注记不伪造（sqlite 无表用例钉住） |
| Forbidden #3 不以静态阅读宣称通过 | **部分违反（轻）** | notes §5 声称栈面证据「脚本已为此备好」——静态阅读结论，本审查运行级证伪（§4.3）。wt765 未谎称已跑过栈面（明确留给 reviewer），故定为轻 |
| Forbidden #4 不弱化既有守卫 | **未违反** | diff 不触任何守卫文件；AV 守卫（65 mode settings/23 services）与 AURORA-CONFIG 守卫本审查独立复跑均 PASS |

## 2. 独立复跑：38 用例（integration HEAD b129040c，本审查自己的 worktree）

```
tests/unit/test_ops_surface_registry.py  21 passed
tests/api/test_ops_release_api.py        17 passed
=============== 38 passed, 3 warnings in 4.20s ===============
```

与交付声称的 38 用例逐一对得上（21+17）。

触达面回归（同环境复跑）：`test_dual_core_router_kill_switch`(6) + `test_startup_smoke`(12) + `test_slo_auto_degrade_api` + `test_release_flag_authority` 合跑 **58 passed**。守卫复跑：`check_rule_av_kill_switch_mode_enum.py` PASS（65/23，含新补字段）、`check_aurora_config_consistency.py` PASS。

## 3. registered-iff-read 咬合力：双向变异抽验（均在审查 worktree 内做，验后 git checkout 还原并复跑 38 绿）

- **变异 A（按审查指令：注释掉一个 binding）**：`aurora_stage39_kill_switch_service.py` 注释掉 `_FEATURE_BINDINGS["scaffolding_prompt"]` → **7 failed / 31 passed**：registry 4 测（id 对齐/覆盖对账/settings 在场/redis 键唯一）+ api 3 测全红，首红 `CapabilityError: cannot resolve ..._FEATURE_BINDINGS.scaffolding_prompt`。
- **变异 B（正向：注入未注册绑定）**：同模块注入 `wt771_probe` 绑定（settings_attr="AURORA_WT771_REVIEW_PROBE_MODE"）→ 对账测试红，报文逐字：`未注册绑定: ['AURORA_WT771_REVIEW_PROBE_MODE']; 幽灵 spec: []`。
- 双向都咬合：漏登 spec 红、删绑定留幽灵 spec 红。AST 扫描限定字面量传参的局限 wt765 已在 notes §5 如实自报。

## 4. smoke 三态实录（scripts/ops_rollback_smoke.py）

### 4.1 默认 in-process（fakeredis）
exit **0**：baseline live → 翻 shadow（history_recorded=True）→ 回滚恢复 live；4 检查（flipped_to_shadow / rollback_restored_baseline / history_recorded / user_state_intact）全 PASS，SMOKE OK。

### 4.2 双确认面（真栈前置闸）
`--redis-url redis://127.0.0.1:6379/0` 无 `--i-understand-this-flips-real-capabilities` →
```
REFUSING: --redis-url requires --i-understand-this-flips-real-capabilities
REFUSE_EXIT=2
```
拒绝发生在建立任何 Redis 连接之前（读码证实：REFUSING 分支先于 from_url）；跑前跑后 sparkle_redis `sparkle:ops:*` 扫描均为空，零接触。

### 4.3 真栈运行实录（本地 sparkle_redis，交付版）——**事故与恢复，全记录**

- **跑前安全审读**（铁律要求）：脚本逐行读毕——目标 mode 硬编码 `SMOKE_TARGET_MODE="shadow"`，永不写 off/live，无批量端点；唯一 Redis 写=哨兵键+能力模式键+回滚史键；rollback 内部仅 delete/rpush **史键**。判定无 destructive 面，授权范围内执行。
- **跑前状态**：`aurora:dual_core_router:mode` 不存在（GET nil），`sparkle:ops:*` 零键（SCAN 空）。
- **执行**（`--redis-url` + 双确认 + 默认 capability=dual_core_router.mode）：[1/3] baseline live → [2/3] flipped live→shadow（史已记）→ **[3/3] 回滚炸**：未捕获 `NoRollbackPointError: no rollback point available for dual_core_router.mode`，脚本 traceback 崩出。
- **事故现场（redis-cli 实录后才动手恢复）**：`GET aurora:dual_core_router:mode` = **`shadow`（旗滞留翻开）**；史键 1 条 set 记录（from=live to=shadow）；哨兵键在。
- **恢复**：对本次冒烟自建的 3 键执行 DEL（恢复字节级 pre-state：该模式键改前本不存在），复查 `aurora:dual_core_router:*` 与 `sparkle:ops:*` 扫描双空。**现栈无任何翻开的旗。**
- **根因（离线 fakeredis bytes 探针证实，未再触真栈）**：`--redis-url` 分支 `aioredis.from_url(args.redis_url)` **缺 `decode_responses=True`**（对比：同脚本 in-process 分支与生产 cache_service 均 True，cache.py:73）。bytes 客户端下 read_mode 取回 `b'shadow'`，`normalize_mode` 做 `str(value)` 得 `"b'shadow'"` → 落 fallback `"live"`（探针实录：`raw=b'shadow' → normalize → 'live'`）→ rollback 判 current=live 与史条目 from=live 相同 → 无异值恢复点 → 异常未被脚本捕获 → **翻转已落盘而恢复未发生**。
- **影响面**：仅限本 smoke 的 `--redis-url` 分支。生产 API 面/ops_surface 不受影响——`cache_service.redis` 构建固定 `decode_responses=True`（cache.py:71-74 本审查复核），且 API 测试的 fakeredis 同构。bytes→fallback 静默回落是 kill_switch 核心 `normalize_mode` 的既有语义（非本卡引入），但 O-06 的 smoke 是第一个给它喂 bytes 客户端的地方。
- **reviewer 补丁后复跑（同栈同 capability 同双确认）**：exit **0**，四检查全 PASS，SMOKE OK；跑后旗读回 `live`（=settings baseline，史尾为 rollback 条目 from=shadow to=live）→ 随后清掉本次 3 个自建键，扫描双空还原字节级 pre-state。补丁 diff 随本 receipt 同 worktree 提交（`scripts/ops_rollback_smoke.py`，1 行实质改动+注释，标签 REVIEWER-PATCH-WT771）。

## 5. 设计合理性审查（语义陷阱逐项）

1. **capability_id 对齐**：`= <binding.stage>.<binding.feature>` 与 Prometheus gauge 标签同坐标系，有测试逐字钉住 + 64 id 唯一性实测（本审查重跑 Counter：aurora 53 / memory 4 / fme 2 / infra 5 = 64，与文档一致）。无陷阱。
2. **回滚史机制**：步进语义正确（同值链跳过、rollback 标记非恢复点防震荡、史尽 409）；RPUSH 逆序回写与 LPUSH「index 0=最新」约定自洽（本审查逐步推演核实）；损坏条目跳过不阻断恢复点查找。**已知取舍**（非缺陷）：a) 回滚后 `remaining` 重写会把恢复点之上的同值链与损坏条目一并压实，审计粒度略降（史本就 20 条上限）；b) 翻转+回滚会在 Redis 留下与 settings 同值的**钉住值**——Redis 现值优先语义下此后改 env 默认不再生效，且本面无「清除回落 settings 权威」操作（DEL 键）。这是既有核心语义的延伸（auto_degrade webhook 同性质），建议在 OPS_SURFACE.md 加一句运维注记即可，不算本卡缺陷。
3. **词表外 400**：`_validate_mode` 借 normalize_mode 的 fallback 槽做哨兵，显式拒绝不静默回落；`__invalid__` 与 TRI_STATE_MODES 无碰撞面。set 与 rollback 恢复值共用同闸。无陷阱。
4. **fail-soft 降级**：读路径 Redis 缺席/连不上→回落 settings + `runtime_mode_available` 如实标注（可观测降级而非不可用）；写路径缺席→503 拒绝（不冒充成功）；manifest 双侧 fail-soft + error 注记。方向全部 fail-closed/loud，正确。一个残余耦合：单个 spec 解析坏会让全量 list 500（fail-loud 可接受，且 CI 期 AST 对账先拦）。
5. **守卫洞（建议改进，不阻塞）**：`test_registry_prefix_matches_owning_service_class_constants` 对字面量前缀家族（"sparkle:"/"aurora:"，恰是最大两族）整族跳过——若 spec 抄错字面量 prefix，现无守卫可拦，将产生「翻一个没人读的键」的静默 no-op。本审查核实这些模块的 read_mode/write_mode 调用点**确有 prefix 字面量在场**（stage37/39/auto_degrade/fme_l3_closure_bridge 逐个 grep），AST 扫描调用点字面量即可闭合此洞。低概率（spec 系从源码抄录）+ 双重对账仍在，故列为改进项，可并入 502 或后续。

## 6. 结论重申与判定依据

- 核心交付 38/38 独立绿、变异双向咬合、守卫独立 PASS、Forbidden 四条实质未破、等价性独立核实、文档数字与实测一致。
- 唯一实锤缺陷：smoke `--redis-url` 分支（decode_responses 缺失 + 异常不恢复）。它使「栈面回滚证据」在交付版上**不可获得**且失败模式危险（滞留翻转旗）——恰是本卡自我声明的安全姿态所不容。一行可修，reviewer 已备 patch 并以补丁版产出栈面绿证据。
- 故 **PARTIAL**：按 §销账建议处理后即可整体销账，无需重审。

## 7. 证据索引

- 复跑环境/口径/命令：见 receipt 头部；全部在本审查 worktree 执行，主仓只读未动。
- 真栈两次运行前后 redis-cli GET/LRANGE/SCAN 实录：见 §4.2/§4.3（逐条在案，终态=字节级 pre-state，扫描双空）。
- reviewer patch：本 worktree `scripts/ops_rollback_smoke.py`（commit 与本 receipt 同批，分支 `agent/node-b/wt771/o06rev`，**不 push、不自行合 main**）。
- 关联在册：V3-FIX-501/500（wt765 登记，本审查复核无撞号：主台账 499=wt767 total_days、500=AURORA_DEFAULT_MODE×2 处、501=metacog proxy）；建议新占 V3-FIX-502（smoke bytes 客户端 + 崩溃不恢复），号 grep 复核空闲。
