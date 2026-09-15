# Core Chain 1 End-to-End Testing Guide
## 意图识别与动态信息补全链路测试指南

---

## 📋 测试概览

本测试套件覆盖**核心链路一：意图识别与动态信息补全**的所有验收标准：

| 验收点 | 测试覆盖 | 测试文件 |
|--------|----------|----------|
| 1. 路由准确率 | ✅ 完整 | `test_core_chain_1_intent_recognition.py::TestSuiteA` |
| 2. 追问停止机制 | ✅ 完整 | `test_core_chain_1_intent_recognition.py::TestSuiteB` |
| 3. LLM Judge 停止判断 | ✅ 完整 | `test_core_chain_1_intent_recognition.py::TestSuiteB::test_stop_mechanism_no_infinite_loop` |
| 4. 多模态兼容 | ✅ 完整 | `test_core_chain_1_intent_recognition.py::TestSuiteC` |
| 5a-5d. 特殊模式入口 | ✅ 完整 | `test_core_chain_1_intent_recognition.py::TestSuiteA::test_special_mode_detection_*` |

---

## 🚀 快速开始

### 方式1：使用测试脚本（推荐）

```bash
cd backend

# 运行所有测试
./tests/test_e2e/run_intent_recognition_tests.sh

# 仅运行单元测试
./tests/test_e2e/run_intent_recognition_tests.sh unit

# 仅运行E2E测试
./tests/test_e2e/run_intent_recognition_tests.sh e2e

# 仅运行性能测试
./tests/test_e2e/run_intent_recognition_tests.sh perf
```

### 方式2：使用 pytest 直接运行

```bash
cd backend

# 运行所有Core Chain 1测试
pytest tests/test_e2e/test_core_chain_1_intent_recognition.py -v

# 运行特定测试套件
pytest tests/test_e2e/test_core_chain_1_intent_recognition.py::TestSuiteA -v

# 运行单个测试
pytest tests/test_e2e/test_core_chain_1_intent_recognition.py::TestSuiteA::test_chitchat_vs_task_routing -v

# 运行性能测试
pytest tests/test_e2e/test_intent_recognition_performance.py -v -s
```

### 方式3：运行独立E2E脚本

```bash
cd backend

# 运行独立E2E测试（不需要pytest）
python tests/test_e2e/intent_clarification_e2e_test.py
```

---

## 📊 测试套件详解

### Suite A: 意图识别与路由准确性 (TestSuiteA)

**验收点覆盖**: 1, 4a, 4b, 5a, 5b, 5c, 5d

| 测试方法 | 描述 | 验收标准 |
|----------|------|----------|
| `test_chitchat_vs_task_routing` | 区分闲聊与复杂任务 | ✅ "帮我制定学习计划"不会误判为闲聊 |
| `test_special_mode_detection_translation` | 翻译模式触发 | ✅ 关键词准确触发translation |
| `test_special_mode_detection_prism` | 认知棱镜模式触发 | ✅ 关键词准确触发prism |
| `test_special_mode_detection_sprint` | 冲刺模式触发 | ✅ 关键词准确触发sprint |
| `test_execution_mode_routing` | 执行模式路由决策 | ✅ 正确路由到direct/langgraph |
| `test_combined_pattern_priority` | 组合模式优先级 | ✅ "制定"+"计划"优先于单独"学习" |

**关键断言示例**:
```python
# 不会把"帮我制定学习计划"误判为闲聊
assert intent != "chat", (
    "CRITICAL FAILURE: '帮我制定学习计划' was classified as 'chat'"
)
```

---

### Suite B: 信息充分性与追问循环 (TestSuiteB)

**验收点覆盖**: 2, 3

| 测试方法 | 描述 | 验收标准 |
|----------|------|----------|
| `test_required_field_detection` | 必需字段检测 | ✅ 缺失task_title时触发追问 |
| `test_clarification_question_generation` | 追问问题生成 | ✅ 生成相关、清晰的追问 |
| `test_stop_mechanism_no_infinite_loop` | **停止机制** | ✅ **信息充足时停止追问，防止无限循环** |
| `test_context_inference` | 上下文推断 | ✅ 从对话历史推断缺失信息 |
| `test_high_risk_confirmation` | 高风险操作确认 | ✅ 删除操作需要确认 |

**关键测试流程**:
```python
# Turn 1: 用户说"创建任务" → 询问标题
result1 = await checker.check(intent="create_task", entities={})
assert result1.status == SufficiencyStatus.NEED_CLARIFICATION

# Turn 2: 用户提供标题 → 停止追问
result2 = await checker.check(intent="create_task", entities={"task_title": "学习数学"})
assert result2.status == SufficiencyStatus.SUFFICIENT  # ← 关键断言

# Turn 3: 验证不会进入无限循环
result3 = await checker.check(...)
assert result3.status == SufficiencyStatus.SUFFICIENT  # ← 防止死循环
```

---

### Suite C: 多模态兼容性 (TestSuiteC)

**验收点覆盖**: 4

| 测试方法 | 描述 | 测试场景 |
|----------|------|----------|
| `test_voice_input_preprocessing` | 语音转文字语义理解 | 填充词、重复、停顿 |
| `test_mixed_language_input` | 中英混合输入 | "I want to study 数学" |
| `test_colloquial_expressions` | 口语化表达 | "搞个任务"、"弄个计划" |
| `test_voice_preprocessing_function` | 预处理函数测试 | 省略号替换、去重 |

**语音输入测试用例**:
```python
voice_cases = [
    ("嗯，帮我制定学习计划", "create", "With filler '嗯'"),
    ("那个，我想复习数学", "review", "With filler '那个'"),
    ("帮我...帮我安排时间", "create", "With repetition"),
]
```

---

### Suite D: 集成与性能 (TestSuiteD)

| 测试方法 | 描述 | 性能目标 |
|----------|------|----------|
| `test_unified_intent_router_integration` | 统一路由器集成 | ✅ 所有模式正确路由 |
| `test_classification_performance` | 分类延迟 | ✅ <50ms (Tier-1 P95) |
| `test_concurrent_classification` | 并发分类 | ✅ 无竞态条件 |
| `test_error_handling` | 错误处理 | ✅ 边界情况不崩溃 |

---

### Suite E: 真实场景模拟 (TestSuiteE)

完整用户流程测试：

| 场景 | 描述 | 测试方法 |
|------|------|----------|
| **学生创建学习计划** | 完整的多轮追问流程 | `test_student_study_plan_flow` |
| **考试冲刺模式** | 冲刺模式触发与路由 | `test_exam_prep_sprint_flow` |
| **翻译请求** | 翻译模式处理 | `test_translation_request_flow` |
| **认知棱镜** | 认知棱镜分析请求 | `test_cognitive_prism_flow` |
| **多轮追问** | 完整追问循环 | `test_multi_turn_clarification_flow` |

---

## 🔧 性能基准测试

**独立测试文件**: `test_intent_recognition_performance.py`

### 延迟目标

| 组件 | 目标 (P50) | 目标 (P95) |
|------|-----------|-----------|
| Tier-1 分类 | <10ms | <25ms |
| Sufficiency Check | <20ms | <50ms |
| Full Routing | <30ms | <100ms |

### 吞吐量目标

| 场景 | 目标 |
|------|------|
| 并发分类 | >100 req/s |
| 并发路由 | >50 req/s |
| 持续负载 | ≥80 req/s |

### 内存目标

| 组件 | 目标 |
|------|------|
| RequestRouter 实例 | <50MB |
| SufficiencyChecker 实例 | <10MB |

**运行性能测试**:
```bash
pytest tests/test_e2e/test_intent_recognition_performance.py -v -s
```

---

## 🐛 故障排查

### 问题1: BERT模型未加载导致测试失败

**症状**: 测试输出显示 "BERT classifier not available"

**解决**:
```bash
# 测试默认禁用BERT以加快速度
# 如需启用BERT，修改测试fixture:
router = RequestRouter(
    redis_client=mock_redis,
    enable_bert=True,  # ← 改为True
)
```

### 问题2: Redis连接失败

**症状**: "Redis connection refused"

**解决**: 测试使用mock Redis，无需真实Redis实例。如需真实测试：
```python
# 使用真实Redis
import redis
redis_client = await redis.from_url("redis://localhost")
router = RequestRouter(redis_client=redis_client)
```

### 问题3: 性能测试不稳定

**症状**: 每次运行延迟差异大

**解决**:
```bash
# 运行多次取平均值
for i in {1..5}; do
    pytest tests/test_e2e/test_intent_recognition_performance.py -v -s
done
```

---

## 📈 测试覆盖率

### 代码覆盖率报告

```bash
# 生成覆盖率报告
pytest tests/test_e2e/test_core_chain_1_intent_recognition.py \
    --cov=app.orchestration.request_router \
    --cov=app.orchestration.sufficiency_checker \
    --cov-report=html \
    --cov-report=term

# 查看HTML报告
open htmlcov/index.html
```

### 目标覆盖率

| 组件 | 当前覆盖率 | 目标覆盖率 |
|------|-----------|-----------|
| `request_router.py` | TBD | ≥85% |
| `sufficiency_checker.py` | TBD | ≥90% |
| `bert_intent_classifier.py` | TBD | ≥80% |

---

## ✅ 验收清单

在合并代码前，确保以下所有测试通过：

- [ ] **Suite A**: 意图识别测试全部通过
  - [ ] `test_chitchat_vs_task_routing` - ✅ 不会误判"帮我制定学习计划"为闲聊
  - [ ] `test_special_mode_detection_translation` - ✅ 翻译模式触发
  - [ ] `test_special_mode_detection_prism` - ✅ 认知棱镜模式触发
  - [ ] `test_special_mode_detection_sprint` - ✅ 冲刺模式触发
  - [ ] `test_execution_mode_routing` - ✅ 执行模式路由正确

- [ ] **Suite B**: 信息充分性测试全部通过
  - [ ] `test_stop_mechanism_no_infinite_loop` - ✅ **无无限追问循环**
  - [ ] `test_required_field_detection` - ✅ 缺失字段检测
  - [ ] `test_context_inference` - ✅ 上下文推断

- [ ] **Suite C**: 多模态测试全部通过
  - [ ] `test_voice_input_preprocessing` - ✅ 语音输入理解
  - [ ] `test_mixed_language_input` - ✅ 中英混合输入

- [ ] **Suite D**: 性能测试全部通过
  - [ ] `test_classification_performance` - ✅ 延迟满足要求
  - [ ] `test_concurrent_classification` - ✅ 并发处理正常

- [ ] **Suite E**: 真实场景测试全部通过
  - [ ] `test_student_study_plan_flow` - ✅ 完整流程
  - [ ] `test_multi_turn_clarification_flow` - ✅ 多轮追问

---

## 📝 测试报告模板

运行完整测试后，使用以下模板记录结果：

```markdown
## Core Chain 1 测试执行报告

**执行日期**: 2026-01-28
**执行人**: [Your Name]
**环境**: [Dev/Staging/Prod]

### 测试结果概览

| 套件 | 总数 | 通过 | 失败 | 通过率 |
|------|------|------|------|--------|
| Suite A: 意图识别 | 6 | 6 | 0 | 100% |
| Suite B: 信息充分性 | 5 | 5 | 0 | 100% |
| Suite C: 多模态 | 4 | 4 | 0 | 100% |
| Suite D: 集成与性能 | 4 | 4 | 0 | 100% |
| Suite E: 真实场景 | 5 | 5 | 0 | 100% |
| **总计** | **24** | **24** | **0** | **100%** |

### 性能指标

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| Tier-1 P95 延迟 | <25ms | 18ms | ✅ |
| Sufficiency Check P95 | <50ms | 42ms | ✅ |
| 并发吞吐量 | >100 req/s | 127 req/s | ✅ |

### 关键验收点

- [x] 路由准确率: 不会把"帮我制定学习计划"误判为闲聊
- [x] 追问停止机制: 信息充足时准确停止，无无限循环
- [x] 多模态兼容: 语音输入、中英混合正确理解
- [x] 特殊模式入口: 翻译、认知棱镜、冲刺模式准确触发

### 缺陷与改进

| ID | 描述 | 严重性 | 状态 |
|----|------|--------|------|
| - | 无 | - | - |

### 结论

**状态**: ✅ **通过验收**

所有核心链路一的验收标准均已满足，系统达到生产就绪状态。
```

---

## 🔗 相关文档

- [验收报告](./FINAL_ACCEPTANCE_REPORT.md)
- [架构文档](../../docs/00_项目概览/02_技术架构.md)
- [API参考](../../docs/02_技术设计文档/03_API参考.md)
- [CLAUDE.md](../../CLAUDE.md)

---

**最后更新**: 2026-01-28
**维护人**: Claude (Sonnet 4.5)
