# V4-B01｜V3→V4 继承基线核验 + RF-06 盘点（diff/evidence only）

执行：wtB01（分支 `agent/v4/b01`，自 main@3c4618cc 开出）· 2026-09-28 · 只读核验 + 证据产出，无产品代码变更。

## 1. 基线 SHA 记录（实况 git log，非快照转抄）

| 项 | SHA | 说明 |
|---|---|---|
| Sparkle-project main HEAD（本卡开工时） | `3c4618cc` | feat(v4): V4 设计与 Agent 执行包收编（58 卡）+舰队 V4 模式切换 |
| 8be9831c 之后的 main 新提交 | `35f0d62f` `b0f07eb3` `c8e9ac14` `3c4618cc` | 轮#317 CI33 起跑+wt816 一审派卡 / wt816 一审 receipt / 一审 C1/C2/C3 勘误（OPEN 去重 46）/ V4 包收编（145 文件 +21175/−4） |
| V3 收官集成点 | `8be9831c` | 轮#317 台账：11 提交（5c288841..8be9831c）已推，CI 32-rerun=第 7 绿；FIX-555/556/557 三行 FIXED 核验 |
| 本卡工作分支 | `agent/v4/b01` @ `3c4618cc` | worktree `/Users/brsama/code/GitHub/wtB01` |
| sparkle-cosmos 本机（只读） | HEAD `aa02635`（分支 `agent/node-b/T36/1`） | 未做任何写操作；worktree/分支/对象库仅只读命令 |

## 2. V3→V4 继承基线清单

### 2.1 直接继承（不重开，差量举证）

- **任务面 104/107 实况核验**：本仓 `v3/07_tasks/tasks.json` 实况 = 107 任务，104 done + 3 TODO（`O-01`/`Q-07`/`Q-08`）。与包内快照 `00_context/V3_INHERITANCE.json`（total 107 / done 104）**零差量**。104/107 仅作快照，现仓差量为 0，证据：本文件 + `run_manifest.json` cmd#3。
- **V3 遗留三项义务沿用（状态不重置、不重开卡）**：
  - `O-01` 公网 Staging HTTPS/WSS 一键部署——AK 轮转等用户前台窗口/代点（两度当面请求挂起，Chrome 探测 hidden）；FIX-556（JWT 注入）+FIX-557（RESTACK runbook）已修为部署前置。
  - `Q-07` Chaos/Recovery/Offline/Restore Storm 终验——TODO。
  - `Q-08` V3 Final Gate Audit / Commercial RC——十一 gate 草案已合（wt812），一审 receipt（`b0f07eb3`）+ 勘误落稿（`c8e9ac14`）在 main；正式执行待双审。
- **已有能力复用清单**（按 `00_context/READING_AND_CONFLICTS.md`「已有能力必须复用」全单继承，V4 不另造）：Aurora 六策略字段、五层用户模型、撤销 epoch/记忆版本、真实命令回执、Human/Agent/Hybrid 契约、OpenClaw 唯一 Runtime、dual-core 路由、关系型星图真源、sprint_task_ledger/goal_today_view、context.* 令牌入口。
- **负结果保留**：S04 Q04 首轮 precision=0/invalid=10/overpersonalization=50/120/uplift=0pp 反例、S03 修后消融 full 9/20 与四臂零澄清、S05/S06 L2 final p95=65.4s / L3=126.7s 慢深推理实录——按冲突表冻结原反例，不借换版删除；后续复验分报时间/版本/证据层级。

### 2.2 FIX 台账实况（核实 FIX507/539/540/543 较新成果，不生成重复修复卡）

台账真源：`v3/06_agent_fleet/DYNAMIC_ISSUES.md`（390 FIX 行）。行序非严格追加式（同一号多行时以 FIXED/CLOSED/WONTFIX/产品拍板行优先，无已解行则取末行），机器口径重算结果：

| 项 | 值 | 交叉验证 |
|---|---|---|
| FIX 号总数 | 388 | |
| 已解（FIXED/CLOSED/WONTFIX/产品拍板） | 319 | |
| **最终 OPEN** | **46** | 与 `c8e9ac14` Q-08 一审勘误「OPEN 去重 46」吻合 |
| 非 OPEN 非标准状态格（unknown 语义） | 23 | 见 §2.3 |

**卡面点名的四项较新成果核实（全部有 commit 锚，不派重复修复卡）**：

| FIX | 状态锚 | 摘要 |
|---|---|---|
| FIX-507 | `FIXED@8e503cd8` | D-05 intervention lifecycle 写路径生产接线 |
| FIX-539 | `FIXED@583e0c8a` | macOS 注册提交 tap 零反馈根治（consent 拦截滚动+持久内联反馈） |
| FIX-540 | `FIXED@b87f5f13` | 快车道 skip 后 FirstActionCard 间歇缺失（first-action 投影失效链） |
| FIX-543 | `FIXED@697e34bf` | J-02 截图证据失真（shot() v2 栈顶路由双条件锚定） |

**带入 V4 追踪的 OPEN FIX（F/J 线直接相关，唯指针不复制全文）**：

- `FIX-549`：tearDownAll Hive.close() 确定性不完结——产品侧根因 community_provider fire-and-forget 缓存写跨 FakeAsync 拆除（wt809 调查行，OPEN）。
- `FIX-554`：WS ticket 请求经单例链路漏到本机活网关（与 549 同族：产品侧 provider 缝隙缺失；登记 2026-09-28，OPEN）。
- `FIX-545`：E-08 FALLBACK 计量错挂（no_generation_model 标签 7 qid），行内明示「**V4 追踪**」。
- `FIX-537`：ope_gatekeeper.py 信号分类门孤儿组件，行内明示「**V4 接线裁决**」。
- `FIX-535/536/541/542`：J 线残差（HybridJourneySheet 孤儿面/落点分歧/注册落点扩展/ops launchd 家族），开放或裁决中。
- `FIX-52/97`：产品拍板待（摩擦诊断 recent_failures 面/第二纠正入口形态）。
- 其余 OPEN（`161 162 168 175 176 188 199 218 220 237 256 261 285 290 291 299 308 317 321 358 373 375 379 385 430 439 495 500 501 502 503 505 509 513 514 524 532 534`）按台账原文生效，本卡不复制不裁决。

### 2.3 未知状态（明确 unknown，不臆断）

23 行状态格为非标准枚举（「随 M-xx 评测迭代捆绑」「产品拍板：…」「行内自登记不阻塞」备忘型、CLOSED 引链纠指混合体等，如 FIX-15/22/30/32/38/39/42/44/46/48/52/55/56/97/113/144/147/160/164/174/187/225/238/240/259/286/341 中的非枚举行）——机器口径既不归 OPEN 也不归已解，**按 unknown 保留原文**，统一口径留 Q-08 终审裁决，本卡不代裁。

## 3. RF-06 未合并改动清单 + 冲突面预判（V4 F 线动 mobile 前必读）

### 3.1 分支存在性（本机实况）

- **本机 sparkle-cosmos（`/Users/brsama/code/GitHub/sparkle-cosmos`，全程只读）：`NOT_PRESENT_LOCAL`**——`git log agent/rf06-full-ui` 与 `origin/agent/rf06-full-ui` 均无引用；对象库无 `8c6b8c17`/`04214f44`/`92203d5ce`（cat-file 逐一证实）。
- **远端实况**（`git ls-remote origin`，只读网络读）：`refs/heads/agent/rf06-full-ui` **存在** @ `92203d5ce64288297fca209ffddf1ebf5765c329`（origin=github.com/thequipster/sparkle-cosmos）。
- GitHub API（只读）核实远端头：`92203d5ce` = "docs(rf06): document frontend design and reproducible handoff"，父 `04214f44`，2026-09-28T07:23Z，作者 thequipster——**即交接文档提交，与交接包快照一致**（交接文档：产品行为/APK=`8c6b8c17`；代码候选 `af0ff8fa` 仅补测试格式、APK 未重建；基线 `agent/rf-nonvisual-integration@e3f85eb3`）。
- 交接文档 `/Users/brsama/Downloads/前端设计与迭代交接.md`（288 行）完整可读，本盘点以其为口径：**RF-06 状态 RUNNING，设备视觉验收 BLOCKED**（Pixel_7 QEMU 三败 0xc0000005）；45/45 自动化回归≠设备验收；**完整前端尚未完成，也未合入主仓**。

### 3.2 未合并改动清单（GitHub compare API 只读：`e3f85eb3...92203d5ce`）

18 commits ahead / behind 0；18 文件，+1121/−408。其中 **mobile/ 10 文件 ≈ +635/−649**：

| 文件 | 状态 | 规模 | 内容 |
|---|---|---|---|
| `mobile/lib/features/home/presentation/widgets/compact_status_bar.dart` | 改 | +120/−249 | 首页身份区重写（人物层级替代拥挤工具条，近全量重写） |
| `mobile/lib/features/home/presentation/screens/dashboard_screen.dart` | 改 | +7/−2 | 首页顺序：身份→今日行动→Aurora |
| `mobile/lib/features/task/presentation/widgets/task_focus_entry_card.dart` | 新 | +204 | 任务执行页首卡（完整标题/正数预计/真实完成标准/主动作；斜切纸卡+代码绘制像素芽苗） |
| `mobile/lib/features/task/presentation/task_completion_criteria.dart` | 新 | +33 | 完成标准唯一解析（guideJson.done_criteria→success_checklist→success_criteria→task.successCriteria） |
| `mobile/lib/features/task/presentation/screens/task_execution_screen.dart` | 改 | +27/−106 | 首卡挂接+六专注特性胶囊移除 |
| `mobile/lib/features/task/presentation/widgets/task_completion_celebration.dart` | 改 | +3/−23 | |
| `mobile/lib/features/task/presentation/widgets/task_guide_panel.dart` | 改 | +2/−6 | |
| `mobile/test/features/home/presentation/widgets/compact_status_bar_hero_test.dart` | 新 | +57 | |
| `mobile/test/widget/dashboard_screen_structure_test.dart` | 改 | +6/−6 | |
| `mobile/test/widget/task/test_task_execution_ux.dart` | 改 | +238/−10 | 三文件组 45/45 回归 |

docs/ 8 文件（交接文档+288、迭代记录+119、任务卡/续报/README/基线首页截图等）。

可回退单位（交接文档 §9）：任务切片 `af0ff8fa`→`8c6b8c17`→`966e33b1`；首页 `eae62843`/`a1761e9b` 独立。

### 3.3 冲突面预判

**结构性事实：两仓不同根**——sparkle-cosmos root `b3908b0`（340 commits）vs Sparkle-project root `1722e6dc`（1789 commits），无共同历史。RF-06 无法直接 `git merge` 进 Sparkle-project；只能按交接文档 §12 走补丁快照（`e3f85eb3..04214f44`）`git apply --check` 后逐切片移植，或由 slsjz 侧按 `agent/sync/sparkle-project-*` 先例重新同步。

**同名双改高危面**（RF-06 触碰 ∩ Sparkle-project main 自 2026-09-24 变更；SP main 该窗 mobile/ 共 163 commits、690 文件）：

| 文件 | RF-06 侧 | SP main 侧（近窗 commits） | 风险 |
|---|---|---|---|
| `features/home/presentation/screens/dashboard_screen.dart` | 改 7+/2− | 8 commits（J-04 FirstActionCard 挂载、U-09 tokens、J-02 投影等） | **高** |
| `features/home/presentation/widgets/compact_status_bar.dart` | 近全重写 120+/249− | 2 commits（wt674 a11y 语义标签、wt676 DS 令牌统一） | **高** |
| `features/task/presentation/screens/task_execution_screen.dart` | 改 27+/106− | 5 commits（wt792 J-02 驱动、wt800 FIX-539 内联反馈等） | **高** |
| `test/widget/dashboard_screen_structure_test.dart` | 改 6+/6− | 2 commits | 中 |

**RF-06 独有文件**（SP main 无此路径，可干净带入）：`task_focus_entry_card.dart`、`task_completion_criteria.dart`（均核实 ABSENT_IN_SP_MAIN）、`compact_status_bar_hero_test.dart`、`task_guide_panel.dart`、`task_completion_celebration.dart`、`test_task_execution_ux.dart`。

**语义相邻面（非同文件但同域，移植时防回退已修缺陷）**：SP main J-02 快车道线（FirstActionCard 修复 `b87f5f13`、value-before-profile 快车道 `787bc973`、today_cockpit_provider 等）与 RF-06 首页「身份→今日行动→Aurora」重写同域——移植后行为准绳 = SP main J-02 修后语义（含 FIX-540 修法），非 RF-06 基线 `e3f85eb3` 的旧行为。

**后续同步建议**：
1. 先由 slsjz 侧/有写权限方把 `agent/rf06-full-ui` 同步到本机可达克隆（或提供含补丁的交接 ZIP；纯 fetch 本仓会写 .git，本卡为守只读红线未执行）。
2. V4 F 线开工卡绑定交接文档 §10 顺序：先补首页/任务切片真实设备证据，再继续重写；RF-06 设备 BLOCKED 不阻塞 F 线代码面盘点。
3. 移植按「可回退切片」逐个 `git apply --check` + flutter analyze/定向测试，不整包盲合（交接文档明令）；`mobile/mobile/` 旧误复制目录不得提交或消费；`mobile/lib/gen` 按本仓 proto 工具链重新生成。
4. RF-06 侧守卫（UI-TOKENS/L10N-EN）与 SP main 守卫版本先对齐再合流；SP main 侧 a11y allowlist/tokens ratchet 基线更新随移植卡走。

## 4. 验收对照

| 卡面验收 | 结果 |
|---|---|
| 104/107 仅作快照，给出现仓库差量及证据链接 | 满足：现仓实况 104 done/3 TODO，差量 0；§2.1 + run_manifest.json cmd#3 |
| 已修事项不生成重复修复卡 | 满足：FIX-507/539/540/543 只举证（§2.2），未派任何修复卡 |
| 未知状态明确 unknown | 满足：§2.3（23 行按 unknown 保留原文） |
| 发布已有 root AGENTS 优先，V4 规范以增量合并不覆盖 | 满足：本卡零触碰根 `AGENTS.md`；v4/ 内纯增量（evidence + tasks.json 状态字段） |
| V3 已 DONE 任务 ID 与证据不可重置 | 满足：v3/ 全目录零写操作 |

## 5. 自证与红线

- sparkle-cosmos 仓全程只读（仅 git log/branch/remote/ls-remote/cat-file 只读命令；未 fetch、未 add/commit/checkout 任何引用）。
- 未跑 HEAVY；未调用任何 LLM；本卡为文档/验证类，产品零改动。
- 独立审查未发生（review_receipt.json 如实 PENDING，不自称完成）；集成 SHA 复验待合并后由审查会话执行。
