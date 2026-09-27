# WT676 · U-09 L5 三端视觉/交互一致性 Diff（盘点矩阵 + 机械收敛实施）

会话 wt676（卡池 U-09 续做）｜2026-09-25｜base=d87ea8fd｜worktree `agent/node-b/wt676/u09`
性质：**Diff 盘点 + ≤5 项零风险机械统一**——U-09 headless 段已由 wt390 双证落地，本卡从实际进度续做：跨表面一致性矩阵盘点 + 令牌消费机械收敛；真机段维持 HUMAN_INBOX 交接不重做不伪造。

---

## 0. 卡完成双证判定（不重做判据）

| 证据 | 内容 |
|---|---|
| 提交证据 | 60366592 `fix(ux): wt390 卡 U-09 三端视觉/交互一致性 headless 段`（`git merge-base --is-ancestor 60366592 HEAD` = true，main HEAD d87ea8fd 祖先） |
| 树内证据 | 本 worktree 实存：`mobile/test/widget/u09_platform_render_contract_test.dart`（11 契约用例）、`mobile/test/shared/canonical_state_fixture.dart`、`scripts/devtools/visual_baseline/matrix.py`、`v3-output/U-09/SCREENSHOT_MATRIX.md`、`v3-output/U-09/DIFF_REPORT.md`、`v3/04_ux/MULTIPLATFORM.md` 允许差异登记表 |
| 状态权威 | wt390 REPORT READY_FOR_REVIEW；真机 45 张截图矩阵段转 HUMAN_INBOX（诚实未采集） |

**本卡续做边界**：wt390 已覆盖平台判定接缝修复、三端渲染契约（C1-C7）、URL/session/keyboard 平台差异、允许差异登记。其 REPORT §8 移交的「设计系统收敛面」（U-01 口径）与本卡任务书的「跨表面 diff 清单+收敛建议」即本卡主体。

## 1. 三端现状边界（如实记录，不虚构）

- **交付三端 = Android / Web / macOS**（`v3/04_ux/MULTIPLATFORM.md` 权威口径）。
- Flutter 目标目录 `mobile/{android,ios,web,macos,windows,linux}` **六目录全在**：三端不是「mobile 单端+缺位」，是真实 Flutter 多平台目标；但 `windows/`、`linux/` 在交付集外（fuchsia 同）。
- 平台差异真源分三类（wt390 已审计）：①`kIsWeb`/`defaultTargetPlatform` 分支（api_constants、design_system 转场）；②条件导入 `_io`/`_web`（token 存储等）；③`Platform` 门控硬件能力（触觉/音频）。全部在允许差异登记表有 reason。
- **真机段边界**：本 worker 无浏览器/AVD 权限，45 张截图矩阵不伪造，维持 HUMAN_INBOX 交接；headless 契约 11 用例（含三端渲染指纹逐字一致、canonical home 三端 viewport 零 overflow）为本卡一致性断言的可执行承载，本卡复跑绿（见 §6）。

## 2. 一致性 Diff 矩阵——令牌消费（context.typo / DS）

权威层级：`tokens_v2/`（唯一事实源）→ `theme/`（`context.colors/typo/space/radius/motion` 唯一 context 入口）→ `DS`（数值层已冻结 @Deprecated，存量过渡）。扫表面=U-01 inventory 口径 13 surface 族。

### 2.1 Typography 消费（context.typo 调用 vs fontSize 字面量）

| surface | context.typo 调用 | fontSize 字面量 | fontSize 令牌形 | 判定 |
|---|---|---|---|---|
| home | **228** | 57 | 7 | 采用最好，字面量 pockets 小 |
| chat | 9 | **108** | 120 | **双态撕裂**：120 处令牌形与 108 处字面量并存，最大字面量族 |
| community | 33 | 83 | 90 | 中等撕裂 |
| plan | 55 | 16 | 20 | 良好 |
| galaxy | 0 | 62 | 2 | **零采用**（视觉锤面，E1 冻结豁免预算内，迁移需视觉 owner 裁决） |
| task | 0 | 40 | 22 | 零 context.typo 但过半令牌形 |
| insights | 0 | 23 | 8 | 零采用 |
| goal | 0 | 12 | 2 | 零采用（面小） |
| settings | 0 | 6 | 0 | 面小，字面量少 |
| memory | 0 | 0 | 7 | 字面量已清零 |

### 2.2 Spacing 消费（抽查本卡三实施面）

| surface | 裸数值 EdgeInsets | DS/SparkleSpacing 形 | 采用率 |
|---|---|---|---|
| home | 155 | 935 | ~86% |
| insights | 41 | 171 | ~81% |
| settings | 19 | 131 | ~87% |

遗留 `SpacingSystem`（tokens_v2/spacing_token.dart）已 @Deprecated 指向 DS/SparkleSpacing，12pt 需组合 sm+xs——存量引用收敛建议见 §5。

### 2.3 圆角族（本卡主实施维度）

features 全仓 `BorderRadius.circular(<literal>)` 共 **1012 处**，分布：

| 值 | 处数 | DS 令牌 | 判定 |
|---|---|---|---|
| 999 | 188 | `DS.borderRadiusFull`（=999.0） | 族内（胶囊族） |
| 12 | 184 | `DS.radius12` | 族内 |
| 16 | 120 | `DS.radius16` | 族内 |
| 8 | 119 | `DS.radius8` | 族内 |
| 20 | 77 | `DS.radius20` | 族内 |
| 4 | 35 | `DS.borderRadius4` | 族内 |
| 14 | 68 | — | **族外** |
| 18 | 58 | — | **族外** |
| 24/2/10/28 | 33/33/33/21 | — | **族外** |

- 仓内已有双先例：`BorderRadius.circular(DS.radius12)`（home/insights/settings 8 处既有）与 `DS.borderRadiusFull`（core/design/widgets 5+ 处）——本卡实施沿用同形。
- **族外值 213+ 处**（14/18/2/10/28/24…）是圆角族不齐的实质 diff：不属零风险机械替换（改值=改视觉），只登记收敛建议（§5）。

## 3. 一致性 Diff 矩阵——交互模式（空态/错误/加载）跨表面

canonical 组件（`core/design/widgets/`）：空态=EmptyState/CompactEmptyState；错误=CompactErrorCard/CustomErrorWidget；加载=LoadingIndicator/SparkleSkeleton（骨架唯一 owner）+StagedSurfaceLoader（U-06 分阶）。

| surface | canonical 空态 | canonical 错误 | canonical 加载 | 裸 spinner 文件 | 备注 |
|---|---|---|---|---|---|
| home | 9 | 3 | 4 | 0 | 最齐 |
| chat | 3 | 1 | 2 | 0 | 主屏未接 U-06 闸门（wt358 已登记，本卡不碰 state 语义文件） |
| community | 16 | 7 | 11 | 3 | rawSpinner 债冻结（ratchet 34/40） |
| plan | 6 | 1 | 4 | 2 | |
| task | 3 | 2 | 1 | 0 | |
| galaxy | 1 | 0 | 1 | 2 | 视觉锤 E1 豁免 |
| memory | 2 | 1 | 0 | 0 | |
| goal | 0 | 0 | 1 | 0 | 无列表屏（goal 渲染于 home dashboard），空态场景天然少，非缺陷 |
| settings | 0 | 0 | 0 | 0 | 设置面无空态/加载场景，非缺陷 |
| insights | 3 | 1 | 0 | 3 | **加载面最薄**：3 裸 spinner 文件零 canonical 加载 |
| user | 1 | 0 | 1 | 1 | |
| error_book | 2 | 3 | 0 | 2 | |
| photon | 0 | 2 | 0 | 0 | |

跨表面模式 diff 结论：空态收敛最好（EmptyState 71 文件）；错误次之（CompactErrorCard 23 + CustomErrorWidget 6，双组件分工已定）；加载面收敛最弱——裸 spinner 34 处（ratchet 冻结、19 surface 组分布）+ insights 无 canonical 加载 + wt390 观察的按钮异源（StagedSurfaceLoader longRunning 退路 TextButton.icon vs SurfaceStateView SparkleButton，U-06 文件，wt673 在航本卡避让）。

## 4. 本卡实施：零风险机械统一 3 项（≤5 限额内）

**统一式**：字面量 → 同值既有 DS 令牌，表达式形状沿用仓内先例。`BorderRadius.circular(12)` ≡ `BorderRadius.circular(DS.radius12)`（DS.radius12=12.0 static const）；`BorderRadius.circular(999)` ≡ `DS.borderRadiusFull`（BorderRadius.all(Radius.circular(999.0)) static const）；`BorderRadius.circular(4)` ≡ `DS.borderRadius4`。类型同（BorderRadius）、值同（逐 token 定义核对）、const 语义同——零视觉/行为变化。

| # | 范围 | 机械替换 | 处数 |
|---|---|---|---|
| 1 | home（20 文件） | 12→radius12、16→radius16、8→radius8、4→borderRadius4、999→borderRadiusFull | 65 |
| 2 | insights（9 文件） | 同上映射 | 18 |
| 3 | settings（4 文件） | 同上映射 | 9 |
| **计** | **33 文件** | | **92 行（+92/−92 纯替换）** |

面选择依据：三个 B-04 canonical 相关面（home=dashboard canonical、insights、settings），全数避开并行在航面（wt673 的 cognitive/community/goal/memory/task/user 15 文件、wt674 U-08 semantics、wt675 U-07 导航、wt667 golden/visual_baseline harness）与 galaxy E1 冻结预算文件。族外值（14/18/2/10/28 共 44 处在三面内）**不动**，只登记。

## 5. 收敛建议（不在本卡实施，逐条移交）

1. **圆角族外值裁决**（设计 owner）：14/18 是最大族外对（68+58 处），建议要么扩 `DS.radius14/radius18` 入族（改 token 文件+冻结口径），要么逐面归一到 12/16——两者都是视觉决策，需 golden 真机基线背书后做。
2. **chat typography 双态撕裂**（108 字面量 vs 120 令牌形并存）：chat 是 parallelClass=62 的最大债面（U-01 已记），typography 撕裂同源；建议随 chat 面收敛卡一次做，避免二次触碰。
3. **galaxy/insights/task/goal 的 context.typo 零采用**：galaxy 受视觉锤豁免约束应最后动；insights/task/goal 可按 U-01 Step 同款「面 owner 唯一」模式逐面收。
4. **加载面收敛**：insights 3 个裸 spinner 文件迁 LoadingIndicator（ratchet 余量 40-34=6，迁移是减向安全）；连同 community/plan/chat 的冻结债按 U-01 ratchet only-down 消化。
5. **按钮异源**（wt390 移交）：StagedSurfaceLoader 退路钮与 SurfaceStateView 动作钮统一为 SparkleButton——U-06 文件，待 wt673 U-06 卡落地后由其 owner 或后续卡执行。
6. **真机段**（HUMAN_INBOX 维持）：45 张矩阵采集后，用 `visual_baseline.py manifest/verify/diff` 链回填 DIFF_REPORT.md；golden 真机基线是 §5.1 圆角归一的前提。

## 6. 验证件套（当场真跑）

| 门 | 结果 |
|---|---|
| flutter analyze | **No issues found**（0 新增） |
| home 定向（exam_sprint/home_notification/predicted_intent/prism 4 件） | 28 绿 |
| home 定向（decoration_tier/decoration_policy/dashboard_growth_sections_l2） | 19 绿 |
| insights 定向（forecast_honesty/overview_screen/evidence_insight_card） | 8 绿 |
| 触达文件直引测试（understanding_panel_copy/openclaw_connection_panel/insights_frontend_smoke） | 16 绿 |
| U-09 契约回归（11 用例，含 C1 三端渲染指纹+C6 canonical home 三端 viewport 零 overflow） | 11/11 绿 |
| UX-COMP ratchet 守卫 | PASS，五维逐位不动（25/34/40/200/121）——92 处替换零 ratchet 漂移实证 |
| dashboard golden | 4 变体 FAIL（各 0.18%/7632px）——**A/B 判定为既有环境漂移非本卡引入**：同命令在无改动 pristine main（Sparkle-project checkout）跑出**逐变体完全相同**的 7632px 失败签名；改前改后失败签名逐位一致 = 本卡零视觉增量。本机 golden 不能出绿是环境边界，禁 `--update-goldens` 强刷（登记 V3-FIX-365） |

验证纪律自查：未触碰 golden 基线文件（test/goldens/** 只读运行，无 `--update-goldens`）；未触碰探针类 v3-output 证据（Q03/U-01 只读引用）；未触碰 wt673/674/675/667 在航面；未动 `.env`/`tasks.json`；未 push。

## 7. Forbidden 自查

- 未重建权威真源：canonical 语义=U-06、采集链=B-04、允许差异表=wt390 MULTIPLATFORM——全部只读复用；本卡只做令牌消费机械收敛与盘点。
- 未用 mock/静态阅读冒充体验通过：真机段诚实维持 HUMAN_INBOX 未采集态；headless 段全部真实泵入断言（契约 11 用例复跑）。
- 未为一致砍平台能力：允许差异登记表零改动。
- 未弱化守卫：ratchet PASS 逐位不动。
