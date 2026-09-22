# SAFETY-LEX（重派）：合规词库误报审计——强制遮蔽法 · 收工报告

- 卡号：SAFETY-LEX（重派）｜基线：`be10d59e`｜worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt146`
- 日期：2026-09-22｜审计对象：`backend/app/core/llm_output_validator.py` 的 `COMPLIANCE_PATTERNS`
- 结论一句话：**唯一确证误报源 = 首条目（violence 类，见 desc 标签）的两个单字 token**（教学语境 44 句良性语料误拦 9 句，20.5%）；已按显式词表法修复（chr 序列编码，交付物零词库明文），修后误报 0/44，全部拦截面零回退，安全域定向 410 例全绿。

---

## 0. 遮蔽纪律执行情况（前卡阵亡教训）

- 全程未 Read 词库文件词库段；结构分析走 AST（`ast.parse` + 字面量长度/类别统计），终端输出一律经 shroud 净化（词库字面量 → 定长星号）。
- 交付物（本报告 + changes.patch）经**自家 validator 修后词库**字符串匹配自扫：**零命中**（类别 desc 标签「暴力内容/色情内容/歧视内容/恐怖内容」定义为豁免项——它们是既有合规元数据而非词库词，已在全库日志与历史提交中公开存在）。
- 诚实记录：审计中段一次自扫工具调试向前卡 `SAFETY-FP/REPORT.md` 打印了 12 字符级命中上下文（该旧报告含 76 处词库明文，系旧纪律产物），随后立即停止对其的一切读取。本卡交付物不受影响。
- 新词表以 **chr 序列编码**写入 validator 源码（`_VIOLENCE_LEX_SEQUENCES`，20 组码点序列），解码：`"".join(chr(c) for c in seq)`。这是「词表程序化、不进我的输出」约束下唯一能同时满足「patch 可交付 + 自扫零命中」的形态。

## 1. 结构审计表（修前，掩码形态；① 要素）

`COMPLIANCE_PATTERNS` 共 **4 条目**，全部为「最短字面量 ≤2 字」的误报风险候选：

| idx | 修前行号 | 类别 | 模式长 | alt 数 | 最短 alt | ≤2字候选 | 掩码形态 |
|---|---|---|---|---|---|---|---|
| 0 | L101 | violence | 9（6 CJK） | 4 | **1** | YES | 单字×2 + 双字×2 |
| 1 | L107 | adult | 97（68 CJK） | 30 | 2 | YES | 双字×22 + 三字×8 |
| 2 | L113 | discrimination | 8（6 CJK） | 3 | 2 | YES | 双字×3 |
| 3 | L114 | terror | 8（6 CJK） | 3 | 2 | YES | 双字×3 |

注：entry1 即前卡 SAFETY-FP（be10d59e）修复产物（30 词显式成人词表，无单字）；entry0 为其未触及的遗留条目，**含两个单字 token**。

## 2. 误报判定（不打印词内容）

方法：44 句良性语料（计算机 19 / 数理 8 / 生物医学 5 / 日常 3 / 英文技术词 9，含死锁、死循环、死代码、死机、僵死进程、杀毒、查杀、秒杀、银行家算法、恐龙、恐慌、种群、色数、色彩、弹性、消毒、deadlock、fork bomb、kill -9、brute force 等），直接跑真 `LLMOutputValidator(strict_mode=True)` 的合规层（Layer 5），匹配文本程序化净化后人工判读。

**修前结果：9/44 误拦（20.5%），全部命中 entry0（desc 标签「暴力内容」）**；entry1/2/3 对全部 44 句零误报（色数、色彩、恐龙、恐慌、种群、种类、弹性、消毒、毒性等学术词均安全）。

误拦句明细（均为本产品核心教学场景）：

| # | 误拦句代称 | 命中 token（掩码） |
|---|---|---|
| 1 | 死锁四必要条件句 | 单字①（len1） |
| 2 | 死循环句 | 单字① |
| 3 | 死代码消除句 | 单字① |
| 4 | 服务器死机句 | 单字① |
| 5 | kill -9 终止僵死进程句 | 单字①（另见 §7-B malicious 层发现） |
| 6 | 杀毒/查杀句 | 单字②（len1） |
| 7 | 杀掉子进程句 | 单字② |
| 8 | 秒杀系统句 | 单字② |
| 9 | 银行家算法（死锁避免）句 | 单字① |

真值核验：前卡遗留真值集（`test_llm_output_validator_math_fp.py` 的 REAL_VIOLATIONS×7 + BOUNDARY_MIXED×3）逐条检测，命中分布为 entry1×8、entry2×1、entry3×1——**零依赖 entry0**，证明收紧 entry0 不回退既有拦截面。数学 14 句修前修后均 CLEAN。

## 3. 修复内容（仅动确证误报的 entry0）

- **改动**：`llm_output_validator.py` L101 单行条目 → `_VIOLENCE_LEX_SEQUENCES`（20 组 chr 序列，L105 定义）+ 由其解码 join 构造的 entry0（`"|".join("".join(chr(c) for c in seq) ...)`），desc 标签不变（下游日志/断言兼容）。
- **词表构成**：原显式双字词 2 个保留 + 新增 18 个（17 双字 + 1 三字，威胁/加害/自伤指向的显式词）。词表明文只存在于 worktree 源码（以码点序列存储）与解码运行时，**不入任何交付物**。
- **选取原则（精度取舍）**：只收「孤立出现即构成合规信号」的显式词。显式排除的高频良性复合词：`杀死`（生物/医学高频，如免疫杀伤）、`打死`（游戏语境高频）、`处死`（历史教学高频）、`致死`（医学术语）、以及两个原单字本身（死锁/杀毒/秒杀等一切复合词的词根）。残余风险见 §7-C。
- **未动面**：entry1/2/3 一字未动；`SENSITIVE/MALICIOUS/CODE_INJECTION` 三层未动；`get_security_stats()` 结构零改动（键集合与 `compliance_patterns=4` 已由新测试钉死）；其余防护层零改动（diff 仅含合规区块 + 新测试文件）。

## 4. 修前后数字对比（② 要素，代称引用）

| 验证炮组 | 修前 | 修后 |
|---|---|---|
| A. 良性语料合规误报（44 句） | **9 误拦** | **0 误拦** |
| B. 既有真值拦截面（10 例） | 10/10 拦 | **10/10 拦**（零回退） |
| C. 新词表真值样例（词表逐词 × 载体句） | —（词表新设） | **74/74 拦** |
| D. 边界：良性长句夹带词表词 | —（新断言） | **拦截**（无豁免通道） |
| E. 离散数学语料（14 句） | 14/14 CLEAN | **14/14 CLEAN** |
| pytest：validator 主套件 + math_fp | 85 passed | **85 passed** |
| pytest：wrapper 族（下游消费方） | 20 passed | **20 passed** |
| pytest：新增 SAFETY-LEX 回归 | — | **54 passed** |
| pytest：安全域定向（11 个测试文件） | **410 passed**（基线 clone 实测） | **410 passed** |

对比法说明：基线 clone（`/tmp/safety-lex-baseline`，即 be10d59e 天然基线）实测 85+410=495 passed；修后 worktree 同套件 85+54+410=549 passed，增量恰为新增回归，**零回退零连带破坏**。

## 5. 回归钉死（新测试文件）

`backend/tests/unit/test_llm_output_validator_lexicon_fp.py`（54 例，fixture 程序化构造、零词库明文）五类断言：

1. `TestTeachingZeroFalsePositive`：44 句良性语料逐句 + 汇总零合规误报（合规层解耦断言，只认「潜在违规」前缀，不受其它层噪声干扰）；
2. `TestLexiconSurfaceIntact`：**任何合规条目不得再出现单字 token**；词表逐词孤立出现必拦、载体句必拦；每条目词表与模式不脱钩；`get_security_stats` 键集合与条目数钉死；
3. `TestBoundaryNoExemptionChannel`：良性语境/长文夹带词表词仍拦；
4. `TestMathCorpusNotRegressed`：直接复用前卡 `MATH_SENTENCES` 防 双卡语料互相回退；
5. 真违规样例全部由「模块词表自取 + 载体句拼接」生成——未来任何删词/改词都会被逐词断言当场暴露，属**有意变更需显式更新测试**。

## 6. 冲突面申报（③ 要素）

- 本卡触碰文件仅：`backend/app/core/llm_output_validator.py`（修改，合规区块 1 处）+ `backend/tests/unit/test_llm_output_validator_lexicon_fp.py`（新增）+ `v3-output/SAFETY-LEX/`（交付物，gitignored）。
- 在途卡均在 backend galaxy/events 域——与本卡**零交集**。未 commit、未 push，worktree 内变更 = 上述文件（`app/gen/` 为主仓拷贝的 gitignored 生成物，供测试导入，不入 patch）。
- 附：测试文件已 `git add -N`（intent-to-add，使 `git diff` 可复现 patch；非提交）。

## 7. 诚实申报（④ 要素）

- **A. 无法遮蔽判定而跳过的**：entry1（成人 30 词）未做逐词人工语义核验——人审每词必须见词明文，违反遮蔽纪律。已用行为面覆盖（44 良性 + 14 数学 + 10 真值 + 30 词逐词必拦断言）替代；逐词人审留人工。
- **B. 范围外发现（登记不修，建议另立卡）**：`MALICIOUS_PATTERNS` 中一条 12 字节模式匹配 `kill -9 ` 类文本，使运维教学句在 Layer 3 被 `sanitize`（误拦 s05 句，本次良性语料即含 1 例）。该层不在本卡 COMPLIANCE 审计范围；鉴于「LLM 输出含高危命令」可能是有意的防护设计，建议 SAFETY-OPS 卡评估白名单（如限定教育语境豁免）。
- **C. 残余误报风险（已入表词的语境误报，接受并记录）**：新表中个别与爆炸/清洗类事件相关的双字词，在游戏战报、历史与文学分析语境可能误拦——但合规层动作是 `sanitize + 人工审核`（非 block），且第 3 节已排除最高频的四个良性复合词，属产品合理取舍。具体词面见源码 hex 表（附录A 解码法）。
- **D. 可读性代价**：词表以码点序列存储，源码不可直读；解码一行 `python3 -c` 可得（见附录A）。此为本卡遮蔽纪律的直接要求，若舰队后续决定放宽，可一键解码回明文提交。

## 8. 交付物与自扫证据（⑤ 要素之一）

- `v3-output/SAFETY-LEX/REPORT.md`（本文件）——自扫 **CLEAN**；
- `v3-output/SAFETY-LEX/changes.patch`（226 行：validator hunk -U0 + 测试文件新文件 hunk）——自扫 **CLEAN**；
- 自扫器：对两交付物全文跑修后词库全字面量匹配（desc 标签豁免），结果零命中；
- patch 可应用性：测试文件 hunk 在基线 clone 上 `git apply --check` **通过**；validator hunk 因唯一一行修前条目明文被红改（`[SAFETY-LEX-REDACTED]`）而**不可直接 apply**——worktree 内已修复的源文件即真相源（§附录A）。

## 9. 收工核查（⑤ 要素之二）

- [x] worktree 内无构建产物（未跑过 flutter/gradle/docker）；无独立端口进程；无模拟器
- [x] `/tmp/safety_lex`（脚本/语料/hex 表）与 `/tmp/safety-lex-baseline`（基线 clone）收工即删
- [x] 主仓全程只读；无 `.env` 创建（测试用 `SECRET_KEY=test`）
- [x] `git status` 仅含申报文件；未 commit 未 push
- [x] 交付物自扫零词库明文

## 附录A：patch 应用 / 重建指引（给 Leader）

1. **推荐**：直接以 worktree `wt146` 的 `backend/app/core/llm_output_validator.py` 与 `backend/tests/unit/test_llm_output_validator_lexicon_fp.py` 为准合入（文件即真相源，已过全量回归）。
2. patch 的测试文件 hunk 可独立 `git apply`；validator hunk 的红改行重建：取 `git show be10d59e:backend/app/core/llm_output_validator.py` 第 101 行（该行即被替换的旧条目），整行删除，替换为 patch 中 `+` 区块（`_VIOLENCE_LEX_SEQUENCES` + 解码 join 条目）。
3. 词表核对：`python3 -c "import sys; sys.path.insert(0,'backend'); from app.core.llm_output_validator import LLMOutputValidator as V; print(sorted(set(V.COMPLIANCE_PATTERNS[0][0].split('|'))))"` 可在合入后导出词表做人审（第 7-A 项）。

## 附录B：关键复现命令

```bash
cd /Users/brsama/code/GitHub/Sparkle-sysrev/wt146/backend
SECRET_KEY=test /opt/homebrew/bin/pytest tests/unit/test_llm_output_validator_lexicon_fp.py \
  tests/unit/test_llm_output_validator.py tests/unit/test_llm_output_validator_math_fp.py \
  tests/unit/test_llm_security_wrapper.py tests/unit/test_llm_security_wrapper_forwarding.py -q   # 159 passed
SECRET_KEY=test /opt/homebrew/bin/pytest tests/unit/test_llm_safety.py \
  tests/unit/test_llm_safety_adversarial.py tests/unit/test_core_security.py \
  tests/unit/test_o03_adversarial_security.py tests/unit/test_stage37_llm_safety_kill_switch.py \
  tests/unit/test_llm_service_security.py tests/unit/test_document_security_fixes.py \
  tests/unit/test_fsm_context_guardrails.py tests/unit/test_context_hard_filter_wiring.py \
  tests/unit/test_memory_prefilter_integration.py tests/unit/test_x06_tool_call_safety.py -q       # 410 passed
```
