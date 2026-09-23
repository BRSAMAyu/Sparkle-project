# PROD-FIX-4 收工报告 — 二轮巡检四小件（i18n 假 key / checkpoint 尾巴 / 冷却旁路 / 小米死车道）

- 卡号：PROD-FIX-4（北极星全旅程战役 · C 纵队生产级线）
- worktree：wt210，基线 `4061644e`（PROD-LOG2 报告所在基线，零漂移）
- 缺陷依据：`v3-output/PROD-LOG2/REPORT.md` 新问题 ②-1 / ②-3 / ②-4 / ②-5
- 交付物：本报告 + `changes.patch`（4 个 app 文件 + 6 个测试文件，含 2 个新测试文件；零凭据、零 commit）
- 测试方法：红证先行（4 项修复全部先写测试、在基线逐项验证 RED，修复后全绿）；回归对比法（基线与修复后各跑同一测试面，零新增失败）；pytest 全程 `--timeout` + sqlite in-memory env；定向不宽扫

---

## ① 四件修法

### 1. i18n 假 key 刷屏（PROD-LOG2 ②-1，5739 条/88min = 引擎 WARNING 93%）

根因不是 `:290` 一条，而是 `metacognition_registry.py` 里存在**两个同名的 `DASHBOARD_LANGUAGE_TEMPLATES` 定义**：第一个（key 版，10 条模板指向 `metacognition.dashboard_*` 合法 key）被第二个（字面中文句子版）**整体遮蔽**——第二个才是活代码，10 条全部把句子当 key 塞给 `I18n.t`（`:290` 的「样本不足，继续观察中。」只是其中之一），每次未命中打 WARNING 且兜底返回 key 本身（输出碰巧正确，掩盖配置错误）。修法：**删除第二个遮蔽定义**（-72 行），key 版定义复活。核实 `app/data/i18n/zh.json` 与 `en.json` **全部 18 个 `metacognition.*` key 两个 locale 齐备**，且 zh 文案与被删句子逐字一致（`dashboard_insufficient` = 「样本不足，继续观察中。」）——**用户可见输出零变化**，同时意外恢复英文支持（此前字面句永远输出中文）。顺带消掉 `render_guard_samples` 同型未命中。

### 2. checkpoint 尾巴 4 键（PROD-LOG2 ②-5，31 条/88min）

按 wt182 先例逐键核实写入点后登记进 `KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS`（已知→DEBUG）：
- `snapshot` — `execution_engine.py:2598`，`StateSnapshotManager.create_snapshot` 产出的 `StateSnapshot` pydantic 对象（`orchestration/schemas`）
- `executable_plan` — `execution_engine.py:2597` / `standard_workflow.py:2348/2361/2532`，LangGraph 计划对象（清理位写 None 可序列化，故仅计划存活期告警）
- `user_context` / `focused_memory` — `session_state_mixin.py:760/762`，合并上下文 dict 内嵌运行期对象（episodic memories / context_pack 等）
恢复面安全核实：全部消费点走 `.get(...) or 默认值` / 真值判断（`standard_workflow.generation_node` 按需重建计划；`context_builder_node` 无 user_context 时重建默认），checkpoint 缺 key 不破坏恢复。清单注释同步补齐四个键的写入点与安全依据。

### 3. SecurityMonitor 冷却旁路（PROD-LOG2 ②-4，90+90 条/88min）

新增 `_send_alert_with_cooldown` 帮助方法：经 `trigger_security_alert` 现成的 300s 冷却通道（`security:alert_cooldown:{type}` setex）发告警；redis 为 None 时退回直发（无冷却通道可吃，保持基线可观测、不因 AttributeError 抛错）。三处直调 `_send_alert_notification` 的旁路点全部接回（`:672` system_security_issue + 同型扫描补钉的 `:631` brute_force_attempt、`:645` unusual_admin_activity）。另把 `_check_system_security` 里「DEBUG mode is ON」的常态说明从 WARNING 降 DEBUG——它是「每分钟一对」的另一半（状态已由冷却后的告警承载，开发环境 1440→0 条/天 WARNING）。修复后频次：告警对从 1 次/分钟 → 1 次/300s。

### 4. 小米死车道（PROD-LOG2 ②-3，404 Unsupported model ×3 站）

**裁决：两层叠加（卡面两个选项都用，各治半个环境），B-MODEL-SWITCH 开关注册先例**：
1. **key-gate 注册**：`XIAOMI_MIMO_API_KEY` 非空才注册 `xiaomi_chat`/`xiaomi_standard_thinking`，无 key 环境 info 日志说明、显式选择经 `select_specific_model` 既有「未注册回退 default」路径干净落地（带原因标注，不误标不炸）。治「无 key 环境（测试/CI/未配置部署）空 key 也注册」的必炸 hop。
2. **死模型名摘出默认降级链**：`fast_models` 去掉 `xiaomi_chat`（第 3 位）、`standard_models` 去掉 `xiaomi_standard_thinking`（第 3 位）。理由：404 是**模型名被小米端点本身拒绝**，与 key 是否有效无关——经 count-only 核实活栈 `.env` `XIAOMI_MIMO_API_KEY` **已配置**（生产 404 而非 401 自证），单靠 key-gate 治不了活栈；自动降级链不得包含确定性失败的 hop。小米官方更正模型名（改 `XIAOMI_CHAT_MODEL`/`XIAOMI_STANDARD_MODEL`）后把两个 key 加回两链即恢复（一行，代码注释已写明操作位）。`.env` 不在改动面（卡面指定），代码侧门控已把死车道对自动流量完全断开。
不动项：`mimo_pro` 走独立 token-plan key/端点，无故障证据且不在任何自动链上，不纳门控面。

## ② 同型扫描结果（#1）

- **`I18n.t` 直调面**（全 app 61 处）：字面实参全部是合法 dotted key，零「句子当 key」。
- **`metacognition_registry.py` 本体**：同型 = 第二个 `DASHBOARD_LANGUAGE_TEMPLATES` 的**全部 10 条**（非仅 `:290`），随遮蔽定义一并删除后，两个注册表 18 条模板全为 dotted key（新增契约测试钉死：key 形状 + zh/en 双 locale 必命中 + 全量渲染零 "Translation key not found" WARNING）。
- **`.template` 变量经 `I18n.t` 的调用点**：全 app 仅 `metacognition_registry.py` 3 处（`render_template`/`render_guard_samples`），无第二家族。
- **形似实不同**（排除项）：`agent_profiles.system_prompt_template`、aurora `wake_reason_template`/`friction_diagnosis.text_template` 均为**直出文案字段**（不经 `I18n.t` 查表），非同型，不动。
- **#3 的同型扫描**：`_send_alert_notification` 全部直调点 = 3 处（system_security / brute_force / admin），已全部接回冷却通道；`trigger_security_alert` 既有调用（failed_login_threshold `:563`）本就走冷却，不动。

## ③ 实现清单

| # | 文件 | 改动 |
|---|---|---|
| 1 | `backend/app/services/metacognition_registry.py` | 删第二个遮蔽 `DASHBOARD_LANGUAGE_TEMPLATES`（-72 行），key 版复活 |
| 2 | `backend/app/checkpoint/redis_checkpointer.py` | KNOWN frozenset +4 键（snapshot/user_context/focused_memory/executable_plan），注释补写入点与恢复面安全依据 |
| 3 | `backend/app/core/security_monitor.py` | 新增 `_send_alert_with_cooldown`；3 处直调改走冷却通道；DEBUG 常态说明 WARNING→DEBUG |
| 4 | `backend/app/core/llm_router.py` | xiaomi 两条目移出静态 dict、改 key-gate 条件注册（无 key info 日志）；`fast_models`/`standard_models` 摘除 xiaomi hop；恢复路径注释 |
| 测试 | `backend/tests/unit/test_redis_checkpointer_allowlist.py` | +2 测试：4 键登记契约、4 键静默跳过（复用既有 sink 夹具） |
| 测试 | `backend/tests/unit/test_confidence_proxy_registry.py` | +3 测试：key 形状契约、zh/en 全量命中、全量渲染零 i18n WARNING |
| 测试 | `backend/tests/unit/test_prodfix4_security_alert_cooldown.py`（新） | 4 测试：冷却通道路由+300s 内不重发、brute/admin 同规、无 redis 退直发、DEBUG 说明不刷 WARNING |
| 测试 | `backend/tests/core/test_llm_router_xiaomi_lane_gate.py`（新） | 5 测试：无 key 不注册、有 key 注册、FAST/STANDARD 链无 xiaomi hop、显式选择干净回退、其余链位次零变化（复用 `_rebuild_router`/环境无关化夹具先例） |
| 测试 | `backend/tests/unit/test_llm_router_health_tracking.py` | 4 用例的健康追踪键 `xiaomi_chat`→`dashscope_fast`（注册面变化使未注册键健康上报被既有 guard 忽略；用例钉的是追踪机制本身，键选择本就任意，注释已说明） |
| 测试 | `backend/tests/unit/test_e07_adaptive_routing.py` | 1 用例第三候选 `xiaomi_chat`→`glm_4_7_flash_no_thinking`（用例钉「不引入/不跨层」，需仍在 FAST 链上的键） |

## ④ 冲突面声明

| 并行卡 | 其改动面 | 本卡触碰 | 判定 |
|---|---|---|---|
| wt206 | chat session | `metacognition_registry.py`（仪表盘语言）/`redis_checkpointer.py`/`security_monitor.py`/`llm_router.py`+注册链 | **零重叠**：session 面文件本卡未动；checkpoint 只加允许清单常量、不改 save/load 逻辑 |
| wt207 | onboarding / 趋势 / 光子 | 同上四文件 | **零重叠**：`render_template` 的 trend 模板 id 在保留定义中原样存在（`mc_dashboard_trend_*` 三键 zh/en 齐备），趋势输出文案零变化；光子路径无 LLM 路由注册面接触 |
| wt209 | goal 回填裁决 | 同上四文件 | **零重叠**：goal 回填不 import 本卡四文件任何一个的改动符号（`KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS` 只增不减、`DASHBOARD_LANGUAGE_TEMPLATES` 键集与 id 集不变、SecurityMonitor/LLMRouter 与 goal 无交集） |

本卡测试改动面（3 个既有测试文件 + 2 新文件）与上述三卡的测试面亦无重叠。

## ⑤ 收工核查

**红绿证据**（先红后绿，全部实测）：
- #1 `test_confidence_proxy_registry.py`：基线 4 failed（key 形状×1、zh/en 命中×2、零 WARNING×1）→ 修复后 8 passed
- #2 `test_redis_checkpointer_allowlist.py`：基线 2 failed → 修复后 5 passed
- #3 `test_prodfix4_security_alert_cooldown.py`：基线 3 failed（直调不查冷却键、冷却期重发、WARNING 刷屏）→ 修复后 4 passed
- #4 `test_llm_router_xiaomi_lane_gate.py`：基线 3 failed（空 key 仍注册、链含死 hop、显式选择误返）→ 修复后 5 passed

**回归对比法**（基线 vs 修复后，同面同序）：
- 17 个测试文件终局合并跑：**217 passed, 0 failed**（含 B-MODEL-SWITCH 守卫面 `test_batch_llm_provider_switch.py` 24/24 绿——本卡动了 `llm_router` 注册逻辑，按卡面要求跑齐；Qwen 路由契约 25/25、credential routing 10/10、LLM policy 7/7、PROD-FIX-1 安全监控 8/8、orchestrator state transitions 26/26）
- **既有测试语义修正申报（非修绿）**：`test_llm_router_health_tracking.py` 4 用例与 `test_e07_adaptive_routing.py` 1 用例原以 `xiaomi_chat` 作样本键，注册面变化后未注册键不再可追踪/不在链上——断言体意图不变，仅换恒注册键，理由入注释
- **基线既有红（非本卡）**：`tests/unit/test_metacognition_kill_switch.py::test_language_contract_hit_disables_runtime_modes` 在基线克隆（`git clone` 到 /tmp，禁 stash 合规）同样 failed——kill_switch 无 redis 时 write 被忽略所致，与本卡四文件无因果，登记不修
- #4 遗留声明：`agent_profiles.py:243/521/612` policy preferred_models 与 `predictive_service:1504`/`multi_intent_service:382` preferred_order 仍列 `xiaomi_chat`——活栈（key 已配）下 policy 命中仍会试 mimo；有 E-07 熔断兜底，且修上游模型名（主会话/.env 持有者）即可全链复活，本卡不扩面
- 注册数自证：修复后无 key 环境注册模型 29→27（恰减 xiaomi 两键），有 key 环境 29 不变

**纪律核查**：
- 零 commit / 零 push（`git status` 仅工作区改动 + 2 个 untracked 新测试文件，全量进 changes.patch）
- 主仓只读（唯一写接触：以只读方式借用主仓 `.venv` 解释器跑 pytest，`PYTHONPATH` 钉死本 worktree，`import app.__file__` 实证解析到 wt210）
- 无 .env 读写（活栈 key 判定用 PROD-LOG2 同款 count-only grep）
- /tmp 清理：基线克隆 `/tmp/wt210-baseline-prodfix4` 与中转 patch 已删（见下）；worktree 内 `backend/app/gen/`（.gitignore 产物，跑通 prodfix1 所需）按 gitignore 约定不进 patch、留待合入环境自生成
- pytest-tmp/`.pytest_cache`/`__pycache__` 收工清除；磁盘 `df` 充裕（14Gi 可用），无 HEAVY 任务、无模拟器、无长驻进程
