# Sparkle R7 全面收尾审查报告

**日期**: 2026-04-30  
**分支**: `roadmapv3`  
**HEAD**: `3f876674`  
**审查人**: Codex  
**审查目标**: 在项目接近收尾阶段，对全链路当前真实状态做一次以代码、测试、契约和用户体验为准的复核，不以历史自评或既有结论为准。

---

## 0. 总结结论

当前项目已经不是“功能残缺型半成品”了，很多关键骨架确实已经落地，尤其是：

- Aurora / Spine 主体结构已成型；
- Python 后端抽样回归稳定；
- 治理模块不再是明显死代码；
- 生产部署脚本里已经存在比早期脚本更真实的切流实现。

但它**还不适合被表述为“全链路收尾完成、只剩人工部署”**。这轮复核里仍然发现了几类真实缺口：

1. **Aurora 状态带纠偏链路仍有契约漂移**，尤其是首页状态带的自由纠偏语义没有完整保真；
2. **压测 CI 的 k6 分支仍未真正启动被测服务**，文档里“已入 CI”的结论仍偏乐观；
3. **Aurora 成本治理只接入了预算前置判断，没有接入实际执行记账**；
4. **文档工作流本身仍有漂移**，愿景验收清单的主引用路径与实际文件位置不一致，Tracker 中也仍有过于乐观的完成表述；
5. **Go Gateway 质量门曾在本轮复核中实际报红，但当前工作区已修复并复测通过，尚未与本次审查文档一起形成独立提交。**

结论上，当前更准确的状态应当是：

> **Phase 0-6 大部分功能实现已具备，但 R7“最终收敛 / 最终验收”仍未完成，且至少还有若干 P1 级尾差需要回收。**

---

## 1. 本轮确认无误、可以继续保留的结论

这部分专门写“已经不是问题”的点，避免重复误报。

### 1.1 Aurora / Governance 接线不是死代码

以下模块已经进入生产主链，不应再按“文件存在但未接线”处理：

- `backend/app/signals/fabrication_guard.py`
- `backend/app/signals/safety_degradation.py`
- `backend/app/signals/high_impact_confirmation.py`
- `backend/app/core/research_isolation.py`

证据：`backend/app/signals/spine_orchestrator.py:152-169` 已实例化，且在后续管线分支中被消费。

### 1.2 RAG 与 Aurora 预算“前置检查”已接线

早前“预算守卫完全未接生产”的判断需要修正为：

- `backend/app/orchestration/graph_rag.py:2006` 已调用 `is_rag_within_budget()`
- `backend/app/orchestration/graph_rag.py:2220` 已调用 `record_rag_cost()`
- `backend/app/signals/spine_orchestrator.py:3281` 已调用 `is_aurora_within_budget()`
- `backend/app/aurora/runtime_v1/l4_async.py:174` 已调用 `is_aurora_within_budget()`

因此，**RAG 的预算检查 + 记账**已形成闭环；**Aurora 则只完成了前置检查，没有完成执行后记账**，见下文 P1-04。

### 1.3 早期 `blue_green_switch.sh` 不能再作为唯一生产证据，但也不是唯一部署路径

`scripts/deploy-prod.sh` 已经具备更真实的 Nginx upstream 切流逻辑，`scripts/deploy_k8s.sh` 也具备 K8s Service selector 切流能力。  
因此，早前对 `scripts/blue_green_switch.sh` 的质疑，应该从“生产切流能力不存在”修正为：

> **存在真实部署路径，但旧脚本仍会误导验收口径，不能继续被当作 T7.3.5 的主要证据。**

---

## 2. 关键问题清单（按严重度排序）

## P2-00 网关质量门已在当前工作区恢复，但需要和代码提交保持一致

**影响面**: Go Gateway / CI / 生产质量门  
**严重度**: P1

### 发现

执行：

```bash
cd backend/gateway && go test ./internal/middleware/... ./internal/agent/...
```

在本轮最初复核时，这条测试链路曾直接失败；但用户随后已在当前工作区修复，复测现已通过。

### 证据

1. `backend/gateway/internal/middleware/ws_auth.go:36-37`

```go
log.Printf("[WsAuth] Request to %s from %s, Origin: %s",
    c.Request.URL.Path, c.ClientIP(), c.GetHeader("Origin"), c.GetHeader("Upgrade"))
```

格式串只有 3 个占位符，但传了 4 个参数，`go test` 直接报错。

2. `backend/gateway/internal/agent/client_test.go:77-79`

测试仍断言“无效地址创建 client 必须报错”，但 `NewClient()` 现在已不再使用阻塞式拨号，这个断言和当前实现语义不一致，导致测试假红。

对应实现：`backend/gateway/internal/agent/client.go:64-89`

### 判断

当前判断应更新为：

> **Go Gateway 质量门在当前工作区已恢复为绿，但修复尚未与本次文档提交绑定，因此仍需要在后续代码提交中显式落档。**

---

## P1-01 Aurora 首页状态带的纠偏语义仍未完整保真

**影响面**: Aurora 用户体验 / 纠偏闭环 / 愿景 AUR-043 AUR-044  
**严重度**: P1

### 发现

首页状态带虽然已经补上了 telemetry，但它仍然没有完整保留 Aurora 纠偏协议的关键语义。

### 证据 A: `band_status` 契约漂移

- 前端枚举：`mobile/lib/features/home/presentation/providers/spine_status_band_provider.dart:6-13`
  - `riskFound`
  - `needsConfirm`
  - `calibrationAvailable`
  - `coolingDown`
- 后端协议解析：同文件 `60-67`
  - `risk_found`
  - `needs_confirm`
  - `calibration_available`
  - `cooling_down`

但首页状态带上报 telemetry 时使用的是：

- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart:487`
- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart:499`

```dart
bandStatus: band?.bandStatus.name ?? '',
```

这里会把 Dart enum name 直接上报成 camelCase，而不是后端已经约定好的 snake_case。

### 证据 B: 自由纠偏选项的 `is_freeform` 语义被丢失

后端明确保证每组状态带纠偏里都带一个自由纠偏位：

- `backend/app/signals/spine_orchestrator.py:522-528`

```python
{
    "label": "都不对，我解释一下",
    "semantic_value": "freeform_correction",
    "is_freeform": True,
    "is_disconfirming": True,
}
```

但首页状态带统一走：

- `mobile/lib/features/aurora/data/services/aurora_telemetry_service.dart:45-64`

```dart
'is_freeform': false,
'telemetry_id': '',
'chip_id': 'status_band_correction',
```

这意味着用户点了“都不对，我解释一下”后：

- 前端不会把它当成真正的 freeform correction 上报；
- telemetry 丢失区分度；
- 后端 `CorrectionFeedbackProcessor` 收到的不是完整自由纠偏语义，而是一个被压扁后的状态带点击事件。

### 证据 C: 跳转到聊天仍只传普通文本

- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart:489-503`

当前仍只传：

```dart
{
  'initial_user_message': opt.label,
}
```

这会把结构化纠偏入口退化成普通聊天入口。  
它比“完全没 telemetry”要强，但仍然没有达到“用户关键反馈会以结构化方式改变 Aurora 下一步行动”的愿景标准。

### 判断

这条链路已经不是“完全失效”，但也**还没有达到 Aurora 愿景要求的高保真纠偏闭环**。  
更准确的状态应当是：

> **首页状态带纠偏已接线，但协议保真度不足，尤其是自由纠偏和状态枚举契约仍存在实质性缺口。**

---

## P1-02 k6 压测 CI 分支仍未真正启动被测系统

**影响面**: CI / 性能验收 / T6.1.6 与 OBS-012 完成口径  
**严重度**: P1

### 发现

`load-test.yml` 里的 k6 job 现在仍然没有启动 gateway/backend/app。

### 证据

- `.github/workflows/load-test.yml:98-116`

当前 job 只做了：

1. checkout
2. install k6
3. `k6 run backend/tests/load/k6/scenarios.js`

但没有任何服务启动步骤。

而测试脚本默认目标是：

- `backend/tests/load/k6/scenarios.js:22`

```js
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
```

也就是说，默认会打一个并不存在的本地地址。

### 判断

这说明：

- “负载测试已入 CI”这句话只能算**部分成立**；
- Locust 分支和 benchmark 场景门不能自动替代 k6 job 的真实性；
- Tracker 中把该项标成“已修复/已完成”仍然偏乐观。

---

## P1-03 Aurora 成本治理尚未形成真实记账闭环

**影响面**: Aurora 成本控制 / 生产治理 / Phase 6 完整性  
**严重度**: P1

### 发现

Aurora 的预算前置检查已经接入，但**实际执行后的成本记账没有接入生产调用链**。

### 证据

- 定义：
  - `backend/app/core/cost_controller.py:173-178` `record_aurora_cost()`
- 调用搜索结果：
  - 生产代码中只找到 `is_aurora_within_budget()`
  - 未找到 `record_aurora_cost()` 的生产调用者

本轮搜索结果显示：

- `backend/app/signals/spine_orchestrator.py:3281` 只检查预算
- `backend/app/aurora/runtime_v1/l4_async.py:174` 只检查预算
- 没有对应的执行后 `record_aurora_cost(...)`

### 判断

这意味着当前 Aurora 的成本治理更像：

> **“会在执行前看一眼预算是否超限”**

而不是：

> **“会对实际消耗持续累计、统计并驱动后续预算决策”**

因此，T6.4.2-T6.4.4 更准确的状态应为：

> **预算守卫已部分生产接线，但 Aurora 侧仍未形成完整的生产级记账闭环。**

---

## P2-01 旧蓝绿脚本仍会误导最终验收口径

**影响面**: 运维文档 / 最终验收证据  
**严重度**: P2

### 发现

`scripts/blue_green_switch.sh` 仍然只是本地 slot 文件 + localhost smoke 的简化脚本：

- `scripts/blue_green_switch.sh:69-71`
- `scripts/blue_green_switch.sh:106-107`
- `scripts/blue_green_switch.sh:163-165`

它不会改 Nginx upstream，也不会 patch K8s Service。

### 判断

它现在更适合作为**开发辅助脚本**，而不是 Phase 7 的主要生产切流证据。  
如果继续在文档里把它当主证据，会让“部署自动化已完成”的结论显得比现实更强。

---

## P2-02 文档工作流仍有主引用路径漂移

**影响面**: 验收流程 / 工作流可追溯性  
**严重度**: P2

### 发现

当前不存在顶层文件：

- `docs/product/愿景验收清单`

实际存在的是：

- `docs/product/critical_files/愿景验收清单`

### 判断

这不是代码 bug，但会影响最终收尾阶段的人机协作效率：  
路线图和多份审查文档都以“愿景验收清单”为总标准，但它的主引用路径并不稳定，容易造成不同 agent / 审查轮次引用不同源文件。

---

## P2-03 Tracker 的完成口径仍需再次校准

**影响面**: 路线图治理 / 审查可信度  
**严重度**: P2

### 发现

Tracker 当前仍有几处“结论比代码现实更乐观”的表述，例如：

- `load-test.yml` 已修复为真实 CI；
- Go Gateway / 跨层一致性已收尾；
- 最终生产收尾只剩人工动作。

### 判断

这轮复核后的建议不是“否认大量既有成果”，而是：

> **把那些已经实现的部分保留下来，但把仍未闭环的问题重新打开，避免 Phase 7 在错误的完成状态上收口。**

---

## 3. 愿景维度差距映射

### 3.1 AUR-043 / AUR-044 仍未完全过线

愿景要求：

- 预测/纠偏选项必须保留结构化语义；
- 用户点击后要进入可学习、可回写的链路。

当前首页状态带只达到了“半结构化”：

- 有 telemetry；
- 但状态枚举有契约漂移；
- freeform 语义被压扁；
- 跳转到聊天后退化为普通文本入口。

### 3.2 “用户关键反馈改变下一步行动”还需要更硬的证据

在 Chat 内链路上，这件事已经做得更好了；  
但在首页状态带这一关键 Aurora 显性入口上，还不能非常有把握地说已经完全达标。

### 3.3 “生产就绪”当前更接近“主要功能已齐，质量门还需再收”

尤其是：

- Go 侧质量门不绿；
- k6 CI 真实性不足；
- Aurora 成本治理缺实耗记账；
- 文档完成口径偏乐观。

这几项叠加后，不适合把当前状态定义成“只剩人工部署”。

---

## 4. 本轮实测记录

### 4.1 通过

```bash
cd backend && pytest tests/unit/test_cost_controller.py tests/unit/test_t34_status_band_preferences.py tests/unit/test_spine_orchestrator.py -q
```

结果：`91 passed, 2 warnings`

说明：

- Aurora 状态带与 Spine 的核心抽样回归是稳定的；
- 仍有既有 `AsyncMock` warning，位置在 `backend/app/aurora/runtime_v1/user_preferences.py:92`

### 4.2 未通过

```bash
cd backend/gateway && go test ./internal/middleware/... ./internal/agent/...
```

结果：失败

原因：

本轮最初失败点：

1. `ws_auth.go` 的 `log.Printf` 参数个数错误；
2. `client_test.go` 里的 invalid address 断言和当前 `NewClient()` 语义不一致。

当前工作区复测后，这两点已不再阻塞测试。

### 4.3 Flutter 定向分析

```bash
cd mobile && flutter analyze lib/features/home/presentation/screens/dashboard_screen.dart lib/core/i18n/intent_keywords.dart
```

结果：

- 1 个 warning：`mobile/lib/core/i18n/intent_keywords.dart:1` 未使用 import
- 其余为 info 级样式/规范提示

这说明前端不是“完全失控”，但也还没达到最终收尾阶段那种干净、可信的静态质量信号。

---

## 5. 建议动作排序

### 第一优先级（先修，修完再宣称收尾）

1. 修复首页状态带 telemetry 契约：
   - `band_status` 改回 snake_case；
   - 保留 `is_freeform`；
   - 为状态带纠偏补足可追踪的 `telemetry_id/group_id`；
   - 自由纠偏不要退化成普通文本入口；
2. 给 k6 CI job 补齐服务启动步骤，或把 job 明确降级为脚本存在而非有效 CI；
3. 在 Aurora L3/L4 执行完成处接入 `record_aurora_cost()`。

### 第二优先级（收口可信度）

4. 把当前工作区里已修复的 Gateway 质量门问题随代码正式提交，避免文档与代码快照脱节；
5. 明确 `scripts/deploy-prod.sh` / `scripts/deploy_k8s.sh` 才是生产切流主路径，并降级 `blue_green_switch.sh` 的文档定位；
6. 修正文档主引用路径，统一“愿景验收清单”的 canonical location；
7. 把 Tracker 中与上述问题相关的“已完成”状态改成 reopen / 待复核。

---

## 6. 本轮审查总判断

这次我不认可“Phase 0-6 已全部收敛，只剩人工部署”的口径。  
更客观的说法是：

> **系统的大部分核心能力已经做出来了，Aurora/Spine 的主体也已经成形，但 R7 最终收敛仍然没有完成。**

如果只看功能存在性，项目已经非常靠近终盘；  
如果按你现在要求的标准去看，也就是“真实、可验收、和愿景一致”，那它还需要再清掉一批关键尾差，尤其是 **Aurora 显性纠偏体验、性能 CI 真实性、成本治理闭环** 这三块，以及文档/代码快照的一致性问题。
