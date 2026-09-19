# Project Input Interpretation Notes

## 资料权威顺序
1. `PROJECT_SNAPSHOT_V3_20260919.md` 的 V2.5 深夜更新视为最新规划快照；
2. `V2_ENGINEERING_CONTEXT_20260917.md` 用于历史架构与旧任务理解；
3. 二者出现模型栈冲突时，以 V2.5：qwen3.8-flash / MiniMax M3 batch 为当前假设，但 B-05 必须 runtime probe；
4. “已修复/已通过”是项目方提供的历史事实，V3 不自动视作当前回归 PASS。

## 我们从输入中抽出的根问题
- 工程已经很强，但用户价值仍碎片化；
- Memory/RAG/画像单点复活，但 conflict/provenance/utility 未闭环；
- Aurora 后端丰富、用户几乎感知不到；
- UI 设计 token 地基修过，但 L2-L5 未完成；
- 42 feature 增加心智负担；
- 数据 mock 会破坏商业可信；
- 第一眼 seed persona 很强，但必须与真实用户数据伦理隔离；
- provider TTFT 曾是体验杀手，新模型必须重新测；
- 社群/Insights/Task completion 等仍需要真实用户旅程终验。
