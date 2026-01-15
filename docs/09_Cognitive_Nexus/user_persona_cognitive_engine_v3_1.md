# V3.1 (最终交付版) 顶级生产方案：用户画像与认知引擎
# Production-Grade User Persona & Cognitive Computing Engine V3.1 (Final Delivery)

## 1. 方案概述 (Executive Summary)

本方案是 V3.0 的最终加固版本，针对顶级合规审计（Top-tier Compliance Audit）与极端工程场景进行了**深度防御（Defense-in-Depth）**升级。

**V3.1 核心升级 (V3.1 vs V3.0)**:
1.  **审计级合规**: 从单纯的“GDPR 兼容”升级为**“审计就绪 (Audit-Ready)”**架构。引入 **Legal Hold (法律冻结)** 协议与 **Crypto-erase (加密抹除)** 标准，确保在面对监管调查与诉讼时具备完整证据链。
2.  **流式零信任**: 在流式处理链路中引入**“双人复核 (Double Check)”**与**“物理时钟同步”**，消除人为操作风险与微秒级并发乱序隐患。
3.  **画像可溯源**: 画像更新全链路引入 `audit_token` 与版本控制，支持秒级状态回滚（State Rollback），确保算法事故“可观测、可逆转”。

---

## 2. 合规与审计深度防御 (Legal & Audit Defense)

### 2.1 年龄校验逻辑修正 (Refined Age Verification)
**原则**: 最小化数据收集原则 (Data Minimization) 与 用户同意优先 (Consent First)。

*   **默认策略 (Default)**:
    *   仅基于**注册强信号**（生日/支付验证）与**基础行为特征**（设备家长模式）进行判定。
    *   **移除**: 将“语调/情感分析”从默认识别管道中**移除**，避免在未经授权下收集生物/心理特征数据。
*   **高风险/可选策略 (High-Risk/Opt-in)**:
    *   仅在检测到极高风险行为（如疑似诱导未成年人消费、极端辱骂）或用户**显式开启**“智能防护模式”时，才激活 NLP 情感分析模块。
    *   **误判申诉**: 在“未成年人保护模式”触发的弹窗中，显著展示“我不是未成年人”申诉通道，接入人工客服（SLA < 4h），并监控**误判率 (False Positive Rate)** 指标。

### 2.2 法效保留协议 (Legal Hold Protocol)
解决“自动清理”与“证据保留”的冲突。

*   **机制**:
    *   在 L1 (Clickstream) 清理任务（Cleanup Worker）中注入 **Legal Hold Check** 逻辑。
    *   **流程**:
        1.  合规官/法务通过 Admin Panel 对特定 `user_id` 或 `device_id` 下发 `LegalHoldTag`。
        2.  清理脚本运行前，校验 `if user.has_tag("LEGAL_HOLD")`。
        3.  若命中，**跳过**该用户数据的 TTL 清理，将其原始流数据转存至 **WORM (Write Once Read Many)** 隔离存储桶，直至 Hold 解除。
*   **审计**: 所有 Hold 的开启与解除操作，必须记录 `admin_id`, `legal_case_ref` (案件编号), `timestamp`。

### 2.3 云原生加密抹除 (Cloud-native Crypto-erase)
替代传统的物理覆写（DoD 5220.22-M 在云盘上不可靠）。

*   **原理**:
    *   利用云存储（AWS S3 / GCS）的 KMS 集成。
    *   每个用户的高敏感数据（L3 画像）使用**用户级密钥 (User-Level Data Key, DEK)** 加密存储。
*   **销毁流程**:
    1.  用户发起“注销账号”或“行使被遗忘权”。
    2.  系统调用 KMS 接口**销毁该用户的 DEK**。
    3.  数据因无法解密而瞬间呈现“加密碎纸”状态 (Cryptographically Shredded)。
    4.  **存证**: 系统生成 `CryptoShreddingCertificate`，包含 `key_id`, `destruction_time`, `cloud_provider_ack`，作为合规存证。

---

## 3. 流式链路安全审计 (Stream Security & Audit)

### 3.1 DLQ 重放协议 (DLQ Replay Governance)
防止“脏数据注入”与“内部人员作恶”。

*   **DLQ 架构**:
    *   所有处理失败的消息进入 Dead Letter Queue (Kafka Topic: `stream.dlq.persona`).
*   **重放规范**:
    *   **双人复核 (Two-Person Rule / Double Check)**: 任何针对 DLQ 数据的**修改重放**（如修复 JSON 格式），必须经由两人操作：A 提交修改提案，B 审核批准。
    *   **注入审计**: 手动注入的消息 Header 中必须强制挂载：
        *   `x-audit-admin-id`: 操作员 ID
        *   `x-audit-approver-id`: 审批员 ID
        *   `x-audit-reason-code`: 变更原因代码 (e.g., `FIX_SCHEMA_01`)
    *   消费者逻辑校验此 Header，缺失则拒绝处理。

### 3.2 高并发时序增强 (Enhanced UUID Ordering)
解决 UUIDv7 在极端并发（>10k TPS/node）下的微秒级排序不确定性。

*   **复合主键策略**:
    *   使用 `UUIDv7` + `PhysicalClock` + `SequenceID`。
    *   **逻辑**:
        1.  **UUIDv7**: 提供毫秒级排序。
        2.  **NTP 物理时钟**: 在 Kafka Broker 端打入 `ingestion_timestamp` 作为物理参考。
        3.  **Atomic Sequence**: 在同一毫秒内，通过 Redis Atomic Increment 或内存计数器生成 `seq_id` (0-999)。
    *   **排序键**: `SortKey = (ingestion_timestamp, uuid_timestamp, seq_id)`。确保即使 UUID 碰撞或时钟回拨，依然具备严格的因果序。

---

## 4. 画像工具规范 (PersonaTool Specs)

### 4.1 版本化落地 (Versioned Schema)
确保 LLM 使用的画像数据具有可追溯性。

*   **输入参数增强**:
    ```protobuf
    message GetPersonaRequest {
      string user_id = 1;
      string purpose = 2; // "learning_recommendation", "chat_style"
    }

    message PersonaResponse {
      string persona_version = 1; // e.g., "v3.1.20231027"
      string audit_token = 2;     // Encrypted token linking to source events
      repeated string tags = 3;
      map<string, float> capabilities = 4;
      string last_update_event_id = 5; // The event ID that triggered the last update
    }
    ```
*   **作用**: 当 LLM 产生幻觉或不当回复时，可以通过 `persona_version` 和 `audit_token` 精确复现当时的画像状态，排查是画像数据错误还是模型推理错误。

### 4.2 状态回滚机制 (State Rollback)
应对“算法漂移”或“污染攻击”。

*   **快照机制 (Snapshotting)**:
    *   每次画像发生**重大变更**（如能力值波动 > 10% 或标签集变动）时，在冷存储（S3/Coldline）触发一次 JSON 快照。
*   **回滚流程**:
    1.  监控系统检测到某用户群体的画像出现异常（如集体判定为“极低能力”）。
    2.  Admin 发起 `RollbackCommand(user_group_id, target_timestamp)`。
    3.  系统从冷存储加载最近的正常快照，**覆写** Redis 热存与 Postgres 温存。
    4.  发送 `PersonaRolledBack` 事件，通知下游服务刷新缓存。
    5.  **时效**: 回滚操作需在 < 30秒内生效。

---

## 5. 数据治理细则 (Data Governance Details)

### 5.1 脱敏字典 (Masking Dictionary)
定义数据流出生产环境（如进入日志、数仓、测试环境）时的严格脱敏规则。

| 字段类型 | 示例 | 脱敏策略 | 算法/逻辑 |
| :--- | :--- | :--- | :--- |
| **User ID** | `u_123456` | **Pseudonymization** | `HMAC-SHA256(uid, rotating_salt)` |
| **Geo/Location** | `39.9, 116.3` | **Generalization** | 降级至**城市中心点**或仅保留行政区划 (City Level) |
| **IP Address** | `192.168.1.1` | **Truncation** | 保留前三段，最后一段置 0 (`192.168.1.0`) |
| **Email/Phone** | `test@a.com` | **Masking** | 首尾保留，中间星号 (`t***@a.com`) |
| **Persona Tags** | `anxiety_high` | **Suppression** | 高敏感标签（心理/医疗类）直接**丢弃**，不输出到非生产环境 |

### 5.2 分层评估指标 (Stratified Metrics)
防止总体指标掩盖局部偏见 (Simpson's Paradox)。

*   **要求**: 所有的算法模型指标 (AUC, RMSE, Precision/Recall) 必须产出**分层报告**。
*   **关键分层维度**:
    1.  **年龄段**: <14, 14-18, >18 (确保未成年人保护逻辑不影响成人体验，反之亦然)。
    2.  **设备类型**: High-end (iOS/Flagship) vs. Low-end (Entry Android) (防止低端机用户因交互卡顿被误判为“能力低”)。
    3.  **学科类型**: 语言类 vs. 逻辑/数理类 (不同学科的认知模式不同)。
*   **验收标准**: 各分层间的指标差异 (Gap) 不得超过 5%，否则视为模型存在群体性偏差 (Bias)，禁止上线。

---

## 6. 最终澄清问题回复 (Final Q&A)

**Q1: 引入 "Legal Hold" 是否会导致存储成本失控？**
*   **A**: 不会。Legal Hold 是**异常处理机制**，而非默认状态。根据历史数据，处于法律调查或合规冻结状态的用户比例通常极低（< 0.1%）。此外，Hold 数据存储在低成本的 WORM 冷存储（Archive Tier）中，成本仅为热存储的 1/10。我们通过精细的 TTL 策略和分级存储，在确保合规底线的同时，将总拥有成本 (TCO) 维持在可控范围。

**Q2: "双人复核 (Double Check)" 会显著降低运维效率吗？**
*   **A**: 这是为了安全必须付出的代价，但我们通过工具化降低了摩擦。我们区分了“自动重试”与“人工修正”。99% 的网络抖动类错误由系统自动指数退避重试解决。仅有 <1% 的 schema/format 致命错误需要人工介入。对于这部分极少量的核心数据，双人复核是防止“内部恶意篡改”的必要防火墙，通过集成的 Admin Dashboard，整个 Approve 流程可在分钟级完成。

**Q3: 如何证明 "Crypto-erase" 真正销毁了数据？**
*   **A**: 依靠**密码学保证**与**审计日志**。相比于物理覆写（难以验证云盘底层是否真写了），销毁密钥是确定性的操作。一旦 KMS 销毁了主密钥 (CMK) 或数据密钥 (DEK)，密文即在数学意义上不可还原。我们提供的 `CryptoShreddingCertificate` 包含了云厂商 KMS 返回的“密钥销毁确认回执”，这在通过 SOC2 和 ISO27001 审计时是业界公认的最高效力证据。
