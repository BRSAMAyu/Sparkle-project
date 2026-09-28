# V4-U11 一审 receipt（R1 · wtU11R1）

- 审查者：wtU11R1（独立会话，未参与 U11 实现）
- 审查对象：`agent/v4/u11` @ `ecda5a5d`（实现头 `f2608836`，基线 `dd74bae9`）；审查时工作树 clean
- 卡标准：`v4/04_tasks/tasks.json` `V4-U11`（high risk，2 独立审查，lock=ui-community）
- 审查方式：只读审查 + 独立复跑（真服双进程本地起服、用后即关即删）+ 4 组 mutation 证伪
- **裁决：APPROVE**（预登记 5 挑战点全部证伪失败=实现成立；全数复跑绿；4 组 mutation 均如声称变红；非阻断勘误 3 条见 §6）

## 0. 独立复跑总表（本会话实测，非转抄）

| 项 | 实现者声称 | R1 实测 | 结果 |
|---|---|---|---|
| 双账号场景 20 步 | 20 PASS / 0 FAIL | 自起 uvicorn :8311/:8312（本仓 backend 代码 + 主检出 .venv + 运行中三容器），复跑 `scripts/devtools/v4_u11_two_account_scenario.py`：**20 PASS / 0 FAIL，20.49s**（新账号 u11_a/b_20260928214143_*） | 一致 |
| 白名单零答案字段 | S10 has_answer_field=false | **亲验强于脚本**：以 A/B 双 token 拉 `/shared-errors` 全量响应体落盘 grep 10 个禁词（correct_answer/user_answer/solution/correct_approach/similar_traps/ocr_text/ai_analysis_summary/answer/persona/xp/photon）→ **零命中**；item 键集=后端白名单 19 键；存储面 `content` jsonb 键集同白名单（`content ?| ARRAY['correct_answer','user_answer','solution']` = f） | 一致且更强 |
| 撤回授权 S16 | 404 | 重跑复现 404；服务端代码锚 `community_shared_error_service.py::retract_shared_error`（sharer_id 比对→LookupError→`community_squad_shared_errors.py::_map_share_error`→404） | 一致 |
| 新测 14 | 全绿 | `flutter test`（3 文件）：**+14 全绿** | 一致 |
| 移动端社区回归 | 100 passed | **+100 全绿** | 一致 |
| 后端社区单测 | 60 passed | **60 passed**（.env 移出 + SECRET_KEY=test，conftest 守卫同口径） | 一致 |
| S05 双账号 E2E + WS 生命周期 | 33 passed | **33 passed** | 一致 |
| N9 棘轮 | 258/260 PASS | HEAD 实测 PASS：arb {error} 258/260, bareCatchVar 73/76, catchVarToString 77/78, assignmentFace 18/18 | 一致 |
| 五件套+场景件 SHA256 | run_manifest 登记值 | shasum -a 256 五文件逐一比对 | 全部一致 |

## 1. 预登记挑战点逐项独立裁决

### R1-C1 撤回授权面绕过 — **实现成立**
- 服务端真源：`backend/app/services/community_shared_error_service.py` `retract_shared_error`：成员校验（`_require_active_member`）后 `share.sharer_id != requester_id or is_deleted or group_id 不符 → LookupError`；API 层 `_map_share_error` 把 LookupError 统一映射 404（不泄露存在性）。非成员→SquadPermissionError→403（只暴露"非成员"，不暴露分享存在性）。
- 端上 `isMine` 只是呈现面：绕 UI 直调 DELETE 已被服务端 404 兜底，S16 重跑复现。
- 变异路径（伪造 sharer）不必打真服：代码路径上 requester_id 恒取 `current_user.id`（`get_current_user` 依赖注入），客户端无从指定 sharer——伪造面不存在。
- UI 测试钉三反例（他人零入口/失败不假删行/取消零调用），`squad_shared_error_retract_u11_test.dart` 实读核过。

### R1-C2 声效开关移除是否视觉回退 — **实现成立（非回退，是假 affordance 移除）**
- 独立核实假开关性质：全仓 `mobile/assets` 无 crackle/任何音频资产；`bonfire_widget.dart` 旧实现只翻 `_crackleEnabled` bool + 换图标 + `SensoryFeedbackService.emit(selection/tap)`（触觉 selection，非声音）——**无声效可开关=假成功家族**，与卡 stop_conditions"发现假成功隔离不绕门"同向。
- SCREEN_FAMILIES（`v4/02_design/SCREEN_FAMILIES.md:19`）："先行动和共享成果，再火堆装饰"——移除装饰性假开关与家族语义一致；"用户可关闭庆祝"由设置域（U14 在航）承接，不在装饰组件私设。回退路径（revert 两文件）已如实登记。

### R1-C3 双账号真实性 — **实现成立（DB 级实证，超出转录核对面）**
- 对共享 sparkle_db 只读查询：`users` 表存在 `u11_a_20260928210149_c9e00ff7`（created 2026-09-28 21:01:49.927）与 `u11_b_20260928210149_3feb3298`（21:01:50.798）——**与实录账号名/内嵌时间戳逐一吻合**；`groups` 表存在 squad `45e4d098-...`（21:01:51.502，名"U11 双账号场景队 20260928210149"）；`squad_shared_errors` 两条：`27f6c106`（21:01:51.96 建，21:02:00.93 软删=S14）与 `91ef29e0`（21:02:00.98 建=S17 新 share_id）——**软删时间线与实录 20 步时序完全自洽**（elapsed 18.57s）。
- 另见 21:00:11 的首轮账号/小队残留——与 manifest 披露"一次 2 FAIL→脚本修正复跑"过程事实吻合，非掩盖迹象。
- mock/demo 零参与：脚本走 `/api/v1/auth/register|login` 真端点（脚本实读核过，R1 并以同密码独立重新登录两新账号完成白名单探针）。

### R1-C4 多实例声称口径 — **实现成立（字面满足卡面，边界披露诚实）**
- 卡验收字面"检验单实例与多实例实时边界"：S12（单实例扇出）+S19/S20（双进程共享 Redis pub/sub 双向）即"检验"了该边界；实现者只声称"机制可达、前提共享 Redis"，未声称生产 LB/粘滞/扩缩容——口径未越界。
- 机制代码锚核实：`app/core/websocket.py:345-350` `broadcast` 双模（有 Redis→`publish("group:{id}")`，无→`_broadcast_local`）；R1 自起双实例日志均见"WebSocket Redis Pub/Sub initialized"，S19/S20 重跑双向可达。
- Redis 瞬断缺口（kick 侧 V3-FIX-66 已登记、广播侧同构）如实引用未扩 claim，核实属实（websocket.py:302-324 注释即该登记）。

### R1-C5 量纲红线三层覆盖 — **实现成立（mutation 实证"必红"为真）**
- 后端结构层：`SquadMemberSprintProgress` schema（community_squad.py:97-112）**字段集本身零 xp/photon/persona**——排序键想读行为量须先改 schema+聚合，攻击面在结构上被封。
- 后端 AST+行为层：`test_squad_modules_import_scan_no_xp_photon_leaderboard`（squad_mvp:141）+ `test_progress_indifferent_to_photon_and_flame_mutations`（:163）+ `test_share_produces_zero_photon_and_zero_board_delta`（shared_errors:171）——R1 全数复绿（60 内）。
- **R1 mutation 实测**：向 `_sort_key`（`community_squad_board_service.py:33`）首位置注入 photon 键并跑四套→**1 failed**：`test_community_study_room.py:517 test_leaderboard_sorting_ties_percentile_and_pagination`（断言精确名次 [1,2,3,4]）——排序键元组形状/序语义有专门判别性测试，"注入必红"声称成立（mutation 后已还原，树 clean）。
- 移动端差量钉真实有判别力：见 §3 mutation。

## 2. 双账号 20/20 可信性（最重靶）— **可信，20/20 全量独立复跑通过**
- 抽核 ≥6 条：S01/S02（账号，DB 实证）、S03（squad，DB 实证）、S10（白名单，亲验强化）、S14/S15（软删+传播，DB deleted_at 实证）、S16（404，重跑复现）、S17（新 share_id，DB 两行实证）、S19/S20（跨实例，重跑复现）——9 条，全部吻合。
- 端到端重跑：**全 20 步**（超出"≥2 条"要求），exit code 0。
- 脚本弱点（不影响裁决）：S11 的 PASS 是"建连未抛异常"的隐式判定（异常会使脚本崩溃无输出，可视作 fail-loud）；WS 走 `?token=` query（`settings.WS_ALLOW_QUERY_TOKEN` 门控的 dev 便利路径，token 仍为真注册账号 JWT，卡面零触碰鉴权）。
- 限额替代腿核实：S13/S20 用群 WS typing 广播替代打卡——代码上 typing 与 checkin 同走 `manager.broadcast` 同一扇出路径，limitations #3 披露准确；A 的打卡额度 S12 消耗、B 的留给 S19，脚本编排自洽。

## 3. mutation 证伪汇总（4 组，全部"声称红→实测红"，验后即还原）
1. **N9**：checkout f2608836 版 6 文件→guard FAIL（3 violations：arb zh/en 新 `{error}` 条目 ×2 + squad_detail_screen bareCatchVar +1）→ 还原 HEAD PASS。证实"N9 修正发生在证据提交 1fcba073"的过程叙述属实。
2. **后端排序键投毒**：`_sort_key` 注入 photon→60 套件 1 red（study_room:517 名次断言）→ 还原。
3. **移动端答案泄漏**：`shared_error_models.dart` fromJson 加 `leakedAnswer: json['correct_answer']`→`squad_boundary_u11_test.dart` red，理由逐字命中 `must not read "json['correct_answer']"`→ 还原。
4. **移动端量纲源词表**：`squad_board_models.dart` 加 xp 词→源码钉 red（`must not reference "xp"`）→ 还原。
- 结论：隐私钉与量纲钉**不是恒绿装饰测试**，判别力实证。

## 4. 数字与披露核
- 14=4（撤回一正三反）+2（火堆一正一反）+8（边界钉）——三分文件实数吻合，14/14 复绿。
- 100/60/33 全部复现（§0 表）。
- 全量 3035/-1：未重跑（时长成本；-1=q03 goldens tearDownAll 披露合理），但**零文件交集**核实：card 触达面（community 6 文件+l10n+devtools+3 测试文件）与 `test/goldens/q03_visual_qa/*` 无交集。
- backend/app 零触碰：`git diff dd74bae9..f2608836 -- backend/app` 为空（实跑）。
- merge 落差：main 已推进至 `dce840da`（比审查简报的 65e3ad38 更新，含 U14 一审+arb 并集解）。`git merge-tree dd74bae9 HEAD origin/main`：**0 CONFLICT**；changed-in-both 6 文件=l10n 四件+arb 两件+tasks.json；U11 六新键在 main 全部不存在、U14 新键（sensory*/cal*/galaxy*）与 U11 键集不相交——limitations #7 预判的"键集不相交则并集即可"成立，合并落差无阻断。

## 5. 测试质量抽评
- 撤回 UI 套件授权三反例 + 失败不乐观删行断言行保留 + 取消零副作用——反例覆盖到位。
- bonfire 反例断言 Crackle/Silent 文案与两图标 findsNothing——覆盖移除面。
- 小疵（不阻断）：`bonfire_widget_u11_test.dart` `pumpBonfire(level:)` 参数为死参（widget 恒 `level:3`）；S11 隐式 PASS（见 §2）。

## 6. 非阻断勘误建议（供实现者/协调者收口时修正）
1. **文档计数不一致**：HEAD 实际新键=6（Action/ConfirmTitle/ConfirmBody/Success/Failed/BonfireLevelBadge）；`limitations.md` #4 写"+7 键"、`run_manifest.json` toolchain.gen_note 写"+7 键"而 commands[4] 写"6 新键"；生成文件行数 manifest 106 / limitations 83 / HEAD 实测 80（36+23+21）。建议统一为 6 键/80 行（HEAD 口径）。
2. **实现头状态披露**：`source_sha_head_impl=f2608836` 本身**不过 N9 守卫**（3 violations，R1 mutation 实证），N9 修正折叠进证据提交 1fcba073——过程合规（manifest commands[14] 如实叙述），但台账读者应知 f2608836 非最终代码态；最终态=ecda5a5d（本审查对象，守卫 PASS）。建议 R2/台账以 ecda5a5d 为准。
3. **卡库状态同步**：分支内 `v4/04_tasks/tasks.json` 已置 in_progress/REVIEW_READY，而权威卡库（Sparkle-project）仍 PENDING/NOT_STARTED——属派发方状态同步事项，非证据缺陷。
- 复核说明：场景重跑与原跑同向共享 dev DB 写入（u11_a/b_20260928214143_*、squad 3c264fee、share 26d3c175/0d053891），与仓库既有探针残留同惯例，未清理以留存 R1 审计痕迹；本地起服两进程已关、探针脚本/临时文件已删。

## 7. 结论
预登记 5 挑战点（C1 授权面/C2 视觉回退/C3 双账号/C4 多实例口径/C5 量纲三层）全部独立下判为"实现成立"；卡三条验收——①双真实账号分享/撤回/重连可达（20/20 复跑+DB 实证）、②sprint 排序不混三量纲（schema/AST/行为/移动端四层+mutation 判别力实证）、③单人完整行动+demo 标记（S03-S07+demo 空态/标记钉）——均有独立复现证据。**R1 裁决：APPROVE**，等待第二独立审查（R2）；§6 勘误不阻断。
