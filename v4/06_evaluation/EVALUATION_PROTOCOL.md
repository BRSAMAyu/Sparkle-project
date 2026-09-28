# V4 验证协议：画面、行为、效用分别验

## 五层证据
L0=静态/合约；L1=可控服务模拟；L2=真实模型调用但合成用户；L3=真实App/运行栈/模拟器或桌面交互；L4=物理设备/真实用户。每份报告写明层级。L0全绿不能替L3；L3角色扮演不能替真实学习或商业留存；感官调用正确不能替硬件感觉舒适。

## 原始证据
每个run写代码SHA、栈启动SHA、build、迁移头、config flags、模型requested/actual、root_request/attempt、设备/分辨率/DPR/网络、开始结束、时区、真实/控制钟、测试输入、oracle来源、失败与重试。引用的截图必须是最上层实际window/overlay，不从首个RepaintBoundary盲抓。关键路径UI操作，不通过API建好账号/完成任务后说用户能做到；只读DB探针是证明，不替代交互。

## 四臂效用实验
A=冻结V3当前部署逻辑（仅剔除已知不合法安全输入，不人为削弱）；B=无可选历史；C=V4语义控制+所有**合法**历史；D=V4语义控制+效用筛选历史。相同当前约束、资料、工具、模型和最大预算；token实际差异单报。不能给D更多历史后称算法更好。

先用30开发episode找协议错误，冻结schema/阈值/prompt/model；再独立生成至少30profile×4episode=120 holdout episode，每臂相同生命周期。按profile簇bootstrap置信区间；两次seed检查敏感性。每episode最多4个决策轮，必要时3seed仅在离线轻量回放，避免未经授权放大live成本。默认分批20episode，在额度允许范围按原顺序运行；超预算暂停并保留全部，不能换简单样本。

测试生成者与实现者隔离。测试operator可读隐藏真值，但AUT只能收到真实用户会说的话和已授权历史；用户模拟器不读取AUT策略名字来迎合。LLM judge若使用，匿名打乱臂顺序、冻结rubric、核对引用，以硬规则检查安全/权限/证据；分歧样本保留，不能用同一实现Agent自夸做终审。

结果指标M08–M14联合判定。推荐同时报告原冻结utility：resolved+1/unresolved−1/wrong decision−0.4/question−0.15/control intrusion−0.6，避免通过乱问或无限输出行动刷成功。该utility是协议，不是心理学效用。不能只比较比自己更弱的fixed_policy。

## UI/UX闭环
基线→相同数据/route新风格→独立审查→具体缺陷→修复→同状态重截。严重度：A=无法完成/误导成功/隐私破坏；B=核心操作被遮挡、难定位、关键信息不可读、页面语义冲突；C=非核心装饰/一致性差；D=偏好建议。A/B=0方可发布。不同审查者意见不能平均掩盖A缺陷。

矩阵：Android主设备配置、Web、macOS；各主旅程至少默认/离线/失败/取消/未知/过期/重开。组件层覆盖theme×font×DPR组合，旅程层用风险组合/成对覆盖减少笛卡尔爆炸。profile帧测与golden静态测分开；音/震默认不在自动回归中真的反复播放。

## 回归预算与任务分割
沿现有测试片区运行，风险映射到整链串行分片。大批次只允许1HEAVY；轻量selectors/contract/unit可与其并行。每修复先最小红例→改动→绿→受影响slice→集成SHA复验，禁止为绿而删断言/放宽基线/重新命名fallback。视觉golden变更需独立签理由。

## 不能自动证明的事
“用户觉得温暖”“一眼惊艳”“喜欢像素风”“长期离不开”“商业付费”“音质舒适”“学习真的提高”。本阶段不派人工任务，但也不捏造Agent代理这些证据；报告写NOT_MEASURED_HUMAN/DEVICE_UNVERIFIED。产品可达到工程候选，不能因此宣称PMF。

## 失败处理
只要硬边界失败，隔离相关flag，保留V3其他功能。效果门不通过，保留观察结果并启动本范围最多三轮归因修正；三轮无进展→交付反例和下一实验，不继续无限audit farm。Q任务的implementation可完成，value verdict仍FAIL；终门读取后者。Budget/权限缺失记明确BLOCKED，不是PASS或无声SKIP。
