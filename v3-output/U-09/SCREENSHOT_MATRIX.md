# U-09 三端截图矩阵（可执行清单）

- 构建 SHA8：`<BUILD_SHA8>`（用 `git rev-parse --short=8 HEAD` 取）
- 端与 viewport 口径：v3/04_ux/MULTIPLATFORM.md；命名：B-04 naming.py（surface__state__persona__platform__viewport__sha8.png）
- 采集前置：真实后端（gateway/engine）与真实账号（demo_data/new_user），不用 mock 冒充；galaxy 允许 dark cosmic。

| # | surface | state | persona | platform | viewport | 采集入口 |
|---|---------|-------|---------|----------|----------|----------|
| 1 | onboarding | persona_start | new_user | android | 1080x2400@3.0 | 注册新账号 → 登录后自动跳 /onboarding/persona |
| 2 | onboarding | persona_start | new_user | web | 1280x720@1.0 | 注册新账号 → 登录后自动跳 /onboarding/persona |
| 3 | onboarding | persona_start | new_user | web | 360x720@1.0 | 注册新账号 → 登录后自动跳 /onboarding/persona |
| 4 | onboarding | persona_start | new_user | macos | 800x600@2.0 | 注册新账号 → 登录后自动跳 /onboarding/persona |
| 5 | onboarding | persona_start | new_user | macos | 1280x800@2.0 | 注册新账号 → 登录后自动跳 /onboarding/persona |
| 6 | home | main | demo_data | android | 1080x2400@3.0 | 演示账号登录 → 底部 Tab 1（home） |
| 7 | home | main | demo_data | web | 1280x720@1.0 | 演示账号登录 → 底部 Tab 1（home） |
| 8 | home | main | demo_data | web | 360x720@1.0 | 演示账号登录 → 底部 Tab 1（home） |
| 9 | home | main | demo_data | macos | 800x600@2.0 | 演示账号登录 → 底部 Tab 1（home） |
| 10 | home | main | demo_data | macos | 1280x800@2.0 | 演示账号登录 → 底部 Tab 1（home） |
| 11 | chat | history_citations | demo_data | android | 1080x2400@3.0 | chat Tab → 会话历史列表 → 打开演示会话，滚至含引用块的回复 |
| 12 | chat | history_citations | demo_data | web | 1280x720@1.0 | chat Tab → 会话历史列表 → 打开演示会话，滚至含引用块的回复 |
| 13 | chat | history_citations | demo_data | web | 360x720@1.0 | chat Tab → 会话历史列表 → 打开演示会话，滚至含引用块的回复 |
| 14 | chat | history_citations | demo_data | macos | 800x600@2.0 | chat Tab → 会话历史列表 → 打开演示会话，滚至含引用块的回复 |
| 15 | chat | history_citations | demo_data | macos | 1280x800@2.0 | chat Tab → 会话历史列表 → 打开演示会话，滚至含引用块的回复 |
| 16 | goal | library_main | demo_data | android | 1080x2400@3.0 | home → 目标入口（/goals） |
| 17 | goal | library_main | demo_data | web | 1280x720@1.0 | home → 目标入口（/goals） |
| 18 | goal | library_main | demo_data | web | 360x720@1.0 | home → 目标入口（/goals） |
| 19 | goal | library_main | demo_data | macos | 800x600@2.0 | home → 目标入口（/goals） |
| 20 | goal | library_main | demo_data | macos | 1280x800@2.0 | home → 目标入口（/goals） |
| 21 | task | library_main | demo_data | android | 1080x2400@3.0 | home → 任务入口（/tasks） |
| 22 | task | library_main | demo_data | web | 1280x720@1.0 | home → 任务入口（/tasks） |
| 23 | task | library_main | demo_data | web | 360x720@1.0 | home → 任务入口（/tasks） |
| 24 | task | library_main | demo_data | macos | 800x600@2.0 | home → 任务入口（/tasks） |
| 25 | task | library_main | demo_data | macos | 1280x800@2.0 | home → 任务入口（/tasks） |
| 26 | memory | panel_main | demo_data | android | 1080x2400@3.0 | home/profile → 记忆入口（/memory） |
| 27 | memory | panel_main | demo_data | web | 1280x720@1.0 | home/profile → 记忆入口（/memory） |
| 28 | memory | panel_main | demo_data | web | 360x720@1.0 | home/profile → 记忆入口（/memory） |
| 29 | memory | panel_main | demo_data | macos | 800x600@2.0 | home/profile → 记忆入口（/memory） |
| 30 | memory | panel_main | demo_data | macos | 1280x800@2.0 | home/profile → 记忆入口（/memory） |
| 31 | galaxy | tree_expanded | demo_data | android | 1080x2400@3.0 | galaxy Tab → 等待节点树渲染后展开演示节点 |
| 32 | galaxy | tree_expanded | demo_data | web | 1280x720@1.0 | galaxy Tab → 等待节点树渲染后展开演示节点 |
| 33 | galaxy | tree_expanded | demo_data | web | 360x720@1.0 | galaxy Tab → 等待节点树渲染后展开演示节点 |
| 34 | galaxy | tree_expanded | demo_data | macos | 800x600@2.0 | galaxy Tab → 等待节点树渲染后展开演示节点 |
| 35 | galaxy | tree_expanded | demo_data | macos | 1280x800@2.0 | galaxy Tab → 等待节点树渲染后展开演示节点 |
| 36 | profile | main | demo_data | android | 1080x2400@3.0 | 底部 Tab 5（profile） |
| 37 | profile | main | demo_data | web | 1280x720@1.0 | 底部 Tab 5（profile） |
| 38 | profile | main | demo_data | web | 360x720@1.0 | 底部 Tab 5（profile） |
| 39 | profile | main | demo_data | macos | 800x600@2.0 | 底部 Tab 5（profile） |
| 40 | profile | main | demo_data | macos | 1280x800@2.0 | 底部 Tab 5（profile） |
| 41 | settings | main | demo_data | android | 1080x2400@3.0 | profile → 设置（/profile/settings） |
| 42 | settings | main | demo_data | web | 1280x720@1.0 | profile → 设置（/profile/settings） |
| 43 | settings | main | demo_data | web | 360x720@1.0 | profile → 设置（/profile/settings） |
| 44 | settings | main | demo_data | macos | 800x600@2.0 | profile → 设置（/profile/settings） |
| 45 | settings | main | demo_data | macos | 1280x800@2.0 | profile → 设置（/profile/settings） |

## 采集清单（逐张勾选；断言点见 diff report）

- [ ] `onboarding__persona_start__new_user__android__1080x2400@3.0__<SHA8>.png`
- [ ] `onboarding__persona_start__new_user__web__1280x720@1.0__<SHA8>.png`
- [ ] `onboarding__persona_start__new_user__web__360x720@1.0__<SHA8>.png`
- [ ] `onboarding__persona_start__new_user__macos__800x600@2.0__<SHA8>.png`
- [ ] `onboarding__persona_start__new_user__macos__1280x800@2.0__<SHA8>.png`
- [ ] `home__main__demo_data__android__1080x2400@3.0__<SHA8>.png`
- [ ] `home__main__demo_data__web__1280x720@1.0__<SHA8>.png`
- [ ] `home__main__demo_data__web__360x720@1.0__<SHA8>.png`
- [ ] `home__main__demo_data__macos__800x600@2.0__<SHA8>.png`
- [ ] `home__main__demo_data__macos__1280x800@2.0__<SHA8>.png`
- [ ] `chat__history_citations__demo_data__android__1080x2400@3.0__<SHA8>.png`
- [ ] `chat__history_citations__demo_data__web__1280x720@1.0__<SHA8>.png`
- [ ] `chat__history_citations__demo_data__web__360x720@1.0__<SHA8>.png`
- [ ] `chat__history_citations__demo_data__macos__800x600@2.0__<SHA8>.png`
- [ ] `chat__history_citations__demo_data__macos__1280x800@2.0__<SHA8>.png`
- [ ] `goal__library_main__demo_data__android__1080x2400@3.0__<SHA8>.png`
- [ ] `goal__library_main__demo_data__web__1280x720@1.0__<SHA8>.png`
- [ ] `goal__library_main__demo_data__web__360x720@1.0__<SHA8>.png`
- [ ] `goal__library_main__demo_data__macos__800x600@2.0__<SHA8>.png`
- [ ] `goal__library_main__demo_data__macos__1280x800@2.0__<SHA8>.png`
- [ ] `task__library_main__demo_data__android__1080x2400@3.0__<SHA8>.png`
- [ ] `task__library_main__demo_data__web__1280x720@1.0__<SHA8>.png`
- [ ] `task__library_main__demo_data__web__360x720@1.0__<SHA8>.png`
- [ ] `task__library_main__demo_data__macos__800x600@2.0__<SHA8>.png`
- [ ] `task__library_main__demo_data__macos__1280x800@2.0__<SHA8>.png`
- [ ] `memory__panel_main__demo_data__android__1080x2400@3.0__<SHA8>.png`
- [ ] `memory__panel_main__demo_data__web__1280x720@1.0__<SHA8>.png`
- [ ] `memory__panel_main__demo_data__web__360x720@1.0__<SHA8>.png`
- [ ] `memory__panel_main__demo_data__macos__800x600@2.0__<SHA8>.png`
- [ ] `memory__panel_main__demo_data__macos__1280x800@2.0__<SHA8>.png`
- [ ] `galaxy__tree_expanded__demo_data__android__1080x2400@3.0__<SHA8>.png`
- [ ] `galaxy__tree_expanded__demo_data__web__1280x720@1.0__<SHA8>.png`
- [ ] `galaxy__tree_expanded__demo_data__web__360x720@1.0__<SHA8>.png`
- [ ] `galaxy__tree_expanded__demo_data__macos__800x600@2.0__<SHA8>.png`
- [ ] `galaxy__tree_expanded__demo_data__macos__1280x800@2.0__<SHA8>.png`
- [ ] `profile__main__demo_data__android__1080x2400@3.0__<SHA8>.png`
- [ ] `profile__main__demo_data__web__1280x720@1.0__<SHA8>.png`
- [ ] `profile__main__demo_data__web__360x720@1.0__<SHA8>.png`
- [ ] `profile__main__demo_data__macos__800x600@2.0__<SHA8>.png`
- [ ] `profile__main__demo_data__macos__1280x800@2.0__<SHA8>.png`
- [ ] `settings__main__demo_data__android__1080x2400@3.0__<SHA8>.png`
- [ ] `settings__main__demo_data__web__1280x720@1.0__<SHA8>.png`
- [ ] `settings__main__demo_data__web__360x720@1.0__<SHA8>.png`
- [ ] `settings__main__demo_data__macos__800x600@2.0__<SHA8>.png`
- [ ] `settings__main__demo_data__macos__1280x800@2.0__<SHA8>.png`

## 通用断言点（每张图都要核对）

核心层级结构一致；核心文案一致；状态语义（空/加载/长等待/错误/离线/部分数据）一致且有下一步
