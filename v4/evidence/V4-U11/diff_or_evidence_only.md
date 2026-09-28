# V4-U11｜小队、火堆与分享边界风格（diff / evidence only）

分支 `agent/v4/u11`，自 main@dd74bae9 开出；实现头 f2608836。不 push。

## 1. 卡面 → 差量裁决总表

| 卡面 | 裁决 | 依据 |
|---|---|---|
| 邀请小队/冲刺语义保留 | **EVIDENCE_ONLY**（零改动差量举证） | D-COMM-3 已交付：邀请卡（squad ID 一等公民+一键复制，`squad_detail_screen.dart::_SquadInviteCard`）、凭 ID 加入（`joinSquad`）、deadline 冲刺窗口。本卡零触碰该语义，双账号场景 S03/S07 实测可达 |
| sprint 排序不混 XP/光子/私人画像 | **EVIDENCE_ONLY（后端）+ 实现差量（移动端钉）** | 后端 D-COMM-4 已钉：`community_squad_board_service.py` 唯一排序键 = completion/ledger（AST 断言 `test_dcomm5_modules_import_scan_no_xp_photon` + 行为断言零光子）；本卡补移动端镜像钉：`squad_boundary_u11_test.dart` 源码词表钉（squad 两模型零 xp/photon/persona）+ 注入键静默丢弃行为钉。真服场景 S06 单人榜诚实降级实测 |
| 成员/成果卡/火堆呈现统一 | **实现差量** | 火堆：等级徽标 l10n 化（原硬编码「Lv.」）+ 移除假声效开关（详见 §2）；成员面（榜行/在场行）与成果卡（错题卡）D-COMM-4/5 已是 context.typo/DS 令牌呈现——本卡差量举证零重写 |
| 私人 Memory 不进群 | **EVIDENCE_ONLY（后端红线）+ 移动端差量钉** | 后端 S-02 `community_context_boundary.py` 单一守卫面已冻结词表（goal/action/artifact），`tests/unit/test_community_context_privacy_boundary.py` 18 用例含私人 memory/profile 泄露路径拦截（本卡回归 60 绿含此面）；移动端本卡补词表钉：`ShareableContentType` 无 memory/profile 族 + 错题卡模型零答案字段（fromJson 读取面钉） |
| 单实例/多实例实时边界 | **检验差量（脚本+实录）** | `scripts/devtools/v4_u11_two_account_scenario.py` 对真实引擎进程（uvicorn app.main:app --env-file .env，本仓 make api-server 同款）实测：单实例本地扇出（S12）、双进程共享 Redis pub/sub 跨实例双向（S19/S20）。结论见 §4 |

## 2. 实现差量明细（6 文件 + 3 新测试 + 1 devtools）

**撤回腿接线（验收 1「分享/撤回/重连可达」的移动端缺口——后端 D-COMM-5 已有
DELETE 端点，移动端此前只有分享/列表，撤回完全不可达）：**

- `core/network/api_endpoints.dart`：+`squadSharedErrorRetract(groupId, shareId)`
- `features/community/data/models/shared_error_models.dart`：
  +`SharedErrorRetractResult`（share_id/retracted/already_retracted，
  对齐后端 `SharedErrorRetractResponse` 幂等诚实语义）
- `features/community/data/repositories/squad_repository.dart`：
  +`retractSharedError`（DELETE；非本人/已撤 = 后端 404 统一不泄露存在性）
- `features/community/presentation/screens/squad_detail_screen.dart`：
  错题分享段本人分享行内撤回动作（`isMine = sharerId == currentUser`）——
  确认对话 → DELETE → invalidate 列表 + 成功回执；失败诚实报错且行保留
  （不乐观删行、不假撤回）；**他人分享零撤回入口**（UI 不出现，服务端 404 兜底）

**火堆统一（SCREEN_FAMILIES「小队/自我锚/光子/成就」家族：先行动和共享成果，
再火堆装饰；假 affordance 不保留）：**

- `features/community/presentation/widgets/bonfire_widget.dart`：
  等级徽标 l10n（`bonfireLevelBadge(level)`，zh「火堆等级 {level}」/en
  「Bonfire Lv.{level}」）；字号硬编码 12 → `DS.fontSizeXs` 令牌；
  **移除 Crackle/Silent 假声效开关**——该开关只翻图标状态、从不播放任何
  声音（全仓无 crackle 音频资产、无播放调用），属假成功家族；真实音频
  偏好归设置域统一开关（U14 在航，不在装饰组件私设入口）
- `features/community/presentation/screens/group_detail_screen.dart`：
  同步移除 `showCrackleToggle: true` 调用

**l10n（铁律 6：arb 源 + gen-l10n 再生）：**

- `app_zh.arb`/`app_en.arb`：+6 键纯增量（撤回动作/确认题/确认文/成功/
  失败固定文案 + 火堆徽标；`@bonfireLevelBadge` 带 placeholders schema）；
  gen-l10n 再生 106 行纯增、零删键
- **N9/N15 守卫合规**：撤回失败文案不带 {error} 模板（异常细节不直达
  用户面，`debugPrint` 进日志；BG N9-LEAK 守卫 PASS，棘轮 258/260 持平）

**devtools（会话产物不入库，工具入库）：**

- `scripts/devtools/v4_u11_two_account_scenario.py`：双真实账号场景驱动
  （登记进 `scripts/devtools/README.md`）

## 3. 双真实账号场景（真服真容器，20/20 PASS）

- 服务：两台真实引擎进程 `uvicorn app.main:app --env-file .env`（:8211/:8212），
  数据面只读复用运行中容器 sparkle_db/sparkle_redis/sparkle_minio（FIX-557 口径）
- 账号：`u11_a_*`/`u11_b_*` 经 `/api/v1/auth/register` **真实注册**
  （demo/mock 仓库零参与，不冒充真人）
- 实录：`two_account_scenario.json`（每步 HTTP status/WS 帧判定逐字段）
  - 单人完整行动（验收 3）：S03–S06 —— 1/8 成员即完整小队（owner）、
    自习室进入/心跳/在场/退出、<3 人榜诚实降级 `self_view_only=true`
  - 分享/撤回（验收 1）：S08–S10（A 分享→B 可见、白名单零答案字段）、
    S14–S15（A 撤回软删→B 即时不可见）、S16（B 越权撤回 404 不泄露存在性）、
    S17（撤回后再分享 = 新 share_id，非复活旧行）
  - 重连（验收 1）：S11–S13 —— 双账号群 WS 建连、打卡广播双端实时可达、
    B 断连→重连（重新鉴权）→ 群广播恢复可达
  - 实时边界：S12（单实例本地扇出）+ S19/S20（第二引擎进程同数据面，
    Redis pub/sub 跨实例双向）

## 4. 单实例/多实例实时边界结论（如实口径）

- **机制事实**：`app/core/websocket.py::ConnectionManager` 双模——有 Redis 时
  `broadcast` 走 `redis.publish("group:{id}")`（多实例扇出），无 Redis 时
  `_broadcast_local` 仅本进程连接（单实例扇出）；`init_redis` 失败降级仅
  warning 不阻断启动
- **实测**：本地双引擎进程 + 共享 sparkle_redis 下，实例2 上的打卡 HTTP
  与实例1 上的 WS typing 均经 Redis pub/sub 抵达对端实例的 WS 连接
  （S19/S20 PASS）→ **多实例实时边界 = 可达，前提是共享 Redis**
- **边界披露**：Redis 瞬断时 publish 失败无跨节点重试/对账（V3-FIX-66
  已登记的 kick 侧缺口，广播侧同构）——本卡如实引用既有登记，不扩claim

## 5. 零触碰面自证

- RF-06 三冲突面（dashboard_screen/compact_status_bar/task_execution_screen）
  零触碰；`app/routes.dart` 零触碰；`tokens_v2`/theme 通道零触碰
- `backend/app/api/` 零触碰（撤回端点 D-COMM-5 已存在）→ OpenAPI/BA-ROUTES
  机械门不触发（`git diff dd74bae9..f2608836 -- backend/app/api` 为空）
- proto/迁移/生成文件（SQLC、buf 产物）零触碰；mobile/lib/gen 为 gitignored
  实体复制（主检出 cp -R），arb 变更仅经 gen-l10n 再生
- mock/demo 语义零重写：demo 模式小队列表诚实空态（既有行为）本卡以
  `squad_boundary_u11_test.dart` 钉住；mock seed 群「（演示）」后缀（S-03
  既有行为）同卡钉住

## 6. 参考图与令牌

参考图=提案非批准：本卡零参考图移植；UI 全部消费既有 `core/design` 令牌
（DS.* / context.typo/colors/space/radius），零新颜色零新像素资产。
