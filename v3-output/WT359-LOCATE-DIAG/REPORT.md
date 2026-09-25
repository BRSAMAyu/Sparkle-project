# WT359 · group_chat 搜索定位 Case B 诊断（装配 vs 产品缺陷裁定+修复）— REPORT

- **Worker**: wt359
- **基线**: main `557cf78c`（worktree `../Sparkle-sysrev/wt359-locate-diag`，branch `wt359-locate-diag`）
- **卡面**: wt339 遗留裁定卡——`group_chat_index_shift_reparent_test.dart` Case B「搜索命中定位（瞬态键 ensureVisible 全链路）」CI 与本地同败，主会话以 `skip: true`（commit `020abea5`）保主干；本卡逐帧探针裁定并修复，交付后 Case B 真实绿。

## 一、裁定：c) 两者皆有——主因产品真缺陷，次因测试装配缺陷

### 1. 产品真缺陷（远屏定位静默失达的根因）

`_revealMessage` 的 jumpTo 逼近估算与列表展示**不在同一坐标系**：

| 坐标系 | 顺序 | 消费方 |
|---|---|---|
| `groupChatProvider` 原始态 | **旧→新**（仓库分页契约：`loadOlderMessages` 以列表 `.last` 为 `before_id` 锚点，`.last` 即最新；`loadMessages` 原样入库不排序） | 恰恰被 `_revealMessage` 误用 |
| `_mergeMessages`（去重+按 createdAt 降序） | **新→旧**（index 0=最新=offset 0） | reversed ListView / itemBuilder / `_findChildIndexForKey` / 瞬态键挂载 |

逐帧探针实测（探针版 run2，`/tmp/wt359_run2.log` 证据链）：点命中 `msg-30`（页内第 30 新）后，`_revealMessage` 用原始序算得 `index=19`（镜像位），`jumpTo(1874.9)` 落在错误邻域——瞬态 GlobalKey 只挂 `msg-30` 的 itemBuilder 项（UI index 30，未构建），`locateKey.currentContext` **12 次重试全为 false**，且每轮重复跳同一 offset（幂等重试，无纠偏），链路静默耗尽后 `_clearLocateTarget` 放弃。`pixels=1874.9` 全程不动即是「空转」实锤。近屏命中（常见场景）context 直接命中 ensureVisible 正常，掩盖了远屏缺陷——真机同败。

### 2. 测试装配缺陷（主会话 60 帧不收敛表象的另一面）

原 `_pumpUntilVisible`「先查后泵」：tap 后**首查未泵帧**即命中仍在退场动画中的搜索 sheet 结果 ListTile（与列表气泡同文 `定位甲正文`），零帧假绿返回、逼近链被饿死（探针版 run1：`frame 0 visible=1 searchIcons=2 sheetOpen=true` 后链路只推进 1 拍）；后续 `Icons.search` 双匹配异常即 sheet 未关的直接后果。主会话曾见的「60 帧仍不进场」为泵帧语义变体下的真实不收敛（产品缺陷面）+ 该装配洞的组合表象。

## 二、修复（`mobile/lib/features/chat/presentation/screens/group_chat_screen.dart`，仅 `_revealMessage` 估算段）

1. **坐标系对齐**：index 改在 `_mergeMessages(原始态, agentState)`（即 UI 展示序）上 `indexWhere`；`itemCount` 同步用 merged 长度。估算锚定正确条目。
2. **收敛性修复（非延长轮询）**：首跳 `attempt=0` 仍纯估算；重试（≥1）围绕估计值按 `3/4 视口`步长正负交替外扩（`±ceil(n/2)×0.75v`，相邻两跳窗口重叠无漏扫），保证有界 12 次内目标必进构建窗；context 物化后仍由 `ensureVisible`（250ms/easeOutCubic/alignment 0.22 逐位不变）精确对齐。**wt339 瞬态键语义（一次性挂载/接管守卫/收尾即摘/键替换路径）零改动**；未碰 chat_screen.dart。
3. 红测先行：Case B 解除 skip 即红（run2 复现原败），修复后转绿。

## 三、测试装配修复（`mobile/test/widget/group_chat_index_shift_reparent_test.dart`）

- `_pumpUntilLocateLanded`（替换原帮手）：每轮**先泵后查**（一帧=endOfFrame 逼近链一次重试预算）；**sheet 未完全关闭（搜索框键仍在）不认命中**（排除同文假阳性）。24 帧预算=有界收敛（sheet 退场 ~3 帧+13 次重试+ensureVisible ~5 帧后仍余量），非掩败等待——链路 12 次放弃后多泵不会进场。
- 达靶判据升级 `_expectOnScreen`：不只 `findsOneWidget`（cacheExtent 内离屏条目也能命中 finder），并断言文本 RenderBox 实际在屏内（`getRect` 对 [0, screenH]）。
- Case B skip 移除，恢复真实断言；原 skip 理由注释替换为本卡裁定结论。

## 四、执行证据（单文件 `--concurrency=1`，全程 swap 门遵从：911M–1236M 窗口，小批单文件跑）

| 运行 | 结果 |
|---|---|
| run1（探针版，原「先查后泵」装配） | 假绿→:155 `Icons.search` 双匹配异常（暴露装配洞） |
| run2（探针版，先泵+sheet 感知） | 复现主会话原败：12 拍全 `ctx=false`、pixels 恒 1874.9、`index=19` 实锤产品缺陷 |
| run4（修复+探针） | **exit 0**：msg-30 两拍收敛（attempt1 `ctx=true`）、msg-40 两拍收敛 |
| 终检（去探针） | `group_chat_index_shift_reparent_test.dart` **2/2 passed**（Case A+Case B 真实断言）；`group_chat_search_locate_test.dart` **3/3 passed**（wt339 定位+高亮直接回归钉不破） |

- **守卫**：`bash scripts/run_all_rule_guards.sh` → **84 条全过，exit 0**（首跑 AQ/BG 失败系 gen 三件套缺 backend app/gateway 两件，`cp -RL` 补齐后全绿）。
- **analyze 门**：`check_flutter_analyze_gate.py` → **E0/W16/I592，gate passed**（±5 平台漂移容差内；两改动文件单独 `dart analyze` 0 issue，自纠 3 处 require_trailing_commas）。
- **gen 三件套**：mobile lib/gen + backend/app/gen + backend/gateway/gen 均自主仓 `cp -RL`；`flutter pub get` 曾重排 l10n 三生成文件（wt336/wt339 同款坑），已 `git checkout --` 还原，未入提交。

## 五、合并核对表

| 文件 | 内容 |
|---|---|
| `mobile/lib/features/chat/presentation/screens/group_chat_screen.dart` | `_revealMessage` 估算段：merged 坐标系 index + 交替外扩扫掠（瞬态键/守卫/ensureVisible 参数零改动） |
| `mobile/test/widget/group_chat_index_shift_reparent_test.dart` | Case B 解除 skip 恢复真实断言；`_pumpUntilLocateLanded` 先泵+sheet 感知；`_expectOnScreen` 真实达靶 |

**未碰**：chat_screen.dart（1:1 战区）、守卫/analyze 基线脚本、backend、l10n、群聊其他行为面。

## 六、定级与收工

- **定级：READY_FOR_REVIEW** —— 裁定有逐帧证据链、修复红转绿、Case B 真实绿（非 skip）、守卫 84 exit 0、analyze 门通过零自增。
- [x] 守卫 84 exit 0
- [x] analyze 门通过（改动文件 0 issue）
- [x] Case B 真实绿 + Case A / search_locate 回归全绿
- [x] REPORT.md + changes.patch commit 进分支
