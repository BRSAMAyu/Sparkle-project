# E-04 Aurora/Action/Memory 专项模型 Eval 与 Prompt 收敛

> 卡片：`v3/07_tasks/cards/E-04.md` ｜ 规格：`v3/05_metrics_eval/EVAL_PROTOCOL.md`（L2 层）
> 评测对象：三面五 prompt——全部为现役生产 semantic-tier 通道（默认关、代码强制
> closed-set、失败降级规则缺省）。eval 只测「语义选择质量 × 结构化输出稳定性 ×
> 注入抵抗」，规则层正确性归各自单测（X-02/A-02/A-04/M-02）。

| 文件 | 职责 |
| --- | --- |
| `ai_face_schema.py` | 冻结 case JSON schema（`e04-ai-face-eval.v1`）+ 覆盖矩阵机检 + 安全/注入维度硬约束 |
| `cases/*.json` | 5 sub-suite × 36 case（15 key：每面 5），`runtime_expectation` 对生产规则层逐字段冻结（漂移绊线） |
| `faces.py` | 生产连接层：live prompt 常量、规则层调用（feasible/se 缺省）、生产同款 prompt 插值、生产 JSON 解析（`LLMService._parse_json_payload` 直接复用） |
| `grading.py` | 确定性判定（零 LLM judge）：contract → closed_set → semantic → facet 四级 |
| `prompt_registry.py` | prompt 三重门：安全骨架子串（结构面）+ sha 白名单（变更面）+ floors（证据面，安全维度恒 1.0） |
| `gate.py` | 回归门禁：逐 case 不被平均掩盖 + 预算纪律 + 密钥扫描 + 四类变异自证 |
| `real_model.py` | 真模型探针（每面 ≤20、合计 ≤60 硬限；key 仅运行时读取，永不入产物） |
| `runner.py` | CLI（静态门禁 / `--probe` / `--gate`，stdout=机读 JSON） |
| `test_ai_face_eval_gate.py` | pytest 门禁断言（24 用例：schema 冻结/漂移/骨架/登记/grader/预算/变异必红） |
| `real_model_baseline.json` | 基线探针产物（30 次；7/15 key 通过） |
| `real_model_converged.json` | 收敛探针产物（30 次；15/15 key 通过） |

## 复现命令（backend/ 下）

```bash
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.ai_face_eval.runner            # 静态门禁（机读 JSON）
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest tests/ai_face_eval -q         # 24 断言（含变异必红）
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.ai_face_eval.runner --gate     # 全量门禁（静态+run+floors+收敛）
# 真模型探针（需 key；预算硬限：每面 20 / 合计 60）
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.ai_face_eval.runner --probe baseline
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.ai_face_eval.runner --probe converged
```

## 修改生产 prompt 的唯一合法路径

1. 改 `backend/app/...` 的 prompt 常量/文件；
2. `--probe <round>` 跑真模型（预算内），产物落 `real_model_<round>.json`；
3. 分数达旧 floors（安全维度恒 1.0，不可放松）；
4. 新 sha + floors 登记 `prompt_registry.APPROVED_PROMPTS`（随 patch 评审）。

跳过任何一步：`pytest tests/ai_face_eval` 红（未登记 sha / 骨架缺失 / floors 未满足）。

## 门禁状态（HEAD 5abd1c4b + E-04 patch）

**GREEN**——15/15 key case 全绿（含 6 个安全/注入关键样本）；预算 60/60 用满
（30 基线 + 30 收敛）；无登记逃逸（`REGISTERED_LIMITATION_CASE_IDS` 为空）。

## 设计红线遵守

- 未改任何 closed-set 代码强制边界（S2 越界拒收路径原样）；prompt 修订只增
  不删：安全骨架子串（学习守卫/风险守卫/敏感定义/情绪禁令）全部保留并被
  `INVARIANTS` 机检冻结。
- 词表 39（D-01）未动；未改模型路由架构（E-02 域）；未动 execution 恢复/
  context_pack/渲染（X-09/FIX-35/36 域）；`decide_joint_two_step` 改动为
  纯附加（annotations.scenario_summary 随行），A-04 全套单测 207 绿。
- 真模型 key 只从 env / 主仓 `backend/.env` 运行时读取（主仓只读）；两份
  探针产物均含密钥扫描通过证明。
