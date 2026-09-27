# WT671-U01 · U-01 集成 HEAD 复核与 Inventory 刷新

会话 wt671（卡池 U-01）｜2026-09-25｜base=2392b0b8（worktree `agent/node-b/wt671/u01`）
性质：**盘点+复核卡**——U-01 本体已双证完成，本卡执行 U-01 卡面 Execution Protocol 遗留项「合并后在 integration HEAD 重跑相关检查」，并刷新设计表面 Inventory 至当前 HEAD。

---

## 1. 结论摘要

- U-01（Inventory 与 Component 收敛计划）**已完成且闭环**：初始盘点 8c69c670 + Step 0-7 收敛链 8 提交（终态 7590aa1a 自述 chain complete），全链为 main HEAD 祖先；fleet state `v3/.sparkle_v3_fleet_state.json` done 列表含 `U-01`。**不重做。**
- integration HEAD 复跑：UX-COMP ratchet 守卫 **PASS**（rawButton=25/58, rawSpinner=34/40, rawChip=40/40, parallelClass=200/201, colorLiteral=121/121）；守卫单测修复陈旧断言后 **10/10 绿**（发现 V3-FIX-357，本卡修复）。
- 卡面验收两条均有实证承载：owner 唯一由守卫 ratchet+README CONVENTION 持续强制；before screenshots（B-04-final 9 张 canonical，sha256 入 manifest）与 consolidation plan（Step 0-7）已随 8c69c670 及各 Step REPORT 落地。
- 证据链 3 处悬空引用登记 V3-FIX-358（不重建已消失文件，以指针注记诚实指向实质承载处）。

## 2. 卡完成双证（git log 判据）

| 证据 | 内容 |
|---|---|
| 提交链 | 8c69c670（INVENTORY 9 surfaces 157 私有平行类 + CONSOLIDATION_PLAN Step 0-7 + CONVENTION + ratchet 守卫）→ 4799997d（Step 0）→ 7729f5a1（Step 2）→ c99838d5（Step 1, rawChip 75→8）→ 76847722（Step 3, rawSpinner 79→8）→ 7cf1198c（Step 4, rawButton 87→19，CustomButton 退役）→ 4e406994（Step 5, colorLiteral 123→103）→ 7590aa1a（Step 6+7, confetti 双挂载修+守卫登记 manifest 第 75 行，**chain complete**） |
| 状态权威 | fleet state done 列表含 `U-01`（与 U-04/U-03 同批入 done）；tasks.json 规格权威由 8d4291aa 批次核对 |
| 链终态量化 | rawChip 75→11（-85%）/ rawSpinner 79→8（-90%）/ rawButton 87→19（-78%）/ colorLiteral 136→100（-26%）/ 带债文件 146→98（终态基线聚合实测吻合：98 文件 {19/8/11/146/100}） |

## 3. 守卫与基线演进（链终态 → HEAD，诚实记账）

| 时点 | 提交 | tracked 文件 | rawButton | rawSpinner | rawChip | parallelClass | colorLiteral |
|---|---|---|---|---|---|---|---|
| U-01 冻结基线 | 8c69c670 | 146 | 87 | 80 | 75 | 149 | 136 |
| 链终态下钉 | 7590aa1a | 98 | 19 | 8 | 11 | 146 | 100 |
| sprint 面入册（第10根） | b10ca9be | +sprint | —（该面裸件迁移后清零，LinearProgressIndicator×3 登记为 rawSpinner 债） | | | | |
| 三域扩扫（第11-13根） | 1e39dd3c (N9) | 154 | 58 | 40 | 40 | 201 | 121 |
| **HEAD 现值（2392b0b8）** | — | 149 有债+见证 | **25** | **34** | **40** | **200** | **121** |

- 限值上升全部来自**扫描面扩容**（sprint/community/photon/error_book 入册时把旧债按登记时点实测冻入基线，only-down），非存量债洗白；N9 提交自证「111 legacy entries 0-deleted 0-changed, +43 new entries」。
- rawChip/colorLiteral 现值**顶格**（40/40、121/121）：任何新增即 FAIL；parallelClass 余量 1；rawButton/rawSpinner 低于限值（N9 后既有清理被 only-down 吸收）。
- 基线孤儿条目 1 条：`photon_balance_card.dart`（rawSpinner=1）文件已删——债随文件消失，良性，无需清键。

## 4. HEAD 现状 per-surface 计数（守卫同款口径，2392b0b8 实测）

| surface | rawButton | rawSpinner | rawChip | parallelClass | colorLiteral | 备注 |
|---|---|---|---|---|---|---|
| galaxy | 4 | 7 | 1 | 19 | 82 | 视觉锤；其中 star_map_painter 26 + sector_config 14 = 40 为 E1 冻结豁免预算 |
| chat | 2 | 0 | 7 | **62** | 12 | parallelClass 全仓最大族（status_awareness_bar 7、aurora_receipt_chip 5 等） |
| community | 8 | 9 | 17 | 29 | 0 | N9 扩扫入册冻结（「本卡不做组件迁移」），待未来收敛卡 |
| plan | 5 | 13 | 5 | 14 | 21 | learning_portfolio 19 处混合债 |
| home | 2 | 0 | 0 | 31 | 0 | Step 2 装饰降档后结构债为主 |
| task | 1 | 0 | 0 | 19 | 5 | |
| error_book | 0 | 5 | 6 | 13 | 0 | N9 扩扫冻结 |
| memory | 3 | 0 | 2 | 7 | 1 | |
| goal | 0 | 0 | 0 | 5 | 0 | |
| settings | 0 | 0 | 1 | 0 | 0 | |
| user（profile/persona/unified 三单文件） | 0 | 0 | 0 | 1 | 0 | Step 5 清零后复核达标 |
| photon | 0 | 0 | 1 | 0 | 0 | N9 扩扫冻结 |
| **合计** | **25** | **34** | **40** | **200** | **121** | 与守卫 PASS 输出逐位一致 |

债集中度 Top 文件：star_map_painter(26)/learning_portfolio(19)/galaxy_screen(18)/sector_config(14)/node_detail_sheet(13)。

## 5. 收敛计划状态与移交候选（均不入本卡）

**已完成**：Step 0-7 全部落地（见 §2）。原计划面（onboarding/home/chat/goal/task/memory/galaxy/profile/settings 9 surfaces）owner 唯一已达成并由 ratchet 持续强制。

**剩余收敛候选**（按债量排序，供后续视觉面卡采撷；全部已被基线冻结、零新增通道）：
1. **chat parallelClass 62**——私有平行组件类最大族，迁移收益最高；与 aurora/chat 设计语言卡同面。
2. **community（54 处混合）+ error_book（24）+ photon（1）**——N9 冻结的三域旧债，收敛时按 sprint 先例（b10ca9be：迁移+清零+登记盲区）逐面处理。
3. **plan rawSpinner 13 / learning_portfolio 混合债 19**——冲刺面（第10治理面）内除 sprint_screen 外的 plan 呈现代码。
4. **galaxy 非 E1 colorLiteral ≈42**（总 82 − E1 冻结 40）——视觉锤豁免只覆盖 painter/sector_config 两文件，其余 literal 仍可收 token。
5. home parallelClass 31（Step 2 只降装饰层，结构类未动）。

**Non-goals（沿 8c69c670）**：不做全仓机械重构；galaxy 视觉锤结构豁免；U-03 撞面（memory/user/aurora）停手登记项不越界。

## 6. 本卡发现与处置

| 号 | 发现 | 处置 |
|---|---|---|
| V3-FIX-357 | UX-COMP 守卫扫描根 `features/onboarding/presentation` 陈旧：该目录已随 V3-FIX-342 @e610853e 整链下线，`scan_roots()` 对缺失根静默跳过（守卫仍 PASS，零覆盖损失），但伴随单测 `test_scan_roots_exist` 自 e610853e 起红（1/10），无人触达守卫文件 | **本卡修复**（机械零行为）：SCAN_ROOTS 摘陈旧根+docstring 同步；基线零 onboarding 条目，ratchet 面零变化（守卫 PASS 输出逐位不变实证）；单测 10/10 绿 |
| V3-FIX-358 | U-01 证据链 3 处悬空引用：守卫 docstring→`v3-output/U-01/INVENTORY.md`（从未入库）；README→`v3-output/U01-STEP4/REPORT.md`、`U01-STEP5/REPORT.md`（从未入库，工作树未合并产物）。在库证据为 U01-STEP{0,1,3}/REPORT.md | **登记+指针注记**：不重建消失文件（不可复原且禁止伪造）；守卫 docstring 改指本刷新文档，README 两处加证据注记指向实质承载（提交 7cf1198c/4e406994 说明+节内保留清单） |

## 7. 验证证据（本卡增量）

- base SHA 2392b0b8（worktree 分支 `agent/node-b/wt671/u01`，不 push）
- `python3 scripts/guards/check_ux_component_convention.py` → PASS，修复前后五维总数值逐位一致（25/34/40/200/121，零覆盖变化实证）
- `python3 scripts/tests/test_ux_component_convention.py` → 修复前 1 失败（test_scan_roots_exist，onboarding 根）→ 修复后 **Ran 10 tests, OK**
- 触达文件均为 .py/.md，零 Dart 产品码变更 → 无需 flutter test/analyze 触达（守卫单测为唯一触达测试面）
- per-surface 计数由守卫模块同款函数复算（/tmp 一次性脚本，不入库），与守卫 PASS 总数交叉吻合
- 零触碰：`.env`、`tasks.json`、golden 基线与 `scripts/devtools/visual_baseline/`（wt667 面）、backend 四卡（wt666/669/670）声明面
