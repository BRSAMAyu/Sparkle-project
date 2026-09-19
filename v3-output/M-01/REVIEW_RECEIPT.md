# M-01 REVIEW_RECEIPT — 第一路独立 Reviewer

- reviewer: R1（M-01 risk=high 需 2 Reviewer 之路 1）
- date: 2026-09-19
- 对象: wt2 未 commit 改动（11 文件 +1430/-4，基线 2f52a972）+ v3-output/M-01/ 交付物
- 方式: 代码审读 + 亲手 RED/GREEN 探针复现 + 测试实跑 + dev PG 只读检查 + patch 完整性核对

## 1. 漏洞复现（最重要验收点）—— 亲手实证，成立

方法：因新文件为 intent-to-add（` A`）导致 `git stash` 拒绝，改用等价法——将
`memory_service.py` / `conflict_resolver_service.py` 临时 checkout 回 HEAD（先备份至 /tmp），
跑独立探针测试，再恢复并逐字节核对 `git status` 与改前一致。

- **基线（HEAD）探针结果**：`explicit_created=True inferred_accepted=True inferred_is_head=True`
  → **VULNERABLE**。推断写（source_type=ai_inferred）被接受并成为 memory_preferences 版本链头，
  显式事实（user_state, value=0.8）被 replaced_by_id 压入链下。
- **工作树（守卫后）探针结果**：`inferred_accepted=False inferred_is_head=False`
  → **GUARDED**。推断写返回 None，链头/版本数零变动。
- 代码路径推演（与实证吻合）：HEAD `upsert_preference` 无任何 provenance 检查，无条件
  version+1 并置 `latest.replaced_by_id`；调用方 `profile_write_service.py:212` 以
  `source_type="ai_inferred"` 直写；user_preferences live 表的 `_has_explicit_override`
  不覆盖 memory_preferences 版本链域；`_allow_write` 仅为用户策略门（默认放行）。

**结论：Worker 自报漏洞真实、修复有效，红→绿证据链完整。**

## 2. 契约设计 —— 自洽

- 五类型枚举 + `EPISODIC_EPISTEMIC_CLASSES`（CONFIRMED_PREFERENCE 由表成员资格承载，不加列，"不建第二库"落法正确）。
- `derive_status` 早退链与声明的优先级 revoked>superseded>retracted>archived>expired>resolved>active 严格一致；无非法转移面（纯派生，无写路径）。
- `lane_priority` 延迟导入委托 `ConflictResolverService.KNOWN_SOURCE_LANES / PRIORITY_BY_TIER`，档位无重复定义；实测 resolver 注册表 6 lane，**aurora_calibration_receipt 确未登记**（仅 D2 防御性注释 + 契约 RESERVED_UNREGISTERED_LANES 文档位），符合 V3-FIX-06 裁决。
- `derive_scope` 为既有列纯投影，零新增存储。
- 迁移链 m01a→ud01→gfix03 唯一 head；全加法、nullable/server_default、downgrade 干净 drop、回填幂等（仅填 NULL）。
- 次要观察（不阻塞）：契约谓词 `inferred_lane_may_supersede_lane` 与 resolver 内联的 rank 比较（`winner_rank < loser_rank → skip`）语义等价但未复用同一函数；契约测试已固定其真值表，建议 M-04 接线时收敛为单一调用点。

## 3. 测试证据（全部实跑，串行）

| 套件 | 结果 |
|---|---|
| tests/unit/test_memory_inference_write_guard.py | 7 passed |
| test_memory_epistemic_contract.py + test_conflict_resolver_epistemic_guard.py + test_memory_v3_migration_sqlite.py | 14 passed |
| 存量回归抽样：test_conflict_resolver_service.py | 11 passed |
| 存量回归抽样：test_memory_service.py | 5 passed |
| 独立 RED 探针（基线）/（工作树） | VULNERABLE / GUARDED |

（test_memory_api.py 等因本 worktree 未跑 proto-gen 缺 `app.gen` 无法收集——基线同样如此，非本卡引入；Worker 以进程内 stub 验证了 API 序列化。）

## 4. dev PG 未动 —— 确认

- `alembic_version` = **ent01_20260919**（不含 m01a；亦不含 ud01，属前一卡的发布节奏，与本卡无关）。
- `episodic_memories` 无 epistemic_class / superseded_by_id 列；`user_memory_settings` 无 memory_epoch* 列（information_schema 查询均 0 行）。

## 5. patch 完整性 —— 通过

- `v3-output/M-01/changes.patch` 与 `git diff HEAD` **逐字节一致**（diff -q 无差异）。
- 11 文件 +1430/-4，与自报一致；无 .env/密钥/私钥/云凭证（唯一命中为测试夹具 `hashed_password="test"` 与 `evidence_token="turn-x"`）。
- MAPPING.csv 实测 23 数据行 × 9 列，五类型 + 瞬态 + 五层联动 + aurora 保留位覆盖齐。

## 6. 复核遗留事项（非阻塞，供后续卡参考）

1. lane 冒领：`source_lane` 仍由调用方申报（Worker 已如实申报为风险 1）——建议随 M-04 治理。
2. 被拦截的推断写不再留 memory_preferences 版本行（推断状态仍完整保留于 user_preferences live 表）——如需推断历史审计行，后续卡再议。
3. `inferred_lane_may_supersede_lane` 谓词与 resolver 内联守卫的收敛（见 §2）。
4. memory_service.py 新增 `_bump_epoch_best_effort` 与模块级 `_normalize_evidence_refs` 之间仅 1 空行（PEP8 惯例 2 行）——格式微瑕，ruff/black 基线本有偏差，不值得返程。

## VERDICT

复核全部通过：漏洞亲手复现（红）且守卫实测生效（绿）；契约自洽、lane 注册表委托正确、aurora 未登记；37 项测试全过、dev PG 未动、patch 与自报完全一致。

**VERDICT: ACCEPT**
