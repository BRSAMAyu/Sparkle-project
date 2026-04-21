# Rule AQ

Stage 29.5 选择 Python 手写 `UserStateV1` schema 保留路径。

因此新增 Rule AQ：

1. `backend/app/state_aggregator/schema.py` 的 `UserStateV1` 必须与 `proto/user_state.proto` 的 `UserStateV1` 同步演化。
2. `backend/app/gen/user_state_pb2.py` 是 Python 侧的 proto 权威镜像；手写 schema 只能作为运行时 adapter，不得脱离 proto 独立扩张。
3. 顶层字段的数量、名称、wrapper 类型和 optional 语义必须等价。
4. `emotion_hint` 保留为历史 Python-only stub；`emotion_hint_reserved` 保留在 proto 作为占位字段，两者均不得重新激活为业务字段。

自动化：

- `scripts/check_rule_aq_python_proto_parity.py`
- `scripts/run_all_rule_guards.sh --rule AQ`
