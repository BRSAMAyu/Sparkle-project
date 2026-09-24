# WT328-CLINE-A — mobile C 线批 A：产品诚实性小簇（F-1 + F-10）

> 工号 wt328 ｜ 2026-09-25 ｜ 分支 `wt328-mobile-cline-a` ｜ 仅 mobile，未碰 backend/gateway/chat/cockpit

## 结论

| 项 | 状态 |
|---|---|
| 任务 1（F-1，major·debug-only）星图草稿 mock 回落切除 | **已完成** |
| 任务 2（F-10，minor）DailyContextLine 拼接缺空格 | **已完成**（修法与卡面预设不同，见下） |
| flutter analyze 门 | **PASS** — E0/W15/I598（allowlist 42/16/594，容差 ±5，`check_flutter_analyze_gate.py` exit 0） |
| 守卫 | **PASS** — `run_all_rule_guards.sh` 83 条 exit 0（拷入 gen 三件套后） |
| mypy 棘轮 1615 | **天然满足** — `git diff` 全部为 mobile 文件，backend 零改动 |
| 定向 flutter test | **DEFERRED** — 两次实测 swap free 923M / 899M，均低于 1.2G 启动门（单批吃 ~700M，923M 下运行将逼近 500M 熔断线），按内存纪律跳过执行；测试代码已随卡交付 |

## 任务 1 — F-1 星图草稿 mock 回落切除

**文件**：`mobile/lib/features/galaxy/data/repositories/galaxy_draft_repository.dart`

- 删除 `kDebugMode` 隐式回落整条路径：空结果（后端已正确返回 `{"drafts":[]}`）现在如实返回 `const []`，由既有空态 UI 呈现；`DioException` 如实抛 `Exception(_extractMessage(error))`。debug 构建不再渲染「OS.pdf 5 颗知识星 / 1 份待审核·5 颗星」假数据（wt324 实测 `G03_empty_graph.png`）。
- 演示数据仅剩**显式构造参数**一条路：`GalaxyDraftRepository(dio, {bool? demoMode})`，缺省跟随应用级显式开关 `DemoDataService.isDemoMode`（静态默认 false，与 galaxy_repository 等其余仓库约定一致），不再有任何 debug 魔法。移除了 `package:flutter/foundation.dart` 依赖。
- Provider（`galaxyDraftRepositoryProvider`）不改签名；`galaxy_draft_review_screen_test.dart` 的 `_FakeDraftRepository` 子类（`super(Dio())`）位置参数兼容，无需改动。

**新增测试**：`mobile/test/features/galaxy/data/repositories/galaxy_draft_repository_test.dart`
1. `{"drafts": []}` + `kDebugMode==true`（flutter test 环境即 debug）→ 返回空列表（钉死「debug 不偷换空结果」）；
2. HTTP 500 → 抛异常而非 mock；
3. `demoMode: true` 显式传入 → mock 可用（演示路径唯一且显式）。

## 任务 2 — F-10 DailyContextLine 拼接缺空格

**溯源结论（与卡面假设的偏差，重要）**：「先完成 Timedpracticeloop打破昨日零记录」这句**在代码库中不存在任何模板**——mobile 与 backend 全文搜索「打破/零记录/先完成+标题」均无命中。实际来源是 backend `growth_dashboard_service.py` 的 AI 生成行（`/growth/daily-context-line` → `_generate_daily_context_line_with_ai`，LLM 把任务名直接拼进中文散文），另有规则模板兜底但两者都带「」引号、与截图渲染（`wt324a，距期末还有118天，先完成 Timedpracticeloop打破昨日零记录。`，见 `U05_home_spine_middle.png`）不符。服务端 LLM 输出的拼接空隙客户端无法在模板层修；且 backend 属本卡禁区。

**修法（展示层排版归一）**：`mobile/lib/core/utils/text_rendering.dart` 新增纯函数 `autoSpaceCjkLatin()`——在 CJK 表意文字与拉丁字母/数字边界插入单个空格（已留空格的串不动，纯 ASCII/纯中文不动，标点邻接不动）；`DailyContextLine` 渲染前应用。该修法对所有来源（AI 行、规则行、l10n 兜底）的同类粘连一律生效，属纯渲染处理、不改数据。

**测试**：
- `mobile/test/core/utils/text_rendering_test.dart` +3 个单元用例（粘连标题、数字邻接+既有空格保真、纯 ASCII/纯中文/空串幂等）；
- `mobile/test/widget/home/test_growth_dashboard.dart` +1 widget 用例：喂入截图原句变体，断言渲染为「先完成 TimedPracticeLoop 打破」「还有 118 天」。

**遗留建议（不在本卡范围）**：服务端若要根治「Timedpracticeloop」小写化与语义拼接质量，需在 AI 提示词/后处理层处理，建议给后端线另开卡（本次仅记录，未硬改）。

## 变更清单（git diff --stat 口径）

```
mobile/lib/core/utils/text_rendering.dart                          | +33
mobile/lib/features/galaxy/data/repositories/galaxy_draft_repository.dart | 25 +/-（切除回落）
mobile/lib/features/home/presentation/widgets/daily_context_line.dart |  9 +/-
mobile/test/core/utils/text_rendering_test.dart                    | +22
mobile/test/widget/home/test_growth_dashboard.dart                 | +15
mobile/test/features/galaxy/data/repositories/galaxy_draft_repository_test.dart | 新增 101 行
```

## 环境备注

- worktree 按规程拷入 gen 三件套（mobile/lib/gen、backend/app/gen、backend/gateway/gen，`cp -RL` 解引用）——BG/AQ 守卫假失败随之消除，首跑 2 红 → 复跑 83 绿。
- analyze 首跑 I602 超预算 3，全部来自本卡新测试文件（unnecessary_import + 3 处 require_trailing_commas），已修至 I598 归位；`galaxy_draft_repository.dart:71` 的 strict_raw_type 为存量（allowlist STRICT_RAW_TYPE:2 预算内），未动。
