# CTX-PACK：context_pack 召回静默缺失修复报告

> 2026-09-22 ｜ Worker：wt104（基于 main@db9e9fd8）｜ 交付：`changes.patch` + 本报告
> 接卡来源：MEM-AMNESIA（wt97）报告 §4 既有失败 #1 的转交申报

---

## 1. 两件各根因一句

1. **「无 embedding provider 时静默不 surface 记忆」是误诊**：`app/core/context_pack` 直连召回链的 embedding 依赖点只有语义门控（`_apply_semantic_gating`），它在 `EmbeddingNotConfiguredError` 时已 fail-soft（warning 日志 + metric + `fallback_reason` 进 metadata + 原样返回候选，非向量召回路径 L0 SQL 列表 + 词法 rank 全程可用）——**真正把记忆切空的是 M-05 Self-ReCheck 的 relevance 词法检查**（`memory_use_selfcheck._relevance_flag`）：红测试场景「早上好，今天从哪里开始？」与跨会话记忆「TCP 流量控制有点难，明天还要考高数」零词法重叠 → 降档 internal-only → prompt 面直接空，且该切割零日志（排障时唯一可见的 embedding WARNING 因此被误认为因果）。探针实证：同一场景 selfcheck 关 → 记忆 surface（episodic=1）；selfcheck 开 → episodic=0、`reason_counts={'selfcheck:irrelevant_to_query': 1}`。该切割与 embedding provider **是否存在无关**。
2. **存量红测试有两层问题**：(a) 断言 `prompt.startswith("## 跨会话记忆 [L2 引导]\n")` 反映的是旧渲染位置——R2-final(a2) 已把记忆段从 prompt 最前部挪到**末尾**（紧邻 user 消息，修 qwen3.8-flash「没有记录」失败模式），`startswith` 断言过期；(b) 即使改成 `in`，链路仍真断——(1) 的 M-05 误降档让记忆根本进不了 pack（探针实测 `memory=0items/2tok`）。测试语义（跨会话记忆应进 prompt、问候/续接开场自然衔接）仍然有效且与渲染层已上线的 L2 引导语明确一致，故按真 bug 修。

## 2. 修复面（6 文件：2 app + 2 测试改 + 2 测试新增，+416/−11）

| 文件 | 改动 |
|---|---|
| `backend/app/services/memory_use_selfcheck.py` | **M-05 v2→v3**：新增会话续接开场保守放行——`CONTINUATION_CUE_MARKERS`（从哪里开始/接着上次/今天学什么…）/ `NO_TOPIC_CJK_RUNS`（裸问候+裸时间词）/ `_CONSUMABLE_ASCII_WORDS` 三个封闭词表 + `is_continuation_opening()`（含 ≥1 暗示词 **且** 全部内容 run 被封闭词表消耗完毕才成立）；`_relevance_flag` 的 conservative-pass 扩及该形状。带主题词的「继续讲泰勒公式」不保守放行、纯 ack 照走 phatic 降档——反过度-personalized 语义不松动。`SELF_CHECK_VERSION` 按词表纪律 bump v3；模块 docstring 同步。 |
| `backend/app/core/context_pack.py` | **只加观测，不改召回语义**：① `_apply_semantic_gating` 区分配置性降级——`EmbeddingNotConfiguredError` → `fallback_reason="embedding_not_configured"`（原与运行时故障混为 `embedding_error:EmbeddingNotConfiguredError`）；② 装配面新增「召回静默缺失观测面」：有合法候选进装配而三 section 全空时，落 `metadata["memory_surface_downgrade"]`（候选数/surface 数/selfcheck 归因/gating fallbacks/`embedding_unavailable`）+ 显式 WARNING 日志——从此「直接空」永不静默。 |
| `backend/tests/unit/test_memory_inferred_write_lane.py` | 红测试断言对齐：`startswith` → `"## 跨会话记忆 [L2 引导]" in prompt` + 尾部位置断言（`index(记忆段) > index(输出格式约束)`），附两条根因注释；四条语义断言（自然衔接语/两条事实/inferred 或 chat 来源）原样保留。 |
| `backend/tests/unit/test_selfcheck_domain_gloss.py` | 版本钉随词表纪律 v2→v3（`test_version_bumped_for_vocabulary_change`）。 |
| `backend/tests/unit/test_selfcheck_continuation_opening.py` | **新增** 12 例：`is_continuation_opening` 形状锁定（红场景句/带主题词/纯 ack/组合形状）+ gate 级三态（续接开场 surface / 主题无关维持降档 / 纯 ack 维持 phatic 降档）+ 词表纪律（v3 钉、暗示词与 phatic 词表不相交、NO_TOPIC 裸词）。 |
| `backend/tests/unit/test_context_pack_surface_observability.py` | **新增** 2 例：`embedding_not_configured` 专用 fallback_reason；有候选但空面必须带 `memory_surface_downgrade` 标记（含 selfcheck 归因 + `embedding_unavailable=True`）。 |

不碰面声明：`memory_inferred_write_lane.py` 的 B1-B 明示事实词典面零改动（本卡测试夹具只是**使用**它）；`prompts.py` 渲染层零改动；declared_fact 写入链零改动；M-05 既有四检固定顺序、封闭词表、阈值、fast-model 钩子契约全部不动。

## 3. 红→绿 + 回归统计（全部进程内哑值 `SECRET_KEY` 运行，worktree 无 .env）

**基线（修复前）**：新词表测试 import 红（词表不存在）；观测面 2 例红（fallback_reason 仍为混称、无 downgrade 标记）；存量红测试红（`startswith` 失败 + `memory=0items`）。均已在修复前实测留证。

**修复后**：

| 套件 | 结果 |
|---|---|
| 存量红测试（inferred_write_lane 全文件） | **7 passed**（含 `test_two_consecutive_sessions_prompt_includes_inferred_memory` 红→绿） |
| **declared_fact 18 例（红线面）** | **18 passed** |
| M-05 自检家族（selfcheck / wiring / OP-Bench 46 例 / domain_gloss / continuation 新测） | **120 passed**（OP-Bench 双指标不动：46 例逐案极性全过，over-personalization 与 legal retention 无漂移） |
| 观测面新测 | 2 passed |
| context pack 家族（pack ×7 / source_contract / sources / hard_filter / cache_versioning） | **93 passed** |
| memory 家族（prefilter ×2 / storage_gate ×2 / past_session_ranking / service_reads / working_memory ×2 / chinese_commitment / revival ×2 / conflict_resolver ×2 / queue / epistemic / provenance） | **211 passed** |
| reflection_kill_switch / subject_type | 4 passed + 1 passed/1 skipped |
| 合计 | **≈460 例绿，0 新增失败** |
| lint | ruff 全绿 + black 120 合规（仅本卡改动文件；未重排仓库既有行） |

诚实申报（留主会话裁决的产品语义问题）：
- **裸问候轮（如单独「早上好」）**：本次修复刻意**不**改变其行为（无暗示词不保守放行，仍被 relevance 切）——但渲染层 L2 引导语对「问候」的承诺同样覆盖它。若主会话认为裸问候也应 surface 跨会话记忆，把 `早上好` 等裸问候 run 视为续接开场是一行词表事（本卡词表已就位），但会扩大 surface 面，建议过 OP-Bench 后再定。
- **embedding_not_configured 的召回语义**：维持现状（非向量路径本就完整可用，语义门控 fail-soft 降级到词法 rank）——按卡片「对照 memory 服务降级先例」（Stage26 consolidation：显式 log + 继续降级路径），本卡补齐了同款显式 log + metadata 标记，未引入新的行为分支。

## 4. 收工核查

- [x] 修改仅在本 worktree（wt104）内；主仓只读未动
- [x] 无 .env 创建/复制；测试全部进程内哑值 `SECRET_KEY`（inline env，未落盘）
- [x] 交付物：`v3-output/CTX-PACK/changes.patch`（6 文件：2 app + 2 测试改 + 2 测试新增，+416/−11）+ 本报告
- [x] 探针/一次性文件已删：`tests/unit/test_zz_throwaway_probe.py`、`/tmp/ctxpack_probe/` 已清
- [x] `backend/app/gen/` 为 gitignore 内本地构建产物（`buf generate` + stub sync，测试必需），不入 patch
- [x] 无模拟器/浏览器/Gradle/独立端口进程（全 LIGHT 任务）；内存纪律遵守
- [x] 未 commit / 未 push
