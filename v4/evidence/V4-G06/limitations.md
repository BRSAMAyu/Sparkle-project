# V4-G06 · limitations（预登记挑战与残余边界）

## 预登记挑战

1. **[Q08] 弹窗庆祝卡渐变身份端点深浅**：rare 金 -25% / epic 紫 -35% / legendary 珊瑚 +30% 的第二端取值按「双端同侧亮度 + 单一实算墨 ≥4.5:1」下限就地收敛，属发布面美术决策（同 milestone_celebration 固定美术底豁免维度），美术终裁待 Q08；随档语义色（warning/brandSecondary/info）退出庆祝卡填充位是其直接推论（classic-light 下三稀有度无公共墨色的实证已由 E- 控制组钉死，数学上不可两全）。
2. **milestone 庆祝面 6 枚冷相硬编码在 ratchet 基线内**（前任登记，本卡未清零）：替换为随档令牌需先裁美术方向；ratchet 只降不升门已就位。
3. **弹窗 legendary 卡 border=rarityRare（金边珊瑚卡）**：既有视觉沿用未动—— border 语义与稀有度 identity 的关系属行为/美术面，超本卡风格面边界。
4. **golden 文本字形**：flutter_test 环境 CJK 渲染为 tofu（无中文字体），文本可读性由同源语义钉（Semantics 断言）+ 对比度守卫钉补足；真机字形不在 golden 钉范围（与 chat/dashboard 既有 golden 同口径）。
5. **B04 容差跨机漂移**：基线在本机（darwin/arm64）签发；跨机环境漂移实测口径 ~0.18% 落 0.5% 带内（G01 实测），真实回归 ≥0.6% 硬失败。若跨机超带按 EVALUATION_PROTOCOL 独立签理由重签，不以放宽容差换绿。

## 残余边界（如实登记，不冒充覆盖）

- 15 态矩阵中本卡以「默认/庆祝/锁定/接近解锁/减动效」widget 级复现钉死；加载/离线/权限失效等长尾态由既有家族测试承载（159 项含账本失败面/幂等/空态），未逐态新增 golden——分母见 test_results.json。
- `DS.textOnPrimary`、`DS.warningLight`、`deepSpaceStart` 等派生公式在守卫钉中以同口径复算（F05/G02 判例同法），未改为注入式单测——公式漂移由守卫红捕获，属既定测试架构取舍。
- 换取的 U12 兑换语义（不暗示付费）本轮未新增钉：photon 兑换面既有 u12 测试（idempotency/账本失败面）全绿，风格面改动仅前景墨色实算，未触商业语义结构。
- 独立审查（1 份，normal 卡）未在本卡内产生——review_receipt.json 由审查会话按接力机制出具。
