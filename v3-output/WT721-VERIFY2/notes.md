# WT721-VERIFY2 notes — V3-FIX-421（统一设置透明模式）独立复核（双轮审查第二轮）

- Agent: wt721（node-b，复核 wt714 猎缺二轮唯一存活发现；主线仓库只读，本分支 `agent/node-b/wt721/verify2`，base main@1510dbb5，worktree `Sparkle-sysrev/wt721-verify2`）
- 日期: 2026-09-27
- 复核对象: V3-FIX-421（P2）「统一设置『启用透明模式/透明度等级』零消费死设置」（wt714 登记 2026-09-25）
- 裁决: **DOWNGRADED（P2→建议 P3）**——移动本地零行为读者成立；但「零消费死设置」「应用零任何可见变化」「后端 transparency_level 仅存储回显」三项关键定性被推翻：服务端该值有真实消费链，且消费面（我的画像屏）可达、有后端测试钉死
- 推荐修法: **C）文案诚实化**（改副标/标题撤「显示状态与资源消耗概览」承诺，改述真实语义=画像/洞察披露档位；顺修下拉 0 值标签误用 l10n.cancel）

## 1. 复跑证据（不信 wt714 行号，全部独立重验 @1510dbb5）

### 1.1 wt714 成立部分（亲证一致）

- `transparentModeProvider`（settings_provider.dart:625-627，= `transparencyLevelProvider > 0` 派生）全仓（lib+test 含 gen）唯一读者：`unified_settings_screen.dart:515`（仅控制等级下拉显隐）。✅ 与 wt714 一致（wt714 写 :515/:516，现 HEAD 实际 :515/:517，行号漂 2，实质相同）。
- `transparencyLevelProvider` 触达点：定义 settings_provider.dart:620-623 + 派生 :626 + 同屏 watch :517 / 写 :1951、:1988（开关 setLevel(v?2:0) 与下拉 setLevel）。等级 int 值移动本地零行为读者。✅
- 存储键 `settings_transparent_mode`/`settings_transparency_level` 仅 settings_provider.dart:19-20/:929/:953 读写。✅
- chat 透明面确走无耦合的 `TransparencyPreferencesNotifier`（transparency_preferences.dart:131；消费者 chat_screen.dart:1387/3056、chat_bubble.dart:820、transparency_floating_capsule、写面 chat_settings_screen.dart:28-30「显示 AI 面板」）。✅
- 副标承诺词在案：app_zh.arb:135 `showStatusOverview`「显示状态与资源消耗概览」/ app_en.arb:135 "Show status and resource consumption overview"，唯一消费点 unified_settings_screen.dart:1948。承诺-现实不匹配（实际语义是画像披露档位，非聊天状态/资源概览）**仍然成立**。

### 1.2 wt714 被推翻部分（本轮新证，wt714 未扫到）

wt714 后端只查了 `models/user_settings.py:13` 与 `api/v1/user_settings.py`，漏了 `api/v1/profile_transparency.py`。`user_settings.transparency_level` 服务端真实消费链：

1. **三端点 gating**（backend/app/api/v1/profile_transparency.py）：
   - `_get_transparency_level`（:862-867，读 UserSettings.transparency_level，clamp 0-3）；
   - `GET /profile/transparent`（:939，:1051-1058）套 `_apply_legacy_transparency_level`（:907-935）：**level 0 清空 layer_1 偏好/目标、layer_2 persona 标签、layer_3 模式/片段并回填 hidden_item_count；level 1 部分披露（layer_3 清空、tags 截 5）；level≥2 全量**；
   - `GET /profile/context`（:1063，:1082-1092）嵌入 `user_insight_transparency` 套 `_apply_insight_transparency_level`（:870-904）：**level 0 清空 claims/predictions/recent_changes/unknowns；level 1 只露 confidence≥0.75 前 5 条；level≥2 全量**；
   - `GET /profile/insights`（:1144，:1159-1179）同款 gating。
2. **移动端可达消费面**：`/profile/persona` 路由（user_routes.dart:142-155，path `/profile/persona`）挂 UserPersonaScreen；入口两处真实可达——「我的」页 profile_screen.dart:716 `myPersona`「我的画像」tile、memory_panel_screen.dart:1304。该屏 watch `transparentProfileProvider`（user_persona_screen.dart:55 → persona_view_provider.dart:5-8 → user_repository.dart:71 GET `/profile/transparent`），:128-144/:198-240 直接渲染 level-gated 的 layer_1 目标/偏好、layer_2 标签、layer_3 模式/片段——**切等级 → 服务端 gating 变化 → 我的画像屏可见内容变化**（新鲜度：屏内下拉刷新/AppBar 刷新 user_persona_screen.dart:79-83/:149、session_refresh_service.dart:81-82 会话级 invalidate、understanding_overview_provider.dart:334-335 变更后 invalidate）。
3. **变更即有反馈**：PUT user_settings 改 transparency_level 触发服务端 toast 通知（user_settings.py:72-78 → state_notification_service.py:266 field_label「透明度级别」，impact「这将影响你未来的学习体验」）。
4. **后端测试钉死该 gating 为预期行为**：tests/api/test_profile_transparency_api.py:326-335（level=3 全量断言）/:397 等 monkeypatch `_get_transparency_level` 验证 payload 形态。
5. 附带面：`docs/legal/data_export_delete_flow.md:98` 数据导出清单引用 `UserSettings.transparency_level`；`docs/contracts/openapi_snapshot.json` 三处契约在案；`preference_consumption_service.get_user_settings_snapshot`（:339-363）含 transparency_level 但该方法全仓 0 消费者（死方法，另一回事）。
6. ws6 透明档案面（profile_transparent_screen.dart 消费 hidden_item_count/claims，ws6_profile_mirror_provider.dart:56-60/:149-160/:651-661）**无路由注册**（全仓唯一引用是自身与测试），孤儿屏——不影响主裁决（UserPersonaScreen 已足够证伪「零可见变化」），留档。

结论：用户视角复现「开开关、切等级，应用零任何可见变化」**不成立**——开关 0↔2 与下拉 0-3 实际改变我的画像/洞察 payload 的披露量并发 toast。真实问题收缩为：**副标文案承诺错误语义（聊天状态/资源概览），且移动本地 provider 与 TransparencyPreferences 双轨无耦合的架构脏味道仍在**。

## 2. 设计意图考证（git 考古，pre-reset 历史存于 Sparkle-archive-20260915/mirror-backup.git）

主线 1722e6dc（2026-09-15 clean-slate reset）把四个关键面原样带入，须到 archive 镜像考源。判定：**「曾接线后被撤，服务端另接」**，不是「从未接线」也不是「已规划未接线」：

1. **前史（<2026-01）**：bool `transparentModeProvider`（TransparentModeNotifier）真实接线 chat——`if (transparentMode) TransparencyPanel(...)`（b1f122b10^ chat_screen.dart:335-346、:79 watch、:338/:352 gate 布局）。彼时副标「显示状态与资源消耗概览」是**诚实**的。
2. **b1f122b10（2026-01-26「feat: 添加认知棱镜功能和系统更新通知」）**：该 commit 同时①把 chat TransparencyPanel 改为无条件渲染（gate 移除）、②把设置升级为 3 级 `transparencyLevelProvider` + 服务端 `user_settings.transparency_level` 双向同步（新增 alembic p20_user_settings、api/v1/user_settings.py）、③另起移动端透明事件模型（认知棱镜）。语义开始漂移：设置从「聊天面板开关」变成「3 档透明度」但消费未跟上。
3. **a5e708346（2026-03-25「chore: sync full local project state」）**：chat_screen 从 `transparentModeProvider` 整体切换到 `aiSystemPreferences.enabled`（即今天的 TransparencyPreferences 体系）——**移动本地消费自此归零**（只剩设置页自消费显隐）。
4. **6de92c126（2026-04-26「fix(backend): align profile and galaxy acceptance routes」）**：backend profile_transparency.py 引入 `_apply_legacy_transparency_level`/`_apply_insight_transparency_level`——**服务端等级值找到真实归宿：画像/洞察披露档位**，后有测试钉死。
5. clean-slate reset 原样携带以上全部；本轮 421 行所述「死设置」实际是**语义漂移后的文案失真**，不是无功能空壳。

## 3. 三案对比与推荐

| 案 | 内容 | 代价 | 评估 |
|---|---|---|---|
| A 下线设置组 | 撤卡+l10n 键+（彻底则）服务端字段/迁移/openapi/legal 联动 | 高：回退一个**真实存在且被后端测试钉死**的画像披露控制；牵动 alembic 迁移、openapi 快照、`docs/legal/data_export_delete_flow.md:98`、tests/api/test_profile_transparency_api.py；与「明晨 day7 稳定性红线」正面冲突 | **否决**——基于「死设置」误判，撤了会制造真回退 |
| B 接线到真透明面 | 统一设置卡改读写 TransparencyPreferences | 高：两套语义本不同（chat 面板开关 vs 画像披露档位），强接需先裁单一事实源、处理 transparencyPreferencesNotifierProvider（riverpod 生成、AutoDisposeAsync）与 TransparencyLevelNotifier（服务端同步）互斥；golden/chat_settings 面受牵连；day7 前夜引入行为变更风险不可控 | **否决**——语义异构，接了才是制造新谎 |
| **C 文案诚实化（推荐）** | 副标 `showStatusOverview` zh/en 改述真实语义（如 zh「控制你的画像与洞察对外披露的详细程度」）；标题 `enableTransparentMode` 可顺改「画像透明度」；下拉 0 值标签误用 `l10n.cancel`「取消」（1967-1970，pre-reset 原为「关闭」，clean-slate 回归错键）改 `close`「关闭」 | **最低**：2-4 个 arb 键值级改+gen 手改同步（wt710/wt717 判例，弃用产物不重生成，L10N-REGEN-PARITY 互证）；不在 49 冻结键（aurora*19+visual*30 前缀不相交）；unified_settings 相关测试（bgm/no_fake_confirm/router_smoke）不钉这些字符串，golden 面（b04 galaxy/q03）不涉设置屏；零行为变更 | **推荐**——直接兑现诚实性诉求，零回归风险 |

推荐 C 的残留（如实声明）：移动本地 `transparencyLevelProvider` int 值依旧无本地读者（仅作服务端同步载体+显隐派生）——架构双轨脏味道留known debt，不属诚实性缺陷，可在台账行内注记不另立卡。

## 4. 对台账的处置

- 421 行状态格追加：`复核@wt721：DOWNGRADED+推荐C`（含关键反证指针）。
- 建议严重级 P2→P3（承诺-现实断裂仍在但非「零功能」，用户实际有可见效果，只是文案说错语义）。
- wt714 行内「T-待裁决（最小修=撤下该设置卡…）」建议**作废**（以本复核推荐 C 为准）。

## 5. verify

```
python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md
（结果见 commit 前运行记录；要求零 FAIL、V3-FIX 行 8 裸管形态合法）
```
