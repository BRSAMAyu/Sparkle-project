# 游客种子空壳修复（aa8f2a3c）端到端验收

- 验收日期：2026-09-18（API 实测时刻，引擎进程启动于 2026-09-19 06:28:24）
- 验收环境：主仓运行环境（sparkle_db Docker + Go 网关 :8080 + Python 引擎，引擎已运行修复后代码）
- 修复提交：`aa8f2a3c` fix(seed): derive content for template-empty seed items + self-heal stock
- 验收方式：只读 DB 查询 + 真实游客注册 API 走查 + 移动端读码；不改代码、不落 commit

## 结论：PASS（6/6 项通过，无残留空壳）

## PASS/FAIL 矩阵

| # | 验收项 | 判定 | 关键证据 |
|---|--------|------|----------|
| 1 | DB：4 条历史空壳（数学示例×3 + Python 闪卡）content 已回填 | PASS | 4 条 `example`/`flashcard` 全部 `has_content=t`，内容为 `derive_item_content` 推导格式（`# 题目/# 解答`、闪卡问答），`updated_at` 统一为 2026-09-18 20:09:32（启动修复批量执行痕迹） |
| 2 | DB：官方库全量无空壳 | PASS | `seed_items` 10 条中 `content` 空值 0 条、`content_data` 空值 0 条；3 个官方库（Python 4 / 回复模板 3 / 数学示例 3）empty 均为 0 |
| 3 | 启动修复链执行 | PASS | `/tmp/engine_api.log:512`：2026-09-19 06:28:29.761 `Global achievements, galaxy skins, galaxy baseline, official seed libraries, and shop items ensured`。本次启动幂等命中 repaired=0（该函数仅在 repaired>0 时打 `Repaired N seed items...` 日志，与代码一致）；实际回填发生于 09-18 20:09:32 的上一次启动 |
| 4 | API：新游客种子库列表 10/10 content 非空 | PASS | `POST /api/v1/auth/guest` 取 token → `GET /api/v1/seed-libraries`（3 官方库）→ 逐库 `GET /api/v1/seed-libraries/{id}/items`：TOTAL=10 EMPTY=0，闪卡 content_len=257，数学示例 content_len=280/273/403（含推导标题格式） |
| 5 | 移动端卡片空态：有内容不显示占位 | PASS | `seed_item_card.dart:105-137`：`content` trim 非空 → 渲染 `SparkleMarkdown` 预览；仅 content 空时显示 `seedLibraryNoContent` 占位。widget 测试 `seed_item_card_test.dart` 三用例（空/null/空白字符串显示占位、有正文不显示占位）覆盖 |
| 6 | 移动端详情空态：仅双空出现 | PASS | `seed_library_detail_screen.dart`（aa8f2a3c 新增）：占位条件为 `content` 空且 `contentData` 空（双空才出现），单项为空仍有结构化内容可渲染 |

## 证据明细

### 1. DB 只读验证（docker exec sparkle_db psql -U postgres -d sparkle）

总量与空壳统计（`seed_items`，`deleted_at IS NULL`）：

```
 total | empty_content | no_content_data
     10 |             0 |               0
```

历史 4 条空壳（item_type IN ('example','flashcard')）回填后抽查：

```
 item_type |            title            | has_content | content_preview                                     | updated_at
-----------+-----------------------------+-------------+-----------------------------------------------------+----------------------------
 flashcard | Python 列表推导式闪卡       | t           | **问题：** 如何用列表推导式将 [1, 2, 3, 4, 5] 中... | 2026-09-18 20:09:32.277875
 example   | 一元二次方程求解示例        | t           | # 题目 | 求解方程：x² - 5x + 6 = 0 | # 解答 ...      | 2026-09-18 20:09:32.277861
 example   | 几何证明示例 - 三角形内角和 | t           | # 题目 | 证明：任意三角形的内角和等于180° ...        | 2026-09-18 20:09:32.277867
 example   | 函数图像分析示例            | t           | # 题目 | 分析函数 f(x) = x² - 4x + 3 ...             | 2026-09-18 20:09:32.27787
```

`# 题目/# 解答` 与闪卡问答格式与 `derive_item_content`（`backend/app/data/seed_content_initial.py:429`）的 EXAMPLE/FLASHCARD 分支输出一致，证明内容来自推导回填而非人工写入。4 条 `updated_at` 完全同刻 → 单次启动修复批量落库。

### 2. API 实测（网关 :8080）

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8080/api/v1/auth/guest -d '{}' | jq -r .access_token)
curl -s http://127.0.0.1:8080/api/v1/seed-libraries -H "Authorization: Bearer $TOKEN"
curl -s "http://127.0.0.1:8080/api/v1/seed-libraries/{id}/items?page=1&page_size=50" -H "Authorization: Bearer $TOKEN"
```

新游客可见官方库 3 个：Python编程练习题库(4)、常见问题回复模板(3)、数学基础示例库(3)。
逐条断言结果：`TOTAL=10 EMPTY=0 -> PASS`。样例：

- exercise「列表操作基础练习」content_len=91：`# 列表操作基础练习\n\n**题目：** 给定一个数字列表 [3, 1, 4, 1...`
- flashcard「Python 列表推导式闪卡」content_len=257：`**问题：** 如何用列表推导式将 [1, 2, 3, 4, 5] 中每个数字平方？...`
- example「一元二次方程求解示例」content_len=280：`# 题目\n求解方程：x² - 5x + 6 = 0\n\n# 解答...`

### 3. 修复链代码走查（六环节全部在位）

| 环节 | 位置 |
|------|------|
| 推导入口 `derive_item_content` | `backend/app/data/seed_content_initial.py:429`（example/exercise/flashcard/knowledge 分类型推导 + 通用字符串兜底） |
| 播种回填 + 双空拒绝 | `seed_content_initial.py:498,595`（`_ensure_item_content`；双空打 warning 跳过播种） |
| add_item 空壳防护 | `backend/app/services/seed_library_service.py:960-968`（双空抛 `ValueError("Seed item requires content or content_data (empty shell rejected)")`） |
| 启动修复 | `backend/app/main.py:464` → `repair_empty_seed_item_content`（`seed_content_initial.py:517`，幂等，repaired>0 才打日志） |
| 读时自愈 | 列表内存兜底 `seed_library_service.py:1096-1100`（不落库）；`get_item` → `_heal_empty_content`（`:1121-1140`，落库持久化，best-effort） |
| 移动端空态 | `mobile/lib/features/seed_library/presentation/widgets/seed_item_card.dart:102-137`；`seed_library_detail_screen.dart`（双空占位）；测试 `mobile/test/features/seed_library/presentation/widgets/seed_item_card_test.dart` |

## 备注（非阻断观察）

1. 当前 `/tmp/engine_api.log` 仅含 06:28 这次启动，无 `Repaired N seed items` 行——属预期（本次启动 repaired=0，代码仅在 repaired>0 时打日志；真正的修复发生在 09-18 20:09:32 的上一次启动，以 `seed_items.updated_at` 为证）。若需复核可查上次启动日志。
2. 引擎当前进程为修复后代码：日志启动时刻（09-19 06:28）晚于修复提交合入（09-19 04:06），且 API 返回内容即推导产物，链路闭环。
3. 无残留空壳，无需定位断链环节（任务第 3 步不触发）。
