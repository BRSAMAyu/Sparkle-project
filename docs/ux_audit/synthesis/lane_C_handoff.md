# Lane C Handoff

实际改动：`ContextOrchestrator` 现在把胶囊收藏偏好注入 `CognitiveContext`；`build_system_prompt` 会渲染带时间感的跨会话记忆段，并增加胶囊内容偏好段；胶囊收藏事件会刷新上下文缓存、写入推断画像，并通过 `BehaviorSignalCollector` 生成认知碎片。

用户可见效果：Aurora 下次开场能自然衔接“上周/昨天/刚才”的历史学习内容；收藏深度型或特定科目胶囊后，回答会更偏完整推理链和对应主题例子。

验证：新增 prompt、context manager、capsule favorite service、behavior signal collector、profile event consumer 单元测试。

遗留：未改 Lane B 的写入开关默认值；胶囊反馈事件仍沿用现有反馈服务写碎片路径。
