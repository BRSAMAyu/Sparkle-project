# WT765-O06 — Kill Switch / Release / Rollback 统一操作面（卡 O-06）

- Agent: wt765 ｜ 分支: `agent/node-b/wt765/o06`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt765-o06`，base main@3cbeb4a7）
- 日期: 2026-09-28（本机时钟）｜ 主线仓库只读 ｜ 状态: **READY_FOR_REVIEW**
- 必读已读: `v3/08_operations/RELEASE_GATES.md`（R0-R7 gate 链 + 「gate 失败不靠关测试过」）；依赖卡 O-01(TODO)/A-01(done)/X-05(done) 卡面与 `tasks.json` 权威条目照读。
- 新文档: `v3/08_operations/OPS_SURFACE.md`（操作面入口文档；该目录无 README 登记惯例，DEPLOYMENT/OBSERVABILITY 等同目录先例均直落）。

## 0. 一句话

给存量 **64 个三态 kill switch 能力**建统一索引 + 受控翻转 + per-capability 回滚 + release manifest（model/config/migration），经 `/api/internal/ops`（INTERNAL_API_KEY）暴露；**零重建既有权威**（绑定与判据仍归各 service 模块与 `app/core/kill_switch.py`）。

## 1. 现状基线（摸底实录，2026-09-28 @ 3cbeb4a7）

- **三态机制权威已在**：`app/core/kill_switch.py`（off/shadow/live、Redis 现值优先、settings 判据、legacy bool 兜底、`KILL_SWITCH_MODE` Prometheus gauge）+ `KillSwitchBinding` 冻结 dataclass（V3-FIX-21 已单一化判据）。
- **绑定散在 27 个模块**：25 个 `aurora_*kill_switch_service`/`fme_*` service + `app/api/internal/auto_degrade.py`（SLO 五绑定，prefix="sparkle:"）+ `orchestration/routing_parameter_registry.py`（META_LEARNING）+ `fme_l3_closure_bridge.py`。AST 扫描（`KillSwitchBinding(...)` 调用）实测 **64 个绑定、settings_attr 64 个、prefix+redis_key 组合全仓唯一**。
- **形态多样**：类级 `BINDING`/`BINDINGS` dict/`MASTER_BINDING`+`FEATURE_BINDINGS`/模块级 `_STAGE37_BINDING` 族；prefix 有类常量（`aurora:dual_core_router:` 等）、模块常量（`REDIS_KEY_PREFIX="aurora:"`）、字面量（`"sparkle:"`）三种。
- **既有翻转面只有一条嘴**：auto_degrade webhook（SLO 告警自动翻转，非人工操作面）；fme_kill_switch_service docstring 明示「无运行时翻转 API，仅工具/演练可用」。**无任何 release manifest**。
- **release 五旗**（`app/config/release_flags.py` 薄视图 + settings `RELEASE_ENABLE_*` 分节）与三态族平行存在，前者管「发布面开关」（shop/transfer/leaderboard/community/visual），后者管「Aurora/Memory 能力三态」——两族语义不同，不合并。

## 2. 设计取舍（逐条 Work 对应）

### Work 1「注册新 flags，清理未受控 live 实验」→ 注册表 + 一处补注册 + 两处如实登记

- **不重建权威**（Forbidden #1）：`CAPABILITY_SPECS` 每行是「module + binding_path + prefix」的**惰性走径**（importlib + getattr/Mapping 键解析，`@cache`），引用既有绑定对象本身，零复制定义、零提前 import services 导入链（core 层不背 27 个模块的 import 成本）。
- **capability_id = `<binding.stage>.<binding.feature>`**：与 Prometheus `KILL_SWITCH_MODE{stage,feature}` 标签逐字对齐（「flag 状态可观测」验收与既有 gauge 同一坐标系）；64 个 id 实测唯一。
- **domain 封闭词表** `{aurora:53, memory:4, fme:2, infra:5}`：stage19 族按代码注释归 memory（「Memory V3 (M-02)」），stage21 技能族留 aurora（stage 编号权威），SLO 五项归 infra，FME 两项归 fme。不造第二套分类权威。
- **补注册一处死 flag**：`META_LEARNING_BINDING.settings_attr="AURORA_META_LEARNING_ROUTING_PARAMS_MODE"` **在 Settings 权威字段缺席**（getattr 默认 None → 恒 fallback "off"，env 通道死路）——settings.py 补该字段默认 `"off"`（与缺席等价，零行为变化，AV 守卫通过：65 mode settings validated）。这是卡面「注册新 flags」在本仓现实中的诚实落点：**补齐已声明未落地的 flag**，而非无读者造新旗（registered-iff-read，V3-FIX-345 学说不变，且 `tests/unit/test_ops_surface_registry.py` 的 AST 生成式对账把这个学说变成机器守卫）。
- **「未受控 live 实验」扫雷结果（两项，均如实登记不顺手修）**：
  - **V3-FIX-501（P3）**：5 个元认知 confidence proxy（`metacognition_registry.ConfidenceProxyDefinition`）直读 settings 三态字段（`!= "off"` 判开）——无 Redis 运行时翻转、无 gauge、非法值判「启用」与 tri-state 回落语义相悖。改线属行为面变更（非法值存量部署会从启用变回落），停手登记。
  - **V3-FIX-500（P4）**：`AURORA_DEFAULT_MODE`（.env.example 承诺的「总默认」，AURORA-CONFIG 托管键）全仓零读者——改它零效果。修法二选一（接线派生 / 处置A 删除）已在台账列明，倾向兑现承诺，需两位 reviewer。
  - 排除项说明：`fallback_mode="live"` 的能力族不是未受控实验——是防「未配置部署被一刀切禁用」的既有决策（`test_dual_core_router_kill_switch.py::test_fallback_mode_is_live` 明文钉住）；`ENABLE_AURORA_RUNTIME_V1` 等 bool 是稳定特性闸，非实验。

### Work 2「定义 per-capability rollback」→ 回滚史栈 + 步进恢复

- **写前快照**：`set_capability_mode` 先 `read_mode` 取当前值，压入 `sparkle:ops:rollback_history:<cid>`（LPUSH 新前，LTRIM 上限 20，TTL 30 天），再走核心 `write_mode`——**写路径语义与拥有方 service 逐字一致**（同 binding、同 prefix、同核心函数），本面不造第二条写语义。
- **步进回滚**：rollback 在 `action=="set"` 记录中找最近「from ≠ 当前值」恢复点；**rollback 标记不是恢复点**（否则连续回滚在「回滚前值」上震荡——单测 `test_rollback_restores_previous_mode_stepwise` 钉 off→shadow→live 逐级步进 + 史尽 409）。
- **史损坏不阻断**：损坏 JSON 条目跳过（`_decode_entry` 归一 CapabilityError），可用恢复点照常可达；史写入失败不阻断翻转（权威动作优先），响应 `history_recorded=false` 如实标注。
- **词表外 mode 显式 400，不静默回落**：`normalize_mode` 的 fallback 槽被借作哨兵——运维面写错词绝不能被悄悄改写成 fallback_mode（`test_invalid_mode_rejected_not_coerced`）。
- **Redis 缺席拒写（503）**：核心 `write_mode` 对 None client 只 log 不落盘——单测语义下安全，运维面就是把 no-op 冒充成功；本面 fail-closed 拒绝（`test_set_mode_redis_unavailable_503`）。读路径不受限（可观测性降级而非不可用）。
- **取舍：史存 Redis 不落 DB**——引擎重启不丢、跨 worker 共享、零迁移；审计级持久史（DB/EventBus 落账）留后续卡评估（OPS_SURFACE.md §6 明示）。注意：auto_degrade 自身的 EventBus 审计 publish 存在 **V3-FIX-491** 形参错位（本 base 在册），本面**不经过**该路径，避免同病灶。

### Work 3「release manifest 记录 model/config/migration」→ 只读装配、fail-soft 如实降级

- `build_release_manifest()`：`model`（LLM_PROVIDER/LLM_MODEL_NAME/LLM_REASON_MODEL_NAME/BATCH_LLM_PROVIDER/EMBEDDING_MODEL，settings 投影）+ `config`（**release 五旗取 `release_flags_response()` 冻结契约键集**，与移动端解码面同形——不是 settings 字段名视图；64 能力 settings 判据快照，纯进程内可算、无 Redis 依赖）+ `migration`（DB `alembic_version` 表只读查询 vs 代码侧 `ScriptDirectory.get_current_head()` 对账，branch-tag 集合相等语义）。
- **任一源缺席/失败 → null + error 注记，绝不伪造**（Forbidden #2）：db=None 时 `database_revision=null`、`error` 注记（`test_release_manifest_snapshot_shape` / sqlite 无表用例双钉）。
- manifest 不含 git SHA：运行时进程不可靠自证构建 SHA，伪造不如缺席；build-time 注入属部署面（O-01 staging 域），不越界。

### 验收「shadow/live 切换不丢用户 state」的论证与证据

结构论证：本面写键=能力模式键（`prefix+redis_key`，全仓唯一对账），从不触碰 `user*`/`memory*` 键；模式读取每次走 read_mode，无缓存陈旧窗（doc_context 的 record_gauge=False 与本面无关，读值同源）。实证：单测 `test_mode_switch_never_touches_user_state` + api 测试 `test_mode_switch_does_not_touch_user_state_keys`（哨兵用户键在 翻转→回滚 全程逐字不变）+ smoke 脚本第 4 项检查同语义。

## 3. 实现面（全部改动清单）

| 文件 | 性质 |
|---|---|
| `backend/app/core/ops_surface.py`（新） | 注册表 64 spec + 惰性解析 + 受控翻转/回滚/史 + 异常词表 |
| `backend/app/core/release_manifest.py`（新） | manifest 装配（model/config/migration，fail-soft） |
| `backend/app/api/internal/ops_release.py`（新） | `/api/internal/ops` 五端点，INTERNAL_API_KEY（同 auto_degrade 语义：未配置 500/缺席 401/不符 401/常数时间比较） |
| `backend/app/main.py`（+5 行） | 挂载 ops_release_router（紧随 auto_degrade 惯例） |
| `backend/app/config/settings.py`（+4 行） | 补注册 `AURORA_META_LEARNING_ROUTING_PARAMS_MODE="off"`（缺席等价，零行为变化） |
| `scripts/ops_rollback_smoke.py`（新） | 冒烟工具：默认进程内 fakeredis；`--redis-url` 需 `--i-understand-this-flips-real-capabilities` + `--capability` 双显式，且**硬编码只翻 `shadow` 并回滚**（本工具永不写 off/live，无批量端点）——「绝不实现默认开启的真实 destructive 操作」 |
| `backend/tests/unit/test_ops_surface_registry.py`（新，21 用例） | AST 生成式对账（覆盖↔幽灵双向）/不变量族（id 唯一、=stage.feature、settings 字段在场、domain 封闭、redis 键唯一、prefix↔拥有方常量对账）/翻转回滚史行为族/manifest 形状族 |
| `backend/tests/api/test_ops_release_api.py`（新，17 用例） | 鉴权四态/可观测/翻转回滚往返/404/400/409/503/哨兵用户键/manifest |
| `v3/08_operations/OPS_SURFACE.md`（新） | 操作面入口文档 |
| `v3/06_agent_fleet/DYNAMIC_ISSUES.md`（+2 行） | V3-FIX-501/500 登记（`ledger_union_merge.py --verify` 通过：339 行、ID 无重号） |

鉴权助手为 ops_release 模块本地副本（8 行，hmac.compare_digest）：auto_degrade 的同名助手是模块私有，抽取共享需改既有守卫文件、扩大爆炸半径；两侧语义由各自测试独立钉住（`TestAuth::test_unconfigured_key_fails_closed_500` 同款先例）。

## 4. 验证实录（本机 macOS/arm64，worktree 内）

- **pytest（38 新用例全绿）**：`tests/unit/test_ops_surface_registry.py` 21 + `tests/api/test_ops_release_api.py` 17 = **38 passed**。
- **触达面回归（99+12 全绿）**：`test_release_flag_authority` / `test_shop_entry_gate` / `test_visual_elements_gate` / `test_v3_fix231_ve_gate_contract_single_authority` / `test_slo_auto_degrade_api` / `test_dual_core_router_kill_switch` / `test_av_kill_switch_guard` = 99 passed；`test_startup_smoke`（main.py 导入/实例化烟测，覆盖新 router 挂载）= 12 passed。
- **守卫**：`check_rule_av_kill_switch_mode_enum.py` PASS（65 mode settings / 23 services——含新补字段）；`check_aurora_config_consistency.py` PASS（settings/.env.example/compose 对齐未破坏——新字段刻意**不**入 .env.example：守卫「remains 'off' 需白名单」规则与 managed key 反查机制下，settings-only 补注册是唯一零副作用的合法形态）。
- **mypy 零新增**：本 worktree `mypy app` 全量 **94 条**（与派单基线 94 逐字一致）；触达五文件中仅 `app/main.py:269` 一条，与主线仓同点同文（既有，非本卡引入）；三个新模块单独 mypy 零错误。与主线仓 diff 仅 +auto_degrade:152-153 与 +plan_review:939 两条——即 **V3-FIX-491/492**（wt754 已在集成侧修、本 base 3cbeb4a7 早于该合并），非本卡新增。CI 棘轮口径（`scripts/ci/mypy_ratchet.sh`，基线 380）按平台代际差注记，本地 94≪380。
- **ruff**：触达 8 文件全过（修一处 UP033 `lru_cache(maxsize=None)`→`cache`）；black --line-length 120 已套用并复检。
- **smoke**：`scripts/ops_rollback_smoke.py` 进程内实跑 PASS（baseline live → 翻 shadow（史记录）→ 回滚恢复 live → 哨兵用户键逐字不变 → SMOKE OK）；`--redis-url` 无确认旗 → `REFUSING` 实录。
- **台账**：`ledger_union_merge.py --verify` 通过。
- 注：worktree 缺 gitignored 生成产物，按 wt369/J-05/wt757 先例自主线仓 `cp -RL backend/app/gen`（不入库、永不手改）；未 push；未碰 docker/运行栈/.env（测试以 SECRET_KEY/ENVIRONMENT 环境变量注入，不依赖也不触碰 .env 文件）。

## 5. 边界与残余（不藏账）

- **依赖卡状态**：A-01/X-05 done、O-01 TODO——O-06 不依赖 staging 存在，本面在 localhost 栈同样成立；O-05（Backup/Restore 演练）未做，回滚演练栈面由其承接时可直接复用本 smoke。
- **acceptance 第二句「rollback smoke 通过」的证据等级**：进程内 fakeredis（Redis 协议真语义）+ 单测/脚本三重覆盖；升栈演练（晨 07:35 升栈面不冲突，本卡不动运行栈）可在 integration HEAD 用 `--redis-url <staging>` + `--i-understand...` 复跑一次即得栈面证据——脚本已为此备好，未替 reviewer 跑（Forbidden #3：不以静态阅读宣称通过，也不越权动栈）。
- **回滚史 TTL 30 天/20 条**：工程取值（覆盖一个发布周期），无历史数据支撑调优；上线后按翻转频度复核。
- **5 个 SLO 绑定进 registry 但其自动化写方（webhook）不写史**：auto_degrade 的翻转不经 ops_surface，史只有人工操作面动作——自动化动作的审计归其自身事件面（V3-FIX-491 修复后）。注册表对它们仍提供可观测与人工兜底翻转。
- **register-iff-read 的机器化**：AST 扫描限定 `KillSwitchBinding(...)` 调用的 `settings_attr` 字面量；若未来绑定改非字面量传参，对账会漏（守卫退化为弱断言）——真实风险低（全部 64 处现皆字面量），届时可在守卫内加 lint。

## 6. 证据索引

- base SHA `3cbeb4a7`（分支首 commit 即本卡交付，SHA 见 commit 记录）
- 新用例 38 + 触达回归 99 + 启动烟测 12，全绿实录见 §4
- smoke PASS 实录见 §4；守卫 PASS 见 §4
- 台账登记：V3-FIX-501（P3，5 proxy 绕核心）/ V3-FIX-500（P4，AURORA_DEFAULT_MODE 零读者），grep 复核主仓+worktree 双 0 命中后预占
