# V4-U10 · limitations

## 已知限制（审查者与后续卡必读）

1. **判分只认单键 `answer`，无等价答案变体**：I07 冻结答案键集（v1，11 键）不含 `accepted_answers` 之类的变体键；本卡**刻意不发明**新答案键——任何新答案键若不先进 I07 键集扩展（contract-owner bump `HYBRID_POLICY_VERSION`），红化门不识别即成泄漏面。归一比对只做 strip/casefold/空白折叠，语义等价判分（模型面）属后续卡，须与键集扩展同一契约变更走审。
2. **检验通过后的解析揭示面未做**：判分反馈是封闭词表的泛化短语（对/错各一句）；`explanation`/`solution` 属 I07 答案键，揭示时机与教学呈现（何时可见、是否进入记忆）归后续教学卡——本卡按验收最严读法一律不出口。
3. **练习证据口径 = 关联错题 SM-2 复习计数 > 0**：这是「用户选择且证据支持」的最小诚实实现（确定性、可审计）；尝试质量/步级证据（task step 完成态、focus 投入）未接入，检验推进的证据面增强归后续卡。
4. **REST 走 gateway registerREST bare-group**：裸组 5 方法面是 I01 先例（引擎子路径 405 直通），已在 BA-ROUTES GATEWAY_ONLY ledger 登记（+1 行）；移动端仓库已按冻结契约实现，但端到端真机/真后端联调未做（无真环境授权，不伪造联调通过）。
5. **错题关联仅走知识节点链路**：goal task 无 `knowledge_node_id` 时错题段为空 + `errors_unlinked_no_node` 警示（不硬凑 subject 匹配——避免把无关错题塞进目标上下文）；subject 级回退策略归后续卡裁决。
6. **来源badge的「跳原文片段」当前为呈现面**：badge 携带 id+版本+片段锚并留 `onOpenFragment` 回调，本卡未接文档查看器深链（documents 查看器路由归 documents 卡族）；版本正确性（真实行 updated_at 装配时点读出）与陈旧拒绝门已落地。
7. **截图为宿主渲染证据，非真机**：flutter test 真实渲染（dpr=2、Hiragino 宿主字体、U02TestFonts 先例）；无 iOS/Android 真机与模拟器授权，真机 200% 字体/键盘遮挡等家族检查表项未逐项实测（SCREEN_FAMILIES 家族检查表归 U14 长尾卡收口）。
8. **`correct` 键名双重语义**：判分面顶层 `correct`（bool 裁决字段）与 I07 答案键集成员 `correct` 同名不同面——移动端收口口径如实（R1 N-6）：允许表 + `correct 必须 bool` 为 **assert（debug/test 生效，release 跳过）**；release 下真实防线 = 服务端出口探针（权威门）+ 移动端运行时兜底（`correct is bool ? correct : null` 三元；契约外键无渲染路径）；`sanitize` 红化为运行时逻辑不受 assert 影响。后续若 I07 键集 bump，需复查该命名碰撞是否要改名（breaking 契约变更，本卡不动）。
9. **V3 已 DONE 任务与证据未触碰**：错题/复习/文档/词汇的 V3 行为与测试零改动（受影响面回归 71 移动 + 93 后端全绿佐证）；本卡不重置任何 V3 任务 ID。
10. **检验裁决 reason 词表 v2（R1 N-5 收口）**：`CHECK_VERDICT_REASONS` 由 4 成员扩至 6（+`HOLD.check_authority_missing`、+`HOLD.check_ungradeable`），按模块冻结集更新流程 bump `LEARNING_JOURNEY_SCHEMA_VERSION` v1→v2（v1 未外发、随本卡整改走审）；词表内容有冻结钉死测试锚定，后续扩展仍须 bump + reviewer。
