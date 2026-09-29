# FIX-564 独立审查 receipt（R1）

- 审查人：R1（独立会话，未参与实现）
- 日期：2026-09-29
- 被审对象：commit `9aaa7e6a`（base `d84cf6cc`），分支 `fix/v4/f564-sweep-candidate`
- 审查环境：worktree wtF564，python 3.11.15（主检出 venv），pytest 9.0.2 / mypy 1.20.2 / ruff 0.15.8 / black 26.3.1

## VERDICT: PASS_WITH_CHALLENGES

八靶全打，无 P0/P1 阻断项；1 项 low 级挑战（C1）+ 3 项 info 级发现。修复真实、完整、可复验；事故重放无缺件。

## 逐靶结论

1. **修前缺陷亲复现**：以 `git show d84cf6cc:...` 旁路换入 base 服务文件（/tmp 备份 + cp 还原，规避事故同类 `git checkout --` 操作）→ 同一测试集 **5 failed, 17 passed**，失败全在 `TestWithdrawalSweepCandidateClosure`，形态 `audit["affected_patch_ids"]==[]`（candidate 不进 sweep 亲证）；还原后 md5 一致、**22 passed**。
2. **事故重放完整性**：逐段读 `git show 9aaa7e6a -- backend/app/services/policy_patch_service.py`，五要件全在且无半件——①候选集 `["candidate","evidenced","active"]`；②`_source_withdrawal_visible` 全三分支（memory fresh 投影/decision 未删 outcome 计数/未知域 `return False`）；③验证门 raise 先于一切写（ValueError 零 revoke 结构性成立）；④`affected_states` additive 审计键；⑤`schema_version` 保持 `experience_strategy.v4.i05.v1`。另核实 `kind` 词表校验前置（`RetractionKind(kind).value`，IO 前 fail-loud）。
3. **弃选裁决复核**：D03 `retraction.registered` 载荷 = `{schema_version, retraction_id, kind, target_type="outcome", target_id=outcome_marker_hex[:64], memory_epoch}`（`retraction_recompute_service.py:_write_retraction_event`）；M-07 `memory.invalidated` 载荷 content-free（ids/action/epoch，correlation 携 memory 表 `memory_id`）（`event_registry.py:452-482`、`memory_invalidation_pipeline.py`）。两者均不携带 `memory://experience/expmem_*`/`decision://aurora_*` 引用身份——弃选理由①成立；按 ref 查台账确需新建映射存储，P2"不增第二套身份系统"禁令语境（AGENTS.md）适用。
4. **验证门语义**：`use_cache=False` 真绕缓存（`experience_memory_projector.py:137` 仅 `use_cache` 为真才查类级 `_cache`）；memory 腿谓词 `record is None or not record.has_outcome_evidence` 与 admit `_verify_evidence`（:988）逐字同款反向；decision 腿与 admit（:1008-1017）同谓词（`not_deleted_filter`+`decision_id`+`OUTCOME_OBSERVED`）。虚假报告反例由 committed `test_false_report_refused_then_true_withdrawal_closes_confirm_leg` 钉死（ValueError + patch 保留 candidate）。inference 域：closed-scheme ref 仅 memory/decision 两型（`experience_strategy.py:764-780`），inference 撤回经本入口物理不可验证 → 门 fail-closed 拒绝，docstring 显式声明契约。
5. **I05 契约零削弱**：`git diff d84cf6cc..9aaa7e6a -- backend/tests/unit/` 为空（unit 56 零文件改动亲证）；service 文件仅 2 处 docstring 首行扩注 + 4 测 setup 各增一行 `_withdraw_experience_source(...)` 真撤回步骤，**断言零改动**。R1-B 反证：反转验证门 memory 腿后 I05 原 4 测全红——setup 增步骤真实依赖验证门（非化妆性改动），且原断言语义在 base（旧 sweep）下依旧全绿（红跑 17 passed 亲证）。
6. **mutation 独立杀（R1 自做 3 个）**：
   - R1-A 删 `affected_states` 审计键 → **2 failed**（off 档 + decision 通道两测钉住审计键）→ 还原 22 passed；
   - R1-B 反转 `_source_withdrawal_visible` memory 腿条件 → **8 failed**（新 5 测中 4 测 + I05 原 4 测）→ 还原 22 passed；
   - R1-C 门内 `use_cache=False`→`True` → **22 passed（存活）**，见 C1。
7. **回归与工具链**：本文件 22 passed；unit 56 passed；19 文件邻接回归 **585 passed**（本机重跑）；ruff All checks passed（exit 0）；black 2 files unchanged（exit 0）；mypy 棘轮 **59 / baseline 77（exit 0）**；mypy 零新增复核：两改动文件入口 transitive 闭包 base vs branch **33==33 逐字节同**（diff 零输出），33 条均系他文件既有债务、无一涉两改动文件。
8. **585 构成核对**：逐文件清点合计恰 585——I05 面 78（unit 56 + service 22）、A-05 `test_policy_patch_service.py` 39、D03 23+11=34、M-06 projector 22、D-05 lifecycle 36、friction_chat_wiring 76、semantic_selector 77、hybrid_policy 31、attribution 38、utility gate 25+9、receipt 8+11、experience_event 31+13、presentation 18、no_action_supplement 39。与 manifest 声明逐项吻合，无凑数。

## 编号发现

- **C1（low，挑战）** `backend/app/services/policy_patch_service.py:763`：`_source_withdrawal_visible` 的 fresh 读（`use_cache=False`）无测试钉住（R1-C 变异存活 22 passed）。当前由投影 watermark 失效机制掩盖（测试内软删行会变 watermark），但 run_manifest 声明的"fresh 读绕缓存"性质仅实现未测试化。建议后续卡补一枚毒化类级缓存的钉子测试。
- **F2（info）**：`inference_retracted` 在 `RetractionKind` 词表内（`retraction_recompute.py:103`），经本入口被结构拒绝（closed-scheme ref 不可表达 + 证据仍解析 → 门拒），由 false_report 测试泛化钉住 raise 路径，但无显式以 inference 为名的 committed 测试。
- **F3（info）**：run_manifest 环境注记称 `backend/app/gen` 为"gitignored"——对真目录成立（`.gitignore:246` 带尾斜杠），对符号链接不成立（显示 `??`）。实现者已在提交前移除（审查起点 worktree 干净），无影响；后续 worktree 使用者需知。
- **F4（info）**：审计 `kind` 由调用方原样字符串改为 `RetractionKind` 规范化值——非纯 additive（词表外输入从"静默无命中"变"前置 ValueError"），已在 diff_or_evidence_only.md 声明，core strategy 面零改动，判定合规。

## 事故披露核验

M1 复原丢失事件：以 commit `9aaa7e6a` 终态 diff 为准做了全要件清点（靶 2）+ 全门禁复跑（靶 7）+ 独立变异（靶 6），终态完整、无缺件/半件——事故未造成入库内容缺损。

## 命令与 exit code

| # | 命令（wtF564/backend 下，env `SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`） | exit | 结果 |
|---|---|---|---|
| 1 | base 服务文件旁路换入后 `pytest tests/services/test_experience_strategy_service.py -q` | 1 | 5 failed, 17 passed |
| 2 | 还原（cp+md5 校验）后同上 | 0 | 22 passed |
| 3 | R1-A 变异后同上 | 1 | 2 failed, 20 passed |
| 4 | R1-B 变异后同上 | 1 | 8 failed, 14 passed |
| 5 | R1-C 变异后同上 | 0 | 22 passed（存活→C1） |
| 6 | `pytest tests/unit/test_experience_strategy.py -q` | 0 | 56 passed |
| 7 | 19 文件邻接回归 `-q` | 0 | 585 passed |
| 8 | `ruff check` 两改动文件 | 0 | All checks passed |
| 9 | `black --check --line-length 120` 两改动文件 | 0 | 2 files unchanged |
| 10 | `bash scripts/ci/mypy_ratchet.sh` | 0 | 59 / 77 |
| 11 | mypy 改动文件闭包 base vs branch diff | 0 | 33==33 逐字节同 |
| 12 | `git status --short`（终态） | 0 | 空（干净） |

## 探针还原声明

全部探针（base 旁路、3 个 mutation、gen 符号链接）已还原：审查结束 `git status --short` 干净、分支头 `9aaa7e6a` 不变；本 receipt 为唯一追加内容。
