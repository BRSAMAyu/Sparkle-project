# P1 集成验证缺口修复记录

日期：2026-04-29
提交：f170379f（+ a5e1e053 中的部分更改）

## 修复清单

### P1-1: 无跨服务真实E2E测试
**问题**: 5个 `FULL_STACK_TESTS=1` pytest 文件从未在 CI 中运行，`e2e_multiturn_test.py` 是唯一验证全栈的脚本但不在 CI 中。

**修复**:
- `scripts/run_e2e_smoke.sh`: 新增 `full-stack` 命令，运行全部 5 个 FULL_STACK_TESTS 套件
- `.github/workflows/e2e-smoke.yml`: 添加 "Full-Stack Integration Tests (5 suites)" CI 步骤
- 触发器扩展: push to main/develop + PR to main（不仅是 schedule）

### P1-2: 无Flutter集成测试
**问题**: `integration_test/app_test.dart` 存在 2 个 lint 警告，`full_stack_e2e_test.dart` 未验证。

**修复**:
- 修复 `app_test.dart` 导入排序（dart:ui 放首位，其余按字母序）
- `flutter analyze` 确认 0 error
- `full_stack_e2e_test.dart` 已通过 `run_e2e_smoke.sh flutter` 在 CI 中运行
- `app_test.dart` 需模拟器（macOS runner），由 `e2e-tests.yml` 覆盖（scheduled + manual）

### P1-3: 无Go集成测试
**问题**: `e2e_chat_orchestrator_test.go` 使用错误导入路径 `github.com/user/sparkle` 且引用不存在的类型，无法编译。

**修复**:
- 完全重写测试文件：
  - 修复导入路径为 `github.com/sparkle/gateway`
  - 使用正确的 `agent.NewClient(cfg)` 签名（返回 `(*Client, error)`）
  - 添加 `cfg.AgentAddress = "localhost:50051"` 避免空地址
  - 优雅跳过（`t.Skipf`）替代 `t.Fatalf` 当 gRPC 不可用时
  - 添加 nil-safety 防止 `resp` 为空时 panic
- `go vet -tags=integration ./internal/handler/` 通过
- 新增 `scripts/run_e2e_smoke.sh go` 命令运行 Go 集成测试
- CI 步骤已添加到 e2e-smoke.yml
- Go 版本从 1.22.0 修正为 1.24.0（匹配 go.mod）

### P1-4: 无性能基线数据
**问题**: `quality/performance_baselines.json` 只有 target/warning/critical 阈值，无 actual 测量值。

**修复**:
- 新建 `scripts/populate_performance_baselines.py`：
  - 测量 gateway P95 延迟（5 次采样）
  - 测量 backend 健康检查延迟
  - 测量 WebSocket 连接延迟
  - 写入 `actual`/`p95`/`measured_at`/`sample_size` 字段
  - 支持 `--write` 写回文件、`--ci` 模式（失败时 warning 而非 error）
- CI 步骤已添加到 e2e-smoke.yml

### P1-5: 无压力测试
**问题**: `test_celery_stress.py` 存在但不在 CI 中运行。

**修复**:
- `.github/workflows/benchmark.yml`: 新增 `stress-tests` job（schedule + workflow_dispatch）
  - 包含 PostgreSQL + Redis 服务容器
  - 运行 `test_celery_stress.py`（5 个压力场景）
  - 移除 `|| true` 使失败可见
- `.github/workflows/e2e-smoke.yml`: 添加轻量 Celery 压力步骤（continue-on-error）

### P1-6: DPO/SGW v2与主系统无连接
**问题**: `scripts/sgw_v2/` 有 42 个文件完整实现 DPO/RL，但 `orchestrator.py` 和 `policy_engine.py` 零导入。

**修复**:
- 在 `docs/engineering/technical_debt_register_2026-03-22.md` 注册 TD-011
  - 记录 DPO 完整实现但零生产接线
  - 定义退出条件：导入 DPOPolicy、kill switch 控制、审计日志、E2E 测试
  - 优先级 P2（非上线阻碍，Era 2 Intelligence Phase 接入）

## Agent 审查修复项

审查发现 2 个阻断 + 5 个警告，全部已修复：
1. ✅ DATABASE_URL 从裸名称修正为完整连接字符串
2. ✅ agent.NewClient 添加 AgentAddress，失败时 Skip 而非 Fatal
3. ✅ WebSocket resp nil-safety
4. ✅ 第二次测量从 gateway 改为 backend 域
5. ✅ regression-report 移除 stress-tests 依赖（避免跳过时阻塞）
6. ✅ 移除 `|| true` 使压力测试失败可见
7. ✅ Go 版本 1.22→1.24 匹配 go.mod
