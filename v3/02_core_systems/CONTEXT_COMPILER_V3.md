# Context Compiler V3

## 1. 核心原则
Context 是有限预算。目标不是装最多，而是为**当前决策**提供最小高信号集合。

## 2. 输入
- DecisionIntent
- UserWorldSnapshot
- candidate memories
- candidate knowledge refs
- recent events/outcomes
- available tools
- permissions/budget

## 3. 输出 ContextPack
分段：
1. task/goal truth
2. current constraints
3. relevant confirmed memory
4. relevant experience memory
5. knowledge excerpts + citations
6. recent outcome/evidence
7. uncertainty/conflicts
8. available actions/tools
9. user-request text

每个 item 有 `ref/type/scope/age/relevance/why_included`。

## 4. Budget policy
优先保存决策必要的 state 与明确纠正；再是同 scope experience；再是 knowledge；历史对话只保留必要摘要/最近消息。

禁止：
- 因 token 够就把 100 条 memory 塞入；
- 将 persona prose 当唯一用户真相；
- 在 slim 模式清掉已经检索且决定需要的材料；
- RAG 材料放到模型容易忽略的尾部且无回归测试。

## 5. JIT retrieval
对大型材料只传 references + 高相关 chunk；Agent 可按需读取更多，而非 upfront 全载入。

## 6. Context observability
记录：候选数→硬筛数→rerank数→实际注入数、token、来源类别、被裁剪原因、model tier。

## 7. Cache key
至少包含：user/tenant, decision type, relevant object versions, memory_epoch, knowledge_version, policy_version, model/capability version。
写操作与纠偏请求不得用旧文本 cache 冒充新推理。
