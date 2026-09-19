# V3-FIX-13 REVIEW_RECEIPT — 独立 Reviewer 验收

> Reviewer：V3 Fleet 独立 Reviewer（wt6）｜日期：2026-09-19｜对象：Worker 交付 changes.patch（6 diff：3 app 文件 +61/-8 + 2 新测试 + REPORT.md）｜方法：全项独立重验（DB 实证 / 读码 / 跑测 / RED 复现 / patch 反向校验），非采信自报。

## 结论总览

| 验收项 | Worker 自报 | Reviewer 独立验证 | 判定 |
|---|---|---|---|
| D-14 判定「已在 HEAD 存在，不加 t34v3」 | gfix01 已建 4 列，fresh 再加会 duplicate_column | **成立**（4 项独立证据，见 §1） | ✅ 认可 |
| D-11 判定「不复现，不改 populate」 | r20807 小写契约 + 按值 coercion | **成立**（含 coercion 独立实验，见 §2） | ✅ 认可 |
| D-12 红→绿 | SAVEPOINT + commit=False | **成立**（语义读码 + 测试 + RED 复现，见 §3） | ✅ 认可 |
| D-15⑦ 红→绿 | _accepts_kwarg 签名探测，23/25 | **修复成立；23/25 为运行时快照**（见 §4 保留项） | ✅ 认可（带备注） |
| patch 完整性 | 6 diff 一致、无密钥、scratch 已删 | `git apply -R --check` 通过；无密钥；pg_database 无 sparkle_fix13_scratch | ✅ 通过 |
| 测试 | 新 6/6 + 回归 75 | 新 6/6 绿、既有回归抽测 8/8 绿、**RED 在 HEAD 独立复现 4F/2P 与报告逐字一致** | ✅ 通过 |

**VERDICT: ACCEPT**（1 条不阻塞备注，见 §4）

## 1. D-14「不做」判定 — 独立验证成立

1. `git log --all`：gfix01 由 67419ba5 引入，commit message 自述与组员报告同一症状（"never-migrated FV-22 columns … broke guest seeding with poisoned transaction"）——前置轮次确已收敛此债。
2. 迁移读码 `alembic/versions/gfix01_shared_resources_fv22_20260918.py`：upgrade 循环 `add_column` 创建 adoption_count/negative_feedback_count/quality_score/quality_hidden；down_revision=`('r20807_20260918','sr8r2g2_c2_intent')`（mergepoint，与报告一致）。
3. dev DB（sparkle）`information_schema` 实证 4 列齐全：integer/0、integer/0、double precision/'0'、boolean/false，均 NOT NULL。
4. 单头权威验证：alembic ScriptDirectory（不连 DB）`get_heads()` = `['x01_20260919']`，共 145 迁移；x01 祖先链（深度 24）中 gfix01@8、r20807@9。fresh 库重复 add_column 必 duplicate_column 的推理成立。**不加 t34v3 正确。**

## 2. D-11「不做」判定 — 独立验证成立（含独立 coercion 实验）

1. r20807 迁移读码：`_LOWERCASE_VALUES` 恰 11 值含 `planning`；docstring 明示设计取向为「DB 收敛到引擎小写契约」——组员「补大写 PLANNING」确实与链上设计相反，跳过条款适用。
2. dev DB 实证：`enum_range(achievementtype)` 恰 11 小写值；`enum_range(achievementrarity)` 恰 4 大写值；`achievements` 表实况 type 全小写 / rarity 大写（COMMON/RARE/EPIC/LEGENDARY）。
3. 模型契约读码 `app/models/achievement.py`：type 列带 `values_callable`（存小写 value），rarity 列无 values_callable（SQLAlchemy 默认存 member NAME=大写）。
4. **Reviewer 独立实验**（SQLAlchemy 2.0.48，与钉装版本一致）：`Enum(AchievementRarity)._db_value_for_elem("common")` → `"COMMON"`；`Enum(AchievementType, values_callable=…)._db_value_for_elem("milestone")` → `"milestone"`。裸字符串按值 coercion 落盘契约与 Worker 实测吻合。**不改 populate 正确**（无红可依）。

## 3. D-12 — 修复合规（语义边界读码确认）

1. `seed_guest_user_data` 包装：进 SAVEPOINT 前取 `user.id/username` 纯值（防御回滚后实例过期→MissingGreenlet 的次生坑属实）；`async with session.begin_nested()` 整段包裹；失败 `logger.warning` 带 user_id/username——**降级告警可观测、非静默吞**。
2. `grep -n "\.commit()" guest_seed_service.py` 零命中——种子内已无主动 commit，SAVEPOINT 不会被提前 RELEASE，隔离边界完整；`_ensure_achievements` 传 `commit=False` 数据留在调用者事务。
3. auth.py:895-933（HEAD 既有，不在本 patch 内）：seed→`db.commit()` 顺序下，seed 失败被 SAVEPOINT 吸收后用户行照常提交，登录不 500；既有 retry 兜底成为无害第二道防御（与报告 §6.3 一致）。
4. 默认 `commit=True` 保留 CLI/engine 路径：`achievement_engine.py:320` 核实仍以默认参数调用（报告 §6.2 备注属实）。
5. 测试语义真实：不抛出+用户存活+零部分残留；commit=False 不 commit 且随调用者回滚消失；默认行为不变。

## 4. D-15⑦ — 修复成立；一条不阻塞备注（数字口径）

1. `_accepts_kwarg` 读码正确：POSITIONAL_OR_KEYWORD/KEYWORD_ONLY 命中或 VAR_KEYWORD 通配；签名不可读保守不传。locale 与 progress_callback 双分支探测，`tool_call_id` 恒传。守卫测试（带 locale 工具照常收到 `runtime_context.locale="zh"`）真实，防回退有效。
2. **保留项**：报告「25 个注册工具中 23 个无 locale」是**运行时快照，非 HEAD 稳定事实**。Reviewer 三口径复算：最小 import 38 工具/36 无 locale；registry 直载 33/31；app.main 全链 38/36。注册数随 import 链浮动（companion_tools 存在 circular import 注册失败等），三口径下「无 locale」占比均 >94%、`**kwargs` 通配工具均为 0。**结构性问题与修复有效性不受影响**（签名探测对任意数量/签名正确），但后续引用该数字时应理解为「统计时点快照」。不阻塞。

## 5. 测试与 RED 复现

- worktree 上：新增 6/6 passed；既有回归抽测 `test_guest_seed_service.py`(3) + `test_executor_execution_observer.py`(2) + `test_tool_executor_observability.py`(3) = 8 passed。
- **RED 独立复现**：`git archive HEAD` 提取无修复代码至 /tmp，置入同两测试文件 → `4 failed, 2 passed`，失败清单与失败原因（`TypeError: … unexpected keyword argument 'locale'`）与报告 §3.1 **逐字一致**。红绿纪律成立，非事后编造。
- 新测试文件 black(120)+ruff 全绿（Reviewer 复跑）。

## 6. Patch 完整性与清理

- `git apply -R --check changes.patch` 通过 = patch 恰为 worktree-vs-HEAD 差量（6 diff 含 REPORT.md）。
- patch 全文无密钥（仅测试语境 SECRET_KEY 注入说明）。
- `pg_database` 无 `sparkle_fix13_scratch`（已删）；dev DB sparkle 全程只读 select；无新迁移、单头不变。
- Reviewer 自身清理：/tmp/fix13_red_check、临时 diff 已删；worktree 内 .pytest_cache 已删。

## 复核命令存档（可复跑）

```
docker exec sparkle_db psql -U postgres -d sparkle -tc "select column_name,data_type from information_schema.columns where table_name='shared_resources' and column_name in ('adoption_count','negative_feedback_count','quality_score','quality_hidden')"
cd backend && SECRET_KEY=test JWT_SECRET=test /opt/homebrew/bin/python3.11 -m pytest tests/services/test_guest_seed_savepoint.py tests/unit/test_executor_tool_locale_signature.py -q
```

REVIEWED_BY: independent-reviewer (wt6) | VERDICT: ACCEPT
