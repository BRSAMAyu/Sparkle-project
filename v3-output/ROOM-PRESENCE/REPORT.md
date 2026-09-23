# ROOM-PRESENCE — 自习室在场状态保真（服务端 TTL 真源）

> Worker：D 纵队社群线 ｜ worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt191`（基线 `de9b5637`）
> 交付物：本报告 + `changes.patch`（7 文件，+380/-79）｜ 零凭据 ｜ 未 commit / 未 push
> 修复对象：wt167 MOBILE-GAP-3 诚实申报的「无后台心跳 Timer → 在场滞留为假在场」

---

## ① 在场真源盘点 + 设计裁决

### 真源盘点

| 面 | 位置 | 现状（改前） |
|---|---|---|
| 存储 | PG 表 `study_room_sessions`（`backend/app/models/study_room.py`，迁移 dc4room_20260922） | 一记录一进出场；`exited_at IS NULL` 即开放记录；`last_heartbeat_at` 列已存在（NOT NULL） |
| 写路径 | `POST /community/squads/{id}/study-room/enter｜exit｜heartbeat` → `StudyRoomService`（`backend/app/services/community_study_room_service.py`） | enter 幂等建档/刷心跳；exit 置 exited_at；heartbeat 刷 last_heartbeat_at |
| 读路径 | `GET .../study-room/presence` → `get_presence` | **in_room = 仅有开放会话（exited_at IS NULL）**——杀进程/后台后永久假在场；is_stale（心跳>15min）只作弱提示不判离场 |
| 移动端 | `squad_detail_screen.dart` `_StudyRoomCard` | 显式 enter/exit 按钮 + 今日累计 + 全员列表；`squadPresenceProvider`/`squadMyRoomStatusProvider` 均为一次性 autoDispose 快照，**无任何轮询**（如实申报：foreground 轮询不是现状） |
| 网关 | `proxy_routes.go` 纯代理（dcomm4 测试钉注册面） | 无语义，零改动 |

### 设计裁决（含理由）

**模型：服务端 TTL 真源，读路径只认未过期。** `in_room = 开放会话 且 now - last_heartbeat_at ≤ STUDY_ROOM_PRESENCE_TTL_SECONDS(90s)`。TTL 过期 = 诚实离场（**惰性判定**：读路径计算，无需后台清理任务，无 Redis 依赖）。

1. **续期信号 = 前台房间轮询（30s 一拍心跳+在场）**——最省的诚实信号源：
   - 诚实性最强：看着自习室 = 在自习室；作用域恰好等于房间（不串队）；
   - 备选否决——学习活动：语义最弱（在 A 队聊天不该续 B 队自习室的在场），且要挂多个写路径不省；WS 帧：自习室屏不持 WS，为此建连接反而更重；
   - 合规：绝不要求后台 Timer——移动端 `WidgetsBindingObserver` 门控，`AppLifecycleState` 一离开 resumed 即停拍；后台/杀进程后无续期，在场由服务端 TTL 如实衰减（≤90s 残留后消失）。
2. **TTL = 90s**：移动端 30s 拍距下可容单拍网络失败；比旧 15min 陈旧阈值收紧两个数量级，「假在场」残留窗口从无限 → ≤90s。功耗：仅前台可见期每 30s 一个小 JSON 调用。
3. **零迁移**：TTL 复用既有 `last_heartbeat_at` 列（本就是 NOT NULL 时间戳），无 schema 变更、无新表、无 Redis（拒绝 Redis 的理由：在场时长结算在 PG 会话记录上，引 Redis 会造第二真源）。
4. **enter 撞 decayed 开放会话**：按诚实离场时刻收档（`exited_at = last_heartbeat_at + TTL`，即模型定义的衰减终点）后**新建记录**——「一记录一进出场」历史不变，已证明的今日时长保留，用户无需先手动退出。
5. **heartbeat = 显式续期**：房间 UI 发来的活性证明，对 decayed 开放记录也续命（不是自动重开——无开放会话时仍诚实上报、不建档）；瞬时网络抖动导致的短暂衰减在下一拍自愈，期间对队友如实显示缺席（诚实=有证据才在场）。
6. **时长诚实封顶**：会话计入终点 = `min(退出时刻或现在, last_heartbeat_at + TTL)`（`_effective_end`）——decay 后今日累计不随墙钟虚增；显式退出的会话按退出前最后活性证明封顶，失联期不算自习时长。
7. **is_stale 重定义**：有开放会话但 TTL 已过期（异常退出待回收的崩溃恢复线索）→ `in_room=False + is_stale=True`；UI 灰点照旧 + 时钟图标提示「心跳滞后，可能已断线」，移动端契约字段零变更。
8. **对现有读面的兼容**：API 形状（字段/端点）零变更 → 网关代理与移动端 fromJson 全兼容；存量开放会话（心跳久远）在新读路径下自然判离场——正是本卡要的行为；北顶点 eval `feature_tour.py` S4 阶段全程秒级完成，不受 90s TTL 影响（核对过断言面）。

---

## ② 实现清单

**后端**（TTL 真源，全部语义在此）：
- `backend/app/schemas/community_study_room.py`：`STUDY_ROOM_STALE_MINUTES(15)` → `STUDY_ROOM_PRESENCE_TTL_SECONDS(90)`；in_room/is_stale 字段描述与契约文档按 TTL 语义改写（形状不变）。
- `backend/app/services/community_study_room_service.py`：
  - 新增 `_is_alive()`（TTL 在场判定）与 `_effective_end()`（时长诚实封顶，含时钟回拨防御）；
  - `get_presence`：in_room 只认未过期；is_stale=开放但过期；`entered_at`/`current_session_minutes` 仅在场时给出；
  - `_today_minutes_for`：所有会话计入终点封顶于 hb+TTL（decay 不虚增）；
  - `enter_room`：TTL 内幂等刷心跳（不变）；撞 decayed 会话 → 收档+新建；
  - `exit_room`：立即清档（含 decayed 回收）；`session_minutes` 按退出前 hb+TTL 封顶；
  - `heartbeat`：语义升级为显式续期（行为本就刷新，文档钉死）；无会话不自动重开（不变）。
- `backend/app/models/study_room.py`：模型文档钉 TTL 真源语义（零 schema 变更）。

**移动端**（轻配合）：
- `squad_detail_screen.dart` `_StudyRoomCard`：前台续期拍——`WidgetsBindingObserver` + `Timer.periodic(30s)`，仅 `resumed` 时运行；每拍 invalidate 心跳+在场两个 provider（续期本人 TTL + 刷新全员列表）；回前台立即拉一次诚实状态；paused 即停拍；dispose 注销 observer 并取消 Timer。
- `study_room_models.dart`：契约文档注释按 TTL 语义改写（字段与 fromJson 零变更）。

**gen/ 环境还原**（非交付物，gitignore 覆盖，未进 patch）：从主仓拷贝 `mobile/lib/gen`（27 文件）、`backend/app/gen`、`backend/gateway/gen`——worktree 缺生成物导致 flutter/go/pytest 无法编译，属基线环境缺口。

---

## ③ 冲突面声明

| 在航卡 | 面 | 与本卡关系 |
|---|---|---|
| wt178 | mobile galaxy/chat | **零冲突**：我动 community 域 `squad_detail_screen.dart`/`study_room_models.dart`+其测试，不碰 galaxy/chat |
| wt180 | event_bus+网关 | **零冲突**：网关零改动（仅跑其 dcomm4 代理测试作回归证据，PASS） |
| wt187 | loguru 批量 | **零冲突**：我未动日志面 |
| wt189 | 评测资产 | **零冲突**：核对 `feature_tour.py` S4（enter→heartbeat→presence 秒级串行），TTL 语义兼容，未改动该文件 |
| wt190 | tests/orchestration | **零冲突**：我只动 `tests/unit/test_community_study_room.py`（社群域） |

改动全集（7 tracked 文件）：后端 4（models/schemas/services/单测）+ 移动端 3（screen/models/单测）。无跨队文件。

---

## ④ 诚实申报

1. **foreground 轮询不是移动端现状**（卡面预置选项不成立）：改前移动端是纯一次性快照取数。本次为续期信号补了 30s 前台轮询（轻配合的实现主体），并如实计入移动端改动。
2. **语义变化集中在两点**，行为断言旧→新：a) 心跳超 TTL 者从「在场+stale 弱提示」变为「诚实离场」（`test_presence_lists_members_with_ttl_and_stale_flag` 按新语义重写，原 stale 测试名退役）；b) decayed 会话的今日累计从「随墙钟虚增」变为「封顶于 hb+TTL」。其余 12 条基线验收（防刷 AST+行为双钉、enter/exit 幂等、跨日窗口、隐私 403/404、API 回路、小队榜全量）**零改动通过**——community/squad 域回归对比法零新增达成。
3. **边界语义如实申报**：恰好 age==TTL 仍算在场（`<=`），越界 1s 判离场（红证测试钉死）；网络抖动致单拍失败时最长 60s 对队友显示缺席后自愈（诚实=有证据才在场，可接受）；「N 人在室」头部在两拍间最多滞后 30s。
4. **worktree 环境缺口**（非本卡造成，已修复并申报）：`mobile/lib/gen`、`backend/app/gen`、`backend/gateway/gen` 在 wt191 缺失，从主仓拷贝后方能编译/测试；gen/ 产物未进 patch。
5. 未跑全量 `flutter test`（HEAVY 纪律+wt178 错峰）与全量 backend pytest：只跑了本卡域 + community 回归（30 passed）+ 网关 dcomm4 代理测试（PASS）+ 目标 widget 测试（5 passed）。全量回归建议合入后由主会话统一跑。
6. 黑格式化过测试文件一处（`.scalars().all()` 链式换行）；ruff/black/dart analyze 全绿。

## ⑤ 收工核查

- [x] 红证：TTL 过期 → 读路径不再在场（`test_ttl_expiry_is_honest_departure_and_minutes_stop_accruing`：边界 1s 内外对照 + 时长封顶不虚增）
- [x] exit 立即清（`test_exit_clears_presence_immediately_even_fresh`：刚 enter 即退 → 零残留零 is_stale）
- [x] 续期信号续命（`test_heartbeat_renews_ttl_for_active_only`：120s>TTL 仍在场 vs 无续期队友同期衰减，对照组设计）
- [x] 多人混合在场列表正确（重写的 presence 测试：活跃/decayed/已退/未入场 4 人 + 非成员不可见 + 计数正确）
- [x] decay 收档（`test_enter_after_ttl_decay_rearchives_and_preserves_proven_minutes`：旧档收于 hb+TTL、新档 now 起算、已证明 31 分钟保留、开放会话恒 1 条）
- [x] 口径红线：「在场」绝不造假——杀进程后最多 90s 残留，TTL 后诚实消失；时长 decay 不虚增；不进榜分红线（D20 AST 扫描）持续钉死
- [x] 测试：backend `test_community_study_room.py` **17 passed**；community 回归 3 文件 **30 passed**；网关 `TestProxyRoutesHandler_SquadStudyRoomAndBoardRoutesRegistered` **PASS**（CGO_ENABLED=0）；移动端目标 widget 测试 **5 passed**（跑前 ps 查无 flutter/gradle 进程、swap 1361M、load 3.3，HEAVY 门放行，单文件串行）
- [x] lint：ruff 全过、black 全过、`dart analyze` 3 文件 No issues
- [x] 纪律：未 commit/未 push、零凭据；交付物=本报告+`changes.patch`
- [x] 收工清理：`mobile/.dart_tool`、`mobile/build` 已删；`/tmp` 自产文件已清；无残留进程；gen/ 拷贝留 worktree（gitignore 覆盖，随 worktree 生命周期回收）

**验证命令复现**：
```bash
cd backend && SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" python3.11 -m pytest tests/unit/test_community_study_room.py -q
cd backend/gateway && CGO_ENABLED=0 go test ./internal/handler/ -run TestProxyRoutesHandler_SquadStudyRoomAndBoardRoutesRegistered -count=1
cd mobile && flutter test test/features/community/presentation/screens/squad_detail_screen_test.dart --concurrency=1
```
