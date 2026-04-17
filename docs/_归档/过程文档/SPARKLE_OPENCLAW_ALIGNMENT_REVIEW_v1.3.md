# Sparkle × OpenClaw 对齐审查文档 v1.3

> 日期：2026-03-28
> 状态：继续深耕；Phase 4 连接管理本地闭环与 Phase 5 富结果主链路已形成可验收增量，远程连接与高级展示仍未全量完成

## 1. 本轮深耕新增范围

### Phase 4 连接架构深水区

- `mobile/lib/core/services/openclaw_connection_service.dart`
  - 新增 `OpenClawConnectionService`
  - 支持连接配置持久化、`/health` 探活、延迟/节点数/能力矩阵解析
  - 支持 30 秒周期健康检查、掉线状态回写、手动断开
  - 支持 `authToken` 与 `deviceToken` 两种鉴权头透传
- `mobile/lib/features/settings/presentation/screens/openclaw_settings_screen.dart`
  - 新增“AI执行引擎”设置页
  - 支持地址输入、HTTP/WebSocket 模式切换、测试连接、保存连接、断开连接
  - 显示当前连接状态、最近检查时间、延迟、节点数、能力矩阵
- `mobile/lib/features/user/user_routes.dart`
  - 新增 `UserRoutes.openClawSettings`
- `mobile/lib/features/user/presentation/screens/unified_settings_screen.dart`
  - 在统一设置页接入“AI执行引擎”入口

### Phase 5 聊天内联富结果、执行回放、结果对比、结果自验证

- `backend/app/services/execution_result_validator.py`
  - 新增结果验证聚合器
  - 生成 `quality_warnings / replay_steps / result_preview / comparison_summary`
  - 提供原始执行响应与 plan validation 双路径的结构化摘要能力
- `backend/app/orchestration/validation_engine.py`
  - 将结果预览、执行回放、质量警告、验证问题、结果对比摘要注入 `execution_validation`
- `backend/app/services/execution_service.py`
  - 执行落库前把 `_sparkle_quality_warnings` 写入原始响应，避免前端只能看到单次运行态
- `backend/app/services/execution_ingestor.py`
  - ingest 侧同步补齐质量警告写入
- `backend/app/api/v1/executions.py`
  - `ExecutionRecordResponse` 新增：
    - `result_preview`
    - `quality_warnings`
    - `replay_steps`
    - `comparison_summary`
  - 查询单条执行记录时会回看同任务上次结果并生成对比摘要
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart`
  - 聊天侧 `execution_summary` widget payload 扩展：
    - `result_preview`
    - `replay_steps`
    - `quality_warnings`
    - `validation_issues`
    - `comparison_summary`
    - `quality_score`
    - `validation_passed`
    - `validation_total`
- `mobile/lib/features/chat/presentation/widgets/action_card.dart`
  - 聊天内联执行摘要卡接入 `ExecutionResultRenderer`
  - 新增结果预览区、结果对比区、执行回放时间线、自验证质量区
- `mobile/lib/features/task/data/models/execution_record_model.dart`
  - 执行记录模型补齐对应字段解析
- `mobile/lib/features/task/presentation/widgets/execution_approval_card.dart`
  - 审批卡支持结构化预览、对比摘要、质量警告、执行回放

### 本轮顺手修复

- `mobile/lib/core/services/openclaw_connection_service.dart`
  - 清理新增文件中的冗余参数与括号 lint
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart`
  - `validation_issues` 判空逻辑改为更稳健的 `?? false`
- `mobile/lib/features/chat/presentation/widgets/action_card.dart`
  - 去除冗余的 `expanded: false`
- `mobile/lib/features/task/presentation/widgets/execution_approval_card.dart`
  - 清理新增 widget 的 expression-body lint

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
  - 本地连接设置页、连接测试、健康监控、状态持久化
  - 执行画像 / 管理端 dashboard API 骨架
- Phase 5
  - 结果内容渲染器
  - 聊天内联富结果
  - 执行回放摘要
  - 同任务结果对比摘要
  - 结果质量警告与自验证展示
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
  backend/tests/unit/test_openclaw_phase1.py \
  backend/tests/unit/test_openclaw_phase2.py \
  backend/tests/unit/test_openclaw_phase3.py \
  backend/tests/unit/test_openclaw_phase4.py \
  backend/tests/unit/test_openclaw_admin_api.py -q
```

结果：`34 passed`

补充覆盖：

- 结果验证器生成 `quality_warnings / replay_steps`
- 结果对比摘要生成
- classify cache 跨实例命中

### Python 编译检查

已通过：

```bash
python3 -m py_compile \
  backend/app/services/execution_result_validator.py \
  backend/app/services/execution_service.py \
  backend/app/services/execution_ingestor.py \
  backend/app/orchestration/validation_engine.py \
  backend/app/api/v1/executions.py
```

### Flutter 静态检查

已通过：

```bash
dart analyze \
  mobile/lib/core/services/openclaw_connection_service.dart \
  mobile/lib/features/chat/presentation/providers/chat_provider.dart \
  mobile/lib/features/chat/presentation/widgets/action_card.dart \
  mobile/lib/features/task/presentation/widgets/execution_approval_card.dart
```

结果：`No issues found!`

另一次更大范围的 analyze 也已通过，无 error，仅保留 `unified_settings_screen.dart` 的历史 info 级 lint。

## 4. 仍未完成的关键范围

- Phase 2
  - 执行中 streaming milestones 回灌聊天流
  - 失败温柔处理文案按 `error_category` 分流
  - 多 Agent 执行链路的 transparency capsule 展示
- Phase 3
  - 周期性委派洞察推送
  - cognitive prism 的完整 execution fragment 建模
- Phase 4
  - mDNS / Bonjour 自动发现
  - 配对码 / QR 绑定
  - 远程 relay / NAT 穿透 / 离线队列
  - WebSocket 持久通道与断网恢复
  - Sparkle 托管执行服务
- Phase 5
  - artifact gallery 全屏预览 / 文档前三页预览
  - 真正的 step log 级执行回放，不只是摘要时间线
  - 同任务多次执行的并排差异高亮视图
  - 专用结果自验证 prompt 与返工策略
  - 分级模型策略与成本透明度
- Phase 5.4 / 6
  - 无障碍语义补齐
  - execution 文案中英文本库
  - 指标落表与 A/B 实验接线
  - 用户旅程自动化验证

## 5. 审查重点

优先审以下 5 组：

1. 连接设置与本地健康监控
   - `mobile/lib/core/services/openclaw_connection_service.dart`
   - `mobile/lib/features/settings/presentation/screens/openclaw_settings_screen.dart`
   - `mobile/lib/features/user/user_routes.dart`
   - `mobile/lib/features/user/presentation/screens/unified_settings_screen.dart`
2. 结果验证与执行记录 API
   - `backend/app/services/execution_result_validator.py`
   - `backend/app/orchestration/validation_engine.py`
   - `backend/app/api/v1/executions.py`
3. 聊天内联富结果
   - `mobile/lib/features/chat/presentation/providers/chat_provider.dart`
   - `mobile/lib/features/chat/presentation/widgets/action_card.dart`
4. 审批卡深水区展示
   - `mobile/lib/features/task/data/models/execution_record_model.dart`
   - `mobile/lib/features/task/presentation/widgets/execution_approval_card.dart`
5. 回归测试
   - `backend/tests/unit/test_openclaw_phase1.py`
   - `backend/tests/unit/test_openclaw_phase4.py`
   - `backend/tests/unit/test_openclaw_admin_api.py`

## 6. 风险与判断

- 本轮 Phase 4 的“深水区”主要完成了本地连接管理闭环，还没有进入真正的远程桥接层。
- 本轮 Phase 5 已经把“摘要卡”推进到“可审阅结果卡”，但距离完整 artifact 工作台还有明显差距。
- 结果自验证目前是规则化聚合与摘要生成，不是独立 LLM validator prompt，因此能增强可见性，但还不足以单独抬升质量基线。

## 7. 结论

当前状态已经从“执行结果只能在详情页粗看”推进到“聊天中可直接看结果、看回放、看警告、看对比；设置里可直接管理执行引擎连接”。

但按你最初定义的商业级目标，这仍然是“Phase 4 本地连接闭环已成形，Phase 5 富结果主链路已成形，远程连接层和高级结果工作台仍待继续攻坚”，还不能宣称深水区已经全部收官。
