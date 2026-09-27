# WT708 · B-04 视觉基线全量重采（27 张单锚化）· 2026-09-25

- 分支：`agent/node-b/wt708/rebase`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt708-rebase`，自 main `b8c94477` 检出）
- 兑现：V3-FIX-376 行尾注「macos 批 home 面仍锚 87b5f432 待下轮全量重采」；连带消解 V3-FIX-395（verify 单 sha8 全套运行混锚 missing-file 挂）。
- 采集锚：worktree HEAD `b8c94477`（main 自任务书下发时的 cb4e0719 又前移，以实际检出 HEAD 为准——capture 时产品代码即 b8c94477 树）。

## 1. 采集与复验（真实渲染，零手改像素）

- 采集：`B04_VISUAL_CAPTURE=true flutter test --update-goldens test/goldens/b04_visual_baseline/ --dart-define=B04_BUILD_SHA8=b8c94477` → 27/27 采集绿（同目录 6 例比较器单测合计 +33 全过）。sha8 段只认 `--dart-define`（`String.fromEnvironment`），沿 wt693 口径。
- 复验（verify 模式，无 `--update-goldens`）：`B04_VISUAL_CAPTURE=true flutter test test/goldens/b04_visual_baseline/ --dart-define=B04_BUILD_SHA8=b8c94477` → **33/33 全绿单锚**。
  - 对照 FIX-395 缺陷态（wt702 实测）：87b5f432 全套跑 25 过 2 挂（android home missing + macos1280 home 15.24% 真差）；e0777bd5 单跑 home 才过。本批 27 张全锚 b8c94477 后，任一面缺失挂消失，单 sha8 全套直过——**FIX-395 的 missing-file 挂已消解**。
- 旧 27 张（26×87b5f432 + android home×e0777bd5）`git rm` 同位替代，无混锚残留；重采后 `find v3-output/B-04/screenshots -name '*.png' | wc -l` = 27。

## 2. 新旧锚对照表（27 张全覆盖）

旧态 = 87b5f432 批 26 张 + android home 单面 e0777bd5（wt696 混锚态）；新态 = 27 张全 b8c94477。

| 批次 | surface/state | 旧锚 | 旧 sha256(16) | 新锚 | 新 sha256(16) | 字节级 |
|---|---|---|---|---|---|---|
| android__1080x2400@3.0 | chat/history_citations | 87b5f432 | 13d9374309507cfd | b8c94477 | a3b5d63bc9c266fb | **差**（已知时间戳噪声，见 §3） |
| android__1080x2400@3.0 | galaxy/tree_expanded | 87b5f432 | e749e3352fd5a6cc | b8c94477 | e749e3352fd5a6cc | 同 |
| android__1080x2400@3.0 | goal/library_main | 87b5f432 | 07b1f010fa64aa6e | b8c94477 | 07b1f010fa64aa6e | 同 |
| android__1080x2400@3.0 | home/main | e0777bd5 | 60cc9310b14f1c92 | b8c94477 | 60cc9310b14f1c92 | 同 |
| android__1080x2400@3.0 | memory/panel_main | 87b5f432 | 217b9d414478b449 | b8c94477 | 217b9d414478b449 | 同 |
| android__1080x2400@3.0 | onboarding/persona_start | 87b5f432 | dbaa42f84b6f75b0 | b8c94477 | dbaa42f84b6f75b0 | 同 |
| android__1080x2400@3.0 | profile/main | 87b5f432 | 8e24a7f4989ca612 | b8c94477 | 8e24a7f4989ca612 | 同 |
| android__1080x2400@3.0 | settings/main | 87b5f432 | ddbf87dc9d40e8a5 | b8c94477 | ddbf87dc9d40e8a5 | 同 |
| android__1080x2400@3.0 | task/library_main | 87b5f432 | 237c9285a71a869e | b8c94477 | 237c9285a71a869e | 同 |
| macos__1280x800@2.0 | chat/history_citations | 87b5f432 | 2019ac40dbfdca94 | b8c94477 | 2019ac40dbfdca94 | 同 |
| macos__1280x800@2.0 | galaxy/tree_expanded | 87b5f432 | 62cde21cd9f73c0a | b8c94477 | 62cde21cd9f73c0a | 同 |
| macos__1280x800@2.0 | goal/library_main | 87b5f432 | ff63befdc895a55c | b8c94477 | ff63befdc895a55c | 同 |
| macos__1280x800@2.0 | home/main | 87b5f432 | fbf2edaba57fc32c | b8c94477 | 8f26c6104ef9fb1d | **差**（FIX-376 home 重做内容演进，见 §4） |
| macos__1280x800@2.0 | memory/panel_main | 87b5f432 | 83e1079c6ef5695d | b8c94477 | 83e1079c6ef5695d | 同 |
| macos__1280x800@2.0 | onboarding/persona_start | 87b5f432 | 70be9f07299f871d | b8c94477 | 70be9f07299f871d | 同 |
| macos__1280x800@2.0 | profile/main | 87b5f432 | b67fae63721d31a4 | b8c94477 | b67fae63721d31a4 | 同 |
| macos__1280x800@2.0 | settings/main | 87b5f432 | 52498abf6b1af36a | b8c94477 | 52498abf6b1af36a | 同 |
| macos__1280x800@2.0 | task/library_main | 87b5f432 | 17c39a0f8449f02c | b8c94477 | 17c39a0f8449f02c | 同 |
| macos__800x600@2.0 | chat/history_citations | 87b5f432 | 9215f72c31dc3bcc | b8c94477 | 9215f72c31dc3bcc | 同 |
| macos__800x600@2.0 | galaxy/tree_expanded | 87b5f432 | f6e4d566d5db1b21 | b8c94477 | f6e4d566d5db1b21 | 同 |
| macos__800x600@2.0 | goal/library_main | 87b5f432 | 8215c8152c8fffe5 | b8c94477 | 8215c8152c8fffe5 | 同 |
| macos__800x600@2.0 | home/main | 87b5f432 | 9f6614d6c2be793a | b8c94477 | 9f6614d6c2be793a | 同（回执卡在 800x600 视口折叠线下，可见面零变化，与 wt702 verify 该面过一致） |
| macos__800x600@2.0 | memory/panel_main | 87b5f432 | a1bae1121d676216 | b8c94477 | a1bae1121d676216 | 同 |
| macos__800x600@2.0 | onboarding/persona_start | 87b5f432 | 4e78c7b947ffd62a | b8c94477 | 4e78c7b947ffd62a | 同 |
| macos__800x600@2.0 | profile/main | 87b5f432 | 8171cf2f7c84f1dc | b8c94477 | 8171cf2f7c84f1dc | 同 |
| macos__800x600@2.0 | settings/main | 87b5f432 | bb7045d155da3719 | b8c94477 | bb7045d155da3719 | 同 |
| macos__800x600@2.0 | task/library_main | 87b5f432 | 45cd830c19e81094 | b8c94477 | 45cd830c19e81094 | 同 |

小结：**25/27 逐字节相同**；仅 2 张差，均可完全归因（§3/§4）。

## 3. chat android 差异归因（已知噪声类）

旧批（wt693 记录）时间标签 17:35 → 本批 18:55（亲验读图确认 app bar 下首消息时间标签「18:55」，其余引用条/反馈操作/模式条零变化）。demo 消息相对时间戳噪声类，wt667 首轮已登记，远低于 0.5% 容差。

## 4. macos 1280x800 home 差异归因（本卡主目标：15.24% 差异归零）

- wt702 实测：87b5f432 旧基线 vs 当时代码 = 真差 **15.24%（624,197 px）**，归因「基线早于 V3-FIX-376 home 重做」。
- 本批亲验读图对照（macos 1280x800 批）：
  - 旧 `home__main__demo_data__macos__1280x800@2.0__87b5f432.png`：主叙事句「早上好，今天先从一小步开始…」正下方裸露「ⓘ 加载失败 轻触重■」（CompactErrorCard 错误态）。
  - 新 `…__b8c94477.png`：错误行消失；同位为 UnderstandingSnapshotCard 空态承载（「…对你的理解」兜底叙事 +「纠正我的理解」按钮 + 右上置信 pill）。
- 结论：旧基线与现行为间 15.24% 像素差**确系 FIX-376 内容演进**（错误态→空态回执卡），非渲染管线问题——同一渲染管线在 25/27 张上逐字节复现旧输出即为管线稳定性反证。新基线即当前真实渲染，verify 模式单锚 33/33 绿（差异在新基线下为 0）。
- android home 本批重采输出与 e0777bd5 批逐字节相同（60cc9310…），wt696 单面重采结论（错误行消失、回执卡空态）在本批管线原样复现；macos 800x600 home 逐字节相同（回执卡位于该视口折叠线下，可见面零变化，与 wt702 verify 该面通过一致）。

## 5. manifest 重建 ×3 → verify OK → coverage 9/9

```
visual_baseline.py manifest v3-output/B-04/screenshots/<批> --build-sha b8c94477 --platform <plat> --viewport <vp> -o v3-output/B-04/manifests/manifest_<批>.json
  → manifest 写入 …：9 条目 ×3
visual_baseline.py verify <批目录> --manifest … → verify OK ×3（missing/extra/hash_mismatch 全空）
visual_baseline.py coverage <批目录> → coverage：9/9 canonical states 已采集 ×3
```

manifest 与 PNG 一一对应：每批 9 条目 sha8 全 `b8c94477`，`build_sha=b8c94477`。

## 6. 布局探针 layout_probe_b04.json 随采刷新（保序换锚）

- 27 条全锚 b8c94477（screen 文件名第 6 段），**恢复测试执行自然序**（android 9 → macos800 9 → macos1280 9；wt696 单面重采把 android home 条并到文件尾的暂态不再存在）。
- 硬信号：**pump_exception=0、截断候选=0**（27/27）。按名逐一对照（26 条同名面）：logical_size 全同；text_widget_count 在 chat/galaxy/profile（×android）与 home/chat/galaxy/profile（×macos 两批）面 −5、home macos1280 面 86→81——与 87b5f432→b8c94477 窗口内 main 合入的 3 个 mobile/lib 修复（V3-FIX-384 aurora_calibration_strip 动效收口 / V3-FIX-385 taskReminderConfigProvider 收敛 / V3-FIX-360 ErrorMessages 收口）同期的 widget 树微差；对应 PNG 除 §3/§4 两张外逐字节相同，即像素面零回归，计数差属屏外/语义层 widget 增减。overflow_bounds_widgets 仅 macos 批口径失真面（ENV-2）随 −5 同幅 −33/−43，趋势参考口径不变。

## 7. 全量回归

- `flutter test test/goldens/`：**84 过 / 15 skip / 0 红**（84=wt702 收口后 84 口径沿用：78 基线 + 6 比较器带界单测；15 skip 为 dart-define 门控面，未动断言）。
- `flutter analyze`：No issues found!。
- 产品代码零改动（本卡无代码 diff）；`mobile/lib/l10n/` 3 个生成文件因本机 l10n 工具排序差异被测试运行重写，已 `git checkout` 还原不入库（内容等价、仅条目顺序差）。

## 8. 台账动作

- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`：FIX-376 行尾注「macos 批 home 面仍锚 87b5f432 待下轮全量重采」→ 已兑现注记；FIX-395 → FIXED@<重采 commit>（27 张单锚化，missing-file 挂消解）。
- `v3-output/B-04/VISUAL_ISSUES_LEDGER.md`：基线头注 + 重采批记录补 wt708 全量重采段。
- 新发现：无（本批全部差异可归因，无新产品缺陷；不占 V3-FIX-407/408）。
