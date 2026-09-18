# 游客种子空壳内容修复（guest-seed-content-fix）

- 日期：2026-09-19
- worktree：`Sparkle-sysrev/wt8`（基于 main `efb1567a`）
- 关联实测：`docs/competition/2026-tmall-hackathon/多端实测/memory-rag-seedlib-eval.md` C 域——官方种子库 10 条中 4 条 content 为空（空壳卡片，点开无内容），quality_score 却标 8.5–9.0
- 产物：本文件 + 同目录 `guest-seed-content-fix.patch`（未 commit）

## 一、根因（代码 + 主仓 DB 双重查证）

主仓 DB 只读取证（`docker exec sparkle_db psql -U postgres -d sparkle`，进程只读未写）：

```sql
SELECT l.name, i.title, length(coalesce(i.content,'')) AS content_len, ...
FROM seed_items i JOIN seed_libraries l ON l.id=i.library_id;
```

4/10 空 content（content_len=0）的确切条目，全部对应 `backend/app/data/seed_content_initial.py` 中**只定义了 `content_data`、没有 `content` 键**的条目：

| 库 | 条目 | item_type | 实际内容载体 |
|---|---|---|---|
| 数学基础示例库 | 一元二次方程求解示例 | example | content_data.input/output |
| 数学基础示例库 | 几何证明示例 - 三角形内角和 | example | content_data.input/output |
| 数学基础示例库 | 函数图像分析示例 | example | content_data.input/output |
| Python编程练习题库 | Python 列表推导式闪卡 | flashcard | content_data.front/back |

根因链（属"模板数据本身缺字段 + 分支漏兜底"，非 LLM 生成失败）：

1. **数据缺陷**：`seed_content_initial.py` 的 OFFICIAL_LIBRARIES 里上述 4 条只有 `content_data`，`content` 缺省为 NULL。
2. **播种无回填**：`initialize_seed_libraries` 原样 `insert(content=item.content)`，无任何从 `content_data` 推导的兜底。
3. **守卫永久化缺陷**：`initialize_seed_libraries` 有"已存在官方库即跳过"守卫，且启动链只在 `initialize` 内插入——**存量空壳行永远不会被修复**。
4. **增量无防护**：`SeedLibraryService.add_item` 同样允许 content/content_data 双空条目落库。
5. **展示无兜底**：`SeedItemCard` 仅 `if (item.content != null)` 渲染预览；详情 sheet 正文与结构化内容双空时整页只有标题和 chips——空壳卡片点开无内容。

## 二、修法（4 层防护）

### 1. 唯一推导入口 `derive_item_content(item_type, content_data)`（seed_content_initial.py）

按 item_type 把结构化数据渲染为可读正文：example→题目/解答，exercise→题目/解答(solution)，flashcard→front/back，knowledge→定义/公式/说明/要点；类型未命中时通用兜底拼接字符串值。任何非空 `content_data` 都能产出正文，推导不出返回 None。

### 2. 增量不落空壳（空壳不落库）

- `initialize_seed_libraries`：播种前经 `_ensure_item_content` 规范化——content 缺失自动推导回填；**content 与 content_data 双空的条目跳过播种并 warning**。
- `SeedLibraryService.add_item`：content 为空白时推导回填；双空条目 `raise ValueError`（端点既有分支映射为 400），拒绝落库。

### 3. 存量补偿（双保险）

- **启动一次性修复**：新增 `repair_empty_seed_item_content(db)`，挂在 `main.py` 启动引用数据链路（`initialize_seed_libraries` 之后，同一非致命 try 块）。把 `content` 为空且 `content_data` 非空的条目推导回填并更新 `updated_at`；幂等（修复后不再命中条件），服务下次重启即生效，无需手工脚本。
- **惰性补偿（读时自愈）**：`SeedLibraryService.get_item` 命中空壳条目时自动推导、内存回填并 `UPDATE` 落库（best-effort：落库失败仅 warning，不影响本次读取）；`get_items` 列表路径做**仅内存**回填（避免列表写放大），持久化交给启动修复与详情页读时自愈。

### 4. 移动端空态兜底（DS 令牌，零新增 l10n）

- `seed_item_card.dart`：预览条件由 `content != null` 收紧为非空白；无正文时渲染占位文案（既有 `seedLibraryNoContent`="暂无内容"，`DS.textTertiary` + italic）——空壳卡片不再是一片空白。
- `seed_library_detail_screen.dart` `_showItemDetailSheet`：正文与结构化内容双空时展示 `GraphiteCardSurface` 空态占位（`Icons.inbox_outlined` + `DS.textTertiary`）。

## 三、红绿证据

- **Red**：新测试文件就位、源码还原到 HEAD 时 → `ImportError: cannot import name '_ensure_item_content'`（旧代码无推导/修复能力，collection 失败）。
- **Green（后端）**：`SECRET_KEY=… python3.11 -m pytest tests/unit/test_seed_content_content_backfill.py -q` → **22 passed**（0.5s）。覆盖：derive 全类型 + 通用兜底 + 空值；官方 10 条全部可规范化出非空 content（4 条缺陷条目专项回归）；双空条目拒绝播种/落库；启动修复、修复幂等、不可推导不修；get_item 惰性回填 + 落库失败不影响读取；get_items 内存回填无落库写。
- **Green（后端回归）**：`test_seed_library_service.py + test_seed_library_stage22.py + test_workflow_experience_phase62.py` → 53 passed（含新 22）；`tests/integration/test_stage38_event_publishers.py + test_auto_seeding_workflow.py + tests/aurora/test_seed_bridge.py` → 4 passed, 8 skipped。
- **Green（移动端）**：`flutter test test/features/seed_library/` → **5 passed**（新增 3 条 SeedItemCard 空态 widget 用例：空 content/空白串显示"暂无内容"占位、有正文渲染 Markdown 不显示占位）。
- **静态检查**：改动文件 ruff 0 error（main.py 的 2 处 I001 与改动无关，HEAD 即有）；black 对新测试文件格式化通过（app 侧三个文件 HEAD 基线本就 non-compliant，未引入新偏差，新增行均 ≤120 列）；`flutter analyze` 改动目录 68 issues = 基线（本次 0 新增）。
- **治理守卫**：`scripts/run_all_rule_guards.sh` 仅 BG 失败（worktree 缺 Go 生成 pb 文件的环境性缺口，`git stash` 验证 HEAD 同样失败）；K/Z 初次失败系本 worktree 复制生成物时保留符号链接所致，已改为 deref 复制后通过。
- **已知无关失败**：`test_theater_seed_and_accuracy.py` 2 failed，`git stash` 验证为 HEAD 既有失败，与本次改动无关。
- 附注：运行 stage22 测试会顺带刷新 `docs/product/stage22_prompt_coverage_baseline.md` 的 audited_at 时间戳（测试副作用），已 `git checkout --` 还原，不进入 patch。

## 四、变更清单

```
backend/app/data/seed_content_initial.py                 | derive_item_content/_ensure_item_content/repair_empty_seed_item_content + 播种回填与空壳拒收
backend/app/services/seed_library_service.py             | add_item 空壳防护；get_item 读时自愈；get_items 展示回填
backend/app/main.py                                      | 启动链挂载 repair_empty_seed_item_content
backend/tests/unit/test_seed_content_content_backfill.py | 新增 22 用例
mobile/lib/features/seed_library/presentation/widgets/seed_item_card.dart        | 预览空态兜底
mobile/lib/features/seed_library/presentation/screens/seed_library_detail_screen.dart | 详情 sheet 空态兜底
mobile/test/features/seed_library/presentation/widgets/seed_item_card_test.dart  | 新增 3 用例
```

## 五、验证与遗留

- 主仓 DB 全程只读；修复将在修复版引擎下次启动时由 `repair_empty_seed_item_content` 落库（4 条空壳全部命中推导条件），或用户点开条目时由 `get_item` 惰性补齐。
- 遗留（不在本任务范围）：种子库 contentData 在详情 sheet 仍是原始 JSON 展示（后端回填后 content 已可读，体验已闭环）；BG 守卫的 Go 生成物需在 worktree 跑 `make proto-gen`（环境项）。
