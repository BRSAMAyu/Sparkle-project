# J-02 证据清单（checklist）——证据 ↔ acceptance ↔ 产物路径 三列映射

- 预备卡：wt784 J-02PREP ｜ base：main@`e36fe444` ｜ 只写不跑
- 「覆盖」列口径：✅=既有交付已覆盖（引 SHA）；🔲=**本卡（门后 simulator 执行，产物落 `v3-output/WT784-J02-SIM/`）补**；◐=既有交付部分覆盖、本卡补实机面
- 权威拆解：`v3/07_tasks/tasks.json` J-02.acceptance 两条 + `required_evidence` 四项；必读 `v3/01_product/FIRST_3_MINUTES.md`「Automated simulator acceptance」七项

## 1. required_evidence 四项（卡面）

| # | required_evidence | 覆盖 | 权威来源（SHA） | 产物路径模板 |
|---|---|---|---|---|
| E1 | base/final SHA | ✅ | wt764：base `3cbeb4a7` / final `787bc973`（均 main 祖先，wt772 已验 ancestry）；本 prep 卡 base `e36fe444` | v3-output/WT764-J02/notes.md §8；WT772 receipt §5 |
| E2 | targeted tests | ✅ | wt764 `787bc973`（红→绿 4/4 + 回归 + 后端 pin 4/4）；wt772 `7bbaf092` 独立复跑一致（含变异咬合抽验） | WT764-J02/notes.md §7；WT772-J02-REVIEW/receipt.md §2-§3 |
| E3 | **integration/simulator evidence** | 🔲 | **唯一销账缺口**（wt772 §6-1：wt764 ≤3min 为验算非实测，审查方无权豁免） | WT784-J02-SIM/evidence/<run_id>/（run_manifest.json + j02_timings.json + screenshots/ + db_probes.jsonl） |
| E4 | review receipt | ✅ | wt772 `7bbaf092`（PARTIAL，工程面合格）；**补证后销账需新 receipt 引用之**（验收模型：独立未参与会话） | WT772-J02-REVIEW/receipt.md；门后新 receipt 由审查会话出 |

## 2. acceptance 逐条

| # | acceptance（tasks.json 原文） | 覆盖 | 既有证据（SHA） | 本卡补的产物 |
|---|---|---|---|---|
| A1a | fresh user ≤3min 到 useful action | ◐ | wt764 `787bc973` headless 验算 ≈5 taps/55-70s（notes §5，**自decl非实测**） | 🔲 Leg R 全步秒表 ×5 persona：`j02_timings.json` + 截图 01-10 序列（≤180,000ms 判据） |
| A1b | seed 不进入真实 Memory | ◐ | wt764 `787bc973` 后端 pin 4/4（`test_j02_seed_memory_namespace.py`：种子后 memory_goals/episodic 恒 0 行 + V3-FIX-258 demo 短路首获覆盖），wt772 独立复绿 | 🔲 活栈 DB 探针双 0 行：`db_probes.jsonl` + guest 截图 11-13 |
| A2a | 注册端 session 稳定 | ◐ | wt764 router_smoke 软墙用例（wt282 `cd154f03` 建墙） | 🔲 实机 R3 软墙落 home + resume 卡：`04-home-softwall.png` |
| A2b | 游客端 session 稳定 | ◐ | wt764 router_smoke guest 折回用例 | 🔲 实机 G1：`11-guest-home.png` |
| A2c | 升级端 session 稳定 | ◐ | wt764 router_smoke 升级可达用例；V3-FIX-205 `cbc8e8ad`（升级 token 降级） | 🔲 实机 U1-U3 原位翻转 + persona 可达：截图 14-16 |

## 3. FIRST_3_MINUTES「Automated simulator acceptance」七项

| # | 清单项 | 覆盖 | 既有证据 | 本卡补的产物 |
|---|---|---|---|---|
| F1 | fresh install / cleared state | ◐ | J-01 `wt398-j01-first3`（v3/09_evidence/j01_first3/）已建立 wipe 语义；但其路线是 J-01 goal-wizard 非 J-02 快车道 | 🔲 manifest `fresh_install` 字段 + 每 persona 独立进程 |
| F2 | 首屏 primary CTA 无滚动可见 | 🔲 | 无（J-01 只测了首屏时延） | R0 断言 + `01-first-surface.png` |
| F3 | 5 次不同 Persona，非模板化 action | ◐ | J-04 后端差异化断言（wt772 §6-1 认可"此处主要是观感与秒表核"）；J-01 5 persona 实测当年因 O10/O11 全量回退/失败——**两缺陷已修（V3-FIX-140/141 FIXED@5aaf2c1a），修复后无实机复测** | 🔲 `proposals.json`（5 份 proposal 两两非同文）+ 5×`09` 截图 |
| F4 | 3 分钟脚本以内到 Action | 🔲 | 同 A1a | `j02_timings.json` verdict |
| F5 | 所有 loading >500ms 有反馈 | 🔲 | 无 | §3 横切断言 + timeout 截图族 |
| F6 | 错误不会回到空白页 | ◐ | wt371 `02b82cd2` FirstActionCard 诚实失败面（widget 级）；wt764 快车道失败 SnackBar（widget 级） | 🔲 实机错误面截图 `9x-*.png` |
| F7 | 截图由视觉 Reviewer 按 rubric 打分 | 🔲 | 无（依赖 E3 产物齐备） | 门后独立 Reviewer rubric 分，附新 review receipt |

## 4. 卡面 Work 三项 ↔ 既有覆盖（本卡不重做，只实测）

| Work | 覆盖 | SHA/证据 |
|---|---|---|
| W1 两个入口与最小 goal capture | ✅ | 体验示例入口=J-01 O5 面（`login_screen.dart:294-298` authTryExample）；goal capture 快车道=wt764 `787bc973`（`j02-fast-path-cta`） |
| W2 只问改变 first action 的问题；其余延后 | ✅ | wt764：goal-only 载荷 + `deferredAt(1)` + `onboardingCompleted` 推断语义（wt772 §5 语义核实 ✅，五问零裁减） |
| W3 guest example 与 real profile namespace 隔离 | ✅ | 机制=V3-FIX-258/257/142 既有裁决；J-02 级证据=wt764 后端 pin 4/4；活栈面归本卡 A1b 探针 |

## 5. 覆盖度小结（终报口径）

- **已覆盖（不动）**：E1/E2/E4 + W1/W2/W3 + A1b 后端面 + A2 router 面 + F3 后端差异化面 + F6 widget 面。
- **本卡（门后执行）全量补**：E3（唯一销账缺口）+ F2/F4/F5/F7 + A1a/A1b/A2 三端的实机对应面。
- **缝隙（如实，不美化）**：见 §6。

## 6. 缝隙与风险清单（预制时点 @ e36fe444，如实列出）

| # | 缝隙 | 性质 | 处置建议 |
|---|---|---|---|
| G1 | **wt764 notes §7 回归测试计数失实**（声称 draft_resume 8/8、submit_feedback 3/3、resume_card 5/5，wt772 实测 7/1/4；用例实际全绿，属笔误非代码缺陷） | 记账更正项（wt772 §6-4 已裁定） | 销账前在 WT764-J02/notes 追加更正注记或台账注记——**至今未做**，门后执行会话随手补 |
| G2 | **tasks.json J-02 status 仍为 `TODO`**，而 fleet 实际状态是 PARTIAL（fd4267ef"J-02 PARTIAL 不销账"）；规格权威与运行状态权威脱节 | 记账不一致 | 集成会话按 ADR-0011 权威模型收口；本卡不改 tasks.json |
| G3 | **O3（桌面注册 tap 无效零反馈，J-01 7 runs × 3 策略）无 FIX 号、无已证修复**；V3-FIX-17 只修 Web 假失败面（e460f192，"O3/wt436 register_screen 面零触碰"）。若门后实跑复现，Leg R 主链直接受阻 | 产品缺陷风险（P0-待归因，J-01 原判） | runbook §3-R3 已设 fallback（API 注册 + UI 登录，instrumented 披露，不计入 ≤3min 主张）；复现即按 §6 留证 + notes.md 登记（V3-FIX-533 起号） |
| G4 | **O10/O11 修复（V3-FIX-140/141 @5aaf2c1a）只有单测/网关红测级证据，修复后无实机端到端复测**；J-02 快车道不经 goal wizard，故不直接阻塞本卡，但 F3 差异化若走 FirstActionCard 生成链仍受益于其实机首验 | 验证缺口（非 J-02 销账前置） | 门后 R8（生成→proposal）天然覆盖该链；如实记录即可 |
| G5 | **J-02 专属 dart 驱动不存在**：`first3_measurement_test.dart` 是 J-01 goal-wizard 路线，不覆盖 resume 卡→快车道→modeling skip→FirstActionCard 链 | 执行前置缺口 | runbook §2.2 明示：执行会话第一步按 §3 编写驱动（J-01 同构，产品代码零改动） |
| G6 | **journeys/GJ01_register_onboarding_home.json web 轮期望已过时**：注册提交后 `then_wait: 学习目标`（persona 步0）与 wt282 软墙语义（注册→/home）矛盾——harness 既有 journey 不可盲目复用 | harness 陈旧 | 本卡 runbook 自带当前期望（router_smoke 语义为准）；GJ01 JSON 留待 harness 维护卡修正，本卡不动 |
| G7 | wt772 §6-3：N49 首聊破冰转 post-RC 跨层卡 | 范围外（已裁定） | 不属 J-02 销账前置，无动作 |
