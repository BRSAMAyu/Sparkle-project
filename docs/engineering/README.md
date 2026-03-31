# 工程规范

适用对象：需要理解 CI 门禁、工程规范、质量基线与迁移约束的开发者。

## 当前推荐阅读

1. [quality_guardrails.md](./quality_guardrails.md)
2. [contract_guardrails.md](./contract_guardrails.md)
3. [flutter_quality_gate.md](./flutter_quality_gate.md)
4. [proto_dual_stack_migration.md](./proto_dual_stack_migration.md)

## 本目录保留标准

- 仍然影响 CI、质量门禁、迁移规则的文档
- 仍然会被团队执行或检查的工程基线

## 使用建议

- 改接口或协议前，看 `contract_guardrails.md` 与 `proto_*`
- 改前端质量门禁前，看 `flutter_quality_gate.md`
- 做稳定性与工业化收口时，看 `definition_of_done_industrial.md` 与 `industrial_readiness_baseline.md`
