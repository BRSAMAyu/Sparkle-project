# ERR-IDEM · 错题 re-analyze 重复扣分幂等化 — 收工报告

- Worker：V3 舰队 Worker（ERR-IDEM 卡）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt129`（基线 aeebc371，含 CP-03）
- 日期：2026-09-22
- 交付物：`backend/app/services/error_book_mastery_sync_service.py`（修改）+ `backend/tests/unit/test_error_mastery_idempotency.py`（新增）+ 本报告 + `changes.patch`
- 未 commit / 未 push（纪律遵守）

---

## 0. 幂等方案裁决：**B 吸收侧**（ErrorBookMasterySyncService 内），键 = `mastery_audit_log.request_id` 天然键 + 诊断内容指纹

**裁决理由（A vs B）：**

| 维度 | A 分析侧（analyze_and_link 内跳过） | **B 吸收侧（选中）** |
|---|---|---|
| 覆盖面 | 只拦 analyze_and_link 一个入口 | 拦 `apply_error_diagnosis` / `apply_review_feedback` 的**所有**调用方 |
| 复盘路径幂等 | 还要另做一套 | 同一扇门天然覆盖（record_type 进键） |
| 状态存哪 | 需给 ErrorRecord 加指纹存储——无空列，`latest_analysis` 会被 `ErrorAnalysisResult.model_validate().model_dump()` 规范化剥掉自定义键，不可靠 | **零新状态**：`mastery_audit_log.request_id` 本就是每次成功同步必留的 append-only 审计行，且同步服务已经把确定性 request_id 写进去（`{record_type}:{error_id}:{node_id}`），天然键现成 |
| 迁移 | 可能要加列 | **零迁移**（符合"能免则免"） |
| 侵入面 | analyze_and_link 是 470 行大方法 | 同步服务内一处门 + 键构造纯函数 |

卡片 B 选项提示"查 outcome/outbox 模型有没有天然键可用"——有：不是 outcome 侧，而是 mastery_audit_log.request_id（GalaxyService.update_node_mastery 每次成功更新必写一行带 request_id 的审计，galaxy_service.py:3377-3394）。

**键设计（紧凑编码，满足 request_id VARCHAR(100)，edi≤78 / erv≤89 字符）：**
- 诊断：`edi:<error_hex32>:<fp8>:<node_hex32>`
- 复盘：`erv:<error_hex32>:<fp8>:<performance>:<node_hex32>`
- 内容指纹 `fp8` = sha256(归一化的 question_text / question_image_url / user_answer / correct_answer)[:8]，仅折叠空白、不折叠大小写
- **刻意不含 error_type**：LLM/兜底对同一内容可能给出不同错因分类，分类抖动不得绕过幂等门

**语义（全部有测试锁定）：**
1. 同一错题、内容未变的重复分析 → 只扣一次；第二条 error_diagnosis 不写 StudyRecord、不发 node_mastery_updated、不触发计划压力评估；
2. 同一错题同一表现的重复复盘（双击/重试）→ 只升一次；**不同表现是不同逻辑证据，各自生效一次**（remembered 后 fuzzy 仍生效——CP-03 review 回升回路不被堵死）；
3. 内容变了（改题/改答案/换图）→ 指纹变化 → 新代际：诊断作为新证据再扣、复盘额度重置（card A 选项语义"内容变了才重发"被吸收在键里）；
4. "旧诊断负反馈先回收"：**不存在可复用的回收机制**（全库检索无 error_diagnosis 反冲/回收逻辑），故内容变化后新证据直接叠加、旧扣分不回收——诚实申报，未造新机制；
5. 部分去重：重分析后新加入关联的节点按新键生效，旧节点不重复扣；
6. 幂等门不可读（表未建/查询异常）→ **fail-open 放行** + 告警：宁可放行一次重复，不可让门故障把掌握度同步整体静默吞掉（与 outcome_absorber "audit 写失败不阻断吸收"同款降级方向）。

**关键落点修正（对卡片背景的一处实证修正）**：error_diagnosis 负反馈**并不**经过 `outcome_absorption_service.py`——该模块只消费任务完成/run receipt 的 `outcome.recorded`（NEGATIVE 在那里明确不降级，docstring 裁决"降级语义归错题路径所有"）。真实扣分链是 `analyze_and_link`（error_book_service.py:417-430）→ `ErrorBookMasterySyncService.apply_error_diagnosis` → `_update_node_mastery` → `GalaxyService.update_node_mastery`（UserNodeStatus）+ StudyRecord。卡片所述"同错题扣两次"现象属实，落点在 mastery sync，故 B 选项的"吸收侧"落地为同步服务内部。

---

## 1. 基线红证（修复前，基线代码上运行 `tests/unit/test_error_mastery_idempotency.py`）

```
tests/unit/test_error_mastery_idempotency.py::test_reanalysis_of_same_error_deducts_only_once FAILED
    assert second == [], "同一错题内容未变的重复分析不得再次扣分"
E   assert [{'_pending_e...ry': 34, ...}] == []
    Left contains one more item: {... 'delta': -8, 'new_mastery': 34 ...}
    （loguru 两条：applied diagnosis for error <同一id> ... affected 1 nodes ×2）

tests/unit/test_error_mastery_idempotency.py::test_repeated_review_same_performance_recovers_only_once FAILED
    assert second == [], "同一错题同一表现的重复复盘不得再次回升"
E   assert [{'...ry': 50, ...}] == []   # 42 → 46 → 50，remembered +4 生效两次
```

同错题二次分析：50 → 42 → **34**（扣两次）；同表现二次复盘：42 → 46 → **50**（升两次）。红证输出全文已存 `/tmp/erridem_red_output.txt`（收工自清，不留在共享目录）。

## 2. 红绿证据（修复后）

```
tests/unit/test_error_mastery_idempotency.py  8 passed
  - test_reanalysis_of_same_error_deducts_only_once          （二次分析只扣一次：50→42 停住，StudyRecord 仅 1 条）
  - test_repeated_review_same_performance_recovers_only_once （同表现复盘只升一次：42→46 停住）
  - test_review_with_different_performance_still_applies     （remembered 后 fuzzy 仍各自生效：42→46→47）
  - test_content_change_reopens_diagnosis                    （改答案→新指纹→再扣：42→(dup 42)→34）
  - test_content_change_reopens_review_recovery              （改题→新代际→可再升：46→(dup 46)→50）
  - test_newly_linked_node_still_receives_diagnosis          （部分去重：A 跳过 B 生效 -5，rank 权重正交）
  - test_gate_unreadable_fails_open                          （门 SELECT 故障 → fail-open，同步照常）
  - test_idempotency_request_keys_fit_column_width           （纯函数：确定性 + ≤100 列宽）
```

## 3. 回归矩阵（红线：CP-03 与吸收链不受损）

| 套件 | 结果 |
|---|---|
| `tests -k "error or absorption or outcome" --ignore=tests/northstar_eval`（改前基线） | 705 passed, 11 failed, 11 errors（22 个失败全部预存） |
| 同命令（改后） | **713 passed, 11 failed, 11 errors —— 失败集逐条 diff 与基线完全一致，0 新增**（+8 = 本卡新测试） |
| 基线 22 个预存失败清单 | orchestration 状态机/LLM 路由域（wt126 在途面）、translation API、north_star_journey、outcome_promotion_governor、intervention tracker——全部远离本卡触碰面，系 aeebc371 环境预存 |
| error 域定向 6 文件（unit/integration/services） | 92 passed（含 CP-03 linker、submit_review 500 修复、错误回路） |
| `tests/unit/test_evidence_resolve.py` + `tests/services/galaxy/test_outcome_absorption.py` | 17 passed（吸收链/evidence 账本不受影响） |
| ruff（改动服务文件） | All checks passed（测试文件已 autofix；注：本树 tests/ 基线本就不 ruff-clean，既有 integration 文件 10 处，非本卡门） |
| 硬编码字符串守卫 | ✅ 未发现 |
| 黑盒核对：CP-03 行为 | linker 调用点（analyze_and_link 内）零改动；`_attach_knowledge_links`/`suggested_concepts`/`linking_hint` 零改动 |

环境预存处置：worktree 缺 `app/gen/`（卡片预告过）→ 从主仓只读拷贝生成产物进 worktree（proto/ 与主仓逐字节一致，diff 仅 .DS_Store），collection 恢复。

## 4. 红线面（触碰文件逐个说明）

1. **`backend/app/services/error_book_mastery_sync_service.py`**（唯一生产代码改动，+151/-5）：
   - 新增模块级纯函数（指纹/键构造）+ 常量，不改既有常量表（ERROR_TYPE_IMPACT 等原样，有 spec 测试锁定）；
   - `apply_error_diagnosis` / `apply_review_feedback`：仅新增 error_id 提升与指纹/键计算，传 `request_key` 给 `_update_node_mastery`——delta 计算、rank 权重、钳制、计划压力评估、_pending_event 机制全部原样；
   - `_update_node_mastery`：新增门（写前查 audit）+ request_id 取值优先用键、无键回落旧格式（`{record_type}:{error_id}:{node_id}`）——审计行格式对无键调用方逐字节不变；
   - **为何不破坏吸收链**：`GalaxyService.update_node_mastery` / outcome_absorber / mastery_audit_log 其他写入方（galaxy API、outcome 证据行）零改动；本卡只是新增**读取** audit 的幂等门，键段 `edi:`/`erv:` 为新命名空间，与 `oc=`/`tk=`（outcome 证据）及 galaxy API 自由 request_id 互不冲突；
   - **为何不破坏 CP-03**：deterministic/concept-hint linking 全在 analyze_and_link/linker，未触碰；review 回升路径仅去重同表现重复提交，`forgotten→-2` 压力信号与不同表现证据保留。
2. **`backend/tests/unit/test_error_mastery_idempotency.py`**（新增测试，零生产影响）。

## 5. 冲突面（对在途卡声明）

- wt125（plans API）：**零交集**——未动 plans/task API；
- wt126（orchestration/LLM 路由）：**零交集**——未动 orchestration/（基线预存失败集中在该域，与本卡无关且未被本卡改变）；
- wt128（memory/今日投影）：**零交集**——未动 memory 投影（episodic memory 写入的既有去重保留原样）；
- wt123（mobile chat UI）：**零交集**——未动 mobile/。
- 唯一改动文件 `error_book_mastery_sync_service.py` 的可能共友：`analyze_and_link`（error_book_service.py，本卡**未改**该文件）。综上：**与其他四卡零文件交集**。

## 6. 诚实申报

1. **并发窗口残留**：幂等门读与审计行写不在同一原子操作，两次**并发**（毫秒级同时）触发的同错题分析可能双双过门后各写一行——串行重复（用户反复点分析、前端重试，即卡片场景）已完全去重；收口需 mastery_audit_log 加 request_id 唯一索引（涉及其他写入方行为面 + 迁移，超出本卡"最小侵入/能免则免"边界，未做）。
2. **内容变化不回收旧扣分**：无既有回收机制可复用，新内容证据直接叠加（语义见 §0.4）。
3. **图片错题指纹含 image_url**：OCR 文本微扰不致指纹漂移（question_text 仅空时一次性回填），但用户替换图片＝内容变化（合理语义）。
4. **无键调用不设门**：error_id 缺失的合成调用保持旧行为（ fail-open，不猜身份）。
5. **修改 analyze_and_link 的调用方语义无变化**：dup 情形 `mastery_results==[]` → `error.mastery_delta/affected_node_id` 保留上次值、事件不重发——调用方对该空列表早有分支（`if mastery_results:`），行为已核实。
6. worktree 的 `app/gen/` 为本卡从主仓拷贝的环境修复（生成产物，非手写），不进 patch。

## 7. 收工核查

- [x] `/tmp` 自清：`erridem_baseline_failures.txt`、`erridem_after_failures.txt`、`erridem_red_output.txt`（见下方执行记录）
- [x] 无进程残留（全程单进程 pytest，无模拟器/浏览器/常驻服务）
- [x] `git status --short` 与交付清单一致：`M backend/app/services/error_book_mastery_sync_service.py` + `?? backend/tests/unit/test_error_mastery_idempotency.py` + `?? v3-output/ERR-IDEM/`（报告+patch）
- [x] 未 commit、未 push；index 已还原（`git reset -q`）
- [x] 主仓与演示 DB 只读（仅只读拷贝 app/gen 产物进本 worktree）
