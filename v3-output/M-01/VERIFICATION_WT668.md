# M-01 门禁复核（wt668，2026-09-27）

**判定：卡面已完成（fleet state `done[16]`），增量仅为测试面 lint 清理，零产品代码改动，零契约面新增。**

- 基线：集成 HEAD `d7a961da`；本卡落地 SHA：`7ef808ee`（M-01 ACCEPT merge，dual-review + R2 rework）
- 双证判定：git log（`7ef808ee` 为 HEAD 祖先，`git merge-base --is-ancestor` 亲证）+ 交付物在场（`services/memory_epistemic_contract.py`、迁移 `m01a_20260919`、`v3-output/M-01/` 五件套、双审查回执）+ fleet state `.sparkle_v3_fleet_state.json` `done` 列表含 M-01。**按「增量不重做」纪律不重做卡面主体。**

## 卡面验收逐条对照

| 卡面验收 | 判定 | 证据 |
|---|---|---|
| 现有数据可向后兼容或有迁移 | ✅ | 迁移 `alembic/versions/m01a_20260919_memory_v3_epistemic.py` 全加法（epistemic_class/superseded_by_id nullable + epoch 三列 server_default）；merge 时已应用 dev 并回填 live-verified（FACT=1/OBS=185/HYP=52，见 7ef808ee 提交文）；sqlite 隔离重放测试在位 |
| Inference 不覆盖 fact | ✅ | 契约守卫谓词 + `memory_service.upsert_preference` inferred-over-explicit 拒写 + `conflict_resolver.apply_live_decision` 变更点 lane 守卫；`test_memory_inference_write_guard.py`(8) + `test_conflict_resolver_epistemic_guard.py`(3) 绿 |
| Memory record 均可指出 source/scope/status | ✅ | `api/v1/memory.py:94-97/324-329/869-889`（面板/episodic/export 三面均序列化 epistemic_class + status/memory_status + scope）；契约 `classify_episodic_class/derive_status/derive_scope/preference_write_provenance` 单一权威 |
| Work1 五类型映射不建第二库 | ✅ | FACT/OBSERVATION/HYPOTHESIS/EXPERIENCE → episodic_memories 列；CONFIRMED_PREFERENCE → 表成员资格（memory_preferences/memory_goals）；B-06 ENTITY_MAP.md §1 Memory 一节当日独立审计同判定 |
| Work2 transient 区分 | ✅ | 契约头注显式规则「transient stays in working memory (Redis), never pollutes long-term tables」 |
| Work3 status/supersede/revoke/epoch contract | ✅ | `derive_status` 派生状态机（revoked>superseded>retracted>archived>expired>resolved>active；candidate/confirmed=视图级，双审通过）；episodic `superseded_by_id` 链；epoch 原子 `UPDATE..RETURNING`+并发不丢增量（R2 F3） |
| Required evidence：base/final SHA | ✅ | REPORT.md §0（2f52a972 → 7ef808ee） |
| Required evidence：targeted tests | ✅ | 本次 HEAD 复跑 24/24（见下） |
| Required evidence：integration | ✅ | dev 库回填 live-verified（7ef808ee 提交文，R2 预测精确命中） |
| Required evidence：review receipt（high risk 需 2） | ✅ | REVIEW_RECEIPT.md + REVIEW_RECEIPT_2.md（R2 判 CHANGES→返修 F1/F3 后 ACCEPT） |

## 本次增量（wt668）

`7ef808ee..d7a961da` 间触达文件发现 6 处测试面 ruff 违规（F401×2、I001×2、SIM300×2；产品码 0 处；其中 `test_memory_epistemic_contract.py` 的 3 处系 a28a5b8c/V3-FIX-06 引入，其余为 merge 既有）。全部机械 autofix：未用 import 删除、import 排序、SIM300 字面量置左（集合相等对称，断言强度零变化，不删断言）。触及文件均为 M-01 锁定面（memory-semantics），并行卡（wt663/wt665/wt666）零交集。

## 本次验证件套（基线 d7a961da，改动后）

```
cd backend
SECRET_KEY=$(python3 -c "print('x'*40)") python3.11 -m pytest \
  tests/unit/test_memory_epistemic_contract.py \
  tests/unit/test_memory_inference_write_guard.py \
  tests/unit/test_conflict_resolver_epistemic_guard.py \
  tests/unit/test_memory_v3_migration_sqlite.py -q
# => 24 passed in 4.80s（merge 时 23 项，+1 系 V3-FIX-06/M-04 合法演进）

/tmp/ruff112/bin/ruff check <11 个触达文件>   # => All checks passed!
python3.11 -m mypy <4 个测试文件>              # => 149 errors 改前 == 149 改后（依赖闭包既有，零新增）
```

迁移测试口径：sqlite 文件库（`tmp_path/m01_test.db`），主库只读纪律未触。

## 裁决与登记

- 无新不诚实面：REPORT §6.1 lane 自报诚实性限制已被卡面披露并随 M-04 治理；V3-FIX-06（a28a5b8c）已收口唯一未登记 lane。**未占用 V3-FIX-357 及之后号段**（grep 台账+全仓亲证零占用）。
- 契约面零新增：`MEMORY_EPISTEMIC_CONTRACT_VERSION` 维持 `memory-v3.m01.v1`，本 session 零契约/产品码改动。
- 无运行级待验项：迁移已应用 dev；epoch 消费者（M-07/C-07）与 lane 写方治理（M-04）属后续卡边界，非本卡欠账。
