# WT289-MYPY-BURN1 — D 线 mypy 基线一期烧减报告

- 卡号：wt289-mypy-burn1 ｜ worktree：`Sparkle-sysrev/wt289-mypy-burn1`（分支同名，本地 commit 未 push）
- 日期：2026-09-24 ｜ mypy 钉版 1.20.2（复用主仓 backend/.venv）

## 一、烧减数字（回执①）

| 口径 | 前 | 后 | 烧减 |
|---|---|---|---|
| **backend/ 目录口径**（卡口径：`cd backend && mypy app --ignore-missing-imports --no-error-summary`，读 backend/pyproject.toml，warn_return_any 开） | **7686** | **2458** | **-5227（68.0%）** |
| 根目录口径（CI ratchet 现行：`mypy backend/app`，根目录无 mypy 配置文件） | 7417 | 2189 | -5228 |
| quality/mypy_baseline.txt | 7688 | **2458** | 已刷新（卡口径） |

两口径差异恒为 269 = `no-any-return` 家族整族（来自 backend/pyproject.toml 的 `warn_return_any=true`，根口径无该配置故不计）。CI 门为只降不升，2189 < 2458 → CI 必绿。

## 二、根因与修法（回执②）

### 根因：全库模型是 SQLAlchemy 1.x legacy 无注解 `Column` 声明（SA 2.0.48）
模型一律 `name = Column(String(100), ...)`（106 个模型文件 2482 处 + 散落 7 个服务/核心文件）。mypy 视角下每个 ORM 属性都是 `Column[T]` 而非 Python 值类型，导致：
- 所有 `instance.attr = value` 赋值报 assignment（~1959）
- 所有 `instance.attr` 读出传参报 arg-type（expected UUID 独占 1043，str 436，int/datetime/bool/float 若干）
- `Column(GUID())` 等自定义 TypeDecorator 不可推断 → var-annotated（模型文件 459）
- call-overload/misc/attr-defined 部分连带

### 曾试并否决：SQLAlchemy 官方 mypy 插件（`plugins=sqlalchemy.ext.mypy.plugin`）
插件可用（mypy 1.20.2 + SA 2.0.48 实测），但净收益差：7686→7038（仅 -648）——它把 nullable 列推断为 `Optional[T]`，真实反映 SQL 语义，却在读点新增 ~2000 条 union-attr(+204)/misc(+718)/call-arg(+217)/operator(+245)。错误面质量反而变差，已回滚，未采用。

### 采用：AST 驱动、DDL 严格保持的 `Mapped[T] = mapped_column(...)` 全量迁移
- **规模**：2597 列 / 108 文件（app/models 全部 + app/core/celery_tasks.py、app/aurora/runtime_v1/models.py、app/services/{friend_match,memory_retrieval_prefilter,memory_epistemic_contract,release_approval,group_recommendation}_service.py）
- **注解推断**：String/Text→str、Integer→int、Boolean→bool、Float/Numeric→float、DateTime→datetime、Date→date、`Enum(X)`→X（枚举类型名）、JSON/JSONB/GUID/未知→Any；乐观型（非 Optional）注解与全库既有"值非空"使用假设一致
- **DDL 保持规则**（运行时零变化的关键）：
  - 原 `nullable=` 显式参数原样保留
  - 原无 `nullable` 且非 `primary_key` → 补 `, nullable=True`（等价于 Column 非主键默认值，抵消 mapped_column 从非 Optional 注解推断出的 nullable=False）
  - 主键列不加 nullable
- **同步机械修复**：sqlalchemy.orm 导入补 `Mapped, mapped_column`；datetime/typing/Any 按需补导入；5 处文件存在 mid-file 导入/多行括号导入导致脚本插错位，已手工修复；ruff F401（Column 失效导入 105）+ I001（导入排序 107）共 212 条自动修复
- **无一处 `# type: ignore`**：全部是真实类型化改善，无裸豁免

### DDL 零变化证明（安全网）
`git clone` worktree 出 HEAD-only 基线克隆，两侧各跑 metadata 全量 dump（218 表 × postgres/sqlite 双方言 CreateTable + 每列 nullable/primary_key/unique/index/default/server_default/onupdate/doc/comment + 索引 + 约束清单）：**substantive diff = 0**（仅约束集合迭代顺序与 default 函数对象地址两类噪声）。

### 家族×修法×计数表

| 家族 | 前 | 后 | 烧减 | 修法 |
|---|---|---|---|---|
| arg-type | 3058 | 479 | -2579 | 模型 Mapped 化（属性读出变值类型，UUID 1043 全清） |
| assignment | 1959 | 427 | -1532 | 模型 Mapped 化（instance 赋值合法） |
| var-annotated | 679 | 77 | -602 | 模型 Mapped 化（GUID/Enum 列可推断） |
| call-overload | 236 | 35 | -201 | 模型 Mapped 化连带 |
| misc | 183 | 147 | -36 | 同上（Column list-comp 等） |
| return-value | 173 | 69 | -104 | 同上 |
| index | 98 | 41 | -57 | 同上 |
| attr-defined | 307 | 275 | -32 | 同上 |
| union-attr | 413 | 363 | -50 | 同上 |
| operator | 73 | 63 | -10 | 同上 |
| dict-item/valid-type/type-var 等 | 余量 | 略降 | ~-24 | 同上 |
| **合计** | **7686** | **2458** | **-5227** | |

## 三、验证（回执③）

| 项 | 结果 |
|---|---|
| 定向 pytest 批1（guest_seed×2、galaxy/ 6 文件、achievement×2、error_book、visual_element） | **118 passed**（25s） |
| 定向 pytest 批2（seed_content、seed_library、community×3、x05b execution 投影、accountability、task plan-link） | **66 passed, 1 skipped**（190s，skip 为既有条件跳过） |
| 定向 pytest 批3（memory_service、card_protocol phaseb/phasec、context_cache） | **40 passed**（43s） |
| 全 metadata `create_all`（sqlite，补 pre-existing 缺注册的 theater FK 桩） | OK，219 表全建成功 |
| import 烟雾（`import app.main` + `import app.models`） | OK |
| ruff（CI 同口径 `ruff check backend/app`） | **All checks passed**（迁移后修复 212 条连带告警，未引入新告警） |
| 守卫 | 变更前 `git status --short` 与清单比对一致；全程未 push、未动 main、未 stash/reset/clean（仅一次性 `git checkout -- backend/app` 回滚自己树内已损坏的中间产物，单树单人操作） |

注：tests/_dbguard 确认 sqlite 串天然安全；DATABASE_URL=sqlite+aiosqlite:///:memory:，SECRET_KEY 用测试值，零真实库接触。

## 四、资源峰值（回执④）

- 无 HEAVY 任务（无模拟器/Gradle/浏览器）；内存峰值主要为 mypy 进程（<2G）与两批 pytest（串行）
- 磁盘：开工 10Gi 可用；临时区 /tmp/wt289-mypy-burn1 峰值 908M（大头是 HEAD 基线克隆）+ backend/.mypy_cache 149M —— 收工已清（见下）
- app/gen（920K，proto 生成物）从主仓只读复制入 worktree 供 import/pytest，gitignored，不入交付，随 worktree 生命周期回收

## 五、二期建议（剩余大户排序，回执⑤）

终态 2458（backend 口径）剩余分布：arg-type 479、assignment 427、union-attr 363、attr-defined 275、no-any-return 269、misc 147、return-value 69、call-arg 64、var-annotated 77。**机械性家族已耗尽，剩余全部需逐点判断**：

1. **no-any-return（269，纯机械、建议二期首选）**：`Returning Any from function declared to return X`——多为未注解中间量/`dict.get` 链。修法：精确注解或 `cast`；或与 Leader 决策"是否干脆对齐两口径"（见下）后按剩余口径重估。
2. **assignment 427 中的 mixin 子族（~160）**：`SQLCoreOperations[T] | T` 型——`SoftDeleteMixin` 等 mixin 里的 `self.deleted_at`/服务层泛型 helper 走了描述符类型。修法：mixin 列也 Mapped 化（`deleted_at: Mapped[datetime | None]`）+ 泛型 helper 加 TypeVar bound，可整族消掉。
3. **union-attr（363）**：真实 Optional 处理（`Item "None" of "X | None" has no attribute`），需 None-guard/assert/提前返回，逐点语义判断，量大面广，建议按文件 top（memory_service 87、guest_seed 59、context_pack 52…）分卡推进。
4. **attr-defined（275）**：`.redis`(25)/`.rowcount`(24)/`.get`(29，Any 型 JSON 列访问)/`_registration_lock`(13) 等——多为 `__init__` 未声明属性，补声明即清；JSON 列访问建议在模型上补 Mapped[dict[str, Any]] 精确化后自然消。
5. **arg-type 剩余 479 / call-arg 64 / misc 147**：真类型错或第三方 stub 缺失，逐点修注解，必要时精确码 ignore + 注释。
6. **给 Leader 的口径建议**：CI ratchet 现行根目录口径读不到 backend/pyproject.toml（warn_return_any 失效，恒比卡口径低 ~243 条）。建议把 `scripts/ci/mypy_ratchet.sh` 改为 `cd backend && mypy app ...`，两口径合一后基线含义唯一；本次基线按卡口径写 2459，两口径下 CI 都绿。
7. **mypy 版本**：requirements.txt 是 `mypy>=1.8.0` 未钉版，版本漂移会晃动基线，建议钉 `mypy==1.20.2`。

## 六、重要操作发现：mypy 1.20.2 增量缓存会静默少报

对 110 个文件做批量修改后，**热缓存**下 mypy 只报 1417 条（静默少报 ~1040 条）；冷缓存（`rm -rf .mypy_cache`）后稳定 2458，且热缓存二次运行亦稳定 2458。结论：**批量改动后刷新基线必须冷缓存跑一次**，否则基线被写低、CI 在新变更时可能误触发。CI 恒为冷环境不受影响。

## 交付物

- worktree：108 文件改动（+3025/-2794）+ quality/mypy_baseline.txt（7688→2458）+ 本报告
- `v3-output/WT289-MYPY-BURN1/changes.patch`：全量 diff（git diff 输出，含 baseline 变更）
- 本地 commit（未 push）：feat(types) …
