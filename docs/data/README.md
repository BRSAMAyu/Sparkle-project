# Data Engineering & Science

本文档包含数据埋点规范、离线评估协议以及数据治理相关文档。

## Index

| Document | Description | Last Updated |
| :--- | :--- | :--- |
| [埋点事件字典](./TRACKING_EVENT_DICTIONARY.md) | **[契约]** 客户端与后端必须严格遵守的埋点 Schema | 2026-01-04 |
| [离线评估协议](./OFFLINE_EVALUATION_PROTOCOL.md) | **[裁判]** 模型上线前的唯一准入标准 | 2026-01-04 |

## Governance

*   **Schema Evolution**: 所有变更需通过 PR 评审，严禁私自新增必填字段。
*   **Privacy**: 严禁明文存储 PII，遵守 GDPR/CCPA 原则。
