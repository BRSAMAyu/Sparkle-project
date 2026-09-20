# V3-FIX-35 + V3-FIX-36 合卡交付报告

> 偏好 supersede 反杀链修复（FIX-35）+ 渲染层偏好值序列化（FIX-36）
> Worker: wt19 Apex · 基线 HEAD `5abd1c4b` · 2026-09-20 · STATUS: READY_FOR_REVIEW

## 0. 结论

| 项 | 状态 |
|---|---|
| M-09 门禁 | **全绿**（`REGISTERED_BUG_CASE_IDS` 清空后 62/62 case，7/7 gate test） |
| R2 resolver A/B 反转 | **通过**（resolver on/off 双臂 pack.preferences 链头恒新值，单测钉死） |
| 渲染面含偏好 value | **通过**（8 个渲染单测：值在场、内部参数/原始 JSON 不在场、emotional 分支同样渲染、条数/长度有界） |
| 变异必红 | **4/4**（链盲 winner / 裸 bump / 删 P09 词条 / 删渲染行 → 各自守卫全红，逐字节还原） |
| M-01..M-08 回归 | **零回退**（M-09 全量 + M-08 provenance 21+ + memory_service/resolver/context_pack/selfcheck/wiring/prefilter 邻接 169+195+33 全绿；51 个 prompts 导入方 2208 测试的失败集与 vanilla HEAD **逐条相同**——38 项全部预先存在，见 §5） |
| 真实 LLM 调用 | 0 次（红线遵守；渲染面用 M-09 模拟层 face 断言 + 单元断言验证，与卡内指示一致） |

## 1. FIX-35：偏好 supersede 反杀链（三环 + 第二失败模式）

### 1.1 根因（R2 定位确认，全部实锤复现）

1. **`memory_service.upsert_preference`（原 L193-195）**：supersede 时把旧行
   `updated_at` bump 到 `utcnow()`——晚于链头 INSERT 时刻（实测 +152µs），
   旧行在任何按 updated_at 排序的消费面里反超链头。
2. **`context_pack.build`（L1367-1370）**：`resolve_preferences` 收到的是未过滤
   全量版本历史（设计如此——链归因是 resolver 职责），但 resolver 不认识链。
3. **`_pick_preference_winner`**：无视 `replaced_by_id`，按
   (evidence_score, updated_at, confidence) 全量排序。两个独立反杀面：
   (a) updated_at bump 反超；(b) 旧行证据引用更多 → evidence_score 反超
   （`test_context_pack_conflicts` 旧断言钉死的 "direct" 胜 "soft" 即此形态）。

**第二失败模式**（R2 更正，修复 FIX-35 后仍剩 2 红）：链头胜出后被 M-05
`selfcheck:irrelevant_to_query` 降档——英文 pref_key 与中文 query 的
跨语言零重叠（`preferred_expansion_depth` vs "给我出几道统计学习的练习题"）。
旧 bug 曾掩蔽它：被取代值从未真正胜出过链解析。

### 1.2 修复

| 环 | 文件 | 改动 |
|---|---|---|
| 环3（结构根因） | `backend/app/services/memory_conflict_resolver.py` | `_pick_preference_winner` 链感知：`replaced_by_id` 非空的行不参与竞争；胜者 = 链头（多链头/无链数据按旧排序轴确定性回退）；有链时 conflicts note reason=`supersede_chain_head`（诚实归因），无链时保持旧 reason 语义 |
| 环1（精确 bump） | `backend/app/services/memory_service.py` | supersede 时刻 `supersede_at` 同时赋给旧行与链头（M-07 失效/审计语义保留——epoch+DEL 契约不动），不变式 `head.updated_at >= 被取代行.updated_at` 由单测钉死 |
| 环2（契约显式化） | `backend/app/core/context_pack.py` | 不改行为：pref_history 保持全量链进 resolver（上游过滤会剥夺链归因、造成 on/off 分支分叉）——以注释固化契约 |
| 第二模式 | `backend/app/services/memory_use_selfcheck.py` | 新冻结词表 `PREFERENCE_KEY_DOMAIN_GLOSSES`（20 键，guard: ⊆ PREFERENCE_KEYS 且与 META_PREF_KEYS 不交）：**值无关**的中文领域词并入 relevance tokens——中文 query 点名偏好领域获得与英文 key 同级的领域相关性。词表 39+（现 56 键 writer 词表）未动；`SELF_CHECK_VERSION` v1→v2（词汇变更纪律）；OP-Bench 重跑绿（`knowledge_gaps` 无词条，op-rel-pref-01 降档保持） |

设计边界：gloss 只表达偏好的**服务领域**，不含任何用户值 → 不可能凭空制造个性化；
无词条键（遥测类/开放词表键）保持旧 relevance 行为（诚实不猜）。

### 1.3 两阶段门禁过程（卡要求记录）

1. **基线**：vanilla HEAD，registry 20 id → 门禁绿（= 签名精确匹配，bug 在场）。
   A/B 探针 7 项红（反杀 + 时间戳倒置 + 链盲 winner 全部复现）。
2. **阶段一**（三环修完，registry 暂清空）：门禁转红**恰好剩 2**——
   `unexpected failures: ['P09-D5-difficulty_chain', 'P10-D3-retention_style_supersede']`
   与 R2 更正逐字一致；其余 18 注册 case 转绿，无新增失败。
3. **阶段二**（M-05 领域词条修完）：62/62 全绿。registry 永久清空（保留历史
   注释），`invalid_use_total > 0`（"bug 在场"时间性断言）反转为 `== 0`，
   门禁 docstring 更新为"此后强制绿"。

## 2. FIX-36：渲染层偏好值序列化

**根因**：生产 `format_user_context` 的【学习偏好】段只渲染深度/好奇心两个
标量；M-01..M-07 保证正确的链头值停留在 `pack.preferences` 结构面，最终
prompt 不可见（M-09 真模型 0/5 的根因）——记忆流「用户可感知闭环」第二道阻断。

**修复**（`backend/app/orchestration/prompts.py`）：
- `_format_memory_preference_lines`：每条记忆链偏好渲染 `- {中文标签}: {用户可读值}`
  （normal 与 emotional_focus 两分支都渲染——情绪主导轮用户纠正同样必须可见）。
- 值提取 `_preference_value_text`：只序列化 `{"value": X}` 契约 / str/int/float/
  bool 字段；嵌套结构与空值跳过；内部参数（分数/置信/版本/id/epoch）与原始
  JSON 结构从构造上不可能出现在输出——隐私口径与 M-08 provenance 对外口径一致。
- 标签 `_PREFERENCE_LABELS`（31 键显示投影，未收录键回退原始 key，诚实不猜）；
  数值型深度/好奇心跳过（已有专属标量行，不重复）。
- 界：单行 120 字符截断、至多 8 行（防画像脏数据撑爆 prompt）；
  `section_weights.preferences == "off"` 时整段不渲染（尊重聚焦加权）。

## 3. 变异必红记录（4/4，全部逐字节还原）

| # | 变异 | 守卫结果 |
|---|---|---|
| 1 | winner 链盲（`heads = records`） | `test_preference_supersede_revive.py` 4 红 |
| 2 | 恢复裸 bump（去掉链头对齐） | `test_head_updated_at_never_older_than_superseded_row` 红 |
| 3 | 删 `preferred_expansion_depth` 词条 | 单测红 + M-09 门禁红且**点名 P09-D5**（双守卫层） |
| 4 | 删渲染行（`lines.extend(...)` → pass） | 渲染单测 6/8 红 |

## 4. 测试资产（新增/更新）

新增：
- `backend/tests/unit/test_preference_supersede_revive.py`（12 测试：A/B 双臂、
  证据反杀、时间戳不变式、winner 纯函数五态、conflicts 归因、三连 supersede 端到端）
- `backend/tests/unit/test_selfcheck_domain_gloss.py`（9 测试：P09/P10 形态、
  knowledge_gaps 仍降档、领域外仍降档、值无关性、phatic 归因、版本钉死）
- `backend/tests/unit/test_user_context_preference_rendering.py`（8 测试）

更新：
- `tests/memory_eval/test_memory_eval_gate.py`：registry 清空（历史注释保留）+ 
  门禁转绿语义 + `invalid_use_total == 0`
- `tests/unit/test_context_pack_conflicts.py`：`"direct"`（被取代值，旧 bug 钉死）
  → `"soft"`（链头）+ `supersede_chain_head` 归因断言
- `tests/unit/test_memory_provenance_api.py`：回执版本字面量 → `SELF_CHECK_VERSION`
  常量（语义：测"当前版本回执"，stale 路径另有 v0 用例钉死）

## 5. 已知边界与遗留（非本卡缺陷，已核实）

1. **`tests/contract/test_decision_context_contract.py::test_builder_populates_decision_context`
   预先存在红**：vanilla HEAD 复现（临时还原全部产品文件后同败）。根因是
   goal 侧同类跨语言相关性（英文 goal 标题 "Goal DC" vs 中文 query），非本卡
   引入；goal 标题是开放词表，无 pref_key 式领域词条可建——fast-model hook
   是其设计救济。该守卫此前因 `app.gen` 缺失在 worktree 不可收集（本卡已用
   `make proto-gen` 在 worktree 内生成 stubs 使其可收集——见下）。
2. **51 个 prompts 导入方 2208 测试中的 38 项失败/错误全部预先存在**：
   与 vanilla HEAD 失败集**逐条 diff 相同**（spine/skill、orchestrator real-engine、
   process-stream integration、2 个需外部服务的 integration ERROR）。本卡零新增。
3. **`app.gen`**：worktree 内由 `PROTO_TOOLCHAIN_IMAGE` 主机工具链生成
   （untracked、gitignored、随 worktree 生命周期回收），使 M-03 prefilter 集成与
   M-05 wiring 守卫首次在 worktree 可收集——全部通过。
4. **M-05 wiring 守卫**（`test_memory_use_selfcheck_wiring.py`）9/9 绿。
5. 真模型复验受 25 次限额已耗（M-09 报告），本卡按卡内指示以模拟层 face 断言
   + 单元断言替代；渲染面改动的真模型增益待下一限额窗口复核。

## 6. 验证命令（可复现）

```bash
cd backend
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest tests/memory_eval/ -q                 # 7 passed
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest \
  tests/unit/test_preference_supersede_revive.py \
  tests/unit/test_selfcheck_domain_gloss.py \
  tests/unit/test_user_context_preference_rendering.py -q                                    # 29 passed
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest \
  tests/unit/test_memory_use_selfcheck*.py tests/unit/test_memory_prefilter_integration.py \
  tests/unit/test_memory_provenance_api.py tests/unit/test_memory_service.py \
  tests/unit/test_memory_invalidation_pipeline.py tests/unit/test_context_pack*.py \
  tests/unit/test_memory_conflict_resolver.py -q                                             # 全绿
```

## 7. 交付物

- `wt19/v3-output/V3-FIX-35-36/REPORT.md`（本文件）
- `wt19/v3-output/V3-FIX-35-36/changes.patch`（含 untracked 新测试；`git add -N` 后 `git diff HEAD`）
