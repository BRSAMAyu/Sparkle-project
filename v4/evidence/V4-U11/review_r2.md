# V4-U11 二审 receipt（R2 · wtU11R2）

- 审查者：wtU11R2（独立会话，未参与 U11 实现与一审）
- 审查对象：`agent/v4/u11` @ `ecda5a5d`（审查时含一审 receipt 提交 `9710fe93`，工作树 clean）；链 = 实现头 `f2608836` → 证据 `1fcba073` → 分支头 `ecda5a5d` → 一审 `9710fe93`
- 卡标准：`v4/04_tasks/tasks.json` `V4-U11`（high risk，2 独立审查，lock=ui-community）
- 审查方式：只读审查 + 一审勘误逐条复核 + 终态核心面亲跑 + 红线抽验/mutation 复放 + 真服双进程场景重跑（用后即关即删）+ 合落差 merge-tree 亲验
- **裁决：APPROVE（成立）**——一审 5 挑战点裁决经抽验无翻案；一审 3 条勘误逐条复核**全部属实**；未发现一审遗漏的阻断面

## 1. 一审勘误复核（首靶）——3/3 属实

| # | 一审勘误 | R2 亲核 | 判定 |
|---|---|---|---|
| ① | arb 新键实数 6 非 7；生成行数 80（manifest 106/limitations 83 陈旧） | `git diff dd74bae9..ecda5a5d -U0 -- mobile/lib/l10n/app_{zh,en}.arb` 亲数：每语言恰 **6 新键**（squadSharedErrorRetractAction/ConfirmTitle/ConfirmBody/Success/Failed + bonfireLevelBadge）；生成三文件 `--stat` = 36+23+21 = **80 行**（合计 106 = 80 生成 + 26 arb 源——manifest gen_note 的"+7 键"与 limitations #4"+7 键"/#7"83 行"为陈旧数字，manifest commands[4]"6 新键/106 行纯增"本身自洽） | **属实** |
| ② | f2608836 不过 N9、修正折叠在 1fcba073；最终代码态以 ecda5a5d 为准 | `git diff f2608836..1fcba073` 亲验：修正 = 撤回失败文案 `{error}` 参数化（zh/en arb + 生成 4 文件）→ 固定人话文案 + `squad_detail_screen.dart` 加 debugPrint；**终态 N9 守卫亲跑** `python3 scripts/guards/check_n9_raw_exception_leak.py` → **PASS exit 0**（arb {error} 258/260, bareCatchVar 73/76, catchVarToString 77/78, assignmentFace 18/18，零 baseline 更新） | **属实** |
| ③ | 权威卡库 PENDING 未同步 | 分支内 `v4/04_tasks/tasks.json` V4-U11 = in_progress/REVIEW_READY；权威卡库（Sparkle-project main@4152266c）= **PENDING/NOT_STARTED/NOT_RUN**。属派发方收口事项（本卡两审齐后置 DONE_REVIEWED），非证据缺陷 | **属实（收口项）** |

处置建议：①②以本 receipt + review_r1.md §6 为准即可收口；若实现者补一次 evidence 提交修数字更佳（非必须，不阻断）。③由协调者在收口合并时随 tasks.json 终态直写解决。

## 2. 终态代码复验（全部亲跑，ecda5a5d 树）

| 项 | 命令 | 实测 |
|---|---|---|
| 本卡新测 14 | `flutter test` 3 文件（retract/bonfire/boundary） | **+14 All tests passed** |
| 移动端社区回归 | `flutter test test/features/community/ test/widget/community_remaining_closure_test.dart` | **+100 All tests passed**（34s） |
| 后端社区四套 | `pytest tests/unit/test_community_shared_errors.py tests/unit/test_community_squad_mvp.py tests/unit/test_community_context_privacy_boundary.py tests/unit/test_community_study_room.py -q`（.env 移出 + SECRET_KEY=test，验后还原） | **60 passed**（44.14s） |
| S05 双账号 E2E + WS 生命周期 | `pytest tests/api/test_s05_community_reconnect_retract_two_account_e2e.py tests/unit/test_community_ws_session_lifecycle.py -q`（同上口径） | **33 passed**（67.93s） |
| N9 棘轮 | `scripts/guards/check_n9_raw_exception_leak.py` | **PASS exit 0**（258/260 持平） |

diff 面亲核：`git diff dd74bae9..ecda5a5d --name-only` = community 6 代码文件 + l10n 5 文件 + 3 测试文件 + devtools 脚本+README + tasks.json + 7 证据件；`-- backend/app` 为空——与 manifest 披露触达面完全一致，零越面。

## 3. 隐私/量纲红线抽验

- **白名单禁词 grep（抽 3 词，实际 11 词全查）**：以一审原跑账号 `u11_b_20260928210149_3feb3298` 真实密码重新登录（同密码独立登录口径同 R1），拉取 squad `45e4d098` 的 `/shared-errors` 响应体落盘 grep：`correct_answer`/`user_answer`/`persona`（抽验 3 词）+ solution/correct_approach/similar_traps/ocr_text/ai_analysis_summary/answer/xp/photon → **11 词零命中**；item 键集恰为 `SharedErrorEntry` schema（`backend/app/schemas/community_shared_errors.py:49-75`）19 键白名单。
- **存储面**：`squad_shared_errors.content ?| ARRAY['correct_answer','user_answer','solution']` 对原跑两行（27f6c106/91ef29e0）= **f / f**。
- **schema 结构层**：`SquadMemberSprintProgress`（`backend/app/schemas/community_squad.py`）字段集零 xp/photon/persona（grep 仅命中文件头规则注释，非数据流）；`SharedErrorEntry` 同净。
- **量纲 mutation 复放（1 次，验后即还原）**：`community_squad_board_service.py::_sort_key` 首位注入 `-getattr(member, 'photon', 0)` → `pytest tests/unit/test_community_study_room.py::test_leaderboard_sorting_ties_percentile_and_pagination` → **1 failed**（精确名次断言红）→ 还原后 `git diff` 树 clean。与一审 mutation 结论同向，"注入必红"判别力成立。

## 4. 双账号场景抽核与端到腿重跑

- **原始记录 DB 抽核 4/4 吻合**（sparkle_db 只读查询）：① `users.u11_a_20260928210149_c9e00ff7` created 21:01:49.927；② `u11_b_20260928210149_3feb3298` 21:01:50.798；③ `groups.45e4d098`（"U11 双账号场景队 20260928210149"，21:01:51.502）；④ `squad_shared_errors` 两行：27f6c106（21:01:51.96 建 → **21:02:00.93 deleted_at**）+ 91ef29e0（21:02:00.98 新行未删，非复活）；两行 sharer_id `8760f223` = u11_a 用户 id 亲映射。与 two_account_scenario.json 逐步吻合。
- **端到腿重跑（超出"至少 1 腿"）**：自起 uvicorn :8211/:8212 双实例（本仓 backend 代码 + 主检出 .venv + sparkle_db/redis 容器，双实例日志均见 "WebSocket Redis Pub/Sub initialized"），复跑 `scripts/devtools/v4_u11_two_account_scenario.py` → **20 PASS / 0 FAIL / 24.78s**（新账号 u11_a/b_20260928220543_*）。**撤回腿端到端**：S14 A 撤回（200, retracted=true）→ S15 B 列表即时 `b_total=0` → S16 非分享者撤回 **404** → S17 再分享新 share_id（0d00ec15 ≠ 7e409a2f）；DB 时间线 22:05:48.85 建 → 22:06:00.28 软删 → 22:06:00.80 新行，与实录一致。单人行动面 S04（1/8 成员 owner 可达）/S05（自习室 enter/heartbeat/presence/exit 全 200）/S06（<3 人 self_view_only+board_valid=false 诚实降级）同轮全 PASS。

## 5. 合并落差终验（main 已推进）

- 本机 `origin/main=dce840da`（U14 收口，arb 并集已解）；主检出本地 `main=4152266c` 含 **ab1b8339（Q03 收口合并）**。
- `git merge-tree dd74bae9 HEAD ab1b8339` → **0 CONFLICT**（输出中唯一 "CONFLICT" 字样为 receipt 引文内容）；changed-in-both = l10n 5 文件（arb×2 + 生成×3）。
- 键集亲验：U11 新 6 键（squadSharedErrorRetract*/bonfireLevelBadge）与 Q03 侧新键（galaxy*/sensory*/homeResume*/objectUnavailable*/cal*/journeyEntryFailed）**零交集**（表面"交集"仅为 placeholders 元数据行形态相同）——limitations #7 预判"键集不相交则并集即可"成立。合并落差无阻断。

## 6. 裁决校准（一审遗漏面排查）

- **C1 授权面 HEAD 亲核**：`community_shared_error_service.py:338-353` `retract_shared_error`——`_require_active_member` 后 `sharer_id != requester_id or is_deleted or group_id 不符 → LookupError`；`community_squad_shared_errors.py:37-44` `_map_share_error` 将 LookupError 统一 404（不泄露存在性）、SquadPermissionError 403。本轮 S16 真服重跑复现 404。无绕过面。
- **demo 标记**：`community_repository.dart:14-18` DemoDataService.isDemoMode → MockCommunityRepository 门控；`mock_community_repository.dart:119-177` demo 群名一律 `l10n.demoGroupSuffix` 后缀（arb："（演示）"/" (demo)"）；新测 14 内"mock community repo seeds are explicitly marked as demo"钉绿。demo 不冒充真人成立。
- **单人完整行动**：S03-S07 本轮重跑全 PASS（验收 ③ 服务端面）；移动端 demo 诚实空态钉在 14 内。
- 未发现 demo 标记、单人行动面或其他面的一审遗漏阻断面。R1 的 C2（假 affordance 移除非回退）/C4（多实例口径）经证据与代码锚复核无翻案理由。

## 7. 遗留与处置（均不阻断）

1. 文档陈旧数字（勘误①：+7 键→实为 6；83 行→实为 80）——以本 receipt §1 为准，或实现者收口时顺手修正。
2. 权威卡库状态同步（勘误③）——派发方收口动作。
3. 场景重跑与原跑同向共享 dev DB 写入（u11_a/b_20260928220543_*、squad 7d63cfb3、share 7e409a2f/0d00ec15），与既有探针残留同惯例留存审计；本地两引擎进程已关（端口 000 复核）、探针文件已删。

## 8. 结论

卡三条验收终态证据齐备且可复现：①双真实账号分享/撤回/重连可达（20/20 重跑 + DB 时间线实证）；②sprint 排序不混三量纲（schema/AST/行为/移动端四层 + mutation 复放 1 red）；③单人完整行动 + demo 角色明确标记（重跑 S03-S07 + 演示后缀/门控亲核）。高风险卡两份独立审查（R1 APPROVE + R2 APPROVE）齐备。**R2 裁决：APPROVE，维持一审裁决**；§7 三项遗留由实现者/协调者收口处理，不影响过点。
