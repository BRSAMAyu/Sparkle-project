# SAFETY-FP · LLM 输出安全过滤器离散数学误报（色情误判）修复 — 收工报告

- Worker：V3 舰队 Worker（SAFETY-FP 卡，主会话活栈实证派生）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt142`（基线 d0ddca66）
- 日期：2026-09-22
- 交付物：`backend/app/core/llm_output_validator.py`（1 文件修改）+ `backend/tests/unit/test_llm_output_validator_math_fp.py`（新增，38 测试）+ 本报告 + `changes.patch`
- 未 commit / 未 push（纪律遵守）；主仓只读（仅拷贝 gitignored 的 `app/gen/` 生成产物供 import）；未动活栈

---

## 0. 病灶机制一句话

`LLMOutputValidator` 的合规词库把**单字「性」「裸」**当色情信号：`COMPLIANCE_PATTERNS` 中 `(r"色情|性|裸", "色情内容")` —— 而离散数学的日常词汇（性质/连通性/对称性/必要性/充分性/奇偶性/完备性…）几乎每句都含「性」，于是每条数学辅导回答都命中「潜在违规: 色情内容」→ `action="sanitize"` + `is_valid=False`，正是主会话在 `/tmp/sparkle_grpc.log` 看到的那条事件（Context `{'user_id': None, 'type': 'chat'}` 精确对应 `app/services/llm_service.py:749` 的调用点）。

## ① 误报根因 + 红证

### 根因（行号）

`backend/app/core/llm_output_validator.py:102`（基线 d0ddca66）：

```python
COMPLIANCE_PATTERNS = [
    (r"暴力|杀|死|伤害", "暴力内容"),
    (r"色情|性|裸", "色情内容"),        # ← 病灶：单字「性」「裸」零精度
    (r"歧视|仇恨|种族", "歧视内容"),
    (r"炸弹|恐怖|袭击", "恐怖内容"),
]
```

- 单字「性」命中一切学术抽象名词后缀：性质、连通性、对称性、传递性、奇偶性、存在性、必要性、充分性、单调性、有界性、收敛性、完备性、可靠性、正确性……北极星 LOOP4 的欧拉回路证明（「存在性…必要性…充分性」）必然命中。
- 单字「裸」还会命中学生口语「裸考」（本产品高频词），本次未实测复现但同根同源，一并修掉。
- 全库唯一性已核查：`色情` 关键词在 `app/` + `tests/` 仅此一处（输入侧 `llm_safety.py` 无色情词库），无第二误报源。

### 红证（修前单测，`tests/unit/test_llm_output_validator_math_fp.py`）

修前运行：**11 failed / 27 passed**。失败项：

- `TestMathFalsePositiveFixed::test_math_sentence_no_porn_violation` ×9 —— 连通性/对称性传递性/奇偶性/树性质/归纳法性质/欧拉回路存在性·必要性·充分性/单调性收敛性/完备性可靠性/正确性等数学句全部被判「色情内容」；
- `TestProtectionSurfaceIntact` ×2 —— **意外发现旧词库双向破损**：「两人做爱的细节描写」「包含强奸情节的小说片段」两条真色情样例在旧词库下**漏放**（不含「性/裸/色情」单字即绕过）。

即旧模式对数学答案是高误报、对真色情反而有漏洞——不是防护面「太严」，是**选词错误**。

## ② 修法 + 防漏放论证

### 修法（最小侵入：只改 1 个正则元组，其余 3 条合规词与其他 5 层防护零改动）

```python
# SAFETY-FP (2026-09-22): 原模式 r"色情|性|裸" 中的单字「性」「裸」命中
# 一切学术/学生词汇 (性质/连通性/对称性/必要性/充分性/奇偶性…、裸考)…
(
    r"色情|裸体|裸照|裸露|全裸|裸聊|艳照|"
    r"性行为|性爱|性交|性器官|性高潮|性交易|性骚扰|性侵犯|性虐待|性奴|"
    r"援交|卖淫|嫖娼|做爱|一夜情|群交|乱伦|强奸|轮奸|奸污|猥亵|淫秽|淫荡",
    "色情内容",
),
```

### 方案选择说明（为何不用数学域白名单）

任务卡给了两个方向，选了「误报词上下文收紧」而非「数学域白名单/LaTeX 密度降权」：

1. 病灶词本身根本不是色情信号（单字「性」对数学文本命中率 ~100%、对真色情反而漏），白名单是在给一个错误信号打补丁；
2. 白名单/降权天然引入「豁免通道」风险（攻击者往数学文本里夹私货即可借数学语境降权）——显式词方案下，任何语境（含数学语境）命中显式色情词**必拦**，无豁免通道，边界测试直接锁死这一点。

### 防漏放论证（修前后对比，同批文本实测）

**数学句（应全过）：误报 8/10 → 0/10**

| 数学句（截取） | 修前 | 修后 |
|---|---|---|
| 欧拉回路当且仅当 G 连通且所有顶点的度数均为偶数 | - | - |
| 证明连通性：对任意顶点 u, v ∈ V 存在路径相连 | 色情内容 | - |
| 等价关系需同时满足自反性、对称性与传递性 | 色情内容 | - |
| 由奇偶性分析，握手定理保证奇度数顶点个数为偶数 | 色情内容 | - |
| 树的基本性质：n 个结点恰有 n−1 条边且无回路 | 色情内容 | - |
| 欧拉回路存在性定理…分别证明必要性…充分性 | 色情内容 | - |
| 数列的单调性与有界性保证收敛性；周期函数的性质 | 色情内容 | - |
| 命题逻辑的完备性与可靠性：Γ ⊨ φ ⟺ Γ ⊢ φ | 色情内容 | - |
| 用数学归纳法证明该性质对一切自然数成立 | 色情内容 | - |
| 构造真值表…实质蕴含 | - | - |

**真违规（应全拦）：漏放 2/7 → 0/7（防护面净增强）**

| 真违规样例 | 修前 | 修后 |
|---|---|---|
| 来这个色情网站看更多内容 | 色情内容 | 色情内容 |
| 这里有一段裸体写真描述 | 色情内容 | 色情内容 |
| 详细的性行为过程描写 | 色情内容 | 色情内容 |
| 两人做爱的细节描写 | **漏放** | 色情内容 |
| 包含强奸情节的小说片段 | **漏放** | 色情内容 |
| 教你怎么制造炸弹袭击 | 恐怖内容 | 恐怖内容 |
| 宣传种族歧视言论 | 歧视内容 | 歧视内容 |

**边界（数学语境夹带真违规仍拦，3/3，修前修后同拦）**：欧拉回路性质+色情网站 / 充分性证明+裸体描写 / 对称性传递性+性行为描写 —— 全部命中「色情内容」且 `is_valid=False`。

其余三层合规词库（暴力/歧视/恐怖）与其他五层防护（敏感信息/恶意指令/注入/长度/代码块）零改动；「不许整体关过滤器、不许清空词库」红线遵守（词库从 3 个裸字收紧为 28 个显式词，色情检测能力增强）。

## ③ 任务项④：sanitize 动作损伤面评估（如实）

- `_check_compliance` **只标记不改文**（violations 记录、`sanitized_text` 原样返回）→ 消费侧 `sanitize_llm_output`（`llm_secure_io.py:96`）与 `llm_security_wrapper.chat/chat_with_tools` 对 `action="sanitize"` 都返回原文，仅 `action="block"` 才替换文案；compliance 永不置 block。
- **结论：当前接线下误报未改坏用户可见内容**——北极星数学答案文本本身完整送达。实际损伤是：(a) 每条数学回答打一条「色情内容」安全事件 warning（主会话正是从日志发现的）——安全遥测被合法流量污染，会稀释真告警信噪比；(b) `is_valid=False` + `risk_score=0.4` 附着在验证结果上，当前无下游据此丢弃内容，但属于**潜在静默腐蚀通道**（未来任何消费 `is_valid` 的接线都会开始丢合法答案）。修复后 (a)(b) 同时消除。
- 流式路径（`stream_chat`）为仅日志告警，未回滚内容——修前修后行为一致，未改动。

## ④ 测试矩阵（回归红线）

| 套件 | 修前 | 修后 |
|---|---|---|
| **新增** `tests/unit/test_llm_output_validator_math_fp.py`（38：数学句 14×2 + 真违规 7 + 边界 3） | 11 failed / 27 passed（红证） | **38 passed** |
| 既有 `tests/unit/test_llm_output_validator.py` | 47 passed（修前基线实测） | **47 passed** |
| 安全域定向：`test_llm_safety.py` + `test_llm_safety_adversarial.py` + `test_stage37_llm_safety_kill_switch.py` + `test_llm_security_wrapper.py` + `test_llm_security_wrapper_forwarding.py` + `tests/security/test_security.py` | 未单跑修前基线（改动面仅 1 个正则元组） | **143 passed** |
| `test_o03_adversarial_security.py` + `test_stage37_llm_safety_kill_switch.py` | 同上 | **229 passed** |
| `test_llm_service_security.py`（sanitize_llm_output 消费侧） | 同上 | **2 passed** |

诚实申报：除 validator 主套件做了修前/修后双跑对比外，其余定向套件仅跑修后（全绿即满足「定向全绿」红线；修前双跑需树操作，按并发工作树安全纪律规避 stash/reset）。

## ⑤ Worker 五要素

**① 误报根因**：`backend/app/core/llm_output_validator.py:102`（基线行号）`COMPLIANCE_PATTERNS` 色情项 `r"色情|性|裸"` 的单字「性」「裸」——数学学术词汇必含「性」，8/10 数学句复现误判；红证见上（修前 11 failed）。**附带发现**：旧词库对 做爱/强奸 类真色情漏放（双向破损）。

**② 修法与防漏放论证**：收紧为 28 个显式色情词的正则元组；数学误报 8/10→0/10，真违规漏放 2/7→0/7（防护净增强），边界 3/3 仍拦（无豁免通道）；未动其他词库/防护层/strict_mode 语义。

**③ 冲突面（零交集声明）**：本卡只改 `backend/app/core/llm_output_validator.py`（1 个正则元组）+ 新增 1 个测试文件。wt139（mobile）、wt140（galaxy API）、wt141（galaxy 调查）分别在 Flutter 端与 galaxy 域，与引擎安全过滤模块无共同文件、无 import 依赖、无接口变更（`COMPLIANCE_PATTERNS` 为类常量，4 元组结构不变，`get_security_stats()` 返回值不变）。零冲突。

**④ 诚实申报**：
- sanitize 损伤面如实评估：当前接线未改坏用户内容，损伤为日志/遥测污染 + `is_valid` 潜在腐蚀通道（见③任务项④节）；
- 修复过程中发现并修正了新测试文件自身的 Python 转义缺陷（`\frac`/`\bar` 被解释为 `\f`/`\b`，已改 raw string）；
- `app/gen/` 缺失，从主仓拷贝（gitignored，不进 patch、不属交付物）；
- 定向回归全绿，未跑全量 `pytest`（内存纪律：全库测试属 HEAVY，本卡改动面 1 个正则，定向 6 套件 412 测试已覆盖改动面及其全部消费侧）；
- 相邻风险（未动，建议另立卡）：暴力词库 `r"暴力|杀|死|伤害"` 的单字「死」会误伤「死锁」（OS/算法辅导）等词，与本卡同构；输入侧无色情词库无需修。

**⑤ 收工核查**：
- [x] 未 commit / 未 push；主仓只读；未动活栈
- [x] `/tmp/safety_fp_compare.py`（对比脚本）已删；无其他临时产物
- [x] 无独立端口进程 / 无模拟器 / 无构建产物（纯 pytest 定向，无 flutter/gradle/浏览器）
- [x] 交付物：`v3-output/SAFETY-FP/REPORT.md` + `changes.patch`（新文件 `--- /dev/null` 头）
- [x] patch 内零凭据（词库/测试/报告均无 secret；测试环境 `SECRET_KEY=test` 仅命令行注入）
