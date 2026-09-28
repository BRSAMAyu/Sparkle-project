# V4-U01 · limitations

1. **memory_epoch 陈旧判定客户端不判**：`resume_view_stale_reason` 的 `memory_epoch_changed` 分支需要当前 epoch 权威，移动端读侧无此真源（epoch 由会话/删除/纠正写侧 bump）。客户端只判 `expires_at`；epoch 漂移的权威出口是 I01 按需重算（视图每次装载重算、TTL 30min），消费面下次取数即自愈。已在新文件 docstring 与 limitations 双登记。

2. **回执读面 off/shadow（默认档）下接续面完全缺席**：I06 `context_selection_receipt.v1` 写先行读未开（mode=off/shadow → receipt=null）时，本卡全部增量（上次/下一步/继续收敛）不呈现——这是契约性缺席（无 receipt 不出视图，B05 §2），不是功能缺失；mode=live **且后端存在 `resume_view` 角色回执生产者**后可见（一审 R1-1 勘误：当前后端唯一回执生产链 context_pack.py:2159 硬编码 chat_context，无 resume_view 生产者——live 开启是必要不充分条件；集成依赖已登记 FIX-567，归 contract-owner 卡承接）。当前演示/提审环境若 receipt mode 非 live，验收①的接续增量需以证据测试（桩 live 回执）举证，真实环境行为以读面开关为准。

3. **D01 mark_seen 曝光面未接线（裁决性限制）**：第一主动作的曝光记账要求 `receipt_ref` 必指 D-05 权威 exposed 回执（I2 双门）；首页接续条不是 intervention record，无权威回执可指——接线即需造 ref（违 I2，假曝光）。F03 消费面已就绪（`resume_available` kind 在封闭词表、replay 抑制就位），待 experience_event WS 帧下发面（contract-owner 单独合并，D01 limitations #1）后由既有 adapter 消费，本卡无需再改。

4. **「可调整」路径复用既有次级入口，未新增显式控件**：回归用户的「不接续、换一个」走 cockpit 既有 ghost 次级按钮（/tasks 任务账本），主 CTA 收敛只在「同任务 + 新鲜」时发生。若审查认为需要显式「换个任务」控件，属新增 CTA——与「无竞争 CTA」验收张力需裁决（见挑战 #3）。

5. **视图解析对 unknown 键容忍、对必需键 fail-closed 的不对称**：按 B05 §8 双读纪律实现（旧客户端忽略未知字段）。若 backend 未来在冻结字段集内新增必需语义，本投影会以 hidden 降级而非崩溃——可接受的诚实降级，但意味着「静默不显示」可能掩盖前端未跟版本；由 schema_version 版本门 + I01 契约测试兜底。

6. **style_preview / harness 桩的 phase 选择**：桩钉 `modeGated`（读关闭）而非 `loading`——两者对消费面同为 hidden，但 modeGated 是「如实说明档位」的终态；若后续 preview 需要展示接续面形态，需给 preview 种子加 live 桩（当前 preview 合同 = 离线零网，不展示）。
