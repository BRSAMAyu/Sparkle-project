# V4-G01 — limitations

## 1. NOT_RUN / 边界面（如实登记，不冒充）

1. **长尾屏未逐泵 × 四风格**：家族五模块共 30 屏，本卡逐面泵制面 = 10
   面/组件族（dashboard/任务列表/目标详情/档案/冲刺卡/复盘/日历/任务卡/
   纸屑/创建对话框族）+ 200%/空/加载/部分/失败/reduce-motion 状态矩阵；
   其余 17 长尾屏（plan CRUD/sprint 序列 9、home 长尾 3、task 长尾 3、
   daily_detail 等）未逐屏四风格泵制。风险边界实证：五模块 `Color(0x…`
   字面量 = 0（无私有色板源），长尾与主链同令牌管线；兜底 = Q05 三端
   重卡审查（no_duplicate_rule 分工，G 系列返绿使 Q05 有据可过）。
2. **真机四风格目检/截图矩阵** → NOT_RUN（本卡无真机/模拟器触达）；
   已交付面 = flutter test 确定性泵制（F05 判例面）+ B04 容差 golden，
   「截最上层实际画面」的逐态实机矩阵归 Q05（卡面 no_duplicate_rule 同
   款分工）。
3. **锁租约 NOT_RUN**：sparkle-coordination-v2 私有远端未配置于本机；
   冲突面以 diff 自证（RF-06 三文件/routes/backend/proto/tokens_v2/gen
   零命中，命令 10 exit=1 实证）。
4. **goldens 仅钉 2 面 × 4 风格**：任务详情/档案/日历/复盘等面以语义钉
   + 零异常泵制覆盖，未各出 8 张 golden（基线量按「家族关键屏」口径：
   RF-06 面入口 + 任务主链；扩 golden 属基线资产膨胀，按 EVALUATION_
   PROTOCOL「golden 基线变更需独立签理由」克制）。
5. **AQ/BG 守卫**：worktree 环境同 S01（gen 已补位，analyze/测试可跑）；
   全量治理守卫基线未在本卡重跑（非本卡面，回归口径=mobile 测试域）。

## 2. 已知取舍（实现面）

1. **B1 令牌化为输出等值设计**：predicted_intent_card 三处改
   rimLight+alpha 覆盖后渲染输出逐字节不变（rimLight 全档 RGB=纯白）。
   价值在字面量清零与令牌槽声明，非视觉变化；golden 零漂移即等值实证。
2. **C1 weather highlight 登记不修**：lerp 派生基料（非终态 surface），
   现有令牌混入将破坏 classic 发布面零差量；待 token 白槽提案（Q08 类）
   裁决后统一处理。四档走查零异常零对比度失败，非在航缺陷。
3. **A2 纸屑颜色以六槽 task 角色色替换原高饱和六色**：四档视觉与
   classic 原色存在可控差异（原六色为 classic-only 字面量，无四档映射）；
   走查面语义与对比度不变，golden 未钉该面（post_exam_review 不在
   golden 基线内），差异已由前任在代码注释叙证。
4. **A6 200% 下任务卡增高**：Wrap 换行使大字阶卡片更高而非截断——
   ACCESSIBILITY_ASSETS 允许「200% 时更少列、更高卡片，不截断主按钮
   标签」；100% 排布逐像素不变。

## 3. 移交与协作边界

1. **RF-06 为他仓独立 lineage**：三文件零触碰（本卡 diff 自证）；
   dashboard 面仅经 harness 只读泵制。若 RF-06 移植冲突，本卡 diff 叙证
   （本文件 + run_manifest 命令 10）即为「可改但须登记」的登记面。
2. **repeat 棘轮口径**：本卡复算 48 文件/90 调用点（base 57edc4e4 与头
   同值）；U15 册记 49 系其清点时点含 1 个其后他卡已移除文件（S01 自述
   48 互证）。棘轮继续「只降不升」，以最新复跑为准。
3. **Q05 分工**：本卡交付后 G01 家族返绿，Q05 三端重卡审查可据
   evidence/V4-G01/ 走查；两卡不重复出同面截图矩阵。

## 4. 审查挑战预登记（CH-1 ~ CH-6，供独立审查 R1 直取）

- **CH-1 走查分母**：10 面逐泵 vs 30 屏家族的覆盖面读法——挑战者可主张
  「逐屏×四风格」应含 17 长尾屏；反方证据 = limitations §1.1（五模块
  私有色板零实证 + Q05 分工）+ 卡面 no_duplicate_rule。
- **CH-2 B1 等值令牌化是否算修复**：输出字节不变的字面量替换是否构成
  验收③「令牌外颜色」清零——正方 = task_card A5 前任判例 + DESIGN_
  SYSTEM「唯一真源」口径；反方 = 「纯符号改动无用户价值」。
- **CH-3 C1 不修裁决**：weather lerp 白基料登记不修是否应升级为「顺手
  修」——反方证据 = classic 零差量钉（sweep 语义钉「classic 无像素扩展
  发布面零差量」）+ 无白槽现状（palette 内 chatBubbleUserText 同用
  Colors.white 先例）。
- **CH-4 repeat 棘轮 48 vs U15 册记 49**：口径漂移归属——反方证据 =
  S01 limitations §1.1 自述 48 + base/头双点复算命令可复现；移交面 =
  motion-policy owner 对账。
- **CH-5 golden 基线量**：2 面 × 4 风格是否满足「每风格 golden」——
  正方 = 「家族关键屏」最小充分口径 + 基线膨胀克制；反方 = 卡面
  acceptance 未限定面数，可主张扩到 6 面。
- **CH-6 reduce-motion 等价的证据层级**：B2 以位置序列零位移证明静态
  等价（非 S01 的 RGBA 字节级）——反方证据 = screen 级面无 RepaintBoundary
  隔离可直接逐像素断言的成本/脆性；正方 = 位置+在场+零异常三重探针且
  E- 控制组证明判别力，widget 级 RGBA 判例已有 SparkleConfetti 面
  （A10）钉住。

## Errata (leader, 2026-09-30, R1 LOW-1/2/4)
- LOW-1：§1.1 屏数口径修正——实点 `*_screen.dart`=27（非 30），长尾 18~20（非 17）；分母结论不变。
- LOW-2：C1 不修理由②修正——等值令牌混入并非全部破坏（rimLight.withValues(alpha:1.0) 即等值）；正确依据=无语义正确的既有不透明白槽（chatBubbleUserText 在 dusk 为深墨）。
- LOW-4：contrast 测试注释色值笔误 textDisabled=#999999（非 #A49B90），断言不受影响。LOW-3 的 G01_GOLDEN_CAPTURE 环境变量为装饰性无读取方。
