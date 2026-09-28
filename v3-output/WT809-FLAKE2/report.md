# WT809 · Flutter 负载敏感测试族第二批（FIX-548/549/550）报告

- 分支：`agent/wt809/flutterflake2`（worktree `/Users/brsama/code/GitHub/wt809`，base main@1f62b36c）
- 修复 commit：**c03fef07**（`fix(tests): wt809 Flutter 负载敏感测试族第二批 FIX-548/550`）
- 台账：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` 新增 548/549/550 三行（548/550 状态 FIXED@c03fef07；549 为调查行保持 OPEN）
- 任务来源：wt805 报告 `v3-output/WT805-FLAKEFIX/notes.md` §3 Flutter 候选清单，取 CI 红风险最高的 3 组
- 红线遵守：不 push；零产品码改动（`mobile/lib/` 未动）；零断言删除/跳过；gen/ 按先例本地拷贝不入库

## 0. 号分配表

| 号 | 组 | 目标 | 状态 |
|---|---|---|---|
| V3-FIX-548 | 组1 | `mobile/test/app/cold_start_release_test.dart` waitFor 真时钟 2s 预算 | FIXED@c03fef07 |
| V3-FIX-549 | 组2 | `mobile/test/widget/group_chat_index_shift_reparent_test.dart` Hive.close 3s 护栏 | OPEN（调查行：前提不成立，根因产品侧） |
| V3-FIX-550 | 组3 | `mobile/test/core/services/websocket_service_test.dart` + `websocket_service_reconnect_budget_test.dart` 四处 10s/3s 预算 | FIXED@c03fef07 |

548/549/550 连续分配；登记前 grep 复核全仓（v3/ v3-output/ docs/）与主干台账均空闲。

## 1. FIX-548（修，已闭）：cold_start_release_test waitFor 2s→30s

**根因**：`test/app/cold_start_release_test.dart` ②组（provider 层认证放行语义）三测共用的 `waitFor` 谓词轮询帮手，deadline 用真时钟 `DateTime.now()` 且默认预算 2s（L166-178）。三条等待（`isLoading==false`×2、`user!=null`）守的是真 `AuthNotifier` 启动链（token 读→isLoggedIn→getCurrentUser 场景仓）落定；全链 mock 内存态、健康路径微任务级（套件实测 ~1s），但这是 `test()`（无 fake-async），轮询与被测链都在真实事件循环上跑——CI 共享 runner 负载下事件循环饥饿可把 2s 吃穿，形成 FIX-544 同款「健康路径快、负载假阴性红」。wt805 定性「CI 负载敏感最典型」；且 `test/app` 在 CI（ci.yml flutter job）被 `flutter test --coverage` 与 Critical Smoke 两步双跑，暴露加倍。

**修法**（仅测试）：默认预算 2s→30s + V3-FIX-548 注释。相对等待成立即返回，健康路径时长不变；30s≈健康路径 30×，仍远小于 flutter_test 默认外层超时（`binding.dart:1939` `defaultTestTimeout = Timeout(Duration(minutes: 10))`，本地 SDK 亲证）。断言语义零改动：预算耗尽仍走 `expect(predicate(), isTrue)` 失败，不掩真回归。

**验证**：`flutter test test/app/cold_start_release_test.dart` 修前 1× 绿（基线）→ 修后 **3/3 全绿**（每次 `00:01 +5`，时长不变）；`flutter analyze test/app/cold_start_release_test.dart` No issues。

## 2. FIX-549（调查行，不修）：group_chat Hive.close 3s 护栏前提不成立

wt805 清单把 `Hive.close().timeout(3s)`（`group_chat_index_shift_reparent_test.dart:57` tearDownAll）列为「真窗」负载敏感。本次按卡先做复核，证据链推翻了前提，**已试改即回退，测试零改动**：

1. **护栏每跑必触发，不是偶发负载窗**。baseline（原样）复跑 2 次，tearDownAll 均恰在 00:01→00:04 之间收尾=3s 预算打满触发、TimeoutException 被空 catch 吞掉——即 `Hive.close()` 在本套件 3s 内**从不**完成。放宽 30s 后 3 跑 `00:31/00:31/00:32`，close 仍不落：**确定性悬挂（≥30s），非慢**。5/5 次预算全耗尽。
2. **预算放宽方向有害**：既然条件永不成立，3s→30s 只把每次绿跑的 tearDownAll 从 3s 拖到 30s（全量 CI 每跑 +27s 墙钟），flake 收益为零。改动已 `git checkout --` 回退。
3. **悬挂根因产品侧（红线外）**：`community_provider.dart:939/1350/1397` 加载/合并链经 `ChatCacheService.getCachedGroupMessages/saveGroupMessages` 打开并写 `group_messages_*` 箱，写链 fire-and-forget；`GroupChatScreen` 的 provider 初始化发生在 testWidgets 的 FakeAsync 域内，其真实 I/O 续延跨域被拆除后，`BoxBase.close() → keystore.close()`（hive 2.2.3 亲读）永久等待未完结事务 → `Hive.close() = Future.wait(各箱 close)` 悬挂。测试侧无解：`ChatCacheService` 是单例工厂（非 provider，无从 override），hive 无公开的箱枚举/事务弃置 API，无法按构造消除。
4. **wt805 记的 9/27 同族 CI 红（job 107905868267）与该护栏无关**：全量日志（`gh api repos/BRSAMAyu/Sparkle-project/actions/jobs/107905868267/logs`）复核，真红 = 本文件定位测试（wt359 修前旧版）line 143 `_expectOnScreen`「瞬态键定位未把目标消息滚入视口」——属装配缺陷，已由 wt359 `_pumpUntilLocateLanded` 装配修复版（先泵后查+24 帧有界收敛预算）消解，此后该文件未见 CI 红。
5. **遗留面**：同构 3s 护栏在同目录 `group_chat_search_locate_test.dart:42-43`（已红过的套件）同款存在；悬挂 close 的在途写收尾风险由产品侧修复一并消除。

**修法方向**（产品侧，派修队列）：ChatCacheService 增加测试可见的收尾 flush/close 钩子；或缓存写挂接可等待生命周期；或把缓存依赖改成 provider 缝隙供测试覆写为内存实现。

**验证**：回退后 `git status` 干净（仅 548/550 两文件入 commit）；期间所有改动版运行均绿（无假红引入）。

## 3. FIX-550（修，已闭）：websocket 两文件四处预算 10s/3s→30s

**根因**：`test/core/services/websocket_service_test.dart`（三连挂 10s、二进制帧首事件 3s）与 `websocket_service_reconnect_budget_test.dart`（6 级退避表走完 10s、三连挂 10s）的 `_waitFor` 是真环回 socket（`HttpServer.bind(loopback)`）上的谓词轮询——结构上已是 FIX-544 式相对等待（成立即返回、耗尽 `fail`），唯预算对负载敏感：三连挂每持 500ms+退避健康 ~2s、6 级退避表健康 ~4s+2.5s 观测窗，CI 负载下进程调度与 socket 遥操作可拖过 10s/3s。wt805 定性中风险；在全量 coverage job 上跑。

**修法**（仅测试）：四处预算 10s/3s→30s + V3-FIX-550 注释（仍在 flutter_test 默认 10 分钟外层超时内）。轮询语义不变，预算耗尽仍 fail，不掩真回归；各测试内的固定观测窗（2500ms「给 buggy 实现留继续拨号空间」、300ms 事件沉降窗）按原样保留——它们是「等待否定」窗，负载只会更长不会假绿，非本族风险面。

**验证**：两文件修前各 1× 绿基线 → 修后 **各 3/3 全绿**（service `00:05 +3`、budget `00:07~00:08 +2`，与健康基线同值不变）；`flutter analyze` 两文件 No issues。

## 4. 汇总验证矩阵

| 目标 | 基线 | 修后 3× | analyze | 备注 |
|---|---|---|---|---|
| test/app/cold_start_release_test.dart | 绿 00:01 | 3/3 绿 00:01×3 | No issues | FIX-548 |
| test/core/services/websocket_service_test.dart | 绿 00:05 | 3/3 绿 00:05×3 | No issues | FIX-550 |
| test/core/services/websocket_service_reconnect_budget_test.dart | 绿 00:07 | 3/3 绿 00:07/07/08 | No issues | FIX-550 |
| test/widget/group_chat_index_shift_reparent_test.dart | 绿（3s 护栏每跑打满） | 改动版 3/3 绿但 00:31（+27s/跑）→**回退不采纳** | — | FIX-549 调查行 |

台账体检：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`（输出全文见 §6，须人工读文本核对）。

## 5. 剩余候选（未动，供后续派卡）

- `test/core/network/token_refresh_coordinator_test.dart:552-561`：`_waitUntil` 默认 2s×5 处调用（L244/358/366/480 等）——同族低风险，单文件可一并放宽。
- `test/integration/full_stack_e2e_test.dart`（多处 10s 真网络栈）：集成面，建议结合 e2e job 的 CI 纳入情况单独评估。

## 6. 台账 verify 输出

`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` 原始输出（exit 0）：

```
verify：382 行 V3-FIX 行，裸管分布 {8: 382}，多数形态 8
deep 抽检（开启）：git 上下文 /Users/brsama/code/GitHub/wt809，rot 0 / hybrid 0 / phantom 1 / env 0
WARN：commit message（HEAD 前 200 条）引用 V3-FIX-473（如 31d4cf3d7b78）而台账全文无此号——幻影号（FIX-514 病）；历史 message 不可改写，仅登记不阻断
verify 通过：零冲突标记残留，8 裸管形态合法（多数容差开），ID 无重号，状态枚举合法，deep 抽检 warning 1 项（默认档不阻断）
```

人工读文本核对：382=379+本批 3 行；{8: 382}=新增三行 8 裸管形态全合法；rot 0=FIXED@c03fef07 主干可达；hybrid 0=549 调查行（OPEN 状态格）无 FIXED@ 混入；phantom 1 为 FIX-473 历史既有问题（wt807 报告同记），非本批引入、不阻断。

## 7. 环境注记

- 新 worktree 缺 gitignored `mobile/lib/gen/`，按 wt805/wt807 先例自主 worktree 拷贝（`cp -R` 主仓 gen/，27 文件；不入库）。
- flutter 3.41.3 stable（本机 homebrew）；`mobile/lib/l10n/*.dart` 为入库文件，本 worktree 已存在，未重新生成。
- CI 日志取证：job 107905868267 全量日志经 `gh api` 下载复核（本地 `/tmp/job107905868267.log`，未入库）。
