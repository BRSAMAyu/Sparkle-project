# PROGRESS — wt398 / J-01 First 3 Minutes 当前体验实测与机会图

- base SHA: `c1efd8a65da961d657f42de1b2c1a71c5c89c2ed`（worktree `wt398-j01-first3`）
- 状态：**完成**（own_goal 5/5 pass + example 路线全部实跑；报告/机会图已定稿，见同目录 REPORT.md / OPPORTUNITY_MAP.md）

## 已确证的实测发现（真实跑出来的，不是推断）

1. **新访客首屏被种入未声明的演示目标**：`backend/app/services/guest_seed_service.py`
   在 guest 注册时种入「数据结构期中冲刺」假目标 + 卡点「数据结构 - 二叉树遍历算法」，
   新用户首屏直接显示「先解决卡点 / 解开卡点」，无任何「示例体验」标识
   （run 2/3 于 +12s 探测：`seeded_goal_visible=true, declared_example_marker=false`）。
   run 5 于 +14.6s 探测 seed 不可见 → 种子数据出现时序不稳定（待 run 7 复核）。
2. **Guest 永远看不到 own-goal 入口**：`先定下你的第一个目标` CTA 属于
   TodayCockpitCard 的 noGoal 态；guest 被种目标后 cockpit 非 noGoal，
   `/goals/new` 向导对 guest 全程不可达（run 2/3/5 三次复现
   `set_first_goal_cta_visible=false`）。
3. **UI 注册失败 = 静默弹回登录页**：注册提交后若后端拒绝（如
   `@test.local` 被 email 校验拒绝），App 回到空登录表单，无持久错误提示
   （run 3/4/6 截图 `07b-register-result.png`）。
4. **Demo/Example 模式无用户入口**：`体验示例/示例体验/tryExample` 在
   mobile/lib 全库 0 命中；demo_guest_mode_enabled 只被写 false；
   DEMO_MODE 只能由 `--dart-define` 编译期注入（example 路线跑测需开发 flag）。
5. **本地状态 wipe 后仍可能自动登录**：secure storage deleteAll + prefs.clear
   后冷启动仍出现 DashboardScreen（keychain token 残留），已按发现记录并走
   产品 logout 继续（run 5 PX1，run 3 PX1 类似）。
6. **登录页无「体验一个示例」次级 CTA**（FIRST_3_MINUTES.md Screen 1 目标设计
   项）：`example_entry_on_login=false`，全部 pass 一致。

## harness 迭代史（全部是测量基建缺陷修复，未改产品代码）

- run 1: worktree 缺 gitignored 生成物 —— 补 `macos/Flutter/Flutter-{Debug,Release}.xcconfig`
  shim + `make proto-gen`（host toolchain fallback）。
- run 2: prefs.clear 清不掉 keychain token（PX1 自动登录）；CTA 文案搜索时
  dashboard 轮播懒加载未 build。
- run 3: guest 腿成功（PX2-5 三项复现）；注册腿 tap 到 AppBar 标题「注册」。
- run 4: tap `.last 注册` 后发现真正问题是注册 API 拒绝 `@test.local`
  （pydantic email 保留域名校验，curl 复现）。
- run 5: 改 `@example.com` 前的对照跑：PX1 auto-login 后 guest 腿测到
  noGoal CTA（注册用户视角 dashboard）→ 证明该 CTA 只在无种用户出现。
- run 6（当前）：UI 注册失败自动记录（错误文案 + authProvider.error）→
  API 兜底建号（真实 /auth/register，example.com）→ UI 登录 → 继续向导测量。

## 待办

- [ ] own_goal run 7 结果解析（向导双腿计时 + 意图分析 outcome per persona）
- [ ] example 路线（DEMO_MODE=true）实跑
- [ ] opportunity map + 第一分钟阻碍清单写入 v3/09_evidence/j01_first3/
- [ ] 提交到 worktree 分支

## 环境限制（如实）

- 无移动真机/模拟器可用（flutter devices 仅 macOS 桌面 + Chrome）。
  所有实测走 **macOS desktop 集成测试真实渲染路径**（与 B-03 journey 先例一致），
  非 mobile 真机；触控/桌面差异已在报告限制节声明。
- 后端为真服务：gateway :8080 / engine :8000 均 healthy，docker
  sparkle_db/redis/minio up（2026-09-25 检查）。


## 最终追加（2026-09-26）

- own_goal pass0-4 全部完成：5/5 persona guest 腿三项一致（种子假目标✅/无示例标识/无 own-goal CTA），own-goal 腿向导可达但创建失败 ×4（pass0 未捕获标记）。
- 根因实锤（curl 双向验证）：`/goals/analyze-intent` 网关 404（引擎 :8000 有路由返回 401）→ 客户端静默回退 legacy 表单（O10）；`POST /goals/`（307→200）API 直建成而 App 内「创建失败」（O11）。
- example 路线（DEMO_MODE=true）：failures=[]；demo 下也无示例标识、四 tab 无示例入口（O5/O1 强化）。
- 头条：own-goal 全链路 245-314s，4/5 persona 超出 3 分钟预算。
