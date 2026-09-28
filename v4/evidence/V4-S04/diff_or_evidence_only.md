# V4-S04 — diff_or_evidence_only

## 结论一句话

零外部素材下载，为 mobile 资产面建立"账本（49 条，六要素）→ 发布面守卫（L001–L008）→ DPR/NN 策略守卫（P001–P005）→ asset key 间接层（PROPOSED 自动落程序生成占位）"四件套；11 项权利未知资产（10 条商业古典录音 + 1 张 Gemini AI 图标）全部登记 PROPOSED 并逐项隔离出发布面；三条验收各带可失败反例实证（红→恢复→绿）。

## 设计一句话

账本 JSON 是唯一权威，守卫独立重算哈希并静态解析发布面（pubspec 声明目录+字体声明+已打包 config 引用+Dart 字面量），业务侧一切像素/角色资源经 `AssetCatalog` 的 asset key 间接层解析，未批准资源在运行时只能落到程序生成、逐字节可复现的最小像素方块占位。

## 差量明细（相对 base 001561c3 = main HEAD）

新增：

- `mobile/assets/asset_ledger.json` — 权威账本：49 条 = 46 存量（28 ui 音效 / 5 环境音 / 10 curated 商业录音 / 1 Gemini 图标 / 1 噪点纹理 / 1 bgm_catalog 配置）+ 3 程序生成占位。每条含六要素：author / source / rights(license_id+commercial_use+redistribution+modification+attribution) / version / sha256 / fallback，另附 status、ship_in_product、dpr_policy、provenance_note。
- `mobile/assets/placeholders/` — 程序生成占位（8×8 最小像素方块）+ 2.0x/3.0x NN 整数倍变体（16×16 / 24×24），生成器重跑逐字节一致（`placeholders_sha256.txt`）。
- `mobile/lib/core/assets/asset_catalog.dart` — asset key 间接层：`SparkleAssetKey`（芽/星光/环境背景，导航种子集）→ `AssetSlot`（status+approvedAssetPath+placeholderPath）；`resolve()` 对 PROPOSED 永远返回占位；`PixelAssetImage` 统一 `FilterQuality.none`（NN 采样的代码面声明）。
- `mobile/test/core/assets/asset_catalog_test.dart` — 5 测试：PROPOSED→占位、错误 approved 路径被忽略、替换角色=只改映射业务零感知、变体文件存在、IHDR 整数倍不变量。
- `scripts/guards/check_asset_release_surface.py`（Rule V4S04-ASSETS）— L001 六要素不全 / L002 哈希漂移 / L003 打包未入账 / L004 未批准上发布面 / L005 未知字体 / L006 目录引用未批准 / L007 Dart 引用未入账 / L008 越过间接层硬编码。
- `scripts/guards/check_pixel_dpr_policy.py`（Rule V4S04-DPR）— P001 策略缺失/非法 / P002 NN 整数倍导出被破坏 / P003 NN 声明未落地代码 / P005 占位与生成器输出逐字节不一致。
- `scripts/devtools/generate_asset_ledger.py` — 账本 scaffold（缺失文件默认 PROPOSED/unknown→守卫红，强制人工补全）/ --rebuild / --verify（重算哈希+覆盖检查）。
- `scripts/devtools/generate_placeholder_sprites.py` — 纯 zlib/struct PNG 生成器（零第三方依赖），NN 整数倍 DPR 变体导出，确定性输出。
- `scripts/tests/test_asset_release_guard.py`（9 用例）+ `scripts/tests/test_pixel_dpr_policy.py`（5 用例）— 守卫反例在夹具仓逐条钉死。
- `v4/evidence/V4-S04/` — 本证据目录。

修改：

- `mobile/pubspec.yaml` — assets 增加 `assets/placeholders/`；注释声明发布面规则与守卫入口。
- `mobile/assets/audio/bgm/bgm_catalog.json` — 10 条 curated 商业录音 `releaseApproved` true→false（数据级，走既有 `entry.releaseApproved` 代码闸门，`_buildCatalogQueue` 对空集合安全回退空队列）；schema/字段未动。
- `mobile/assets/icons/Gemini_Generated_Image_*.png` → `mobile/assets/staging/`（git mv）— 移出 pubspec 声明目录，脱离打包面；无任何 Dart 引用（已 grep 证实）。
- `scripts/rule_guard_manifest.tsv` — 追加 V4S04-ASSETS / V4S04-DPR 两行。
- `v4/04_tasks/tasks.json` — V4-S04 → in_progress / REVIEW_READY / PENDING_REVIEW（唯一非 evidence 产品面外变更）。

## 三验收对照（可失败证据见 counterexamples.txt）

1. **没有未知许可字体/商业 BGM/游戏图标混入产物**
   - 存量盘点：字体 0（pubspec fonts 段整体注释态）；商业 BGM 10 条（文件名级证据：Rubinstein/Ugorski/Mozart 等商业古典录音）→ 全部 PROPOSED + catalog 翻 false + 移出递归打包路径；疑似游戏/AI 图标 1 张（Gemini 生成文件名）→ staging 隔离。
   - 守卫反例：向 `assets/images/` 塞未知文件 → `L003 ×2, exit=1`；catalog 翻回 true → `L002+L006, exit=1`；恢复后 exit=0。
2. **原生多 DPR 导出或 nearest-neighbor 处理一致**
   - 账本每像素资产带 `dpr_policy`（native_multi_dpr / nearest_neighbor_runtime / full_resolution / not_applicable_audio|data）；占位资源带 2.0x/3.0x NN 整数倍变体；NN 的代码面声明在 `PixelAssetImage`（FilterQuality.none），守卫 P003 逐 consumer 校验、P002 校验 IHDR 整数倍、P005 校验占位=生成器逐字节输出。
   - 反例：2x 变体改写为 15×20 → `P002+P005, exit=1`；恢复后 exit=0。
3. **替换芽/星光角色不改业务协议；未批准资源走占位**
   - 业务只持 `SparkleAssetKey`；替换=改 `kAssetSlots` 映射（Dart 测试第三例：starlight 从占位切到 approved 路径，resolve/slotFor/PixelAssetImage 业务面零变化）；PROPOSED 状态下错误映射 approvedAssetPath 也被 `effectivePath` 强制回落占位（测试第二例）。
   - 守卫面：L008 拦一切绕过间接层的硬编码（账本 consumers 白名单 + asset_catalog.dart 豁免）。

## 发现（非本卡制造，本卡如实登记）

1. **bgm_catalog.json 曾以 `releaseApproved:true` 引用无许可文件的 10 条商业录音**：本 SHA 前该闸门形同虚设（文件名级商业录音无任何许可文档）。本卡翻转 + 守卫 L006 固化；`scripts/curate_bgm_library.py` 若按旧 AlbumRule 重跑可能回写 true，届时守卫立即红（该脚本未在本卡修改，属既有工具）。
2. **`Gemini_Generated_Image_*.png` 直接位于打包声明目录 `assets/icons/`**（B04 resource_inventory 已在盘面上），且无 Dart 引用——纯粹的死重资产。已移 staging 待权利评审，非删除。
3. **worktree 环境债（非回归）**：新 worktree 缺 gitignored 实体目录 `backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen`，导致既有守卫 AQ/BG 假红；按卡指示复制实体目录（永不提交）后 AQ/BG 均 exit=0。已在 run_manifest 环境节记录。

## 差量举证边界

- 未动 bgm_service.dart / materials.dart 等既有消费者代码（materials.dart 的 noise 引用作为账本 consumers 白名单既成事实登记，留待 F02 在航像素组件统一收口）；未新建第二套截图/视觉工具权威；V3 路径与证据未触碰。
- 本卡未生产任何"真实新素材"（原创 sprite/icon 归后续卡），全部占位为程序生成——这是卡面明示的交付边界，不是素材缺口隐瞒。
