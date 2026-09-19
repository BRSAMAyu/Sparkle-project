# 测试债第五波清理（testdebt-wave5）

基线：`d4338948`（worktree wt7，前任会话被重启中断，遗留 mobile l10n 产物已存 /tmp 后 `reset --hard`）。挂账 5 红（3 项）全部清零：review_skip 2 红**对齐现行语义**、reflection 3 红**对齐 messages-first 新签名**；galaxy 3 红确认为**环境性**（.env + gen 产物 + PostgreSQL），零代码改动转绿。**本波生产代码零改动**，全部为测试断言对齐 + 环境恢复。

环境说明（按纪律不入 patch）：`backend/.env` → 主 worktree 绝对符号链接（wt5 同款，`git check-ignore` 确认 `**/.env` 忽略）；`backend/app/gen/`（gitignore 的 proto 产物）从主 worktree 等价复制（主 worktree 与 wt7 同在 `d4338948`，proto 无漂移）；PostgreSQL 用 `make dev-up` 常驻容器 `sparkle_db`。前任账面"仅 ln -s .env"不够——本 worktree 此前从未生成过 `app/gen`，galaxy 收集期即 `ModuleNotFoundError: app.gen`。

## 逐例台账

### R1+R2 review_skip 2 红（断言描述了从未实现的策略——对齐现行"也审查"）

- 测试：`tests/unit/test_review_skip_logic.py::test_should_skip_review_for_final_study_plan_response_without_pending_tools`、`::test_should_skip_review_for_deep_analysis_without_tools`
- 症状：期望 study_plan 终版答复（`tool_calls=[]`）与 deep_analysis 无工具答复**跳过**审查，`_should_skip_review`（`app/agents/graph/nodes/review_nodes.py:333`）无对应分支返回 False。
- 根因判定：**断言过时，非生产缺陷**。`git show 1722e6dc`（clean-slate 初始提交）比对：现行实现与初始版逐行一致，skip 分支在本仓库历史上**从未存在过**——测试是对某套未随 reset 迁入的旧策略的"愿望式"断言。而现行"实质内容一律审查"是两次近期修复的**有意选择**：
  - `5416b1d3`：审查超时 12s→45s（实测 reviewer 延迟 12.6-14s、最差 41.8s，旧超时必然 fail-closed 假 critical），reflection_node 断链修复——审查管线被刻意修好，而非打算绕开；
  - `42956c11`：审查**系统错误**（超时/解析失败）标记 `review_error` 不再向用户流推"内容审查未通过"文案，fail-closed 语义保留。即"也审查"的噪声/延迟代价已被该提交消化——若产品当时想跳过 deep_analysis 审查，那是最佳时机，但该提交反而做了三次 deep_analysis 实弹验证（幻觉 0/3），说明审查是该模式有意保留的质量闸门（deep_analysis 恰是幻觉风险最高档位）。
  - 生产接线旁证：deep_analysis 无工具/无专家时 `_should_disable_tools_for_deep_analysis`（standard_workflow.py:2629）只关工具暴露，仍走 `generation→generation_review` 边（注释明言"所有生成内容都经过审查"）。
- 修法（仅改测试）：两用例翻转断言为 `is False` 并改名 `test_should_not_skip_review_for_*`，行内注释写明依据提交与翻转理由；其余 4 例（standard 简短跳过、工具进度跳过、带工具/专家不跳过）不动，全绿。
- **产品决策备案（本波不硬修，留档评估）**：deep_analysis 长回复真实审查成本 12-67s（R2 复验 `test_reviewer_system_error_no_user_trailer.py` docstring 实证 ~67s 恒超时 fail-closed→reflection 重写再加 12s+）。若产品未来决定"延迟优先"，正确路径是在 `_should_skip_review` 增加 `chat_mode == "deep_analysis"`（及 study_plan 终版）skip 分支 + 离线/异步兜底机制（**当前不存在，需新建**），并回翻这两条断言。本波按"现行语义即最新产品信号"处理。
- 证据：`test_review_skip_logic.py` 6 passed。

### R3 phase62 早停 1 红 + R4/R5 user_id trigger_mode 2 红（fake 停留在 N2 修复前的幽灵签名）

- 测试：`tests/unit/test_reflection_agent_phase62.py::test_reflection_agent_stops_early_on_low_second_round_gain`；`tests/unit/test_reflection_agent_user_id.py::test_reflection_agent_trigger_mode_returns_triggered_result`、`::test_reflection_agent_trigger_mode_falls_back_on_invalid_json`
- 症状：`TypeError: _FakeGenerator.chat() missing 1 required positional argument: 'user_message'`
- 根因判定：**测试 fake 过时**。`5416b1d3` 的 N2 修复把 `_reflect_trigger`（reflection_agent.py:568）与重写路径（:734）统一改为 messages-first 签名 `chat([{"role":...},...], temperature=...)`（与 `app/core/llm_client.py:257` 裸服务真实签名一致），并注明旧 `chat(system_prompt=, user_message=)` "在任何实现上都不存在（必 TypeError）"——即 trigger 模式在修复前生产上根本跑不通。业务逻辑（早停 `low_marginal_gain` 判定、trigger_mode JSON 解析失败 fallback 到 `_fallback_trigger_summary` 的"负荷"摘要 + confidence 下限 0.55）均完好，无需改生产。
- 修法（仅改测试）：两文件 `_FakeGenerator.chat` 改为 `(self, messages, temperature=0.3)`，`calls` 记录 `(messages, temperature)`；索引断言对齐——phase62 的 `"讲解/深度分析审查" in calls[0][0]` 改为 `calls[0][0][0]["content"]`（messages[0] 即 system 条目，deep_analysis 画像 display_name 位于 `workflow_experience.py:108`，经 `build_reflection_system_prompt` 注入），user_id 的 `calls[0][2] == 0.3` 改为 `calls[0][1] == 0.3` 并补 system 角色结构断言。
- 证据：`test_reflection_agent_phase62.py` + `test_reflection_agent_user_id.py` 5 passed。

### R6 galaxy 并发 3 红（环境性，零改动转绿）

- 测试：`tests/unit/test_galaxy_concurrency.py`（revision 乐观锁并发/顺序/过期拒绝 3 例）
- 症状与根因：wave4 已备案为环境性红（彼时无 `.env` 凭据）。本波补齐三件套：`backend/.env` 符号链接、`backend/app/gen/` 产物复制、`sparkle_db` 容器（PostgreSQL 16 直连 `app.db.session.engine`，非 sqlite/mock 可替代）。
- 结果：3 passed（1.85s），C1 乐观锁契约在真实 PostgreSQL 上验证通过，**测试与生产均无需改动**。

## 邻域回归核验（最终树，定向）

- 4 个挂账文件合跑：**14 passed**（review_skip 6 + phase62 1 + user_id 4 + galaxy_concurrency 3）
- review/reflection 邻域 12 文件：**55 passed, 2 failed**——2 失败经 `git stash` 复验为**基线既存红**（与本波改动无关，见下）
- 审查节点消费方：`test_standard_workflow_*` 4 文件 + `test_task_reflection_service.py` **39 passed**

### 邻域既存红备案（wave6 候选，本波不动）

1. `tests/unit/test_reflection_trigger_extension.py::test_reflection_service_exposes_all_six_categories`：生产 `TaskReflectionService.ELIGIBLE_CATEGORIES`（task_reflection_service.py:91）已扩到 **8 类**（原 6 负向类 + `plan_completed`/`milestone_reached` 两个正向触发，PROMPT_TEMPLATES 同套件注册测试已过），测试仍断言恰好 6 类——典型的"功能扩展后集合断言未跟上"，对齐方向明确（改断言或改用超集断言），建议 wave6 顺手清理。
2. `tests/unit/test_reflection_context_injection.py::test_build_reflection_context_respects_token_budget`：期望 `route_history_context_truncated is True`，实得 False——token 预算截断的触发阈值/计算在某次改动后变化，需先定位是阈值调宽（断言过时）还是截断失效（生产缺陷）才能定性，本波未硬修。

## 产物

- 本文档 + `testdebt-wave5.patch`（`git add -A && git diff --cached` 生成，**未 commit**）
- 变更面：3 个测试文件（`test_review_skip_logic.py`、`test_reflection_agent_phase62.py`、`test_reflection_agent_user_id.py`）+ 本文档；生产代码零改动
- 本地环境（不入 patch）：`backend/.env` symlink、`backend/app/gen/` 复制产物
