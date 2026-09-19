# Knowledge / RAG V3

## 1. RAG 的工作不是“证明我们有向量库”
它必须在 Goal Context 中解决：理解材料、引用依据、从用户资料生成 action/practice、让 Galaxy/Knowledge 形成真实关系。

## 2. Pipeline
Ingest → parse → chunk → metadata → embedding → index → retrieve → rerank → cite → outcome feedback。

## 3. Metadata
每个 chunk 至少有 user/tenant、document、version、page/section、created_at、language、content type、permission。

## 4. Citation UX
回答使用用户材料时显示自然引用，可展开来源；“参考了你的 OS.pdf 第 12 页”比后台 `retrieval=true` 更有信任价值。

## 5. Query Strategy
先由 DecisionIntent 决定是否需要 retrieval；不对 every chat 做 RAG。
支持 lexical + vector + metadata hybrid；评估中文、代码、标题、长文、扫描内容。

## 6. Retrieval evaluation
- source recall/precision；
- citation faithfulness；
- wrong-user=0；
- outdated version 不使用；
- 用户删除文档后 chunk 不可召回；
- model 是否实际使用检索材料，而不仅 prompt 里存在。

V2.5 8/9 Memory/RAG 验收是基线；V3 继续解决“材料已注入但模型间歇不引用”的真实效果，而不是重建 RAG。
