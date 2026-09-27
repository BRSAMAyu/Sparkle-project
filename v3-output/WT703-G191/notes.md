# WT703-G191 — V3-FIX-191 处置实录（COMM-LB 守卫误伤 routes.dart 路径消费形态）

- Agent：wt703 ｜ 卡：V3-FIX-191（P2，wt695 日终盘点 A1 队列项）
- 分支：`agent/node-b/wt703/g191`（base = main@3065938b）
- 守卫修复 commit：`f93774ac`（fix(guards)）；台账/产出 commit：见分支 HEAD
- 裁决：**选项 (a) 守卫口径收窄**（非豁免条目）
- 边界遵守：涉事字面量源头在 sparkle-cosmos（`mobile/lib/app/routes.dart:142`），
  该仓库**只读取证、零改动**；全部处置在 Sparkle-project 侧守卫完成。

## 1. 证据链与红复现

台账行（v3/06_agent_fleet/DYNAMIC_ISSUES.md）：T36（cosmos WIP）移动端重定向块移植陷阱——
`startsWith('/leaderboard')` 字面量会被 COMM-LB 守卫 `LEADERBOARD_UI_RE`
（`LeaderboardScreen|leaderboard` ignorecase，逐行扫 routes.dart）打红（无
`rule-comm-lb: ignore` 注即失败）；wt483 PLAN.md F9 实证同款命中。

守卫定位（find 实证，一族仅此一件）：`scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py`
（manifest 条目 `COMM-LB`，rule_guard_manifest.tsv:86）。

红复现（基线先证绿，再原样移植 cosmos T36 块
`sparkle-cosmos/mobile/lib/app/routes.dart:135-145` 到 worktree routes.dart
redirect 闭包尾）：

```
$ python3 scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py   # 修前
RULE COMM-LB FAILED: D-COMM-1 排行榜路由裁决被破坏
  - mobile/lib/app/routes.dart:231: 全站榜 UI 挂路由 (D17 隐藏裁决被破坏;
    D-COMM-1/DESIGN §3.2——自我锚视图走独立 widget, 改造裁决前先更新本守卫并注
    `rule-comm-lb: ignore <reason>`)
EXIT=1
```

231 行即 `state.uri.path.startsWith('/leaderboard');`——纯路径前缀消费，
被误判为「全站榜 UI 挂路由」。

## 2. 裁决依据（为何收窄而非豁免）

守卫 docstring 不变量 1 的本体是「routes.dart **不挂** LeaderboardScreen
（全站榜 UI 无入口）」——校验对象是**挂载/注册形态**。而
`startsWith('/leaderboard') → return '/home'` 是把全站榜路径 redirect away
的**裁决执行面**：它强化而非破坏 D17/D-COMM-1。粗口径打红执行面属「错标准门」
（守卫口径过宽误伤合法代码），加豁免条目会让每个合法执行行都挂 ignore 注
（语义错位：明明无需豁免）。故按守卫意图收窄口径。

## 3. 修复（commit f93774ac，+27 行，仅守卫文件）

- 新增 `LEADERBOARD_CONSUMPTION_RE`：`(?:startsWith\(\s*|==\s*)['"]/leaderboard`
  ——startsWith/== 后紧跟 /leaderboard 前缀字面量（`'/leaderboard'`、
  `'/leaderboards/self-anchor'` 等前缀均覆盖，双引号形态覆盖）＝消费，豁免；
- 新增 `LEADERBOARD_MOUNT_RE`：`LeaderboardScreen|Routes\.routes|GoRoute\(|\.(?:go|push)\(`
  ——挂载/导航 token 在场时**不**适用消费豁免，防
  `if (startsWith('/leaderboard')) return LeaderboardScreen();` 类混合行漏网；
- `return '/leaderboard'` / `go('/leaderboard')` 等 promote 目标形态不含消费
  token，照常打红；
- `_scan_gateway`（不变量 2）零触碰；既有 escape hatch（行内/上一行
  `rule-comm-lb: ignore`）语义不变，既有两条豁免行（routes.dart:29 import、
  410-411 自我锚 spread）不受影响（基线复跑仍绿）。

diff 全文（3065938b..f93774ac）：

```diff
diff --git a/scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py b/scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py
@@ -16,6 +16,15 @@
      任何在 leaderboards 组上显式注册具体榜面路由的行都是「把某张榜 promoted
      成产品路由」的动作，必须先改裁决再接线。

+口径（V3-FIX-191 收窄，2026-09）：不变量 1 校验的是「挂载/注册形态」。路径
+前缀消费（`state.uri.path.startsWith('/leaderboard')` 一类，把全站榜路径
+redirect away 到 /home）是 D17/D-COMM-1 裁决的执行面而非注册，不计入违规；
+同文件内 redirect/导航目标指向 leaderboard 路径（`return '/leaderboard'`、
+`go('/leaderboard')`）仍是 promote 动作，照常打红。携带挂载 token
+（LeaderboardScreen / Routes.routes 展开 / GoRoute( / go|push 导航）的行
+不适用消费豁免，防 `if (startsWith('/leaderboard')) return LeaderboardScreen()`
+类混合行漏网。
+
 Escape hatch（两处皆适用）：行内注 `rule-comm-lb: ignore <reason>`。
@@ -29,6 +38,16 @@
 LEADERBOARD_UI_RE = re.compile(r"LeaderboardScreen|leaderboard", re.IGNORECASE)
+# V3-FIX-191：路径消费形态——startsWith/== 后紧跟 /leaderboard 前缀字符串
+# 字面量（'/leaderboard'、'/leaderboards/self-anchor' 等均覆盖），是对读入
+# 路径的判定消费，不是路由注册。
+LEADERBOARD_CONSUMPTION_RE = re.compile(
+    r"""(?:startsWith\(\s*|==\s*)['"]/leaderboard"""
+)
+# 挂载/导航形态永不因消费形态在场而豁免（不变量 1 的本体）。
+LEADERBOARD_MOUNT_RE = re.compile(
+    r"LeaderboardScreen|Routes\.routes|GoRoute\(|\.(?:go|push)\("
+)
 LEADERBOARD_GROUP_EXPLICIT_RE = re.compile(
@@ -50,6 +69,14 @@ def _scan_mobile_routes():
         if IGNORE_RE.search(prev):
             continue
         if LEADERBOARD_UI_RE.search(raw):
+            # V3-FIX-191 口径收窄：路径消费形态（startsWith/== '/leaderboard*'，
+            # 把全站榜路径 redirect away）是裁决执行而非注册，不再误报；但
+            # 挂载/导航 token 在场的行不适用本豁免（混合行仍按违规处理）。
+            if (
+                LEADERBOARD_CONSUMPTION_RE.search(raw)
+                and not LEADERBOARD_MOUNT_RE.search(raw)
+            ):
+                continue
             failures.append(
```

## 4. 变异实证（收窄后守卫仍咬真违规——四形态全红）

修后把 T36 块**留在文件内**，再叠加四个真违规变异（MUTATION-A/B/C/D，均无
ignore 注），一次运行：

```
$ python3 scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py
RULE COMM-LB FAILED: D-COMM-1 排行榜路由裁决被破坏
  - mobile/lib/app/routes.dart:237: 全站榜 UI 挂路由 (...)
  - mobile/lib/app/routes.dart:239: 全站榜 UI 挂路由 (...)
  - mobile/lib/app/routes.dart:240: 全站榜 UI 挂路由 (...)
  - mobile/lib/app/routes.dart:242: 全站榜 UI 挂路由 (...)
  - mobile/lib/app/routes.dart:246: 全站榜 UI 挂路由 (...)
EXIT=1
```

逐行映射（对照插入区实测行号）：

| 行 | 内容 | 判定 |
|---|---|---|
| 231 | `state.uri.path.startsWith('/leaderboard');`（T36 消费） | **豁免（本卡修复目标）** |
| 237 | `...GlobalLeaderboardAllRoutes.routes,`（MUTATION-A 展开挂载） | 红 ✓ `Routes.routes` token |
| 239 | `GoRoute(path: '/leaderboard', builder: ... LeaderboardScreen()),`（MUTATION-B 注册） | 红 ✓ |
| 240 | MUTATION-C **注释行**含 leaderboard token | 红（守卫既有口径：注释行同样计扫，escape hatch 覆盖，非本卡改动） |
| 242 | `return '/leaderboard';`（MUTATION-C promote 目标） | 红 ✓ 消费豁免未吞 promote 形态 |
| 245 | `if (state.uri.path.startsWith('/leaderboard')) {`（MUTATION-D 消费条件行） | 豁免（正确：条件行本身是消费） |
| 246 | `return LeaderboardScreen();`（MUTATION-D 挂载行） | 红 ✓ 混合行违规整体仍被咬住 |

结论：收窄只豁免「读入路径的前缀判定」，四类真违规（展开挂载/GoRoute 注册/
redirect 目标 promote/消费+挂载混合）全部仍红——**咬合力未削弱**。

## 5. 验证

```
$ git checkout -- mobile/lib/app/routes.dart   # 复现/变异产物全部不入库
$ python3 scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py
RULE COMM-LB OK: 全站榜保持 D17 隐藏 (mobile 无 LeaderboardScreen 路由,
gateway leaderboards wildcard-only), 自我锚视图是唯一产品面
EXIT=0

$ bash scripts/run_all_rule_guards.sh --rule COMM-LB
[Rule COMM-LB] START
RULE COMM-LB OK: ...
[Rule COMM-LB] DONE
all rule guards passed (1 rules)
RUNNER_EXIT=0

$ ruff check scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py
All checks passed!
（black 本机不可用；自查新增行宽全部 ≤120）

$ python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md
verify：292 行 V3-FIX 行，裸管分布 {8: 292}，多数形态 8
verify 通过：零冲突标记残留，8 裸管形态合法（多数容差开），ID 无重号，状态枚举合法
VERIFY_EXIT=0
```

守卫配套测试：find 实证无独立测试文件（`*comm_lb*` 仅守卫本体），咬合力由
§4 变异实证承担。

## 6. 台账与残留

- V3-FIX-191 → `FIXED@f93774ac`（守卫侧闭合；7 列 8 裸管合规，verify 零 FAIL）。
- **残留（非本卡）**：台账行「修复方向」列的移植侧处方——重定向面裁剪为
  /shop*、/visual-elements*，显式排除 /leaderboard*、/photon/*——属产品移植
  处方，仍随 T-release-flag-mobile 卡执行；本卡只消除守卫误伤，不改变该处方。
- 新发现登记：无（无需动用 V3-FIX-397/398 备用号）。
