# User World Model — Sparkle 的状态宇宙

## 四类对象不可混

### 1. Current State
业务真值：Goal / Milestone / Action / Schedule / Artifact / Run / Membership / current constraints。

### 2. Memory
未来可能复用的用户相关信息：
- FACT（明确事实）
- CONFIRMED_PREFERENCE
- OBSERVATION
- HYPOTHESIS
- EXPERIENCE（情境→干预→结果）

### 3. Knowledge
用户上传/外部内容：document, chunk, knowledge node, citation, embedding。

### 4. Events
不可变或追加式历史：message sent, action accepted, task completed, memory corrected, run failed, artifact created 等。

## UserWorldSnapshot
Context Compiler 不查“所有表”，而请求结构化快照：
- identity/tenant
- active goals
- current focus
- constraints
- memories candidates
- material candidates
- recent events
- outcome summary
- capabilities/permissions

每项必须带 `source_ref`、`observed_at`、`valid_at`/TTL（若适用）。

## 五层用户模型与四分法关系
现有五层：raw evidence → projection → inference → shadow → correction。
它是 **Memory/Understanding 的 epistemic layer**，不是替代四类存储对象。

铁律：
- inference/shadow 不能写回 raw fact；
- correction 产生 supersede/revoke，不通过覆盖旧文本抹掉证据链；
- current explicit statement 在当前 decision 优先。
