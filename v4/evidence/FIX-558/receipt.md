# FIX-558 修复回执 — Flutter Web 全模式构建解封（int64 字面量 codegen 源头 JS-safe 化）

日期：2026-09-28 ｜ 分支：`agent/v4/fix558`（worktree `wtF558`，基于 main@67b3c558）｜ 台账：V3-FIX-558（P1，V4-F 线前置）

## 1. 根因（先读 v4/evidence/V4-B04/build_logs/ 三份失败日志）

- 失败点：`mobile/lib/core/offline/models/cached_list_snapshot.g.dart` 第 19/49/62 行三处 int 字面量：
  `-3993110354800439673`（collection schema id）、`-5780496603892815176`（index `i_cls_key_2529` id）、
  `1681328346514525477`（index `i_cls_ver_2530` id）。
- dart2js CFE：`The integer literal ... can't be represented exactly in JavaScript`（|v| > 2^53 超出 JS double 精度域）。
- 来源定性：**不是源 schema 的默认值/常量**。这三个值是 Isar 生成器对集合名/索引名做 64-bit XXH3 哈希
  （`isar_generator` `object_info.dart`：collection id = `xxh3(utf8(isarName))`，index id 同法）后直接以 int 字面量
  写进模板输出。全仓 7 个 isar 生成文件共 41 个 id 字面量，仅这 3 个超 2^53（最大其余值 8993238488764258 < 9007199254740992）。
- 生成器定位：`isar_generator 3.1.0+1`（pub.dev hosted，修复前非 vendored；`build.yaml` `auto_apply: dependents`）。

## 2. 修法选择（择优理由）

**选定：vendor `isar_generator` fork + 生成器模板条件补丁**（任务选项三中"改生成器模板"路线）。

- 为什么不用"源 schema 加注解/改常量为 String"：id 非源码常量，是生成器对**名字**的哈希；源头在生成器模板，
  任何源侧注解都够不着；改集合/索引名以"碰运气"避开哈希域既污染 DB schema 名又不可维护。
- 为什么不用"改单个源值"：无源值可改（同上）；且仅修单个文件，下一个 isar 集合命中超域哈希时 web 构建再度失败。
- 为什么不用"build_runner post_process 钩子全局文本重写"：需在 mobile 引入 `build` 依赖 + build.yaml + 工具程序，
  机械面更大、每次构建都全局改写、review 可信度低；且仓库已有成熟的 `third_party_plugins` vendored fork 接入先例
  （`dependency_overrides` path，8 个在册），生成器补丁落在真实 emission 点，`dart run build_runner build` 用法零变化。
- **代价与回退**：新增 vendored fork 需随上游升级重新套补丁（已写进 fork README 升级注意）；
  回退 = 删 `dependency_overrides` 的 `isar_generator` 条目 + 删 fork 目录（pubspec.lock 回 hosted 解析）。

### 补丁内容（唯一改动文件 `third_party_plugins/isar_generator/lib/src/code_gen/collection_schema_generator.dart`）

1. 新增 `_maxJsSafeInt = 9007199254740992`（2^53）与 `_schemaIdLiteral(id)`：|id| > 2^53 时输出
   `int.parse(r'<十进制串>')` 替代 int 字面量；域内 id 输出不变（⇒ 其余 6 个 isar 生成文件**零漂移**）。
2. collection/index/link 三处 id emission 全部走 `_schemaIdLiteral`（link id 同为 xxh3 哈希，防未来同类雷）。
3. 存在超域 id 时顶层 schema 声明 `const` → `final`（`int.parse` 非常量表达式；`CollectionSchema` ctor 为 const
   工厂但允许非 const 调用）。已核验全仓无任何 const 上下文引用 `*Schema` 常量（仅 `local_database.dart:185`
   以普通值列入 schemas 列表）。
4. VM 侧 `int.parse` 精确还原 64-bit 值（native 行为不变）；web 侧确定性就近取整——Isar schema id 只需
   平台内自洽（core 以 f64 收发并存盘），不跨平台比对，故精度损失无害。

## 3. codegen 与构建验证（串行执行）

| 步骤 | 命令 | exit | 备注 |
|---|---|---|---|
| 依赖解析 | `flutter pub get`（wtF558/mobile） | 0 | pubspec.lock：isar_generator hosted → path，其余解析不变 |
| 重新 codegen | `dart run build_runner build --delete-conflicting-outputs` | 0 | 349 outputs / 11408 actions，1m10s |
| proto 生成 | `make proto-gen`（worktree 无 gitignored `lib/gen/`，经标准工具链补齐；docker 镜像缺失自动回退 host buf/protoc） | 0 | 生成物不入库（.gitignore） |
| 构建① | `flutter build web --release` | **0** | log: `build_logs/flutter_build_web_release_PASS.log.txt`（首次尝试 exit 1 系 worktree 缺 gen/ 产物，非本修回归，补 proto 后即过） |
| 构建② | `flutter build web --profile` | **0** | log: `build_logs/flutter_build_web_profile_PASS.log.txt` |
| 构建③ | `flutter build web --debug` | **0** | log: `build_logs/flutter_build_web_debug_PASS.log.txt` |
| 冒烟 | `flutter run -d web-server`（127.0.0.1:8138） | served | `lib/main.dart is being served at http://127.0.0.1:8138`；**诚实记录**：首次冒烟撞上并行会话的 flutter test 资源竞争，`The Dart compiler exited unexpectedly`，清场重试即 served（与编译器接受性无关，debug 构建已独立证明 CFE 通过） |

三份构建日志中 `can't be represented exactly` 计数：**0**（修复前 release 日志为 3）。

## 4. 产物 diff 摘要

- `mobile/lib/core/offline/models/cached_list_snapshot.g.dart`（唯一改动的生成物，纯 codegen 产出，无手改）：
  `const` → `final`（1 处）；3 处 id 字面量 → `int.parse(r'…')`；其余 1083 行逐字节不变。
- 其余 6 个 isar 生成文件（cached_statistics_model / local_database / focus_session_record / vocab_word /
  offline_chat_message / translation_record 的 .g.dart）：**零漂移**（id 均在 JS-safe 域，模板条件不触发）。
- 同轮 codegen 冲出的**与本卡无关的陈旧漂移**（riverpod hash 5 处、json_serializable 字段序 2 处、l10n 空行规范
  3 处——系源文件先期改动未重新生成/flutter 工具链自带重生成所致）已 `git checkout --` 还原，不入本卡
  （如上，l10n 在后续构建中会再现，属工具链行为，非本修产物）。
- 接线：`mobile/pubspec.yaml` dependency_overrides 增 `isar_generator: path: third_party_plugins/isar_generator`
  （dev_dependencies 版本行不动，override 生效）；`pubspec.lock` 仅 isar_generator 一条 source 变化；
  `mobile/third_party_plugins/README.md` fork 表 7→8 登记（含补丁与升级注意）；fork README 记上游版本与补丁 diff 点。

## 5. 消费方回归（cached_list_snapshot 消费面）

`flutter test`（wtF558/mobile），exit 0：

- `test/core/offline/list_read_cache_test.dart`（N34 读缓存主体）
- `test/features/task/data/repositories/task_offline_wiring_test.dart`
- `test/features/community/data/repositories/community_feed_cache_test.dart`
- `test/features/error_book/data/repositories/error_book_cache_test.dart`
- `test/core/offline/models/`（vocab_word 等 isar 邻接模型）

合计 **26 passed / 0 failed**。

## 6. 红线自查

- 生成物只经 codegen 产出：cached_list_snapshot.g.dart 由补丁后生成器重新生成，无手改 ✅
- 未碰 .env / proto/ 契约 / 迁移 ✅（proto-gen 仅补齐 worktree 缺失的 gitignored 生成物，与 main 检出内容同源）
- 未 push（本地银行领先 origin，遵守）✅
