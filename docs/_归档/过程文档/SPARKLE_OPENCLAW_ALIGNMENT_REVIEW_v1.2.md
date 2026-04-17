# Sparkle × OpenClaw 对齐审查文档 v1.2

> 日期：2026-03-28
> 状态：继续增量交付；已补齐 Phase 5 / 6 的一部分能力与回归验证，仍未达到 6 个 Phase 全量完工

## 1. 本次续做新增范围

### Phase 5 部分补齐

- `mobile/lib/features/task/presentation/widgets/execution_result_renderer.dart`
  - 新增执行结果渲染器
  - 支持 `plainText / structured / markdown / codeBlock / linkList` 自动路由
  - 支持 artifact 列表、图片缩略预览、链接复制
  - 自审修复：当结果同时包含摘要与来源链接时，改为 mixed 渲染，不再丢失摘要正文
- `mobile/lib/features/task/presentation/widgets/execution_approval_card.dart`
  - 审批卡从原始摘要切换为 `ExecutionResultRenderer`
  - 结果预览改为可扩展的结构化展示
- `backend/app/services/execution_service.py`
  - 为 `classify_task()` 增加短 TTL 缓存
  - 自审修复：缓存从单实例改为跨 `ExecutionService` 实例共享，避免 API 请求级实例化导致缓存形同虚设
  - 缓存 key 改为兼容当前 `Task` 模型字段的稳健构造
- `backend/app/services/execution_template_service.py`
  - 为 5 个内置模板补充 `optimized_prompt`
- `backend/app/adapters/openclaw/intent_translator.py`
  - 将模板优化 prompt 注入到执行侧 system instructions

### Phase 6 部分补齐

- `backend/app/services/execution_profile_service.py`
  - 聚合 `estimated_time_saved_minutes`
  - 用户画像与管理端聚合均可返回节省时间统计
- `backend/app/api/v1/executions.py`
  - `GET /executions/profile/summary` 响应新增 `estimated_time_saved_minutes`
- `mobile/lib/core/network/api_endpoints.dart`
  - 新增执行画像与连接状态 endpoint 常量
- `mobile/lib/features/report/presentation/screens/learning_report_screen.dart`
  - 新增“AI执行助手”板块
  - 展示总执行数、成功率、节省时间、按类型分布

### Phase 1 体验回归修复

- `mobile/lib/features/task/presentation/screens/task_execution_screen.dart`
  - 自审修复：模板列表恢复为全部展示，不再错误截断为前 3 个

### 测试补强

- `backend/tests/unit/test_openclaw_phase3.py`
  - 增加节省时间字段断言
- `backend/tests/unit/test_openclaw_phase4.py`
  - 增加 classify cache 命中回归测试

## 2. 当前累计完成面

### 已具备的主链路

- Phase 1
  - 执行状态指示器、审批卡、模板卡、拒绝理由收集、感官反馈接线
- Phase 2
  - Orchestrator 执行建议检测
  - 聊天流执行建议卡
  - 聊天内联执行摘要卡
  - 执行助手 Agent profile 与 UX envelope 基础接线
- Phase 3
  - 审批速度、任务类型倾向、质量敏感度、拒绝情绪/安全顾虑等学习信号
  - 执行画像聚合与 replanner 参数回流
- Phase 4
  - 基础连接状态 API
  - 执行画像 / 管理端 dashboard API 骨架
- Phase 5
  - 结果内容渲染器
  - classify cache
  - 模板 prompt 精调接线
- Phase 6
  - 学习报告页“AI执行助手”板块
  - 管理端 dashboard API

## 3. 本轮验证

### 后端测试

已通过：

```bash
backend/venv/bin/pytest \
  backend/tests/unit/test_openclaw_phase3.py \
  backend/tests/unit/test_openclaw_phase4.py \
  backend/tests/unit/test_openclaw_admin_api.py -q
```

结果：`20 passed`

其中包含自审补强：

- classify cache 跨实例命中测试

### Python 编译检查

已通过：

```bash
python3 -m py_compile \
  backend/app/services/execution_profile_service.py \
  backend/app/services/execution_service.py \
  backend/app/services/execution_template_service.py \
  backend/app/adapters/openclaw/intent_translator.py
```

### Flutter 静态检查

已通过：

```bash
dart analyze \
  mobile/lib/features/task/presentation/widgets/execution_result_renderer.dart \
  mobile/lib/features/task/presentation/widgets/execution_approval_card.dart \
  mobile/lib/features/report/presentation/screens/learning_report_screen.dart \
  mobile/lib/core/network/api_endpoints.dart
```

结果：无 error，仅剩 info 级 lint。

## 4. 仍未完成的关键范围

- Phase 2
  - 执行中 streaming milestones 回灌聊天流
  - 失败温柔处理文案按 `error_category` 分流
  - 多 Agent 执行链路的 transparency capsule 展示
- Phase 3
  - 周期性委派洞察推送
  - cognitive prism 的完整 execution fragment 建模
- Phase 4
  - 设置页连接管理 UI
  - mDNS / Bonjour 自动发现
  - 配对码 / QR 绑定
  - 远程 relay / NAT 穿透 / 离线队列
  - Sparkle 托管执行服务
- Phase 5
  - 聊天内联结果卡接入富渲染器
  - artifact gallery / 文档前三页预览 / 执行回放 / 结果对比
  - 结果自验证 prompt
  - 分级模型策略与成本透明度
- Phase 5.4 / 6
  - 无障碍语义补齐
  - execution 文案中英文本库
  - 指标落表与 A/B 实验接线
  - 用户旅程自动化验证

## 5. 审查建议

优先审以下 4 组：

1. 结果渲染与审批体验
   - `mobile/lib/features/task/presentation/widgets/execution_result_renderer.dart`
   - `mobile/lib/features/task/presentation/widgets/execution_approval_card.dart`
2. 学习报告中的执行可见性
   - `mobile/lib/features/report/presentation/screens/learning_report_screen.dart`
   - `mobile/lib/core/network/api_endpoints.dart`
3. 执行效率优化
   - `backend/app/services/execution_service.py`
   - `backend/app/services/execution_template_service.py`
   - `backend/app/adapters/openclaw/intent_translator.py`
4. 聚合与统计正确性
   - `backend/app/services/execution_profile_service.py`
   - `backend/tests/unit/test_openclaw_phase3.py`
   - `backend/tests/unit/test_openclaw_phase4.py`

## 6. 结论

当前状态已经从“有执行入口”推进到“有执行体验、有聊天委派、有学习回流、有基础结果富展示、有用户侧执行报告”。

但按你最初定义的商业级目标，这仍然是“Phase 1 完成度高，Phase 2/3/5/6 已有关键可验收增量，Phase 4 和 Phase 5 深水区仍待继续攻坚”，还不能宣称 6 个 Phase 全量收官。
