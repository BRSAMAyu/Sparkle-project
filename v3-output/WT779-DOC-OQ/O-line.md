# O 线（Ops 7 卡）深挖章节 —— V4 交接文档素材（wt779）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」O 线章节的深挖草稿。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt779（2026-09-28）。**基线说明**：本档开写时 main@b12125ed，撰写中途主干推进（wt773 O-05 交付集成轮#269、wt777 探针收口轮#270、wt780 度量章轮#271、wt778 mypy 批十一），本档已随 `git reset --hard` 追平至 main@c0306be1 后定稿——O-05 的「交付待审」态、FIX-524~530 等新账均按新基线收录。方法：卡面（v3/07_tasks/cards/O-0*.md）+ `git log`/wt759 报告逐卡定位 → 全部交付 SHA `merge-base --is-ancestor` 亲证祖先（O-02 `1ac2ec17`/O-03 `d475d8be`/O-04 `c86a6237`/O-07 `ea0167ca`+`864edcb1`/O-06 `1ca6c2dc`+`a376dbdb`+`e06d50ff`/O-05 `1680d16c` 全过）→ 代码开文件亲证（trace_spine.py/entitlement.py 双侧/budget_matrix.py/queue_backpressure.py/ops_surface 注册表面/llm_safety._mask_match/memory_storage_gate R9 前闸/gateway user_context.go 判官）→ 测试实跑（**O+Q 线全部交付测试套件 445 passed** @c0306be1，含 O 线 10 文件 359 用例与 Q 线 4 套件）→ receipt/演练产物抽读（WT765 notes、WT771 receipt、WT773-O05/drill 四件产物、HUMAN_INBOX/HANDOVER）→ 台账闭环逐条复核。**未轻信任何台账/报告结论性文字。**

---

## O.0 线级概览

O 线是 V3 的「运维真实线」：可观测脊柱（O-02）→ 安全终审（O-03）→ 付费解耦（O-04）→ 成本/配额/背压（O-07）→ 统一操作面（O-06）→ 备份恢复演练（O-05）→ 公网部署（O-01）。当前 **5/7 done + O-05 交付待独立审查**（tasks.json@c0306be1 亲证：O-01/O-05 TODO，O-02/03/04/06/07 done；O-05 交付本体 `1680d16c` 已在主干）。

O 线执行形态最重要的特点（V4 设计者必须先读）：**O 线的「就绪度」必须按三层分开看，混读会高估**——

1. **机制层（代码+测试，全部在库且本次实跑绿）**：O-02/03/04/07 四卡（09-21 首批，R2 PASS 签收在 commit）+ O-06（09-28 双审查链）。这一层是真实且可复跑的。
2. **演练层（运行级实录，环境受限）**：O-06 的真栈 shadow 回滚是 wt771 审查用**本机 docker sparkle_redis** 跑出来的（事故与恢复全记录）；O-05 的演练是 wt773 **一次性容器栈**（零触碰常驻栈）跑出来的。两次演练都是 localhost 形态——**staging 级演练从未发生**（等 O-01）。
3. **生产部署层（零交付）**：O-01 未启动。本地 docker compose 栈是**唯一已验证运行形态**（与主档 §8-4 一致）。V3-9 Commercial Gate 的「HTTPS 远程环境可部署」「RC 一键 smoke+rollback runbook」两款在远端意义上整体 BLOCKED。

**O 线的第二特点：它是全舰队供血最多的被依赖线**——O-04 的 entitlement 判官被 O-07 budget_matrix 消费；O-07 的 queue_backpressure/safe_error_messages 成为 Q-06 波动注入修复（FIX-78/79）的落点基底（safe_error_messages.py 50→191 行的增长即 Q-06 修复所致，`git log` 亲证）；O-06 的 release manifest 端点是 Q-08 RC manifest 的直接前身；O-05 的 restore_consistency_check.py（INV-1..7）是 Q-07 restore storm 的现成判据。**V4 若裁撤 O 线任何一卡的面，先查这条依赖网。**

---

## O.1 意图（卡面目标与验收）

七卡共性 Forbidden 条款（卡面原文，全线一致）：不得重建已存在的权威真源；不得用 mock/seed 冒充真实行为；不得只通过静态代码阅读宣称用户体验通过；不得弱化既有安全/幂等/隔离/审计守卫。

| 卡 | Risk/Resource/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| O-01 公网 Staging HTTPS/WSS 一键部署 | high/HEAVY/2 | fresh device 不依赖 localhost，真实产品运行环境 | GJ01 远端设备通过；密钥不在 client bundle；部署/rollback 文档+smoke 脚本 |
| O-02 End-to-End Trace/Metrics Spine | medium/MEDIUM/1 | 贯穿 UI→Gateway→Context→Aurora→LLM→Run→Outcome 的 trace | 任一 GJ 能用 trace_id 还原关键阶段/actual model/receipt；latency/cost/context 关联；日志不记 Memory/PII 正文 |
| O-03 Secrets/Prompt Injection/Tool Permission 安全终审 | critical/MEDIUM/2 | 防 prompt injection、tool escalation、secret leakage | 安全 adversarial suite 高危=0；tool permission 决定不由 prompt 文本覆盖 |
| O-04 Paid Entitlement 与 Flame/Gameification 解耦 | high/MEDIUM/2 | 修正 is_pro=flame_level 历史语义混用 | 改变 flame 不改变付费能力；付费状态变化正确生效；metrics 能区分 plan |
| O-05 Backup/Restore+Agent Run/Memory Consistency 演练 | critical/HEAVY/2 | 验证数据飞轮不是只能单机活着 | 恢复后 GJ03/GJ08/run query 通过；无已删 memory 复活；RPO/RTO 实测 |
| O-06 Kill Switch/Release/Rollback 统一操作面 | high/MEDIUM/2 | Aurora/Memory/Agent 新能力可 off/shadow/live 并安全回滚 | shadow/live 切换不丢用户 state；rollback smoke 通过；flag 状态可观测 |
| O-07 成本/配额/Queue 生产预算与 Graceful Degradation | high/MEDIUM/2 | 成本控制与用户价值关联，避免 Agent/Batch 失控 | provider/Redis/queue 故障不无界成本不全站假成功；额度耗尽有可理解 UX |

---

## O.2 实际交付逐卡

### O-01 · 公网 Staging HTTPS/WSS 一键部署 —— 未启动（卡凭据，非卡弹药）

**状态：TODO，零交付 commit**（wt759 §1 亲证「无任何交付 commit」+本次 `git log --grep` 复核一致）。阻塞点是**用户动作不是弹药**：

- 阻塞链：中央收件箱 **H-002**「阿里云 TCC 开关确认+ZCode 重启」（v3/08_operations/HUMAN_INBOX.md:10，OPEN）；HANDOVER-20260925 §2-7 记录凭据三选一（粘 AK/IAB 扫码/装 Chrome 扩展）AskUserQuestion 多次超时未答；fleet notes 09-25 轮已探明「computer-use 的 TCC 实际未生效（主体 dev.zcode.cua-helper 未被勾选）→浏览器路阻塞用户动作」。
- **弹药现状（本机 2026-09-28 实测）**：`/tmp/sparkle_cloud_secrets/{env.prod,jwt_private.pem,jwt_public.pem}` **在盘**（HANDOVER 所记 /tmp/sparkle_src.tar.gz 未复核）；ECS i-2ze439t934c2gsdqm778 已配好（HANDOVER §2-7）；workbench CLI+skill 已装。
- **部署资产在库清单（本次亲证）**：`docker-compose.prod.yml`；`deploy/{deploy-prod.sh, deploy_k8s.sh, verify_deployment.sh, backup_prod_data.sh, restore_prod_data.sh, install_backup_cron.sh}`；`scripts/chaos_drill.sh`。即 O-01 的工程面准备度远高于零——缺的是远端执行+验证+staging 文档化。
- **被它单点阻塞的面**（V4 排期必读）：O-05 的 staging 升栈面、Q-02 GJ19 remote 段（wt394 已如实 RESTRICTED）、Q-07 remote 腿、Q-08 的 V3-9 gate、DoD V3-9 整款。

**残差**：无交付即无残差；但 /tmp 弹药易失（重启即清），V4 若接手应先把 secrets/源码包转移到持久位置再等凭据。

### O-02 · End-to-End Trace / Metrics Spine —— done（`1ac2ec17`，09-21，R2 PASS）

**交付（主干 SHA 祖先亲证+开文件亲证 @c0306be1）**：

| 面 | 内容 | 本次亲证 |
|---|---|---|
| 脊柱模块 | `backend/app/core/trace_spine.py`（交付 225 行/现 223 行，漂移=wt285 lint 批）：单行 JSON span（`TRACE_SPINE {json}` 前缀解析锚点）；tag 收敛只放行标量+≤48 字符短串，其余一律 `<len=N,hash=h12>` 指纹（与 C-08 content_fingerprint 同算法，正文不可还原=PII/Memory 红线）；所有发射路径吞异常（观测永不阻断主链） | 开文件全读 |
| 9 阶段 span | orchestrator_entry / context_build / aurora_turn / plan_validate / route_decision / llm_call / graph_execute / final_compose / finish（+orchestrator_error） | orchestrator.py :2211/:2509/:2703/:3729/:3769/:3858/:4069 逐点亲证；llm_call span 在 llm_service.py:1857（actual model/token/cost/latency 四要素齐全=「任一 GJ 还原 actual model/receipt」的验收面） |
| 跨任务传播 | contextvar 在 graph worker task 不可达（行为学证明）→ 改经 state.context_data/user_context 传播 | orchestrator.py:2172 `context_data.get("trace_id")` 优先、缺失回退本 span OTel id；`sparkle.trace_id` OTel interop 属性 :2176 与 llm_service.py:1682 双写 |
| 网关侧 | 网关收客户端 trace_id 并注入 gRPC metadata | chat_orchestrator.go:541 收 `msgMap["trace_id"]`、agent/client.go:343 injectMetadata；mobile 侧 websocket_service.dart 含 trace_id（文件亲证） |
| 收尾锚 | **reviewer 加锚：finish span 在 finally**（早退路径无 recorder 判存在，失败绝不阻断清理） | orchestrator.py:4112-4120 开文件亲证 |
| 查询脚本 | `scripts/devtools/trace_timeline.py`（391 行，3 载体消费）+ 165 行脚本测试 | 文件+测试在库 |

**验证**：test_trace_spine.py 15 测 + test_trace_timeline_script.py 5 测，本次实跑绿（O 线批量 445 passed 内）。

**残差（V4 引用前必读）**：①「任一 GJ 能用 trace_id 还原」的验收证据是**单测/脚本级**——全库未定位到任何运行级「真 GJ trace_id→时间线重建」的 receipt 或产物（grep trace_timeline/TRACE_SPINE 于 v3-output/docs 零命中）；V4/终门应把「trace_timeline.py 对一条真实 GJ 的重建输出」补为 V3-6 gate 证据。②卡面 Work 3「dashboard **或**查询脚本」以脚本满足——又一例字面收窄（同 E-03 教学案例）；OBSERVABILITY.md 仅 20 行规划文档，无操作面板。③延迟/成本关联的数据面由 Q-06 400 样本 bench 承接（token/cost 计量经 billing worker 落库），O-02 自身无运行级读数在档。

**用户可见行为**：无直接可见面；它是「出事后能不能查」的基础设施。

### O-03 · Secrets/Prompt Injection/Tool Permission 安全终审 —— done（`d475d8be`，09-21，critical，R2 PASS）

**交付（commit message 逐项+代码亲证）**：

- **红线**：`decide_tool_permission` 纯函数签名封闭（inspect 钉住）；全部授权生产方服务端结构化；词表 fail-closed 过 10 个自造变体——「tool permission 决定不由 prompt 文本覆盖」的验收以**构造性证明**达成。
- **HIGH#1（反泄漏层自身记明文）**：viola­tions+异常消息带原始 secret → `_mask_match` 遮蔽（llm_safety.py:189-195 注记「O-03 HIGH#1 修复」；:237/:247/:254 三处调用亲证），8 类 secret 三面零明文。
- **HIGH#2（R9 稳定句式洗白绕过 FIX-41 敏感域 fail-closed）**：「总是头疼」类健康内容曾借 R9 stable-pattern 抢先 store 长期化 → 健康网+R9 前闸（memory_storage_gate.py:822-848 注记原文「O-03：『总是头疼』类健康内容曾借 R9 免确认长期化，重开」亲证），baseline-vs-fix 双臂 6/6 store→confirm。
- **对抗套件**：24 corpus × 3 污染点 × 3 层 + 16 组合 + 7 个新型绕过变体（嵌套代码围栏/西里尔同形字/零宽字符/RTL/截断），全部 write-denied；`test_o03_adversarial_security.py` 现 651 行 33 测（交付 622 行，+29 行=wt597 `9c5f4737` JSON 形态凭据漏检三处收口的后续加固——本档 git log 追踪亲证）。
- **诚实注记（commit 原文）**：「worker died pre-return at quota window; reviewer served as sole independent gate」——worker 进程在额度窗返回前死亡，R2 独立审查即唯一独立闸。签收形态合规但属孤例，V4 引用本卡审查强度时应知此背景。

**验证**：33 测本次实跑绿。**残差**：套件是离线 corpus 红队（确定性判据），无 LLM-in-the-loop 持续对抗面——与 Q-05（最终红队，43 场景五路）分工互补；卡面「高危=0」的判定域=本套件覆盖面，V4 扩攻击面时应重跑扩域。

### O-04 · Paid Entitlement 与 Flame 解耦 —— done（`c86a6237`，09-21，high，R2 PASS）

**交付（双侧单一判官，本档两侧开文件亲证）**：

- **引擎侧**：`backend/app/core/entitlement.py`（现 96 行）——`normalize_entitlement` 只有精确 'pro' 判 pro，未知/缺失/值域外一律 free（**宁降不升**：判级故障最多丢权益、绝不送成本）；docstring 明载历史病灶（「游客 flame_level 曾被 guest_seed 写到 15，导致全部游客以 is_pro=true 进 pro 层，真实付费用户反被压 free 层」）。
- **网关侧**：`backend/gateway/internal/service/user_context.go` :69-70「entitlement 是唯一的权益判据；flame_level 仅为展示层字段，**永久禁作权益派生**」+ `IsProEntitlement`/`IsProEntitlementEffective`（equal-fold + 到期降级）；两侧 docstring 互指「改动需同步」——双源同语义+同步义务成文。
- **请求级接线**：gRPC 入口以 users.entitlement 定 request tier → `_resolve_budget_dimensions` 消费（关闭 C-06 R-RISK-1：pro 用户曾被永久钳 free 预算）；plan 标签进 3 个路由 metrics（free/pro/unknown 封闭词表 `request_tier_label`），**flame 永不入 metrics**。
- **12 个 soul tests**：flame 1-10 零能力变化、free→pro 下请求生效（test_o04_entitlement_flame_decouple.py 12 测本次绿）。

**后续演进的存活证明（本档追踪）**：D-REDEEM 兑换码闭环（`e375ed62`）给 entitlement 加了 `entitlement_expires_at` 到期面——`entitlement_effective` 引擎/网关双侧同步扩展（NULL=永久，过期降级方向仍恒 pro→free），**解耦契约在扩展中存活**；wt688 mypy 批四只动类型。这是「单一判官+两侧同步义务」设计对后续演进的韧性实证。

**残差**：「付费状态变化正确生效」的运行级证据=测试面；V3 无真实支付 provider（商业面只有兑换码），staging 级真实支付流验收天然不存在——V4 若接支付，判级面已就绪、支付通道面全新。

### O-05 · Backup/Restore + 一致性演练 —— **交付待审**（`1680d16c` 已在主干，独立审查 wt782 在航）

**状态**：tasks.json 仍 TODO（审查未回，销账待 wt782 receipt——符合「worker 自称完成不算完成」验收模型）。交付本体随轮#269 集成（ fleet notes 原文「重大发现：既有备份链静默失效」）。

**重大发现（运维面最高价值的单笔发现）**：**V3 的生产备份链此前是静默失效的**——① backup pg_dump 缺 `--clean --if-exists`，恢复进非空库=假成功混合态（RED 实录：exit 0 + **2156 条被吞 SQL 错误**、漂移 ghost 行/硬删行缺失/run 状态推进全残留）；② MinIO 归档依赖容器内 tar，生产镜像（RELEASE.2025-09-07）无 tar → backup 实跑 exit 127，**cron 每晚 03:15 的备份从未产出完整包**（sha256sums/manifest 从未存在）。两者均已修复：dump 精确快照+restore ON_ERROR_STOP=1+连接排空+STRICT_SCHEMA 代差门+MinIO 改宿主 tar+manifest 增 alembic_head/pg 版本/耗时。

**演练实录（v3-output/WT773-O05/drill/ 四件产物，本次抽读亲证）**：一次性容器栈（零触碰常驻栈）——backup_manifest.json（PG 16.15/`--clean --if-exists`/alembic wt598_20260927/**backup 5s**）；restore 6s；7 表快照等价 12 项全过（ghost 清零/硬删行 PITR 找回/run 脊柱/outbox/processed_events 回备份点）；**restore_consistency_check.py INV-1..7 全 PASS verdict=PASS**（词表封闭/末条迁移投影/per-intent 活跃唯一/序列计数器不回填/墓碑完整/零孤儿/基线快照等价——479 行校验器+362 行 14 测在库）；恢复栈起 uvicorn+网关后 **GJ03 11/11 全真链路 PASS**、run query 三面 200；**GJ08 4/6 如实**（两个 real_llm chat 步无 key 走引擎 demo-mode 空回，引擎日志在案不伪造）。「无已删 memory 复活」由 INV-5 墓碑完整+Q-04 2b/2c 探针族双保险。

**RPO/RTO 如实判读**：RPO 由 cron 周期决定=**最坏 24h 丢失窗**（收紧/异地化属容量决策，install_backup_cron.sh 头注已登记 mc mirror 待办）；RTO 实测≈restore 6s+栈起。

**新增台账**：**V3-FIX-505**（P2，OPEN）——redis-stack 持久化 dir=/var/lib/redis-stack 与 compose 卷挂载 /data 错位：旧 restore 写 /data/dump.rdb 是**静默无效恢复**（keys loaded: 0 实录），prod 容器重建即 Redis 全损；脚本面已修（CONFIG GET dir 动态落盘，keys loaded: 2 实录），**compose/启动参数裁决 OPEN**——不加 `--dir /data` 或改挂载，prod Redis 耐久性=容器生命周期。**这是 O-05 留给 V4 的最高优先运维裁决项。**

**编号占位混乱（本档登记 V3-FIX-514，见 §O.5）**：交付 commit message 自称「V3-FIX-504/505」——其 504（备份脚本缺陷，卡内已修 RESOLVED）与 wt769 已占的 504 撞号，轮#269 记「撞号 504→520 已闭」但**台账从未存在 520 行**（本次 `git show` 于 1680d16c/9a4ea3d4/deb5e27c/7dfe1577 四个时点 grep 全零亲证）；卡内已修项无台账行本身合规（停手登记纪律的反面=修了不用登记），但 commit message 的 504 引用成了幻影指针——检索者会撞到 wt769 的 FIX-258 行。

### O-06 · Kill Switch / Release / Rollback 统一操作面 —— done（交付 `1ca6c2dc` → 独立审查 `a376dbdb` PARTIAL → 补丁采纳 `e06d50ff` 升 APPROVE → 销账 101/107）

**V3 后期唯一走完「实现→独立审查抓真运行级缺陷→补丁→APPROVE」全链的高风险卡**，审查链三笔全部主干祖先亲证。

**交付面（wt765 notes 逐项+本档复核）**：

- **注册表**：`ops_surface.py`（885 行）`CAPABILITY_SPECS` 对 **64 个既有三态绑定**（散在 27 模块，AST 扫描实测）做惰性走径索引（importlib+getattr，引用绑定对象本身零复制定义）；capability_id=`<binding.stage>.<binding.feature>` 与 Prometheus `KILL_SWITCH_MODE{stage,feature}` 标签逐字对齐（「flag 状态可观测」与既有 gauge 同一坐标系）；domain 封闭词表 aurora 53/memory 4/fme 2/infra 5。**registered-iff-read 机器化**：AST 生成式对账测试（漏登 spec 红/删绑定留幽灵 spec 红——wt771 双向变异抽验 7 failed 实录咬合）。
- **诚实补注册**：`AURORA_META_LEARNING_ROUTING_PARAMS_MODE` 声明在绑定而 Settings 权威字段缺席（env 通道死路）→ settings.py 补字段默认 "off"（与缺席等价零行为变化）——「注册新 flags」在本仓现实中的诚实落点是**补齐已声明未落地的 flag** 而非无读者造新旗。
- **未受控 live 实验扫雷两项，如实登记不顺手修**：**V3-FIX-500**（P4，OPEN）`AURORA_DEFAULT_MODE`「总默认」全仓零读者；**V3-FIX-501**（P3，OPEN）5 个元认知 confidence proxy 直读 settings 绕开 kill switch 核心（无 Redis 翻转/无 gauge/非法值判「启用」与三态回落语义相悖）。
- **per-capability 回滚**：写前快照压史（LPUSH/LTRIM 20/TTL 30 天）→ 步进恢复（rollback 标记非恢复点防震荡、损坏条目跳过、史尽 409）；词表外 mode 显式 400 不静默回落；Redis 缺席 503 拒写（不把 no-op 冒充成功）。
- **release manifest**：model/config/migration 三段只读装配，任一源缺席→null+error 注记绝不伪造；**不含 git SHA 是设计决定**（「运行时进程不可靠自证构建 SHA，伪造不如缺席；build-time 注入属部署面 O-01 域」）——Q-08 做 RC manifest 时必须处理这个缺口。
- **安全姿态**：`/api/internal/ops` 五端点 INTERNAL_API_KEY 常数时间比较；smoke 脚本默认进程内 fakeredis、真栈需双显式确认且**硬编码只翻 shadow 并自回滚、无批量端点**。

**独立审查价值实录（WT771 receipt，本档全文抽读）**：wt771 按「真栈 shadow 回滚实录铁律」执行，**抓获交付版实锤缺陷**——`--redis-url` 分支 `aioredis.from_url` 缺 `decode_responses=True`，bytes 客户端下 read_mode 取回 `b'shadow'` 被 normalize 成 fallback `"live"` → 回滚判无恢复点 → NoRollbackPointError 崩出且**翻转旗滞留 shadow**；审查现场字节级恢复（DEL 自建 3 键，扫描双空）+离线 fakeredis bytes 探针证实根因；reviewer patch 后同栈复跑 exit 0。 Forbidden #3「不以静态阅读宣称通过」被评「部分违反（轻）」——wt765 声称「栈面证据脚本已备好」恰是静态结论。补丁采纳（`e06d50ff`：decode_responses+异常时恢复 baseline 非零退出）后升 APPROVE 销账。**这是验收模型（独立审查必须独立执行关键验收）价值的一次教科书级兑现。**

**后续**：层21 CI 红揭示 O-06 五路由未登记网关 parity → 修复 `8d59598c` 登记 **ENGINE_ONLY**（设计判断原文：「kill switch 必须在网关自身被回滚时仍可达，控制面不依赖被控面」——本档认为这是本卡最重要的架构裁决，V4 的控制面设计应继承）。

**残差**：① 回滚史 TTL 30 天/20 条为工程取值无数据支撑；② 5 个 SLO 绑定的自动化写方（auto_degrade webhook）不经 ops_surface、不写史（自动化动作审计归自身事件面）；③ **字面量 prefix 守卫洞**（receipt §5-5 建议的对 `"sparkle:"/"aurora:"` 字面量家族调用点 AST 扫描，至今未采纳——test_ops_surface_registry.py:101 整族跳过亲证；若 spec 抄错字面量 prefix 会产生「翻一个没人读的键」的静默 no-op）；④ **钉住值语义**（receipt §5-2b）：翻转+回滚会在 Redis 留下与 settings 同值的钉，此后改 env 默认不再生效且本面无 DEL 键操作——建议的 OPS_SURFACE.md 运维注记未见追加；⑤ 升栈演练证据（staging+`--redis-url`）待 O-01。

### O-07 · 成本/配额/Queue 生产预算与 Graceful Degradation —— done（本体 `ea0167ca` + P2-7 `864edcb1`，验收 PASS_WITH_P2）

**交付（六件套，全部开文件亲证）**：

| 面 | 内容 | 关键判据 |
|---|---|---|
| budget_matrix | entitlement→四维 run 限额薄派生（free 150k tok/$0.5/50 tools/1800s；pro 600k/$2/200/3600s）；**判级唯一走 entitlement、派生值过 X-06 normalize_budget 单一校验面**（不造第二套预算形状） | settings.py:515-519 默认值在库；`RUN_BUDGET_DEFAULTS_ENABLED` 可关；配置为空→「run stays unlimited this creation」**仅 WARNING**（模块自定位「best-effort 收紧非可用性闸门」——诚实但 V4 应知此 fail-open 边界） |
| queue_backpressure | celery_dispatch 投递 choke point：LLEN 超限丢弃不 send_task+`sparkle_queue_backpressure_drops_total`+WARNING；glm_batch 上限 200/默认 1000；LLEN 与 send_task 同 broker 连接 | queue_backpressure.py（现 335 行）结构亲证；上限默认 settings.py:527-530 |
| 预算熔断 | BudgetCircuitBreaker：Redis 故障退**进程内保守累计**（成本仍有 per-process 上界，非 fail-open），恢复回落真值+fallback metric 留痕 | test_o07_cost_redis_bounded_degrade.py 9 测 |
| 超预算 UX | chat 流式补发确定性双语收尾说明（零 LLM）+gRPC 错误映射「发生了什么+怎么办」（RATE_LIMITED+retryable），变异红证钉死不被 provider 分支误吸 | safe_error_messages.py（现 191 行） |
| cost/WVPL metrics | 日成本/D-06 loops_total→`sparkle_cost_per_wvpl_usd`；**loops=0 不写不伪造**；beat 05:10 low_priority | cost_wvpl_metrics.py+worker 亲证；分母注释「7 日窗口 WVPL loop 数」 |
| P2-7 背压收口 | 摸底 37 处直发点：36 改接统一背压投递面（dispatch_task_async 薄壳化）；**保留 1**：users.py purge_deleted_account（30 天 ETA GDPR 硬删除——丢弃=静默取消删除语义不可接受）+静态守卫 allowlist | `864edcb1`；禁新增直发点守卫 `test_no_direct_dispatch_outside_allowlist` :341 亲证 |

**验收实录（commit message）**：单员全权 PASS_WITH_P2——224 重跑零失败、4 变异 11 红证、真 broker 201 深度拒投探针、超预算 UX 全链探针；默认限额裁决 ACCEPT（dev 实测均值 2856 tok/req，余量 9×）；P2×7 登记→P2-7 即时收口（上表）。

**跨线供血（本档追踪）**：O-07 的 queue_backpressure/celery_dispatch/safe_error_messages 是 Q-06 波动注入修复（FIX-78 全断供快速失败/FIX-79 过载背压，`3717355e`）的落点——safe_error_messages.py 50→191 行的增长即 Q-06 修复所致。其观察移交项「generate_capsules_batch 显式 default 队列（疑似事故同模式漏改）」由后续 P3 sweep `a8937be9` 修复（celery_app.py task_routes 现指向 glm_batch，本档亲证）——**O-07 的观察-移交-闭环链完整**。

**残差**：① cost/WVPL 指标有计数器面无运行级读数在档（分母依赖 D-06 north-star fact 的生产数据——JOURNEY ns001 七日驱动是唯一真实分母来源）；② 预算派生的空配置 fail-open 边界（见上表）；③ 全链运行级「额度耗尽 UX」验收是探针级（A2 预算 UX 全链探针），无长周期真实耗尽案例。

---

## O.3 设计决定与取舍（从提交/审查考古）

1. **宁降不升的 fail-safe 指向全线一致**（O-04 判级/O-07 预算派生/O-06 词表外 400）：判级/预算/翻转的故障方向恒为「丢权益/不 flip/拒绝」，绝不「送成本/静默改写/冒充成功」——O-06 notes 把它说成「成本 fail-safe」哲学，是本线最一致的设计签名。
2. **不重建权威——薄派生+惰性走径+单一判官**（Forbidden #1 的正面执行）：O-06 注册表引用绑定对象本身、O-07 派生值过既有 normalize_budget、O-04 单一 judge 双侧同语义+成文同步义务。代价：字面量形态的对账盲区（O-06 prefix 守卫洞）与两侧漂移风险（靠 docstring 纪律维持）。
3. **控制面与被控面分离**（O-06 + 层21 ENGINE_ONLY 裁决）：kill switch 控制面挂引擎 INTERNAL_API_KEY 且不依赖网关存活——「网关被回滚时仍可翻旗」。V4 的运维面拓扑应继承此判断。
4. **危险操作的多层确认与不可逆操作的结构性排除**（O-06 smoke 双显式+只 shadow+无批量端点+503 拒写；O-07 P2-7 对 GDPR 删除任务的唯一豁免+静态守卫）：不是靠流程纪律而是靠「脚本里没有那个能力」。
5. **观测/降级永不伪造**（O-02 span 吞异常但 PII 指纹化；O-06 manifest fail-soft null+error；O-07 loops=0 不写不伪造；O-05 GJ08 4/6 如实空回）：失败可见、缺席诚实，与全库「不静默兜底」教义同源。
6. **演练宁可一次性容器栈也不碰常驻栈**（O-05）与**审查必须真栈执行**（O-06 wt771 铁律）：两条纪律合力把「运维能力」从代码存在性推进到运行级证据，同时也暴露了 staging 缺位时运行级证据的天花板（全部 localhost 形态）。

---

## O.4 残差与 V4 注意点（汇总）

1. **O-01 是单点也是天花板**：V3-9 gate、Q-02 GJ19、Q-07 remote 腿、全部 staging 级演练都挂在用户 TCC 一个动作上；弹药（secrets/ECS/部署脚本）全部就绪且部分易失（/tmp）。**V4 排期应把「凭据到手」建模为随机事件：先做本地容器栈能做的一切（O-05 判例），remote 段显式 RESTRICTED。**
2. **O-05 交付待审 + FIX-505 OPEN 残差是当前最高优先运维项**：prod Redis 耐久性=容器生命周期（redis dir≠compose 卷）待 compose/启动参数裁决；RPO 最坏 24h。这两个是「数据会不会丢」级的问题，优先级高于本线其余全部残差。
3. **O-02 的运行级证据缺一口**：trace 脊柱机制真实（445 测内绿），但「真 GJ 用 trace_id 重建时间线」的运行级产物全库没有——终门/审计前用在库脚本 trace_timeline.py 跑一条真实 GJ 即可补上，成本极低。
4. **O-06 的三个未采纳建议**（prefix 守卫洞/钉住值运维注记/DB 级审计史）都在 receipt 里写明修法，属低成本收尾；FIX-500/501 两处声明-行为脱节仍 OPEN（A 线章亦引用）。
5. **O-03 的审查强度背景**：worker 额度窗死亡、reviewer 唯一独立闸——审查结论成立但孤例；V4 扩对抗面时应对本套件做一次双审查复跑。
6. **O-04 的契约韧性已验证**（D-REDEEM 扩展存活），V4 动权益面时唯一必须遵守的是「引擎/网关双侧同步」的成文义务（entitlement.py:19-20 / user_context.go:85 双侧注释）。
7. **O 线卡级 v3-output 证据目录形态**：O-06 有 WT765/WT771 目录、O-05 有 WT773-O05 目录（均为深挖/审查期产物）；O-02/03/04/07 首批四卡无卡级目录（签收在 commit message，wt759 已裁决合规形态）——无台账死指针（本档 grep 复核），按 wt774 先例作形态残差不占号。

---

## O.5 本次审查登记

- **V3-FIX-514**（P4，本次新登记，O 线章主登记）：O-05 交付 commit `1680d16c` 的 message 自称「V3-FIX-504/505」，其中 504 为**幻影号**——该号实属 wt769（FIX-258 行闭账指针）；轮#269 fleet note 记「撞号 504→520 已闭」，但 **V3-FIX-520 行在任何时点的台账中都不存在**（本档对 1680d16c/9a4ea3d4/deb5e27c/main-tip 四时点 `git show` grep 全零亲证）。后果：备份链静默失效（cron 夜备份从未产出完整包+restore 吞 2156 SQL 错）这笔 O 线最有运维价值的发现，在台账里**无行可稽**（缺陷本体已卡内修复故无 OPEN 行合规），唯二检索入口=commit message（错号）与 fleet note（对不上号的「520」）；V4 考古按号检索会错配到 wt769 行。可证伪判据：`git show 1680d16c --format=%B -s | grep 504` 命中而台账 `grep -c "V3-FIX-520"`=0；`grep "V3-FIX-504" v3/06_agent_fleet/DYNAMIC_ISSUES.md` 唯一内容为 wt769 的 258 行笔。修法方向：不动台账（无账可改）；在 O-05 独立审查 receipt（wt782 在航）与本章（已写）双处注记「备份脚本缺陷=卡内修复无台账行，检索锚=commit 1680d16c 本体，号 504/520 均无效」；ledger 工具可加「commit message 引用号 vs 台账行存在性」抽检（与 504/508 行修法建议同族合并）。
- **零号新登记两项（形态/残差照登不占号）**：①O-02/03/04/07 无卡级 v3-output 目录且无台账死指针——按 wt774 A 线先例作形态残差（§O.4-7）；②O-06 receipt 三条未采纳建议+FIX-500/501 OPEN——已在册或在 receipt 在案，本章 §O.4-4 复述不占号。
- 号占用核验：512-523/527 起空闲——`grep -c "V3-FIX-512\|V3-FIX-513"` HEAD 台账零命中；在册最高 530（530=wt780 后新 P1）；本档取 **514**（512/513 归兄弟章 Q-line.md，同批登记三号两章共用）。
