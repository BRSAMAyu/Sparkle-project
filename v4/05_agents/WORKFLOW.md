# 六后台Agent持续工作规约

## 权威
规格：收编后仓库内V4 tasks.json。运行状态：沿现有fleet单一真源，不同时维护ZIP、TASK_INDEX和手写表三份事实。原V3 ID只引用，原开放义务继续原号。新发现用V4子编号，先查重复，避免历史FIX撞号。

## 角色流动
Leader负责依赖、全局裁决、合并与证据；六后台槽通常为四实现+一review+一测试，也可三实现+两review+一测试。模型名称不等于质量：使用当前可用GLM/Codex/Gemini，但独立审查必须不同会话、未参与实现、看原验收而不是只听作者解释。Leader不能用同一作者自评替代独立review。

## 任务租约与路径
每次claim写node_id/session_id/base_sha/actual_paths/resource/lease_generation；同路径写互斥，读允许。失效租约接管后老Agent不能继续提交权威状态；其代码可作为未验证patch再审。单机不需要新外部协调服务，已有仓库的fleet状态工具足够。跨机启用必须共享同一个状态权威，不各自拿相同卡；当前远端被冻结就不绕禁令推送，用允许的bundle/局域同步并校验SHA。

## 资源
HEAVY=1/宿主（Flutter构建、原生模拟器、全量/大分片测试、内存密集profile共用）。API测量同样有独立预算与provider限流。轻量分析/单元测试可并行，但不能借“小测试”名义启动另一份数据库或Docker堆栈。低磁盘保护沿仓库值，未知则先检测不删除日志；保留近期failed原件与哈希清单，归档后才按已授权策略清理。

## 每张卡四个状态轴
- implementation：NOT_STARTED/WORKING/REVIEW_READY/INTEGRATED。
- evidence：NOT_RUN/PASS/FAIL/BLOCKED。
- release：INTERNAL_ONLY/ELIGIBLE/EXTERNAL_BLOCKED。
- design：PROPOSED/APPROVED（只对风格）。

依赖默认要求前驱implementation已INTEGRATED且其适用evidence=PASS；设计卡PASS只代表契约完整，不代表真人批准。Q类评测FAIL不阻止归档报告，但阻止相关live启用与最终value gate。发现已有实现满足则evidence-only；禁止无意义重新编码。

## 有界修复
同卡首轮定位→修复→同原例验证→受影响slice→集成复验。最多3轮未改善就停扩散，记录最小反例、候选原因、需要新实验；能做其他卡就继续。不得为关闭状态把FAIL改成“诚实PASS”，不得调整oracle/移除难例/把生成流标成no_model。golden更新必须附变更原因。

## 交接五行
当前任务与base/integrated SHA；已完成行为及证据；明确失败/未测；持有锁与释放条件；下一条可执行动作。上下文压缩前写入，下一Agent从证据文件恢复，不重听几十页聊天。
