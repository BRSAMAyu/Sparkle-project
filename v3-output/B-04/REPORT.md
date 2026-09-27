# B-04 REPORT · V3 视觉基线截图与 L2–L5 Review Harness

- **Worker**: wt667（stream=BASELINE，HEAVY，卡 [B-04](../../v3/07_tasks/cards/B-04.md)，Gate V3-0）
- **Worktree**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt667-b04`（分支 `agent/node-b/wt667/b04`）
- **Base SHA**: `d7a961da`（`d7a961da5d28e5e238265cf56ff12703e79a6d88`，截图文件名中的 sha8 即此）
- **Final SHA**: 本 worktree 单提交（产品代码零改动，见 §5）
- **Status**: **READY_FOR_REVIEW**（自评不判 DONE；独立 reviewer 须至少复跑 §4.1/§4.2 两条命令并抽读 3 张 PNG）
- **环境现实声明**: 本机 flutter 3.41.3 + macOS 桌面 + Chrome，无 Android/iOS 模拟器运行段授权预算；按红线只做本机可用的 **flutter test golden 路径**，其余列运行级待验清单（§6），零伪造。

---

## 1. 交付物

| 交付 | 路径 |
|---|---|
| 视觉基线截图 ×27（9 canonical states × 3 viewport 批） | `v3-output/B-04/screenshots/{android__1080x2400@3.0, macos__800x600@2.0, macos__1280x800@2.0}/` |
| Baseline manifest ×3（sha256 事实源，PNG 改动可检） | `v3-output/B-04/manifests/manifest_{android__1080x2400@3.0, macos__800x600@2.0, macos__1280x800@2.0}.json` |
| 首轮视觉问题 ledger（A0/B3/C4 + 环境限制 2） | `v3-output/B-04/VISUAL_ISSUES_LEDGER.md` |
| 采集 harness（复用 Q03 链路，零新真源） | `mobile/test/goldens/b04_visual_baseline/{b04_harness.dart, b04_visual_baseline_capture_test.dart}` |
| 布局探针报告（27 条） | `v3-output/WT401-Q03-VISUAL/layout_probe_b04.json`（复用 Q03 落盘目录，suite 名 `b04` 区分） |
| states 注册表裁决修正 | `scripts/devtools/visual_baseline/states.py`（goal/chat 两条，见 §3） |
| Q03 pump 配方增量（可选参数，向后兼容） | `mobile/test/goldens/q03_visual_qa/q03_harness.dart` |

## 2. 卡面验收逐条对照

- [x] **至少核心 9 surfaces × 主要状态有 baseline；截图来自真实渲染**
  → 9/9 canonical states（states.py 注册表一比一）×3 viewport 批 = 27 张；全部经真实 `routerProvider` + `matchesGoldenFile` 渲染出图（Q03 同源配方），coverage 9/9。
- [x] **每张图有 build SHA/persona/state**
  → 命名走 B-04 naming.py GBNF：`<surface>__<state>__<persona>__<platform>__<viewport>__<sha8>.png`，文件名自证六元组；manifest 补 sha256/bytes/captured_at；sha8=d7a961da（真实渲染源码基）。
- [x] **输出首轮视觉问题 ledger**
  → VISUAL_ISSUES_LEDGER.md：A=0、B=3（home 叙事错误裸露 / chat 手机宽死区 / chat 桌面宽浮层叠压）、C=4、环境限制 2；12 维 rubric 逐面评分表在案。
- [x] Required evidence：base/final SHA（本文件）｜targeted tests（§4）｜integration/simulator evidence（golden 双跑 + §6 运行级待验清单）｜review receipt（**待 reviewer 独立签收**）。

## 3. 卡面/注册表与实际冲突的裁决（消费面亲证）

1. **goal 入口 `/goals` 不存在**：亲证 `mobile/lib/app/routes.dart` 及 GoalRoutes/TaskRoutes/MemoryRoutes——goal 仅有 `/goals/new`（创建）与 `/goals/:goalId`（详情，走 `/experience/goal-detail/{id}`，**无 demo 分支**）；目标库主视图实际 = `/plans`（SprintScreen，PlanRoutes.home，demo 数据在库）。states.py goal 条目 entry/definition 已改为 `/plans` 口径；goal 详情留待真机批次（需真后端）。
2. **chat 引用块非 demo 数据自带**：亲证 `demo_data_service.dart` demoChatHistory msg_1..11 均无 citations 字段；引用条渲染路径（ChatBubble→AssistantCitationStrip）要求消息带 `rawMetadata['citations']`。裁决：以 canonical fixture 注入一条 assistant 消息走真实渲染管线，states.py chat 条目已注记；采集测试内置 in-tree 断言（消息正文+引用标题两找不到即红——首轮曾红：构造期注入被 demo 历史 reload 冲掉，红测实证后改为加载后注入）。
3. **macos 批字形伪影（非产品缺陷）**：flutter_tester 无平台字体，macOS 目标语义下 ASCII 数字/Latin/个别汉字在部分 span 渲染为实心黑块（SFNS.ttf 注册后仍复现）；android 目标与真实 macOS 桌面（B-03 journey 实测）不受影响。登记为 B-04-ENV-1：macos 批只用于布局/层级审查，文字审查权威 = android 批 + 真机批次。
4. **U-09 SCREENSHOT_MATRIX 的 `/goals` 入口同步失效**：其权威口径已被 states.py 修正取代；真机批次执行时应按 `/plans` 入口（矩阵 45 行清单本身不改，执行注记见本报告 §6）。

## 4. 当场真跑证据（质量门）

### 4.1 采集 + 复验（golden 双跑确定性）
```
B04_VISUAL_CAPTURE=true flutter test --update-goldens \
  --dart-define=B04_BUILD_SHA8=d7a961da --concurrency=1 \
  test/goldens/b04_visual_baseline/         → +27 全绿（落 27 PNG）
B04_VISUAL_CAPTURE=true flutter test \
  --dart-define=B04_BUILD_SHA8=d7a961da --concurrency=1 \
  test/goldens/b04_visual_baseline/         → +27 全绿（比对复验通过）
```
确定性容差 0.5%（`B04TolerantGoldenComparator`）：卡面明确「不要求像素完全一致」；实测噪声源 = 消息时间戳分钟位（≈0.01%/224px）。真实回归（布局/文案）远超此界。
- 不设容差的默认 comparator 在首轮复验即红（0.01% 被拒）——红测先行留证于本会话执行记录。

### 4.2 manifest/verify/coverage 链（Python harness 复用）
```
visual_baseline.py manifest <批目录> …  → 3 份 manifest（各 9 条目）
visual_baseline.py verify  <批目录> …  → verify OK ×3（exit 0）
visual_baseline.py coverage v3-output/B-04/screenshots → 9/9 已采集（exit 0）
visual_baseline.py diff <android home> <macos home>    → verdict "similar"（0.072）
```

### 4.3 触达测试与静态门
| 门 | 结果 |
|---|---|
| B-04 采集套件 | 27/27 ×2 跑全绿 |
| Q03 邻域回归（共享 harness 被我改过） | 26/26 全绿（core+longtail） |
| flutter analyze（全量 mobile） | **No issues found**（0 error/0 info） |
| visual_baseline pytest | **48/48**（/tmp venv 装 pytest；系统 python3.14 无 pytest，如实记录） |
| states.py 注册表自检 | assert_registry_consistent 通过（9 条） |
| ruff/mypy | N/A（本卡零 backend 改动） |
| 治理守卫 | 未跑全量（本卡零产品代码、纯 test/docs 增量；`bash scripts/run_all_rule_guards.sh` 留给集成 HEAD 复核，不冒充已跑） |

### 4.4 并行卡避让（wt665 触点）
- 避开了 `chat_design_language_widgets.dart` 的 `ChatHistoryInlineError` 组件：本批 chat 面不渲染错误卡（demo 历史加载成功路径），零文件触点（git status 可证未改该文件）；引用 fixture 走 ChatBubble/AssistantCitationStrip 路径，与 wt665 hunk 无交叠。

## 5. 变更面（零产品代码）

```
mobile/test/goldens/b04_visual_baseline/          [新增] harness + 采集测试
mobile/test/goldens/q03_visual_qa/q03_harness.dart [修改] pumpQ03App 可选 viewport/platform 参数；
                                                        dispose 内复位平台覆盖（addTearDown 晚于
                                                        foundation 不变量断言，红测实证）；
                                                        SFNS.ttf 注册（ENV-1 缓解尝试，保留）
scripts/devtools/visual_baseline/states.py         [修改] goal/chat 两条裁决注记（§3）
v3-output/B-04/**                                  [新增] 27 PNG + 3 manifest + ledger + 本报告
```
产品代码（mobile/lib、backend、gateway）零改动——截图 sha8 锚定 base SHA d7a961da 即渲染源码基。

## 6. 运行级待验清单（交主会话，不伪造）

| # | 项 | 入口 | 阻塞什么 |
|---|---|---|---|
| 1 | 真机/模拟器 45 行矩阵（U-09 SCREENSHOT_MATRIX，android 真机+web 双宽+macOS 桌面窗） | U-09 §5 清单 + B-04 states.py 入口；goal 行按 `/plans`（§3-1 注记） | Gate V3-7「三端核心 golden journey」与跨端一致性签收 |
| 2 | goal 详情真后端采集（`/goals/{id}`） | 需 gateway+engine 活栈 + demo/真实账号 | goal 详情面视觉审查（本批以 /plans 库视图为该面基线） |
| 3 | chat 引用块真数据复核 | 真后端会话含真实 citations | fixture 注入版（本批）与真实引用渲染等价性确认 |
| 4 | galaxy 节点标签交互级审查 | 真机 tap/zoom 展开节点 | ledger B-04-L-06 的复核 |
| 5 | macos 文字级审查 | 真实 macOS 桌面 app（非 flutter_tester） | 规避 ENV-1 后的文字审查权威份 |
| 6 | 探针逻辑尺寸参数化（B-04-ENV-2） | q03_harness probeLayout 接受 viewport 参数 | off-bounds 信号在 macos 批精确化（下轮 harness 增量） |
| 7 | 独立 review receipt | reviewer 复跑 §4.1/§4.2 + 抽读 PNG | 卡面 Required evidence 收口 |

## 7. V3-FIX 台账
- 本卡**未新开 FIX 号**（grep 台账核实 356 为现占用上限；本卡发现均非「宣称/实现背离」类不诚实面——states.py 陈旧入口属文档精度，已在本卡内修正并留痕）。

## 8. 复现手册（后续 UI 卡按此 diff 闭环）
```bash
# 1) 采集（SHA 换新构建基）
B04_VISUAL_CAPTURE=true flutter test --update-goldens \
  --dart-define=B04_BUILD_SHA8=$(git rev-parse --short=8 HEAD) \
  --concurrency=1 test/goldens/b04_visual_baseline/
# 2) manifest + verify + coverage
python3 scripts/devtools/visual_baseline/visual_baseline.py manifest …
# 3) 改 UI 后重采集同 SHA 新目录 → visual_baseline.py diff / diff-manifest
# 4) 新 issue 按 VISUAL_ISSUES_LEDGER.md 格式续行
```
