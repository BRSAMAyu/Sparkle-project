# 技术设计文档

适用对象：需要修改接口、协议、数据库、编排逻辑或关键架构的开发者。

## 推荐阅读

1. [06_框架概览](./06_框架概览.md)
2. [03_API参考](./03_API参考.md)
3. [10_gRPC协议定义](./10_gRPC协议定义.md)
4. [04_数据库设计](./04_数据库设计.md)
5. [02_知识星图系统设计 v3.0](./02_知识星图系统设计_v3.0.md)

## 文档分类

| 分类 | 文档 |
|------|------|
| **架构全景** | [01_技术白皮书](./01_技术白皮书.md)、[06_框架概览](./06_框架概览.md) |
| **API 与协议** | [03_API参考](./03_API参考.md)、[05_API设计](./05_API设计.md)、[10_gRPC协议定义](./10_gRPC协议定义.md) |
| **数据与存储** | [04_数据库设计](./04_数据库设计.md)、[11_Docker配置详解](./11_Docker配置详解.md) |
| **专项设计** | [02_知识星图系统设计 v3.0](./02_知识星图系统设计_v3.0.md)、[09_Design System V2](./09_Design_System_V2_指南.md)、[12_ASR与文档清洗API](./12_ASR与文档清洗API.md) |
| **AI 编排** | [AI_WORKFLOW_STRATEGY](./AI_WORKFLOW_STRATEGY.md)、[EXECUTABLE_PLAN_SCHEMA](./EXECUTABLE_PLAN_SCHEMA.md) |
| **Schema 与规则** | [FEEDBACK_PAYLOAD_SCHEMA](./FEEDBACK_PAYLOAD_SCHEMA.md)、[GROUNDING_VALIDATOR_RULES](./GROUNDING_VALIDATOR_RULES.md) |
| **系统对齐** | [GROWTH_LOOP_CLOSURE](./GROWTH_LOOP_CLOSURE.md)、[PREFERENCE_SYSTEM_ALIGNMENT](./PREFERENCE_SYSTEM_ALIGNMENT.md) |

## 阅读原则

- 优先读描述当前系统事实的文档
- 审查总结、阶段对齐稿、历史改进提案只在需要追溯背景时查看归档
- 若某文档与代码现状冲突，以代码与当前协议定义为准
