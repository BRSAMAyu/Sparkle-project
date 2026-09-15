# ADR-0002: Single Source of Truth for AgentService Proto

## Status
Accepted

## Context
项目存在 `agent_service.proto` 与 `agent_service_v2.proto` 的并行维护，导致：
- 定义重复与不一致
- 生成代码不稳定
- 服务端/客户端实现难以对齐

## Decision
统一以 `proto/agent_service.proto` 作为唯一契约，移除 v2 文件及其生成产物。

## Consequences
- ✅ 单一契约降低维护成本
- ✅ 生成代码链路稳定
- ❗ 需要更新文档与引用路径

## Alternatives Considered
- 保留 v2 并补齐实现（成本高、迁移复杂）
- 兼容双版本（长期维护负担更大）
