# V4-I10 二审 receipt（独立审查 R2）

- 审查会话：wtI10R2（未参与 I10 实现与一审）
- 审查对象：分支 `agent/v4/i10` 实现.commit `2ad27c96f9d916902262bb518d6d322935e87b23`（基线 `c67e45a3`）；一审 receipt @ `d40b5d25`
- 审查日期：2026-09-28 ｜ 方式：只读审查 + 差异化探针（3 个 sqlite 端到端探针测试，临时目录 /tmp，不入库）+ 独立复跑；零真模型、零预算消耗
- **总裁决：PASS_WITH_CHALLENGES（维持一审裁决，无阻塞新增）**——二审四项差异化靶全部完成并量化；一审三靶闭环结论未被推翻；新增 1 项升级 CHALLENGE（R2-C1，记录性）+ 2 项微观察。

## 0. 二审范围（差异化，不重复一审全量）

1. **R1-C1 深挖**：混合场景（实测帧+rescue）行级归因边界端到端实证 + 「sub_calls 切片披露是否足以让消费者不误读」判定；
2. **端到端账务一致性**：rescue 路径完整记账（真实 TokenTracker→queue:billing→BillingWorker→sqlite 实库读回），根行口径 vs 主-only 差值可对账性；
3. **幂等攻击面**：同 request_id 不同内容的落库行为 + 批内重复隔离 + 同 id 双写生产者普查；
4. **抽验**：真实 router 注册价存在性（生产现实面）+ 关键测试独立复跑。

## 1. R2-T1｜混合场景端到端（R1-C1 深挖，属实且量化）

探针设置：stub router 双价（main_model $0.010/1k、rescue_model $0.001/1k）；真实 `TokenTracker` + 捕获型 redis；`_cleanup(total 500+80 实测, rescue_metering 30+12@rescue_model)` → 队列载荷 → `BillingWorker._flush_to_db` → sqlite 读回 `token_usage` 行。

**归因边界（与 R1-C1 描述一致，逐项复现）**：
- 行级 `model=main_model`、`usage_source="measured"`、tokens 530+92（含 rescue 折入）——主生成有实测帧时归因不变、行级标签无 mixed 形态；
- `sub_calls[0]` 切片齐全（lane=generation_rescue、model_key=rescue_model、tokens 30+12、usage_source=estimated），但**无 per-slice 核价字段**。

**账务可对账性（无静默黑洞，口径唯一可推）**：

| 量 | 值 | 含义 |
|---|---|---|
| 根行 cost | $0.006220 | = 主价 × 622 tok（含 rescue），单一口径 |
| 主-only cost | $0.005800 | 500+80 按主价 |
| 差值 | $0.000420 | = rescue token × **主价**（rescue 被按主模型价折算） |
| rescue 真实成本 | $0.000042 | 30+12 按 rescue 价 |
| 高估 | $0.000378 | 本例 10 倍于 rescue 真实成本 |

结论：总量自洽、无黑洞、可推算，但差值以主价静默重计价——与一审 R1-C1 判断一致，此处完成数值定谳。

**持久化断点（二审新实证，决定性）**：
- `billing_worker._to_stmt_data`（services/billing_worker.py:237-255）白名单映射列，**丢弃 `usage_source`/`sub_calls`**；`token_usage` 表（models/chat.py:129-164）无这两列——sqlite 读回行 `model=main_model, 530+92, cost=0.00622`，与纯实测行**不可区分**。
- 切片仅存活于：①队列载荷（flush 后丢弃）②Redis `user:details:{user}:{date}`（**24h TTL**，token_tracker.py:282）。全仓 grep（backend+gateway）：`sub_calls`/`user:details` 在生产代码中**零读者**（仅 producer）。
- 实现证据如实披露过边界：diff_or_evidence_only.md「随 billing 队列/Redis 明细行透传，**DB 插入映射不变**」——但未与「独立开销可审计」的验收措辞对齐：审计面止步于管道载荷级，durable 账面（报表/成本界面的唯一事实源）无法表达或恢复混合构成。

**R1-C1 问题判定：sub_calls 切片披露不足以让（现行及近期）报表/成本界面消费者不误读**——按现行 schema，DB 消费者必然把混合行读成「纯实测主模型行」，构成性信息（含多少估算 rescue、价差多少）在 durable 面不可恢复。量级有界（价差 ≤ 注册表最大价差 $0.0079/1k × rescue token 量），故不阻塞；升级为 R2-C1。

## 2. R2-T2/T3｜幂等攻击面（重放语义定谳）

- **同 request_id 不同内容（T2）**：首份先落库（100 tok/$0.01），第二份（999 tok/$9.99）撞唯一约束后逐条重试静默跳过（debug 日志），DB 保留首份内容——**first-write-wins，content-blind**。语义上正确（exactly-once），且当前接线无同 id 双写生产者：queue:billing 唯一 producer 是 `TokenTracker.record_usage`（每根请求恰一次，response_builder.py:1795）；celery 变体 `record_token_usage`（celery_tasks.py:278）**无调用方**；`llm_quota`/`llm_security_wrapper` 的 record_usage 走配额键不进 billing 队列。残留：未来若出现同 id 双写（如 celery 复活），后者静默丢失且无指标（R2-C2）。
- **批内重复隔离（T3）**：批 `[新b, 重复a, 新c]` → 批量 insert 原子失败 → `_retry_individually` → b、c 落库、a 跳过，3 行账面正确——重复不毒化批内其他记录。
- **操作面噪声**：每次重放撞约束先打 ERROR「Failed to persist billing records: UNIQUE constraint failed」+ WARNING，随后才 DEBUG 跳过——错误监控的误报面；dup-skip 无计数器。量级小，记录知悉。

## 3. R2-4｜抽验（独立复核）

- **真实 router 注册价在位（生产现实面）**：llm_router.py 注册条目逐条显式 `cost_per_1k_tokens`（0.0001–0.008，dataclass 默认 0.001，无 0.0 条目）——「已注册但无价 → 0 冒充免费」在现行注册表不可达；单一核价权威有真实价格源，未知键/计量标签→None 语义有实价对照面。
- **独立复跑（本机、主仓 venv、零真模型）**：`test_v4_i10_metering_truth.py` 19 + FIX-80 守卫 `test_metering_model_attribution.py` 7 + `test_billing_worker.py` 7 = **33 passed**，与一审申报一致。
- R1-C2 抽验对象 `test_cleanup_measured_row_real_key_passes_bisect` 经真实注册表通过——其价目真源耦合确认存在，方向 fail-loud，维持 R1 原判。

## 4. Challenges（记录性，均不阻塞集成）

- **R2-C1（承接并升级 R1-C1）**：`usage_source`/`sub_calls` 在 billing_worker 持久化边界被丢弃，durable 账面无 mixed 标记无切片，切片零生产读者。收敛建议：后续报表/计量收敛卡为 `token_usage` 增 `usage_source` 列 + `sub_calls` JSON 列（或子表），行级引入混合组合语义 + per-slice 核价，并在 UI/报表口径中说明「混合行差值=rescue 按主价计」。本卡「无 DB 迁移」红线与零迁移声明自洽（persist 化属收敛卡范围），但「独立开销可审计」应按管道级审计理解，验收 3 的 PASS 不因此降级。
- **R2-C2（微观察）**：first-write-wins 为 content-blind 幂等——同 id 不同内容的后来者静默丢弃、无指标；批撞约束的 ERROR 日志在重放场景属预期路径却打 ERROR。建议收敛卡加 dup-skip 计数器并降级该日志。
- **R2-C3（微观察）**：混合场景下回执（流帧 500+80 按主价）与根行（530+92 按主价）数值不等，差=rescue 按主价折算；两口径各自自洽（回执=流帧口径、行=根调用树口径）但无用户可见解释，归入 R2-C1 收敛范围。

## 5. 与一审的关系及残留

- 一审 R1-C1 → 二审深挖后升级为 R2-C1（新增持久化断点实证与「不误读」否定判定）；R1-C2/C3 维持原判；一审三靶闭环结论、1333 复跑与 mypy 零漂移数据未重复验证（差异化审查），二审抽样复跑（33 passed）与其一致。
- 二审探针测试位于 /tmp/v4_i10_r2/（3 测，全绿），不入库；未 push、未改产品代码、零真模型调用。
- **残留（不阻塞，供协调面裁量）**：①R2-C1 收敛卡候选（persist 化 + mixed 语义 + per-slice 核价，与 R1-C1 建议合并路由）；②R2-C2 观察面随收敛卡顺带；③limitations 8 项维持一审定性，二审无推翻。

—— wtI10R2，2026-09-28
