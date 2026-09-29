# FIX-564 limitations（移交事件接线卡与后续卡）

1. **撤回报告与删除的时序要求**：入口验证门要求撤回在真源证据面可见后才受理。
   事件接线卡投递 `invalidate_on_source_withdrawal` 时必须保证删除/墓碑事务已
   提交（投影 watermark 随行集变化失效，验证门又绕缓存 fresh 读，落定后投递即
   可见）；「先报告后删除」的投递顺序会被 ValueError 拒绝（fail-closed，需重投）。
2. **inference_retracted 不可经本入口受理**（源证据合法存续，物理不可验证）：
   inference 域消费卡的失效路径属其自有卡面；本入口 docstring 已显式声明。
   core `strategy_withdrawal_plan` 的全 kind 词表支持零回退（纯函数层不动）。
3. **D-05 行软删执行器尚未落地**：当前生产无删除 `intervention_lifecycle_events`
   的路径（memory 域删除执行器属后续卡）。验证门在该执行器落地前事实上只放行
   「证据面已被墓碑/删除」的撤回——测试内以软删 helper 等价模拟（M-07 删除链
   口径，projector 测先例同款）。
4. **审计 payload 为 additive**：新增 `affected_states` 键；
   `schema_version` 保持 `experience_strategy.v4.i05.v1` 不 bump（键 additive、
   既有键语义不变；当前全仓无生产消费方——limitations I05 #3 口径延续）。
5. **候选集覆盖的时点性**：sweep 是时点结算——撤回报告之后**新提议**的、引用
   同一已撤源的 patch：同内容返回 revoked 行（内容寻址终态）；异内容在真源已
   删时 admit 走 G1（既有证据门），在证据面墓碑口径下由 `_verify_evidence` 的
   `has_outcome_evidence` 谓词同等拦截。与修前 active/evidenced 的时点语义一致，
   非本卡新增缺口。
6. **误伤防护的边界**：验证门按「证据面是否仍解析」判定，不校验报告者身份——
   入口仍应只由撤回域执行器/运维（有权发起撤回的主体）调用；事件接线卡接线后
   人工入口应收敛为受控运维面（信任主体收窄属接线卡登记义务）。
7. 本卡未触 `friction_chat_wiring` / 决策环装配面；I05 limitations #2（生产
   chat 链 live 门出事实缺位）与 #3（撤回事件面无生产监听器）口径在合并后仍
   成立，移交事件接线卡。
