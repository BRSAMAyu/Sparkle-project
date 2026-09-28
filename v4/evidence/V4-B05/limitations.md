# V4-B05 · limitations

1. **设计≠实现**：本合同未实现任何代码/迁移/proto；所有"已存在"断言截至 base SHA 3c4618cc 只读勘察，开工由实现卡按当前 HEAD 复核（卡边界条款：禁止假设已存在）。
2. **why_now 物理落点未绑死**：`action_plan.v1.1` 的 DB 落点（独立 JSONB 列 vs 既有 plan JSONB 版本化子键）由 contract-owner 裁定；本合同只冻结字段位语义与读门纪律。
3. **RF-06 交接面为读面推断**：「理解条目」四要素对齐基于 `experience_readouts.py:90` 现行读面与任务指令给定口径（结论/确定程度/来源/纠正动作相邻）；RF-06 分支 `agent/rf06-full-ui@8c6b8c17` 未在本仓可及范围内逐行核验，接续时以其实际 UI 改动盘点为准。
4. **双读用例未运行**：§8 的双读断言属实现卡测试清单（本卡无实现可测）；examples/ 的 JSON 仅语法自测（5/5 通过），未接任何 schema 校验器。
5. **无独立审查**：卡要求 2 位独立审查，本 worktree 交付时仅完成设计自证；review_receipt.json 由审查会话补。
6. **竞态/并发**：同一轮重复产生 receipt 的幂等依赖 `receipt_id` 重算一致，服务端幂等键实现细节留实现卡。
