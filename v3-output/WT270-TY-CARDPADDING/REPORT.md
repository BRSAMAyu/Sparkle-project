# WT270-TY-CARDPADDING · N43 卡内边距两档制落地（A 线·排版收尾）REPORT

> 卡号 wt270-ty-cardpadding；分支 wt270-ty-cardpadding（本地 commit，未 push）。
> 上游依据：`v3-output/A-SPEC7/REPORT.md` TY-G4/G5、N43 条款（§4 改造表 #8「§3.3 两档制落地首验」）；`v3/FLEET-BRIEF.md`。
> 本卡只动首验面，不做全库清洗（N43 条款本身即登记制）。

## 0. 交付四件

| # | 交付 | 落点 | 状态 |
|---|---|---|---|
| 1 | §3.3 条款修订（单向 16dp → 两档制） | `v3-output/DL-R3/SPEC.md` §3.3 | 完成 |
| 2 | 两档语义 token（DS + SparkleSpacing 双挂） | `mobile/lib/core/design/design_system.dart`、`mobile/lib/core/design/tokens_v2/theme_manager.dart` | 完成 |
| 3 | 首验迁移（task_card → 列表卡档 12；两处「保持」核对） | `mobile/lib/features/task/presentation/widgets/task_card.dart` 等 | 完成 |
| 4 | 半格登记棘轮守卫（姊妹守卫 + 基线 + manifest 登记） | `scripts/guards/check_spacing_rhythm_ratchet.py`、`scripts/guards/spacing_rhythm_baseline.json`、`scripts/rule_guard_manifest.tsv` | 完成 |

## 1. 改动文件清单

修改（5）：
- `v3-output/DL-R3/SPEC.md` — §3.3 就地修订：卡内边距两档制（列表卡 12 / 内容卡 16，修订说明保留：依据 A-SPEC7 实测三档并存 10/12/16 与列表密度需要）；新组件 4 基栅格硬条款；半格档（2/6/10/14/18）登记只降不升 + 守卫落点；同屏卡片家族必须同档（审查口径）。
- `mobile/lib/core/design/design_system.dart` — `DS` 新增 `cardPaddingList = 12.0` / `cardPaddingContent = 16.0`（static const，随 spacing 阶梯，附 N43 条款注释）。
- `mobile/lib/core/design/tokens_v2/theme_manager.dart` — `SparkleSpacing` 新增同值两字段（theme 侧消费口，与 DS 双挂）。
- `mobile/lib/features/task/presentation/widgets/task_card.dart` — `_spacingMd`（theme.spacing.md=16）改写为 `_cardPadding`（`spacing.cardPaddingList` ?? `DS.cardPaddingList`），卡内容 Padding 换用之；这是本卡唯一的行为改动（16→12，列表卡档）。
- `scripts/rule_guard_manifest.tsv` — 新增 `SPACING-RHYTHM` 行（置于 TYPO-RHYTHM 之后）。

新增（2）：
- `scripts/guards/check_spacing_rhythm_ratchet.py` — N43 半格登记棘轮守卫（TYPO-RHYTHM 姊妹守卫，同族形制：per-file 基线、只降不升、`--update-baseline` 拒绝升高、`--self-test` 端到端夹具测试）。
- `scripts/guards/spacing_rhythm_baseline.json` — 冻结基线（见 §2 口径）。

未动（核对面，核即证据）：
- `mobile/lib/core/design/components/atoms/sparkle_card.dart:34` — 默认 padding = `context.space.edge(all: context.space.md)`，md=16=内容卡档，保持。
- `mobile/lib/features/error_book/presentation/screens/error_list_screen.dart:459` — 列表卡 `EdgeInsets.all(DS.spacing12)`，保持。

## 2. 基线口径（重要）

- **台账口径 1285**（A-SPEC7 §2.1b）：只数 spacing token（`spacing2|6|10|14|18`）用量，rg 实测 1284（含 design_system.dart 5 条定义行与 2 条注释；注释剥离后 1282）。
- **守卫机器口径 1623**：token 1282 + `EdgeInsets` 行内裸字面量（2/6/10/14/18，含 `.0` 变体，lookaround 防误配 `0.6`/`1.35`/`16`/`148`）341，扫 `mobile/lib/**`（剔 `.g.dart`/`.freezed.dart`，注释行剥离）。
- 基线 JSON 以机器口径冻结（1623/324 文件），为棘轮唯一事实源；两口径差已在守卫 docstring 与基线 comment 中写明，防后续对不上账。

## 3. 守卫设计要点

- 维度 `spacingHalfStep`；行粒度计数（token 计全行；裸字面量只在含 `EdgeInsets` 的行计）。
- **行内 ignore 标记陷阱**（卡面已知陷阱，已写进守卫与自测）：标记 `// spacing-rhythm-ratchet:ignore <理由>` 必须骑在**匹配行本身行尾**——注释独立成行会在进 counter 前被 `_code_lines()` 剥除，压不住计数；self-test case4 双向证明（行首标记不豁免 / 行尾标记豁免）。
- 已知漏报（接受并在 docstring 登记，同族 DL-SPEC 的 sat<0.15 先例）：多行 EdgeInsets 构造的续行裸字面量（该行无 `EdgeInsets` 字样）不计数；token 形态行无关、全覆盖。
- `--update-baseline` 沿族例拒绝升高；新文件带债即 FAIL。

## 4. 测试/守卫命令与结果

（原样贴关键行；全部 exit-checked `; echo exit=$?`，无 tail 吞码）

```text
$ python3 scripts/guards/check_spacing_rhythm_ratchet.py --self-test; echo exit=$?
[spacing-rhythm-ratchet] SELF-TEST PASS — clean PASS, token+literal count=5, ratchet raise/lower, leading-vs-trailing ignore trap all behave
exit=0

$ python3 scripts/guards/check_spacing_rhythm_ratchet.py --update-baseline; echo exit=$?
[spacing-rhythm-ratchet] baseline updated: {'spacingHalfStep': 1623} (324 files)
exit=0

$ python3 scripts/guards/check_spacing_rhythm_ratchet.py; echo exit=$?
[spacing-rhythm-ratchet] PASS — ratchet holds: spacingHalfStep=1623/1623 (324 files with debt)
exit=0

$ python3 scripts/guards/check_typography_rhythm_ratchet.py; echo exit=$?
[typo-rhythm-ratchet] PASS — ratchet holds: sub12FontSize=234/234, fontWeightW800=0/0, fontWeightW900=6/6 (111 files with debt)
exit=0

$ bash scripts/run_all_rule_guards.sh --rule SPACING-RHYTHM 2>&1 | tail -6; echo exit=$?
[Rule SPACING-RHYTHM] START
[spacing-rhythm-ratchet] PASS — ratchet holds: spacingHalfStep=1623/1623 (324 files with debt)
[Rule SPACING-RHYTHM] DONE
all rule guards passed (1 rules)
exit=0

$ cd mobile && flutter analyze lib/features/task/presentation/widgets/task_card.dart lib/core/design/design_system.dart lib/core/design/tokens_v2/theme_manager.dart
Analyzing 3 items...
No issues found! (ran in 6.2s)
exit=0

$ cd mobile && flutter test --concurrency=1 test/features/task/presentation/widgets/task_quick_action_silent_success_test.dart
00:00 +7: All tests passed!
exit=0
（注：首次调用误用 `flutter test … | tail; echo $?` 把 tail 的 exit=0 当判定——恰是卡面警告的 tail 吞码陷阱反噬自身；改为输出落 /tmp/wt270_flutter_test.log 后 `echo exit=$?` 取真码。）

$ cd mobile && flutter test --concurrency=1 test/core/design/typography_rhythm_convergence_test.dart
00:00 +5: All tests passed!
exit=0
```

**测试前置（关键交接信息）**：本 worktree 缺 `mobile/lib/gen/`（gitignore 的 proto 生成物），任何 flutter test 编译都会因 `package:sparkle/gen/agent_service.pb.dart` 缺失炸在 `review_grpc_service.dart`。已按硬规则正门生成（宿主工具链窄化调用，非手改 gen/）：

```text
$ PATH="$HOME/.pub-cache/bin:$PATH" buf generate --template buf.gen.dart.yaml
（生成 mobile/lib/gen/*，gitignore 不入 commit；合入侧跑测试前同样需要先出这层）
```

## 5. 资源峰值

- 开工时（09:42）：`swap used = 13055.25M, free = 1280.75M`；load 1m=12.68（>8，测试延后，先做文档/代码轻活）。
- 等门期间谷值（10:27）：`free = 778M`（舰队并发 HEAVY 施压，未越权开跑）。
- 跑测试前（10:44 门检）：`used = 17000.19M, free = 1431.81M`，load 1m=4.08——过门（swap 空闲 ≥1.2G 且 load <8）后开跑。
- 跑测试后（10:52）：`used = 17937.88M, free = 494.12M`——两个单文件测试把可用 swap 吃掉约 0.9G，逼近 500M 熔断线；本卡随即停止一切 HEAVY。

## 6. 未解决问题

1. **A-SPEC7 报告「task_card 10」与机器现状不符**：`task_card.dart` 自初始提交起卡内边距走 `_spacingMd` = `theme.spacing.md` = 16（`SparkleSpacing.md=16`，全库无自定义 SparkleSpacing 实例）；文件内的 10 是 `DS.spacing10`（swipe 背景与 `_SyncFailureStrip` 的段内距）。报告的「10」应为视觉采样口径或抽样点错置。**本卡不改口径记录**（报告为历史实测档案），按 N43 意图把 task_card 落到列表卡档 12，并在 SPEC §3.3 修订说明中沿用「10/12/16 三档并存」的台账表述；实际首验迁移是 16→12。
2. **§10.5 台账 N43 行未回写**：A-SPEC7 N45 表规定台账行「随 v1.7 合入」登记，归 v1.7 合入 owner（主会话），本卡不越界；SPEC §3.3 修订文本已自带 v1.7 N43 溯源标注。
3. **l10n 生成文件格式噪声**：本机 `flutter pub get`/`analyze` 会触发 l10n 再生成，产生与本卡无关的格式 churn（缩进风格），已 `git checkout --` 逐文件还原；合入侧跑测试后如复现，同样只还原 `mobile/lib/l10n/app_localizations*.dart` 三文件即可。
4. **守卫行粒度启发式的已知漏报**（多行 EdgeInsets 续行裸字面量）：如后续要收严，可在触碰批把裸字面量归并到 token 形态解决，不必扩启发式。

## 7. 交接建议

- **合入侧**：patch apply 后按 §4 逐条复跑（尤其 `run_all_rule_guards.sh --rule SPACING-RHYTHM` 与 TYPO-RHYTHM 双守卫）；flutter test 前先出 `mobile/lib/gen`（`buf generate --template buf.gen.dart.yaml`，见 §4 前置）；l10n 三文件如现 churn 直接 checkout 还原，勿入 commit。
- **下一张卡（A 线排版收尾余项）**：同屏卡片家族同档审查（§3.3 审查口径条款）适合做一轮 home/dashboard 抽查——dashboard 区块壳 20/24 与卡片 12/16 的层级关系（壳-卡间距 vs 卡内边距）尚无条款，建议下轮补「壳 padding ≥ 卡 padding」细则。
- **清洗批**（远期，登记制下不立专项）：半格档 1623 机器口径如做燃烧批，优先吃 `EdgeInsets` 行裸字面量 341 处（无 token 语义、迁移零争议），token 形态 1282 随触碰批消化。
- **守卫维护**：`--update-baseline` 只在真实下降后跑；ignore 标记必须行尾骑线（陷阱已写进 FAIL 提示文案，误用者会被守卫自己教回）。
