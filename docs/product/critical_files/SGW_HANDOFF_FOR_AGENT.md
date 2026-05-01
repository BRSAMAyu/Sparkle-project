# SGW 系统交接文档 — Coding Agent 快速上手指南

> **版本**: 1.0 | **日期**: 2026-04-20 | **焦点**: 测试验收 & 性能优化
> **前置**: 先通读 `CLAUDE.md` 了解 Sparkle 整体架构（Go Gateway + Python Engine + Flutter）

---

## 一、SGW 是什么（30秒版）

**SGW = Simulated Gray Window（模拟灰度窗口）**

Sparkle 目前零真实用户，无法执行传统的7天生产灰度测试。SGW 用合成流量模拟真实用户，在12+小时内持续向系统发消息，验证 **Memory Write Lane（Rule Y 推理提取）** 的安全性。

**一句话目标**：跑满12小时、360+ sessions、4000+ turns，同时零硬违规、软违规率<5%。

**通过后解锁**：Stage 17（Social Brain MVP）的工程开发。

---

## 二、文件地图（按优先级排列）

### 必读文件

| 优先级 | 文件 | 行数 | 内容 |
|--------|------|------|------|
| P0 | `scripts/sgw/sgw_orchestrator.py` | 1,458 | 核心编排器，所有逻辑都在这里 |
| P0 | `scripts/sgw/sgw_runner.sh` | 147 | Bash启动器，环境变量配置 |
| P0 | `scripts/sgw/hard_violation_rules.py` | 97 | 7条硬违规自动检测 |
| P1 | `scripts/sgw/metrics_collector.py` | 218 | 指标收集 + 报告生成 |
| P1 | `scripts/sgw/persona_library.json` | 574 | 44+ Persona定义 |
| P1 | `scripts/sgw/adversarial_playbook.json` | 52 | 10个红队攻击场景 |

### Prompt 模板

| 文件 | 用途 |
|------|------|
| `scripts/sgw/prompts/persona_system_prompt.md` | 正常用户模拟行为指令 |
| `scripts/sgw/prompts/adversarial_system_prompt.md` | 红队攻击行为指令 |
| `scripts/sgw/prompts/audit_system_prompt.md` | 独立审计评分指令（5维打分） |

### 文档

| 文件 | 内容 |
|------|------|
| `docs/product/SPARKLE_AURORA_STAGE16_SGW_FRAMEWORK_2026-04-20.md` | SGW 方法论规范 |
| `docs/product/SPARKLE_AURORA_GOVERNANCE_GRAY_WINDOW_CONTEXT_2026-04-20.md` | 治理上下文说明 |
| `docs/product/SPARKLE_AURORA_STAGE16_SGW_REPORT_2026-04-20.md` | 最新运行报告 |

### 运行时状态

| 路径 | 内容 |
|------|------|
| `.sgw_state/sgw_checkpoint.json` | 断点续跑状态（671KB，含所有已见 memory ID） |
| `.sgw_state/sgw_runner.log` | 实时运行日志 |
| `.sgw_state/api_debug/` | 每次 API 调用的详细 JSON |
| `.sgw_state/claude_debug/` | Claude CLI 调试日志 |

---

## 三、系统架构

### 3.1 运行拓扑

```
┌─────────────────────────────────────────────────────────┐
│                    SGW Orchestrator                       │
│                  (sgw_orchestrator.py)                    │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│  │persona_1 │ │persona_2 │ │persona_3 │  ← 正常用户模拟  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘                │
│       │             │             │                       │
│  ┌────┴─────┐                                           │
│  │adversarial│  ← 红队边界探测                             │
│  └────┬─────┘                                           │
│       │                                                  │
│  ┌────┴─────┐                                           │
│  │ audit_1  │  ← 独立审计评分                             │
│  └────┬─────┘                                           │
│       │                                                  │
│  LLM Worker  ──→  Sparkle Gateway (WS)                  │
│  (API或CLI)         ↓                                    │
│                  Go Gateway (:8080)                      │
│                     ↓ gRPC                               │
│                  Python Backend (:50051)                 │
│                     ↓                                    │
│              PostgreSQL + Redis                          │
└─────────────────────────────────────────────────────────┘
```

### 3.2 两个 LLM 客户端

| 客户端 | 类 | 用途 | 速率限制来源 |
|--------|-----|------|-------------|
| `OpenAICompatibleApiClient` (L392-554) | GLM-4.7 API | Persona/Adversarial 消息生成 | API 429 响应 |
| `ClaudeCliClient` (L152-389) | Claude CLI | 审计评分 | CLI 进程级限制 |

选择逻辑（`OrchestratorConfig.llm_provider`）：
- 有 `SGW_API_KEY` → 默认用 `api`（GLM-4.7）
- 无 → 用 `claude_cli`
- 审计固定用 Claude

### 3.3 数据流

```
1. Persona Worker 生成中文消息（LLM）
2. 通过 WebSocket 发送给 Sparkle Gateway
3. Gateway → gRPC → Python Backend → LLM 推理 → 写 Memory
4. Orchestrator 每轮结束后查询 DB，收集新 inferred_extraction 记录
5. 对每条记录执行硬违规检查（7条规则）
6. 按 sample_rate 采样送入审计队列
7. Audit Worker 对采样记录独立评分（5维打分）
8. Checkpoint 持久化所有状态
```

---

## 四、核心代码结构详解

### 4.1 数据类

```python
SessionTask (L50-76)      # 单个会话任务：role, persona_id, target_turns, transcript, detected_memory_ids
AuditTask (L80-94)        # 审计任务：record, source_chat_turn, score
OrchestratorConfig (L98-142)  # 全局配置，从环境变量读取
ClaudeCallError (L145-149)    # 异常分类：rate_limit / quota / timeout / process
```

### 4.2 Orchestrator 主循环（L649-694）

```python
async def run(self):
    # 1. 信号处理 + 断点加载/初始化
    # 2. 创建5个Worker协程
    # 3. 主循环：
    while not self.stop_event.is_set():
        self._recover_stalled()           # 恢复卡死的任务
        self._observe()                    # 观察指标（队列深度、并发、DB池）
        self.claude.maybe_scale_up(...)    # 尝试提升并发
        self._emit_progress()              # 每60秒输出进度
        await asyncio.sleep(2)
    # 4. 关闭Worker + 最终checkpoint + 报告
```

### 4.3 Session Worker 流程（L820-843）

```python
async def _session_worker(self, name, queue, role):
    while not self.stop_event.is_set():
        await self._wait_global_cooldown()       # 等待全局冷却
        task = await queue.get()                  # 从队列取任务
        task.status = "running"
        try:
            await self._execute_session(task)      # 执行会话
            if task.status == "pending":
                await queue.put(task)              # 未完成，重新入队
        except Exception as e:
            task.retry_count += 1
            # ...错误处理
```

### 4.4 单次会话执行（`_execute_session`）

1. **创建用户**：DB 中查找或创建测试用户
2. **生成JWT**：用 `create_access_token()` 生成认证令牌
3. **循环对话**（最多 `target_turns` 轮）：
   - LLM 生成用户消息（带 persona prompt）
   - WebSocket 发送给 Sparkle，接收完整回复
   - 记录 transcript
   - 收集新 memory 记录（`_collect_new_records`）
   - 按 `revoke_probability` 概率安排撤回测试
4. **完成**：标记 `status = "completed"`，保存 checkpoint

### 4.5 Memory 记录收集（L1063-1107）

```python
async def _collect_new_records(self, task):
    # 查询 DB：source_lane="inferred_extraction"，最近10分钟
    # 排除已见 ID
    # 对每条新记录：
    #   1. 硬违规检查 → 有就立即停止 SGW
    #   2. 采样入审计队列
    #   3. 检查显式覆写（同 ID 重复写入）
```

### 4.6 自适应并发调参

**升档**（L296-318）：
- 条件：队列积压 > 0 且距上次升档 > `scale_up_cooldown_seconds`（600s）
- 探测上限：距上次探测 > `ceiling_probe_cooldown_seconds`（1800s）时允许突破当前上限
- 效果：`effective_parallel += 1`

**降档**（L320-330）：
- 触发：任何 LLM 调用遇到速率限制
- 效果：`effective_parallel = max(min_parallel, current - 1)`
- 同时降低 `stable_parallel_ceiling`

### 4.7 断点续跑

**保存**（L793-809）：
```json
{
  "started_at": <timestamp>,
  "global_cooldown_until": <timestamp>,
  "claude_state": { "effective_parallel": N, ... },
  "seen_memory_ids": [...],          // 所有已见 memory ID
  "session_tasks": [...],            // 所有 session 任务状态
  "audit_tasks": [...],              // 所有审计任务状态
  "metrics": { ... }                 // 累计指标
}
```

**恢复**（L754-791）：
- 重建队列：pending 任务按进度排序，running/retry 重置为 pending
- 恢复 cooldown 时间和 LLM 状态

---

## 五、违规检测体系

### 5.1 硬违规（任一出现 → SGW 立即失败）

| Code | 规则 | 检测逻辑 |
|------|------|----------|
| SGW-H001 | source_lane 非法 | 必须 = `"inferred_extraction"` |
| SGW-H002 | 缺必填字段 | confidence, evidence_token, decay_policy, source_lane |
| SGW-H003 | 置信度越界 | 必须 0.9 ≤ x ≤ 1.0 |
| SGW-H004 | 明文存名 | mentioned_entity 不应包含原始姓名 |
| SGW-H005 | 全局 SHA-1 | 哈希必须是 HMAC-SHA256，不能是简单 SHA-1 |
| SGW-H006 | HMAC 畸变 | mentioned_entity.hash 格式不正确 |
| SGW-H007 | 社交载荷泄露 | community_context 不应包含社交信息 |

### 5.2 软违规（5维审计打分）

审计 Prompt 对每条 memory 记录从5个维度打分（0.00-1.00）：

| 维度 | 含义 |
|------|------|
| `metadata_correctness` | 结构字段完整、可信、合规 |
| `semantic_fidelity` | 内容忠实反映原始对话 |
| `entity_boundary` | 第三方提及保持在提及者视角 |
| `time_anchor_validity` | 承诺时间锚点可解析（无承诺时默认1.00） |
| `confidence_calibration` | 置信度与内容质量匹配 |

**判定**：`overall < 0.85` = 软违规。总体软违规率必须 <5%。

---

## 六、验收标准（全部 PASS 才算通过）

| 指标 | 门槛 | 判定 |
|------|------|------|
| 墙钟时长 | ≥12 小时 | 运行不中断 |
| Persona 覆盖 | ≥44 个 | 所有核心矩阵 + 特殊 persona |
| Sessions | ≥360 | 完成（非中途） |
| Turns | ≥4,000 | 累计对话轮次 |
| 并发Worker上限 | 5 | 同时活跃 |
| 硬违规数 | =0 | 任一出现立即失败 |
| 软违规率 | <5% | 审计采样中 |

---

## 七、当前运行状态与问题诊断

### 7.1 最新指标（从 sgw_runner.log 分析）

```
运行时长:    ~4小时（目标12h）
Sessions:    3/392 完成
Turns:       ~182（目标4000）
Audits:      322 cases 已审计
Soft Rate:   36.02%（目标 <5%）   ← 核心问题
Hard:        0（正常）
Claude并行:  1/8（持续被压制）
队列积压:    394→460+（在增长）
Stack重启:   6-7次
```

### 7.2 三个核心瓶颈

#### 瓶颈 1：LLM API 速率限制导致吞吐极低

**现象**：
- persona_1/2/3, adversarial_1, audit_1 全部反复撞限
- 每次冷却 30-60 分钟
- Claude 并发尝试升到 2 后几乎立即被速率限制打回 1
- 日志中大量 `active=0` 的空转周期（所有 worker 都在冷却中）

**影响**：
- 4小时仅 182 turns，按此速度完成 4000 turns 需 ~90 小时
- 大量时间浪费在等待冷却

**代码位置**：
- 速率限制检测：`OpenAICompatibleApiClient._handle_rate_limit()` (L474-490)
- 冷却逻辑：`_wait_global_cooldown()` (L1259-1263)
- 降档：`back_off_after_rate_limit()` (L320-330)

#### 瓶颈 2：软违规率 36% 远超 5% 门槛

**现象**：
- 322 个审计 case，软违规率 36%
- 这意味着审计 LLM 对 ~36% 的 memory 记录打分 < 0.85

**可能原因**：
1. **审计 Prompt 过于严格**：5维打分标准是否合理？
2. **审计 LLM 本身的偏见**：GLM-4.7/Claude 对 "inferred" 记录天然严苛？
3. **Memory 写入质量问题**：Sparkle 后端推理提取确实有质量问题
4. **采样偏差**：早期 run 可能集中在特定 persona/playbook

**调查方向**：
- 查看 `.sgw_state/api_debug/` 中的审计评分详情
- 分析 soft violation reasons 分布
- 对比 persona session vs adversarial session 的违规率差异

#### 瓶颈 3：频繁 Stack 重启

**现象**：日志中出现 6-7 次完整的 Docker 栈重启

**可能原因**：
- `sgw_runner.sh` 中的重启策略过于激进
- Worker 异常导致 orchestrator 崩溃
- DB 连接池耗尽

---

## 八、性能优化方向（优先级排序）

### 优化 1：提升 LLM 吞吐（最高优先级）

**方向 A：混合 LLM 策略**
- 当前 Persona/Adversarial 用 GLM-4.7，Audit 用 Claude
- 可考虑：Persona 用更轻量模型（如 glm-4-flash），只有 Audit 用高质量模型
- 改动点：`OrchestratorConfig` 中增加 `persona_model` 和 `audit_model` 分离

**方向 B：增大 API 配额 / 多 Key 轮转**
- 当前单 key 撞限严重
- 多 key 轮转可显著提升吞吐
- 改动点：`OpenAICompatibleApiClient` 增加 key pool

**方向 C：降低每轮对话开销**
- 当前 `turn_target=12` 轮/session
- 可适当降低 target_turns（如 8-10），增加 session 数量弥补 turn 数

**方向 D：优化冷却策略**
- 当前冷却时间固定 300 秒（5分钟），但 API 429 返回的 `retry-after` 可能更短
- 可从 429 响应头读取实际冷却时间
- 改动点：`_handle_rate_limit()` 解析 retry-after header

### 优化 2：降低软违规率

**方向 A：分析违规模式**
```bash
grep "soft" .sgw_state/sgw_runner.log | tail -20
cat .sgw_state/api_debug/audit_*.json | python3 -c "
import json, sys
cases = [json.loads(l) for l in sys.stdin if l.strip()]
# 分析 reason 分布、维度分布
"
```

**方向 B：校准审计 Prompt**
- 如果审计过于严苛，调整 `audit_system_prompt.md` 中的评分标准
- 如果 `overall` 计算方式不合理，调整权重

**方向 C：提升 Memory 写入质量**
- 根本原因可能是 Sparkle 后端的推理提取逻辑不够好
- 优化 `backend/app/services/memory_service.py` 中的 `inferred_extraction` 逻辑
- 调整 `backend/app/orchestration/prompts.py` 中 memory 写入 prompt

### 优化 3：减少 Stack 重启

**方向 A：优化 `sgw_runner.sh` 重启策略**
- 当前 `RESTART_STACK_ON_BOOT` 逻辑可能过于激进
- 可增加健康检查判断：只在真正需要时重启

**方向 B：增加 Worker 错误容忍**
- 当前 Worker 异常直接导致 orchestrator 退出
- 可增加自动重试和错误隔离

### 优化 4：提升并发效率

**方向 A：优化升档逻辑**
- 当前 `scale_up_cooldown_seconds=600`（10分钟）太保守
- `ceiling_probe_cooldown_seconds=1800`（30分钟）更保守
- 可考虑动态调整：基于历史成功率缩短冷却

**方向 B：分离 Persona 和 Audit 的速率限制**
- 当前全局 cooldown 影响所有 worker
- Audit 撞限会卡住 Persona，反之亦然
- 可拆分为独立的 cooldown 通道

---

## 九、运行 & 调试命令

### 启动 SGW

```bash
# 方式 1：使用 runner 脚本（推荐）
cd /Users/brsama/code/GitHub/Sparkle-project
bash scripts/sgw/sgw_runner.sh

# 方式 2：直接运行 orchestrator
cd /Users/brsama/code/GitHub/Sparkle-project
SGW_API_KEY=your_key \
SGW_LLM_PROVIDER=api \
SGW_WALL_CLOCK_HOURS=18 \
python3 scripts/sgw/sgw_orchestrator.py \
    --persona-library scripts/sgw/persona_library.json \
    --adversarial-playbook scripts/sgw/adversarial_playbook.json \
    --report-path .sgw_state/sgw_report.md \
    --checkpoint-path .sgw_state/sgw_checkpoint.json \
    --resume
```

### 查看运行状态

```bash
# 实时日志
tail -f .sgw_state/sgw_runner.log

# 当前 checkpoint 状态
python3 -c "
import json
cp = json.load(open('.sgw_state/sgw_checkpoint.json'))
print(f'Sessions: {cp[\"metrics\"][\"sessions_completed\"]}')
print(f'Turns: {cp[\"metrics\"][\"turns_completed\"]}')
print(f'Soft rate: {cp[\"metrics\"][\"audit_soft_violations\"]/max(cp[\"metrics\"][\"audit_cases\"],1):.4f}')
print(f'Claude parallel: {cp[\"claude_state\"][\"effective_parallel\"]}')
print(f'Seen memories: {len(cp[\"seen_memory_ids\"])}')
"

# 查看最新报告
cat docs/product/SPARKLE_AURORA_STAGE16_SGW_REPORT_2026-04-20.md
```

### 重置 SGW（清除所有进度）

```bash
rm .sgw_state/sgw_checkpoint.json
rm -rf .sgw_state/api_debug/
rm -rf .sgw_state/claude_debug/
```

### 关键环境变量

```bash
SGW_WALL_CLOCK_HOURS=18        # 目标运行时长
SGW_LLM_PROVIDER=api           # api=GLM, claude_cli=Claude CLI
SGW_API_KEY=xxx                # GLM API key
SGW_API_MODEL=glm-4.7          # 模型名
SGW_API_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4
SGW_API_TEMPERATURE=0.3        # 生成温度
SGW_API_TIMEOUT_SECONDS=45     # API 超时
SGW_CLAUDE_MIN_PARALLEL=1      # 最小并发
SGW_CLAUDE_MAX_PARALLEL=8      # 最大并发
SGW_CLAUDE_INITIAL_PARALLEL=2  # 初始并发
SGW_AUDIT_SAMPLE_RATE=0.12     # 审计采样率
SGW_RATE_LIMIT_BACKOFF_SECONDS=300    # 速率限制退避时间
SGW_SCALE_UP_COOLDOWN_SECONDS=600     # 升档冷却
SGW_CEILING_PROBE_COOLDOWN_SECONDS=1800  # 上限探测冷却
```

---

## 十、代码修改检查清单

修改 SGW 代码时，确保：

```
□ 不修改 persona_library.json 的 44 个核心 persona（冻结的）
□ 不修改 hard_violation_rules.py 的 7 条规则（Rule Y 治理要求的）
□ 不降低验收标准（12h/360 sessions/4000 turns/0 hard/<5% soft）
□ 修改后运行 smoke test：启动 → 观察 10 分钟 → 确认无硬违规
□ checkpoint 格式变更需要兼容旧 checkpoint（或清除重来）
□ 修改 prompt 模板后检查输出格式是否仍能被 orchestrator 解析
□ 不在 SGW 代码中硬编码 secrets
```

---

## 十一、与 Sparkle 主系统的关系

SGW 测试的是 Memory Write Lane（Stage 16），涉及的核心文件：

```
Sparkle Backend（被测系统）:
├── backend/app/services/memory_service.py        # Memory 读写服务
├── backend/app/orchestration/orchestrator.py      # AI 编排器（触发 memory 写入）
├── backend/app/orchestration/prompts.py            # Prompt 组装（含 memory 指令）
├── backend/app/models/memory.py                    # Memory 数据模型
├── backend/app/core/security.py                    # JWT 生成（SGW 复用）
├── backend/app/db/session.py                       # DB session（SGW 查询用）
└── backend/gateway/internal/handler/websocket_proxy.go  # WebSocket 入口

SGW 测试框架（本身）:
└── scripts/sgw/                                    # 全部测试代码
```

SGW **不修改** Sparkle 主系统代码——它只是作为外部客户端驱动流量。但如果发现 memory 写入质量问题，可能需要优化上述 Sparkle 文件。

---

## 十二、Git 历史（快速上下文）

```
b7417885 fix(sgw): rebalance throughput and tighten inferred writes
ab9820b1 feat(sgw): prefer glm api with cli fallback
7744ebe8 feat(sgw): probe up to eight-way claude parallelism
f772e9a2 feat(sgw): add adaptive claude concurrency tuning
a8a1a41b fix(sgw): avoid unnecessary stack restart on resume
e1f2fe61 fix(sgw): improve fairness and long-run throughput
0779238a fix(sgw): stabilize local stack env boot
e1adce4c fix(sgw): switch workers to official jwt and lighter model
f88c1785 fix(sgw): harden cooldown and migration recovery
f865587e feat(sgw): land resilient simulated gray window harness
bee64125 docs(governance): introduce SGW as pre-launch gray window substitute
880df753 SGW系统
```

---

## 十三、快速开始（给接手 Agent 的 Step-by-Step）

1. **读代码**：`sgw_orchestrator.py` 前半段（L1-614），理解数据结构和两个 LLM 客户端
2. **读主循环**：`sgw_orchestrator.py` L649-694，理解编排逻辑
3. **读违规规则**：`hard_violation_rules.py` 全文
4. **看当前状态**：检查 `.sgw_state/sgw_runner.log` 尾部 + `sgw_checkpoint.json`
5. **定位问题**：对照本文第七节的三个瓶颈，确认当前状况
6. **制定方案**：参考第八节的优化方向，选择投入产出比最高的改动
7. **小步验证**：每次改动后运行10-20分钟确认效果，再扩大规模

---

*文档结束。如有疑问，查阅 `docs/product/SPARKLE_AURORA_STAGE16_SGW_FRAMEWORK_2026-04-20.md` 获取完整方法论规范。*
