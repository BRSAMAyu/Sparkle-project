# wt791 ledger 工具自检强化实录（notes）

> 2026-09-27 ｜ worker wt791 ｜ worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt791-ledgerguard`（分支 `agent/node-b/wt791/ledgerguard`，自 main@`27bd05e5`）
> 任务：WT788-POSTGATE 门后手册波 1 第 3 项（§1.3 ledger 工具自检增强）提前执行——给 `scripts/devtools/ledger_union_merge.py` 的 `--verify` 叠加三项 deep 抽检，治 FIX-504/508/510/512/514 同族「台账行内容丢失/幻影号」病。未改台账、未碰运行栈与 `/tmp/northstar_ns001_real_drive_state.json`、未 push。

## 1. 基线确认（与派卡面的偏差如实注记）

- 派卡面预期 HEAD 含「docs(b01delta) 不在也可——见 WT788-POSTGATE 目录即对」：该 commit **不在 main log**（`git log --grep=b01delta` 零命中）；实际 HEAD `27bd05e5`（轮#277，明文「补位 wt790/791」即本卡）晚于该基线，`v3-output/WT788-POSTGATE/`（notes+runbook）在册。按「协调状态以最新为准」以此继续。
- 工具现状：`--verify` 四项结构检查（零冲突标记残留/8 裸管形态多数容差/行首锚定 ID 无重号/行尾状态枚举）+ `--check` 合并后验证；配套测试 `scripts/devtools/test_ledger_union_merge.py`（27 用例）。
- **执行中途 main 前进**（`27bd05e5 → da9516f0`，轮#277 后新集成：wt789/wt790 登记面 535/536 新增、533/534/513 行更新）：本分支按派卡基线 `27bd05e5` 不动（一任务一分支，表尾 append 冲突归集成会话）；已对 **main 新版台账**（`git show main:…`）信息性复跑——exit 0、warning 同为 48 项零新增（新行均 OPEN 无 FIXED@/无新幻影），工具落位对前滚后的台账同样兼容。上游 `27bd05e5..main` 零 commit 触碰 `scripts/devtools/ledger_union_merge.py`（本卡改动面集成零冲突）。

## 2. 关键设计裁决：deep 抽检默认 warning 级（实测依据）

派卡面检查 1 的字面语义是「不可达=FAIL，git 失败降级 warning」。但**现行主干台账实测存在历史残留**（本卡摸底，FIX-504/510 的台账卫生卡 1.2 尚未执行）：

- **20 个去重 FIXED@ sha 主干不可达**（`git merge-base --is-ancestor <sha> HEAD` exit 1），计 26 处行级出现；
- **17 行 OPEN 开头混合体 + 1 行收口无凭证**（340 行 `FIXED@wt701`）；
- **4 个幻影号**（413/441/473/475，HEAD 前 200 条 message 引用而台账全文无此号）。

若 deep 发现默认 FAIL，主干台账 `--verify` 即翻红，违反硬性兼容要求「对当前主干台账全量跑 --verify 必须仍通过（历史残留输出 warning 清单但不 FAIL）」。故采三层严重级别：

| 发现类型 | 默认档 | `--deep-strict` | 依据 |
| --- | --- | --- | --- |
| ① 指针腐烂（不可达） | WARN | FAIL | 新引入的腐烂必须拦；存量残留归 1.2 卫生卡 |
| ② OPEN/FIXED 混合体 + 收口无凭证 | WARN | FAIL | 同上 |
| ③ 幻影号 | WARN | 恒 WARN | 历史 message 不可改写，升格无意义（派卡面明示） |
| 环境降级（无 git 仓/无 HEAD/git 调用出错） | WARN | 恒 WARN | 性能/环境护栏，任何模式不 FAIL |

`--no-deep` 跳过 git 依赖的 ①③（②纯文本恒跑）。`--deep-strict` 即 1.2 卫生卡 DoD「自检三项抽检零红」的验收工具（收口后应 default 零 rot/hybrid，strict 才可全绿 exit 0）。

## 3. 三项检查说明（实现要点）

1. **`check_fixed_pointer_reachability`（FIX-504 病）**：对形态合法行内全部 `FIXED@<sha>`（7-40 位十六进制，`FIXED@([0-9a-f]{7,40})(?![0-9a-f])`）跑 `git merge-base --is-ancestor <sha> HEAD`；exit 1=确证不可达（指针腐烂/预 rebase），exit ∉{0,1}=无法核验降级 warning。同 sha 去重缓存，O(去重指针数) 次 git 调用（主干 239 去重指针全量 2.7s）。git 上下文解析：**ledger 所在目录仓优先，回退进程 cwd**（`resolve_git_dir`，worktree 感知）——/tmp 病样也能借 cwd 仓被抽检。
2. **`check_status_pointer_consistency`（FIX-512 病）**：正向=状态格 OPEN 开头而行内含 FIXED@（混合体，53 行事故的机器口径误报源）；反向=状态格 FIXED@ 开头而全行零 `FIXED@<sha>` 指针（收口无凭证，如 `FIXED@wt701` 仅 worktree 名）。复用 `status_cell()` 裸管口径与形态 FAIL 行跳过（不对粘连行双重报警）。
3. **`check_commit_message_phantoms`（FIX-514 病）**：`git log -n200 --format=%x1e%H%x1f%B` 扫 HEAD 前 200 条 message 的 V3-FIX-N 引用，**台账全文（`FIX_ID_TOKEN_RE`）查无该 token=幻影**（行首锚定行与行内提及都算「在册」——重编号注记「原登记 V3-FIX-491」等合法引用不误报）。恒 warning。
4. 聚合器 `verify_ledger_deep()` 与既有 `verify_ledger_file()` **完全解耦**（旧函数签名/行为零改动，27 存量测试不动一行全绿）；CLI 新旗标 `--no-deep`/`--deep-strict` 仅 `--verify` 模式适用、互斥（误用 exit 2）。输出形制：`WARN：…` 行 + `deep 抽检（开启）：git 上下文 …，rot X / hybrid Y / phantom Z / env N` 统计行；FAIL/WARN 分列，退出码只由 FAIL 驱动（零 FAIL 仍 exit 0——老语义陷阱原样保留）。

## 4. 红绿实录

**红**（改动前工具，两病态样例均 exit 0 零发现——三病全盲）：

- `/tmp/wt791-red/bad_ledger.md`（5 行：rot 行=孤儿提交 `acee9124…`（`git commit-tree HEAD^{tree} -p HEAD` 构造的有效但不可达对象）+ OPEN 混合体行 + `FIXED@wt999` 无指针行 + 干净 OPEN/可达 FIXED 对照行×2）：`verify 通过…exit 0`；
- `/tmp/wt791-red/phantom_ledger.md`（scratch 仓 `/tmp/wt791-red/phantom_repo`，HEAD message 引用 V3-FIX-9998 而样例台账无此号）：`verify 通过…exit 0`。

**绿**（改动后）：

- bad_ledger 默认档：`rot 1 / hybrid 2 / phantom 68 / env 0`，三条病行各出 WARN（phantom 68=样例仅 5 行、历史 68 个引用号对它全是「幻影」——口径使然，对照真实台账使用），exit 0；`--deep-strict`：3 项升格 FAIL，`verify 失败：3 项` exit 1；
- phantom_ledger（scratch 仓 cwd）：`phantom 1`，`V3-FIX-9998 …幻影号` WARN，exit 0；
- **主干台账全量**（365 行 V3-FIX 行）：默认档 `rot 26 / hybrid 18 / phantom 4 / env 0` 共 **48 项 warning，exit 0**；`--no-deep` 仅 hybrid 18，exit 0；`--deep-strict` 44 项 FAIL exit 1（1.2 收口前预期行为）。

## 5. 现行台账 warning 清单（48 项汇总，只登记不修——账面编辑权归 1.2 卫生卡）

**① rot 26 项（20 个去重 sha，集中 FIX-504 病登记区 345-397 行）**：220(258,305e230c)、345(417,df51a731)、346(418,a0d5360e)、347(419,59291208)、348(420,423c7b06)、349(421,7ee8d61c)、350(426,f72934f2)、351(427,23e813a3)、352(428,f72934f2)、354(431,e824a39f)、355(437,bdd64e4b)、357(440,b06f972a)、358(443,3378e633)、359(445,eb6f7cd7)、360(447,2d82a628)、362(451,023b2205)、367(467,6fbf15d3)、370(479,6fbf15d3+7fb03747)、384(499,749341e1)、386(525,749341e1)、387(526,749341e1)、392(504,305e230c)、393(506,9c1899bc)、397(510,3d00aec9×2)。

**② hybrid 18 项**：OPEN 混合体 17 行=15(09)、16(10)、19(23)、65(61)、66(62)、178(222)、207(251)、212(243)、213(250)、218(257)、224(262)、345(417)、346(418)、351(427)、363(455)、392(504)、397(510)；收口无凭证 1 行=340(393 `FIXED@wt701` 零 sha)。

**③ phantom 4 号**：V3-FIX-413（9b30fb3203c4）、441（6cc37d3160e0）、473（31d4cf3d7b78）、475（0202db21ff68）。

**已知案例对照（runbook §1.3 DoD）**：FIX-53 已翻格 `FIXED@10d3d7e8` → 零报警（正确结论：混合体已消）；FIX-504 行 → rot 报出（正确）；FIX-508 已闭带 sha → 零报警（正确）；FIX-510 行 → rot+hybrid 双报（正确）；FIX-514 幻影面 → phantom 检查在册（504 引用因台账行内提及不报、505 同理，413/441/473/475 报出）。

## 6. 门禁实录

- pytest：`python3.11 -m pytest scripts/devtools/test_ledger_union_merge.py` **32 passed**（27 存量 + 5 新增⑪节：无 git 降级/临时仓三病点名+strict 升格/--no-deep 跳过①③保②/可达对照零发现/CLI 端到端+用法护栏）。基线 27 用例零改动。
- ruff 0.15.8（line-length 120）：两文件 All checks passed（基线同为 0）。
- black 26.3.1（line-length 120）：`ledger_union_merge.py` 基线干净、改后仍干净（black 全文重排仅及新增行）；`test_ledger_union_merge.py` 残留 2 处 black flag **均为基线既有漂移**（glue 推导式、theirs_row 赋值——基线 black --diff 同样点名），按「新增行零 flag、base 既有不动」惯例未触碰；本卡新增行已逐一清零。
- 主仓工作区非本卡动面；本 worktree 仅改 2 个 devtools 文件 + 新增本 notes 目录。

## 7. 边界与遗留

- 幻影号口径=「台账全文无该 token」：对**碎片/样例台账**会放大 warning（每个真实历史引用都成幻影），对照真实台账使用；warning 级无误伤。
- rot 检查成本 O(去重指针数) 次 git 调用：主干 239 指针 2.7s（M 系 macOS 本机实测）；更大台账可用 `--no-deep` 护栏。
- `git merge-base` 不可达≠提交不存在：也可能是「修复在未集成分支」的合法中间态——故 ① 的存量发现全部导向 1.2 卫生卡逐行复核「翻格或纠指」，本卡不代行。
- 环境注记：主仓无根级 pyproject/ruff 配置，lint 按仓库 Python 惯例（black 120/ruff）本机 homebrew 工具直跑；pytest 需 python3.11（3.14/3.12 无 pytest 模块）。
- 未 push；worktree/分支留存待审查集成。
