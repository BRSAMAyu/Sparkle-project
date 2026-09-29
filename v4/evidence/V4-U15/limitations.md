# V4-U15 — limitations

## 1. NOT_RUN / 边界面（如实登记，不冒充）

1. **sparkle-coordination-v2 ui-longtail 锁租约**：本机未配置该私有远端
   （git remote 无此远端），租约 NOT_RUN（S01 limitation #1.3 同环境性）。
   冲突面以 diff 自证：唯一 diff = 1 测试新文件，无他卡在航文件交集；
   在航卡 U02/U06/U13 的模块文件零触碰。有远端配置的会话请补登。
2. **repeat 门控分级是代理口径**：「22 有门引用 / 27 无门引用」按文件内
   reduce-motion/disableAnimations/resolveSparkleMotionTokens/SemanticMotion
   关键词引用计数——文件级代理，非逐动画审计（一个文件的每个 repeat 未必
   各有门；有引用≠每处生效）。逐动画清尾由 motion-policy owner 推进时按
   S01 同款机器证据口径另行落证。B 组棘轮钉的是**文件集上限**，不冒充
   「无后台无限动画已达成」。
3. **全量守卫基线未在本卡重跑**：`bash scripts/run_all_rule_guards.sh`
   非本卡面（backend 治理为主）；本卡只复跑 mobile 相邻三守卫
   （UI-TOKENS/L10N-PARITY/i18n-coverage）全 PASS。
4. **fitness 面 N/A 而非 PASS**：SCREEN_FAMILIES「每家族统一检查表」的
   截图/大字体/键盘等运行时面，因本卡零 UI 差量而不触发（无新面可截）；
   各面的既有证据归属各收口卡，本卡不转贴冒充。
5. **处置表的「他卡已收」以 tasks.json 已审状态 + 本卡静态复核为据**：
   抽检面 = 目录在位、C3/D 组守卫清单、域回归绿；不重跑各卡完整证据链
   （V4_DONE「旧工作不重做」判例）。

## 2. 已知取舍（实现面）

1. **零产品码差量是本卡的主交付形态**：依据 no_duplicate_rule「当前仓库
   已满足本卡行为时做差量举证，不重写」。反方证据链在 diff_or_evidence_
   only.md §2/§3：U07 已摘四类 LABS 入口、UI-TOKENS 棘轮在册、LABS 五屏
   状态族一致、八模块零主题声明。若审查判「清点卡必须伴随清理」：§1 P1
   优先级表已备好，但清尾触及 achievement/chat/home 等已收口他卡面，逐面
   会签超出本卡 normal 风险/单审授权，登记归属是本卡授权内的最大动作。
2. **C2 选择「钉死不删除」孤儿组件**：SeedLibraryDashboardCard 在 home/
   面（U01/U07 裁决域），本卡 modules 清单不含 home——删除他卡面文件
   越界；机器钉（零消费点断言）达成与删除等价的「不泄露」效果，且保留
   home owner 的裁决自由（删除时顺手拆钉即可）。
3. **B 组棘轮基线以常量内嵌**（kRepeatBaseline49/kRepeatRatchetMax）而非
   独立 JSON：与 nav 契约测试同风格；代价是降棘轮需改 Dart 文件（diff
   可见性等同 UI-TOKENS 的 baseline JSON diff）。
4. **learning 的处置**：44 目录 = 43 矩阵 + learning，A 组白名单钉死。
   若未来规范 owner 把 learning 立为第 44 模块，改白名单常量 + MATRIX
   canonical_count 同步即可（显式双改，不可单边漂移）。
5. **D 组扫描含生成面例外说明**：扫描域 = lib/features 八模块目录，天然
   不含 lib/gen（生成产物）；`*.g.dart` 在模块内者若未来出现主题字面量
   会被 D 组命中——生成文件按硬规则 1 不手改，届时应调扫描域而非改生成。

## 3. 测试口径注记

1. **反例纪律**：14 用例 = 7 正 + 7 反；每个零值/包含断言都有同谓词合成
   反例（幽灵目录、新增 repeat、合成导航调用方、合成消费点、合成字面
   push、合成主题声明、新增调色板消费方），证明断言非恒真；B- 额外含
   「注释行不计数」口径钉与 allowed⊆actual 控制组。
2. **B+ 实录**：常规跑打印「U15 repeat 复跑数 = 49（基线 49）」——复跑数
   即卡面强制移交数字的机器可读形态。
3. **零 skip**：14/14 无 skip；各回归套零失败。
4. **C1 排除面**：reflection 扫描排除 `lib/features/reflection/`（自身）与
   `lib/app/routes.dart`（注册面）——注册≠入口；若他卡在 routes.dart 增加
   reflection 深链处理，属深链 owner 面（登记 §3-4 of diff 文档）。

## 4. 审查挑战点预登记

- **CH-1｜「清点卡零产品码差量」的读法**：若判 acceptance 隐含「迁移=
  必须有代码变更」——反方 = 卡面 no_duplicate_rule 明文 + objective 的
  「迁移」在现存面已被 U07/F 线完成的实事 + 49 文件 repeat 清尾与孤儿
  删除均触他卡裁决面（本卡 normal/单审不授权）。请裁决口径或在 receipt
  注记；若判必须清理，建议拆独立小卡按 P1 表逐面会签推进。
- **CH-2｜repeat 棘轮的「只降不升」强度**：本卡钉「文件集 ⊆ 基线且 ≤49」，
  不钉「逐文件调用点数不升」（同文件内加一处 repeat 不触棘轮）。若判须
  调用点级棘轮：把 91 调用点数入基线即可（结构已留 maxAllowed 通道），
  属规范 owner 裁决面。
- **CH-3｜门控代理口径**：22/27 分级非逐动画审计（limitation #1.2）。
  若判 P1/P2 分级须以逐动画机器证据为据：归清尾卡首件事，本卡不冒充。
- **CH-4｜learning 是否应立为第 44 模块**：本卡按 onboarding_note 判例
  记承载目录。MATRIX owner 若判立模块：A 组白名单 + canonical_count 双改
  显式化，本卡结构不受影响。
- **CH-5｜C3 字面清单的完备性**：kForbiddenLiteralPaths 只列 push/go 五
  LABS 路径两种导航形式；`goNamed`/`pushNamed` 名称跳转形式未列（路由
  name 与 path 双轨）。现存 CORE 面 named 跳转零命中（符号级既有守卫
  覆盖 Routes 类引用），若判须字面 named 形式入清单：加常量即可。
- **CH-6｜验收①「截图或不可达证据」的 LABS 面**：mirofish/simulation/
  theater 的「不可达」以 U07 摘除注释 + nav 契约 + C 组钉复合举证，无
  逐屏运行时截图（零 UI 差量不触发 evidence_required 的 if_ui 条件面）。
  若判须运行时深链到达截图：归设备面卡（V4_DONE 设备 NOT_RUN 判例）。
