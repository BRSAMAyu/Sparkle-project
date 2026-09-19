# P1-B 修复：推送链 tz-aware/naive 混用崩溃（每日流 R2 · DF-9 下游）

- 日期：2026-09-19
- worktree：`Sparkle-sysrev/wt5`，基线 `f01f4ae8`（未 commit）
- 关联：`多端实测/daily-flow-eval-r2.md` P1-B / DF-9；同款修复模式参考 `d9210935`（memory 写入 naive-UTC 归一化）

## 一、现象（实测证据回放）

推送默认开 ✓、全量评估 ✓（DF-9 前四项全过），但**带 `push_preferences` 行的用户在评估下游确定性崩溃**：08:23 智能推送循环 `Error processing push for user` ×14 = 偏好行用户 14/14 全灭；实测账号 3 天 notifications 恒 0。对照组：无偏好行用户走合成默认路径，通道 2h 内 56 用户有产出——崩溃点精确落在"有无偏好行"分叉上。

## 二、根因诊断（naive-UTC canonical 规范下）

项目规范：naive UTC 是 DB canonical 形态（`app/core/time_utils.py`），`TIMESTAMP WITHOUT TIME ZONE` 列收到 aware 绑定值时 asyncpg 抛 `DataError: can't subtract offset-naive and offset-aware datetimes`。

**核心爆点（任务定位行）**：`backend/app/services/push_service.py` `_check_frequency_cap`
- `utc_start_of_day = local_start_of_day.astimezone(UTC)` 是 **tz-aware**，绑定到 `PushHistory.created_at >= utc_start_of_day`（`created_at` 为 naive `DateTime`，见 `app/models/base.py:104`）→ DataError。
- 该查询只在 `prefs` 非空时才执行（入口 `if not prefs: return False`）——这正是 14/14 偏好行用户全灭、无偏好行用户反而正常的分叉机制。
- 异常被 `process_all_users` 捕获计为 error 并跳过该用户，其余用户不受影响——与生产日志形态一致。

**同链扫描发现并一并修复的同类混用（3 处）**：

| 位置 | 问题 | 后果 |
|---|---|---|
| `push_service.py` `_send_push`：`last_push_time = datetime.now(UTC)`（aware 写入 naive 列） | 修完频控后**首次成功推送就会在 `commit()` 崩**：通知已建但 `last_push_time` 永不落库 → cooldown 失效、outcome 计 error。不与频控同修则 P1-B "修而不断" | 崩溃 + 频控数据损坏 |
| `intervention_event_consumer.py` `_deliver_push`：`prefs.last_push_time = datetime.now(UTC)`（同款 aware 写入） | 行为干预推送投递路径，带偏好行用户 flush 时 DataError | 投递崩溃 |
| `notification_service.py` `_should_push_notification`：`action_time >= datetime.now(UTC) - timedelta(days=7)`（aware 绑定 vs naive `NotificationInteraction.action_time`） | NUDGE-007 连续忽略退避检查**每次静默失效**（异常被 except 吞成 warning）——不崩但功能整体失活 | 防打扰机制失效 |

扫描确认其余推送链文件（`push_delivery_service` / `push_scheduler` / `notification_center_service` / `push_strategies` / `personalization/*` / `notification_analytics_service`）均已使用 naive helper（`datetime.now(UTC).replace(tzinfo=None)` 或 `_utcnow()`），无同类问题。`_is_in_control_surface_dnd` 传入 aware 值但 `is_within_dnd` 内部做双形态归一（`control_surface.py:117-122`），安全。

## 三、修复内容（4 文件，最小定向 diff）

1. `backend/app/services/push_service.py`
   - import `from app.core.time_utils import ensure_naive_utc, utcnow`
   - `_check_frequency_cap`：`utc_start_of_day = ensure_naive_utc(local_start_of_day.astimezone(UTC))`——语义不变（仍是"今日（用户时区）零点"的 UTC 形态），仅归一为 naive
   - `_send_push`：`last_push_time = utcnow()`
2. `backend/app/services/intervention_event_consumer.py`：`last_push_time = utcnow()`，删除内联 `from datetime import datetime`
3. `backend/app/services/notification_service.py`：`>= _utcnow() - timedelta(days=7)`，剪除已无引用的 `UTC` import
4. `backend/tests/unit/test_push_tz_naive_utc.py`（新增，4 用例）

## 四、红绿验证

测试设计要点：单测环境是 SQLite（aiosqlite），其绑定层会静默吞掉 aware 偏移、无法天然复现 asyncpg 行为。故给会话 `execute` 挂"PG 严格绑定守卫"——任何 aware datetime 绑定参数一律抛 asyncpg 真实同签名 `DataError`，把测试环境拉到 PG 的严格度上，忠实复现生产崩溃路径。

- **红**（修复前，`f01f4ae8` 裸基线 + 测试文件）：`2 failed, 2 passed`
  - `test_frequency_cap_binds_naive_utc_start_of_day`：抛 `asyncpg.exceptions.DataError: invalid input for query argument: datetime.datetime(2026, 9, 18, 16, 0, tzinfo=utc)`（= 上海零点的 UTC aware 形态，生产同签名）
  - `test_push_flow_user_with_preference_row_produces_notification`：`process_all_users` 日志出现 `Error processing push for user …`，`errors=1`——生产 14/14 的单用户复刻
- **绿**（修复后）：`4 passed`
  1. 频控日上限查询必须绑定 naive UTC 且语义等于"今日上海零点换算 UTC"
  2. 频控语义回归：只数今日（昨日记录不计，cap 3 触顶 / cap 4 放行）
  3. **14/14 复现场景**：带偏好行用户走完整推送循环（真实 `_check_frequency_cap`），errors=0、产出站内通知、`last_push_time` naive 落库、`push_histories` 有行
  4. 对照组：无偏好行用户路径不受影响

## 五、邻域回归（推送三套件 + 周边全绿）

| 套件 | 结果 |
|---|---|
| push 三套件（`test_push_default_coverage` / `test_push_delivery_service` / `test_push_quiet_hours`） | **10 passed** |
| 邻域 10 套件（behavior_driven_push、d01_notification_fatigue、push_recall_policy_guards、notification_service_preferences、push_content_parsing、push_policy_compiler、daily_sprint_reminder、comeback_nudge_task、phase2_intervention_pipeline、proactive_intervention） | **72 passed** |
| 新增 `test_push_tz_naive_utc` | **4 passed** |

lint：自引入的 import 排序问题已清；三文件在 HEAD 基线上本就存在 ruff I001/black 预存项（已核对基线），按最小 diff 原则未动。

## 六、影响面与遗留

- 修复后带偏好行用户：频控不再崩 → 可正常触发推送 → 通知落库、`last_push_time` 正确回写（cooldown 生效）→ 实测"3 天 0 通知"链路应打通。建议下一轮实测在带偏好行账号上复测 DF-9。
- `notification_service` 退避检查修复使 NUDGE-007 防打扰在 PG 上首次真正生效，推送频次可能略降（符合设计预期）。
- 未做（超出本单范围）：`push_service` 频控 cooldown 比较里对历史 aware 值的 `.replace(tzinfo=UTC)` 兜底（内存比较，安全）；预存 lint 噪音。
