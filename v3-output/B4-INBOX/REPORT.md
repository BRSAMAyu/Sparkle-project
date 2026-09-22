# B4-INBOX 收工报告 — Aurora 确认队列 → 收件箱引擎数据桥

- Worker：B4-INBOX（A 线批 4 首卡）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt160`（基线 `7d8a828d`，含 B3-CHAT `b7956f1c`，已验证 ancestor）
- 交付物：本报告 + `changes.patch`（1605 行，已在 HEAD 干净克隆验证 `git apply --check` 通过）
- 红线遵守：零 commit / 零 push / 零凭据 / 主仓只读 / 未动活栈

---

## ① 盘点结论：Aurora 确认的数据现状

Aurora「确认」在引擎侧有**两层**，持久化程度完全不同：

1. **带状态（band status）= 纯派生，无持久化事件**。`/aurora/control-surface` 的
   `overall_status`（`needs_confirm` / `risk_found` / `calibration_available`）由
   `AuroraControlSurfaceService._resolve_band_status` 每次请求从 Redis 能量存储 + 四
   facet 状态**实时计算**，不存在离散的"Aurora 确认事件表"。B3-CHAT 的徽标轮询就是这
   一层。
2. **校准卡确认队列 = 唯一持久化的确认面**。用户偏好存储
   `UserPreferencesCenter.inferred.self_model.known_assumptions` 中
   `status=candidate` 或 `needs_confirmation=true` 的 claim，经
   `AuroraCalibrationCardService.list_cards`（`GET /aurora/calibration-cards`，最多
   MAX_VISIBLE_CARDS=3 张）成为确认队列；用户响应走
   `POST /aurora/calibration-cards/{card_id}/respond`（confirm/incorrect/mute →
   `InferenceWritePipeline.respond_to_claim` + `MemoryCorrection` 落库）。**响应值
   枚举与 mobile 既有 `AuroraCalibrationResponse.apiValue` 完全对齐**。

notification-center 现状：`get_unified_notifications` 只支持
system / intervention / push 三源；`ChatInboxEntryIcon` 徽标是快照 actionable 布尔点，
无计数、无数据桥。

## ② 桥接方案论证（走卡上"已有持久化"分支）

判定：确认队列有持久化（偏好存储里的 claim），故按卡面第一分支执行——**notification-center
新增 `aurora_confirm` 派生类型（列表项+操作回调=既有确认 API）+ 徽标计数端点**，不新增
任何写入路径、不建新表（最小面）。

### 引擎（backend/app）

| 文件 | 改动 |
| --- | --- |
| `services/aurora_confirm_bridge_service.py`（新） | `AuroraConfirmBridgeService`：`pending_cards`（复用 `list_cards` 原口径，与校准卡面板逐字节一致）→ `UnifiedNotificationResponse`（`source_type='aurora_confirm'`，id=claim id，metadata 携带卡面）；`pending_count`（**无写**轻量读：跳过 `promote_due_trials`——它只动 `trial` 态 claim，而 trial 本就被 `_is_visible_assumption` 排除，故计数与列表口径一致；计数**不封顶**，徽标报真实积压，卡面仍受 MAX_VISIBLE_CARDS=3 约束——诚实差异，已注明）；`count_visible_from_inferred` 纯函数可单测 |
| `services/notification_center_service.py` | `get_unified_notifications` 合并 aurora_confirm 源（`unread_only` 下保留——卡未响应即未读，语义自洽）；桥接异常时降级为空列表不拖垮列表；`mark_notification_read` / `delete_notification` 对 aurora_confirm 为文档化 no-op（派生项无行，响应后自动离队） |
| `api/v1/notification_center.py` | source_type / notification_type 校验放宽（`_SOURCE_TYPES` / `_NOTIFICATION_TYPES` 常量）；新增 `POST /notifications/{id}/aurora-confirm-action`（`AuroraConfirmActionRequest`：confirm/incorrect/mute + reason/corrected_assumption），**委托既有** `AuroraCalibrationCardService.respond`，异常映射 400/404 |
| `api/v1/aurora.py` | 新增 `GET /aurora/calibration-cards/pending-count`（徽标计数端点；声明在同形参数化路由之前，符合 R2-EI-13 约定） |
| `services/aurora_control_surface_service.py` | 快照 payload 增加只读字段 `pending_confirm_count`（无写轻量读，异常安全默认 0）——复用入口件已 30s 轮询的通道，**mobile 零新增网络路径** |
| `schemas/unified_notification.py` | 新增 `AuroraConfirmActionRequest` |

网关：`/notification-center/*path` 与 `/aurora/*path` 均为 catch-all 代理
（proxy_routes.go:825/1147），**零网关改动**。

### Mobile

- `unified_notification_model.dart`：`_normalizeSourceType` 透传 aurora_confirm；
  `isAuroraConfirm` / `canRespondAuroraConfirm` / `auroraConfidenceLabel` /
  `auroraEvidenceSummary` / `auroraNeedsConfirmation` / icon '✨'。
- `notification_center_repository.dart`：`sendAuroraConfirmAction` —— **直发既有
  `ApiEndpoints.auroraCalibrationCardRespond(cardId)`**（与 `AuroraCalibrationRepository`
  同端点同契约），demo 模式复用 `respondToDemoAuroraCalibrationCard`。
- `notification_center_provider.dart`：`respondToAuroraCard`（成功后本地移除该项——
  引擎侧已离队，而非翻已读）+ `SourceTypeFilter.auroraConfirm`。
- `unified_notification_card.dart`：aurora 分支渲染（确认=primary / 不准确=outline /
  暂不确认=ghost + 置信度标签 + 证据摘要≤2 行，照既有 Wrap+SparkleButton 模板与 SPEC
  令牌，零硬编码色值/字号）+ 来源 badge。
- `notification_center_screen.dart`：三回调接线 + 筛选枚举新 case + 双语 toast。
- `aurora_status_provider.dart`：快照解析 `pending_confirm_count`（默认 0，向后兼容）。
- `chat_inline_signals.dart`：**B3-CHAT 收容语义原样保留**（actionable → 徽标可见；
  count==0 时仍是无数字的点）；count>0 时 Badge 显示真实计数（99+ 封顶），数据源=
  控制面新字段。

### l10n

zh/en 各 +6 键（source badge、确认/不准确/暂不、两条 toast）；生成文件为**基线 legacy
格式下的等价键注入**（见④），`L10N-REGEN-PARITY` guard PASS（11106 键三方对齐），
l10n 目录 diff = +86 行纯新增、零格式 churn。

## ③ 冲突面声明

- **wt144（events，aurora consumer）**：本卡**未触碰**任何 aurora 消费/写入面——
  `write_pipeline`、`respond_to_claim`、`promote_due_trials`、信号管线零 hunk。唯一的
  aurora 域接触点是**新增只读调用**（bridge 调 `list_cards`/读偏好）与控制面 payload
  的一个新字段。若 wt144 改 `aurora_control_surface_service.py` 的 `build_snapshot`
  返回体合并时，保留 `pending_confirm_count` 键即可（其余 hunk 无交叠基础）。
- **wt158 / wt159**：未触碰其域（本卡改动集中在 notification-center 服务/API、aurora
  状态读面、mobile 通知/chat 收容件；三方若同文件相交，预期在
  `notification_center_service.py` 的 `get_unified_notifications` 尾部合并块与
  `unified_notification_model.dart` 的 getter 追加区，均为纯追加，冲突易解）。
- l10n 三生成文件：本卡采用"在既有锚点后等价注入"而非本机 regen（原因见④），若其他卡
  同时 regen 这些文件，按键合并即可，键集已过 parity guard。

## ④ 诚实申报

1. **l10n 生成文件为等价键注入，不是本机 regen 产物**。本机 Flutter SDK 的
   `flutter gen-l10n` 恒定输出 dart_style tall 格式（删 `.dart_tool`、清
   package_config、`--no-pub` 均无法复现基线 legacy 格式，+457/-129 全文件 churn）。
   处置：以 arb 为源（真实 regen 输入），把 6 个简单 getter（无占位符，格式确定）按
   arb 顺序注入三个生成文件的既有锚点之后，逐格式复刻基线模板；`check_l10n_regen_parity.py`
   PASS。字面格式 guard 属 CI 建议（L10N-REGEN 注明未强制本地），接受方如有 canonical
   SDK，可直接 `flutter gen-l10n` 覆盖验证。
2. **测试中途误执行过一次 `git stash`（违反工作树纪律），当即 `git stash pop` 完整恢复**
   ——恢复后逐文件核对：17 modified + 3 new 与改动清单完全一致，零丢失。此后未再使用
   stash/reset/clean；基线对照一律改用 `/tmp` 克隆（BG 守卫、patch 验证均用克隆法）。
3. **worktree 缺生成产物**：`backend/app/gen`、`mobile/lib/gen`（均不入库）从主仓只读
   复制进 worktree 以通过编译/测试；其中 3 个符号链接指回主仓曾致 K/Z 守卫崩溃，已
   `cp -L` 替换为真实文件并复跑通过。两份 gen 留在 worktree 内随其生命周期回收。
4. **chat 域首轮 mobile 回归出现过 1 例 flaky**（21 例中 1 败，WebSocket/timer 类
   chat_history 域），同一命令立即复跑 23/23 全绿；未复现，按 flaky 记录。
5. **治理守卫终态**：UI-TOKENS / K / Z / L10N-PARITY 等全绿；`BG`（buf Go/Dart 生成
   产物未入库）在 `/tmp` HEAD 基线克隆上同样 FAIL——**基线存量问题**，与本卡无关。
6. `chat_inline_signals.dart` 遗留 1 条 pre-existing `unnecessary_import` info（B3-CHAT
   自带，非本卡引入，未动以免污染收容件 diff）；触碰文件 **analyze 0 error**。
7. 徽标计数（不封顶）与通知中心列表项数（封顶 3）存在有意差异：徽标=真实积压，
   列表=引擎展示窗口（MAX_VISIBLE_CARDS），已在端点 docstring 与桥接服务注释注明。

## ⑤ 收工核查

- [x] 新增测试全绿：引擎 `tests/unit/test_aurora_confirm_bridge.py` 17/17（桥接映射、
      纯计数逻辑、无写断言、合并/降级/no-op、API 委托与校验、pending-count 端点）；
      mobile `test/widget/aurora_confirm_notification_test.dart` 7/7（模型解析、卡渲染
      三动作、provider 委托+本地移除、徽标计数/点回退/不可见）。
- [x] 定向对比：notification-center 域 25 passed（d01/r2/error-replan/spaced-rep）；
      Aurora 域 40 passed（control_surface/t34 状态带/校准卡 API）。
- [x] mobile 触碰文件 analyze 0 error；`flutter test --concurrency=1` 串行。
- [x] 收工清理：`mobile/.dart_tool`、`build/`、pytest tmp、/tmp 探针（b4inbox-*：基线
      克隆、patch 克隆、日志）已删；未起模拟器/无遗留进程；HEAVY 合规（无模拟器/无
      Gradle，仅串行单测）。
- [x] 未 commit / 未 push；patch 头 `--- /dev/null`（新文件）；零凭据入库。

### 改动清单（changes.patch 内）

新增 3：`backend/app/services/aurora_confirm_bridge_service.py`、
`backend/tests/unit/test_aurora_confirm_bridge.py`、
`mobile/test/widget/aurora_confirm_notification_test.dart`。
修改 17：引擎 5（notification_center API/service、aurora API、控制面 service、schema）；
mobile 8（model/repository/provider/card/screen/aurora_status_provider/chat_inline_signals
+ l10n 2 arb）；l10n 生成 4（3 dart + 计入 arb）。
