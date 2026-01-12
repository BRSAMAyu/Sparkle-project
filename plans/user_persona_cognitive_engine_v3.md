# V3.0 (最终版) 生产级用户画像与认知计算引擎方案
# Production-Grade User Persona & Cognitive Computing Engine V3.0 (Final)

## 1. 方案概述 (Executive Summary)

本方案在 V2 版本基础上，针对**合规治理**、**流式可靠性**、**LLM 安全**、**算法精度**及**存储安全**进行了深度工程化加固。

**核心差异化升级 (V3 vs V2)**:
1.  **合规闭环**: 引入“双因子年龄校验”与“取证级删除协议”，满足 GDPR-K/COPPA 最严苛标准。
2.  **流式高可用**: 采用 "Shadow Write" + "Dual Dispatch" 策略，实现从 Redis/Celery 到 Kafka/Flink 的零停机平滑迁移。
3.  **确定性安全**: 废弃 XML 注入，全面转向 `PersonaTool` 结构化工具调用，配合输出审计实现 100% 违规拦截。
4.  **算法自适应**: 引入“自适应停止准则 (Stopping Criterion)”，替代固定题量测试，实现动态精度收敛。

---

## 2. 合规与数据治理增强 (Compliance & Deletion Engineering)

### 2.1 双因子年龄校验 (Dual-Factor Age Verification)
解决仅靠“声明”无法有效识别未成年人的痛点。

*   **因子一：注册强信号 (Strong Signal)**
    *   注册流程强制要求用户选择年龄段或输入出生日期。
    *   **策略**: 若计算年龄 < 14 岁，系统自动进入“未成年人保护模式”，并触发 **Parental Consent Flow** (家长同意流程)。
    *   **证据链**: 记录家长同意的 Timestamp、验证方式（如短信验证码/支付验证）及协议版本号 `consent_v1.2`。
*   **因子二：端侧弱信号推断 (Weak Signal Inference)**
    *   **信号源**: 交互频率（防沉迷分析）、设备家庭模式设置、输入语调（情感分析）。
    *   **作用**: **仅作风控提示**。若注册为成年人但表现出明显的未成年特征，系统**不**自动修改年龄标签，而是：
        1.  在后台标记 `suspected_minor: true`。
        2.  触发“内容降级”策略（过滤成人化内容）。
        3.  发送“身份确认”弹窗。

### 2.2 分级销毁协议 (Tiered Deletion Protocol)
解决“永久保留”与“被遗忘权”的工程冲突。

| 数据层级 | 销毁时效 | 销毁方式 | 备注 |
| :--- | :--- | :--- | :--- |
| **L1 (Clickstream)** | T+24h | **Crypto-Shredding** (销毁解密密钥) | 原始流数据，无需长期保留 |
| **L2 (Session Features)** | 用户发起删除 | **Soft Delete** (标记删除) | 立即对用户不可见，7天后物理删除 |
| **L3 (Persona Tags)** | 用户发起删除 | **Hard Delete** (物理覆写) | 覆盖热/温存储，触发关联缓存失效 |
| **Cold Backup** | T+90d | **Pruning** (定期修剪) | 归档数据在90天滚动窗口内清除 |

*   **Forensic-grade Deletion (取证级删除)**:
    *   对于 L3 级敏感数据，执行 **DoD 5220.22-M** 标准的覆写操作（或云厂商等效的 Crypto-Erase），确保无法通过磁盘恢复工具复原。
    *   生成 `DeletionCertificate` (删除证书)，记录删除时间、范围及操作 ID，供合规审计。

### 2.3 监护人报告协议 (Guardian Reporting Protocol)
*   **默认策略**: **不主动推送**。除非获得双重授权（用户本人 + 监护人）。
*   **触发阈值**: 仅基于**客观学习行为**，严禁基于心理推断。
    *   *触发条件*: 连续 7 天无学习记录、知识点掌握度在一周内下降 > 30% (Learning Regression)。
    *   *通知内容*: "建议关注孩子近期的学习状态"，附带客观数据图表，**不**包含"焦虑"、"抑郁"等定性词汇。
*   **授权管理**: 支持监护人随时撤回授权 (Right to Withdraw)，撤回后系统立即停止生成报告并删除历史报告记录。

---

## 3. 流式链路可靠性与迁移方案 (Streaming & Migration)

### 3.1 渐进式迁移策略 (Progressive Migration)
从 Redis/Celery 迁移至 Kafka/Flink 的平滑路径。

*   **Phase 1: Shadow Write (影子写入)**
    *   业务逻辑保持向 Redis/Celery 写入主流量。
    *   **新增**: 在 Gateway 层异步向 Kafka Topic 发送同一事件的副本。
    *   **验证**: 比较 Kafka Consumer 处理结果与 Celery Worker 结果的一致性，暂不生效 Kafka 结果。
*   **Phase 2: Dual Dispatch (双发双收)**
    *   Gateway 同时向两端写入。
    *   **Read Proxy**: 读取层引入 Feature Flag，按 User ID 灰度切换读取源（1% -> 10% -> 100%）。
*   **Phase 3: Cut-over (切换)**
    *   停止 Celery 写入，仅保留 Kafka 链路。下线 Redis Queue。

### 3.2 数据可靠性工程
*   **DLQ (Dead Letter Queue) 重放策略**:
    *   无法处理的消息（Schema 不匹配、字段缺失）路由至 DLQ Topic。
    *   **自动重试**: 针对网络抖动类错误，指数退避重试 3 次。
    *   **人工介入**: 针对格式错误，提供 Admin Tool 修正 Payload 后手动 Re-inject 回主 Topic。
*   **Watermark & 乱序处理**:
    *   **时钟同步**: 所有事件携带 `event_time` (Client Time) 和 `ingestion_time` (Server Time)。
    *   **迟到容忍**: Flink 窗口设定 `BoundedOutOfOrderness` 为 15 分钟。超过 15 分钟的数据进入 Side Output 流，触发 **Backfill** 逻辑更新长期画像，但不触发实时推送。
    *   **UUIDv7**: 利用 UUIDv7 的时间有序性，解决高并发下的时序冲突问题。

---

## 4. LLM 注入与输出校验工程规范 (LLM Security & Guardrails)

### 4.1 结构化 Context 注入 (PersonaTool)
废弃不安全的 XML 文本注入，采用 Agent 协议原生的工具定义。

*   **PersonaTool 定义**:
    ```protobuf
    message PersonaContext {
      repeated string capability_tags = 1; // e.g., "visual_learner", "fast_reader"
      repeated string preference_tags = 2; // e.g., "concise_style", "encouraging_tone"
      float confidence_score = 3;
    }
    ```
*   **注入机制**:
    *   系统作为 "System Agent" 在对话开始前调用 `get_user_persona()` 工具。
    *   将返回的结构化 JSON 对象注入到 LLM 的 `tool_outputs` 中。
    *   **优势**: LLM 将其视为确定的“外部事实”而非“提示词建议”，显著降低幻觉率。

### 4.2 输出审计与熔断
*   **策略违规检测 (Policy Violation Detection)**:
    *   在 LLM 返回结果前，经过一个轻量级 BERT 模型（或规则引擎）。
    *   **检查项**: 是否泄露画像数据（如“根据系统记录，你是个...”）、是否包含攻击性语言。
*   **不稳定性重生成 (Regeneration on Instability)**:
    *   若检测到违规，拦截输出。
    *   向 LLM 发送修正指令：“回复包含违规内容，请重新生成，注意语气平和。”
    *   若连续 3 次失败，回退到**兜底脚本回复**。

---

## 5. 算法精准度升级 (Algorithm Precision)

### 5.1 自适应锚点 (Adaptive Anchoring)
替代固定的“5题测试”。

*   **Stopping Criterion (停止准则)**:
    *   每做一题，计算当前能力估计值 $\theta$ 的标准误 $SE(\theta)$。
    *   当 $SE(\theta) < Threshold$ (如 0.3) 时，立即停止测试。
    *   **效果**: 能力极强或极弱的用户可能只需 3 题，中间段用户可能需要 7-8 题。
*   **动态选题**: 下一道题的难度 $b_{next}$ 应最大化信息量，即 $b_{next} \approx \hat{\theta}_{current}$。

### 5.2 离线回测规范 (Offline Backtesting)
*   **Hold-out Set (留出集)**:
    *   随机抽取 20% 的历史交互数据作为测试集，不参与参数训练。
*   **漂移检测 (Drift Detection)**:
    *   周期: 每周一次。
    *   **报警阈值**: 若模型在留出集上的预测准确率 (Accuracy) 下降超过 5%，或 RMSE 上升超过 0.1，触发报警，暂停模型自动更新，转由人工排查。

---

## 6. 存储安全基线 (Storage Security)

*   **分层加密**:
    *   **L3 (Hot/Warm)**: 字段级加密 (Field-level Encryption)。敏感字段（如 `psych_profile`）使用 AES-256 加密存储，密钥由 KMS 管理，与应用代码解耦。
    *   **Cold Storage**: 存储桶默认开启 Server-Side Encryption (SSE-S3)。
*   **访问审计**:
    *   所有对 `UserProfile` 表的查询操作记录 `audit_log`。
    *   **内容**: Who (User/Service), When, What (Query Pattern), Why (Request ID)。
    *   **异常检测**: 针对“批量拉取用户画像”的行为配置实时报警规则。

---

## 7. 澄清问题回复 (Q&A - Finalized)

**Q1: 未成年人“自动识别”的信号来源?**
*   **A**: 我们坚持**“强信号定性，弱信号风控”**的原则。**账号注册信息 + 家长同意**是判定未成年人身份的唯一强信号。端侧推断（如交互频率、设备模式）仅作为弱信号，用于触发风控提示（如身份确认弹窗），**绝不**直接用于修改用户的年龄标签或开关画像功能，避免算法误判导致用户权益受损。

**Q2: “监护人报告”触发阈值与法域依据?**
*   **A**: 我们的策略是**默认关闭**。仅在获得**双重授权**（用户本人+监护人）且符合 GDPR-K/COPPA 要求的前提下开启。报告触发阈值严格限定为**客观学习异常**（如连续 7 天学习中断、能力值显著回退），严禁基于“焦虑”、“抑郁”等心理学推断触发报告，确保平台保持在中立的教育辅助角色。

**Q3: “永久保留”与删除/失效机制?**
*   **A**: 我们废除“永久保留”策略，转为**“持续有效，定期复评”**。画像标签引入 TTL（生存周期）和 `last_validated_at` 字段，到期自动降级或失效。对于用户删除请求，我们执行**全链路删除**：覆盖热/温/冷存储及备份数据，对于高敏感数据采用加密粉碎（Crypto-Shredding）技术，并承诺在 30 天内完成所有副本的物理清除。

**Q4: Context 注入的结构化接口落地?**
*   **A**: 我们已废弃非结构化的 XML 拼接，采用 **PersonaTool 结构化接口**。定义严格的 Protocol Buffer Schema（包含能力标签、偏好标签、置信度），限制 LLM 仅能读取白名单内的字段。在 Orchestrator 层增加数据脱敏与长度截断，在 LLM 输出层增加策略校验，确保画像数据仅作为背景参考，不被泄露给终端用户。
