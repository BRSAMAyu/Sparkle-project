# wt288-dartfix-burn 卡报告（A 线/D 线·flutter analyze 基线烧减）

日期：2026-09-22 ｜ 分支：wt288-dartfix-burn（本地 commit `1cf52bf3`，未 push）｜ 基点：`43b23983`（main 尖）

## ① 烧减数字（核心交付）

**flutter analyze 总量：1014 → 1014 条不变按 severity 拆分后——INFO 3793 → 956（-2837，-74.8%）**，ERROR 42 → 42（持平），WARNING 24 → 16（-8）。预算文件 `quality/flutter_analyze_allowlist.json` 已刷新为新基线：`max_error 42 / max_warning 16 / max_info 956`，本地复跑 gate **exit 0 ✅**。

### 各 code 前/后对照（before = 昨日校准预算，after = 本卡实测钉值）

| code | before | after | | code | before | after |
|---|---|---|---|---|---|---|
| REQUIRE_TRAILING_COMMAS | 1130 | **0** | | UNAWAITED_FUTURES | 34 | 34 |
| DIRECTIVES_ORDERING | 422 | **0** | | UNRELATED_TYPE_EQUALITY_CHECKS | 31 | 31 |
| DISCARDED_FUTURES | 360 | 359 | | AVOID_DYNAMIC_CALLS | 29 | 29 |
| PREFER_CONST_CONSTRUCTORS | 318 | **0** | | UNDEFINED_FUNCTION (ERR) | 26 | 26 |
| CASCADE_INVOCATIONS | 309 | 309 | | PREFER_CONST_LITERALS_TO_CREATE_IMMUTABLES | 24 | 1 |
| PREFER_EXPRESSION_FUNCTION_BODIES | 283 | 11 | | USE_DECORATED_BOX | 16 | 0 |
| AVOID_REDUNDANT_ARGUMENT_VALUES | 187 | **0** | | OMIT_LOCAL_VARIABLE_TYPES | 15 | 0 |
| UNNECESSARY_IMPORT | 93 | **0** | | PREFER_FINAL_LOCALS | 14 | 0 |
| USE_BUILD_CONTEXT_SYNCHRONOUSLY | 86 | 86 | | NOOP_PRIMITIVE_OPERATIONS | 14 | 0 |
| ALWAYS_PUT_REQUIRED_NAMED_PARAMETERS_FIRST | 68 | **0** | | UNNECESSARY_LAMBDAS | 46 | **0** |
| SORT_CONSTRUCTORS_FIRST | 42 | 3 | | USE_IF_NULL_TO_CONVERT_NULLS_TO_BOOLS | 32 | **0** |
| UNNECESSARY_BREAKS | 32 | **0** | | PREFER_IF_ELEMENTS_TO_COND_EXPR | 29 | **0** |

**烧到 0 并从预算移除的 code 共 25 个**；其余机械项（SORT_CONSTRUCTORS_FIRST 42→3、PREFER_EXPRESSION_FUNCTION_BODIES 283→11 等）为 dart fix 可修子集，余量钉入新预算。dart fix 无能为力的语义类大项原样保留：DISCARDED_FUTURES 359、CASCADE_INVOCATIONS 309、USE_BUILD_CONTEXT_SYNCHRONOUSLY 86——这些是下一张卡的候选。

dart fix --apply 落地 **2555 处修复**（dry-run 清单 1837 处 + 级联；top：trailing commas 1047、expression bodies 206、const constructors 196、redundant args 143）。l10n 三个生成文件被 dart fix 重排，按卡指令 `git checkout -- mobile/lib/l10n/` 还原，未入库。gen/ 已拷入未提交（gitignored）。

## ② 改动文件计数

**602 文件（+2631 / -3507，净 -876 行）**：601 个 `mobile/**`（lib 253 + test 123 + tool 6 由 dart fix；另含 2 个 test 手修）+ 1 个 `quality/flutter_analyze_allowlist.json`。改动面零越界（`git status` 全程核对，无 mobile/quality 之外文件）。

### dart fix 引入的 2 个编译错误及手修（语义最小还原）

1. `test/shared/widgets/action_proposal/action_proposal_dual_mount_test.dart:52` — `prefer_const_constructors` 给含 spread 的 map 加 `const`，而 `proposalPayload` 已含同值 `'status'` 键 → const map 重复键编译错（EQUAL_KEYS_IN_CONST_MAP）。**修法**：摘除误加的 `const` + 注释说明（恢复原语义，代价 1 条 PREFER_CONST_LITERALS_TO_CREATE_IMMUTABLES info，已钉预算）。
2. `test/features/memory/presentation/widgets/understanding_overview_view_test.dart:21` — dart fix 删掉从未传值的构造参数 → `final bool withSource` 失去初始化（FINAL_NOT_INITIALIZED_CONSTRUCTOR）。**修法**：还原 `{this.withSource = false}`（代价 1 条 UNUSED_ELEMENT_PARAMETER warning，本就存在于旧基线 24 内）。

手修后 ERROR 回到基线 42（全部为预存的 `.mocks.dart` 缺失类：UNDEFINED_FUNCTION 26 + UNDEFINED_CLASS 10 + URI_DOES_NOT_EXIST 6，与旧预算完全吻合，属 build_runner 产物未生成，非本卡范围）。

## ③ 测试结果

### 定向测试（单文件单进程，--concurrency=1 串行，18 文件）

| 批次 | 文件 | 结果 |
|---|---|---|
| 手修验证 | understanding_overview_view_test | **+10 pass** |
| 手修验证 | action_proposal_dual_mount_test | **+4 pass** |
| accountability 链 | accountability_invite_flow_test | **+6 pass** |
| chat 链 | chat_notifier_stream_test / chat_screen_basic_test | **+8 / +24 pass** |
| task 链 | task_provider_test | **+29 pass** |
| 目录抽样 | a11y_contrast +8、app_event_stream_service +7、galaxy_contribution_banner +5、exam_sprint_setup_guard +2、main_pages_load_smoke +6、motion_reduce_motion +9、community_feed_cache +2、exam_sprint_dashboard_card +20、shop_provider +25、err_secondary +5、goal_detail_screen_a6_l10n +2、chat_area_budget | **17/18 pass** |

唯一红：`chat_area_budget_test.dart`（+0 -2，SharedPreferences 未 override）。**对比法判定为 HEAD 预存失败**：按 AGENTS.md 规以 `git clone <worktree> /tmp/wt288-baseline` 建干净基线（仅含 HEAD），同测试同败（+0 -2 同签名）；且失败路径（chat_screen initState:224 → guest_provider 的 sharedPreferencesProvider throw）在 dart fix diff 中零改动，测试 diff 全部语义等价（const/tearoff/默认参数/死代码）。基线克隆已删。

### 守卫与 gate

- `run_all_rule_guards.sh --jobs 4`（exit-checked）：**86/88 过**。2 红（AQ、BG）均为**环境性预存失败**——worktree 缺 backend `app.gen` 与 Go/Python 生成产物（本卡明令禁 buf/buf generate），两规则输入（backend/proto 生成物）与本卡 diff（mobile/** + quality/**）完全不相交，已隔离论证。L10N-PARITY 等 mobile 相关规则全绿。
- analyze gate 本地复跑新预算：`Analyze counts => ERROR=42, WARNING=16, INFO=956` → **✅ passed, exit 0**。

## ④ 资源峰值

- HEAVY 门遵守：测试批开工前轮询 swap，1215M ≥1.2G 放行；全程串行单实例，无模拟器/Gradle/浏览器。
- 实测区间：swap free 最低 847M（开工时邻卡负载，非本卡进程；当时本卡仅跑 LIGHT 的守卫）、定向测试阶段 swap free 稳定 1215M–1303M、load ≤4；未触发 500M 熔断线。
- 磁盘：开工 9.9G free，未产生大构建产物（flutter test 不落 build/ 目录于本次规模）。

## ⑤ 交接建议

1. **下一张语义烧减卡**：DISCARDED_FUTURES 359 + CASCADE_INVOCATIONS 309 + USE_BUILD_CONTEXT_SYNCHRONOUSLY 86 = 754 条，占新基线 79%——需要人工改 async 语义，dart fix 无能为力；建议按 feature 目录分卡。
2. **chat_area_budget_test 预存红**：B3-CHAT 批4 桥（wt160）在动 chat_screen initState 链，合入窗口时该测试的 ProviderScope 需补 SharedPreferences/guest 链 override——已由本卡基线克隆证明非 dart fix 回归，勿误判。
3. **AQ/BG 守卫环境债**：任何不跑 `make proto-gen`/buf 的 worktree 都会红这两条；建议守卫 runner 对生成物缺失给 SKIP-ENV 语义（而非 FAIL），避免每次人工论证。
4. **dart fix 两个已知反例模式**（若下轮再跑批量 fix 需先查）：含 spread 的 map 字面量 + prefer_const_constructors；未传值构造参数 + final 字段初始化依赖。可考虑在 analysis_options 对 test/ 降 prefer_const_constructors 级别。
5. **收工已清**：/tmp 基线克隆、/tmp 探针日志（dryrun/machine/guards/tests/fa.json 共 6 个 wt288-* 文件见下方清单，收工统一删）、worktree 内不落 build/.dart_tool。
