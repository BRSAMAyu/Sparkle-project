# 测试系统（考试冲刺/诊断/错题本）真实链路实测（exam-system-eval）

- 日期：2026-09-19 01:47–02:10（本机真服务，未重启任何进程；引擎自发重启 2 次已如实记录）
- 仓库 HEAD：164a1cd6
- 评测员：测试系统真机实测员（curl/python 串行，DB 只读 SELECT；实际触发 LLM 请求 ≈1 次（错题 analyze），预算 15 内）
- 双身份：游客 `guest_917d1105`（`POST /api/v1/auth/guest` 200/548ms，含演示数据种子）＋ 注册用户 `exam_eval_62640`（`POST /auth/register` 200/277ms → `/auth/login` 200/215ms；注册必须带 `accepted_tos:true, accepted_privacy:true`）
- 服务面：网关 :8080（所有请求走网关）；引擎 FastAPI :8000 仅用于故障隔离对照

## 0. 功能面梳理结论

| 层 | 模块/路由 | 状态 |
|---|---|---|
| mobile | `features/plan`（exam_sprint_repository：intake/post-exam-review/completion/portfolio）、`features/home`（exam_sprint_dashboard_card）、`features/error_book`（add/list/detail/review 全套 UI） | UI 存在 |
| mobile | **diagnose/generate、diagnose/grade 无任何调用点与模型**（全仓 grep 零命中） | 功能孤岛（P1-E5） |
| gateway | `/exam-sprint` 9 条路由（R2 补齐 dashboard、diagnose/generate、diagnose/grade、sprint-summary）；`/errors` 走 **gRPC 桥**（非 HTTP 代理），另 3 条 `/error-book/*` 走 HTTP 代理 | 见 P1-E1 |
| engine | `app/api/v1/exam_sprint.py` 8 端点 + `app/api/v1/error_book.py` 全套 | 全部实活 |
| 刷题/练习模式 | 无独立刷题模块；练习面=诊断小测（模板题）+ 错题本复习 | 定性记录 |

## 1. API 实测矩阵（全部经网关，除标注"引擎直连"）

### 1.1 exam-sprint 全端点

| # | 端点 | 身份 | 结果 | 延迟 | 响应摘录 |
|---|---|---|---|---|---|
| 1 | GET /exam-sprint/dashboard | 游客 | ✅ 200 | 83ms | `active=false, plan_id=null`（游客有种子计划却不激活，见 P1-E2） |
| 2 | GET /exam-sprint/dashboard | 注册 | ✅ 200 | 22ms | intake 后 `active=true, plan="15天计算机网络冲刺", days_left=14, task_groups=14, high_freq=20` |
| 3 | POST /exam-sprint/intake | 注册 | ✅ 200 | 501ms | 请求 `{subject:"计算机网络", exam_date:+15d, target_mode:"pass", baseline:{current_level:40, weak_chapters:[子网划分,TCP 拥塞控制]}, daily_study_minutes:90}` → 返回 planning_session_id/goal_model/selected_pack/strategy_preview；`current_level:40` 被自动译为 `knowledge_baseline:"上过课但没复习"` |
| 4 | POST /exam-sprint/diagnose/generate（subject=数据结构，游客种子目标场景） | 游客 | ❌ 422 | 34ms | `{"detail":"知识节点覆盖不足，至少需要 5 个不同知识领域"}`——**MVP 仅支持计算机网络**（`_contains_network_subject` 白名单，`exam_sprint_diagnostic_service.py:568`），种子场景直接不可用（P1-E2） |
| 5 | POST /exam-sprint/diagnose/generate（subject=计算机网络） | 游客/注册 | ✅ 200 | 11–16ms | 10 题/7 领域/est 10min；8 单选+2 简答；**响应内含 grading_payload（带 correct_choice_index）下发客户端**（P1-E4） |
| 6 | POST /exam-sprint/diagnose/grade（受控混合作答①：4 对+2 错+2 短答错） | 游客 | ✅ 200 | 68–87ms | `estimated_score_now=1.0`——**选项文本作答判 0 分**：判分仅认 `a/b/c/d` 或数字索引（`_score_choice_answer`），见 P1-E4 |
| 7 | POST /exam-sprint/diagnose/grade（受控作答②：字母契约 5 对 5 错） | 游客 | ✅ 200 | 87ms | `score=50.0`（恰=5/10 全分题），`pass_probability=0.763`，path=minimum_pass；mastery_updates 按域计算正确（如 TCP 可靠传输 33.3=1/3 对） |
| 8 | POST /exam-sprint/diagnose/grade（受控作答③：9 对 1 错） | 注册 | ✅ 200 | 25ms | `score=90.0`（恰=9/10），`pass_prob=1.0`，path=score_max——**两次受控验证判分精度 100%** |
| 9 | GET /exam-sprint/sprint-summary?plan_id | 注册 | ✅ 200 | 46ms | `days_used=16`、headline「你用了 16 天，完成了 0 项任务」——计划当天创建却显示用了 16 天（P2-Q1，`(end_date-created)+1` 误作已用天数） |
| 10 | GET /exam-sprint/completion?plan_id | 注册 | ✅ 200 | 13ms | `{completed:false, summary:null}`（活跃计划，行为正确） |
| 11 | GET /exam-sprint/portfolio | 注册 | ✅ 200 | 14ms | 1 条 entry，`growth_area="子网划分"`（正确继承 intake 弱项） |
| 12 | POST /exam-sprint/post-exam-review | 注册 | ✅ 422 | 45ms | `{"detail":"考试结束满 24 小时后才能进入复盘"}`——活跃计划被正确业务护栏拦截（非缺陷） |

判分真实性结论：**规则判分，非 LLM**。选择题=索引匹配（0.0/1.0），简答=accepted_answers 精确 → required_keywords 全中 1.0 → 部分关键词封顶 0.85。延迟 25–87ms、generate 11–16ms，排除 LLM 参与。**题目也非 LLM 生成**：`_CN_TEMPLATES` 13 道预置模板按领域优先级选题，generate 零 LLM、零随机。

### 1.2 错题本链（拿题→作答→判分→掌握度）

| # | 端点 | 路径 | 结果 | 响应摘录 |
|---|---|---|---|---|
| 1 | POST /errors 建错题 | 网关 | ❌ 401 | `{"error":"missing authentication metadata"}` |
| 2 | GET /errors 列表 | 网关 | ❌ 401 | 同上 |
| 3 | GET /errors/stats | 网关 | ❌ 401 | 同上 |
| 4 | GET /error-book/remediable-patterns（HTTP 代理路径） | 网关 | ✅ 200 | `[]`（HTTP 代理路径正常，反衬 gRPC 桥断裂） |
| 5 | POST /errors 建错题 | 引擎直连 | ✅ 201 | 67ms；`/27 可用地址` 题，mastery_level=0 |
| 6 | POST /errors/{id}/review（remembered×2→forgotten） | 引擎直连 | ✅ 200×3 | 218–308ms；**mastery 0→0.15→0.3→0.0999… 真实递推**（BKT 类计算，非写死）；review_count 1→2→3 |
| 7 | GET /errors/stats（复习后） | 引擎直连 | ✅ 200 | `need_review_count` 1→0（今日已复习即出队，行为正确） |
| 8 | GET /errors/today-review | 引擎直连 | ✅ 200 | 11ms，1 题在列 |
| 9 | POST /errors/{id}/analyze（异步） | 引擎直连 | ✅ 200 | 41ms「分析任务已提交」；约 1 分钟后 `latest_analysis` 出现内容：error_type=概念混淆 + root_cause + study_suggestion——**此路径是真 LLM**（`error_book_service._run_llm_analysis` → `llm_client.chat_completion`） |
| 10 | GET /errors/{id}/semantic | 引擎直连 | ✅ 200 | 18ms；root_cause 合理，但 `recommended_knowledge=["线性代数","概率论与数理统计","高等数学"]`——**子网题链到数学域**（P2-Q2） |

移动端 `error_book_repository.dart` 全部走 `/errors`（即网关 gRPC 桥）→ **App 内错题本全功能 401 不可用**（P1-E1）。

## 2. 出题质量人工评分（题目=预置模板，非 LLM 生成）

> 场景说明：任务指定的「数据结构期中」场景被 422 拒绝（P1-E2），改用引擎唯一支持的计算机网络科目出 10 题，人工抽验 3 题（含答案核验与干扰项设计）：

| 题号 | 题干摘要 | 标准答案核验 | 干扰项设计 | 人工评分 |
|---|---|---|---|---|
| diag_1 cn_layers_transport_layer | 「TCP/IP 协议栈里负责端到端进程复用与分用的层次？」正确=传输层(idx1) | ✅ 正确 | 应用/网络/链路层均为典型混淆项 | **9/10** |
| diag_2 cn_subnet_hosts | 「192.168.10.0/27 最多可用主机地址？」正确=30(idx1) | ✅ 2⁵−2=30 | 14(误/28)、32(忘减2)、62(误/26) 全是经典错误值 | **9/10** |
| diag_4 cn_tcp_ack | 「seq=1000 长 200 字节，B 返回累计 ACK？」正确=1200(idx3) | ✅ 1000+200=1200 | 1000/1001/1199 为 ACK 语义三种典型误读 | **9/10** |

- 扣 1 分统一原因：**0/10 题带解析**（DiagnosticQuestionPrompt 无 explanation 字段），答错只知对错不知为何。
- 格式合法性：8 道单选全部 4 选项、correct_choice_index 全部落在 0–3；2 道简答均有 accepted_answers+required_keywords；无空 stem、无重复题。**格式合法率 10/10**。
- 切题性：领域覆盖 7 个、难度阶梯（计算/概念/过程追踪/综合）符合「高频考点诊断」定位；但 subject 适配面为零（仅计网）。
- 简答判分核验：`255.255.255.192，62` 全分（标点归一化后 required 全中）、`26` 得 0.1 部分（partial keyword）——与规则一致。

## 3. 闭环验证（做题 → 画像/掌握度/成长值 → aurora/spine 感知）

| 闭环段 | 结论 | 证据 |
|---|---|---|
| 作答→判分 | ✅ 成立 | 受控两次：50.0 与 90.0 与提交组合精确吻合 |
| 判分→用户画像 | ✅ 成立 | `GET /profile/context` 出现 `cold_start_context.diagnostic_estimated_score=50.0`、`diagnostic_top_bottlenecks`、`knowledge_gaps`（含掌握度快照），evidence_refs=exam_sprint_diagnose |
| 判分→dashboard | ⚠️ 有条件成立 | 注册用户（经 intake 建计划）dashboard 实时吸收 `estimated_score_now=90.0 / baseline=40.0 / pass_prob=1.0`；游客（无 intake 元数据计划）恒 `active=false` 不吸收 |
| 判分→galaxy 掌握度 | ❌ **不成立** | `update_galaxy=true` 但 7 条 mastery_updates 全部 `node_id=null`；`_persist_node_mastery` 对解析不到同名节点的项 `continue` 静默丢弃；/galaxy/graph 前后均 57 节点、0 条计网节点、无变化 |
| 判分→成长值(growth-dashboard) | ❌ 不成立 | 前后 narrative 完全相同（该模块为周聚合+LLM 叙事，不吸收单次诊断事件；`growth_dashboard_service.py:260` 确为 LLM 路径） |
| →aurora/spine 感知 | ❌ 不成立 | `/aurora/spine/timeline` `{entries:[],total:0}`；status-band=`sensing/L0 轻量感知中`；modeling-status 5 域全 `missing`；spine_state goal_frame 空——intake+诊断全程未产生 spine 事件 |
| 错题→重练 | ⚠️ 引擎直连成立/网关断裂 | 引擎直连 mastery 真实递推+today-review 循环正常；经网关（App 实际路径）401 全断（P1-E1） |
| 错题模式→补练任务 | ⚪ 未触达 | remediable-patterns 返回空（需先积累错误模式），本轮无法验证模板→任务生成 |

**总评：诊断闭环只走完「判分→画像→dashboard」半条；掌握度/成长值/spine 三处末梢全部断开。**

## 4. 数据真实性核验

| 疑点 | 结论 |
|---|---|
| 判分是规则还是 LLM？ | 规则（索引/关键词匹配），毫秒级延迟+受控可复现即证 |
| 出题是 LLM 吗？ | 否，13 道预置模板轮换（`_CN_TEMPLATES`），generate 11–16ms |
| 掌握度更新是真实计算？ | 两处实测均为真实计算但**去向不同**：错题本 mastery 0→0.15→0.3→0.0999 落库成功；诊断 mastery_updates 计算正确但**写库被静默跳过**（P1-E3） |
| LLM 是否真接入（对照） | 是：错题 analyze 后台真调 qwen3.8-flash，产出 latest_analysis；growth 叙事亦为 LLM 路径（本轮前后文案未变，因周聚合未跨窗口） |
| pass_probability | 公式计算（score/pass_score/days_left/过度自信次数），90 分→1.0、50 分→0.763，单调合理 |

## 5. P1 清单（记录不修）

| # | 问题 | 证据 | 影响 |
|---|---|---|---|
| P1-E1 | **网关错题本 gRPC 桥缺 `user-id` metadata → App 错题本全功能 401**。`injectAuthContext`（`gateway/internal/handler/error_book.go:27`）只附加 authorization；引擎侧 `_resolve_authenticated_user_id`（`error_book_grpc_service.py:58`）要求 `user-id` metadata 且与 JWT sub 一致，否则 401 | 网关 4 连 401 + 引擎日志 `SECURITY: request.user_id present without metadata user-id`（grpc_server_2026-09-19_01-53-25 日志三连）+ 引擎直连同 token 201/200 正常 | App 错题本增删改查/复习/统计全部不可用（HTTP 代理的 3 条 `/error-book/*` 例外） |
| P1-E2 | **游客种子场景与诊断功能脱节**：种子目标「数据结构」422 拒绝（MVP 白名单仅计网）；种子计划 `数据结构期中冲刺` plan_stage=daily、subject 空、无 `source_metadata.exam_sprint_intake` → dashboard 恒 `active=false`（`_get_active_exam_sprint_plan` 过滤，dashboard_service.py:124-140；DB 只读实查证实） | T1 422 + 游客 dashboard active=false + DB 查询记录 | 新游客在唯一被播种的考试场景上，考试冲刺首页与诊断双双不可用；演示链路断头 |
| P1-E3 | **诊断掌握度写库静默丢弃**：galaxy 无同名知识节点时 `node_id=null → continue`（`exam_sprint_diagnostic_service.py:_persist_node_mastery`），`update_galaxy=true` 成为无效参数；不报错、无回执 | grade 响应 7 条 update 全 node_id=null；/galaxy/graph 前后 57 节点零变化 | 「做题→知识星图掌握度」闭环不存在；用户感知不到任何掌握度变化 |
| P1-E4 | **判分契约脆弱+答案下发客户端**：generate 响应携带 grading_payload（含 correct_choice_index/accepted_answers）供无状态判分；判分只认 a/b/c/d 或数字（0-based/1-based 混收），选项**文本**作答一律 0 分（受控实测 4 题全对文本→总分 1.0） | T3 vs T4 对照 + `_score_choice_answer` 代码 | 直连 API 消费者可自改答案作弊；自然语言作答全判错；两问题同根（无服务端判分态） |
| P1-E5 | **移动端无诊断入口**：mobile 全仓无 diagnose/generate、diagnose/grade 调用与响应模型；网关 R2 刚补的 4 条路由从 App 不可达 | 全仓 grep 零命中；`exam_sprint_models.dart` 无对应模型 | 诊断小测对最终用户是隐藏功能；前述 P1-E2/E3/E4 均被此遮蔽 |

P2（记录）：Q1 sprint-summary 首日显示「用了 16 天」（`(end-created)+1`，`exam_sprint_review_service.py:946`）；Q2 错题语义链接错域（子网题→线性代数/概率论）；Q3 题目 0/10 无解析；Q4 游客 `POST /auth/guest` 的 guest_id 为 query 参数，body 传参被静默忽略。

环境观察：测试 40 分钟内引擎 uvicorn 自发重启 2 次（PID 85606/85607→95795@2:02→97067@2:04，恢复约 1 分钟），期间网关一次 502（post-exam-review 首发请求被吞）；JWT 与数据均存活，但**进行中的请求会被打断**。

## 6. 结论

- **exam-sprint 主链（游客+注册双身份）12/12 调用形态正确**（含 2 个正确业务护栏 422），判分精度受控验证 100%，数据真实（规则判分/模板出题/画像真写库）——「考试冲刺规划+诊断」演示可用。
- **错题本经网关 0/4**（401），引擎直连 7/8——功能真实存在但 App 到达路径断裂，是本系统最重 P1。
- **闭环判定：半成立**。作答→判分→画像→dashboard 成立；掌握度（galaxy）、成长值（growth）、aurora/spine 感知三段全断；错题重练仅引擎直连成立。
- 题目质量：3 题人工评分 9/9/9（内容全对、干扰项专业），扣分主因是无解析；「AI 出题」实为「AI 系统预置题库」，营销表述需校准。
