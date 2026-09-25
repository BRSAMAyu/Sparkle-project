# Q-02 · HUMAN_INBOX 视觉/真机/远程清单（不伪造，待真实环境采集）

> 卡 Q-02「保存视频/截图/trace」：本环境 headless（无 AVD/真机/浏览器自动化权限、无远程
> HTTPS 部署），已交付 API 级 trace（`raw/*.jsonl`，20 条旅程逐步请求/响应/断言链）。
> 以下为转人工/真实环境项。三端平台差异按 U-09 允许差异表
> （`v3/04_ux/MULTIPLATFORM.md`）登记口径执行。

## A. 视频/截图采集（每项注明对应旅程与断言点；命名按 B-04 naming.py）

- [ ] GJ01 fresh→goal→first action：注册→onboarding→建目标→任务完成庆祝覆盖层（android 1080x2400 + web 1280x720 + macOS 800x600 各一段录屏；断言点=任务状态翻 COMPLETED 后首页/今日面即时反映）
- [ ] GJ02 示例→升级→自有目标：guest 演示计划可见→upgrade-guest 表单→升级成功 toast→自有 goal 卡（web 段优先，断言点=表单错误态与成功态两帧）
- [ ] GJ03 Today→行动→结果：今日任务卡完成勾选→成长面板 streak/flame 变化（三端各一段）
- [ ] GJ04 卡住→澄清→rescope：chat 输入「我卡住了…」（当前后端缺陷 V3-FIX-53 修复后采集：应出现一次澄清提问而非沉默）→rescope 后任务卡预计时长/成功标准变化（键盘 IME 动作按钮视觉为系统渲染，允许差异已登记）
- [ ] GJ06 approval→run→receipt：proposal 卡→approve→receipt 页（三端各一段；断言点=transitions 审计可见 approve 记录）
- [ ] GJ08 纠偏→下轮适配：校准卡四动作→下一轮 chat 不再引用已纠偏记忆（V3-FIX-53 修复后采集）
- [ ] GJ09 记忆删除→不复用：memory 面板删除条目→召回面板即时消失（U-09 矩阵 #26-30 同款 surface）
- [ ] GJ10 RAG 引用块：文档处理后 chat 引用块渲染（citations 卡；V3-FIX-53/50 修复后采集）+删除入口存在性（V3-FIX-54 裁决后）
- [ ] GJ11 stale plan 接住横幅：过期计划页首横幅+重新校准流（wt303 交付面真机验证）
- [ ] GJ12 建议卡四态：accept/dismiss/mute/cooldown 呈现与后续抑制（推送通道真机段）
- [ ] GJ13 离线→重连：飞行模式操作→恢复→无重复任务卡（android 真机优先；web 用 DevTools offline）
- [ ] GJ14 run 恢复：杀进程重开→awaiting_step 推导恢复（android 后台杀死 + macOS 重启）
- [ ] GJ16 squad check-in：study-room 进出/心跳 presence→共享错题卡反馈（WS 推送真机段）
- [ ] GJ17 低刺激模式：设置切 low→daily-startup 面呈现降刺激（三端）
- [ ] GJ18 账号切换：A→B 退出登录→登录 B→本地无 A 残留（token 存储后端差异已登记：io=Keystore/Keychain，web=localStorage；断言点=切换后 memory/chat sessions/goals 全为 B 或空）
- [ ] GJ19 远程 HTTPS fresh device：远程部署端点+新设备登录全程录屏（依赖 D 项远程部署）
- [ ] GJ20 竞赛级冷启动 demo：全链一镜到底录屏（V3-FIX-53 修复后采集，chat 拍当前中断）

## B. 真机/真实浏览器交互段（headless 契约测试已覆盖语义，以下为观感与手感）

- [ ] U-09 45 行截图矩阵真机采集（`v3-output/U-09/SCREENSHOT_MATRIX.md`，本卡不重复登记；采集后走 manifest/verify/diff 链）
- [ ] iOS 边缘滑返手势（允许差异登记项的真机确认）
- [ ] android 10.0.2.2 宿主别名连真机栈（dart-define 覆盖路径）
- [ ] 触觉/音频：移动端有、桌面/web 静默降级（允许差异登记项确认）

## C. WS 主路径定界（V3-FIX-53 修复卡输入）

- [ ] /ws/chat（gateway→gRPC StreamChat→ChatOrchestrator 异构实现）对工具意图消息的文本帧下发验证——本卡仅探到 ack/message_ack/status_update/metadata 帧流，未定界文本帧是否同样缺失
- [ ] WS 断线重连+消息幂等真机段（Flutter 客户端重连语义）

## D. 远程环境口径（GJ19 remote 段 RESTRICTED 的解除条件）

- [ ] 远程 HTTPS 部署端点（当前环境无云端）；提供后重跑：
  `python scripts/devtools/q02_run_golden_journeys.py --env remote --remote-url https://<host>`
- [ ] 远程端点证书/域名在 android（cleartext 配置）与 web（CORS/混合内容）下的连通确认
