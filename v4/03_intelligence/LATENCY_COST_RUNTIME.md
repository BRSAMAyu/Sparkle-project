# 速度、成本与长期运行

## 基线边界
S05/S06是真gRPC模型调用，不包括Flutter/网关整链，26条/层不足以精确估p95尾部。L2/L3长尾明显；主调用cost漏辅助调用且model标签有错（FIX545）。V4不引用“每次只花$0.00122”作为商业单价。

## 前台预算
本地触控反馈p95≤100ms；确定性状态操作p95≤500ms（网络额外分层）。L0必须零生成调用，已知问候/状态不走分类+生成双调用。L1真实首个有用内容p50≤2s/p95≤5s；L2受限行动提案p50≤4s/p95≤12s，20s为本次交互转交/终止上限而非任意深任务总时限。以上是目标，需按网络、模型、硬件报告，失败就保持未通过。

“有用”必须是请求相关内容/必要澄清/可操作阶段产物。ack、转圈、“正在思考”、随机鸡汤与像素粒子不计。不要把reasoning_content直接给用户当可解释证据；用工具阶段/所用来源/可验证计划摘要。

## 深任务
只在用户请求或同意后进入L3。run卡5s内应可查看真实范围、取消、离开；最终耗时单独记录，初始默认软预算90s/硬预算180s可配置，超过则明确暂停/失败而不是无限等待。每步独立deadline和幂等键；取消发出不代表已撤销外部副作用；UNKNOWN先对账。已完成片段可用但标明未全完成。

## 能力路由
模型配置以真实probe（schema/tool/text/stream/latency/context/价格来源）决定，保留V3可用provider，不为追“最新”换未经验证型号。不把同一模型不同tier冒充独立更强能力。fast失败要保持能力合同，不能悄悄从工具执行降为文字“已完成”。探测不读取或打印Key。

## 完整费用
一条root_request包括classifier、sufficiency、retrieval辅助、generation、review、reflection、tool模型、embedding、语音等attempt。记录requested/actual model、token/用量来源、currency、price_version、unknown parts、retry与取消。无计费数据保留unknown，决不填0；no_generation_model且token>0作为计量错误。

预算先reserve再settle，重放不双计；竞争worker共享原账本原子扣限；离线分析与用户请求分账。成本门先用开发配置限额运行，价格未核验或未授权预算时BLOCKED_BUDGET，不自动消耗所有额度。用“每个完成目标闭环的总成本”而非每token成本评商业性。

## 长期可控
跨App重开，恢复run与同一episode；后台重试不重播触觉/声音，不替用户确认人类步骤。过期权限和记忆版本在每次副作用前再验。关闭pixel主题不影响运行，关闭semantic selector回到V3安全路径，关闭主动不影响被动求助。

## 资源
前台Leader+6后台Agent；同机HEAVY=1，模拟器/大测试/构建共享独占。其他Agent继续轻量代码、评审、脚本分析。磁盘低于安全阈值暂停新build并保留状态，不删未归档证据。测试片级快速反馈，发布整链用既有CI串行分片，不因旧材料曾取消全量而永久忽略当前发布套件。
