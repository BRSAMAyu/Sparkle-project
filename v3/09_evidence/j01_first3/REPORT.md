# J-01 REPORT — First 3 Minutes 当前体验实测与机会图

- 卡：J-01（stream JOURNEY，HEAVY，gate V3-1）｜worker：wt398｜worktree 分支：`wt398-j01-first3`
- base SHA：`c1efd8a65da961d657f42de1b2c1a71c5c89c2ed`（产品代码零修改；新增测量基建见 §6）
- 实测环境：macOS desktop（darwin-arm64，Flutter 3.41.3）集成测试真实渲染 + **真实后端**（gateway :8080 / engine :8000 healthy，sparkle_db/redis/minio up，2026-09-25/26 核验）
- 诚实声明：无移动真机/模拟器；无录屏（截图序列替代）；所有时间为 `DateTime.now()` 真实墙钟（fullyLive 真实渲染帧），无 fake-clock、无 pump 时长冒充、无拍脑袋数

## 1. 方法（实跑命令，可复现）

```
bash scripts/devtools/run_j01_first3_measurement.sh   # 一次性跑完全部
# 或逐 pass（own_goal：每 persona 一条独立进程 = 真·clean install）：
cd mobile && flutter test integration_test/first3_measurement_test.dart -d macos \
  --dart-define=J01_ROUTE=own_goal --dart-define=J01_PASS=<0..4> \
  --dart-define=J01_SHOT_DEST=<worktree>/v3/09_evidence/j01_first3/screenshots/own_goal
# example 路线（必须 DEMO_MODE 编译 flag —— 该依赖本身即发现 O5）：
flutter test integration_test/first3_measurement_test.dart -d macos \
  --dart-define=J01_ROUTE=example --dart-define=J01_PASS=all --dart-define=DEMO_MODE=true ...
```

- clean install 语义：每条进程启动前 `FlutterSecureStorage.deleteAll()` + `SharedPreferences.clear()`；进程内不做状态复用。
- persona：`v3/01_product/USER_SEGMENTS_AND_JTBD.md` 的 5 Builder persona。卡面所称 `persona.py "10 persona"` 实为 3 arc（stalled/deadline/completion）种子总体生成器，非 10 个命名 persona——按 JTBD 5 persona 抽 5 个并映射 arc：比赛→deadline、科研→stalled、作品集→stalled、课程→deadline、Creator→completion。
- 双路线：每 persona 先 **guest 腿**（零摩擦新用户现实），再 **own-goal 腿**（注册/登录 + 建自己的目标）。

## 2. 计时表（真实墙钟 ms，距各 pass t0；日志 J01_MARK 可对账）

### 2.1 Guest 腿（零摩擦新用户现实，5/5 一致）

| pass | persona | 冷启动→首屏 | 点访客→Dashboard | 种子假目标可见 | 示例标识 | own-goal CTA | 「解开卡点」CTA |
|---|---|---|---|---|---|---|---|
| pass0 | PX1 比赛 | 15,539 | 18,000 | ✅ | ❌ | ❌ | （截图可见） |
| pass1 | PX2 科研 | 9,917 | 11,996 | ✅ | ❌ | ❌ | ✅ |
| pass2 | PX3 作品集 | 23,115 | 25,950 | ✅ | ❌ | ❌ | ✅ |
| pass3 | PX4 课程 | 9,585 | 12,606 | ✅ | ❌ | ❌ | ✅ |
| pass4 | PX5 Creator | 10,075 | 12,294 | ✅ | ❌ | ❌ | ✅ |

**Guest 新用户在 12-26 秒内看到的是一个不属于他的「数据结构期中冲刺/二叉树遍历卡点」仪表盘**，无任何示例标识，且没有任何入口能表达自己的目标。

### 2.2 Own-goal 腿（注册/登录 → 向导 → 创建）

| pass | persona | CTA 可见 | 向导打开 | 意图提交→返回 | 意图结果 | 创建结果 | 路线总时长 | clicks |
|---|---|---|---|---|---|---|---|---|
| pass0 | PX1 | 101,518 | 102,304 | 109,883→110,018（**135ms**） | legacy 回退 | （v10 未捕获标记） | 244,669 | 18 |
| pass1 | PX2 | 95,246 | 96,034 | 103,628→103,755（**127ms**） | legacy 回退 | ❌ 创建失败 | 285,861 | 18 |
| pass2 | PX3 | 117,633 | 118,425 | 126,015→126,142（**127ms**） | legacy 回退 | ❌ 创建失败 | 313,966 | 18 |
| pass3 | PX4 课程 | 110,332 | 111,146 | 118,797→118,938（**141ms**） | legacy 回退 | ❌ 创建失败 | 302,661 | 18 |
| pass4 | PX5 | 97,043 | 97,885 | 105,470→105,586（**116ms**） | legacy 回退 | ❌ 创建失败 | 288,287 | 18 |

**头条结论：own-goal 全链路 245-314s，4/5 persona 超出 3 分钟预算**（其中含 UI 注册 37s 无效尝试与 instrumented provider 登录的降级时间——这正是 O3 摩擦的一部分，如实计入）。且即使走完，「创建」仍失败（O11）。

### 2.3 Example 路线（DEMO_MODE 编译 flag 强制开启）

- PX1 冷启动：Dashboard 12,540ms；扫描：`seeded_goal_words=true`、`declared_example_marker=false`、种子库入口无；星图/对话/社群/我的四 tab 均**无任何示例/种子入口**。
- PX2-PX5：UI 登出循环每 pass ~50s，重扫跳过（表面与 persona 无关，证据由 PX1 冷启动承载；如实记录）。
- 该 run `failures=[]`。结论：**即使开发者强制开 demo，产品也没有任何「示例体验」声明**——demo 与真实数据在第一分钟不可区分（O1/O5）。

## 3. 关键发现（第一分钟阻碍，全部可复现；全文见 [OPPORTUNITY_MAP.md](OPPORTUNITY_MAP.md)）

| # | 阻碍 | 严重度建议 |
|---|---|---|
| O1 | 新访客首屏被种入未声明演示目标（`guest_seed_service.py`），无示例标识 | P0（诚实性） |
| O10 | **AI 意图分析全量静默失效**：网关缺 `/goals/analyze-intent` 代理（404），引擎有路由（401）；客户端 catch-all 静默回退 legacy 表单；5/5 persona 116-141ms 回退 | P0（旗舰入口死亡） |
| O2 | Guest 被 O1 堵死 own-goal 入口（「和 AI 定目标」只在 noGoal 态出现） | P0（核心动作缺失） |
| O11 | 向导终点「创建失败」而同 payload API 直调 200 成功（307→`/goals/`）——客户端集成 bug | P0（最后一步破灭） |
| O3 | UI 注册提交桌面端无效且零反馈（7 次运行 × 3 种点击策略） | P0-待真机归因 |
| O5 | Example Mode 无用户入口，需编译 flag | P1 |
| O4 | 注册 API 拒绝保留域邮箱且报错为英文原始校验 | P2 |
| O6 | splash/登录文案绑定期末备考，排除 4/5 Builder persona | P1 |
| O7 | 本地状态清空后仍自动登录（keychain 残留） | P2 |
| O8 | 新访客首屏无来由 Lv.15/心境晴朗 | P1（可信度） |

## 4. example vs own-goal 分叉（实测）

1. 登录页：目标设计应有「开始我的目标 / 体验一个示例」双入口；现状无示例入口（O5）——分叉点缺失。
2. guest 线：登录即被种入未声明 example（O1），own-goal 不可能（O2）。
3. 注册线：无种子 → noGoal → 「和 AI 定目标」→ 向导（实测可达 `wizard_reached=true` ×5）。
4. **结论：当前 example 与 own-goal 不是用户可见的二选一，而是被 guest 种子静默决定**。

## 5. 证据清单与可证伪性

证据：
- 计时 JSON：`screenshots/{own_goal,example}/j01_timings_*.json`
- 全量日志（J01_MARK/TEXTDUMP/FINDING）：`logs/run_own_goal_pass{0..4}.log`、`logs/run_example.log`、`logs/passes_runner.log`
- 截图：`screenshots/own_goal/PX*/`（每 pass 首屏/登录/guest Dashboard/注册表单与结果/CTA/向导各步/创建失败 10-16 张）、`screenshots/example/PX1/`
- 复现 runner：`scripts/devtools/run_j01_first3_measurement.sh`；驱动：`mobile/integration_test/first3_measurement_test.dart`

真跑 vs 推断：
- **真跑**：§2 全部计时（墙钟差值）；种子/标识/CTA 可见性（widget 探测+截图双证）；意图分析 116-141ms 回退 ×5（后端真实交互）；网关 404 vs 引擎 401（curl）；创建失败文案 ×4（截图+标记）vs API 直调 200（curl `"first_task_id":"5f6abae1…"`）；UI 注册/登录 tap 无效（7 runs × 3 策略 + TEXTDUMP）。
- **instrumented（已标注）**：provider 登录（`provider_login_to_dashboard=true`）。向导腿起点因此非纯 UI 登录；CTA→向导→创建链路全部真实 UI tap + 真实后端。
- **推断**：O3 真机归因需人工复核；种子时序不稳定（run5 +14.6s 未现 vs run6/7 +12s 现身）根因未深查。
- **DEFERRED**：移动真机复测；录屏（截图序列替代）；O3 人手操作归因；种子时序根因。

## 6. 新增文件（测量基建；产品代码零改动）

- `mobile/integration_test/first3_measurement_test.dart`（新测试文件）
- `scripts/devtools/run_j01_first3_measurement.sh`
- `v3/09_evidence/j01_first3/`：本报告、OPPORTUNITY_MAP.md、PROGRESS.md、screenshots/、logs/
- worktree 本地环境修复（gitignored，不入库）：`mobile/macos/Flutter/Flutter-{Debug,Release}.xcconfig` shim、`make proto-gen` 生成物
