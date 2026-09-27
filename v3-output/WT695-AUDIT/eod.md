# WT695 台账日终盘点与悬案整理（EOD Audit）

- 会话：wt695（node-b，纯文档单文件卡；不占 FIX 号）
- 基线：main HEAD `0b1f58e3`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt695-audit`，分支 `agent/node-b/wt695/audit`）
- 对象：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` 全表 287 行（行首 `| V3-FIX-` 计），只读，未改台账
- 方法：脚本按 7 列切分（转义 `\|` 还原）后按状态格前缀精确分类；287/287 行均 ≥8 列无残缺（唯一 9 列行 = V3-FIX-119，多出一格行尾补记注记，不影响分类）。抽样与统计脚本参数见 §5，可复现。

---

## 1. 状态分布（状态格形态 × 优先级交叉）

| 状态格形态 | P0 | P1 | P2 | P3 | P4 | 合计 |
|---|---:|---:|---:|---:|---:|---:|
| FIXED@（纯前缀引用） | 5 | 25 | 71 | 86 | 35 | **222** |
| CLOSED@ | 0 | 0 | 1 | 2 | 0 | **3** |
| WONTFIX@ | 0 | 0 | 1 | 0 | 0 | **1** |
| OPEN（纯） | 0 | 0 | 4 | 6 | 2 | **12** |
| OPEN［wt474分诊:可派发］ | 0 | 0 | 0 | 5 | 0 | **5** |
| OPEN［wt474分诊:备忘型］ | 0 | 0 | 0 | 7 | 0 | **7** |
| OPEN［wt474分诊:待拍板］ | 0 | 0 | 2 | 1 | 0 | **3** |
| OPEN·带注记（登记/待裁/部分修复/重编号等） | 0 | 0 | 1 | 16 | 6 | **23** |
| OPEN·补记FIXED@（实质已修，行状态待维护） | 0 | 1 | 4 | 1 | 0 | **6** |
| OPEN→FIXED@（转固注记，实质已修） | 0 | 0 | 0 | 2 | 3 | **5** |
| **合计** | **5** | **26** | **84** | **126** | **46** | **287** |

要点：

- 真实 OPEN 态（纯 OPEN + 三种分诊态 + 带注记）= **50 条**；实质已修但行状态仍挂 OPEN 前缀 = **11 条**（补记FIXED 6 + OPEN→FIXED 5），属台账卫生欠账而非悬案。
- CLOSED@ 仅 3 条（FIX-16/45/47），WONTFIX@ 1 条（FIX-341 整行）；另有行内子项 WONTFIX 1 处（FIX-379① @c46d5b97，行整体仍 OPEN）。
- P0 无悬案（5/5 全 FIXED@）；P1 无悬案（26 = 25 FIXED@ + 1 补记FIXED）。悬案全部落在 P2–P4。

## 2. 悬案清单（50 条 OPEN 态，三类）

### A 类：可自动派发修复 —— 33 条

**A1 独立小卡可直接派发（23 条）**

| 号 | 优先级 | 一句话 | T-归属 | 建议卡型 |
|---|---|---|---|---|
| FIX-22 | P3 | test_stage38_d3_persistence 覆写 sys.modules 不恢复，进程内 fake 永久驻留 | T-test-isolation-stage38 | LIGHT 小卡（fixture/finalizer 摘除） |
| FIX-175 | P3 | test_privacy_community_production 模块级假 app.gen 注入不恢复（与 22 同病） | T-privacy-fake-gen-isolation | LIGHT 小卡（与 22 并批） |
| FIX-176 | P3 | llm_router 测试被本地 .env tier override 污染 | 协调方主会话 | LIGHT 小卡（修法已处方：fixture 重建 settings 单例） |
| FIX-321 | P4 | 测试时钟风险面 43 文件残留（真风险窗=UTC 16:00–24:00Z） | T-待派 | LIGHT 批量小卡 ×2–3 |
| FIX-46 | P3 | outbox→Redis 桥缺，run.awaiting_user 发布点落空 | T-outbox-redis-bridge | MEDIUM 小卡（桥）；gen import 环境债随行备忘 |
| FIX-56 | P3 | 网关 chat 流崩溃 502 级联归因未定（仓内无显式熔断实现） | T-gateway-breaker-tuning | LIGHT 排查卡先行，排查后勘误归因再定配置面 |
| FIX-144 | P3 | friction 出口载荷携词牌短语进 metadata（142 同构） | T-utterance-matches-payload | LIGHT 小卡（计数/指纹投影，修法在案） |
| FIX-189 | P3 | conversational_extractor 直读 env 旁路 stage19 三态门 | ——（wt486 判可机械修） | MEDIUM 小卡（resolve_settings_mode 同构，186/21 判例） |
| FIX-191 | P2 | T36 重定向 `startsWith('/leaderboard')` 字面量被 COMM-LB 守卫打红 | —— | LIGHT 小卡（守卫豁免/字面量机械对齐） |
| FIX-192 | P3 | POST /community/posts visibility 硬编码 public，写侧不闸 | —— | MEDIUM 小卡（读写对称闸；公开策略若变另议） |
| FIX-193 | P3 | state_estimator 防抖 per-user 锁仅进程内，FastAPI 多 worker × Celery 跨进程双写残留 | —— | MEDIUM 小卡（跨进程锁/幂等） |
| FIX-198 | P2 | 「Aurora」名未引入即自称；首卡已落地，余 54 活键 | —— | LIGHT 跟随批（copy-aurora-intro 后续卡） |
| FIX-218 | P3 | age_client.add_vertex 声明 `-> str` 实可返 None，建图链静默消费 | —— | LIGHT/MEDIUM 小卡（空结果显式失败） |
| FIX-237 | P3 | ab_test assign_variant 声明 tuple 实可返 (None, False) | —— | 与 218 同族并批（类型谎收口） |
| FIX-258 | P3 | LLM demo 产出落库与真实产出 schema 层不可区分且喂记忆推断管线 | ——（wt533 登记） | MEDIUM（origin 标记/隔离，B-02 判例） |
| FIX-291 | P3 | ENUM-PARITY 守卫只扫 app/models/，models 外 6+ 族未入管 | T-guard 扩射程 | LIGHT 独立小卡（守卫扩表） |
| FIX-220 | P4 | l10n_agent_overlays 六镜像 45 键零引用孤儿 | —— | LIGHT 小卡（对齐 FIX-200/210 收割先例） |
| FIX-256 | P4 | gen-l10n 工具版本格式漂移：本机 flutter 3.41.3 对未改基线全文件 restyle | —— | LIGHT 小卡（钉版本/allowlist，含环境面） |
| FIX-261 | P4 | 批一收割 6 死键被 e720416f 复活，部分修复@b98c7ca1 后余 2 键 | —— | LIGHT 顺收小卡 |
| FIX-308 | P4 | 两处收尾 gather 无超时属隐式约定 | T-待派 | LIGHT 小卡（可与关停语义批并） |
| FIX-336 | P2 | per-tool-call 幂等键=尝试唯一非意图稳定，跨尝试重复副作用 | T-round2 结论（wt634 CONFIRMED） | MEDIUM（wt634 判定证据在案） |
| FIX-360 | P4 | ErrorMessages 默认分支直出 technicalMessage 穿透 zh 界面 | T-error-message-default-l10n | LIGHT 跟随卡（随 i18n 卡顺带） |
| FIX-181 | P2 | KNOWN_CODE_DEBT_LEDGER P1 #1/#2 旧 file:line 挂「未修」但缺陷已修，误导产品判断 | —— | LIGHT 文档同步小卡（纯文档） |

**A2 跟随卡·随既有卡族/迭代批捆绑，不独立开卡（10 条 = wt474 备忘型 7 条 + 3 条同性质；「跟随载体」一列为台账在案口径，标注◇者为本审计建议）**

| 号 | 优先级 | 一句话 | T-归属 | 跟随载体 |
|---|---|---|---|---|
| FIX-15 | P3 | M-02 gate 打磨（模态前缀绕过/裸工作日锚点/稳定性词表缺口） | T-m02-gate-polish | 随 M-05/M-09 评测迭代 |
| FIX-44 | P3 | M-02 门残留（「见底」「确诊」裸词仍存活，保守方向低优） | T-m02-gate-residue | 随 M-02 评测迭代 |
| FIX-38 | P3 | M-09 评测套件 follow-ups | T-m09-eval-polish | 随 M-09 评测迭代 |
| FIX-39 | P3 | M-08 旗标矩阵补全+历史回填 | T-m08-flag-backfill | 随 M-08 迭代 |
| FIX-30 | P3 | A-04 follow-ups（decide_joint 陷阱/to_dict 缺注记等，均不阻塞） | T-a04-followups | 与执行面投影点接线同批 |
| FIX-32 | P3 | X-05B follow-ups（once-set 键/cancel 白名单序/sweep 措辞） | T-x05b-followups | 与 X-09 故障恢复卡同批 |
| FIX-42 | P3 | X-09 follow-ups | T-x09-polish | 随 X-10 E2E 评测 |
| FIX-52 | P3 | 历史失败痕迹把新类型卡点系统性带偏（无双刃消解） | T-friction-fact-decay | 随 A-03 迭代 |
| FIX-161 | P3 | 池预算权威按单进程计，多进程倍数同时满载面无观测 | —— | ◇建议：随观测面/容量批 |
| FIX-162 | P3 | BillingWorker 自建引擎生命周期不入关停链 | —— | ◇建议：随生命周期/关停语义批 |

### B 类：需产品或设计裁决 —— 13 条

| 号 | 优先级 | 一句话 | T-归属/裁决事项 |
|---|---|---|---|
| FIX-97 | P2 | 纠正通道以「错位行动」为唯一输入源，诚实 no_action 饿死纠正记忆回路 | 产品拍板：无行动出口的第二纠正入口形态，与 FIX-49 降噪目标联合权衡 |
| FIX-174 | P2 | 网关 FIX-155 截断防线对引擎哨兵截断不可达 | 待拍板：与 FIX-160 合并裁决落地（产品拍板历史可见性后按备忘方案 A 一卡实现） |
| FIX-168 | P2 | 引擎哨兵后网关缓存退出结构盲区（部分文本+STOP 终帧以完整轮过网关） | 同 160/174 裁决联动，不单独裁决 |
| FIX-160 | P3 | 截断轮持久化残留（error 帧已下行仍 finalize 落库） | 产品拍板历史可见性；决策备忘在 FIX160_DECISION_MEMO.md |
| FIX-48 | P3 | 主动建议面打扰权衡（dismiss 冷却/退避/扫描频率/过期衰减） | 产品拍板：打扰权衡无工程单方面解 |
| FIX-188 | P3 | memory_inferred_write_lane 直读 env 旁路 stage20 三态门 | wt486 判「不可零风险行内修」，需裁决（legacy bool 语义即 shadow 布尔） |
| FIX-290 | P3 | focus streak 服务端下发与 mobile 本地计算双真源双时钟结构性打架 | T-设计裁决（主会话组织，可并入愿景对照轮） |
| FIX-299 | P3 | 证据账本全量重放对无 payload 证据行不重套数值 | T-待裁决后派卡（影子行甄别机制主会话组织） |
| FIX-358 | P3 | U-01 证据链悬空引用，指针诚实化已收、余悬空重建待裁 | 待裁（方向已明=不重建消失文件，以 INVENTORY_REFRESH 补位） |
| FIX-368 | P3 | dashboard golden 套件本机渲染环境整族漂移 | T-golden-baseline-env-provenance（基线唯一签发环境=流程裁决） |
| FIX-373 | P3 | 无名图标可点节点长尾 7 文件（allowlist 只降不升已钉） | T-待裁决（①-⑤机械补名但键面归 wt672 文案卡协调；⑥⑦结构性单开） |
| FIX-375 | P3 | U-02 残余双债：FirstActionCard 无标题层+折叠件低刺激档位接线 | 需卡视觉改版裁决（golden 真机基线背书后做；10/4 红线不入当期实施） |
| FIX-379 | P3 | X-07 run-step 契约移动端消费面缺口（①已 WONTFIX@c46d5b97） | T-待裁决（②③属新交互流设计；①机械项与键面卡协调） |

### C 类：需用户拍板 —— 0 条（HUMAN_INBOX 查重结论）

- v3 仓内**无中央 HUMAN_INBOX 登记册**；仅有的波次级收件箱文件（`v3-output/WT394-Q02-GOLDEN/HUMAN_INBOX.md`、`v3-output/WT395-G05-GALAXY/HUMAN_INBOX_G05_VISUAL.md`）各指向 V3-FIX-53/54，两者均已实质收口（53=OPEN 补记FIXED、54=FIXED），与当前 50 条悬案**零重合**。
- 悬案 50 条无一落入人类专属域（费用/商户/上线/法律/比赛提交）；B 类 13 条的「拍板」主体均为产品/设计侧（主会话组织），非真人工。
- 唯一挂人事项附着在**已 FIXED 行**：V3-FIX-293（eb1b6a28）行尾注记——生产库 user_streak_days 历史行 UTC 日回填的量化 SQL 需主会话对生产库人工执行（真错子集=源事件落在用户本地 00:00–07:59 的行）。建议按规程补登人类收件箱，避免随行闭账而遗失。

### 附注：疑陈旧/记录型（4 条，建议随下次扫陈处置，本卡不动表）

| 号 | 优先级 | 发现 |
|---|---|---|
| FIX-199 | P3 | 其全部面（onboardingArchitectureStep1-5Desc 键）已随 V3-FIX-342 onboarding 整目录下线消亡（现 HEAD 全仓零命中）——建议扫陈闭账为「面消亡」 |
| FIX-222 | P4 | 其描述的「6 行粘连、28 行被吞」在现台账已不存在（27/28 均独立成行），消解于 V3-FIX-279 的 W558-R2 回扫——可闭账 |
| FIX-285 | P3 | 交接 wt561 的粘连/双行/管形存量已由 wt561 交付并闭账为 V3-FIX-279——交接已完成，可随之收口 |
| FIX-317 | P4 | validate_message 拒绝门语义记录型备忘（触发条件在案），无卡可派、无需裁决，维持 OPEN 备忘 |

## 3. 修复波完整性抽查（FIX-329~379）

**抽样框**：329–379 号段共 44 行（FIXED@ 36、OPEN 7、WONTFIX 1；349/364/366/367/369/376/377 为号段空洞未登记）。抽样：`random.seed(695)` 从 36 条 FIXED@ 抽 12 条：**329、333、339、342、345、346、347、353、355、359、361、363**。

**结论：内容链 12/12 完整，引链 0/12 可达。**

- **引链（FIXED@ 引用的 commit 是否 main 祖先）**：0/12。10 条显式 SHA 全部 `git merge-base --is-ancestor → NOT-REACHABLE`（对象存在但不在 main 历史）；2 条别名引用（FIXED@wt685）无 SHA 可直验。
- **内容链**：12/12。每条均在 main 上定位到同主题集成提交，`git show | git patch-id --stable` 比对**全等（EQUAL）**：

| FIX | 台账引用 SHA | main 可达 | main 集成提交 | 集成可达 | patch-id |
|---|---|---|---|---|---|
| 329 | 7f13c161 | 否 | a6b6e19b | 是 | EQUAL |
| 333 | cf120ca1 | 否 | e71a5df4 | 是 | EQUAL |
| 339 | d74ef092 | 否 | 92e750fb | 是 | EQUAL |
| 342 | 9268b35f | 否 | e610853e | 是 | EQUAL |
| 345 | e059cf05 | 否 | 66225669 | 是 | EQUAL |
| 346 | 3fec64f6 | 否 | 301eed3c | 是 | EQUAL |
| 347 | b4acf2d3 | 否 | b303dcbe | 是 | EQUAL |
| 353 | 2dde59a0 | 否 | 4130f984 | 是 | EQUAL |
| 355 | c8142703 | 否 | 936ae4f7 | 是 | EQUAL |
| 359 | 7a914a2c | 否 | b92ae2ec | 是 | EQUAL * |
| 361 | FIXED@wt685（别名） | — | 53414f8a（+台账 c3af4048） | 是 | — |
| 363 | fdd25867 | 否 | 6dfe2ad5 | 是 | EQUAL |

\* FIX-359 的 worker 与集成提交 subject 均误标「V3-FIX-357」（重编号期漂移），patch-id 全等 + 台账 359 行引用绑定证实即本行内容（删失语义拆分 not_determinable）。

**系统性背景（超出抽样要求的附加复测）**：全表 222 条 FIXED@ 中显式 SHA 引用 183 条，其中 main 可达仅 **14 条（7.7%）**、不可达 **169 条**；另 39 条为别名引用（FIXED@wtNNN/FIXED@卡名/FIXED@本卡 commit 等）。即「台账引用停在集成前 worker worktree 原 SHA、集成以同 patch 新 SHA 重提交」是**全台账系统性集成形态**，非本波独有。存量先例：V3-FIX-146 曾由 wt470「纠指可达整合 SHA」（714f474b→9f4c9f71），该纠指实践未推广。

**处置建议**（不在本卡执行，不占号）：集成闭账时以可达整合 SHA 落笔（或双写 `worker@SHA→integrated@SHA`）；可作台账卫生批一次性纠指，本卡 §3 的 patch-id 抽验方法可直接复用。169 条不可达引链未逐条做内容等价验证（仅本节 12 条抽样做了 patch-id 级验证），如实声明。

## 4. 台账卫生欠账清单（汇总，不动表）

- 实质已修行状态待维护 11 条：补记FIXED 6（FIX-09/10/23/53/61/62，其中 FIX-53 的补记自身即「行状态漏更新」却仍挂 OPEN 前缀）+ OPEN→FIXED 5（FIX-243/250/251/257/262）。
- 疑陈旧可闭 3 条：FIX-199（面消亡）、FIX-222/285（粘连存量已被 W558-R2 消解/交接兑现）。
- 引链纠指需求：183 条显式 SHA 引用中 169 条不可达（§3），建议一次性卫生批纠指为集成 SHA。
- HUMAN_INBOX 缺位：v3 无中央登记册，FIX-293 行尾挂人事项（生产库回填量化）建议补登。

## 5. 方法与可复现性

- 表解析：`^\| V3-FIX-\d+` 行首匹配 × `(?<!\\)\|` 切分（`\|` 还原），第 2 列 ID / 第 3 列 Severity（P0–P4 前缀）/ 第 7 列 Status；状态分类按前缀：`FIXED@`/`CLOSED@`/`WONTFIX`/`OPEN`（再分：纯 / `［wt474分诊:…］` 三态 / 带注记 / `补记FIXED@` / `OPEN→FIXED@`）。
- 抽样：`python3 random.seed(695); random.sample(36 条 FIXED@, 12)`，样本可复现。
- 验链：`git merge-base --is-ancestor <sha> HEAD`（HEAD=0b1f58e3=main tip）；内容等价：`git show <sha> | git patch-id --stable` 两两比对；别名引用以 `git log --grep="V3-FIX-NNN"` 定位闭账/集成提交。
- 已知局限：§3 全量复测只验了引用可达性（SHA 级），内容等价仅 12 条抽样验证到 patch-id 级；39 条别名引用未逐条定位。
