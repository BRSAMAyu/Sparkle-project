# 跨模块数据闭环与真实成长

## FIX507已修，不再重做
S07说明干预生产写入已接到mark_delivered/accepted/dismissed/acted、spine下发和6h outcome关联任务。V4继承这些方法与测试。增量是**交付与实际呈现的区分、同域关联、用户可读来源、丢失与撤回一致性**，不是另造一条生命周期队列。

## 事件定义
- dispatched/delivered：服务器确实下发或接收成功，不等于用户看到。
- rendered：对应卡在活跃表面可见。默认≥50%面积且持续≥500ms作为工程测量条件，屏幕阅读器路径以等价焦点阅读事件登记；此为项目假设，不是心理学注意力证明。
- accepted/rejected/edited/started：按真实操作记录；既有枚举没有edited时走显式契约扩展，不填假accepted。
- outcome_observed：既有OutcomeEntry引用、类型与时间；不能由客户端“感觉完成”直接伪造。
- censored：观察窗结束但无可解释结果；包括未返场/退出/失去授权。与failed分开。

每个事件至少携带user、decision_id、goal/task/run可选真实外键、causation_id、dedupe_key、source_version、occurred_at/received_at。不能把task_occurrence_id当Task.id；缺关联就unattributed。received_at用于延迟与watermark，不能覆盖真实事件时间。

## 事务与可靠性
业务写入原有UoW+outbox不变；呈现/分析hook不拖垮主链，但要有持久可重放投递记录和计数告警，不能只logger后永久丢失。暴露“未关联结果占比、投影滞后、死信、epoch不一致”，每次发布样本追踪`UI→decision→receipt→event→outcome→insight`。

## 星图权威
资料显示当前主星图是关系型knowledge_nodes/node_relations/user_node_status/study_records；AGE是另一路GraphRAG且写生产者存在空缺。V4前台优先关系型当前真源。AGE只能作可检查版本/覆盖率的派生检索索引，落后时回到关系查询/普通检索；不因为想做“世界模型”新建第二套掌握度。

能力证据与活动轨迹分离。旧时间累计亮度可作为“参与足迹”，标签不能叫精通；独立测验/修正过的练习证据才能支撑相应能力描述。遗忘估计标模型估计，不把没登录等于能力下降。成就光子与sprint排行只读其原账本，不把AI打分影响奖励和付费身份。

## 撤回与重算
outcome撤回→依赖索引查受影响节点/insight/experience→标pending_recompute→从仍有效事件按确定顺序重新投影→新version发布。Kalman/Bayesian更新非简单可逆，不能直接减去“撤回分”。重算过程中UI显示旧视图已失效/更新中，不展示双份相矛盾成长。用户删除材料亦使相关引用不可用，但不自动删除其他合法来源的事实。

## 对照指标
关联完整率按具备合法同域键的eligible事件计算，同时公开unattributed占全部比例；不能剔除难配对事件制造100%。feedback repeated去重；exposure分母不混服务端派发。D07洞察的出现不是效果门：必须验证文字中的数值/比较/来源，不能出现“2次成功=提升100%”。
