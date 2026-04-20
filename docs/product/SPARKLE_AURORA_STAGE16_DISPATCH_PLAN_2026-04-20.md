# SPARKLE Aurora Stage 16 Dispatch Plan (2026-04-20)

> Workstream Bundle: `WS-MWL-*`（Memory Write Lane Activation）
> Phase Mapping: Roadmap v2.0 Phase 0A-Write
> 战略定位: 转向能力轨，打通 chat -> EpisodicMemory 的受治理写入车道

---

## §0 Stage 16 元信息

### 0.1 7-Phase Growth Ring 映射

Stage 16 只解锁 `Sense -> Reflect -> Adapt` 之间的最小闭环，不声称万能。

| Phase | Stage 16 后状态 |
| --- | --- |
| Sense | chat 首次成为 episodic 记忆来源，但必须受 Rule Y 约束 |
| Clarify | 不变 |
| Plan | 不变 |
| Execute | 不变 |
| Reflect | 可见用户最近说过什么、在意什么、准备做什么 |
| Reinforce | 不变 |
| Adapt | 可把近期对话记忆作为后续 prompt 上下文 |

未触发相位明确保持不变，避免把“写通 Memory”误读为“高级能力全开”。

### 0.2 Aurora 三层架构定位

- 仅允许写入 `L1` 画像系统中的 `EpisodicMemory`
- 严禁写入 `L0` 基础设施事实表、`L1` 结构化人物/技能/掌握度、`L3` Aurora 决策记录
- 不替换、不旁路既有 `User Correction` lane

### 0.3 Rule 审计清单

- Rule G: dispatch / 每个 WS / closeout 独立提交
- Rule H: chat 写入只能落 EpisodicMemory，不能扩到结构化 fact 表
- Rule K: Stage 16 正式新建 Rule Y；Rule K 守卫同步升级
- Rule N: 静态守卫覆盖 Rule Y 受控边界
- Rule P: 显式纠正继续走 User Correction lane
- Rule Q: 每条 chat-originated episodic 必须能被声明为“AI 推断”
- Rule U: mobile 必须提供 front door + widget-level 撤销路径
- Rule V: 至少新增 3 条回归契约测试（写入开关 / 撤销 / 杀闸）
- Rule W: Stage 16 只打通写入，不开放 Router / Push / Skill / Accountability 消费

### 0.4 Path B / Path C 兜底

- Path B: 只保留 read-verify、dry-run、kill switch 与 front-door 声明，不开启真写入
- Path C: 若 dry-run precision `< 0.85`，写入开关锁死，整期退回 Path B

### 0.5 Codex 自答（GLM-observer 6Q 子集）

1. 这一阶段没有用治理绕能力。
   写不写 Memory 不是纯规则题；因此本期除了 Rule Y，还必须交付 extractor、dedupe、read-verify、kill switch 和 mobile front door。
2. 这一阶段没有用能力绕治理。
   写入能力只有在 `source_lane=inferred_extraction`、`confidence`、`evidence_token`、`decay_policy`、撤销路径与 kill switch 全部到位后才成立。
3. Stage 17 会被真实约束。
   只有当 Stage 16 证明“写得进、读得到、可撤销、且没有被下游偷消费”，Stage 17 才有资格谈 Memory -> Router / Accountability。
4. 整体回滚不能留下半截脏数据。
   所有 inferred lane 记录都必须带 `source_lane` 与 `revoked_at`，因此能被 admin kill switch 定向撤回。

---

## §1 Stage 16 总目标

Stage 16 打通 Memory 写入通道，但不开放下游消费。

1. chat 流量可以产生 episodic 写入，且默认 `OFF`
2. 写入必须经过 Rule Y 治理
3. 写入必须可读、可声明、可撤销
4. 下游 `Router / Push / Accountability / Skill / Evidence Resolve 之外的消费路径` 一律不得读取 inferred lane

---

## §2 Gate S16-0 入场基线

动任何 Stage 16 代码前必须 replay：

```bash
# Stage 12 frozen baseline
cd backend && ./.venv/bin/python -m pytest tests/aurora -q

# Rule V regression suite
cd backend && ./.venv/bin/python -m pytest tests/unit/test_persistent_bayesian_learner_contract.py -q

# Rule K 守卫
./backend/.venv/bin/python scripts/check_rule_k_write_paths.py

# Stage 13+14+15 backend 合并扫
cd backend && ./.venv/bin/python -m pytest tests/unit/test_router_node_learning_integration.py tests/unit/test_tool_preference_router.py tests/unit/test_persistent_bayesian_sqam_scale.py tests/unit/test_evidence_resolve.py tests/services/test_within_category_preference_service.py tests/unit/test_predictive_service_productization.py -q

# Stage 13+15 mobile sweep
cd mobile && flutter test test/widget/evidence_card_navigation_test.dart test/features/memory/presentation/widgets/evidence_cards_test.dart test/features/home/presentation/widgets/predicted_intent_card_test.dart
```

期望分别为 `144 / 8 / 35-0 / >=40 / >=52`。任何一项失败立即停工。

---

## §3 Workstreams

### WS-MWL-RULE

正式定义 Rule Y，并把 inferred chat write 从模糊地带拉进明文治理。

### WS-MWL-READ-VERIFY

证明标准 chat 路径写入的 episodic 记忆会在下一轮 prompt 渲染中出现；读不通就不许写。

### WS-MWL-EXTRACT

实现非阻塞、固定 schema、可 dry-run 的 inferred episodic extractor。

### WS-MWL-CONFLICT

实现同 evidence_token 去重、显式纠正优先、近义语义合并、到期标记过期不物理删。

### WS-MWL-WRITE

实现 default-OFF 的真实写入车道；原始 chat 文本不得直写，失败必须静默降级。

### WS-MWL-KILL

实现只针对 `inferred_extraction` 通道的 kill switch；不得误删 explicit lane。

### WS-MWL-MOBILE-DECL

在 memory front door 暴露 “AI 自动记忆” 区段、证据入口、单条撤销、总开关。

---

## §4 Gate S16-FINAL

Final gate 必须同时拿到：

1. Gate S16-0 baseline 全绿
2. Rule Y 定义文档
3. READ-VERIFY 集成测试 green
4. EXTRACT dry-run precision 报告 `>= 0.90`
5. WRITE 默认 OFF 时不影响既有 baseline
6. KILL 回归测试 green
7. MOBILE widget-level 测试 green
8. grep 验证 `inferred_extraction` 未出现在 router / push / skill / accountability / evidence resolve 下游消费路径

---

## §5 延迟到 Stage 17+

Stage 16 不做：

1. Memory -> Router
2. Memory -> Push
3. Memory -> Skill
4. Memory -> Accountability
5. Social brain 的任意写/读通路
6. State Aggregator 消费 Memory

---

## §6 Stage 17 入场条件

- Path A: 全 WS green + 灰度观察稳定 + Rule Y 无破例
- Path B: 只完成 dry-run / read-verify / kill，则 Stage 17 先补真写入
- Path C: precision 不达标，继续重做 extractor

---

## §7 Codex 执行守则

1. dispatch 文档先落盘，再做代码
2. 每个 WS 进入实现前先确认边界，不夹带 Stage 17 能力
3. closeout 产出 `SPARKLE_AURORA_STAGE16_HANDOFF_2026-04-20.md`
4. final-accept 前保留 targeted test、grep、artifact、handoff 全证据链
