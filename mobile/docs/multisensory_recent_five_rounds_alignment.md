# 多感官升级最近五轮对齐文档

更新时间：2026-03-22  
范围：仅记录进入“多感官升级”阶段后，最近五轮已经实际落地的前端改动。  
原则：只涉及 Flutter 前端 UI、动效、音效、触感与视觉细节，不涉及后端 API、协议契约或数据结构修改。

## 总览

这五轮的工作重心，是把“局部已经打磨好的多感官基础设施”继续往真实业务链路里铺开，并把“我的 / 设置 / 头像 / 计划详情”这批还带有旧样式痕迹的页面与弹窗收口到统一设计语言中。

重点方向包括：

- 统一 BGM 与环境音能力，支持页面级和阶段级覆盖
- 为设置页补齐用户可见的音频控制能力
- 扩展头像与个人资料编辑链路的视觉层次
- 持续修正个人中心链路里的溢出、布局和信息密度问题
- 统一低频弹窗、危险操作、账号安全页、记忆控制页的材质、留白与反馈体验

---

## 第 1 轮：BGM 基础设施与主链页面覆盖

### 目标

从“已经有音效能力”升级到“页面可以挂载不同 BGM，并且后续可以继续扩展”的状态。

### 已做改动

- 新增全局 BGM 服务，支持：
  - 页面级音乐切换
  - 淡入淡出
  - 音量与启用状态持久化
  - 风格偏好映射
- 新增页面/阶段级音频作用域，允许页面或局部流程覆盖默认 BGM
- 为主链路补了第一轮 BGM 映射：
  - 首页 / 洞察
  - 聊天 / 任务 / 工具
  - 社群
  - 日历 / 成就 / 星图
  - 计划 / 个人页
  - 专注

### 重点文件

- [bgm_service.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/services/bgm_service.dart)
- [bgm_scope.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/widgets/bgm_scope.dart)
- [routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/app/routes.dart)
- [chat_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/chat/chat_routes.dart)
- [community_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/community/community_routes.dart)
- [task_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/task/task_routes.dart)
- [calendar_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/calendar/calendar_routes.dart)
- [achievement_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/achievement/achievement_routes.dart)
- [insights_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/insights/insights_routes.dart)
- [tools_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/tools/tools_routes.dart)
- [plan_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/plan/plan_routes.dart)
- [user_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/user_routes.dart)
- [focus_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/focus/focus_routes.dart)

### 资源与文档

- [bgm](/Users/brsama/code/GitHub/Sparkle-project/mobile/assets/audio/bgm)
- [bgm_sources.md](/Users/brsama/code/GitHub/Sparkle-project/mobile/docs/bgm_sources.md)

### 验证

- 跑过定向 `flutter analyze`
- 未引入新的 `error`

---

## 第 2 轮：设置页 BGM 面板与阶段级节点覆盖

### 目标

把 BGM 从“底层能播”推进到“用户可控制、场景可切换、局部流程可覆盖”。

### 已做改动

- 在设置页新增 BGM 控制面板，提供：
  - 开关
  - 音量
  - 场景偏好
  - 持久化保存
- 将阶段级 BGM 覆盖接入到：
  - 聊天思考态
  - 专注开始
  - 专注沉浸
  - 成就解锁弹窗
  - 视觉元素解锁弹窗

### 重点文件

- [unified_settings_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/unified_settings_screen.dart)
- [bgm_service.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/services/bgm_service.dart)
- [bgm_scope.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/widgets/bgm_scope.dart)
- [ai_status_indicator.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/chat/presentation/widgets/ai_status_indicator.dart)
- [achievement_unlock_dialog.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/achievement/presentation/widgets/achievement_unlock_dialog.dart)
- [visual_element_unlock_dialog.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/visual_elements/presentation/widgets/visual_element_unlock_dialog.dart)
- [focus_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/focus/focus_routes.dart)

### 验证

- 跑过定向 `flutter analyze`
- 无新的前端阻塞错误

---

## 第 3 轮：头像体系扩展、音乐资源补充、路由音频收口

### 目标

增强个人表达与感官氛围，让头像系统与音乐资源都更接近产品气质。

### 已做改动

- 扩展头像选择器：
  - 增加更多头像预设
  - 增加分类筛选
  - 增加顶部预览卡和选中高光
  - 让头像选择本身更像完整体验，而不是简单网格
- 新增 BGM / 环境音资源：
  - 古典钢琴
  - 海洋感 BGM
  - 海浪环境音
- 更新 BGM 与环境音映射逻辑：
  - `piano` 更明确地对应轻钢琴
  - `airy` 更偏海洋、空灵
  - `ocean` 环境音进入可选场景
- 补齐首页、洞察、计划、用户路由的音频映射

### 重点文件

- [avatar_selection_dialog.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/widgets/avatar_selection_dialog.dart)
- [bgm_service.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/services/bgm_service.dart)
- [sensory_feedback_service.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/services/sensory_feedback_service.dart)
- [home_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/home/home_routes.dart)
- [insights_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/insights/insights_routes.dart)
- [plan_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/plan/plan_routes.dart)
- [user_routes.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/user_routes.dart)

### 资源

- [classical_piano_loop.ogg](/Users/brsama/code/GitHub/Sparkle-project/mobile/assets/audio/bgm/classical_piano_loop.ogg)
- [oceanic_drift.ogg](/Users/brsama/code/GitHub/Sparkle-project/mobile/assets/audio/bgm/oceanic_drift.ogg)
- [ocean_waves.ogg](/Users/brsama/code/GitHub/Sparkle-project/mobile/assets/audio/ambient/ocean_waves.ogg)

### 验证

- 跑过定向 `flutter analyze`
- 无新的 `error`

---

## 第 4 轮：设置页与“我的”主链的布局修正与视觉深化

### 目标

优先解决“我的 / 设置”里最容易出问题的溢出、表单挤压和旧样式问题，再往更细的质感与反馈上压。

### 已做改动

- 设置主页面：
  - 修复窄屏下多处 `ListTile + trailing` 的拥挤问题
  - 把容易溢出的设置项改成标题说明 + 下方整行输入/下拉的结构
  - 优化通知权限卡、AI 指标卡、BGM 信息区的材质与说明层级
- 二维偏好控制面：
  - 增强拖动时的微光效、焦点光晕和色偏反馈
  - 让二维手柄不只是“位置变化”，而是有更直观的视觉反馈
- 胶囊生成预览：
  - 做成响应式布局
  - 避免模型名与说明互相挤压
- 个人中心主入口页：
  - 优化等级胶囊、荣誉卡片、设置入口卡
  - 拉齐标题层级、说明文案和图标底板
- 主题设置与智能推送页：
  - 重构为更统一的分组卡片结构
  - 补齐引导说明、视觉层次和一致的表面语言

### 重点文件

- [unified_settings_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/unified_settings_screen.dart)
- [preference_controller_2d.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/widgets/preference_controller_2d.dart)
- [learning_mode_control.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/widgets/learning_mode_control.dart)
- [capsule_generation_preview.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/cognitive/presentation/widgets/capsule/capsule_generation_preview.dart)
- [profile_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/profile_screen.dart)
- [theme_settings_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/theme_settings_screen.dart)
- [smart_push_settings_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/smart_push_settings_screen.dart)
- [sync_center_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/sync_center_screen.dart)

### 验证

- 跑过定向 `flutter analyze`
- 修掉了 `sync_center_screen.dart` 中的实际阻塞错误
- 剩余为历史性 `info` 级 lint

---

## 第 5 轮：个人中心剩余二级页、低频弹窗、计划详情收口

### 目标

把“我的”链路剩下的安全页、低频页、危险操作页、语言弹窗、记忆设置页统一掉，让入口到末端弹窗都不再割裂。

### 已做改动

#### 1. 账号安全链路

- 账号安全页增加了摘要胶囊和更清晰的功能说明
- 会话管理页重做为“摘要卡 + 设备卡”的统一结构
- 社交绑定页增加状态胶囊、解绑确认弹窗统一模态样式
- 安全日志页增加记录总览、异常标记、展开态的二级信息卡片

#### 2. 危险操作与低频确认流

- 删除账号页改成更明确的高风险流程：
  - 风险提示先行
  - 输入确认与二次确认分离
  - 对话框统一为 `GraphiteModalSurface`
- 语言弹窗改成更完整的语言选择卡片，不再是普通列表项
- 邮箱验证码输入弹窗也使用统一模态层次

#### 3. 记忆控制与资料编辑

- 记忆控制页增加状态胶囊、说明层级、分区副标题
- 头像来源底部弹层做成统一的卡片式入口
- 个人资料编辑页顶部增加轻信息带，和头像体系、验证体系配套

#### 4. 边角补齐

- 游客升级页补了说明胶囊、输入区材质统一、社交绑定说明
- 计划详情页补了元信息胶囊，并把归档确认弹窗接入统一模态系统

### 重点文件

- [account_security_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/account_security_screen.dart)
- [session_management_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/session_management_screen.dart)
- [social_accounts_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/social_accounts_screen.dart)
- [security_log_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/security_log_screen.dart)
- [delete_account_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/delete_account_screen.dart)
- [memory_settings_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/memory/presentation/screens/memory_settings_screen.dart)
- [edit_profile_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/edit_profile_screen.dart)
- [unified_settings_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/unified_settings_screen.dart)
- [guest_upgrade_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/guest_upgrade_screen.dart)
- [plan_detail_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart)

### 验证

- 对上述文件跑过定向 `flutter analyze`
- 当前没有新增 `error`
- 剩余仍主要集中在老文件中的 `info` 级 lint，尤其是：
  - [unified_settings_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/unified_settings_screen.dart)
  - 少量 trailing comma / discarded futures / const 建议

---

## 这五轮之后的当前状态

### 已经明显收口的部分

- 多感官基础设施已经可用，不再只是概念层
- BGM 已支持页面级和阶段级覆盖
- 设置页已经能让用户控制 BGM
- 头像、个人资料、语言、记忆控制、安全链路的视觉语言明显更统一
- 低频弹窗和危险确认流不再像系统默认组件“混进来”

### 仍然建议继续推进的部分

- 继续清理 [unified_settings_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/unified_settings_screen.dart) 里的历史 `info` 级 lint
- 把 [persona_onboarding_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart) 继续往新的视觉语言靠齐
- 对“我的”链路做一次真机走查，重点看：
  - 窄屏下文本折行
  - 浅色模式对比度
  - 弹窗与页面之间的动效衔接
  - BGM / SFX / 触觉在设置链路中的一致性

---

## 结论

最近五轮不是在做大重构，而是在持续把已经存在的多感官基础设施和设计系统，真正落进个人中心、设置链路与相关边角页面里。  
当前整体已经从“部分页面精致、部分页面默认感很重”推进到了“主入口到低频页基本同语境”的状态，后续再做就是偏末端收尾和真机体验验收了。
