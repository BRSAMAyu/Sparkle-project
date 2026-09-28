# V4-U05 · 已知限制

1. **画布顶页截图 headless 不可得**：星图四态的像素级顶层截图依赖真实相相机就位与入场动画（headless 泵内节点不可见，捕获为空画布）。四态视觉档以 17 个纯函数钉（亮度/环标记/脉冲逐值断言）+ 真实 GalaxyScreen 泵的 painter 集成断言（三通道节点进 painter.nodesById）+ 语义 dump 承载；真机/桌面运行时画面未取证（本机无 iOS/Android 设备面）。

2. **证据截图为 Ahem 方块字形**（F04/U03 同先例）：测试环境无 CJK 字体，PNG 中文案为方块；真实文案由同帧语义 dump 逐行承载（`u05_sheet_*_semantics.txt` 含「练习过 · 未独立检验」「不代表已掌握」「投影版本 v7」原文与坐标）。是否满足卡面「顶层截图+语义」按 F04 先例口径裁决。

3. **gateway gRPC 形状图响应无通道数据**：proto `GalaxyNode`（node_id/label/mastery）不带 `user_status`，该路径节点 fail-closed 渲染为未检验（虚线环、封顶 SHINING 档）。这是诚实降级而非回归；通道字段的 gRPC 透传属契约变更（proto owner 单独合并），本卡红线禁触 proto。

4. **J-08 成果证据行（既有面）的 verified 图标未在本卡改**：`_OutcomeEvidenceRow`（J-08 已 DONE 面）以 `Icons.verified_outlined`+success 色呈现「成果证据 · N 条」。该行的语义是「有 outcome 溯源行」而非「独立检验通过」，视觉上有潜在的强解读空间；因属 V3 已 DONE 任务面（证据不可重置），本卡只登记不动，建议接续卡裁决是否换中性图标。

5. **`mastery_evidence.capability_channel` 为节点级二值 + None**：后端 D04 节点级词表只有 verified/practiced/None；non_human/trace_only 在移动端词表中存在但当前线上数据不会出现（per-outcome 通道不透传到节点级）。移动端按四态封闭词表实现（与 D04 卡面口径一致），若后端未来透传节点级 non_human/trace_only，渲染面已就绪。

6. **D06 关系新鲜度语义未在星图 UI 消费**：D06 的 `graph_index` 水位/fallback 元数据在 GraphRAG 检索面，不在星图图投影面；本卡以 `projection_version`（D04 读门同 version 载体）承载「来源与轨迹的版本一致性」，AGE/关系型水位语义与星图页面的接续属后续卡。

7. **legacy 存量的颜色温度保留**：`_masteryTemperatureColor` 按分数连续映射色温，未检验高分存量仍是「暖色」——这是 D04「亮度保留存量分数=参与足迹」的语义（温度连续、非离散掌握声明）；封顶的是掌握档专属视觉（透明度/光晕/脉冲/双环）。若审查裁决温度也应封顶，改动点在 `_nodeStyle` 一处。

8. **语义播报后缀改动既有文案长度**：`getNodeSemanticLabel` 全部解锁节点播报追加通道词（「，检验状态未知」等）；既有 keynav/semantics 测试用 contains/prefix 断言未破坏（192 测全绿），但读屏总长增加。若需更短播报，可裁剪 unknown 后缀为空——交审查裁决。
