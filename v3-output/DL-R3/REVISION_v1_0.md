# DL-R3 · 设计语言规范 v0.9 → v1.0 修订对照记录

> 修订人：A 线规范修订 ｜ 2026-09-22 ｜ worktree wt107（base main@9ca4cd0c）
> 依据：`v3-output/DL-R4/REVIEW.md`（21 条修订清单 P0×3/P1×10/P2×8 + 10 条升级条件）
> 修订对象（就地覆盖为 v1.0 全文）：`v3-output/DL-R3/SPEC.md` + `v3-output/DL-R3/ACCEPTANCE.md`
> 性质：纯文本修订卡。零产品代码改动；所有与实现相关的修订均对照 wt107 树内真实代码二次核验（rg/read，只读），未沿用 R4 转述而未复核的任何数字。

---

## 0. 处置总表

**21 条处置统计：采纳 19 / 改写采纳 2 / 不采纳 0**（P0×3 全部解决；P1×10 逐条落实；P2×8 全部表态，无沉默跳过）。改写采纳 2 条均为「采纳意图、修正建议文本」：

- **P1-2**：R4 建议文本「reverse 取 forward×0.7 后就近向上取白名单值（200→140、…、650→450）」自身矛盾——140 与 450 均非其白名单成员（0.7×650=455 就近向上应为 480）。采纳其意图（reverse 正典表 + 白名单定性），改写为「**正典值 ∪ reverse 表**收窄口径」：映射表 {200→140, 320→250, 480→350, 650→450} 为唯一 reverse 口径且表值本身入 G1 白名单，禁现场另算（SPEC §11 勘误 R8/R9 记录此裁决）。
- **P2-4**：R4 建议 widget test 断言为主、golden 为辅——照采；「运行时截图测量」口径废除。归改写采纳因替换了 v0.9 条款的度量方式而非仅补定义。

| R4 条目 | 级别 | 处置 | 修订位置（v1.0） |
|---|---|---|---|
| P0-1 §1.7 门禁时序自相矛盾 | P0 | **采纳** | SPEC §1.7（两段门禁改写）＋§11 勘误 R7；ACCEPTANCE 头部生效时点注 |
| P0-2 ΔE≤2 无公式/工具/过程 | P0 | **采纳** | SPEC §1.2.2 增补（CIEDE2000＋脚本落点＋tone 对齐三件）；ACCEPTANCE A1.6 同步引用＋BLOCKED 门 |
| P0-3 §6.4 词典 schema 与实现冲突 | P0 | **采纳**（附实现核验修正） | SPEC §6.4 整体改写（schema 现行形态＋criterion 组装唯一 owner 链四条） |
| P1-1 H3 裁决未同步 | P1 | **采纳** | SPEC §0.1/§0.3/§6.1（诚实三件套）/§7.2/§7.4/§8.9/§10.1 B1-6/§10.6；ACCEPTANCE A0.1（错题本 2.0）/A0.4/A6.9/A7.9；候选条款落 SPEC §8.2 备选位 |
| P1-2 阶梯与 G1 白名单矛盾 | P1 | **改写采纳** | SPEC §2.1.1（reverse 映射表）/§9.1 G1（白名单定性＋收窄时点）/§11 R8/R9；ACCEPTANCE A2.1 |
| P1-3 迁移顺序缺中间态守卫 | P1 | **采纳** | SPEC §2.1.3（顺序①→④＋引用计数纪律；现值 172 refs 已树内复核） |
| P1-4 A1.2 幽灵白名单 E5 | P1 | **采纳** | ACCEPTANCE A1.2（无 E5 目录；`mobile/test` 天然域外；routes.dart 域外单点登记） |
| P1-5 A6.6 大小写漏报＋清库无 owner | P1 | **采纳** | ACCEPTANCE A6.6（`(?i)` pattern＋3 逃逸行入基线＋清洗 BLOCKED 门） |
| P1-6 A1.3 示意正则与实现不符 | P1 | **采纳** | ACCEPTANCE A1.3（删正则，改述 HLS 判定口径＋漏报面申报） |
| P1-7 arb/l10n 工程纪律缺失 | P1 | **采纳**（批准裁决 1：委托式为默认） | SPEC **§6.5 新增**（5 条）；ACCEPTANCE A6.11 新增 |
| P1-8 单一事实源升 §9 | P1 | **采纳**（批准裁决 2：升 §9 不进 §4＋注册可达性测试） | SPEC **§9.4 新增**（4 条）；§6.3② 改写；ACCEPTANCE A7.5 改写＋A9.5 新增 |
| P1-9 §10.5 缺实施状态台账 | P1 | **采纳** | SPEC §10.5 升级台账（首批 12 行回写）；§8 就地【已落地】标注；ACCEPTANCE A10.4 改写 |
| P1-10 A3.4 前缀机检空转 | P1 | **采纳** | ACCEPTANCE A3.4（角色后缀制）；SPEC §3.2.4 新增＋§3.2 en 估算脚本常数化 |
| P2-1 附录统计失实 | P2 | **采纳** | ACCEPTANCE 附录重刷（49/37/14/⛔14，口径注明）＋A4.7 归人审 |
| P2-2 A8 引用错位 | P2 | **采纳** | ACCEPTANCE A8 表逐格审计：A8.2 V13 改挂 chat 域回归用例；A8.8 改挂 A2.13；列名改「验收引用」 |
| P2-3 「3 秒」无操作定义 | P2 | **采纳** | ACCEPTANCE A8.1（可测半句交 A5.4＋PerformanceTier.medium；人审留主观半句） |
| P2-4 chat 面积无测量工具 | P2 | **改写采纳** | ACCEPTANCE A5.6（widget test：无面板挂载态 ListView 约束高/屏高 ≥0.70；golden 为辅） |
| P2-5 触觉开关无验收条款 | P2 | **采纳** | ACCEPTANCE **A2.13 新增**（机检·批 3）；SPEC §2.3 同步引用 |
| P2-6 B1-3 引批 2 手段 | P2 | **采纳** | SPEC §10.1 B1-3 验收改 A4.3–A4.5＋手测；§10.2/§4.4.1/冒烟清单 5 注 golden 自批 2 起 |
| P2-7 域外存量无下降目标 | P2 | **采纳** | SPEC §1.5.2（coldColorLiteral 90 处：批 2 降 ≥50%、批 3 清零）；A1.2 域外单点；§10.5 台账行 |
| P2-8 行号漂移＋基线共享态 | P2 | **采纳** | SPEC **§11.1 新增**（引用纪律：@commit＋符号名优先）；§9.1（基线 JSON 共享态纪律）；§1.4.2 等行号标注时点；ACCEPTANCE A9.3 同步 |

**升级条件 10 条核对（R4 §5）**：条件 1–10 全部满足（对应 P0-1/P0-2/P0-3/P1-1/P1-2/P1-4+5+6/P1-7/P1-8/P1-9/P2-1）；P1-3/P1-10 与其余 P2 一并带入。**v1.0 判定：达成。**

---

## 1. P0 三条修订后关键文本（摘要）

1. **P0-1（SPEC §1.7）**：「新代码门禁分两段：【立即】段＝禁新增 `Color(0x…)` 字面量与 `Colors.*` 引用（ratchet 守卫执行，基线 103 只降不升）；【批 2 起】段＝语义别名 getter 随 B2-2 合入 `sparkle_context_extension.dart` 后，新代码取色只走语义名，旧字段名降为只读 owner。两段生效时点均以守卫/别名合入 commit 为准，不以本规范合入为准。」（核验：`context.colors` 现返回旧 `SparkleColors`，语义名零存在。）
2. **P0-2（SPEC §1.2.2）**：「ΔE 采用 CIEDE2000（D65/2°，Lab 由 sRGB 线性化换算）；度量脚本落点 `scripts/design/check_surface_ladder_de.py`（输入=算法输出四值+锚点四值，输出=逐对 ΔE 与 PASS/FAIL），随 B2-2 同批交付并入 A1.6 机检——脚本合入前 A1.6 不得宣称达成。对齐过程：对每个锚点 hex 反推 HCT tone，算法侧取同一 tone 输出值逐对比较；『偏差』一律指本脚本输出。」（核验：`scripts/design/` 现不存在，故必须绑 B2-2 交付时点。）
3. **P0-3（SPEC §6.4）**：「`LexiconEntry{domain, raw, label}`，label 为 arb key 间接引用——禁止在词典内建 labelZh/labelEn 双字段。criterion 标签唯一组装链：引擎只下传结构化原值＋模板 key；mobile `criterion_lexicon` 为唯一组装/兜底 owner；`experience_models._criterionLine` 机器形重建仅为旧引擎滚动兼容，超集形状全量生效后删除（登记 §10.5 台账）；任何新域接词典前先登记组装 owner，禁止出现第二个组装点。」（核验：树内 `LexiconEntry` 仅 {domain,raw,label}；组装三方 `experience_readouts.py:184`/`experience_models.dart:206`/`criterion_lexicon.dart:20` 均在；readouts 侧 helper 在 GOAL-ROUTER 后已无生产消费者，修订文本如实标注「随批 1 收尾删除并迁移其单测」。）

---

## 2. 树内核验记录（修订依据，只读）

| 核验点 | R4 主张 | wt107 实测 | 结论 |
|---|---|---|---|
| `sparkle_context_extension.dart` | `get colors => sparkle.colors` 返回旧 owner | 一致（无语义名 getter） | P0-1 修订与实现一致 |
| `core/display/lexicon/lexicon.dart` | `LexiconEntry{domain,raw,label}`，label=arb 间接引用 | 一致（`typedef LexiconLabel`） | P0-3 schema 按实现改写 |
| criterion 组装三方 | readouts:184/:211、models:206、criterion_lexicon:20 | 全部命中；且 readouts 两 helper 已无生产消费者（GOAL-ROUTER 删 GET 后遗留） | 修订补「删除待办」标注 |
| SparkleMotionToken 引用数 | 172（非 131） | `rg -c` 合计 **172** | §2.1.3 采用守卫口径条款 |
| `DS.accent` 行号 | :614（v0.9 写 :610） | design_system.dart:**614** | §1.4.2 改符号名＋@commit |
| `routes.dart` Colors.grey | :113 | **:113** | A1.2/§1.5.2 登记准确 |
| ACCEPTANCE 计数 | 47 机检/36 人审/15 立即/⛔14 | `^- A` 行 awk=47/36；【立即=15（含 A4.7） | P2-1 重刷口径成立 |
| Oops 大小写逃逸 | 3 行 | :2042/:14004/failures.dart:181 全命中 | A6.6 修订与实现一致 |
| PulseScope maxActiveSlots | 2 | pulse_scope.dart **=2** | §11 R2 维持 |
| DL-SPEC 守卫与 SSOT 测试 | 已落地 | `check_dl_spec_ratchet.py`+baseline+manifest:75 在树；`test_goal_today_view.py`/`test_goal_detail_route_shadowing.py` 在树 | §10.5 台账「已落地」行属实 |
| reverse 表值 vs 白名单 | R4 建议文本自相矛盾（140/450∉白名单） | 白名单机械核对成立 | P1-2 改写为「正典∪reverse 表」 |

---

## 3. v1.0 定稿声明与统计口径

- **定稿声明**：R4 §5 升级条件 10 条全部满足；21 条修订全部处置（采纳 19/改写采纳 2/不采纳 0）；`SPEC.md` 与 `ACCEPTANCE.md` 已就地覆盖为 v1.0 全文，版本头、§12 修订记录、交叉引用（条款号/依据编号 D/C/S/E-P/I-P）自查通过（章节号引用全部有主，脚本核验无 missing）。
- **ACCEPTANCE 统计口径（v1.0 重刷）**：`^- A#.#` 行计数；A8 表格 9 行为验收索引行不计入；A4.7 归人审（其条文自declared静态不可判）；新增 A2.13/A6.11/A9.5 计入。结果：**机检 49（立即 14＋批 1 的 12＋批 2 的 13＋批 3/4 的 8＋程序性 2）＋人审 37 ＝ 86 条；⛔=14（正文标记与速览逐一对应，v0.9 的 A4.10/A5.7 正文漏标已补齐）**。v0.9 附录宣称 42/27/14 与正文实况（47/36/15）不符的问题，以本口径重刷后消除。
- **与 R4 实测数的差异说明**：R4 实测 47/36/15 为 v0.9 正文计数；v1.0 因新增 3 条机检（A2.13/A6.11/A9.5）并将 A4.7 归人审，得 49/37/14。两数均真实，差异可由口径完全解释。

---

## 4. 收工核查

- [x] 产物 3 份，全部在本 worktree：`v3-output/DL-R3/SPEC.md`（v1.0 覆盖）、`v3-output/DL-R3/ACCEPTANCE.md`（v1.0 覆盖）、`v3-output/DL-R3/REVISION_v1_0.md`（本文件）
- [x] 零产品代码改动（`mobile/lib`、`backend/app` 未动；引用代码仅为 rg/read 只读核验）
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean 类树操作
- [x] /tmp 无驻留（本轮全程未写 /tmp）
- [x] 未 commit / 未 push
