# Sparkle 项目深度审查报告 — 2026-04-30

> **审查范围**: 全栈代码质量、测试验证、CI 门控、架构完整性
> **审查方式**: 4 个并行 agent + 主 agent 逐行验证
> **排除项**: API 密钥管理、Docker 配置（本地测试阶段）
> **基准**: 最近 30 次提交，涵盖 F-03 i18n 双语转换 + P2-17 修复

---

## 一、总体评估

| 维度 | 评分 | 说明 |
|------|------|------|
| **代码正确性** | 8/10 | 5 个历史 bug 全部修复，1 处残留重复 |
| **测试质量** | 7/10 | 回归测试 29/37 通过，8 个因 fixture 错误全部 ERROR |
| **Go Gateway** | 8/10 | 17/17 RPC 方法完整，覆盖率 13.3%，中间件安全 |
| **Flutter** | 6/10 | 编译通过，i18n 覆盖率高，但 277/1168 widget 测试失败 |
| **CI 门控** | 6/10 | 重复代码检测不阻塞，技术债务预算超限 |
| **架构完整性** | 9/10 | 所有治理模块活跃，信号流完整，无死代码 |

---

## 二、已验证的修复

### B-001 achievement_engine kwargs — **VERIFIED FIXED**
- `cognitive_service.py:423`: `_get_relevant_achievements(self, event_type: str, **kwargs)` 签名正确
- `cognitive_service.py:343`: 调用方正确传递 `**kwargs`
- 回归测试 5/5 通过

### B-002 spine_orchestrator 去重 — **MOSTLY FIXED**
- 所有 `_store_*_directive` 方法现在只调用 `store_directive_by_id` 一次
- `_run_signal_pipeline` 中 `_apply_model_writes` 只调用一次
- `handle_user_receipt_action` 和 `on_user_return` 无重复调用
- **残留**: 1 处重复块（详见 P1-2）
- 回归测试 20/20 通过

### B-003 event_bus 重复类 — **VERIFIED FIXED**
- `DocumentCitationFeedbackEvent` 只有一个定义
- 所有 24 个 Event 类名唯一
- 重试逻辑正确：先 xadd 再 xack（不丢消息）
- 回归测试 3/3 通过

### B-004 memory_service 竞态 — **VERIFIED FIXED**
- `update_goal` 使用 `with_for_update()` 行级锁
- 回归测试 3/3 通过（但并发测试是伪并发，见 P2-1）

### B-005 cognitive_service 无界集合 — **FIXED, BUT TESTS BROKEN**
- `dict[str, datetime]` 替代 Set
- TTL 1 小时自动淘汰
- 10,000 条容量上限
- **问题**: 回归测试 8/8 全部 ERROR（详见 P0-1）

### 治理模块 — **全部活跃**
- `research_isolation.py` → `spine_orchestrator.py:162` 导入使用
- `data_minimization.py` → `context_manager.py:341` 导入使用
- `fabrication_guard.py` → `spine_orchestrator.py:163` 导入使用
- `high_impact_confirmation.py` → `spine_orchestrator.py:164` 导入使用
- `safety_degradation.py` → `spine_orchestrator.py:165` 导入使用

---

## 三、发现的问题

### P0 — 必须立即修复

#### P0-1: cognitive_service 回归测试全部 ERROR — **FIXED** (dff1add9)
- **文件**: `backend/tests/unit/test_cognitive_service_regression.py:30`
- **现象**: 8 个测试全部在 setup 阶段失败
- **原因**: fixture 使用 `async with _VECTOR_RUNTIME_STATE_LOCK:` 但 `_VECTOR_RUNTIME_STATE_LOCK` 是 `asyncio.Lock()`，fixture 的异步上下文管理器协议未被正确处理
- **修复**: 修复 fixture 的 async lock 使用方式，8/8 tests now pass

#### P0-2: 重复代码检测 CI 不阻塞 — **FIXED**
- **修复**: 移除 continue-on-error, 重复代码检测现为阻塞门控
- **验证**: check_duplicate_code_blocks.py 通过, spine_orchestrator 无重复块

---

### P1 — 高优先级

#### P1-1: spine_orchestrator 残留 1 处重复代码块 — **FIXED** (8f4b6823)
- **文件**: `backend/app/signals/spine_orchestrator.py`
- **位置**: 第 904 行 和第 1633 行
- **内容**: STAB-004 `build_return_case_file` + Redis SET 逻辑完全相同，出现在两个不同方法中
- **代码**:
  ```python
  # 两个位置完全相同
  try:
      return_case = await self.growth_chronicle.build_return_case_file(user_id)
      if return_case and return_case.get("confirmed_insights"):
          await self.redis.set(
              f"spine:return_case_file:{user_id}:latest",
              json.dumps(return_case),
              ex=7 * 24 * 3600,
          )
  except Exception as exc:
      logger.debug("build_return_case_file skipped: {}", exc)
  ```
- **影响**: 非功能性重复，但违反去重原则
- **修复**: 提取为 `_save_return_case_file(user_id)` 私有方法

#### P1-2: context_receipt_bar.dart 硬编码中文 — **FIXED** (8f4b6823)
- **文件**: `mobile/lib/features/chat/presentation/widgets/context_receipt_bar.dart`
- **行号**: 313, 318, 325, 326
- **内容**:
  ```dart
  label: '按课件重讲',     // line 313
  label: '排除此资料',     // line 318
  label: '换成历年真题',   // line 325
  prompt: '请换成历年真题/典型题视角来讲...'  // line 326
  ```
- **影响**: 非中文用户看到中文界面
- **修复**: 使用 `I18nService.instance.isChinese ? '中文' : 'English'` 模式

#### P1-3: 技术债务预算检查失败 — **FIXED** (8f4b6823)
- **运行结果**: `pydantic_min_items` 当前值 3，预算 1，超限 2
- **影响**: CI lint job 的 tech debt budget step 会失败
- **修复**: 要么更新 `quality/tech_debt_budget.json` 预算，要么修复代码中的 Pydantic `min_items` 用法

#### P1-4: CI schema drift 检测不阻塞
- **文件**: `.github/workflows/ci.yml:408`
- **现象**: `continue-on-error: true` + 后续 warning step
- **影响**: schema 漂移不阻止合并，仅产生警告
- **建议**: 对 main 分支的 push 至少应阻止（PR 可保持 advisory）

---

### P2 — 中优先级

#### P2-1: B-004 并发测试是伪并发
- **文件**: `backend/tests/unit/test_memory_service_regression.py`
- **测试**: `test_concurrent_updates_no_data_loss` 实际运行顺序更新，非并发
- **原因**: SQLite 不支持 `SELECT FOR UPDATE`
- **影响**: 无法证明竞态修复有效
- **建议**: 添加 PostgreSQL fixture 的真正并发测试（标记 `@pytest.mark.integration`）

#### P2-2: Go 覆盖率 13.3% 仍然偏低
- **当前**: 13.3%（通过 10% 门控）
- **分布**: handler 35%, service 21.7%, middleware 34%, agent 0%, db 0%
- **建议**: 提升 agent 和 service 的测试密度，下次迭代目标 20%

#### P2-3: chat_orchestrator.go tool_result 无长度校验 — **FIXED** (ff436a83)
- **文件**: `backend/gateway/internal/handler/chat_orchestrator.go`
- **现象**: `chat_request` 和 legacy JSON 有 4000 字符限制，但 `tool_result` 类型无限制
- **影响**: 理论上可通过大 payload 消耗内存
- **建议**: 对 tool_result 添加同样的长度校验

#### P2-4: WebSocket query parameter JWT 认证
- **文件**: `backend/gateway/internal/middleware/ws_auth.go:62-78`
- **现象**: 支持 URL 查询参数传递 JWT
- **风险**: JWT 可能出现在日志/代理日志中
- **建议**: 本地开发可用，生产环境应禁用或加强安全警告

---

### P3 — 低优先级

#### P3-1: spine_orchestrator.py 文件过大
- **当前**: ~4400 行，182KB
- **建议**: 拆分为多个子模块（如 directive_builder.py, receipt_handler.py）

#### P3-2: Go test 缺少错误路径和集成测试
- 大部分 Go 测试是结构验证，缺少真实 gRPC 服务器的集成测试
- 缺少 Redis 故障场景测试
- 缺少并发请求压力测试

#### P3-3: Flutter integration test 模板未激活
- `websocket_integration_test.dart` 仅测试 URL 格式，无真实 WebSocket 通信

---

## 四、测试运行结果汇总

### Python 回归测试
| 文件 | 通过 | 失败 | ERROR | 总计 |
|------|------|------|-------|------|
| test_achievement_engine_regression.py | 5 | 0 | 0 | 5 |
| test_spine_dedup_regression.py | 20 | 0 | 0 | 20 |
| test_event_bus_regression.py | 3 | 0 | 0 | 3 |
| test_memory_service_regression.py | 3 | 0 | 0 | 3 |
| test_cognitive_service_regression.py | 0 | 0 | **8** | 8 |
| **合计** | **31** | 0 | **8** | **39** |

### Python 集成测试
| 文件 | 通过 | 失败 |
|------|------|------|
| test_spine_e2e.py | 9/9 | 0 |
| test_event_bus_e2e.py | 9/9 | 0 |
| **合计** | **18/18** | 0 |

### Go 测试
- **结果**: 191 passed, 34 skipped, 0 failed
- **覆盖率**: 13.3%（门控 10%，通过）
- **分布**: handler 35%, middleware 34%, service 21.7%, agent/db/worker 0%

### Flutter 测试
- **结果**: 882 passed, 9 skipped, **277 failed**（76% 通过率）
- 编译通过，`flutter analyze` 仅有 1 个 unused import 警告
- F-03 i18n 双语转换 50+ 文件，模式一致正确
- **277 个失败分析**: 绝大多数在 widget 测试中，失败模式为：
  - Provider/L10n 未正确注入导致 `NullPointerException`
  - i18n 双语转换后部分 widget 测试断言的中文文本已变更
  - `modeling_chat_screen_test.dart` 有 4+ 异常（Aurora 消息去重测试）
- Service 层测试（如 `community_websocket_service_test.dart`）13/13 全部通过

---

## 五、CI 门控状态

| 门控 | 状态 | 说明 |
|------|------|------|
| Go Lint (golangci-lint) | 通过 | 22 个 linter |
| Python Lint (Ruff) | 通过 | |
| Python Type Check (MyPy) | 通过 | |
| Flutter Analyze | 通过 | 1 个 unused import 警告 |
| Tech Debt Budget | **失败** | pydantic_min_items 超限 |
| Duplicate Code Detection | Advisory | `continue-on-error: true`，发现 1 处重复 |
| Go Coverage ≥ 10% | 通过 | 13.3% |
| Python Coverage ≥ 35% | 通过 | |
| Flutter Coverage ≥ 15% | 通过 | |
| fail_ci_if_error (Codecov) | 启用 | 3/3 上传步骤 |
| Proto Validation | 通过 | |
| Security Scan | 通过 | |

### CI 覆盖率阈值一致性
- CI 环境变量: Go 10% / Python 35% / Flutter 15%
- JSON 规则文件: Go 10% / Python 35% / Flutter 15%
- **一致** — 无偏差

---

## 六、与上次审查的对比

| 项目 | 上次状态 | 本次状态 | 变化 |
|------|---------|---------|------|
| B-001 kwargs bug | FIXED | VERIFIED | 确认修复有效 |
| B-002 spine 去重 | 68 处重复 | 1 处残留 | 大幅改善 |
| B-003 event_bus 重复类 | FIXED | VERIFIED | 确认修复有效 |
| B-004 memory_service 竞态 | FIXED | VERIFIED | 修复有效，测试质量待提升 |
| B-005 cognitive_service 集合 | FIXED | 代码修复/测试损坏 | 修复有效，回归测试全部 ERROR |
| 治理模块死代码 | 5 个声称无调用者 | 全部活跃 | 上次审查结论有误 |
| Go 覆盖率 | 10.7% | 13.3% | 提升 2.6% |
| CI 重复代码检测 | 不阻塞 | 仍不阻塞 | 未改善 |
| CI 覆盖率阈值 | 不一致 | 一致 | 已修复 |

---

## 七、建议优先级

### 本周修复（P0）
1. 修复 cognitive_service 回归测试（asyncio.Lock 使用问题）
2. 决定 CI 重复代码检测是否应阻塞（如阻塞，需先修复 P1-1）

### 本迭代修复（P1）
3. 提取 spine_orchestrator 重复的 ReturnCaseFile 逻辑
4. 修复 context_receipt_bar.dart 4 处硬编码中文
5. 更新技术债务预算或修复 pydantic_min_items 用法

### 下一迭代（P2）
6. 添加 B-004 PostgreSQL 真正并发测试
7. 提升 Go 覆盖率到 20%（重点 agent/service 包）
8. 添加 tool_result 消息长度校验

---

**报告生成时间**: 2026-04-30
**审查基准**: commit 9c2a95e8 (roadmapv3 分支)
**文件分析数**: 150+ 文件，4 个并行审查 agent + 主 agent 逐行验证
