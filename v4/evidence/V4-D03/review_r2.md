# V4-D03 · 独立审查 receipt（二审 R2）

- **审查者**：wtD03R2（独立会话，未参与 D03 实现与一审）
- **审查对象**：`agent/v4/d03` @ `a24e368a`（实现 commit；一审 receipt `7995e3f3` 可读但本审独立下判）
- **审查方式**：只读实现 + 独立复跑 + 11 条自写对抗探针（跨卡交互 3 / 恢复对抗 4 / epoch 单调 1 / 读门穷举 3）+ 逐处实现审计；探针为临时 pytest 文件，跑毕即删（`git status` 终态干净），零修改实现面
- **总裁决**：**APPROVE（二审通过）。** 二审七靶（跨卡交互 / 恢复对抗 / epoch 单调 / 读门双出口 / W-1+C-1+C-4 复核 / 复跑 / limitations）全部无阻断发现；CHALLENGED = ∅。一审 C-1~C-4 定性全部复核属实，其中 **C-1 经本审量化后比一审表述更尖锐**（读门对该交错窗口的检测不是"大概率"而是**系统性漏检**，见 §4），修复建议升级为"读门接 epoch 为主、commit 前重读为辅"，仍不构成本卡回退（触发方未接线，无运行时暴露）。

---

## 1. 复跑（独立执行，SECRET_KEY=ci-test-key DATABASE_URL=sqlite://，共享 venv python 3.11.15）

| 批次 | 本审复跑 | 登记/一审 | 判定 |
|---|---|---|---|
| 34 新测（core 23 + services 11） | **34 passed** (4.93s) | 34 passed | ✅ 一致 |
| tests/services 全量 | **1047 passed, 10 skipped** (566.63s) | 1047+10 (453.86s) | ✅ 逐数一致 |
| mypy 全 app | **55 errors / 51 files**（`grep retraction` 命中 = **0**，新文件零 error 行） | 55 / baseline 77 | ✅ 零新增 |
| mypy 两新文件直检 | 30 errors 全部在依赖文件，retraction 两文件 0 | 同 | ✅ |

## 2. 靶1 · 跨卡交互（探针 P1–P3 亲跑全绿）

- **I01 续读视图（P1，实测）**：真实 `register_retraction`（sqlite 全 IO）bump epoch 1→2 后，撤回前装配、钉 `memory_epoch_at_compute=1` 的 `episode_resume_view.v1`（过 `validate_resume_view_shape`）经 `resume_view_stale_reason(current_memory_epoch=2)` 判 **`memory_epoch_changed`**；撤回后新建视图（钉 2）判新鲜。I01 freshness 经 epoch bump 判 stale **实测成立**，无第二计数器。
- **I06 回执（P2）**：receipt 是落账审计面，`input_versions.memory_epoch` 钉选择时点——撤回前落账回执钉 1、撤回后权威 2，**版本不一致可检出**（消费侧按 C-07 读侧门处理，不静默续用）；撤回后新装配回执钉新 epoch。M-07 记忆域的 `status:retracted` 理由仍映射 I06 封闭词表 `stale_epoch`（`rejection_reason_code` 亲测），D03 结果撤回**不改**记忆行 status，故不进该映射——两域边界干净，无分裂。
- **D02 归因（P3）**：`attribute_outcome` 纯函数在撤回前后对同一 (task 锚点， outcome) 判定**全等**（status/domain/matched_key/`sample_id`/observation_status 恒同）——归因与掌握度融合零共享 IO 态。**边界下判**：结果撤回移除的是该 outcome 对掌握度投影的证据贡献；outcome 本身仍是真实发生的事实行，`TruthClass` 冻结词表**无 retracted 成员**（亲测），账本行不动 → D02 归因样本**不降级、unattributed 分母形态不变**。这与 DATA_AND_GRAPH 对照指标「不能剔除难配对事件制造 100%」一致：撤回不构成把 outcome 剔出归因分母的理由。若未来出现"用户否认 outcome 发生过"的需求，那是 TruthClass 词表扩展（冻结词表，需 bump 版本 + 双 reviewer），不是掌握度撤回，归后续卡。
- **观察 R2-O3**：DATA_AND_GRAPH §撤回与重算列「节点/insight/**experience**」，卡面列「策略/insight/能力节点」，`DerivedFace` 词表 = capability_node/insight/strategy——experience 面不在契约词表。卡面是本卡任务权威，experience/其余派生面由 epoch 门间接保护（limitations #6，P1 对 I01 面做了实证补强）。登记为观察，非缺口。

## 3. 靶2 · 恢复对抗（探针 P4–P7 亲跑全绿）

- **crash①（P4）墓碑+bump 已执行、commit 前死**：登记主链墓碑 UPDATE + epoch bump + 事件 INSERT 同事务、恰一次 commit（service L203）——进程死等效整事务回滚。探针实测：回滚后 effect_kind 仍 evidence、epoch 未动、零事件行；重放登记收敛（tombstoned=1、epoch 恰 +1、事件恰 1 条）；直呼 G-01 重放 belief=20 非 42（**无复活**）。
- **crash②（P5）登记已 commit、重算前死**：重放方登记幂等检出 duplicate=True 零副作用（不双 bump、事件仍 1 条）；重算收敛 revision 恰 +1；读门 pending→fresh 转移正确。
- **crash③（P6）重算中途死（trace 写后、commit 前）**：ORM 分数变更与 trace INSERT **全部回滚**（分数 42 未写回、revision 0、零半个 trace 行）；重放重算收敛到权威回放值 20（非 42，无复活）、revision 恰 +1、trace 恰 1 行。**三个 crash 点全部收敛、全部无复活**。
- **双撤回并发（P7）**：同 outcome 两个 rtr id **结构上不可能**——id 内容寻址 (user, kind, target_type, target_id)，服务构造期把 kind 钉死 result_retracted、target_type 钉死 outcome（亲测同参数 id 恒等）。最坏交错（两进程都过幂等检出）按 limitation #3 的承诺形态仿写实测：2 条事件 + 冗余 bump（epoch 单调 +1，读者更 stale 的安全方向）+ 墓碑条件更新零行；此后重算收敛同值、revision 只 +1、重放幂等、读门 fresh——**冗余但零损坏、零复活**，与登记完全一致。

## 4. 靶3 · epoch 单调性（实现审计 + 探针 P8）

- **全仓扫描**：`memory_epoch` 的写实现恰两处——`MemoryService.bump_memory_epoch` 与 `_bump_memory_epoch_in_txn`——**均为相对自增** `UPDATE SET memory_epoch = memory_epoch + 1 ... RETURNING`（M-01 R2-F3）。调用源恰三处：M-07 管线 invalidate（L184）、memory_settings 权限变更（L85）、**D03 登记复用同函数**（service L191）。无第二计数器、无第二写路径。
- **回退不可能的结构保证**：唯一的绝对写 = 懒建 `memory_epoch=2`，仅当 settings 行缺席（UPDATE 零行）才触达，并发首 bump 撞 unique(user_id) → IntegrityError → 整事务中止重试收敛——不存在把已存在行写小的路径。PG 行级锁下并发相对自增各自得到自己的 +1 返回值，交错任意（含撤回 bump）终值 = 起点 +(bump 次数)，**严格单调**。
- **探针 P8 实测**：M-01 权限源 → 完整撤回登记 → M-07 管线源 → 再权限源交错，epoch 严格递增不回退；撤回重放 duplicate 不再 bump。

## 5. 靶4 · 读门双出口一致性（探针 P9–P11，一审④的独立复核）

- **P9 穷举矩阵**：3 status × 6 computed_epoch 形态（None/0/5/7/"7"/99）× 6 current_epoch 形态 = **108 组合全过**：不变量 `suggestions_allowed == not stale` 无一违例（**不存在分裂态**）；stale 恒带 `ui_marker=stale_recomputing`、新鲜恒 None；pending 无条件双出。
- **P10 世代边界**：相等=新鲜（发布即新鲜起点）；落后=过期；computed 未钉 fail-closed；current 未钉不越权代判（归消费面 C-07）；`"6"`/6.5 等强制转换不产生假新鲜（int(6.5)=6<7 stale；int(7.9)=7 不落后 fresh，语义正确）；词表外 status ValueError fail-loud。
- **P11 pending 无条件性**：25 种 epoch 形态组合下 pending 恒 stale+禁建议+带 marker——重算中不可能被任何世代放行。
- **观察 R2-O2**：computed_epoch > current_epoch 按新鲜（ P10 末项）——当前结构性不可达（computed_epoch 钉自 bump 返回值 ≤ current），如实注记不改判定。

## 6. 靶5 · W-1 勘误 + C-1/C-4 复核

- **W-1 复核**：manifest 原文「增量 29 = 本卡 11 + F02 等已并卡测试」——本审复跑 1047/10 与 manifest、一审逐数一致；「增量 29」的算术成立（D02 基线 1018 + 29 = 1047），归因短语不精确（F02 本体不在本分支）与一审 W-1 结论一致，**数字无问题、措辞已勘误在案**。
- **C-1 复核 + 量化（R2 收紧）**：窗口 = service L255 epoch 快照读 → 逐节点回放 SELECT → L329 commit。窗口内另一撤回 commit：栅栏对比的是**窗口起点**快照（非契约 docstring 的"发布时点"）→ 放行；回放值可能仍含被撤回效果并写进 `user_node_status`，至下次重算。**本审新增量化**：该交错下读门**系统性漏检**而非"大概率转 pending"——`event_outbox.created_at` 是 server_default `now()`（PG 事务开始时点，先于其 commit），而重算 trace 行 `created_at` 是 Python `datetime.now`（INSERT 语句时点，晚于撤回 commit）→ 恒有 `last_retraction_at < last_recompute_at` → 读门判**新鲜**。即：C-1 窗口内落下的撤回，capability 读门抓不到（墙钟序 + C-3 秒粒度双因），context/I01/profile 的 **epoch 门能抓到**（bump 已提交）。量级：窗口 = 单用户受影响节点的回放耗时（ms 级）；影响 = 一个可能微偏的投影值，下次重算自愈、账本干净、无复活。**修复建议升级**：消费卡（重算 job 调度）除 commit 前重读 epoch 外，**应把重算钉的 epoch 落进 trace（request_id 空位可用）并让 `capability_node_read_state` 切 epoch 比较（即 C-3 的修复）**——epoch 接线才是对该窗口的闭合修复，墙钟只是兜底。触发方未接线前无运行时暴露，维持非阻断。
- **C-4 复核（如实性实证）**：① UUID 裸绑定 sqlite 失败——独立微探针亲测 `ProgrammingError`（aiosqlite 不收 uuid.UUID 裸绑定）；② `_write_mastery_update_event` try/except 确吞为 warning（P7 的值变更重算实际走过该分支且测试全绿，证明吞错真实发生）；③ 两个 D03 测试文件 grep `galaxy.mastery.updated` = **零断言**——"零有效测试覆盖"**属实**；④ PG 原生 UUID 绑定（asyncpg）生产预期可用，判断成立。C-4 如实，移交消费卡不变。

## 7. limitations（9 条）与一审 C-2/C-3 定性复核

- 逐条对实现复读：#1 生产触发方未接线（全仓 `RetractionRecomputeService` 零生产消费者亲核）✅；#2 构造期拒绝非 result 组合 ✅；#3 有界竞态——P7 按其承诺的最坏形态复现，描述精确 ✅；#4 墓碑单列 UPDATE 保留审计列 ✅；#5 锚 NULL 防御分支不可达 ✅；#6 非星图面靠 epoch 门——P1 对 I01 面做了本审的实证补强（该条原为"未逐一端到端断言"，本审补上 I01 一面）✅；#7 读门用户级聚合 + 墙钟粒度 ✅（C-3 属实，且 §6 已证其在 C-1 窗口下还有时序序语义问题，修复方向不变）；#8 BG worktree 环境差异（未复验，环境性声明，一审已核主检出 PASS）✅；#9 无 UI 交付面、类型化出口承载验收③ ✅。
- C-2（服务层 excluded===retracted 构造满足、栅栏本体契约层在库）：复读属实，接线形态注记。

## 8. 结论

- 二审七靶全部通过；11 条对抗探针（P1–P11）亲跑全绿；34/1047/55 复跑逐数一致。
- **CHALLENGED = ∅**；无新缺口。新增非阻断观察 R2-O1（C-1 量化收紧：读门对窗口内撤回系统性漏检，修复以读门接 epoch 为主）/ R2-O2（computed>current 按新鲜，结构不可达注记）/ R2-O3（DerivedFace 无 design 文 experience 面，卡面权威内）/ W-2 维持（event_registry 注释描述契约终态，建议顺手勘误）。
- 一审 C-1~C-4、W-1 全部复核属实；C-1 修复建议按 §6 升级表述随本 receipt 移交消费卡。
- 本卡两审均 APPROVE，可按流程进入集成 SHA 复验与合并排队。

*所有数字与探针结论均为本审查者独立执行所得；探针临时文件已删，工作树终态干净。*
