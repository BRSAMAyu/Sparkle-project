# V4-G06 · limitations（预登记挑战与残余边界）

## 预登记挑战

1. **[Q08] 弹窗庆祝卡渐变身份端点深浅**：rare 金 -25% / epic 紫 -35% / legendary 珊瑚 +30% 的第二端取值按「双端同侧亮度 + 单一实算墨 ≥4.5:1」下限就地收敛，属发布面美术决策（同 milestone_celebration 固定美术底豁免维度），美术终裁待 Q08；随档语义色（warning/brandSecondary/info）退出庆祝卡填充位是其直接推论（classic-light 下三稀有度无公共墨色的实证已由 E- 控制组钉死，数学上不可两全；V4-G06R1/F-1 勘误：实证数字以真实默认板复算 3.431/4.498/3.600 为准，原引 2.95/4.499/4.02 系误用 non-default 板色，结论不变）。
2. **milestone 庆祝面 6 枚冷相硬编码在 ratchet 基线内**（前任登记，本卡未清零）：替换为随档令牌需先裁美术方向；ratchet 只降不升门已就位。
3. **弹窗 legendary 卡 border=rarityRare（金边珊瑚卡）**：既有视觉沿用未动—— border 语义与稀有度 identity 的关系属行为/美术面，超本卡风格面边界。
4. **golden 文本字形**：flutter_test 环境 CJK 渲染为 tofu（无中文字体），文本可读性由同源语义钉（Semantics 断言）+ 对比度守卫钉补足；真机字形不在 golden 钉范围（与 chat/dashboard 既有 golden 同口径）。
5. **B04 容差跨机漂移**：基线在本机（darwin/arm64）签发；跨机环境漂移实测口径 ~0.18% 落 0.5% 带内（G01 实测），真实回归 ≥0.6% 硬失败。若跨机超带按 EVALUATION_PROTOCOL 独立签理由重签，不以放宽容差换绿。

## 残余边界（如实登记，不冒充覆盖）

- 15 态矩阵中本卡以「默认/庆祝/锁定/接近解锁/减动效」widget 级复现钉死；加载/离线/权限失效等长尾态由既有家族测试承载（159 项含账本失败面/幂等/空态），未逐态新增 golden——分母见 test_results.json。
- `DS.textOnPrimary`、`DS.warningLight`、`deepSpaceStart` 等派生公式在守卫钉中以同口径复算（F05/G02 判例同法），未改为注入式单测——公式漂移由守卫红捕获，属既定测试架构取舍。
- 换取的 U12 兑换语义（不暗示付费）本轮未新增钉：photon 兑换面既有 u12 测试（idempotency/账本失败面）全绿，风格面改动仅前景墨色实算，未触商业语义结构。
- 独立审查（1 份，normal 卡）未在本卡内产生——review_receipt.json 由审查会话按接力机制出具。

## R1 返修登记（review_r1.md 三项 + 小项）

- **F-3（HIGH，合并门）已闭**：contract 屏辉光循环收敛回单一启动点 `_syncGlowMotion()`（`.repeat` 全文件唯一 4→2 ≤ 基线 3，reduce-motion 语义不变）；DL-SPEC 守卫 exit 0，全套守卫失败仅剩 AQ/BG 环境性既有（非本卡）。
- **F-1（MEDIUM）已闭**：E- 控制组改引 `SparkleColors.light()` 默认板真值，重算 3.431/4.498/3.600 判负不变；数字勘误见 diff_or_evidence_only.md B6e 与挑战①内注。
- **F-2（MEDIUM）已闭**：地图状态 chip 实现级 widget 钉落地（`achievement_map_state_chip_nail_test.dart`），M-B mutation 回退红/还原绿双向探针亲跑；守卫头注收窄为配对层/实现层两层口径。
- **N2 勘误**：legendary 深墨双端 7.567/10.12（原 "7.6/8.9" 第二值不精确，方向保守无害）。
- 残余不变：R1 N5（弹窗内残余透明度文字 0.88/0.7 两处）与 Q08 美术终裁仍待后续卡，本返修未扩边。
