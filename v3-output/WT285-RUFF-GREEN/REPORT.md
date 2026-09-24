# WT285-RUFF-GREEN 交付报告 — D 线·CI Python Ruff 门清绿

- 分支/worktree：`wt285-ruff-green`（基线 `8221131e`，未 push，仅本地 commit）
- CI 对象：run 35952738336「Python Lint (Ruff)」步，钉版 ruff==0.15.12（backend/requirements.lock），CI 调用 `ruff check backend/app --output-format=github`
- 结论：**86/86 清零，本地 `ruff check backend/app` 零输出 exit=0**；mypy 与 HEAD 基线归一化完全一致（零回归）；定向 pytest 438 passed

> 口径说明：卡面写 87，CI 日志 `##[error]` 行实为 86 条代码错误 + 1 条「Process completed with exit code 1」进程行。本地钉版 ruff 复跑同样 86，全部对齐后清零。

## 一、修复计数（回执①）

| 阶段 | 数量 | 说明 |
|---|---|---|
| ruff `--fix`（safe） | 56 | 两阶段实测（scratch clone 复放验证） |
| ruff `--unsafe-fixes` | 32 | 含修复过程二次暴露的 3 项（如 auth.py 移除 `asyncio.TimeoutError` 后 `import asyncio` 变 unused 被 F401 连带清掉） |
| 手修（SIM113） | 1 | `langgraph_redis_checkpointer.py:224` 计数循环 → `enumerate()`（该版本 ruff 无此 fix） |
| 语义校准（在自动修结果上手改） | 4 | 1 处 E712 改写 + 3 处 B905 `strict=False→True`，见第三节 |
| **合计** | **86** | |

## 二、规则 × 文件 × 修法映射（86 项）

| 规则 | 数 | 修法 | 文件 × 数 |
|---|---|---|---|
| UP006 | 12 | safe auto（`Dict`→`dict`） | workers/signals_learning_worker.py ×12 |
| E731 | 12 | unsafe auto（lambda→def） | tools/entity_cards.py ×11、orchestration/context_funnel.py ×1（`_FALLBACK_TOKEN_ESTIMATOR`，签名带类型注解） |
| UP037 | 10 | safe auto（去引号） | aurora/correction_types.py、core/action_plan.py、core/task_manager.py、core/trace_spine.py、services/batch_worklane.py、services/execution_run_producer.py、services/galaxy_service.py、services/memory_storage_gate.py ×2、signals/spine_orchestrator.py |
| UP017 | 9 | safe auto（`timezone.utc`→`UTC`，py311 同一对象） | api/v1/goals.py ×3、api/v1/scenario_packs.py ×3、causal/episode_logger.py、causal/redis_episode_sink.py、services/galaxy_grpc_service.py |
| UP041 | 8 | unsafe auto（`asyncio.TimeoutError`→`TimeoutError`，py311 起二者同一类型；auth.py 处原 tuple 内二者并列属冗余，修后去重） | api/v1/auth.py、core/celery_dispatch.py、core/request_coalescing.py ×2、core/sse.py、orchestration/execution_engine.py、services/cognitive_service.py、services/memory_storage_gate.py |
| B905 | 6 | unsafe auto（`strict=False`）＋3 处校准为 `strict=True` | aurora/signal_aggregator.py、orchestration/context_funnel.py ×2、services/community_service.py ×2、signals/absence_detector.py（逐点判定见第三节） |
| I001 | 4 | safe auto（import 排序） | api/v1/auth.py、api/v1/router.py、services/galaxy/outcome_absorption_service.py、services/galaxy_service.py |
| E712 | 4 | unsafe auto（3 处直传列表达式）＋1 处手修 `.is_(False)` | services/community_advanced_service.py（`User.is_superuser`）、services/community_service.py（`PrivateMessage.is_read`，**手修**）、workers/signals_learning_worker.py ×2（`CandidateActionFeedback.executed`） |
| C420 | 3 | safe auto（`dict.fromkeys`） | orchestration/routing_parameter_registry.py ×2、services/intervention_lifecycle_service.py |
| B007 | 3 | safe auto（循环变量 `_` 前缀） | checkpoint/langgraph_redis_checkpointer.py、orchestration/context_funnel.py ×2 |
| UP042 | 2 | unsafe auto（`(str, Enum)`→`StrEnum`，使用点全量审计后放行） | api/internal/auto_degrade.py（AlertType）、services/galaxy/mastery_evidence.py（MasteryEvidenceType） |
| SIM300 | 2 | safe auto（Yoda 条件翻转） | core/action_plan.py、core/intervention_lifecycle.py（import 期 assert，集合不等号方向同步翻转） |
| SIM114 | 2 | unsafe auto（同体 if 分支合并） | core/trace_spine.py（`isinstance(bool)` 并入 `(bool,int,float)`）、signals/learning_base.py（insufficient/harmful 同写 `belief.beta`） |
| F401 | 2 | safe auto（unused import 删除） | models/redeem_code.py（`datetime`）、services/aurora_confirm_bridge_service.py（`SELF_MODEL_KEY`） |
| SIM113 | 1 | **manual**（`count += 1` 循环 → `enumerate`，`count` 仅用于 limit 断行、无 continue 干扰） | checkpoint/langgraph_redis_checkpointer.py |
| F841 | 1 | safe auto（`except Exception as exc` 删绑定量；loguru `opt(exception=True)` 取自 sys 不用变量） | core/cost_wvpl_metrics.py |
| B004 | 1 | auto（`hasattr(x,"__call__")`→`callable(x)`） | middleware/admin_audit.py |
| C408 | 1 | auto（`dict()`→字面量） | services/llm_service.py（span tags） |
| UP032 | 1 | safe auto（`.format`→f-string） | services/experience_memory_projector.py（cache_key） |
| UP012 | 1 | safe auto（`.encode("utf-8")`→`.encode()`） | services/redeem_service.py |
| UP034 | 1 | safe auto（多余括号） | services/batch_worklane.py |

## 三、语义敏感项专节

1. **E712 的 `not <SQLAlchemy 列>` 必炸点（本卡抓到的唯一 auto-fix 运行时 bug）**：`community_service.py:2821` 的 `PrivateMessage.is_read == False` 被 unsafe fix 机械改成 `not PrivateMessage.is_read`——SQLAlchemy Column 的 `__bool__` 直接 raise（Boolean value of this clause is not defined），该 UPDATE…WHERE 一执行就 500。已手修为 `PrivateMessage.is_read.is_(False)`（NULL 行为与 `= false` 在 WHERE 匹配语义等价）。其余 3 处 `== True`→裸列表达式传 `.where()`，生成 SQL 与过滤结果均等价，保留。
2. **UP042 StrEnum**：py3.11.15 实测 `(str, Enum)`→`StrEnum` 唯一差异是 `str()`/f-string/format 输出（`"Class.MEMBER"`→`"value"`）；json 序列化、`==`、哈希/字典键、拼接全部不变。审计两枚举全部使用点：AlertType 仅作 dict 键/身份比较；MasteryEvidenceType 的字符串化全部显式走 `.value`（outcome_absorption_service.py:96、mastery_evidence.py:396），无裸插值 → 放行。
3. **B905 zip(strict=) 逐点判定**：
   - `signal_aggregator.py:316` `zip(tasks, gather_results)`：gather 对同一 tasks 提取的协程按序返回同长列表，**成对性可证明 → 校准 `strict=True`**；
   - `context_funnel.py:276` `zip(aligned, markers)`：上游显式 `len` 不等即诚实降级 "unverified"，到达 zip 点必等长 → **校准 `strict=True`**；
   - `absence_detector.py:140` `zip(keys, pipe.execute())`：redis pipeline 每命令一条结果同序同长 → **校准 `strict=True`**；
   - `context_funnel.py:184` `zip(ordered, ordered[1:])`：滑窗配对，天然差 1，`strict=False` 即正确语义，**保守保留**；
   - `community_service.py:3218` `_cosine_sim` 与 `:3349` `zip(candidates, embeddings)`：长度失配属「静默截断 vs 降级」的产品行为决策（embedding 局部失败/异长向量），**保守保留 `strict=False` 不改行为**。
4. **UP041**：Python 3.11 起 `asyncio.TimeoutError` 就是内建 `TimeoutError` 的别名（CI Python 3.11、target-version py311），8 处替换零行为差异；auth.py 原 `except (…, TimeoutError, asyncio.TimeoutError)` 重复捕获同一类型，修后去重。
5. **UP037 去引号**：10 处全部验证被引名在注解求值点已可解析（`from __future__ import annotations` 或先定义），43 改动模块 import 烟雾 43/43 通过实证。
6. **black 决策（放弃格式化）**：锁版 black 26.3.1 对 43 个改动文件跑一遍会产生 ~4000 行与修复无关的重排（存量代码非 black-26 风格），违反最小 diff 纪律且 CI 无 black 门 → 已回滚，交付仅含 lint 修复的最小 diff（43 files，+107/−108）。

## 四、本地复验证据（回执②③）

- **Ruff**：`ruff check backend/app`（ruff 0.15.12，与 requirements.lock 钉版一致）→ `All checks passed!`，exit=0
- **Import 烟雾**：43 个改动模块逐个 import，43/43 通过（需 `SECRET_KEY` 假值 + 从主仓只读拷贝 gitignored 的 `app/gen/` 后验证，验完即删）
- **定向 pytest**（venv=主仓 .venv py3.11.15 只读复用，DATABASE_URL=sqlite 内存库，三批共 **438 passed / 0 failed**）：
  - 批A 214：test_context_funnel / test_entity_cards / test_absence_detector / test_memory_storage_gate / test_action_plan_contract / test_trace_spine / test_request_coalescing / test_celery_dispatch_async / galaxy test_mastery_evidence / test_redis_checkpointer_allowlist / test_aurora_confirm_bridge
  - 批B 81：test_com011_similar_goal_pursuers（覆盖 community zip/cosine 域）/ test_auth_refresh_rotation / test_spine_orchestrator / test_community_e2e（覆盖 is_read 更新域）
  - 批C 143：test_no_unregistered_routers（router I001）/ test_scenario_pack_names_zh / test_photon_redeem_pro_status / test_batch_worklane / test_a03_friction_diagnosis / test_phase2_intervention_pipeline
- **mypy 零回归**：CI 同款调用（mypy 1.20.2，冷缓存）对 HEAD 基线克隆与本树各跑全量：基线 1975 条、本树 1975 条，按 (file, error-code) 归一化 multiset **完全一致**（存量错误是 CI 下一层洋葱，非本卡范围）
- **守卫**：`run_all_rule_guards.sh` exit-checked。本树仅挂 **AQ/BG**；HEAD 基线克隆同样仅挂 AQ/BG——均因 worktree/克隆缺 gitignored 生成物（`app/gen/`、Dart/Go pb 产物），属环境性，与本卡无关；**首跑曾挂 K/Z 系烟测拷入的 gen/ 含指回主仓绝对路径的 symlink 所致，删除后 K/Z 转绿**。本卡改动对守卫零回归。

## 五、资源峰值（回执④）

无 HEAVY（全程无模拟器/Gradle/浏览器/全库测试）。峰值负载为单进程 ruff/mypy/pytest：内存 <2G，swap 无变化；定向测试三批全程串行、最短路径采集。磁盘：venv 与全部探针均在 /tmp（收工自清），worktree 内新增物仅本报告 + commit 内容。

## 六、交接建议（回执⑤）

1. **合入**：分支本地 commit 未 push；主会话按管线 apply/定向测试/commit/push，worktree 可直接回收。`v3-output/WT285-RUFF-GREEN/changes.patch` 为未跟踪交付副本（与 commit 等价）。
2. **下一层洋葱是 mypy**：冷基线即有 ~1975 条（CI `mypy backend/app` 步在 Ruff 清绿后会立刻暴露），建议独立开卡、按 file×error-code 分桶清（本卡已产出归一化对比方法可复用：剥行号按 multiset diff）。
3. **AQ/BG 守卫在无生成物的 worktree 永远红**：需在主仓或跑过 `make proto-gen`/Flutter 代码生成的树上验收；或后续给守卫加「生成物缺失→SKIP」分支。
4. **gen/ 副本陷阱**：主仓 `backend/app/gen/proto/error_book/` 内含指向主仓绝对路径的 symlink，任何 `cp -R` 拷入 worktree 都会让守卫 K/Z 扫描越界崩溃（ValueError: not in the subpath）——建议后续把主仓 gen 内 symlink 改为真文件或在守卫里跳过 symlink。
5. **black 漂移**：black 26.3.1 与存量代码风格严重漂移（一次全量重排 ~4000 行）。建议要么排期一次性 black 全量格式化（独立卡、禁其他改动混入），要么在 CI/文档里明确 black 仅对新增代码生效。

## 七、清理声明

已删：/tmp/wt285-venv、/tmp/wt285-baseline、/tmp/wt285-stage、/tmp/wt285_mypy_cache_cold、/tmp/wt285_*.txt|diff、worktree 内烟测用 `backend/app/gen/` 副本、`.mypy_cache`。工作树仅含：43 个修复文件改动 + 本报告（tracked）。
