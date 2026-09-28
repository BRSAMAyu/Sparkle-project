# V4-D02 · limitations（如实）

1. **生产消费面本卡零接线（最重要）**：`backend/app/core/attribution.py` 是冻结契约 + 守卫测的契约模块，全仓无生产 import（治理守卫 BJ 按设计提示，已按既有先例落 `# rule-bj: exempt` + `KNOWN_CODE_DEBT_LEDGER.md` P3 #13 双登记）。unattributed 公开分母的「公开可查」当前指 `AttributionDenominator.to_dict()` 结构面（schema 冻结、可被 insights/evidence cards 直接消费），**尚无 API 路由或 UI 呈现**——公开呈现面归 V4-D05（可读且不夸大的洞察），撤回派生影响的消费归 V4-D03。接线落地后应删除豁免与台账条目。
2. **`CorrelationIds`（event_registry）未分域化**：事件 correlation 的值域门仍只验 canonical UUID。本卡的分域纪律作用于 `attribution.py` 判定面；把 `CorrelationIds` 本身改造为分域键属 event-domain 契约变更（D-01 冻结集 + 值域门），按「契约/迁移由单一 owner 单独合并」边界本卡不越权。因此：**经 `CorrelationIds` 直投的裸事件流仍可能在键名槽位错置 UUID**——判定面能拒绝跨域匹配（domain_mismatch），但源头槽位纪律要靠后续契约卡收口。
3. **四域之外的域未纳入**：`AttributionDomain` 封闭四值（goal/task/occurrence/run，卡面口径）。intervention/plan/memory 等域的关联仍归各自权威（D-05 linkage 等），本模块未统一它们；扩展域 = bump `attribution.domain.v1` 过 reviewer。
4. **unjudgeable 的存储面**：行损坏（`broken_row`）只有判定与计数语义，无独立持久化队列/告警接线（DATA_AND_GRAPH「死信、epoch 不一致暴露面」整面归后续可靠性卡）；当前由调用方消费 verdict 时落观测。
5. **守卫基线差异如实记录**：wtD02 worktree 缺 Go/Dart 生成物 → BG 守卫环境性失败（主检出同 guard 通过）；主检出另有 AM/AURORA-CONFIG/CARD-DUAL-WRITE 三项 base 既有失败（本 worktree 反而通过）。均与本卡增量无关，但「全绿」在任何单一检出上都尚未成立。
6. **测试环境依赖共享 venv**：worktree 无独立 .venv，Python/pytest/mypy/ruff 均用主检出 `/Users/brsama/code/GitHub/Sparkle-project/backend/.venv`；`backend/app/gen` 为主检出复制实体目录（gitignored，未提交）。CI（Linux）口径未在本卡复跑。
7. **随机追踪还原的边界**：`trace_receipt_to_outcome` 验证的是 `receipt_ref→experience_event→outcome` 三段链的**可还原性**（逐跳重算比对）；「UI 交互 → event_id」第一跳的采样入口依赖消费方持有 event_id（WS 呈现事件的既有重播抑制键，D01/F03 面）。UI 侧事件缓冲/丢事件重投的可靠性归 F03/事件总线可靠性卡。
8. **延迟/时序语义口径**：判定一律用 outcome 真实事件时间（`occurred_at`），不读 `received_at`（DATA_AND_GRAPH：received 用于延迟与 watermark，不覆盖真实事件时间）；watermark/迟到统计本身不在本卡范围。
