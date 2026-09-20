# M-09 Memory Longitudinal / Adversarial 评测套件

> 卡片：`v3/07_tasks/cards/M-09.md` ｜ 规格：`v3/05_metrics_eval/PERSONALIZATION_EVAL.md`
> 评测对象：**已合入的记忆系统真链路**（M-02 存储门 / M-03 检索预筛 / M-04 冲突仲裁 /
> M-05 使用自检 / M-06 投影边界 / M-07 纠正删除失效），sqlite 隔离环境跑真实服务。
> 唯一模拟层 = LLM 抽取决策（case JSON 编码）＋ 25 次预算内真模型答案探针。

## 目录

| 文件 | 职责 |
| --- | --- |
| `memory_eval_schema.py` | 冻结的 case JSON schema（`m09-memory-eval.v1`）+ 装载校验 + 覆盖矩阵机检 |
| `cases/p01..p10*.json` | 10 persona × 82 case（5 维度 × 每 persona 全覆盖，全部多 session） |
| `harness.py` | 真链路时间线执行器（生产写/纠错/删除入口）+ 读链探针（pack.build + 真实渲染）+ paired no-history 臂 |
| `grading.py` | 三指标：invalid use / overpersonalization / valid-use precision（+ uplift、per-case 判定） |
| `gate.py` | 回归门禁：per-case 判定不被平均掩盖 + 阈值 + 变异自证 |
| `real_model.py` | 5 关键 case × 5 真模型重复（硬上限 25 次；key 仅运行时读取，永不入产物） |
| `runner.py` | CLI（确定性，可重复） |
| `test_memory_eval_gate.py` | pytest 门禁断言（覆盖矩阵 / 门禁签名 / 变异必红 / 真模型产物完整性） |
| `real_model_stability_report.json` | 5×5 真模型稳定性报告（已脱敏：无 key、无环境转储） |

## 复现命令（backend/ 下）

```bash
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.memory_eval.runner            # 全量 82 case + 门禁（stdout=机读 JSON）
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest tests/memory_eval -q         # 门禁断言
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.memory_eval.runner --real-model   # 真模型 25 次（需 key）
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.memory_eval.runner --persona P03   # 单 persona
```

确定性：case 用户身份 = uuid5(固定命名空间, case_id)；时间线为相对锚点的偏移；重复运行判定/指标不变。

## 门禁状态（HEAD e56be400）

**RED**——82 case 中 20 个失败，全部为**已登记产品 bug** 的签名（详见
`v3-output/M-09/REPORT.md` §产品 bug 登记：`ContextPackBuilder` 偏好冲突消解分支忽略
M-01/M-07 supersede 链，被取代的旧偏好值在 `pack.preferences` 复活）。其余 62 case 全绿。
产品 bug 修复后，清空 `test_memory_eval_gate.py::REGISTERED_BUG_CASE_IDS` 即转为绿灯门禁。

## 设计红线遵守

- 不 mock 记忆行为本身；`time_advance` 仅做墙钟模拟（对已写入行平移时间戳），不改任何记忆决策。
- 词表 39（D-01 事件词表冻结 sha）未动；未改任何产品代码。
- 真模型调用严格 25 次（`_CallBudget` 硬限）；key 从 env 或主仓 backend/.env 运行时读取（主仓只读）。
