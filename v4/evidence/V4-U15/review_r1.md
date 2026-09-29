# V4-U15 一审 receipt（独立审查 wtU15R1）

- 审查会话：wtU15R1（未参与实现）；日期 2026-09-28
- 审查对象：agent/v4/u15 实现 6eaf6b3a + 证据 e17f7394（基线 90275dc4；审查时工作树干净）
- 卡标准：v4/04_tasks/tasks.json `V4-U15`（normal 风险，单审，required_locks=ui-longtail）
- 审查方式：只读复跑 + 注入探针（用后即删）；全程未改实现文件、未 push

## 裁决：PASS_WITH_CHALLENGES（无阻断项）

三条验收逐条下判：

| 验收 | 判 | 独立证据 |
|---|---|---|
| ① 43 模块每有 explicit disposition/截图或不可达证据 | **PASS** | 靶2/靶4 |
| ② 不新增同义组件和主题真源 | **PASS** | 靶3/靶5 |
| ③ 原 guard 棘轮只降不升，无半接线屏偷开 | **PASS** | 靶1/靶3 |

## 靶1｜repeat=49 移交闭环（首靶）——**闭合，全部独立复现**

1. **S01 base 复跑**：`git grep -l "\.repeat(" d57a7aa8 -- mobile/lib | sort` = **49 文件**；
   与本卡 HEAD 复跑集（`grep -rln "\.repeat(" mobile/lib --include="*.dart"` = 49）逐路径
   `diff` = **空（1:1 零漂移）**。S01 自述 48 系少记 1 的实证成立，移交条件①按复跑数 49 取数闭合。
2. **91 调用点**：`grep -rn "\.repeat(" mobile/lib --include="*.dart" | wc -l` = 91（原始与剥注释
   同为 91，无注释行干扰）。抽 2 文件核对：`home/presentation/screens/weather_guide_screen.dart`
   = 2（自述 2）✓；`core/design/widgets/flame_indicator.dart` = 4（自述 4）✓。
3. **B 组棘轮注入反例（亲放）**：造 `lib/features/probe_u15_review_50th.dart`（含 `controller.repeat()`）
   → 套件 14 跑出**恰好 1 红**：B+ 双通道判负——「repeat 新增越基线面（须先裁决扩基线）:
   lib/features/probe_u15_review_50th.dart」+「repeat 总数 50 > 棘轮上限 49」；B+ 实录打印
   复跑数 50。其余 13 用例不受扰（探针未触 A/C/D/E 面）。探针即删，复跑 **14/14 全绿**还原。
   棘轮「只降不升」机制真实有牙。

## 靶2｜43 模块清点 exact match——**闭合**

- 亲比对：MODULE_MATRIX.json `canonical_count=43`、`features[]`=43 名 ↔ `mobile/lib/features`
  目录 = **44**；ghost=0、missing=0、唯一 extra=`learning`。
- **onboarding_note 判例原文核获**：「历史F24不是当前独立目录，承载在user，不额外算第44模块」
  ——引证真实。
- **learning=U10 承载全链实证**：目录实存（learning_journey_screen/routes/repository/provider）；
  routes.dart:440 `...LearningJourneyRoutes.routes`（注释「V4-U10…只增路由」）；
  goal_detail_screen.dart:95 `LearningJourneyRoutes.journeyUri(...)` 携参进入；
  learning_journey_models.dart:207/210 缺参 `ArgumentError`（「目标上下文缺失：不得从目标跳入
  无上下文工具页」）；V4-U10 卡 DONE_REVIEWED/PASS。
- 判例同构性注记（不阻断）：F24 判例=无独立目录承载于 user 模块内；learning=有目录、以 U10
  路由契约为承载。同构不完美但实质等价——该面有明确归属（DONE 卡）且 A 组白名单钉死防漂移，
  满足 acceptance①「explicit disposition」。是否立为第 44 模块留 MATRIX owner（CH-4，同意
  实现者的双改显式化方案）。

## 靶3｜零产品码差量（CH-1 最重裁决）——**差量举证形态成立**

- git 层亲证：`git diff --name-status 90275dc4..6eaf6b3a` = **恰 1 个新测试文件（+543）**，
  产品码 0 改动；RF-06 三文件/routes.dart/backend/proto/tokens_v2/gen 零命中。
- 抽验 2 项反方证据：
  1. **LABS 入口摘除在先收口**：现 chat_screen 零 seed-libraries/simulation/theater/
     visual-elements 引用；摘除考古命中 **8ac6bad5**（V3 wt356 卡 U-07 长尾导航减负：insights
     摘 sim-theater/seed_library 别名+chat 设置摘除/visual_elements 双入口摘除等，与矩阵断言
     逐项吻合），`git merge-base --is-ancestor` 证实其为 base 90275dc4 **与** HEAD 的共同祖先
     ——收口发生在开卡之前，零差量主张成立。
  2. **UI-TOKENS 冻结棘轮在位**：审查者亲跑 `python3 scripts/guards/check_ui_design_tokens_ratchet.py`
     = **PASS 225/275、632/727（183 files）**，与自述数字一致；脚本自 eb7ccc76（G7 注册）后
     零改动。
- **5 登记项实据与归属逐项核**：
  - #1 repeat 清尾归 motion owner：P1 表抽 2 文件吻合（靶1），跨已收口面会签超出单审授权，
    归属合理。
  - #2 孤儿组件：`seed_library_dashboard_card.dart` 实存于 home/presentation/widgets/
    （U01/U07 裁决域），全 lib 除自身**零消费点**亲证——归 home owner 裁决合理，C2 钉等效
    「不泄露」。
  - #3 translator CPI：translator_tool.dart:**473** 裸 `CircularProgressIndicator(color: accent)`
    行号精确；「替建第二加载组件将违反验收②」的反向论证成立——归 tools owner 合理。
  - #4 reflection 深链面：见靶4；归 notification/深链 owner 合理。
  - #5 palette 消费面：模块外消费方亲证**恰 1 文件** community/achievement_share_card.dart
    = 冻结集——E 组钉与登记一致。
- **CH-1 裁决：零产品码差量读法成立**。卡面 no_duplicate_rule 明文「当前仓库已满足本卡行为时
  做差量举证，不重写」；acceptance① 要求的是 disposition/证据而非代码变更；现存面确已被在先
  卡片收口（上两项抽验+五登记实据）。清尾/删除触他卡已收口裁决面，登记归属是 normal/单审
  授权内的正确动作。**不判「清点卡必须伴随清理」**；P1 表已备好，清尾拆独立卡逐面会签推进。

## 靶4｜LABS/HIDDEN 不可达钉（抽 C1 亲放 grep）——**闭合**

- 路由注册在案：routes.dart:434 `...ReflectionRoutes.routes`（reflection_routes.dart 注册
  `/reflection/summary`，name=reflectionSummary）。
- 零导航调用方亲证：`ReflectionRoutes` 全 lib 仅 features/reflection 自身与 app/routes.dart
  两处；`'/reflection` 路径字面唯一命中为 core/network/api_endpoints.dart:111
  `/reflections/summary`——后端 API 常量，非 Flutter 导航面。HIDDEN「注册≠入口」成立，
  深链兜底归 notification owner（U07 口径）的登记合理。

## 靶5｜测试质量与数字——**全数亲证**

- **14 分解**：源码亲读 = A±2 + B±2 + C1±/C2±/C3±6 + D±2 + E±2 = **7 正 7 反**，与自述一致；
  B- 含注释口径钉与 allowed⊆actual 控制组，断言非恒真（探针实验佐证判别力）。
- **design 261 亲跑**：`flutter test test/core/design/` = **+261 All tests passed**。
- **analyze 亲跑**：`flutter analyze --no-pub` = **No issues found!**；nav 契约亲跑 = **+6**。
- **门控代理 22/27 复现（CH-3 裁决）**：谓词 `reduceMotion|disableAnimations|
  resolveSparkleMotionTokens|SemanticMotion` 逐文件复算 = **GATED=22 / UNGATED=27 精确复现**。
  口径裁决：卡面验收③字面只要求棘轮只降不升+无偷开，未要求逐动画审计；limitations #1.2 已
  如实自曝代理性质且 B 组钉的是文件集上限不冒充达成——**文件级代理对本卡充分**；逐动画机器
  证据归清尾推进卡首件事。
- CH-5 独立核验：`goNamed/pushNamed` × LABS 路由名全 lib 零命中；LABS Routes 类符号引用在
  CORE 面零命中——named 形式现存零实例属实。

## 靶6｜合并落差（main 推进至 6135a2cd）——**干净**

- `git merge-tree --write-tree 6135a2cd HEAD` = 仅 1 行 tree OID，**零冲突行**。
- 产品码文件交集 = 空；tasks.json 双侧均改但 main 侧 3 hunk 只触 I04/I06/I08/U03/U07 条目，
  U15 条目（REVIEW_READY 推进）零重叠——文本与语义双干净。

## 勘误（E 级，不阻断）

- **E-1｜「U07 已摘」归属精度**：§2 矩阵四处「U07 已摘…」实际摘除 commit 为 **V3 wt356 卡
  U-07（8ac6bad5）**，非 V4-U07（长对话 RAG，其实现 commit d798b321 未触这些文件）。实质
  断言（入口已摘、现存面清洁、在先收口）不受影响—— Fleet 状态账引用时请写「V3 U-07 nav
  减负（8ac6bad5）」。
- **E-2｜门控关键词转录**：文档写「reduce-motion」（kebab），实际复现谓词为驼峰
  `reduceMotion`（kebab 形式下为 13/36，不落 22/27）。数字本身真实可复现，仅记录口径注记。

## 挑战裁决汇总（对预登记 CH-1..CH-6）

| CH | 裁决 |
|---|---|
| CH-1 零差量读法 | **支持实现者**：差量举证形态成立（靶3），不判必须清理；P1 表拆卡推进 |
| CH-2 棘轮文件级 vs 调用点级 | 本卡充分；清尾卡开工时建议把 91 调用点入基线（结构已留 maxAllowed 通道），非阻断 |
| CH-3 门控代理口径 | 对本卡充分（验收③字面不要求逐动画）；逐动画证据归清尾卡首件事 |
| CH-4 learning 立模块 | 承载处置实质成立（靶2 全链实证）；立模块归 MATRIX owner 双改显式化 |
| CH-5 named 形式清单 | 现存零命中亲证；加常量是廉价加固，随清尾卡顺手做 |
| CH-6 不可达证据形态 | 零 UI 差量下 C 组机器钉+在先摘除+nav 契约的复合举证充分；运行时深链截图归设备面卡 |

## 移交结论

- repeat=49 移交条件①**闭合**：复跑 49 文件/91 调用点、S01 base 1:1 零漂移、B 组集合棘轮
  注入亲验有牙。
- U 家族收官面成立：五 LABS/HIDDEN 模块（intent/mirofish/reflection/seed_library/simulation/
  theater/visual_elements/tools 中五模块）不可达/维持处置均有机器钉；U15→Q05 依赖可解除。
- 后续动作（非阻断）：E-1 归属勘误随手账；清尾独立卡（motion owner 主导，P1 表在手）；
  CH-2/CH-5 加固随清尾卡。

## 审查者复跑命令索引

```bash
git grep -l "\.repeat(" d57a7aa8 -- mobile/lib | sort   # 49
grep -rln "\.repeat(" mobile/lib --include="*.dart" | wc -l   # 49；-rn|wc -l = 91
grep -n "\.repeat(" mobile/lib/features/home/presentation/screens/weather_guide_screen.dart   # 2
grep -c "\.repeat(" mobile/lib/core/design/widgets/flame_indicator.dart   # 4
# 棘轮探针：lib/features 下新增含 controller.repeat() 文件 → B+ 双通道红；删后 14/14
python3 -c "MODULE_MATRIX vs os.listdir"   # 43↔44，extra=learning，ghost=0 missing=0
git diff --name-status 90275dc4..6eaf6b3a   # 恰 1 新测试文件
git merge-base --is-ancestor 8ac6bad5 90275dc4   # 在先收口
python3 scripts/guards/check_ui_design_tokens_ratchet.py   # PASS 225/275、632/727
cd mobile && flutter test test/core/design/   # +261；flutter analyze 零 issue；nav 契约 +6
git merge-tree --write-tree 6135a2cd HEAD   # 零冲突
```

—— wtU15R1（独立未参与会话）
