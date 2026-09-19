# M-03 Review Receipt 2 — DeepAudit（返修 delta 复核）

> 首轮全量审计收据（F1-F8 + 焦点正面核实）在 `Sparkle-sysrev/wt2/v3-output/M-03/REVIEW_RECEIPT_2.md`。
> 本文件为返修轮（R2-F1/F2 + R1-F1/F2 处置）的 delta 复核记录，基座 43942d23 不变。

复核人: R2 / DeepAudit ｜ 方式: wt4 只读 diff + 定向 pytest + 4 组独立变异实验（/tmp，已清理）
｜ dev DB 只读 ｜ 未 commit/push ｜ gen 符号链接按 REPORT §5 协议临时借用、复核实毕已撤除

## 1. R2-F1 复核 — 通过（两处修复均实证）

- **代码修复**: `scope_of_record` 删除 `if level not in SCOPE_LEVELS: level = "global"` 归一化，
  未知 level 原样进 descriptor（:354-361，注释明确引用 R2-F1）。
- **① 原攻击场景重放（独立探针，非复用 Worker 测试）**: monkeypatch `derive_scope` 返回
  `level="subject"` → `descriptor.level="subject"` 保留 → `allowed=0`、`dimension=scope`、
  `reason=scope:unknown_level`、`dimension_counts["scope"]=1`——从"静默注入"变为
  **fail-closed 砍除 + 指标化**。与首轮流水结论（allowed=1 注入）对照，修复确认。
- **② 不可达分支问题解决**: 新测试 `test_unknown_level_from_derive_scope_is_fail_closed`
  monkeypatch 的是 **pf 模块级 `derive_scope` 绑定**、走真实 `scope_of_record →
  prefilter_candidates` 全链（不再只配显式 descriptor 直调 `scope_compatible`）；断言 level
  保留 + 砍除 + 指标三件套。首轮"守卫钉死代码分支"的问题已消除。
- **parity 守卫亲验（源码级变异，非 monkeypatch）**: 将真实 `memory_epistemic_contract.py`
  源码拷贝至 /tmp 并注入 `scope["level"] = "subject"`（模拟 M-01 加词），以 pytest 插件换入
  sys.modules 后运行 `test_derive_scope_level_vocabulary_parity_with_prefilter` → **RED**，
  报错信息精确点名 `['subject']` 并指引扩展 SCOPE_LEVELS。"M-01 加 level 必红"端到端成立
  （inspect 读到的是变异后的真实文件源码）。词表方向为 derive_scope 产出 ⊆ SCOPE_LEVELS（保护
  方向；task_type 保持 explicit-only 属设计而非漏洞）；正则双模式覆盖 `scope["level"]="x"` 与
  `{"level": "x"}` 两种写法，扫描零命中时 fail-red（防 derive_scope 重构绕过守卫）——安全方向正确。
- 附: 空 projection（无 level 键）回退 "global" —— 真实 derive_scope 首行恒置 level="global"，
  该路径不可达，不构成发现。

## 2. R2-F2 复核 — 通过（reorder 必红，两面各自亲验）

- docstring 新增 Order note（实现顺序即唯一权威 + 与 MEMORY_V3 §3 差异理由 + 版本 bump 要求），
  §2.1 同步——首轮"三处矛盾"消除。
- **实验 A（求值 or-chain 交换 ttl↔scope）**: /tmp 插件在 pytest 收集前换入变异模块 →
  `test_evaluation_order_adjacent_pairs_are_pinned[ttl-ttl_before_scope]` **RED**（期望 ttl 得
  scope）——行为链 reorder 被相邻对测试捕获。
- **实验 B（仅 FILTER_DIMENSIONS 元组交换）**: `test_filter_dimensions_order_is_pinned` **RED**、
  5 相邻对仍绿——元组面 reorder 被专用钉序测试捕获。两面互补，任一 reorder 必红成立。
- 5 相邻对测试走真实 `prefilter_candidates`（非 mock 派发），每用例恰违反相邻两维断言先者胜出。

## 3. R1 项复核 — 通过

- **R1-F1 (I001)**: context_manager.py:29-30 与 context_builder.py:46-47 均为
  memory_retrieval_prefilter 先于 memory_service，M-03 行序正确。ruff（项目配置含 "I"）对
  context_builder.py 报 2 处 I001——经 base 43942d23 原文件导出对比确认**两处在基座即存在**
  （:21 time_utils 混入 stdlib 块、:865 函数内 aurora 局部导入块），M-03 前后错误数相同（2=2），
  未引入新 lint。REPORT §8 "ruff clean" 措辞略宽（实际为"M-03 触达行 clean"），不构成缺陷。
- **R1-F2 (stage34) 红绿亲验**: `test_stage34_episodic_prompt_injection_is_prefiltered` +
  `test_stage34_user_settings_permissions` 单独亲跑 **2 passed**（真实 DB 行 + payload 面与
  `format_user_context` 渲染面双断言）；`git stash push -- context_builder.py` 后同两测试
  **2 failed**（superseded 行 importance=0.99 高居榜首泄漏进渲染提示词）→ pop 恢复。红绿真实性
  独立重证。stage34 函数其余拉取核实：`PlanService.list_active`（plans 族，非 V3 记忆）、
  `get_last_session_mood`/`list_recent_calibration_receipts`（Redis 会话信号，非记忆表）——
  stage34 记忆面无残余未预筛拉取。

## 4. 套件与回归、patch 与登记

- **M-03 套件 68/68 亲跑通过**（61 单测含参数化 + 7 集成，与 REPORT §8 一致）。
- **回归抽 4 文件 18/18 通过**: test_context_builder_mixin（stage34 邻接+夹具适配）、
  test_past_session_memory_ranking、test_context_manager、h6_dialogue_quality_audit
  （scenario4 经 get_context 全链渲染提示词）。
- **patch**: `changes.patch` 精确 11 文件列表（8 改 + 3 新，逐文件核对，无 add -A 副产品、无
  gen、无 v3-output 混入）；`^+` 行 1994 - 11 文件头 = **+1983/-6** 与声明一致；
  `git apply --check --reverse` 通过。行数实测：模块 716 / 单测 718 / 集成 447。
- **登记完整性（派卡输入确认）**: §6.4 routing_engine:2530 + aurora/signal_aggregator:99-110
  （R2 裁决登记不接线，M-04 必含前两项）；§6.6 goal_id 别名正名；§6.7 today-only UTC 切日 →
  M-07 时区裁决；§6.8 settings 读失败方向 → M-04；§6.9 plan-only 过砍 task 锚守则 → M-04；
  §7 另登记滚动部署缓存 bump。协调方点名的五项全部在册且有明确去向。

## 5. 结论

首轮 P1（F1）与 P2（F2）修复均经独立变异实验证实闭环；R1 两项处置属实（I001 为基座预存、
stage34 红绿独立重证）；登记项完整可作 M-04/M-07 派卡输入。无新增发现；唯一注记为 REPORT
"ruff clean" 措辞（见 §3，不影响交付）。收工清理已做：wt4 gen 符号链接撤除、wt4 状态恢复
复核前原样、/tmp 实验目录与探针全删。

VERDICT: ACCEPT
