# V4-U14 · 已知限制（limitations）

如实登记；不降验收阈值，不剪失败样本。逐条给出边界与后续路径。

## L1 · 真机感官证据缺失（DEVICE_UNVERIFIED）
音频降级阈值逻辑、背景声独立开关、触觉偏好只在宿主机单元/widget 测试层验证（调用计数、持久层读写、状态机）。真实系统「拒绝播放」（静音模式/信道占用/系统权限）触发路径、背景声实际听感、触觉舒适度未在物理设备实测。MOTION_AUDIO_HAPTICS 允许口径：模拟器/单元层测调用/去重/静音，硬件舒适度记 DEVICE_UNVERIFIED，不阻止推进。→ 归 Q06（全感官关闭/重放/真机能力矩阵）。

## L2 · 音频降级阈值的「失败注入」未做端到端测试
`_audioPlaybackDegraded` 的状态机（阈值 2 连败、显式重开清位、emit 安全）以 `debugSetAudioPlaybackDegraded` 驱动测试；真实 AudioPlayer 抛错→计数的通路（`_playSound` catch 分支）未在测试中注入真实播放失败（测试环境无音频信道）。代码路径逐行可读、非死代码（catch 块内唯一新增），但该分支本身无自动测试钉。诚实记：机制面已测，故障注入面未测。

## L3 · 深链闸的「本地-only 任务刷新」路径测试覆盖不全
闸的四条解析路径中，本地-only id（访客离线任务）的「刷新列表后再查，仍无→已删面」分支未写独立 widget 测试（需要给 `taskListProvider` 注入可编程 TaskNotifier，其构造面（repository/scheduler/ref 三参 + 自动三加载）在测试下噪声大）。该分支逻辑与已测的服务端 404 分支共享 `_markMissing` 出口；风险为本分支回归不被自动发现，非行为缺陷证据。

## L4 · 无法确认面将 auth 类异常与通用失败并为「暂无法确认」
`categorizeUiError` 的 auth 类别在闸里落了 `offline` 同款可重试面（文案走 lexicon 通用句），未单独建「登录失效」替代页——理由：路由级认证闸（routes.dart redirect）在会话失效后的下一次导航会接管登录流；闸内再建登录面属于与既有认证流重复的第二个权威，违反「不加第二套身份系统」边界。SCREEN_FAMILIES 要求的「404/离线/登录失效不同」中，404 vs 离线已分开；登录失效由路由闸兜底，此取舍如实登记。

## L5 · 关提示音不再连带停背景声是**行为变更**
向后兼容只覆盖了偏好值继承（无 ambient 键时继承 sound_enabled），不覆盖「运行中关提示音同时停掉正在播的背景声」这一旧联动。既有用户若依赖该联动，升级后需单独关背景声。这是卡验收 1（独立偏好）的直接要求，非缺陷；记录为可预期行为差量。

## L6 · 通知「落真实对象」覆盖面以任务执行深链为界
本卡验收 3 的落点实现覆盖 `/tasks/:id/execute`（notification_service 与 push_navigation_service 的主导航目标）。其他深链族（plan/goal/chat）的已删对象面由各自域的 RouteResilience fallback 兜底（回父路由，非空白），未在本卡内逐一改造为「对象不存在」面——那是同族推广工作，如需统一到 `ObjectUnavailableSurface` 应按域逐卡接线（避免单卡横切全部 feature 路由）。

## L7 · 感官偏好的服务端权威同步未扩展
`sensory_feedback.ambient_enabled` 为本地持久（SharedPreferences），未像 accessibility_settings/transparency_level 那样做服务端 user_settings 同步（多设备一致性）。既有 cue/haptic 偏好同为本地口径（U14 未改变其权威面）；若产品要求多设备一致，需后端 user_settings 键 + 同步链（契约变更走单一 owner，不在本 UI 卡内私开路由）。

## L8 · 截图/视频证据未采
`evidence_required.screenshots_video_and_semantics_if_ui` 以 widget 测试断言（键定位 + 中文文案逐字断言）承担语义证明；未采模拟器截图。原因：本会话无接入模拟器预算（六会话并发约束），且新增面均为列表行级 UI（开关行/提示行/居中失效页），测试断言已锁定结构语义。后续审查如需视觉证据，可用 F06 的 evidence 采集测试模式补采。
