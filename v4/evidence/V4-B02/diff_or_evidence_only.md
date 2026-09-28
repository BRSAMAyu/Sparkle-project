# V4-B02 diff_or_evidence_only

**性质判定：evidence-only（差量举证，不重写）。**

当前仓库行为已满足本卡验收（43 目录 exact match、路由/深链/provider 可映射、HIDDEN/LABS 无自动开放），故本卡零产品代码变更，全部产出为证据：

- `v4/evidence/V4-B02/mapping.csv` — 43 特征 × 在用路由映射（新增，本卡唯一"最小增量"）
- `v4/evidence/V4-B02/route_inventory.csv` — 136 注册路由分类清单（新增）
- `v4/evidence/V4-B02/drift_findings.md` — 漂移登记 10 新 + 2 确认未变（新增）
- `v4/evidence/V4-B02/mapping_report.md` — 方法/覆盖/验收对照（新增）
- `v4/evidence/V4-B02/run_manifest.json` / `test_results.json` / `review_receipt.json` / `limitations.md`
- `v4/04_tasks/tasks.json` — V4-B02 状态与证据指针（本卡管理面更新）

## 产品代码 diff

无（红线：只读产品代码不改）。V3 已 DONE 证据未触碰；矩阵（v3-output/B-01/MODULE_MATRIX.csv）未修改——漂移移交 B-01 线。

## 与既有决策的一致性

- D-COMM-1 自我锚唯一路由面：核验一致（无全站榜路由回潮）。
- D-COMM-2 光子兑换出口：/photon/redeem-pro 在案，/photon/transfer 保持撤除。
- NAV-IA P-3 / U-07 等既有摘除决策：被本次静态扫描独立复现（DF-02/DF-03），非本卡新决策。
- onboarding 归 user：user_routes 承载 /onboarding/persona 与 /onboarding/modeling-chat，无独立 feature 目录，矩阵 F24 空位正确。
