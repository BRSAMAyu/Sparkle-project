# V4-S04 — limitations

1. **权利判定是"文件名级证据 + 仓内无外部署名"的如实登记，不是法律结论**。audio/ui、audio/ambient、noise_texture.png、bgm_catalog.json 按"仓内 initial-commit 程序产出、特性命名成批、无外部来源记录"登记 internal_original；若存在未入档的外部素材来源（如开发者本地下载后提交），账本无法从仓内证据发现——这需要原始作者确认，已列 HUMAN_INBOX 候选。
2. **10 条 curated 商业录音只做了隔离（PROPOSED + catalog 翻 false + 非递归打包面），未删除**。删除/取证/取得许可是权属决策，超出工程卡授权。文件仍占 ~155MB 仓内体积。
3. **curate_bgm_library.py 未修改**：若以旧 AlbumRule 重跑目录治理，可能把 releaseApproved 回写 true——届时守卫 L006 立即红（这是设计行为：守卫拦，而非靠人记）。该脚本属既有工具，改动应归其 owner。
4. **Gemini 图标仅移出打包面（staging/），未做权利评审**；`v4/02_design/REFERENCE_ONLY.jpg` 维持 B04 登记口径（REFERENCE_ONLY / ship_in_product=false），未纳入本账本（不在 mobile/assets 下，本守卫管辖发布面）。
5. **DPR 验证是文件层不变量 + 代码面 NN 声明，非设备渲染截图**。2.0x/3.0x variant 在真机上被 Flutter 选中的行为属平台既定机制；设备级像素视觉验证归 F02 像素组件联调（已在 test_results.json not_run 披露）。
6. **账本与 Dart 侧 AssetCatalog 是"权威 + 经守卫校验的镜像"**，非 codegen 单源。账本改动需同步 kAssetSlots（守卫 L007/L008 会拦不一致的路径引用，但 status 语义一致性靠审查确认）。选镜像而非生成代码是为避免引入第二套构建期 codegen 步骤（l10n 之外的生成面扩张需单独决策）。
7. **scaffold 的默认拒绝策略**：新入 assets 文件默认 PROPOSED/unknown → 守卫红。这意味着任何后续卡加素材必须先补全六要素——是有意摩擦，但要求后续执行者了解 generate_asset_ledger.py 的用法（README 级指引未单独建，脚本 docstring 即文档）。
8. **全量守卫基线未在本 worktree 重跑**（60+ 规则，非本卡面）；新规则经 run_all_rule_guards.sh 的 LIST_ONLY + RULE_FILTER 通道验证可被发现与执行。
