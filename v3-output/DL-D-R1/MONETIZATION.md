# MONETIZATION — Sparkle 价值增量型盈利设计（D 线 R1 研究稿）

> 轮次：D 线第一棒 · 纯研究/方案轮（零代码改动）｜ 2026-09-22 ｜ worktree wt82
> 命题：不阉割免费体验、非死板充值——付费只买「更深、更省时、更个性」的增量价值。
> 边界申报：所有定价锚点为**估算/市场常识推断**（无一手调研数据）；每项模式标注与现有架构的衔接点（file:line）与实现成本定性；本轮不写代码。

---

## 1. 原则层（先立规矩，再谈钱）

1. **免费 = 完整学习闭环**。聊天辅导、星图、计划/任务、记忆、光子/成就/排行榜，免费全可用——因为产品的增长引擎就是数据飞轮（用得越多，Aurora 越懂你），阉割体验等于掐死数据源。
2. **付费 = 增量价值三象限**：**更深**（更强的模型/更深度的诊断）、**更省时**（更高额度/更大批量）、**更个性**（更大的长期记忆容量、年报/深度报告）。免费用户永不因「付费墙」在学习主路径上被拦。
3. **禁止暗黑模式清单**（对照反面教材：Quizlet 在资本压力下从学习工具滑向答案查找器、把已做对题目的学生继续塞进付费测试的路径——短期 LTV 换来品牌信任塌方）：
   - 不做倒计时弹窗、不做「仅剩 x 个名额」假稀缺、不做取消流程藏入口；
   - 免费额度用尽 = 明确的终态文案（现成的 BUDGET_EXCEEDED 终态 UX，见 §4），**不说「再不付费学习进度将丢失」**——进度与数据永远属于用户（`docs/legal/data_export_delete_flow.md` 已有数据可携/删除流程背书）；
   - 不把社交压力当付费杠杆（排行榜不卖名次、光子不可人民币直购——见 §3.6）。
4. **学生价格锚点 = 一杯奶茶/一顿食堂午饭**（¥6-15 区间为心理闸门，估算）；所有付费按「周期」不按「月费订阅制」设计——学生的时间结构是学期制，不是月薪制。

---

## 2. 现有架构给盈利预留的接口（这是本设计能落地的原因）

| 接口 | 位置 | 现状 |
|---|---|---|
| **权益唯一真源 `users.entitlement`**（'free'/'pro'，未知一律降 free 的 fail-safe） | 迁移 `backend/alembic/versions/ent01_20260919_add_user_entitlement.py`；引擎判级 `backend/app/core/entitlement.py:35-43`；网关镜像 `backend/gateway/internal/service/user_context.go:77-78`（`IsProEntitlement`） | **已上线**。历史上 `is_pro = flame_level>=3` 的派生已拆除（债务台账 B-06 条目登记、V3-FIX-02 处置）——付费判级地基干净 |
| **免费层模型钳制**（free 用户能力层压到 fast 档） | `backend/app/config/settings.py:701-702`（`FREE_TIER_DOWNGRADE_ENABLED=true`、`FREE_TIER_MODEL_CEILING="fast"`）；执行 `backend/app/core/llm_router.py:377-448`（`_clamp_tier_for_free_tier`，带 `free_tier_downgrade` 可观测标记 :292） | **已上线**。付费第一档「解锁更强模型」= 把 ceiling 放开 + tier 路由放行，零新代码路径 |
| **run 级预算按权益分档**（free: 150k tokens/$0.5/50 工具调用/1800s；pro: 600k/$2/200/3600s） | `settings.py:422-427`（`RUN_BUDGET_LIMITS_FREE_JSON/PRO_JSON`）；派生 `backend/app/core/budget_matrix.py:76-97` | **已上线**。pro 四维全 4 倍——「更深更省时」的字面定义已经写进配置 |
| **用户日额度层**（`llm_tokens:{uid}:{date}`，默认 100k tokens/日、80% 预警、紧急模式 ×2） | `backend/app/core/llm_quota.py:40-48,79-93`（LLMCostGuard）；网关计量 `backend/gateway/internal/service/quota.go:29-82`（RecordUsage/GetDailyUsage） | **已上线**（注意：云上须 `LLM_QUOTA_ENABLED=true`，见 CLOUD_DEPLOY.md §4） |
| **额度用尽的 UX 终态**（BUDGET_EXCEEDED 为明确终态、不进自我修正循环） | `backend/app/core/run_state_machine.py`、`backend/app/api/v1/chat.py:517`、`backend/app/core/failure_semantics.py` | **已上线**。这就是「非打断式升级触达」的技术底座（§4） |
| **AI 模式日请求限**（fast 120 / balanced 60 / deep 24 次每日） | `settings.py:437-439` | **已上线**。「深度模式额度」商品无需新计量系统 |
| **光子系统 + 商城**（光子流水 11 类交易、商城 5 类商品：皮肤/称号/消耗品/加成/视觉元素） | `backend/app/services/photon_service.py`、`backend/app/services/shop_service.py`、`backend/app/models/shop.py:19-47` | **已上线**。游戏化货币与人民币**严格隔离**的现成结构（光子只能挣不能买，§3.6） |
| **期末冲刺功能面**（intake/dashboard/诊断生成/判分/考后复盘） | `backend/app/api/v1/exam_sprint.py:32-85` | **已上线**。「期末周期包」的功能载体现成 |
| **学习周报开关**（`ENABLE_WEEKLY_LEARNING_REPORT`） | `.env.production.example:431` | **已上线**。年报/学期报告的数据管道起点 |
| **数据导出**（`GET /me/export`） | `backend/app/api/v1/data_export.py:55` | **已上线**。「个人学习年报」的合规取数口 |
| **游客→注册转化链**（/guest 自动播种体验数据、/upgrade-guest 两种） | `backend/app/api/v1/auth.py:860,967,1039` | **已上线**。付费转化的前置漏斗（先用爽，再谈钱） |
| **长期记忆体系**（工作记忆/巩固/冲突消解/演化等 memory_* 服务群） | `backend/app/services/memory_*.py`（约 10 个模块） | **已上线**（容量上限未按权益分档——需要新配置，见 §3.3） |
| ❌ **支付通道** | 全仓无 alipay/wechat-pay/IAP 模块 | **缺失，需新建**——这是全部模式里唯一的大额工程量（估算：微信支付 APP 支付 + 后端订单/对账，1-2 人周；若参赛期只做「兑换码」可缩到 1-2 人日，见 §5 分期） |

---

## 3. 候选模式矩阵

> 定价全部为**估算锚点**，实际定价需上线后按转化数据校准。实现成本按「S=纯配置/文案、M=需新模块但架构衔接点现成、L=需新子系统」分级。

### 3.1 星火 Pro · 深度档（核心 SKU）

- **价值主张**：更强模型（deep/plus 档）+ 4 倍单次深度（run 预算四维翻 4 倍）+ 深度诊断模式日额度提升（deep 24→80 次/日，估算值）。一句话：**「难题，用更贵的脑子帮你拆」**——免费层 fast 模型能答 80% 的问题，pro 解锁剩下 20% 的「想不通的题」。
- **定价锚点（估算）**：¥12/月 或 ¥68/学期（约 5 个月，打 5.7 折锚定「学期制」）；对照锚：B 站大会员 ¥25/月、网易云学生价 ¥8/月、知乎盐选 ¥19/月——卡在学生「无感区间」。
- **实现成本：S**。`users.entitlement='pro'` + `FREE_TIER_MODEL_CEILING`/`RUN_BUDGET_LIMITS_*`/`AI_MODE_DEEP_DAILY_REQUEST_LIMIT` 按权益读配置（后三项已按权益分档或加一个 tier 判断即可）。**唯一新代码：一个把 entitlement 映射到这三组配置的读取函数（现价：半天）**。
- **参赛叙事价值**：★核心★——「免费全功能 + 付费买深度」直接回应「如何不阉割体验还能挣钱」的评委必问题。

### 3.2 算力加油包（非订阅的次卡）

- **价值主张**：「期末周急救包」——7 天内深度次数 ×3 + 日 token 额度 ×2。买的是**省时**，不是解除痛苦（免费层照常能用，只是慢/浅）。
- **定价锚点（估算）**：¥6/7 天（一杯奶茶锚点）。
- **实现成本：M**。额度面现成（LLMCostGuard 日 key + AI_MODE 日限 + run 预算派生），新的是「限时乘数」：在 entitlement 旁加 `boost_until/boost_factor` 两列或 Redis 侧 key（`llm_quota.py` 的 key 面加一层乘数读取）；到期自然回落，无需退订流程。
- **叙事价值**：「我们连加值包都是限期的、按需的，不搞自动续费陷阱」——反暗黑模式的活证据。

### 3.3 长期记忆扩容（最独特的增量）

- **价值主张**：免费层 Aurora 记忆保留 N 条/90 天滚动，Pro 保留 3N 条/永久 + 记忆整理报告（哪些记忆被巩固、哪些过期）。**「AI 真的记得你」是大学生的情感刚需**，也是竞品最难抄的护城河（记忆是数据，不是功能）。
- **定价锚点（估算）**：并入 Pro 档，不单卖（单卖容易变成「记忆要丢了」的恐吓式付费，踩 §1 红线；并入 Pro 则是正向增量）。
- **实现成本：M**。memory_* 服务群现成，缺的是按 entitlement 的容量/时效分档配置（需新建：memory 写入路径按 entitlement 读配额 + 超限降级策略「最旧先归档且可导出」——归档不删除，守住数据底线）。memory_admin 面（`backend/app/api/v1/memory_admin.py`）已有管理钩子。
- **叙事价值**：★差异化★——评委问「护城河」时，答案不是模型是记忆。

### 3.4 期末冲刺周期包（功能打包，贴合学期节奏）

- **价值主张**：考试季 4 周：冲刺计划生成（exam_sprint intake/dashboard 现成）+ 每日诊断 + 考后复盘 + 冲刺期深度额度包。免费用户同样能建冲刺计划（基础版），Pro 周期包多的是**每日诊断批改与复盘报告**（高频 LLM 消耗项）。
- **定价锚点（估算）**：¥19.9/期（期末季限售 6 周窗口，制造「季节性在场感」但不做假稀缺——窗口真实对应考试季）。
- **实现成本：M**。exam_sprint 功能面齐（`exam_sprint.py`），缺的是「周期权益」的计时生效（同 §3.2 的 boost 机制可复用）+ 诊断批改次数按包计量。
- **叙事价值**：收入的时间分布贴学期（期末季峰值），故事好讲：「我们的收入曲线长在用户的考试日历上」。

### 3.5 个人学习年报 / 学期报告

- **价值主张**：学期末生成一份图文报告：星图点亮轨迹、专注时长、知识点征服路径、Aurora 观察到的学习习惯演变。**免费给「报告摘要卡」（可分享的 1 张图），Pro 给完整交互式年报**——分享卡本身就是增长物料（见 GROWTH_ASSETS.md §4）。
- **定价锚点（估算）**：¥9.9/份 或并入 Pro；生成成本可控（数据导出接口现成 `data_export.py:55`，排版为离线批任务走 celery，成本估算每份 ¥0.1-0.3 LLM 费用——估算，按 3k tokens 排版文案 + 模板渲染）。
- **实现成本：M**。数据全在库里（analytics/insights 面），缺的是报告生成器（celery 任务 + 模板）+ 分享卡渲染。周报开关（`ENABLE_WEEKLY_LEARNING_REPORT`）证明报告管道已验证过。
- **叙事价值**：期终传播事件 + 「数据属于你」原则的正面展示。

### 3.6 光子系统 = **明确不卖**（这本身就是叙事）

- 光子（`photon_service.py`：成就/每日首胜/契约完成发放，契约失败扣除）与商城（皮肤/称号/视觉元素，`models/shop.py:29-47`）是**纯游戏化货币**：只能挣、不能买、不能兑换权益。付费永不触碰光子账本。
- 为什么：一旦光子可买，「学习赚光子」立刻贬值成「充值赚光子」，契约/打卡的行为设计崩塌；且光子可买的虚拟物品经济在未成年人保护与合规上多一类风险。**「光子永不售卖」写进定价页**，是反 Quizlet 化的公开承诺。
- （光子 → 人民币的转移在模型里存在 `TRANSFER_OUT/IN`（`models/shop.py:28-29`），参展口径明确为「未来好友间赠送玩法，非交易功能」，不开放。）

### 3.7 团队/班级版（延后，参赛期不做）

- 价值主张：辅导员/社团/自习室批量开通 Pro + 班级学习看板。转化效率最高的校内渠道（见 GROWTH_ASSETS.md §5）天然是其销售面。
- 定级 **L**（组织账号体系/批量授权/看板均需新建），参赛期只在叙事里作为「规模化收入想象」一句话带过，不进承诺。

### 3.8 矩阵总览

| 模式 | 买什么 | 定价锚点（估算） | 实现成本 | 架构衔接 | 叙事价值 |
|---|---|---|---|---|---|
| Pro 深度档 | 更深（模型+run 预算×4） | ¥12/月・¥68/学期 | **S** | entitlement→3 组配置 | 核心答案 |
| 加油包 | 更省时（限时乘数） | ¥6/7 天 | M | llm_quota key 面 | 反订阅陷阱 |
| 记忆扩容 | 更个性（并入 Pro） | —（并入 Pro） | M | memory_* 配额分档 | 护城河 |
| 冲刺周期包 | 深度诊断+复盘 | ¥19.9/期 | M | exam_sprint + boost | 学期节奏收入 |
| 学习年报 | 更个性+传播物料 | ¥9.9/份 | M | data_export + celery | 期终传播 |
| 光子 | **永不售卖** | — | — | — | 反暗黑承诺 |
| 班级版 | 规模化想象 | 延后 | L | — | 增长想象 |

---

## 4. 与 budget_matrix 的具体衔接设计

### 4.1 配额落点：四层预算面已经存在，付费只是改参数

```
请求进入
  ├─ 网关层: QuotaService.RecordUsage (quota.go:29)          ← 日 token 计量（llm_tokens:{uid}:{date}）
  ├─ 引擎用户面: LLMCostGuard.check_quota (llm_quota.py:119) ← 日额度判定 + 80% 预警 + 紧急模式
  ├─ 引擎 run 面: budget_matrix.derive_default_run_budget     ← 按 entitlement 派生四维 run 预算
  │              (budget_matrix.py:76；free/pro JSON: settings.py:422-427)
  └─ 全局面: cost_controller BudgetCircuitBreaker             ← llm/rag/aurora/glm_batch 四桶日预算熔断
              (cost_controller.py:119-155)
```

**设计规则：免费/付费差异只落在用户面与 run 面（1-3 层），全局面（第 4 层）对所有用户统一**——平台级熔断是保护服务商自己的，永远对付费用户也生效（烧穿平台日预算时付费用户同样降级，避免「付了钱买来无限风险」的运营黑洞）。

| 层 | free | pro（建议初值，估算） | 改动点 |
|---|---|---|---|
| 日 token 额度 | 100k（现默认） | 400k | `LLM_QUOTA_ENABLED=true` + LLMCostGuard 按 entitlement 读 limit（新增一个 config 读取，S） |
| run 四维预算 | 150k tok / $0.5 / 50 调用 / 1800s | 600k tok / $2 / 200 调用 / 3600s | **零改动**（`RUN_BUDGET_LIMITS_PRO_JSON` 已存在，:425-427） |
| 模型能力层 | ceiling=fast | ceiling 放开至 plus/pro | `FREE_TIER_MODEL_CEILING` 按 entitlement 读（S） |
| deep 模式日限 | 24 次（现默认） | 80 次（估算） | `AI_MODE_DEEP_DAILY_REQUEST_LIMIT` 按 entitlement 读（S） |
| 记忆容量/时效 | N 条 / 90 天 | 3N / 永久 | memory 写入路径新增分档读取（M，§3.3） |

### 4.2 升级触达：在「价值已兑现时刻」出现，永不在「打断时刻」

利用现成的 BUDGET_EXCEEDED 终态与 80% 预警，把触达点全部钉在**用户刚获得价值的瞬间**：

| 触达点 | 时机性质 | 文案方向（草案） |
|---|---|---|
| run 正常完成、且本次用到了 3 次以上工具调用 | 价值兑现后 | 「这次深度拆解用了 5 个推理步骤。Pro 可以每周多做 8 次这样的深拆。」 |
| LLMCostGuard 80% 预警（现成钩子，llm_quota.py:42） | 自然节点，非拦截 | 「今日深度额度还剩 20%。明天恢复，或了解 Pro。」——**倒计时是事实陈述，不是施压** |
| BUDGET_EXCEEDED 终态（现成，chat.py:517） | 明确终态后 | 「今天的深度额度用完了。你的进度已保存，明天 0 点恢复；Pro 深度档是 4 倍额度。」——进度永不丢（可导出背书） |
| free_tier_downgrade 指标触发时（llm_router.py:292，模型被压到 fast 的那次回答交付后） | 价值差体验后 | 不弹窗；在该次回答尾部加一行小字：「本次为快速档回答，深度档可给出多步推理」 |
| 期末季（考试日历驱动） | 季节性 | 冲刺包入口，一次性横幅，不追索 |
| 游客转正流程中（auth.py:967 upgrade-guest） | 主动转化时 | 转正礼：7 天 Pro 体验（数据随转正延续——体验期攒的记忆不回收） |

**反向规则（写进工程验收）**：付费引导**禁止**出现在：聊天流式中途、任务执行等待中、错误/异常弹窗内、每日首次打开的前 30 秒。指标面：`business_metrics.py` 已有业务指标注册面，加 `upsell_shown/upsell_converted` 两枚计数器即可验证「触达不伤留存」。

---

## 5. 支付缺口的分期偿还

| 期 | 内容 | 工程量（估算） | 说明 |
|---|---|---|---|
| 第 0 期（参赛演示） | **兑换码**：admin 面生成 `SPARK-XXXX` 码 → app 内兑换 → `users.entitlement='pro'` + `entitlement_expires_at` | 1-2 人日 | 演示「付费闭环」用兑换码完全够；entitlement 字段与判级全现成 |
| 第 1 期（首批真实用户） | 微信支付（APP 支付）+ 订单表 + 回调对账 + entitlement 自动升降级（含到期降级 job 挂 celery beat——beat 拓扑现成） | 1-2 人周 | 唯一的大额新增；订单/幂等可复用网关 idempotency 面（`app/core/idempotency.py`） |
| 第 2 期 | 加油包/周期包 SKU 化 + 苹果 IAP（若上 App Store） | 另案 | iOS 上架前不动 |

---

## 6. 评委/投资人叙事

### 一段话版（30 秒）

「Sparkle 的商业化不靠阉割免费体验：学习闭环全功能免费，因为用户的学习数据就是产品智能的燃料。付费买的是三个增量——更深的模型、更大的额度、更久的记忆。这套分层不是 PPT：权益判级、四层成本预算、免费层模型钳制、额度终态文案，在我们代码库里已经是上线状态的工程事实（users.entitlement 字段、run 预算按 free/pro 分档的配置、BUDGET_EXCEEDED 终态）。我们每单位收入背后的边际成本是可预算、可熔断、可观测的——这是 AI 应用里大多数团队做不到、而我们做到了的部分。」

### 一页版（路演附录页骨架）

1. **问题**：AI 学习工具两条死路——全免费烧死在 API 账单（无成本架构），或付费墙劝退学生（无数据飞轮）。
2. **我们的路**：免费全功能 + 增量付费；成本侧四层预算兜底（用户日额度 → run 预算 → 分类目熔断 → 队列背压），收入侧六个 SKU 全部贴学期节奏。
3. **为什么是我们**：预算/权益/钳制/终态 UX 是**已合入 main 的代码**，不是规划（可现场指认 budget_matrix.py / entitlement.py / llm_router.py 的行号）。
4. **单位经济（估算）**：免费用户月 LLM 成本 ¥1-3（fast 档 + 100k tokens/日帽），Pro 用户 ¥68/学期——毛利率故事成立的前提全由预算面数值保证，可随 LLM 降价同步调参。
5. **红线承诺**：光子永不售卖、进度永不因欠费丢失、取消/导出永远一键（data_export_delete_flow.md）——「我们不做成下一个 Quizlet」。
6. **规模想象**：班级版/校园渠道（一句话 + 指向 GROWTH_ASSETS.md 渠道清单）。
