# WT795 台账卫生卡 notes（WT788 门后手册波 1 第 2 项）

- 分支：`agent/node-b/wt795/hygiene`（worktree wt795-hygiene，基线 main@7de5e46e）
- 日期：2026-09-27（工单口供 2026-09-28 深夜档）
- 工具：`scripts/devtools/ledger_union_merge.py`（wt791 版，**零改动**，`git status scripts/devtools/` 干净；`test_ledger_union_merge.py` 32 passed）
- 台账：`v3/06_agent_fleet/DYNAMIC_ISSUES.md`（369 行 V3-FIX 行，8 裸管形态全程合法，ID 无重号）

## 1. DoD 前后对比

| 档位 | 改前（基线） | 改后 |
|---|---|---|
| `--verify`（默认档） | deep 抽检 warning **48** 项（rot 26 / hybrid 19 / phantom 3 / env 0） | warning **3** 项（rot 0 / hybrid 0 / phantom 3 / env 0）——仅剩 phantom「不占号声明」类，见 §5 待裁决 |
| `--deep-strict` | rot+hybrid 全部升格 FAIL（45 项） | **零 FAIL**，verify 通过（exit 0） |
| `pytest scripts/devtools/test_ledger_union_merge.py` | — | **32 passed**（0.78s，backend/.venv） |

命令：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md [--deep-strict]`

工单口径「phantom 类 4（413/441/473/475）」与本次实测 3 项的差异：**413 未再被报**——其引用提交已滑出工具 200 条扫描窗（`git log -n200 --format=%B HEAD | grep -c V3-FIX-413` = 0；`-n2000` 口径 = 1），属扫描窗漂移自然消解，非台账侧修复。

## 2. 三类处置计数

- **rot 26 warning → 0**：24 行纠指/改写。25 个腐指中 23 个按「集成即纠指」判例纠指到主干可达 SHA（subject 逐字匹配法，wt709 判例同款）；2 个是叙述性引文（258 行状态格补记内、504 行 Reproduction 列病史），改写措辞保留 SHA 事实、去除机器指针形态。
- **hybrid 19 warning → 0**：19 行状态格手术。12 行纯翻格（`OPEN 补记FIXED@…`/`OPEN→FIXED@…`/`OPEN；FIXED@…` 首词改 `FIXED@…`，补记原文保留）；6 行闭账翻格（222/393/504/510/498 + 345/346/351 翻格并纠指）；1 行 worktree 名指针补真实 commit 凭证（393）。
- **phantom 3 warning → 3（不阻断）**：441/473/475 查证均为 commit message 里的**「不占号/保持空闲」声明**（非笔误、无对应真实工作），按规则 3 记勘误不造行、不改台账，留待裁决（工具设计恒 warning 不 FAIL，deep-strict 亦不升格）。
- 触达行合计 **38 行**，全部只动状态格与 FIXED@ 指针 token；描述列文字零改动（两处描述列内**指针 token** 的最小改写见 §4-4，如实报备）。

## 3. 逐行三件套（行号=基线行号；改前/改后取状态格头部或指针 token 段；完整逐字节 diff 见本卡 commit）

### rot 类纠指（证据命令通式：`git log -1 --format=%s <old> && git log -1 --format=%s <new> && git merge-base --is-ancestor <new> HEAD && echo OK`；定位命令 `git log HEAD --grep="V3-FIX-<n>" --format='%h %s'`）

| 行 | ID | 改前指针 | 改后指针 | 证据 |
|---|---|---|---|---|
| 345 | 417 | FIXED@df51a731 | FIXED@0b6f8ee4 | subject 逐字匹配「fix(orchestration): wt732 V3-FIX-417 幂等闸门拒绝不进自修正环…」；df51a731 预 rebase 不可达 |
| 346 | 418 | FIXED@a0d5360e | FIXED@6cff69e2 | subject 逐字匹配「fix(fusion): wt736 V3-FIX-418 信念融合跨进程丢更新…」 |
| 347 | 419 | FIXED@59291208 | FIXED@2ae4495d | subject 逐字匹配「fix(V3-FIX-419): community 写面帖定位补软删+双向拉黑双闸…」 |
| 348 | 420 | FIXED@423c7b06 | FIXED@1e96dc2b | subject 逐字匹配「fix(streak): wt734 V3-FIX-420 连胜统计读-算-写补行锁…」 |
| 349 | 421 | FIXED@7ee8d61c（格内另「已落@7ee8d61c」） | FIXED@f7b14f5a（格内同步「已落@f7b14f5a」） | subject 逐字匹配「fix(V3-FIX-421): 修案C 文案诚实化…」 |
| 350 | 426 | FIXED@f72934f2 | FIXED@9665be8b（注 engine 半 028f6ff0→主干 4c752a16） | gateway subject 逐字匹配；engine 双子 028f6ff0↔4c752a16 subject 逐字匹配 |
| 351 | 427 | FIXED@23e813a3 | FIXED@5e7cedbe | subject 逐字匹配「fix(gateway): wt739 V3-FIX-427 ChatHistoryPersister 优雅关停批不丢…」 |
| 352 | 428 | FIXED@f72934f2（格内「Go 半（f72934f2）/engine 半（028f6ff0）」） | FIXED@9665be8b（格内同步 9665be8b/4c752a16） | 同 426 双半 subject 匹配 |
| 354 | 431 | FIXED@e824a39f | FIXED@0d7cda55 | subject 逐字匹配「fix(galaxy): wt718 G-04 验收补强——跨用户隔离收口（V3-FIX-431）…」 |
| 355 | 437 | FIXED@bdd64e4b | FIXED@8d12ba54 | subject 逐字匹配「fix(V3-FIX-437): 死 l10n 键 transparentMode 全仓清除…」 |
| 357 | 440 | FIXED@b06f972a | FIXED@8e837e8a | subject 逐字匹配「fix(V3-FIX-440): GOV-015 孤儿屏…全链删除…」 |
| 358 | 443 | FIXED@3378e633 | FIXED@f1d791b1 | subject 逐字匹配「fix(fleet): wt730 V3-FIX-443 kill_switch 邻批扫雷…」 |
| 359 | 445 | FIXED@eb6f7cd7 | FIXED@558a7904 | subject 逐字匹配「fix(V3-FIX-445): l10n EN 占位残余清零…」 |
| 360 | 447 | FIXED@2d82a628 | FIXED@22f00244 | subject 逐字匹配「fix(orchestration): wt740 V3-FIX-447 IdempotencyInterrupted…」 |
| 362 | 451 | FIXED@023b2205 | FIXED@8c195be1 | subject 逐字匹配「fix(V3-FIX-451): 连胜统计首建并发去重…」 |
| 367 | 467 | FIXED@6fbf15d3 | FIXED@9625e9e9 | 6fbf15d3 系 wt766 docs 提交预 rebase 形；修复真身=主干重提交 9625e9e9（subject 逐字匹配 worker 7fb03747；docs 孪生 ff42830f） |
| 370 | 479 | FIXED@6fbf15d3 + FIXED@7fb03747（格内「见 467 行 FIXED@7fb03747」） | FIXED@9625e9e9（格内同步改引 9625e9e9） | 同 467 |
| 384 | 499 | FIXED@749341e1 | FIXED@491495d7 | subject 逐字匹配「fix(backend): wt777 FIX-499 total_days 类型收口 + wt768 三观察探针后处置…」 |
| 386 | 525 | FIXED@749341e1 | FIXED@491495d7 | 同上（wt777 观察②=本行摘除无效 loader 面，见 491495d7 body） |
| 387 | 526 | FIXED@749341e1 | FIXED@491495d7 | 同上（wt777 观察③=call-arg 五处真路径修复） |
| 393 | 506 | FIXED@9c1899bc | FIXED@55cb9668 | subject 逐字匹配「fix(guest-seed): V3-FIX-506 种子演示群打「（演示）」标记…」；闭账 commit 82dad4ad 当时写的是预 rebase SHA |
| 220 | 258 | 活指针 FIXED@52fbed29 不动；格内补记叙述「写 FIXED@305e230c 被 e9a0e5b7 回退」 | 「写指针 305e230c（预 rebase 不可达）被 e9a0e5b7 回退」 | 305e230c 为历史叙述非活指针；52fbed29 主干可达亲证（wt769 b0418523 message 亦确证「修复本体 52fbed29 在主干完整在案」） |
| 397 | 510 | Reproduction/Owner 两列各 1 处 FIXED@3d00aec9 | FIXED@3ec111c4（注「原记 3d00aec9 系预 rebase」） | 3ec111c4 与 3d00aec9 subject 逐字匹配（refactor(design-tokens): wt686 卡 U-05…V3-FIX-377…）；510 行原文自证「集成态 3ec111c4 同题在 main 祖先链」 |
| 392 | 504 | Reproduction 列病史「写入（OPEN→FIXED@305e230c）」 | 「写入（OPEN→翻 FIXED@ 格，初指 305e230c——预 rebase 不可达，现役纠指 52fbed29）」 | 事实保全改写（9d478473 曾写 305e230c、e9a0e5b7 回退、wt769 补闭 52fbed29），去除机器指针 token |

### hybrid 类翻格（补记原文全保留，仅首词手术；证据=改后 `git merge-base --is-ancestor <格内sha> HEAD` 全 OK）

| 行 | ID | 改前状态格头 | 改后状态格头 |
|---|---|---|---|
| 15 | 09 | `OPEN 补记FIXED@b2e8fa13（wt474 扫陈：…` | `FIXED@b2e8fa13（wt795 依补记翻格 2026-09-28；wt474 扫陈：…` |
| 16 | 10 | `OPEN 补记FIXED@fa4e5837（wt474 扫陈：…` | `FIXED@fa4e5837（wt795 依补记翻格 2026-09-28；…` |
| 19 | 23 | `OPEN 补记FIXED@a2327787（wt474 扫陈：…` | `FIXED@a2327787（wt795 依补记翻格 2026-09-28；…` |
| 65/66 | 61/62 | `OPEN 补记FIXED@5236e68d（集成时已修…wt471 返航触发扫陈）` | `FIXED@5236e68d（集成时已修…；wt795 依补记翻格 2026-09-28）` |
| 207 | 251 | `OPEN→FIXED@23b99db6（原 worker 5518d95d 重提交；…` | `FIXED@23b99db6（wt795 翻格 2026-09-28；原 worker 5518d95d 重提交；…` |
| 212 | 243 | `OPEN→FIXED@31ee7e83（原 worker 47e58a88…` | `FIXED@31ee7e83（wt795 翻格 2026-09-28；…` |
| 213 | 250 | `OPEN→FIXED@abc0e516（原 worker 0905200c…` | `FIXED@abc0e516（wt795 翻格 2026-09-28；…` |
| 218 | 257 | `OPEN→FIXED@2b32d728（原 worker afbfdef2…` | `FIXED@2b32d728（wt795 翻格 2026-09-28；…` |
| 224 | 262 | `OPEN→FIXED@ef135804/964ebf5b（原 worker 48598701/77bfc581…` | `FIXED@ef135804/964ebf5b（wt795 翻格 2026-09-28；…` |
| 363 | 455 | `OPEN；FIXED@85fe80e0（原 worker 93f9ea6a…` | `FIXED@85fe80e0（wt795 翻格 2026-09-28；…` |
| 413 | 498 | `OPEN（wt755 登记 2026-09-28） （重编号注…）FIXED@0b063c7c（…集成即纠指…）` | `FIXED@0b063c7c（wt755 登记 2026-09-28；重编号注…；wt795 翻格 2026-09-28；…` |

### 闭账/凭证类（行内事实已含修法方向与证据，本次补状态格凭据）

| 行 | ID | 改前 | 改后 | 证据命令 |
|---|---|---|---|---|
| 178 | 222 | `…复核 Status 时效 \| OPEN \|` | `…时效 \| FIXED@ba0b0baa（wt795 闭账翻格…5 行粘连拆分已由 ba0b0baa 执行…）\|` | `git log HEAD --grep="V3-FIX-222" --format='%h %s'` → ba0b0baa「台账粘连修复（协调方执行）——5 行粘连拆分…全表零重复 ID」；现状 `grep -c '｜｜'` 仅本行叙述自指、被吞行 28/150/190 均已独立在案 |
| 340 | 393 | `FIXED@wt701（worktree agent/node-b/wt701/shardleak…）` | `FIXED@48d5a438（wt795 纠指…集成提交 48d5a438 在主干…；原补记…）` | `git log HEAD --grep="wt701" --format='%h %s'` → 48d5a438「fix(tests): wt701 V3-FIX-393 CI shard 顺序污染第二轮双根因收口」与本行双修面吻合 |
| 392 | 504 | `OPEN（wt769 登记 2026-09-28…）` | `FIXED@ef36b870（wt795 闭账翻格…修法方向两面均已落地…）` | 258 行补闭=本提交内 L220 格（52fbed29）；工具强化=`git log HEAD -S "check_fixed_pointer_reachability" -- scripts/devtools/ledger_union_merge.py` → ef36b870「wt791 ledger --verify 三项 deep 抽检（FIX-504/512/514 同族）」 |
| 345/346/351 | 417/418/427 | `OPEN；复核@wt719/wt735：CONFIRMED…`（格中段含腐指闭账记录） | `FIXED@<真sha>（wt795 翻格纠指 2026-09-28）；复核@…（格中段改「worker 提交 <old> 主干重提交为 <new>」）` | 同 §3 rot 表 |
| 397 | 510 | `OPEN（wt775 登记 2026-09-28，分支 agent/node-b/wt775/upsg）` | `FIXED@92ea564f（wt795 闭账翻格…补登 377 行已随 wt775 深挖并入 92ea564f 补行在案…）` | `git log HEAD -S "wt775 补行" -- v3/06_agent_fleet/DYNAMIC_ISSUES.md` → 92ea564f；现役 377 行（wt775 补行）格 `FIXED@3ec111c4` 可达亲证 |

## 4. 待主会话裁决 / 报备清单

1. **phantom 3 项（默认档恒在 warning，不阻断、deep-strict 不 FAIL）**：
   - V3-FIX-441：6cc37d31（wt728 mypy 烧减批七）body 明言「真 bug 0（V3-FIX-441/442 不占，台账未新开行）」——**不占号声明**，非笔误、无工作可登记，按规则 3 不造行。
   - V3-FIX-473：31d4cf3d（wt745 mypy 烧减批八）body 明言「台账零新开（无真 bug，V3-FIX-473/474 保持空闲）」——同上。
   - V3-FIX-475：0202db21（wt746 day7 预演手册）subject 明言「零阻塞不占 V3-FIX-475」——同上。
   - 处置：本 notes 勘误登记，台账零改动。若主会话希望警告归零，可选：工具对「不占/空闲」声明语境豁免（工具改动需另立卡），或接受长驻 warning（工具注释本就定义其「仅登记不阻断」）。
2. **三处闭账判断报备**（各有 commit 证据，如主会话认为需独立验收可 reopen）：222→ba0b0baa、504→ef36b870、510→92ea564f。
3. **描述列内指针 token 最小改写两处**（约束「描述列不动，只动状态格/指针」的指针面，描述文字零改动）：504 行 Reproduction 病史句、510 行两处 FIXED@3d00aec9 引文。若裁决恢复原引文，rot 类 warning 将在 deep-strict 下升格 FAIL（504×1、510×2），请一并裁量（备选：工具对引文/病史语境豁免）。
4. **插曲如实记录**：首轮编辑曾按 510 行修法方向新插一行 V3-FIX-377（P3 详版），verify 抓出与 wt775 已补行的**377 重号**——wt775 早在 92ea564f 补过最小行（置于 378 之后故基线重号检查未触发）。已删除本卡插入行、保留 wt775 原行，510 行改按「已补行在案」闭账。verify 的重号检查在本次实战中完成一次有效拦截。
5. 413 幻影：引用已滑出 200 条扫描窗（2000 条口径存 1 处），自然消解，未做台账动作。

## 5. 验证实录

```
$ python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md
verify：369 行 V3-FIX 行，裸管分布 {8: 369}，多数形态 8
deep 抽检（开启）：… rot 0 / hybrid 0 / phantom 3 / env 0
verify 通过：零冲突标记残留，8 裸管形态合法（多数容差开），ID 无重号，状态枚举合法，deep 抽检 warning 3 项（默认档不阻断）

$ python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md --deep-strict
（同上，零 FAIL，exit 0）

$ backend/.venv/bin/python -m pytest scripts/devtools/test_ledger_union_merge.py -q
32 passed in 0.78s
```

硬约束自查：描述列事实内容未动（除 §4-3 报备的指针 token）；未动任何 CLOSED/WONTFIX 行；未 push；未碰运行栈与 ns001 状态文件；工具文件零改动。
