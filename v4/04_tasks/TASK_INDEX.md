# V4 任务总表

58张增量卡；不包含V3已完成卡的重布。B01—B06可先并行，HEAVY单槽。详细标准见对应卡与依赖规格。

|ID|任务|依赖|类型|锁/资源|
|---|---|---|---|---|
|[V4-B01](cards/V4-B01.md)|继承当前HEAD与最新修复，不重开V3|—|verification|v4-baseline|
|[V4-B02](cards/V4-B02.md)|43模块及在用路由映射增量|—|verification|v4-portfolio|
|[V4-B03](cards/V4-B03.md)|冻结负结果与配对评测基线|—|verification|v4-eval-fixtures|
|[V4-B04](cards/V4-B04.md)|原生视觉与资源基线，不把参考图当V3截图|—|verification|v4-visual-harness / HEAVY|
|[V4-B05](cards/V4-B05.md)|冻结呈现与上下文回执最小合同|—|design|v4-contract-design|
|[V4-B06](cards/V4-B06.md)|真实模型能力、调用预算与全链测量基线|—|verification|v4-model-probe|
|[V4-F01](cards/V4-F01.md)|像素候选主题并入唯一令牌体系|V4-B04|implementation|design-tokens|
|[V4-F02](cards/V4-F02.md)|原生像素组件与完整状态故事页|V4-F01, V4-B05|implementation|design-components|
|[V4-F03](cards/V4-F03.md)|真实状态驱动的反馈呈现适配器|V4-F02, V4-B05|implementation|experience-presenter|
|[V4-F04](cards/V4-F04.md)|五Tab Shell与响应式布局升级|V4-F02, V4-B02|implementation|mobile-shell|
|[V4-F05](cards/V4-F05.md)|可替换设计Preview与主题切换|V4-F03, V4-F04|implementation|style-preview / HEAVY|
|[V4-F06](cards/V4-F06.md)|无障碍与文本缩放基础能力|V4-F02, V4-F04|implementation|a11y|
|[V4-I01](cards/V4-I01.md)|目标Episode接续读模型|V4-B01, V4-B05|implementation|episode-view|
|[V4-I02](cards/V4-I02.md)|合法历史的效用筛选与反向迁移抑制|V4-B01, V4-B03|implementation|context-memory|
|[V4-I03](cards/V4-I03.md)|复杂表达的受限语义选择器|V4-I02, V4-B06|implementation|aurora-selector|
|[V4-I04](cards/V4-I04.md)|无动作仍可纠正与一次决策性澄清|V4-I03|implementation|stuck-policy|
|[V4-I05](cards/V4-I05.md)|经验策略影子验证与有界启用|V4-I02, V4-I04, V4-D02|implementation|policy-patches|
|[V4-I06](cards/V4-I06.md)|Context使用回执与来源验证|V4-I02, V4-B05|implementation|context-receipt|
|[V4-I07](cards/V4-I07.md)|学习/交付目标的人机权限与脚手架|V4-I03, V4-B05|implementation|hybrid-policy|
|[V4-I08](cards/V4-I08.md)|深任务返回控制与恢复一致性|V4-B06, V4-I01|implementation|agent-runtime|
|[V4-I09](cards/V4-I09.md)|真正零模型的确定性快路与快慢分层|V4-B06|implementation|ai-fast-lane|
|[V4-I10](cards/V4-I10.md)|根请求全调用计量与label真实性|V4-B06|implementation|cost-ledger|
|[V4-D01](cards/V4-D01.md)|交付到真实呈现的曝光语义增量|V4-B01, V4-B05|implementation|lifecycle-exposure|
|[V4-D02](cards/V4-D02.md)|结果窗口、关联键与缺失语义|V4-D01|implementation|lifecycle-attribution|
|[V4-D03](cards/V4-D03.md)|撤回派生影响与投影重算|V4-D02|implementation|evidence-retraction|
|[V4-D04](cards/V4-D04.md)|星图证据与参与足迹分离|V4-D03, V4-B02|implementation|galaxy-evidence|
|[V4-D05](cards/V4-D05.md)|可读且不夸大的洞察与经验回访|V4-D02, V4-I05|implementation|insights-view|
|[V4-D06](cards/V4-D06.md)|GraphRAG时效与关系型fallback|V4-D04|implementation|graph-retrieval|
|[V4-U01](cards/V4-U01.md)|首页接续与有价值的第一主动作|V4-F04, V4-I01|implementation|ui-home|
|[V4-U02](cards/V4-U02.md)|卡住→纠正→差异确认垂直交互|V4-F03, V4-I04, V4-I06|implementation|ui-recovery|
|[V4-U03](cards/V4-U03.md)|我的理解：项目范围与校准控制|V4-F02, V4-I06|implementation|ui-memory|
|[V4-U04](cards/V4-U04.md)|Hybrid入口接线与运行工作台|V4-F03, V4-I07, V4-I08|implementation|ui-hybrid|
|[V4-U05](cards/V4-U05.md)|星图轨迹与证据详情视觉|V4-F02, V4-D04|implementation|ui-galaxy|
|[V4-U06](cards/V4-U06.md)|首程落点、账号升级与确认反馈|V4-F04, V4-U01|implementation|ui-onboarding / HEAVY|
|[V4-U07](cards/V4-U07.md)|长对话、代码、RAG与快慢反馈|V4-F02, V4-I09, V4-I06|implementation|ui-chat|
|[V4-U08](cards/V4-U08.md)|任务计划日历统一行动语义|V4-F04, V4-F03|implementation|ui-plan-task|
|[V4-U09](cards/V4-U09.md)|专注：低刺激与真实成果收口|V4-F03, V4-U08|implementation|ui-focus|
|[V4-U10](cards/V4-U10.md)|资料→错题→练习→检验连续体验|V4-F02, V4-I07|implementation|ui-learning|
|[V4-U11](cards/V4-U11.md)|小队、火堆与分享边界风格|V4-F04, V4-D01|implementation|ui-community|
|[V4-U12](cards/V4-U12.md)|自我锚与光子：保留最新商业决定|V4-F02, V4-U11|implementation|ui-rewards|
|[V4-U13](cards/V4-U13.md)|洞察报告：让分析可理解|V4-F02, V4-D05|implementation|ui-insights|
|[V4-U14](cards/V4-U14.md)|设置、通知与所有异常表面|V4-F04, V4-F06|implementation|ui-settings|
|[V4-U15](cards/V4-U15.md)|长尾家族清点与风格一致性闭合|V4-F02, V4-B02|implementation|ui-longtail|
|[V4-S01](cards/V4-S01.md)|动效节奏与降低动态等价实现|V4-F03|implementation|motion-policy|
|[V4-S02](cards/V4-S02.md)|音频焦点、合法音轨与静音fallback|V4-F03, V4-U14, V4-S04|implementation|audio-policy|
|[V4-S03](cards/V4-S03.md)|平台语义触觉与去重|V4-F03, V4-U14|implementation|haptic-policy|
|[V4-S04](cards/V4-S04.md)|原创像素资产与许可账本|V4-B04|implementation|asset-pipeline|
|[V4-P01](cards/V4-P01.md)|主动建议与接续同策略同打扰预算|V4-I01, V4-D02, V4-I04|implementation|proactive-policy|
|[V4-P02](cards/V4-P02.md)|记忆污染、授权与媒体边界红队|V4-I05, V4-D03, V4-U11|verification|privacy-review|
|[V4-P03](cards/V4-P03.md)|运行韧性与V3外部依赖衔接|V4-I08, V4-I10|implementation|ops-bridge / HEAVY|
|[V4-Q01](cards/V4-Q01.md)|核心像素×AI垂直旅程真端验收|V4-U01, V4-U02, V4-U03, V4-U04, V4-D02, V4-F05|verification|qa-vertical / HEAVY|
|[V4-Q02](cards/V4-Q02.md)|记忆效用四臂与新holdout|V4-I05, V4-I06, V4-D03|verification|qa-memory|
|[V4-Q03](cards/V4-Q03.md)|人机分工与学习迁移护栏验收|V4-U10, V4-U04, V4-I07|verification|qa-learning|
|[V4-Q04](cards/V4-Q04.md)|端到端有用延迟与完整成本重测|V4-I09, V4-I10, V4-I08, V4-U07|verification|qa-latency / HEAVY|
|[V4-Q05](cards/V4-Q05.md)|三端页面家族视觉与无障碍审查|V4-U05, V4-U06, V4-U07, V4-U08, V4-U09, V4-U10, V4-U11, V4-U12, V4-U13, V4-U14, V4-U15, V4-F06, V4-S04|verification|qa-visual / HEAVY|
|[V4-Q06](cards/V4-Q06.md)|全感官关闭/重放/真机能力矩阵|V4-S01, V4-S02, V4-S03|verification|qa-sensory / HEAVY|
|[V4-Q07](cards/V4-Q07.md)|长期接续、离线与多账号组合回归|V4-Q01, V4-P01, V4-P02, V4-P03, V4-U05, V4-U06, V4-U09, V4-U11|verification|qa-soak / HEAVY|
|[V4-Q08](cards/V4-Q08.md)|V4发布裁决与可修改设计快照|V4-Q02, V4-Q03, V4-Q04, V4-Q05, V4-Q06, V4-Q07, V4-D06, V4-S04|verification|qa-release|
