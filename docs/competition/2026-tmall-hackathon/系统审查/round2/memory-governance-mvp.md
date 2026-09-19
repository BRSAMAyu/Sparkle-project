# memory-governance-mvp：记忆来源标注 + 用户可查看/可纠正（MVP）

- 基线：`d4338948`（worktree wt6，独立进程实测，未 commit）
- 产品愿景对齐：数据飞轮缺"用户侧出口"——用户看不到 AI 记了什么、不能纠正错误记忆。V2.5 已修通记忆全链（写入/召回/注入），本专项补治理面：**来源标注（读侧）+ 纠正/删除/确认（写侧）+ 移动端最小 UI**。

---

## 1. 现状盘点（读码结论）

V2.5 交付的记忆面已具备：

| 既有能力 | 位置 |
| --- | --- |
| `episodic_memories`：source_type/source_id/source_lane/evidence_refs(含 chat_turn id)/tags/correction_count/revoked_at | `backend/app/models/memory.py` |
| `MemoryCorrection` 审计表 | 同上 |
| GET `/api/v1/memory/episodic`（limit + 起止时间，无分页游标；**未返回 tags/写入时间/结构化来源**） | `backend/app/api/v1/memory.py` |
| POST `/api/v1/memory/correct`（通用三型记忆，action=reject/no_longer_applicable/lower_confidence；**无 confirm、无显式 delete**） | 同上 |
| 召回入口 `MemoryService.list_recent_episodic` 已排除 revoked/retracted/deleted/archived | `backend/app/services/memory_service.py` |
| 网关 `/memory/*path` REST 反代（`proxyWithHeaders` 注入 `X-User-ID`/`Authorization`） | `backend/gateway/internal/handler/proxy_routes.go:960-966` |
| 移动端记忆面板（仅 inferred 自动记忆有"撤销"；无 per-item 纠正/删除/确认、无来源/标签展示、无分页） | `mobile/lib/features/memory/` |

**缺口**：分页、tags、结构化来源标注（哪轮对话/哪个模块+写入时间）、单条 episodic 专用治理路由（delete→revoked_at、confirm→confidence 提升）、移动端 per-item 操作。

## 2. 引擎（读侧 + 写侧）

### 2.1 GET `/api/v1/memory/episodic`（扩展，向后兼容）

- 新增 `offset` 分页参数；响应新增 `total / offset / limit / has_more`。
- item 新增：
  - `tags`：标签列表；
  - `source_annotation`：`{ turn_id, label, written_at }` —— `turn_id` 从 `evidence_refs` 中 `type=="chat_turn"` 的引用提取（哪轮对话写入），`label` 按 source_type 映射模块名（对话记录/AI 分析/错题本…，未知回落原始值），`written_at` 为写入时间；
  - `_serialize_episodic`（/correct、/retract、export、新纠正端点共用）同步带上 `tags` + `source_annotation`。

### 2.2 POST `/api/v1/memory/episodic/{memory_id}/correction`（新增）

单条情景记忆的用户治理出口，action 四选一：

| action | 语义 | 服务路径 | 效果 |
| --- | --- | --- | --- |
| `wrong` | 记错了 | `apply_correction(reject)` | 撤回（inferred→revoked_at / 直采→retracted_at，均退出召回）+ correction_count+1 + MemoryCorrection 留痕 |
| `outdated` | 不再是这样了 | `apply_correction(no_longer_applicable)` | 同上 |
| `delete` | 删除 | **新增** `revoke_episodic_memory` | 任意 lane 一律 `revoked_at` 软删 + evidence_refs 打 `user_deleted` + correction_count+1 + MemoryCorrection(action="delete") |
| `confirm` | 这就是对的 | **新增** `confirm_episodic_memory` | confidence/evidence_score 各 +0.05（封顶 1.0）；**确认不是纠错：correction_count 不增**，但写 MemoryCorrection(action="confirm") 留痕（数据飞轮正样本） |

设计决策：
- **delete 一律 revoked_at**（任务口径），与既有 reject 的按 lane 分流并存；`list_recent_episodic` 两条都排除，召回面等效收敛。
- **confirm 写审计不计纠错**：正反馈信号要进 `memory_corrections` 供飞轮消费，但不能让"用户夸了一句"污染纠错计数。
- 复用 `ENABLE_MEMORY_CORRECTION` / `ENABLE_MEMORY_PANEL` 旗标；跨用户 404（不泄露存在性）；proto 不动（纯 REST，符合本专项约束）。
- `CONFIDENCE_CONFIRM_INCREMENT = 0.05` 与既有 `CONFIDENCE_DECREMENT = 0.1` 非对称（确认是弱信号，纠错是强信号）。

## 3. 网关：零代码改动（复用既有纪律）

- `/api/v1/memory/*` 反代组**已存在**（`proxy_routes.go` `registerREST(memory, "/*path")`），新引擎端点自动可达；
- user-id 纪律照旧：REST 反代走 `SetProxyUserContextHeaders`（`X-User-ID` + `Authorization` 透传），引擎 REST 端鉴权以 JWT 为准——gRPC 桥的 `user-id` metadata 纪律（error_book 模式）在本专项无新增面（proto 不改、无新 gRPC 方法）。
- 验证：`CGO_ENABLED=0 go build ./...` OK；`go test ./internal/handler/` 全绿（28.9s，零改动通过）。

## 4. 移动端（最小 UI）

- **设置页入口**：`unified_settings_screen` 的"数据与隐私"卡新增「查看 AI 记忆」（`SettingsDataControlsCard.onOpenMemoryPanel`）→ 直达 `/memory` 面板；原"管理记忆写入规则"（MemorySettingsScreen）不变。
- **记忆面板**（`memory_panel_screen.dart`，V1/V2 两条渲染路径）：
  - 每条 episodic 卡片新增治理 footer：来源行（`来源：对话记录 · 对话 turn_xxxx · 写入 2026-09-18`，来源名按 l10n 本地化，turn_id 截断 8 位）+ tags chips（最多 4 个）+ 动作行【确认无误 / 纠正 / 删除】（inferred 自动记忆保留原"撤销此条"与证据抽屉入口）；
  - 「纠正」弹出 bottom sheet：记错了 / 不再是这样了 + 可选补充说明（≤200 字）；
  - 分页：面板改走 `getEpisodicPage(limit: 20)`，尾部「加载更多（共 N 条）」；
  - 状态：`correctingIds` 防重入；delete/wrong/outdated 后从列表移除，confirm 原位替换（confidence 更新）。
- **API/模型**：`MemoryApiService.getEpisodicPage/correctEpisodicMemory`；`EpisodicMemoryItem` 增 `tags/sourceTurnId/sourceLabel/writtenAt`（可空，向后兼容）；`EpisodicMemoryPage` 分页载荷。
- **l10n**：`memoryGov*` / `memSrc*` / `settDataOpenMemoryPanel` 共 26 键，中英双语。arb 仅追加（零删改既有键）；`app_localizations*.dart` 经 `flutter gen-l10n` 重新生成，diff 中除新增键外含本地工具链（Flutter 3.41.3）对既有内容的机械重排版（多行参数折叠），非语义变更。
- 设计令牌全部走 `mobile/lib/core/design/`（DS.* / SparkleButton / ButtonVariant.ghost）。

## 5. 红绿测试

### 5.1 引擎 pytest（sqlite 内存库，新增 `tests/unit/test_memory_episodic_governance_api.py`，6 条全绿）

1. 分页：5 条数据 limit=2×3 页 → total/has_more/去重 5 id；tags/confidence/source_annotation（turn_id/label/written_at）断言；
2. delete：revoked_at 置位、correction_count=1、MemoryCorrection(action="delete") 落行、列表 total=0、**召回查询（`list_recent_episodic`，即 context_builder 召回入口）为空**；
3. wrong/outdated/confirm：reject 只撤回不动 confidence；confirm +0.05 且 correction_count 不增、留痕 action="confirm"；
4. 跨用户治理 → 404；非法 action → 422；
5. 无凭证 → 401/403；
6. `ENABLE_MEMORY_CORRECTION=False` → 403。

回归：`test_memory_api.py` / `test_memory_service_reads.py` / `test_memory_export_api.py` 全绿（12 passed）。

### 5.2 网关

`CGO_ENABLED=0 go build ./...` + `go test ./internal/handler/ -count=1` 全绿（无代码改动，验证 `/memory` 反代对新增端点的通配覆盖）。

### 5.3 移动端

- 新增 `test/widget/memory_governance_panel_test.dart` 4 条全绿：来源标注/tags/三动作渲染、delete 移除卡片且 API 调用入参正确、confirm 保留卡片、纠正 sheet（记错了/不再是这样了 + reason 提交）；
- 既有 9 个记忆相关测试套件补齐 `MemoryApiService` 新成员 mock（`implements` 接口约束）后，结果与主仓基线**逐条一致**（worktree +59-10 vs 主仓 +59-10，失败集完全相同：均为基线既有的 SparkleThemeExtension 未注册问题，与本专项无关）；
- `flutter analyze`：按文件比对 worktree vs 主仓基线，**本次改动文件零新增 lint**（全仓 +4 条均为 third_party_plugins vendored fork 噪声，非本专项文件）。

## 6. 全链实测（:8009 引擎 + :8090 网关，收工已杀净）

环境：worktree 代码 + 主仓 Postgres/Redis（进程独立、端口 8009/8090；`.env` 软链只读引用主仓，未改主仓任何文件/进程）。

1. **注册/登录**：`POST :8090/api/v1/auth/register`（accepted_tos/privacy）→ `POST /auth/login` → token；
2. **写入**：测试用户写入 3 条 episodic（source_type=chat，evidence_refs 含 `chat_turn` 引用，tags=[英语,六级]，confidence=0.55）；
3. **列表可见来源**：`GET :8090/api/v1/memory/episodic?limit=2&offset=0` → `total=3, has_more=true`；item 含 `tags=['英语','六级']`、`confidence=0.55`、`source_annotation={turn_id: "turn_2abc12345", label: "对话记录", written_at: ...}`；
4. **纠正（删除）**：`POST /memory/episodic/{id}/correction {"action":"delete"}` → `status=corrected, correction_count=1, revoked_at 置位`；再查列表 `total=2` 且不含该 id；DB 中 `MemoryCorrection(action='delete')` 落行；
5. **确认**：对另一条 `{"action":"confirm"}` → `status=confirmed, confidence 0.55→0.60, correction_count=0`；
6. **召回排除**：`MemoryService.list_recent_episodic`（context_builder 召回入口）仅返回 2 条，被删条目排除；
7. **鉴权**：无 token / 假 token 经网关访问 → 401/401。

清理：测试用户及全部关联行（按 FK 元数据逐表删除）清零（episodic leftover=0，user leftover=0）；:8009/:8090 进程杀净；/tmp 二进制已删除。

本地软链说明（均不入库，收工已移除；后续会话复跑测试/引擎时按需重建）：

```bash
ln -s /Users/brsama/code/GitHub/Sparkle-project/.env                wt6/.env
ln -s /Users/brsama/code/GitHub/Sparkle-project/backend/.env        wt6/backend/.env
ln -s /Users/brsama/code/GitHub/Sparkle-project/backend/app/gen     wt6/backend/app/gen
ln -s /Users/brsama/code/GitHub/Sparkle-project/backend/gateway/gen wt6/backend/gateway/gen
ln -s /Users/brsama/code/GitHub/Sparkle-project/mobile/lib/gen      wt6/mobile/lib/gen
```

## 7. 已知边界 / 后续

- `wrong`/`outdated` 复用既有 reject 语义（撤回），不做内容级"改写"；改写涉及 embedding 重算，留待 V3。
- confirm 的 confidence 增益为固定 +0.05，未接贝叶斯证据融合（`services/evidence/`），后续可作为飞轮正样本权重入口。
- 来源标注的 `label` 在引擎侧返回中文兜底（对话记录等），移动端已按 locale 本地化渲染；引擎侧 i18n（Accept-Language）留后续。
- 网关 `/memory` 反代为通配 REST；若后续要求 gRPC 桥（error_book 模式）需改 proto，本专项约束 proto 不动。
- 移动端 10 条既有失败为主仓同款基线问题（SparkleThemeExtension 未在测试主题注册），与本专项无关，建议另开专项修复。

## 8. 变更清单

引擎：
- `backend/app/api/v1/memory.py`（episodic 分页 + tags + source_annotation；新纠正端点；`EPISODIC_SOURCE_LABELS`）
- `backend/app/services/memory_service.py`（`list_recent_episodic(offset)`、`count_episodic`、`revoke_episodic_memory`、`confirm_episodic_memory`、`CONFIDENCE_CONFIRM_INCREMENT`）
- `backend/tests/unit/test_memory_episodic_governance_api.py`（新增）

网关：无改动（复用既有反代 + 鉴权纪律）。

移动端：
- `lib/core/models/memory_models.dart`、`lib/core/services/memory_api_service.dart`
- `lib/features/memory/presentation/screens/memory_panel_screen.dart`
- `lib/features/settings/presentation/widgets/settings_behavior_explanation.dart`、`lib/features/user/presentation/screens/unified_settings_screen.dart`
- `lib/l10n/app_zh.arb`、`lib/l10n/app_en.arb` + 生成的 `app_localizations*.dart`
- `test/widget/memory_governance_panel_test.dart`（新增）；9 个既有测试 mock 补齐新接口成员
