# V4-F03 · limitations（如实登记，不作实现事实外推）

## 本卡交付边界内的已知限制

1. **WS 下发面未落 proto（契约 owner 位评估结论：单独移交合并）**：F03 被
   指名为 WS Frame 契约 owner 位，但本会话工程纪律明令「不碰 proto」，且卡
   path_policy 原文「契约/迁移由单一 owner 单独合并」。判定：`ExperienceEventFrame`
   proto 增量（oneof 挂 `WebSocketMessage` + `make proto-gen`）作为**单独契约
   commit** 移交（消费面已 transport-ready：mobile 按 B05 §3 JSON 形状解析，
   frame 落地即插即用；映射建议：frame 字段 = `event.to_dict()` 原样载荷 +
   `event_id`/`dedupe_key` 顶层冗余位，对齐 D01 发布载荷形状）。**「移动端已
   能收到呈现事件」不是本卡可声明的事实**；本卡可声明的是「事件生产流已接
   通、消费语义已实现并被测试钉死」。
2. **mobile 适配器尚无真实屏幕消费方**：现有屏幕的成功反馈仍走各自直调
   `SensoryFeedbackService` 的既有路径（V3 形态）。本卡交付统一入口 + 事件
   消费语义；把既有屏幕逐面切换到适配器属后续逐 surface 工程（与 F04
   mobile-shell 在航面强耦合，且在 WS frame 落地前无事件源可接）。在切换完成
   前，「全部屏幕经适配器呈现」不可声明；已可声明的是：事件驱动的呈现
   （backend 生产流 + mobile 适配器）满足三条验收。
3. **生产挂点 event_bus=None（与 D01 生产形态同构）**：`approve`/过期清扫/
   API 错误面挂点投影成立、发布跳过（`published=False`）——与生产 mark_seen
   调用方形态一致（D01 二审 §3 判例）。发布随 consumer 形态注入（同
   `intervention_event_consumer` 模式）；事件内容寻址可重放，`replay_action_receipt`
   任意时点补发恒同 id。
4. **记忆域回执暂无可投影的 ref scheme**：`EXPERIENCE_RECEIPT_REF_SCHEMES`
   六元封闭集无 `memory://`——记忆写回执接入 ExperienceEvent 需要 scheme 契约
   变更（contract-owner）。卡验收 2 的 memory 面由两处机制保证并可测：(a)
   backend 冻结文案路由（memory→memory.saved，永不任务成功文案/成功模态），
   (b) mobile subject 分层路由（memory→高亮+轻触，无成功徽章/声触，禁词扫描）。
   真实记忆回执的生产投影留待 scheme bump。
5. **create 型命令（create_batch）不产对象级呈现事件**：无 subject（type/id
   空）→ `subject_unanchorable` 如实拒绝——去重身份无锚，不造泛化成功。
   milestone 式建批的完成呈现留待有锚方案（如以创建行数聚合的 progress 语义）。
6. **声/触为决策面证据，非设备面**：适配器声/触断言用记录型 sink（真机
   听感/震感/舒适度属 DEVICE_UNVERIFIED，MOTION 纪律原文）；`SensoryFeedbackSink`
   默认实现委托既有服务的系统语义触觉，未新增音频资产（零资产=零授权负担）。
7. **copy 文案为中文单语**：冻结表与 F2 像素组件族中文标签同构（V4 竞品面
   现状）；i18n 接线归 l10n 面（本卡不触 l10n 生成文件）。
8. **错误面挂点覆盖 approve 端点**：`cancel`/`reject` 端点按契约 §6 不产
   事件（用户亲自操作即时可知）；其余端点（create/list/get/receipt/transitions）
   无呈现语义。若未来 `create` 需要失败呈现，走同款 by-id 挂点（已有）。

## 环境性限制（非代码事实）

- worktree 无 .env：backend pytest 需 `SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`
  （conftest 强制 test 环境落 sqlite 内存，不触 dev DB）。
- `backend/app/gen`、`mobile/lib/gen` 为 gitignored 实体目录，从主检出复制
  （非 symlink，永不入库）；`flutter pub get` 会误触 l10n 再生成（F02 同款
  已知行为），已 `git checkout -- mobile/lib/l10n/` 还原。
- 本机 macOS arm64（AGENTS.md 硬规则 4 的 Windows 表述为旧阶段事实）；纯
  Python/Dart 变更无 cgo/平台面。

## 审查挑战点预登记（供两位独立审查复核）

1. **C-1 闭合的「生产」强度**：`project_terminal_reason`/`project_error_state`
   的生产调用方 = 本卡三个挂点。请复核：(a) 挂点确为生产路径（approve 服务
   成功路径 + expire sweep + API approve 错误面）；(b) 韧性壳不吞 fail-loud
   语义（INVALID_COMMAND 拒绝 → warning 留痕 + None，不静默映射）；(c) 双重
   投影面（approve 懒转过期走 API 错误面挂点、sweep 走终态挂点）dedupe 身份
   是否恒一（kind=terminal_failed + receipt_ref + version——懒转与 sweep 的
   proposal.subject_version_token 相同则同 id，幂等吸收）。
2. **mobile copy 表与 backend 表的镜像同步**：17 键逐键测试钉死在两侧各自
   测试内，但**无跨端单一真源**（flutter 侧不能 import backend）。漂移风险 =
   一侧 bump 忘改另一侧（两侧测试都会因键数断言先红，但文案内容改字不会红）。
   请评估是否需要生成式单一真源（scripts/devtools 同步脚本）作为后续卡。
3. **version 校验的语义口径**：当前口径 = committed 成功类事件在
   `currentSubjectVersionToken == null`（断网/未对账）时降级 unknown、不匹配
   时过期抑制。反方向挑战：失败事件（terminal_failed）**不**做 version 校验
   （失败是已发生事实）——是否会被读成「失败呈现不受版本纪律约束」？判定
   依据：MOTION「单次失败只提示一次」+ B05 §6 失败模态纪律；请独立复核。
4. **replay 抑制的会话级存储**：`_seenEventIds` 为内存会话级集合，App 重启
   即清空——重启后重放同一 event_id 会再次触发声/触。B05/MOTION 口径是
   「恢复重放不重复音/震」（恢复流程内的重放，本卡满足）；跨会话持久去重
   需要存储面（SharedPreferences/DB），本卡未夹带。请复核该边界是否可接受。
5. **适配器未被任何屏幕消费（limitations #2）**：验收以适配器 + 徽章绑定
   测试为面。若审查认为「统一入口」必须包含至少一个真实屏幕切换才算闭合，
   修正路径 = 选一个非路由冲突面（如 intervention 卡片 mark_seen 上报处）做
   单点接线增量——请裁决是否属本卡。
