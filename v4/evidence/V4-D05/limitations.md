# V4-D05 · limitations（如实限制清单）

1. **评测/统计面未跑，value 不标 PASS**：本卡交付为「可失败的呈现契约面」——验收判据是结构性红线（门/词表/信封/回访完整性），已由 52 测钉死；但没有任何真实用户数据上的效果评测。卡面三验收的 self-check PASS 指测试面，不宣称产品价值已验证（V4_DONE 口径：VALUE_VERIFIED_IN_TESTS 需独立效用门）。独立审查若对措辞/门参数有异议，按反例归因再裁决，不降阈值。

2. **「充分理解」门是呈现侧资格门，不是理解度度量**：`understanding_claim_gate` 只判定「宣称资格」（samples>0 且 missing=censored=0 才放行），本服务任何档位都不产出理解宣称文案（放行 ≠ 面上会写）。真正的理解度呈现（五维/校准/漂移）仍归 `/insights/understanding-dimensions` 既有面（D-03 遗产），本卡零接触。

3. **回访面窗口边界**：`_build_revisit` 只在 `window_days`（缺省 30d）查询窗内找最近 exposure——更早的「上次建议」不进回访（如实 no_prior 语义边界：读面不宣称看到全历史）。D-05 摘要本身有 5000 行 ASC cap（FIX-31 P2-1 已在 M-06 消费侧处理，本卡未重复处理）。

4. **churned 判定参数面**：回访的 `resolve_observation_status` 消费 `users.last_login_at`（D-05 `_resolve_last_active` 的同源 fallback 口径）；D-05 聚合面另有「显式参数 > last_login_at」的调用方兜底通道，呈现面无该显式参数——与聚合面在极端数据下可能相差一档（window_closed vs churned），两者都是显式不结论，都不进失败语义。

5. **样本身份命名空间**：`presentation_sample_id` 的 domain 固定 `OCCURRENCE`（decision_id 是 intervention occurrence 级锚，`aurora_<32hex>` 与 D02 归因的 canonical UUID 锚点不同 id 空间）——与 D02 四域归因身份不会碰撞，但这是呈现面约定而非 D02 词表成员；若未来 D02 增设 intervention 域，应迁移到该权威域（登记为后续owner事项）。

6. **outcome 级撤回（D03 tombstone）未接入呈现去重**：`exclude_withdrawn_refs` 是契约层（精确身份排除，已测），但「已删来源」在本读面的真实删除信号仍是**软删行**（`not_deleted_filter`，已测正反）。outcome 账本行本身无撤回态（D03 的 retraction 消费面在 galaxy mastery 侧），故「outcome 被撤回后卡样本回落」依赖其关联行被软删——账本级撤回传播到 D-05 关联行的接线归后续owner卡（本卡不造第二撤回权威）。

7. **呈现门无独立 off 旗标**：门是结构性恒在（只加严：违例卡扣下+meta 登记）。回滚 = revert 实现单 commit（变更独立、无共享状态）。未加 `INSIGHT_PRESENTATION_GATE=off` 旗标：本面无行为路径分歧（不像 I05 off/shadow/live 有「启用行为」可关），关旗标等于删门，revert 语义等价且更诚实。

8. **无 UI 截面**：本卡为数据/判定面卡；`next_step`/`understanding`/`revisit` 的用户可见文案组合在移动端 l10n（V4-U13 洞察报告 UI，tasks.json depends_on V4-D05）。Dart 面零改动（既有 fromJson 只读已知键，附加字段向后兼容；evidence_cards_api 既有契约测试零改动通过）。

9. **环境差记录**：受影响面扫描对 `tests/core/test_bert_intent_classifier.py` 显式 `--ignore`——既有环境债（transformers/AutoTokenizer 不在解释器环境），该文件及其 import 链与本卡 diff 零交集；主检出 main 上同文件在本环境同样不可执行。除此之外 597 passed / 1 skipped 无任何既有失败回归。
