# J-02 Simulator 证据 · 门后执行手册（runbook）

- 预备卡：wt784 J-02PREP（只写不跑）｜base：main@`e36fe444`｜分支 `agent/node-b/wt784/j02prep`
- 执行时点：**day7 终门（2026-09-28 08:00）之后**，由持模拟器/设备会话机械执行
- 验收权威：`v3/07_tasks/tasks.json` id=J-02（本文件 §7 逐条映射）+ `v3/01_product/FIRST_3_MINUTES.md`「Automated simulator acceptance」清单
- 销账缺口唯一来源：wt772 receipt（`v3-output/WT772-J02-REVIEW/receipt.md` §6-1）——simulator 实测证据
- 配套：`first3minutes.sh`（编排骨架，DRYRUN 默认安全）、`checklist.md`（证据三列映射）

---

## 0. 本卡补什么（一句话）

在 integration HEAD 上，对真实运行栈实跑「fresh install → ≤3min 到 useful action」与「guest 种子不进真实 Memory」「注册/游客/升级三端 session 稳定」，产出秒表数据 + 截图序列 + DB 探针 + run manifest，存入 `v3-output/WT784-J02-SIM/`。

---

## 1. 设备前置（哪台、什么镜像/环境）

### 1.1 通道选择（按本机已证事实排序）

| 优先 | 通道 | 依据 | 限制 |
|---|---|---|---|
| **主** | **macOS desktop**（darwin-arm64，`flutter test -d macos` 集成测试） | J-01 已证全要素可跑：真实渲染帧 + 真实后端 + 墙钟秒表 + 引擎帧截图 ×5 persona（`v3/09_evidence/j01_first3/REPORT.md`） | 严格说是桌面通道非"模拟器"；若 fleet owner 要求字面 iOS/Android 模拟器，见 1.2 |
| 备选 | iOS Simulator（xcrun simctl + `scripts/mobile/ios_*.sh`） | 仓库已有 boot/install/screenshot 脚本 | **无 UI 步进驱动先例**；需补 integration_test 驱动（复用主通道同一份 dart 驱动即可，`-d` 换模拟器 UDID） |
| 备选 | Android 模拟器（journey harness android driver） | B-03 有 boot+install+launch+logcat+截图先例 | harness android 通道**仅最小壳，UI 步进未接入**（GJ01 journey 注明"待无障碍驱动接入"）；走 integration_test 驱动同上 |

**执行原则**：主通道先出全要素证据；若 fleet owner 指定必须模拟器通道，用同一份 dart 驱动换 `-d` 目标，UI 步进逻辑不变。**不因换通道重写旅程**。

### 1.2 环境清单（主通道，J-01 2026-09-25/26 同款）

```
Flutter 3.41.3（本机共享 SDK；注意 B-03 记录的 dartaotruntime 断链前科，开工先 flutter doctor -v）
Xcode + macOS desktop enabled（flutter config --enable-macos-desktop 已开）
Go gateway  :8080 healthy   （curl -s http://localhost:8080/health）
Python 引擎 :8000 healthy   （curl -s http://localhost:8000/health 或 /docs）
gRPC        :50051          （gateway 桥接依赖；由 make grpc-server 承载）
docker      sparkle_db / sparkle_redis / sparkle_minio up（make dev-up）
```

worktree 一次性 setup（gitignored 产物，不入 patch，J-01/B-03 同法）：

```bash
make proto-gen            # 生成 gen/（gitignored 编译依赖）
printf '#include "ephemeral/Flutter-Generated.xcconfig"\n' > mobile/macos/Flutter/Flutter-Debug.xcconfig
printf '#include "ephemeral/Flutter-Generated.xcconfig"\n' > mobile/macos/Flutter/Flutter-Release.xcconfig
```

### 1.3 运行栈注意

- 本卡证据是**唯一允许且必须触碰运行栈**的 J-02 环节（门后）；预制包阶段（wt784）未触碰。
- 账号全部用时间戳后缀唯一名（`j02px1<ss>` 形制，J-01 同法），不碰既有账号。
- **禁触清单沿用舰队纪律**：不 push；不改 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`；不碰 `/tmp/northstar_ns001_real_drive_state.json`。

---

## 2. Fresh install 步骤

### 2.1 语义定义（三选一按通道，manifest 记录用了哪种）

| 通道 | fresh install 操作 |
|---|---|
| macOS desktop | dart 驱动进程启动前 `FlutterSecureStorage.deleteAll()` + `SharedPreferences.clear()`（`first3_measurement_test.dart` `wipeLocalState()` 同款）；**own-goal 每 persona 一条独立进程 = 真·cold start** |
| iOS Simulator | `xcrun simctl uninstall booted <bundle_id>` 后 `simctl install`（bundle id 以 `defaults read $(pwd)/build/ios/iphonesimulator/Runner.app/Info CFBundleIdentifier` 为准，**不猜**） |
| Android | `adb uninstall <pkg>` 后重装（pkg 以 `aapt2 dump badging app-release.apk` 解析，**B-03 教训：不猜包名**；gradle 默认 `com.example.sparkle`，B-03 实跑曾见 `com.sparkle.app`） |

### 2.2 构建命令（执行时才跑；预制阶段未执行）

```bash
# 主通道（无独立 build 步——flutter test -d macos 直接编译运行）
cd mobile && flutter test integration_test/j02_fastpath_journey_test.dart -d macos \
  --dart-define=J02_PASS=<0..4|all> \
  --dart-define=J02_SHOT_DEST=<worktree>/v3-output/WT784-J02-SIM/evidence/<run_id>/screenshots

# iOS Simulator 备选（构建一次，重装覆盖安装前先 simctl uninstall）
flutter build ios --simulator   # 或 flutter run --debug 安装态
bash scripts/mobile/ios_boot.sh "iPhone 16" && bash scripts/mobile/ios_install.sh
```

**前置缺口（如实声明）**：`integration_test/j02_fastpath_journey_test.dart` **当前不存在**。既有 `first3_measurement_test.dart` 是 J-01 的 goal-wizard 路线（`和 AI 定目标`→`GoalCreationWizardScreen`），**不覆盖 J-02 快车道**（resume 卡 → persona 步1 → `j02-fast-path-cta` → modeling skip → FirstActionCard）。执行会话第一件事是按 §3 脚本编写该 dart 驱动（红→绿形制，产品代码零改动，J-01 驱动同构：`J01_MARK`→`J02_MARK`、`textAny`/`waitUntil`/`safeSettle`/`shot` 辅助函数直接照搬）。

---

## 3. 3 分钟价值旅程脚本（逐步骤 + 预期画面 + 截图时点）

文案事实全部取自当前 main 代码（arb 键 + widget key 实证，见括号）。每步耗时打点 `J02_MARK pass=<PX*> leg=<leg> mark=<step> ms_since_pass_t0=<n>`。

### Leg R —— 注册端 fresh user（主判据：≤3min 到 useful action）

| # | 动作 | 预期画面 | 截图 | 判据/风险 |
|---|---|---|---|---|
| R0 | 冷启动（wipe 后 `app.main()`） | splash → 登录屏；标题 + `welcomeSubtitle`，登录主按钮**无滚动可见**（`login_screen.dart:194-200`） | `01-first-surface.png` | FIRST_3_MINUTES「首屏 primary CTA 无滚动可见」；冷启动→首屏 J-01 实测 9.5-23s |
| R1 | tap `还没有账号？`（`login_screen.dart:345`） | 注册屏（4 字段 + 2 同意 tile） | `02-register.png` | 链接在折叠线下，J-01 记录 tap flaky，重试 ×3 并以 `确认密码` 字段出现为准 |
| R2 | 顺序填 username/`j02px<i><ss>`/email/password/confirm + 勾 2 个 CheckboxListTile | 表单满 | `03-register-filled.png` | 密码 `J02-Passw0rd!`；勾 tile 整行命中（J-01 教训） |
| R3 | tap `注册` 提交（**SparkleButton 祖先过滤定位**，AppBar 标题同名陷阱） | **落 /home 软墙**（非旧 GJ01 的 persona 步0！），Dashboard + `OnboardingResumeCard`（标题"完成引导，让 AI 更懂你"，CTA `继续引导`）可见 | `04-home-softwall.png` | router_smoke 钉的软墙语义；**V4-U06 裁决回填（2026-09-30）**：注册无待发请求 → 落点必须 /home，落「我的」= 规则违规计入 failures（`post_register_rule_ok`；FIX-541 移动端两腿已修 commit 1617feb1，原 wt802 6/7 落「我的」反例由 widget 级 `guest_upgrade_landing_route_test.dart` 冻结）；**风险 O3 残留**：J-01 曾 7 runs 桌面 tap 无效零反馈——若复现，走 §6 fallback（API 注册 + UI 登录）并在 manifest 如实记 `register_ui_bounce=true`，证据仍有效但口径降级 |
| R4 | tap `继续引导`（OnboardingResumeCard CTA，`dashboard_screen.dart:1156`） | persona 引导屏步 1（学习目标输入） | `05-persona-step1.png` | 草案恢复语义：新号无草稿，直接步 0 |
| R5 | 输入目标文本（如 PX1「两周内做出一个可展示的算法可视化比赛作品…」） | 目标非空后快车道 CTA **`先拿第一步行动`**（`ValueKey('j02-fast-path-cta')`）+ 一行 hint 出现 | `06-goal-typed-fastpath.png` | 判据：空目标时 CTA 不在（wt764 快车道测试①）；hint 文案含"只回答目标这一个问题" |
| R6 | tap `先拿第一步行动` | 进入 modeling 访谈屏；**其余四问未问**（延后） | `07-modeling-deferred.png` | goal-only 载荷（仅 `learning_goal_type`+`learning_goal`）POST `/profile/onboarding`；`onboardingCompleted` 仍 false → resume 卡语义留存 |
| R7 | tap `跳过`（modeling 屏 ghost） | **按 V4-U06 裁决落点规则**：快车道（有待发请求 `post_onboarding_message`）→ 落 /chat（请求随行到目标对话）；无待发请求 → 落 /home（今天）。`FirstActionCard` 生成入口随后可见（落 chat 时经驾驶舱 tab 真实用户路径续行 R8） | `08-home-first-action.png`（或 `07b-post-skip-chat.png`） | 裁决=V4-U06（FIX-536/541 合并裁量："携带用户待发请求到目标对话，否则到该目标今天"）；skip 即 `onboardingCompleted=true`（wt764 §5 段6）；驱动断言已收紧（`post_skip_rule_ok`，违规计入 failures——2026-09-30 回填） |
| R8 | tap FirstActionCard 生成入口 | loading 反馈（**>500ms 必须有**）→ proposal 卡三字段 + `开始`/`不合适` | `09-action-proposal.png` | **秒表核：`t_action_ready - t_pass_start ≤ 180,000ms`**；LLM 推导秒级，失败有 503 诚实重试（wt371）——失败截图 `09b-action-error.png` 记失败不粉饰 |
| R9 | tap `开始`（确认 proposal） | 确认态 | `10-action-confirmed.png` | useful action 定义终点 = proposal 确认 |

**Leg R 通过**：R0-R9 全步达成 且 R8 秒表 ≤180s 且全程无空白错误页。`t_pass_start` = R0 冷启动进程起点（真墙钟，fullyLive）。

### Leg G —— 游客端（seed 不进真实 Memory + session 稳定）

| # | 动作 | 预期画面 | 截图 | 判据 |
|---|---|---|---|---|
| G1 | 登录屏 tap `以访客身份继续`（`continueAsGuest`） | 种子 home（J-01 实测 ~2-3s 到 Dashboard） | `11-guest-home.png` | session 稳定：不落入 persona 引导循环 |
| G2 | 观察示例声明 + 种子目标可见性 | 种子内容（如"期中冲刺"）可见；**示例标识现状大概率缺失**（J-01 O1：`declared_example_marker=false`） | `12-guest-seed-scan.png` | 如实记录标识有无——缺失本身是测量数据非执行失败 |
| G3 | 与种子 demo 内容对话一轮 | 回复正常 | `13-guest-demo-chat.png` | demo 轮不进记忆 lane（V3-FIX-258 短路） |
| G4 | **DB 探针**（只读 psql，见 §5.2） | `memory_goals`=0 行 ∧ `episodic_memories`=0 行（该 guest uid）∧ `users.registration_source='guest'` | `db_probes.jsonl` | **acceptance「seed 不进入真实 Memory」的活栈级证据**（wt764 后端 pin 的实机对应面） |

### Leg U —— 升级端（三端 session 稳定第三角）

| # | 动作 | 预期画面 | 截图 | 判据 |
|---|---|---|---|---|
| U1 | guest 态 tap 升级转化入口（GuestConversionCard / 注册升级链） | 注册/升级表单 | `14-upgrade-form.png` | V3-FIX-205 已修升级 token 降级（原「重试撞已存在」家族）——本 leg 是修复后首个实机走查机会 |
| U2 | 完成升级提交 | **原位翻转**：仍在本会话（不被登出/弹登录），身份变注册 | `15-upgraded-session.png` | session 连续性 = GJ02 转正事务语义；DB 探针 `registration_source` 已翻转 |
| U3 | 升级后直访 persona 引导路由 | **保持可达**（供补完延后问），resume 卡承接 | `16-upgraded-persona-reachable.png` | router_smoke 升级端用例的实机对应面 |

### 5 Persona 差异化（FIRST_3_MINUTES「不出现相同模板化 action」）

- 5 个目标文本取 `first3_measurement_test.dart` personas 常量（PX1 比赛/PX2 科研/PX3 作品集/PX4 课程/PX5 Creator），own-goal 每 persona 一条独立进程（真 cold start）。
- 判据：5 份 `09-action-proposal.png` 的 proposal 三字段**两两非同文**（截图对 + proposal 文本留存 `proposals.json`）。J-04 后端差异化断言已存在，本步是 UI/观感对应面（wt772 §6-1 口径）。

### Loading/错误横切断言（全程）

- 任一 wait 超时 → 当场截图 `9x-<step>-timeout.png` + TEXTDUMP（J-01 `dumpTexts` 同款）。
- 断言「错误不回空白页」：任何错误面必须有可见文案/SnackBar/错误卡（R8 失败重试面、注册失败面均按此核）。

---

## 4. 秒表与计时产物

- 打点形制沿用 J-01：`J02_MARK pass= leg= mark= ms_since_pass_t0=` + 进程末 `J02_SUMMARY {json}` 落盘 `j02_timings.json`（含每 pass 的 `t_first_surface_ms / t_register_done_ms / t_action_ready_ms / total_ms / clicks / failures`）。
- 判读脚本：`first3minutes.sh` 的 `verdict()` 用 python3 对 180,000ms 判定，逐 pass 输出 PASS/FAIL。

---

## 5. DB 探针（只读）

### 5.1 连接

```bash
docker exec sparkle_db psql -U postgres -d sparkle -tAc "<SQL>"
```

### 5.2 探针 SQL（join 列名执行时先 `\d memory_goals` 校准——预制阶段未连库，此处按 wt764 测试所引表名写模板）

```sql
-- G4-a：guest 种子不进真实 Memory（<USERNAME> 换该 leg 实际 guest 名）
SELECT count(*) FROM memory_goals mg JOIN users u ON mg.user_id=u.id
WHERE u.username='<USERNAME>';                        -- 期望 0
SELECT count(*) FROM episodic_memories em JOIN users u ON em.user_id=u.id
WHERE u.username='<USERNAME>';                        -- 期望 0
-- G4-b：身份面
SELECT registration_source FROM users WHERE username='<USERNAME>';   -- 期望 guest / U2 后 email
```

每条探针追加写 `db_probes.jsonl`：`{run_id, leg, sql_label, result, ts}`。

---

## 6. 失败时留证规则

1. **任何步 FAIL 不删 run、不重跑抹除**：落 `<step>-FAIL` 截图 + 当刻 TEXTDUMP + 全量日志；manifest 记 `status=FAIL` + 失败步（B-03 env-fix run 亦是证据的同款纪律）。
2. **注册静默弹回（O3 家族）**：截 `04b-register-bounce.png` + 记 `register_ui_bounce=true`，走 J-01 同款诚实 fallback（真实 register API 建号 → UI 登录；再不行 provider 登录并标 `instrumented`）——fallback 段不计入 ≤3min 秒表口径的主张，另列 `t_route_done_fallback`。
3. **新缺陷登记**：凡执行中新发现的真缺陷，自 **V3-FIX-533** 起（预制时点 grep 复核 533 空闲，最新已用 532）**只写 `notes.md`，不编辑 DYNAMIC_ISSUES.md**（编辑权归集成会话）。
4. 失败 run 与通过 run 同目录并存：`evidence/<run_id>/`（run_id 含时间戳，永不覆盖）。

---

## 7. 通过判据 ↔ J-02 acceptance 逐条映射

| acceptance / 清单项 | 本 runbook 判据落点 | 产物 |
|---|---|---|
| A1 fresh user ≤3min 到 useful action | Leg R 全步 + R8 秒表 ≤180s ×5 persona | `j02_timings.json` + 截图 01-10 序列 |
| A1b seed 不进入真实 Memory | Leg G G4 DB 探针双 0 行 + G3 demo 轮 | `db_probes.jsonl` + `11-13` 截图 |
| A2 注册/游客/升级三端 session 稳定 | R3 软墙 + G1 折回 + U1-U3 原位翻转/可达 | 截图 `04/11/14-16` + manifest |
| F1 fresh install / cleared state | §2.1 wipe 语义 + 每 persona 独立进程 | manifest `fresh_install=<>` 字段 |
| F2 首屏 primary CTA 无滚动可见 | R0 断言 | `01-first-surface.png` |
| F3 5 persona 非模板化 action | §3 差异化判据 | `proposals.json` + 5×`09` 截图 |
| F4 3 分钟脚本内到 Action | §4 verdict | `j02_timings.json` |
| F5 loading >500ms 有反馈 | §3 横切断言 | timeout 截图族 |
| F6 错误不回空白页 | §3 横切断言 + R8 失败面 | `9x-*.png` |
| F7 截图由视觉 Reviewer 按 rubric 打分 | 产物齐备后交独立 Reviewer（另卡/同人非本会话） | rubric 打分附于 review receipt |

---

## 8. 产物命名模板（post-gate 执行会话写入 `v3-output/WT784-J02-SIM/`）

```
v3-output/WT784-J02-SIM/
├── REPORT.md                          # 实跑报告（判据映射表逐条回填）
├── evidence/
│   └── <run_id>/                      # run_id = j02sim_<lane>_<yyyymmdd_hhmmss>_<hex4>（B-03 形制）
│       ├── run_manifest.json          # base/final SHA、lane、device、fresh_install 方式、起止时刻、status
│       ├── j02_timings.json           # J02_SUMMARY 汇总（秒表权威）
│       ├── steps.json                 # 逐步 PASS/FAIL
│       ├── db_probes.jsonl            # §5 探针逐条
│       ├── proposals.json             # 5 persona proposal 文本（差异化判据）
│       ├── screenshots/               # NN-<step>.png（§3 命名逐字）
│       └── logs/                      # flutter test 全量 stdout（J02_MARK 可对账）
```

## 9. 执行会话纪律（照抄卡面 Forbidden + 验收模型）

- 不用 mock/seed 冒充实测；失败如实记；不自勾验收框（Worker 只能报 READY_FOR_REVIEW / PARTIAL / BLOCKED）。
- 证据齐后由**独立未参与会话**审（含视觉 rubric 打分），引用 wt772 receipt `7bbaf092` 作为销账前置闭环。
- 完成后 `notes.md` 追加 §7 更正注记（wt772 receipt §6-4 要求的 wt764 计数更正）随销账申请一并处理。
