# V4-S04 · 独立审查 receipt（一审 R1）

- 审查会话：**wtS04R1**（未参与 S04 实现；只读审查 + 本 receipt 提交，不 push）
- 审查锚：分支 `agent/v4/s04` @ **`7e6302d6`**（基线 `001561c3`）
- 卡：V4-S04（implementation · risk normal · 独立审查 1 位）；权威账本 `mobile/assets/asset_ledger.json`（49 条）
- 日期：2026-09-28
- 合并落差声明：main 已前进至 `1063abb3`（领先 15 提交）；本审查全部复跑在分支锚点 `7e6302d6` 上完成，落差面用 `git diff` + `git merge-tree` 实测（见靶 7）。

## 总裁决：**PASS_WITH_CHALLENGES**

三验收的可失败反例全部亲做复现（红→还原绿），49 条账本哈希/字节独立重算全对，11 条 PROPOSED 物理隔离证据真实（10 条纯布尔 diff + 1 张 git mv R100、仓内零删除），占位逐字节可复现亲证。**1 项 C 级挑战（C1）**：实现方 receipt 自称 pubspec 解析器修复"经夹具反例逐条钉死"，变异实验实测**同缩进 `- ` 列表分支未被任何测试钉死**（修复本身真实可用，但"钉死"声明过满）——合并时补一个小夹具测试即闭环，不阻塞销账。

---

## 靶 1 · 验收① 许可守卫（V4S04-ASSETS）——PASS

- **发布面 allowlist 反例亲做**：`printf` 未知字节 → `mobile/assets/images/game_icon_rip.png` → 守卫 **L003×2（打包未入账 + 栅格未入账）exit=1** → 删除还原 → **exit=0**。与 `counterexamples.txt` 反例1逐字一致。
- **46 存量 internal_original 判定的边界如实性**：抽读账本条目 `provenance_note` 明写 "repo-initial-commit … feature-coherent batch naming; **no external attribution record in repo**"——文件名级证据没有说满；limitations ① 自认"若存在未入档的外部素材来源，账本无法从仓内证据发现，需原始作者确认"。判定措辞与证据强度匹配，**未夸大**。license 分布实测：38×internal_original + 11×unknown，无第三种未申报口径。
- **11 条 PROPOSED 隔离的物理真实性**：
  - 10 条 curated 商业录音：`git diff 001561c3..7e6302d6 -- bgm_catalog.json` 实测 **10 处 `releaseApproved: true→false` 纯布尔翻转，无字段增删**（末尾补 newline 一处，无害）；运行时闸门真实（`bgm_service.dart:2594` `entries.where((e) => e.releaseApproved)`，`:2596` 空集合安全回退空队列——全翻 false 后这些轨道不可达）。
  - 1 张 Gemini 图标：`git show -M --name-status` 实测 **R100 rename** `assets/icons/… → assets/staging/…`（真 git mv，**非删除伪造**）；`grep -rn Gemini mobile/lib/ mobile/test/` = **零引用**；`assets/icons/` 现为空目录。
  - **仓内零删除**：commit 非新增状态仅此一条 R100，无任何 D。权属决策（删除/取证/许可）未越权，只隔离——正确。

## 靶 2 · 验收② DPR 一致（V4S04-DPR）——PASS

- **P002+P005 形态反例亲做**：把 `2.0x/placeholder_pixel_block.png` IHDR 改写为 15×20 → **P002（15x20 != 8x8 × 2.0，NN 整数倍被破坏）+ P005（与生成器输出不一致）exit=1** → `git checkout` 还原 → **exit=0**。
- **NN 策略声明落地**：P003 对 `nearest_neighbor_runtime` 条目逐 consumer 校验源码含 `FilterQuality.none`；代码面真实声明在 `PixelAssetImage`（asset_catalog.dart:159）。
- **占位逐字节可复现性亲证**：重跑 `generate_placeholder_sprites.py --out /tmp/...` → `diff -r` 仓内 `assets/placeholders/` **BYTE-IDENTICAL**；三枚 sha256 与 `placeholders_sha256.txt` 全中（2e898f7b…/96533566…/2cecc7e7…）。生成器纯 zlib/struct，零第三方依赖属实。

## 靶 3 · 验收③ 间接层——PASS

- **业务只持 key**：`SparkleAssetKey`（芽/星光/环境背景）→ `AssetSlot`；`resolve()`/`effectivePath` 对 PROPOSED **无视 approvedAssetPath 强制落占位**（asset_catalog.dart:71-73）；`PixelAssetImage` 是唯一像素渲染入口。
- **Dart 测试三例抽验全绿**（含在 +31 亲跑中）：①全 key PROPOSED 落占位；②错误映射 `assets/sprites/unapproved_seed.png` 被 proposed 状态忽略；③starlight 占位→approved 纯映射翻转（`debugOverrideSlots`），resolve/slotFor/PixelAssetImage 业务面零变化——**catalog 翻转=纯数据变更**成立。
- **L008 反越界**：夹具测试 `test_hardcoded_reference_outside_catalog_and_consumers_blocks_L008` 钉死（materials.dart 夹具红）；实仓 lib/ 下 assets 字面量引用面仅 3 文件（materials.dart/bg m_service.dart/asset_catalog.dart），全部在账本 consumers 白名单内。
- 账本 config 条目抽验：`audio/bgm/bgm_catalog.json` consumers=[bgm_service.dart]，与 `:652` 的 `_catalogAssetBundlePath` 字面量对上，L007 放行口径正确。

## 靶 4 · pubspec 解析器 `- ` 分支"顺手修"——修复真实，测试钉**不完全**（→C1）

- 实仓解析正确：6 目录（images/icons/placeholders/audio/ui/audio/ambient/audio/bgm）+ 字体 0（fonts 段注释态无误报）。
- **变异实验 1**：删去 `or stripped.startswith("- ")`（同缩进列表分支）→ **9 夹具测试仍全绿**（14/14 中其余 5 个不触该分支）——该分支**无回归钉**。而同缩进列表是合法 YAML（Flutter 接受），一旦未来 pubspec 改用该风格，守卫会静默失明（bundled 集合为空 → L003 不再红）。
- **变异实验 2**：让 `- ` 值提取整体失效 → **2 夹具红**（L002/L004 测试失败）——主提取路径**有钉**。
- 结论：修复本身真实可用（同缩进输入亲测解析正确），但实现方 review_receipt.json"守卫静态解析器经夹具反例**逐条钉死**（含一个解析器真 bug 的修复回归）"对同缩进子分支**说满了**。修法很轻：夹具加一个同缩进 pubspec 变体断言（或解析器单测），见 C1。

## 靶 5 · ~155MB 商业录音留仓 + L006 防线——PASS

- 留仓体积实测 `find …curated -name '*.m4a'` 合计 **154,691,453 bytes ≈ 154.7 MB**——"~155MB"声明属实；只隔离未删除（靶 1 零 D 已证）。
- **重跑回写风险真实存在**：`scripts/bgm_curator_config.curated.json` 实测含 **6 处 `"releaseApproved": true`**；`curate_bgm_library.py` 按规则重建 catalog 会回写 true（届时 L002 哈希漂移 + L006 同时红）。limitations ③"守卫拦，而非靠人记；脚本属既有工具归其 owner"口径属实。
- L006 自身经夹具（`test_bgm_catalog_release_approved_pointing_to_proposed_blocks_L006`）+ 反例3 亲做双重验证。

## 靶 6 · 复跑（全部亲跑，分支锚点 `7e6302d6`）

| 套件 | 结果 | 对照声明 |
|---|---|---|
| `python3 -m unittest test_asset_release_guard test_pixel_dpr_policy` | **14/14 OK** | ✅ 一致 |
| `flutter test asset_catalog + bgm_service + bgm_service_p2_10 + unified_settings_bgm` | **+31 全绿**（新 5 + 既有 BGM 面 26，catalog 翻转零回归） | ✅ 一致 |
| `flutter analyze`（asset_catalog.dart + 其测试） | **No issues found** | ✅ 一致 |
| `run_all_rule_guards.sh --rule V4S04-ASSETS / --rule V4S04-DPR` | 两规则各自 **PASS**（manifest :91-92 可被发现与执行） | ✅ 一致 |
| 两守卫实仓直跑 | 双 exit=0（ledger=49 approved=38 proposed=11；pixel entries=5） | ✅ 一致 |
| `generate_asset_ledger.py --verify` | **49 entries verified** exit=0 | ✅ 一致 |
| `artifacts_sha256.txt` | `shasum -c` **10/10 OK** | ✅ 一致 |
| 占位重生成 diff -r | 逐字节一致 | ✅ 一致 |

## 靶 7 · 合并落差预警（main `1063abb3`，+15 提交）

- 触碰面重叠：仅 **`v4/04_tasks/tasks.json`**（main 心跳/销账动其他行，S04 动 V4-S04 行）。产品面（`mobile/assets/**`、pubspec、`scripts/guards/**`、`rule_guard_manifest.tsv`、`asset_catalog.dart`）main 增量**零触碰**。
- **`git merge-tree --write-tree` 实测：干净自动合并，零冲突**（exit=0）。落差风险低；建议合并后照例复跑两守卫 + ledger verify 一次即可。

---

## CHALLENGED 列表

### C1（集成必落，量级：一个测试）：解析器同缩进 `- ` 分支无回归钉

- **事实**：`check_asset_release_surface.py:79-81` 的 `or stripped.startswith("- ")` 使同缩进列表（合法 YAML）可解析；变异删除该子句后 **14 测试仍全绿**——实现方 receipt"逐条钉死"对该分支不成立（主提取路径有钉，变异 2 实证 2 红）。
- **风险**：当前实仓 4 空格缩进不受影响（守卫行为今日正确）；若未来 pubspec 改同缩进风格，L003 面静默失明且无测试报警。
- **修法**：`test_asset_release_guard.py` 夹具补一个同缩进 pubspec 变体（`"  assets:\n  - assets/images/\n"`）断言 L003 仍红；或把解析器抽成纯函数加直接单测。随合并落，或由 S04 owner 紧随 fix commit。

### 非阻塞观察（O）

- **O1** L008 白名单为"账本 consumers + asset_catalog.dart 豁免"——未来条目可自declare consumers 换取硬编码许可，属流程性绕过面；L007 仍要求路径 APPROVED+ship=true 兜底，账本 diff 可审。接受，供 F02 收口时回顾。
- **O2** Dart `kAssetSlots` 的 status 是账本的手工镜像而非 codegen（limitations ⑥ 已自认）：账本把某 sprite 翻 APPROVED 时守卫不校验 Dart 侧 status 同步——status 语义一致性目前只有审查面保障。选镜像避免第二套 codegen 的理由成立，登记知悉。
- **O3** L006 用 `path.endswith(ref)` 后缀匹配账本条目，理论上存在后缀碰撞误配；当前文件名唯一性下无实际影响。
- **O4** 历史口径澄清：`assets/audio/bgm/curated/` 是未声明子目录，**从来不在 pubspec 打包面**（守卫 bundled_files 非递归，与 Flutter 语义一致）；audio 的隔离实质是运行时闸门+账本级，bundle 级隔离仅 Gemini 图标一张。`run_manifest.json`"非递归打包面"措辞准确，但读证据时勿推断"m4a 曾在打包面"。
- **O5** counterexamples.txt 反例3 的 `violations=2` 对应 run_manifest 的 inject 口径（仅 entries[0] 翻回）；本审翻全部 10 条得 violations=11（L002+10×L006），两者内部一致，非证据失真。

## limitations 8 条如实性核验

任务面问"6 条"，实文件 **8 条**（超集，多做不限）。逐条对照：①仓内证据边界（文件名级、需原作者确认）——与账本 provenance_note 措辞一致，**未说满，如实**；②隔离未删除+体积——实测相符；③curate 回写风险+L006 拦截——实测相符（靶 5）；④Gemini 仅 staging 未评审+REFERENCE_ONLY 维持 B04 口径——实测相符；⑤设备级渲染归 F02、test_results.json not_run 披露——**如实**（本审同口径：本卡交付文件层不变量，variant 真机选中是平台既定行为）；⑥镜像非 codegen——如实（O2）；⑦scaffold 默认拒绝的摩擦——设计意图披露，如实；⑧全量基线未在本 worktree 重跑——如实（本审亦未重跑 60+ 全量，仅按其声明的 RULE_FILTER 通道验证两新规则，与声明一致）。

## 结论

- 三验收反例亲证可失败、账本独立重算全对、隔离证据物理真实（R100/布尔 diff/零删除）、占位可复现、复跑全绿且数量声明一致、run_all 通道可发现可执行、零模型调用属实。
- **PASS_WITH_CHALLENGES**：C1（解析器同缩进分支无测试钉 + "逐条钉死"声明过满）不阻塞按「独立审查 + 集成 SHA 可失败测试」销账，但该测试应随集成或紧随 fix commit 落地。
- 本 receipt 锚定 `7e6302d6`；合并后以集成 SHA 复跑靶 6 清单（预期落差为零冲突，见靶 7）。

— wtS04R1，2026-09-28
