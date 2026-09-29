# V4-U12 一审 receipt（R1 · wtU12R1）

- 审查者：wtU12R1（独立会话，未参与 U12 实现）
- 审查对象：`agent/v4/u12` @ `a7eb52b0`（实现头 `7cadd507`，基线 `c94afbe4`）；审查时工作树 clean（首尾两验 `git status --porcelain` = 0 行）
- 卡标准：`v4/04_tasks/tasks.json` `V4-U12`（normal risk，1 独立审查，lock=ui-rewards）
- 审查方式：只读审查 + 独立复跑 + 3 组临时探针（mutation 1 组 + 行为探针 2 组，用后即删）
- **裁决：APPROVE_WITH_CONDITIONS**（三条验收均有独立证据支撑、无检测面弱化、无契约违例；两条条件级修正见 §C——均不动验收与实现语义，属测试效力与证据归属勘误）

## 0. 独立复跑总表（本会话实测，非转抄）

| 项 | 实现者声称 | R1 实测 | 结果 |
|---|---|---|---|
| 新测 14 | 全绿 | `flutter test`（3 文件）：**+14 全绿**（幂等 5 + 自我锚 3 + 家族边界 6，逐用例过屏） | 一致 |
| 幂等守卫 mutation | （自述"mutation 判别对"覆盖庆祝面；幂等钉未单独声称 mutation） | **拆 `_actionInFlight` 闸后 5 用例仍全绿**——双击钉对守卫不可失败（详见 §2） | **不一致（条件 C-1）** |
| 后端屏障抽验 | 23 passed（307s） | 抽验三测：`monthly_cap_blocks_second_redeem_and_converges` + `concurrent_redeem_exactly_one_success` + `transfer_in_excluded_from_redeemable_base` → **3 passed, 39.34s** | 一致 |
| 三守卫 | 3 PASS | N9（SELF-TEST PASS + 棘轮 256/256, 72/72, 77/77, 18/18）、COMM-LB、BA-ROUTES（621↔1015, 169 ledgered）**全部亲跑 PASS** | 一致 |
| N9 基线下调 | 260→256 / 76→72 / 78→77 | 数字属实但**非全部本卡贡献**：基点 c94afbe4 探针实测实际值已 258/73/77（基线早已陈旧），本卡净降 = arb 258→256、bareCatchVar 73→72、catchVarToString 77→77（0）；详见 §1 | **部分（条件 C-2）** |
| 全量分母 | +3104 / ~23 skipped / 0 failed | `/tmp/u12_full_test.log` 亲验：**恰 23718 行**（与声明一致），尾行 `+3104 ~23: All other tests passed!`、`EXIT:0` | 一致 |
| analyze 零 issue | No issues found! | 亲跑：**No issues found! (7.6s)** | 一致 |
| arb 勘误可再生 | gen-l10n 逐字可再生 | `flutter gen-l10n` 亲跑后 `git status mobile/lib/l10n/` **零输出=逐字节一致**（已复原） | 一致 |
| 拦截器带键 | 移动端仍随请求带 X-Idempotency-Key | `idempotency_interceptor.dart:16-17` 亲证 | 一致 |
| 引擎忽略该键 | IdempotencyMiddleware PROTECTED_PATHS 不含 redeem-pro | `backend/app/api/middleware.py:51-57` 亲证（PROTECTED_PATHS 仅 chat/tasks/plans/events） | 一致 |
| 商店旗 | RELEASE_ENABLE_SHOP=False | `backend/app/config/settings.py:144` 亲证 | 一致 |
| worktree / 合并 | clean；与 main 可并 | clean 亲验；`git merge-tree --write-tree a7eb52b0 main`（main=3bd1cec6）**零冲突**；详见 §6 | 一致 |

## 1. 靶一：N9 棘轮基线下调归属（最重靶）——**无检测弱化；下调全部对应真实泄漏关闭；但归属表述不成立（条件 C-2）**

**逐处 diff 核（baseline JSON ±14 行全部处置面）：**

| 基线条目变动 | 归属 | 性质 |
|---|---|---|
| `leaderboardSelfAnchorLoadFailed` ×2（zh/en arb）删除 | **本卡**（arb 占位删除亲证 diff） | 真实泄漏关闭（占位通道关闭，非删规则） |
| `self_anchor_screen.dart` 条目删除（bareCatchVar -1） | **本卡**（调用面改无参 getter + debugPrint 亲证） | 真实泄漏关闭 |
| `learningModeSaveFailed` ×2（zh/en arb）删除 | **开卡前**（`a29ed3f1` V3-FIX-490 删 learning-mode 孤儿屏+独占键，`git merge-base --is-ancestor` 证为 c94afbe4 祖先） | 真实泄漏关闭（整链删除） |
| `learning_mode_screen.dart` 条目删除（catchVarToString -1） | **开卡前**（同 a29ed3f1） | 真实泄漏关闭 |
| `understanding_overview_view.dart` bareCatchVar 6→3 | **开卡前**（该文件最后改动 01e63308=U03 时代，非本卡 diff） | 真实泄漏关闭 |

**守卫脚本 `check_n9_raw_exception_leak.py` 零改动**（不在 diff 文件清单）——三检测维度（arb 占位/l10n 实参/assignment face）与正则原样，棘轮"只罚上升"语义原样：**无任何检测面弱化**。

**决定性实测锚**：基点 c94afbe4 临时 worktree 探针（已删）跑旧基线守卫 → `arb 258/260, bareCatchVar=73/76, catchVarToString=77/78 PASS`——开卡时基线就已陈旧（260/76/78 为注册点 a025e82a 的历史值），且 **U11 receipt §0 同样记录了 258/260、73/76、77/78 PASS**（U11 审查时点即已实测在案）。本卡 `--update-baseline` 按守卫协议把基线同步到磁盘真值，陈旧差量（arb -2 / bareCatchVar -3 / catchVarToString -1）随卡导入——这是工具固有行为，任何后续 cleanup batch 都会触发同样导入。

**判定**："260→256/76→72/78→77 基线随卡下调"的**数字为真、性质为真（每一格都是真实泄漏关闭）、协议为真**；但把这些数字整体记在本卡勘误名下**不成立**——本卡净贡献是 `258→256`（arb）与 `73→72`（bareCatchVar），catchVarToString 净降为 0。证据四处文案（diff doc §2-②、run_manifest cmd#9、test_results guards、卡库自述）均未分解 → **条件 C-2**。

## 2. 靶二：幂等双闸——服务端闸真证；客户端守卫实现正确但其专属测试不可失败（条件 C-1）

- **实现面亲核**：`_actionInFlight` 同步 check-and-set 无 await 缝隙、`finally` 释放、取消（confirmed≠true）即释放；与既有 `_redeeming`（确认后网络窗）+ `capped`（`_lastResult.ok` 封口，既有逻辑非本卡新增）三层叠加。代码正确。
- **mutation 亲放（审查靶 2 明确要求，结果为阴性）**：删除守卫体后重跑 `photon_redeem_idempotency_u12_test.dart` → **5 用例全绿**。三组探针（均用后即删）坐实根因：
  1. 普通 InkWell 同帧双 `tester.tap` → **两击都命中**（tester 分派语义无问题）；
  2. 第一击触发 `showDialog`/路由 push 的场景 → **第二击在 hit-test 层被框架吞掉**（计数探针 1 次）；
  3. mutant 屏上加打印 → 同帧双击 `onRedeem` **仅触发 1 次**——第二击从未到达回调，守卫分支从未被执行。
  结论：**"同帧双击只开一个确认面"的行为断言为真，但它证的是框架同帧吸收行为，不是 `_actionInFlight`**。测试注释"重入守卫吞掉第二次"归因错误；该守卫当前为零有效测试覆盖。真实设备上对话框 barrier 一帧后即起，守卫的独特保护窗（同帧/亚帧窗口）本身极窄——属防御纵深，不减损验收 2。
- **验收 2 幂等的真证据在服务端**（亲跑 3 passed）：月顶重复请求同结果且状态收敛不双扣（snapshot 相等断言）；8 并发恰 1 OK / 7 monthly_cap、余额恰扣一次、恰 1 条 redeem 流水、权益不叠加双倍。断言强度充分。
- **X-Idempotency-Key 归属**：引擎忽略该头属实且已在 limitations #2 + CH-1 如实披露；本卡按 path_policy 不扩引擎保护面（契约归单一 owner）合规。移动端拦截器继续带键（未来接入零客户端改动）亲证。

## 3. 靶三：验收三条断言强度（逐条独立下判）

1. **全站榜不恢复 + flame_level 不冒充付费身份**：COMM-LB 守卫亲跑 PASS；路由词表钉（`LeaderboardRoutes.routes` 恰 1 条 self-anchor + 域内零全站榜词，注释豁免亲核）；flame_level 分离钉（四家族零 flameLevel + 全 mobile 零 entitlement×flameLevel 同行）亲跑绿；引擎红线亲证（`users` 表 `entitlement` 独立列注释「'free' | 'pro'，V3-FIX-02/D17 冻结」紧邻 flame_level 列）。词表扫描的绕过残留（CH-5 自我披露）在零动态路由构造库内可接受，服务端 entitlement 列构成真源兜底。**成立**。
2. **真账本 + 幂等**：server-first 判别钉亲跑绿（4321/1777/9 上屏、1500/7 不上屏、`redeemCalls==0`）；`balance_after 2544` 上屏钉（服务端值非本地减法口径）；幂等=服务端屏障（§2 亲跑）+ 客户端守卫（实现正确、测试效力见 C-1）。**成立**。
3. **庆祝可关 + 纠正/隐私不收费**：庆祝正反判别对是真 mutation 对（同弹窗仅切 `EmotionResponsiveConfig` 档位，亲跑绿）+ `SparkleConfetti` 低刺激整体短路机制源码亲证（build 期缓存抑制位，播放路径整体短路）；付费墙反例钉亲跑绿（memory 域零 photon/purchase/entitlement/付费词表 + `/memory/provenance` 免费链路正锚）+ 引擎侧 memory API 零 photon 引用亲证（grep 零命中）+ 扣减面亲证仅 photons.py:215（admin）/photon_redeem_service.py:289（redeem-pro）/achievement_engine.py:3364（契约押金）三处。**成立**。

## 4. 靶四：HIDDEN 商店钉与 B01 portfolio 语义一致——**一致**

- 钉亲跑绿（奖励域四目录零 `ShopRoutes`/`'/shop'`）；全仓引用面亲证仅 `app/routes.dart` + shop feature 自身（与 diff doc §卡面表一致）；`RELEASE_ENABLE_SHOP=False`（settings.py:144）。
- `v4/01_product/MODULE_MATRIX.md:38`：`|shop|HIDDEN|维持HIDDEN；不为像素装扮重新开放未批准交易。|V4-U12|`——矩阵行明确归属本卡，本卡"钉零入口、不撤路由"与矩阵处置一致；撤路由属处置变更（limitations #7 如实登记）。
- S09_delta_report:40 与 **B-01 RECEIPT §3.4/E11 同口径**（不可达面内按钮不构成用户可达入口）——U12 钉与 B01 portfolio 语义同源一致。

## 5. 靶五：测试质量与数字

- **14 计数分解**：5+3+6=14，逐用例名单与 test_results.json 一致，亲跑全绿。
- **3104 分母**：日志文件亲验恰 23718 行、尾行 `+3104 ~23` + `EXIT:0`——分母与终态属实。
- **首跑 -3 归因**：首跑日志未留存（无法直接复验），但复跑日志完整同码全绿、失败例名（q03_visual_qa_longtail tearDownAll）与 U11 已登记先例同型（limitations #8）、该域本卡零触碰。归因可信度中上；**integration_reverify（receipt 已预登记：集成 SHA 复跑全量+三守卫+后端 23）为兜底**。接受，不入条件。
- **arb 勘误合规**：修改非纯新增，U11 先例亲证（`36e722ad` 合并信息「勘误 arb 6 键」+ U11 receipt「errata_recheck 一审勘误 3/3 复核属实」）；本卡键名保留、零新增零删键、gen-l10n 逐字节可再生亲证、唯一调用面（self_anchor_screen）grep 亲证、既有前缀断言回归绿（67 回归含 self_anchor_screen_test 4 用例）。

## 6. 靶六：合并落差与树态

- `c94afbe4` 是 main 祖先（亲证）；main 现头 `3bd1cec6`（协调者所给 `768f8c39`=「V4 心跳#22」在其历史中，信息略滞后不构成落差）。
- base→main 间 3 个代码提交（P01 nudge/spine）与 U12 diff **零文件交集**；main 对 `tasks.json` 的改动（P01 条目）与 U12 条目不同行——`git merge-tree --write-tree a7eb52b0 main` **零冲突**（干净树 `a7650c56`）。
- pkill 披露（波及 wtS02/wtU02 并行会话）不影响本树态：审查首尾两次 `git status --porcelain`=0 行亲验。

## C. 裁决与条件（APPROVE_WITH_CONDITIONS）

三条验收均成立（证据见 §3），实现差量真实且小、零触碰面自证核实、无检测弱化、无契约违例。以下两条**不阻塞验收、须随收口或下卡修正**：

- **C-1（测试效力）**：`photon_redeem_idempotency_u12_test.dart` 双击钉须二选一：(a) 改造为守卫真实可达的钉（如经 `tester.state<_PhotonRedeemProScreenState>` 直调 `_redeem()` 两次跨微任务窗口，使 `if (_actionInFlight) return` 分支被执行并可证伪）；或 (b) 保留现测试但修正归因口径——登记守卫为「防御纵深、无独立可失败测试钉」，并改正测试内注释「重入守卫吞掉第二次」的失实表述。幂等验收主张继续由服务端屏障承担。
- **C-2（证据归属勘误）**：diff doc §2-②、run_manifest cmd#9、test_results guards 三处（及对外自述）的「N9 棘轮 260→256/76→72/78→77」须分解为「本卡净降 arb 258→256 / bareCatchVar 73→72 / catchVarToString 77→77（0）+ 开卡前已修复的陈旧基线导入 arb -2 / bareCatchVar -3 / catchVarToString -1（a29ed3f1 等，U11 receipt 已实测在案）」。

建议（不阻塞）：X-Idempotency-Key 引擎侧缺口目前仅口头登记于 CH-1/limitations #2，建议按「契约归单一 owner」流程进 KNOWN_CODE_DEBT_LEDGER 或契约台账显式登记。

## 复现命令锚

- 14 用例：`cd mobile && flutter test test/features/photon/presentation/screens/photon_redeem_idempotency_u12_test.dart test/features/leaderboard/presentation/screens/self_anchor_boundary_u12_test.dart test/widget/rewards_family_boundary_u12_test.dart`
- 后端抽验：`cd backend && SECRET_KEY=test <venv-python> -m pytest tests/unit/test_dcomm2_photon_redeem_pro.py -k "monthly_cap_blocks_second_redeem_and_converges or concurrent_redeem_exactly_one_success or transfer_in_excluded_from_redeemable_base" -q` → 3 passed
- N9 归属分解：`git merge-base --is-ancestor a29ed3f1 c94afbe4`；c94afbe4 临时 worktree 跑 `check_n9_raw_exception_leak.py`（实测 258/260、73/76、77/78 PASS）
- 合并落差：`git merge-tree --write-tree a7eb52b0 main` → 零冲突
- 分母日志：`grep -c "" /tmp/u12_full_test.log` = 23718；尾行 `+3104 ~23 ... EXIT:0`
