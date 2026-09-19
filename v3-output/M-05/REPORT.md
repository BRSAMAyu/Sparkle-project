# M-05 Over-personalization Self-ReCheck — 执行报告

worktree: `Sparkle-sysrev/wt4`，base = HEAD `2375694c`（C-03 ACCEPT merge 后）
gate: V3-2 ｜ stream MEMORY ｜ risk medium ｜ reviewers_required 1 ｜ locks: memory-retrieval, ai-eval
禁 commit/push（已遵守，全部改动为工作区未提交状态）。改动全文见 `changes.patch`
（6 文件修改 + 5 文件新增，正向 apply 已在基线浅克隆上校验通过）。真实 LLM 调用 **0 次**。

## 1. 接续盘点（前任 worker 额度中断遗留，~15 分钟工作量）

`git status` 显示 3 个 untracked 草稿，逐文件判定如下：

| 文件 | 判定 | 处置 |
| --- | --- | --- |
| `backend/tests/fixtures/op_bench_memory_use_v1.json` | **合格沿用**。46 case（must_block 21 / must_surface 24 / known_limitation 1），四检查×两档×正反例矩阵完整，标注对齐 MEMORY_V3 §4 与 PERSONALIZATION_EVAL（含对抗项 "repeatedly mentioned preference should not appear in every response"），盲评纪律声明在案 | 原样交付（本目录副本） |
| `backend/tests/unit/test_memory_use_selfcheck.py` | **合格沿用，修 1 处数据 bug**。38 测试完整钉住契约（封闭词表冻结/求值顺序/meta⊆writer 词表/fast-model 只收紧+封闭 reason/阈值冻结），测试先行质量高。bug：`test_fast_model_hook_tightens_surfaced_item` 的 e1（"用户看了星际穿越" vs 提问"高数期中考试"）零词法重叠 → 规则层先砍，hook 永不被咨询，与该测试自述意图（"钩子把规则放行条目降档"）矛盾 → 改 e1 为"用户看了电影星际穿越，对其中的高数彩蛋很好奇"（有共享 bigram 放行、语义不符留给 hook 演示） | 修复后沿用 |
| `backend/tests/unit/test_memory_use_selfcheck_wiring.py` | **合格沿用，修 2 处装配 bug**。(a) W-G2 渲染断言 `count==1` 不可能成立：渲染器对每条记忆输出 `content:` 与 `natural_line:` 两行（实测 1 条=2 次、2 条=4 次），改为 `==2`（红条件不变）；(b) W-G3 `ContextOrchestrator(db_session)` 缺必填 `redis_client` → 补 `None`（同 M-03 集成测试同型） | 修复后沿用 |

前任未写实现模块与接线（测试先行状态）。实现按测试契约从零完成，另发现前任 3 个测试
设计上的隐藏问题在实现校准中暴露（见 §5 echo 校准、§6 旧夹具对齐）。

## 2. 交付形态（六句总结）

检查器形态：单一权威模块 `backend/app/services/memory_use_selfcheck.py`——纯函数核心
`evaluate_memory_use_gate(preferences, goals, episodic, ctx)`（零 I/O、零 LLM、同步确定性），
四检查固定求值序 relevance → necessity → repetition → sycophancy，**首失败独占归因**（M-03
`FILTER_DIMENSIONS` 同法）；`run_memory_use_selfcheck` 为 fast-model 钩子异步壳：只在接线层
默认关、只对规则放行条目咨询、**只收紧不放松**、reason 必须落封闭集 `FAST_MODEL_REASONS`
（否则 ValueError，非法 reason 不可能进指标）。两档用途：`SURFACE_TO_USER`（可进渲染 prompt
面）与 `USE_FOR_INTERNAL_DECISION`（保留给内部决策面——pack 面实测降档条目仍完整进入
`_build_decision_context`，召回不删）。接线三面 + kill-switch
`settings.ENABLE_MEMORY_USE_SELFCHECK`（默认开；关=passthrough 且不写 metadata，显式运维
动作）：W-G1 `context_pack.build`（有 query_text 的话题面权威 gate；claims/evidence_summary
同步排除防正文经 metadata 复活）、W-G2 `context_builder._attach_stage34_memory_context`
（主聊天 payload episodic 注入面，M-03 R1-F2 同位）、W-G3 `context_manager.
_get_past_session_memory`（past-session 拉取面）。与 M-03/C-03 分工：它们是候选池准入硬过滤
（能不能进来），本卡是合法候选在输出装配面的使用自检（该不该用/该不该说出来）。验收双指标
（OP-Bench 46 case，规则层盲跑）：**过度个性化率 0.0%（0/21，目标 ≤5%）；合法个性化保持率
100%（24/24）**；无关记忆可召回但不进输出（W-G1 行为级测试：CAT 无关记忆被降档出
pack.episodic_memories 但保留在 decision_context 与 metadata ids/reasons）。

## 3. 检查规则（规则层确定性实现）

- **词法模型**：CJK 字符 bigram + ASCII 小写字母数字词（`lexical_tokens`）。
- **relevance**：无话题信号（无消息/phatic 轮）→ 不定保守放行（M-03 unconstrained 同法，
  phatic 归因给 necessity）；meta 沟通形态偏好（`META_PREF_KEYS` ⊆ 写方词表
  `PREFERENCE_KEYS`，守卫钉死）恒相关；其余候选与提问零词法重叠 →
  `selfcheck:irrelevant_to_query`（pref_key 域名计入候选内容面）。
- **necessity**：安全钉与 meta 偏好豁免；phatic 轮（封闭词表 + 尾缀语气词归一，吧/吗刻意
  不在集合——"对吧"是求认同不是寒暄）→ `selfcheck:phatic_query`；回声（剥"用户"称呼前缀
  后覆盖 ≥0.85 且 |C|≥4 token）→ `selfcheck:echoed_in_query`。
- **repetition**：窗口任一 assistant 轮已传达记忆内容（覆盖 ≥0.6）→
  `selfcheck:recently_surfaced`（安全钉/meta 豁免——安全信息重复提及的社交成本 < 健康风险，
  形态一致性不是重复伤害）；包内近重复（smaller-set containment ≥`DUPLICATE_JACCARD_RATIO`
  =0.8，优先序在前的胜出）→ `selfcheck:duplicate_in_pack`。
- **sycophancy**：只绑认同偏好类 `AGREEMENT_BIAS_PREF_KEYS` ⊆ META（feedback_style/
  feedback_tone/coaching_style）× 肯定式值（`AFFIRMATIVE_VALUE_MARKERS` 封闭集）× 求认同
  cue（`VALIDATION_CUE_MARKERS` 封闭集）三条件同时成立 →
  `selfcheck:agreement_bias_risk`；实质工作轮照常塑造语气（合法个性化保留）。
- **安全钉**：`SAFETY_PIN_CONTENT_MARKERS` 封闭内容词表（过敏/休克/麸质/gluten/哮喘/糖尿病
  等）豁免全部话题检查——词法 gap 把过敏事实挡在 surface 外的代价是物理伤害；包内去重仍
  生效（保留一份 surfaced 即可）。

## 4. 接线与可观测

- **W-G1 `context_pack.build`**：budget 裁剪后、consumption 标记后接线。降档只作用于
  prompt 面（`trimmed_*` → pack.face），`decision_tier_*` 未门控副本传
  `_build_decision_context`（两档用途的行为级证据）；`metadata["memory_selfcheck"]` =
  指标 payload + `internal_only`（ids+section+封闭 reason，**无正文**——metadata 经
  `to_prompt_context()` 进 prompt，W-G1 专门测试 CAT 正文不因 claims/evidence_summary 复活）。
- **W-G2 stage34 / W-G3 past-session**：该两面无本轮对话信号 → relevance/跨轮 repetition
  休眠（unconstrained 保守放行），仅包内去重生效（W-G2 近重复不进渲染 prompt；W-G3 去重后
  再切 limit，近重复不再浪费名额）。
- **已知边界**：pack 面暂无 assistant 历史窗口可取 → 跨轮 repetition 在接线面休眠
（纯 gate API 层可用；单元测试明示 known-boundary）；跨会话窗口语义留待后续卡。

## 5. 实现校准中被测试逼出的修正（红→绿证据链）

1. **echo 误伤（C-03 兼容红）**：初版 echo 阈值 0.8 使 C-03 合法条目被误砍
   （`LEGAL-EVENT` 全含于提问 `LEGAL-EVENT topic`；`LINEAR-...-NOTES` 覆盖恰 0.8）。
   基线对照定位（同测试在 pristine HEAD 绿）后校准：剥"用户"前缀 + 阈值 0.85 + |C|≥4
   token 下限——"提问点名记忆主题"与"用户刚陈述过该事实"两类被区分开。
2. **phatic 尾缀词**："谢谢啦"因"啦"不在封闭词表被误判为实质轮 → 尾缀语气词归一
   （`_phatic_run_core`），吧/吗刻意排除（求认同 cue 轮不能被当寒暄放行）。
3. **旧夹具教义对齐**：两个 C-02/C-03 期测试在 TCP 提问下断言无关记忆（音乐偏好）/
   英文摘要记忆必进 pack 面——正是本卡要拦的形态。意图保全式最小修改：夹具摘要改为与
   提问同域（claim 标注/manifest 分类断言全部保留），`depth_preference` 认入 META
   （决定回答深度的沟通形态偏好，ai_verbosity 同族）。

## 6. 验收证据

### 6.1 双指标（OP-Bench `op_bench_memory_use.v1`，规则层盲跑，零 LLM）

| 指标 | 结果 | 阈值 | 判定 |
| --- | --- | --- | --- |
| 过度个性化率（must_block 泄漏 / 21） | **0.000（0 泄漏）** | ≤0.05 | PASS |
| 合法个性化保持率（must_surface 存活 / 24） | **1.000（0 误伤）** | ≥0.90 | PASS |
| known_limitation 登记 | 1 case（op-rel-ep-06，2.2%） | 披露不入 headline | 如实披露 |

known_limitation 内容：CJK/EN 词法鸿沟（《星际穿越》记忆 vs "recommend a movie similar
to Interstellar"）——语义相关但词法零重叠被规则层误拦；fast-model 钩子（默认关）是设计内
补救，开闸前必须有独立 eval 证据。**Tradeoff 声明**：0.0/100% 是 bench 内数字；生产混脚本
流量（英文内容记忆 × 中文提问）会落在该已知误伤面，量化属后续 ai-eval 域工作（fast-model
钩子开闸评估）。词表/阈值任何演进必须 bump `SELF_CHECK_VERSION` 并重跑双指标——冻结测试
钉死 reason/section/payload 词表、求值序与 `DUPLICATE_JACCARD_RATIO`。

### 6.2 测试（命令统一 `SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest`，backend/ 下）

| 套件 | 结果 |
| --- | --- |
| `tests/unit/test_memory_use_selfcheck.py`（纯函数契约 38） | 38 passed |
| `tests/unit/test_memory_use_selfcheck_opbench.py`（46 case 参数化 + 结构完整性 + 双指标） | 48 passed |
| `tests/unit/test_memory_use_selfcheck_wiring.py`（3 AST 钉 + 6 行为级 + kill-switch） | 9 passed |
| 邻接回归（M-03 prefilter 集成/C-03 hard-filter 接线/context_pack×7/context_manager/stage34×3/prompt 消费者） | 全绿 |
| 有界大扫（`-k "memory or context or prompt"`，857 测试） | 845 passed + **12 失败=预存**（与 pristine 基线失败清单逐条 diff 完全一致：working_memory_consolidation/aggregator、memory_*_api、user_insight_compiler，本卡未触碰其模块） |

### 6.3 变异必红（删 final-gate；/tmp 备份式单文件变异，已恢复）

三面 gate 同时以 `if False:` 禁用（含常量假分支——AST 钉剪枝后同样失守）→
`test_memory_use_selfcheck_wiring.py` **7 红**（3 AST + W-G1×2 + W-G2 + W-G3），kill-switch
测试与 C-03 兼容测试保持绿（禁用语义=显式豁免，正确）；恢复后 9/9 绿。

### 6.4 基线对照

`git clone wt4 /tmp/m05-baseline`（HEAD `2375694c`）+ 拷入 gitignored `app/gen`：C-03
`test_wm_context_pack_never_ranks_or_embeds_illegal_memory` 基线绿 → 定位本卡 echo 误伤
（§5.1）；`changes.patch` 在该基线 forward-apply 校验通过（patch 完整自洽）。

## 7. 风险与遗留

- **词法层天花板**：CJK/EN 鸿沟已登记；语义残余空间由 fast-model 钩子承接（接口已钉、
  默认关、reason 封闭、只收紧）。开闸属 ai-eval 域后续工作。
- **窗口接线空白**：跨轮 repetition 的 assistant 窗口在三接线面均暂不可得（known-boundary
  测试在案）；后续若 orchestrator 面可取近轮 assistant 消息，接线只需补 ctx 构造。
- **安全钉词表封闭**：仅内容标记（过敏/休克/麸质/gluten/哮喘/糖尿病/癫痫/胰岛素/肾上腺素），
  未含的医药事实（如"服用二甲双胍"）不享受钉——词表演进走 bump 版本 + bench 重跑纪律。
- **旧夹具改动**（§5.3）与前任草稿修复（§1）均已在本报告披露，供 Reviewer 独立复核。

## 8. Reviewer 复现清单

```bash
cd backend
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest \
  tests/unit/test_memory_use_selfcheck.py \
  tests/unit/test_memory_use_selfcheck_opbench.py \
  tests/unit/test_memory_use_selfcheck_wiring.py -q        # 95 passed
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest \
  tests/unit/test_memory_use_selfcheck_opbench.py::test_opbench_tradeoff_metrics -q -s
# → over-personalization rate = 0.000；legal personalization retention = 1.000
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest tests/unit/test_context_hard_filter_wiring.py tests/unit/test_memory_prefilter_integration.py -q   # 邻卡不回归
```

STATUS: READY_FOR_REVIEW
