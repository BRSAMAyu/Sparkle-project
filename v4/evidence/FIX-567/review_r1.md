# FIX-567 · R1 独立审查回执

- 审查人：R1（独立未参与会话）
- 审查日期：2026-09-29
- 被审对象：分支 `fix/v4/f567-resume-view-producer`，实现 `5290e010`（5 文件 +394/−20），头 `8ee42b98`，基线 `834651a7`，证据 `v4/evidence/FIX-567/`
- 审查方式：只读 + 临时探针（已还原，探针文件已删，结束工作树干净、被审头不变）；允许本 receipt 单一追加提交
- 环境：darwin arm64；Python 3.11.15（共享主检出 venv）；pytest 以进程级 `SECRET_KEY=x` + 自然 sqlite（与 run_manifest env_discipline 同口径）

## VERDICT: PASS

九项审查靶全部打完，无 FAIL 级发现；1 条 LOW（证据措辞精度，不影响裁决）；预登记 5 挑战点（CH-F567-1…5）逐条裁决如下。

## 编号发现

| # | severity | 位置 | 结论 |
|---|----------|------|------|
| F-1 | INFO | `backend/gateway/internal/db/schema.sql:2077`、`backend/gateway/internal/db/models.go:2784` | 网关存在 `context_selection_receipt` 字样，但仅在**生成物**（自动导出 schema 快照 + sqlc `DO NOT EDIT` 模型）——手写 Go 代码零引用（排除 internal/db 后 grep 空，exit 1）；proto/ 零引用；diff 834651a7..5290e010 触零 proto/gateway 文件。裁决成立：receipt 从不过 WS 帧 |
| F-2 | LOW | `v4/evidence/FIX-567/run_manifest.json`（proto_boundary_ruling / limitations #1「全域 grep 零引用」措辞） | 「backend/gateway 全域 grep 零 context_selection_receipt 引用」字面上不成立（F-1 两处生成物命中）；实质主张（零 WS 帧/零网关逻辑携带 receipt）经亲验为真。建议后续证据措辞加「（手写代码域）」限定；不改代码 |
| F-3 | INFO | `backend/app/api/v1/experience_readouts.py:489-535` | 下发面亲证：REST `GET /experience/context-receipts/latest` 返回 `receipt.to_payload()`（= `model_dump(mode="json")` 透传），`selection_role` 是 payload 字段值非帧结构；移动端 `context_receipt_provider.dart` 消费的正是该 payload（`_project` → `ContextReceiptView.tryParse`） |
| F-4 | INFO | `backend/app/core/context_selection_receipt.py:61-68` | `resume_view` 是 `SELECTION_ROLES` 既有成员；移动端词表镜像 `context_receipt_models.dart:40-45` 含同名值；角色门在 `episode_resume_provider.dart:95`（`!= 'resume_view'` → hidden），与修复角色值逐字一致 |
| F-5 | INFO | `backend/app/core/context_selection_receipt.py:211-272` | 装配只使用既有契约字段（ReceiptInputVersions/ReceiptBudget/ReceiptCandidate/ContextSelectionReceipt 形状逐一对上）——零自造字段、零遗漏必需字段；消费面所需 schema_version/receipt_id/selection_role/candidates/why_now 全部产出 |
| F-6 | INFO | `backend/app/api/v1/episode_resume.py:114-116` | B05 §2 时序亲验：落账在 404 守卫后、`view is not None and observations is not None` 门内、HTTP return 前；off 模式在装配前早退（零回执）；装配+落账整体 try/except 只 WARN（fail-soft）。正反例测试均绿 |
| F-7 | INFO | `backend/app/services/context_selection_receipt_service.py:96-231` | 真源 join 独立探针：写侧 `record_receipt` 只做契约校验（形状/词表/scheme），不拒格式合法的悬空 ref（设计即 E4 读时验证）；探针悬空 task://+goal:// 回执经读面判双 `unresolved`、`resolved_selected_count=0`，真实行 ref 判 `resolved`——join 真实存在，非直通 |
| F-8 | INFO | `backend/app/services/episode_resume_service.py`（本卡 diff） | 零写纪律：diff 只增 ResumeSelectionObservations 数据类 + 可选 observations 字段 + `version_token(updated_at)` 读数填充；服务全部 `.execute()` 均为 `select`；测试文件 diff 零删除行（`test_service_is_read_only_surface` 锚测试原样） |
| F-9 | INFO | `mobile/lib/features/home/presentation/providers/episode_resume_provider.dart:104` | 触发链缺口登记属实：mobile 唯一 I01 调用方是角色门后的 provider（`ApiEndpoints.episodeResumeTask` 全库唯一使用点）；backend 无任何内部调用方（scheduler/事件源零命中）——首条 resume_view 回执确需外部触发源，limitations #2 诚实 |

## 预登记挑战点裁决

- **CH-F567-1（端点层生产挂点）**：成立。锚测试 `test_service_is_read_only_surface` 在场且零改动；观测随 `EpisodeResumeResult` 交付、端点持 db 会话与用户身份；B05 §2 时序本归 API 边界（「resume view 返回之前」= HTTP 返回前，F-6 亲验）。
- **CH-F567-2（触发链间隙定性）**：成立（F-9 亲证）。首条触发需外部源属消费/集成侧后续卡；本卡交付的是生产者本体，与 R1-1 缺陷登记（「生产者缺位」）口径吻合。
- **CH-F567-3（候选集 task+goal 双 selected）**：成立。`_resolve_scheme` 对 `run://` 判 unknown——进候选会在 U03 读面显「来源已不可定位」假阴性；subtask 属 task 聚合内部读。不进候选是诚实读数，扩映射归 I06 sources 增量卡。
- **CH-F567-4（GET 写副作用）**：成立。B05 §8「shadow 写先行」为既有契约设计；`receipt_id` 唯一约束防重放；每聚合一条与 chat 面每 build 一条同纪律，非本卡新引入。
- **CH-F567-5（mypy 波动）**：成立。本审冷缓存 59 = 声称基线 59；改动 5 文件 grep `episode_resume|context_receipt` 零 mypy 错误。

## 独立探针与 mutation（自做，非复述实现者）

1. **HTTP 全链翻转探针**（挂双 router 经 TestClient 走真 HTTP）：chat_context 在场 → latest=chat_context → I01 GET（200+view）→ latest 翻转 `resume_view`，payload 逐断言（selector_version=`episode_resume.v4-f567.v1`、policy_version=null、why_now=null、双 ref selected+双 resolved、resolved_selected_count=2）——2/2 绿。
2. **悬空 ref 探针**：格式合法悬空回执写侧过契约校验（如实）、读面双 unresolved + count=0；随后 I01 真流把 latest 顶为真源回执（双 resolved）——绿。
3. **mutation M1**：删 I01 落账调用 → 恰 2 新正例红（端点正例 + latest 翻转）+ 2 探针红；反例（off 零回执/降级零回执）不误伤。
4. **mutation M2**：候选集剪去 goal:// → 装配形状测 + 端点正例红（2 红），其余 20 绿。
5. 每次 mutation 后还原；还原后 22/22 复绿；探针文件已删、`.mypy_cache` 已清、工作树干净、HEAD 恒 `8ee42b98`。

## 命令与 exit code 清单

| # | 命令（`cd wtF567/backend` 前缀，`PY` = /Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python） | exit |
|---|---|---|
| 1 | `grep -rn 'context_selection_receipt' backend/gateway/`（及 broad 变体、排除 internal/db 变体） | 0 / 0 / 1 |
| 2 | `grep -rn … proto/`；`git diff 834651a7..5290e010 --stat -- proto/ backend/gateway/` | 1 / 0（空 diff） |
| 3 | `SECRET_KEY=x $PY -m pytest tests/api/test_episode_resume_api.py tests/unit/test_context_selection_receipt_wiring.py -q` | 0（22 passed） |
| 4 | `SECRET_KEY=x $PY -m pytest tests/contract/test_context_selection_receipt_contract.py tests/unit/test_context_selection_receipt_sources.py tests/services/test_episode_resume_service.py tests/unit/test_episode_resume_view_contract.py tests/api/test_episode_resume_api.py tests/unit/test_context_selection_receipt_wiring.py tests/integration/test_episode_resume_cross_process.py -q` | 0（130 passed） |
| 5 | `SECRET_KEY=x $PY -m pytest tests/unit/test_calibration_receipt.py tests/unit/test_a06_calibration_receipt.py tests/unit/test_a06_receipt_respond.py -q` | 0（44 passed） |
| 6 | R1 探针 `tests/api/test_r1_probe_fix567_tmp.py`（临时，已删） | 0（2 passed） |
| 7 | mutation M1 后同 #3 + 探针 | 1（4 failed, 20 passed） |
| 8 | mutation M2 后同 #3 | 1（2 failed, 20 passed） |
| 9 | 还原后同 #3 | 0（22 passed） |
| 10 | `rm -rf .mypy_cache && SECRET_KEY=x $PY -m mypy app --ignore-missing-imports --no-error-summary \| grep -c 'error:'`（冷缓存） | 0（=59） |
| 11 | 同 #10 冷缓存重跑 `\| grep -E 'episode_resume\|context_receipt'` | 1（零命中=改动文件零错误） |
| 12 | `$PY -m ruff check <5 改动文件>` | 0 |
| 13 | `$PY -m black --check <5 改动文件>` | 0 |
| 14 | `git status --porcelain`（终态） | 0（空输出，工作树干净） |

## 裁决

**PASS** —— 修复达成 U01 一审 R1-1 的修复意图：resume_view 角色回执生产者落地、契约零自造、时序合 B05 §2、真源 join 可验证、latest 翻转链亲证、零写纪律守住、limitations 如实。F-2（证据措辞精度）不阻塞闭账，建议后续卡修证据措辞或在台账闭账注记中带一句限定。
