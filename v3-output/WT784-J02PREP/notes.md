# WT784 · J-02PREP notes —— simulator 证据卡「门后机械执行」预备包

- 工号：wt784 ｜ 日期：2026-09-27/28 ｜ worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt784-j02prep`
- 分支：`agent/node-b/wt784/j02prep` ｜ **base = main@`e36fe444`**（轮#272）
- 性质：J-02 尚余 simulator 证据卡（FIRST_3_MINUTES 清单）的**预备包，只写不跑**——门后（day7 终门 2026-09-28 08:00）由执行会话机械执行。
- DoD 达成：三件产物 + 语法核验 + 本 notes。

---

## 1. 验收权威原文摘录（v3/07_tasks/tasks.json id=J-02，base e36fe444 亲读）

```json
{
  "id": "J-02", "title": "Onboarding：Value Before Profile", "stream": "JOURNEY",
  "depends_on": ["J-01","U-01"], "required_locks": ["mobile-onboarding"],
  "objective": "重构入口与 progressive profiling，先让用户得到 Action。",
  "work": ["实现两个入口与最小 goal capture。","只问改变 first action 的问题；其他信息延后。","guest example 与 real profile namespace 隔离。"],
  "acceptance": ["fresh user ≤3min 到 useful action；seed 不进入真实 Memory。","注册/游客/升级三端 session 稳定。"],
  "path_seeds": ["mobile/lib/features/onboarding","mobile/lib/features/auth","backend/app/services/guest_seed_service.py"],
  "must_read": ["01_product/FIRST_3_MINUTES.md"],
  "risk": "medium", "resource_class": "HEAVY", "reviewers_required": 1,
  "gate": "V3-1", "status": "TODO",
  "forbidden_practices": ["不得重建已存在的权威真源","不得用 mock/seed 冒充真实行为","不得只通过静态代码阅读宣称用户体验通过","不得弱化既有安全/幂等/隔离/审计守卫"],
  "required_evidence": ["base/final SHA","targeted tests","integration/simulator evidence","review receipt"]
}
```

必读 `v3/01_product/FIRST_3_MINUTES.md`「Automated simulator acceptance」七项：fresh install/cleared state；首屏 primary CTA 无滚动可见；5 次不同 Persona 不出现相同模板化 action；3 分钟脚本以内到 Action；loading >500ms 有反馈；错误不回空白页；截图由视觉 Reviewer 按 rubric 打分。

## 2. 既有交付盘点（git log --grep + v3-output 双证，亲读）

| 交付 | SHA | 内容 | 与本卡关系 |
|---|---|---|---|
| wt282（J02-VALUE-ONBOARD） | `f18f99f4` → `cd154f03` | 首跑字幕 N48 zh+en、persona 草案 8 字段 debounce+clamp 续存、注册硬跳移除→软墙 + OnboardingResumeCard（dashboardSections 挂载） | 工程底座，E1/E2 面 |
| wt764（WT764-J02） | base `3cbeb4a7` / final `787bc973` | 快车道 CTA（`j02-fast-path-cta`，goal-only 载荷、deferredAt、onboardingCompleted 推断语义）+ router_smoke 三端三角 + 后端两 pin 测试 4/4；≤3min 为 **headless 验算**（自decl非实测） | J-02 工程面合格（wt772 判）；simulator 缺口即本卡 |
| wt772（WT772-J02-REVIEW） | `7bbaf092` | 独立审查 receipt：**PARTIAL 不销账**，唯一缺口=integration/simulator evidence（§6-1）；变异咬合抽验过；§6-4 计数笔误裁定 | 销账前置权威；门后新 receipt 须引之 |
| 轮#265 | `fd4267ef` | "wt772 集成（J-02 PARTIAL 不销账）+ simulator 卡排门后"——即本预备包的派单依据 | — |
| wt398 J-01（v3/09_evidence/j01_first3/） | base `c1efd8a6` | **本卡方法学先例**：macOS 集成测试 + 真实后端 + 5 persona + 墙钟 + 截图全要素已证可跑；O1-O11 发现清单 | 驱动形制/runner/fallback 全部照搬其法 |
| wt430 O10/O11 | V3-FIX-140/141 `FIXED@5aaf2c1a` | analyze-intent 网关代理 + createGoal 307 修复 | J-01 当年阻塞项已修（无实机复测，见 checklist G4） |
| wt490/wt496 | V3-FIX-17 `e460f192` / V3-FIX-205 `cbc8e8ad` | Web 注册假失败修复 / 升级 token 降级修复 | 升级端 leg 依托 |
| wt287 | `2f27dd2a`/`e387f380` | GuestConversionCard 盲区闭合 | wt759 缺口⑤确认过时（wt772 §4 复核） |

## 3. 三件产物说明

| 产物 | 内容 |
|---|---|
| `runbook.md` | 门后执行手册：通道选择（主=macOS 集成测试通道，J-01 已证；iOS/Android 模拟器为备选并明示 UI 驱动缺口）、环境清单与一次性 setup、fresh install 三通道语义、Leg R（注册端 10 步）/G（游客端 4 步+DB 探针）/U（升级端 3 步）逐步骤预期画面+截图时点+判据、5 persona 差异化、秒表规则、产物命名模板、失败留证规则、acceptance 逐条映射 |
| `first3minutes.sh` | bash 编排骨架（DRYRUN 默认 1 安全门）：preflight→fresh_install（三通道）→build_and_install（iOS/Android 为占位并明示）→run_journey（驱动存在性守卫+flutter test 形制）→db_probes（sparkle_db 只读 psql）→verdict（180,000ms 秒表判定，**注明 exit 0 不冒充验收**） |
| `checklist.md` | 证据↔acceptance↔产物路径三列映射：required_evidence 四项 + acceptance 两条拆五面 + FIRST_3_MINUTES 七项 + Work 三项；覆盖列引 SHA；缝隙七条（§6）如实 |

## 4. 语法核验实录（first3minutes.sh）

```
1) bash -n first3minutes.sh                    → SYNTAX-OK（首轮）
2) DRYRUN 冒烟（默认模式实跑打印计划）          → 暴露真缺陷：$LANE 后随全角（
   在 set -u 下解析为未绑定变量 LANE（ 报错退出 55 行
3) 修复：${LANE}/${bundle}/${pkg}/${PASS}/${SKIP_BUILD} 加花括号 ×5 处
4) grep -E '\$[A-Za-z_]+[）(（]' 复扫          → 0 命中
5) bash -n 复核                                → SYNTAX-OK
6) DRYRUN --lane macos / ios / android 三通道  → 全部 exit 0，计划打印正确
7) chmod +x 落位
```

未执行任何真跑路径（DRYRUN 门未开、无设备/栈触碰）。

## 5. 关键代码事实核（本包文案/键名全部实证于 base e36fe444）

- `continueAsGuest`="以访客身份继续"、`authTryExample`="体验一个示例"（app_zh.arb :97/:15939；login_screen.dart :282-298）
- 快车道：`personaFastPathCta`="先拿第一步行动"、hint="只回答目标这一个问题…"（arb :958-961）；`ValueKey('j02-fast-path-cta')`（persona_onboarding_screen.dart :251）
- 软墙三端语义（router_smoke_test.dart :150-240）：注册未完成→/home + Dashboard；guest 访 persona→折回 /home；升级后 persona 可达
- `OnboardingResumeCard` 挂载 dashboard_screen.dart :1156；`FirstActionCard` :1168（诚实失败面 + PENDING proposal 确认三字段）
- API base：Android 模拟器默认 `http://10.0.2.2:8080`、iOS 模拟器/桌面 `http://localhost:8080`，`API_BASE_URL` dart-define 可覆写（api_constants.dart）
- DB 探针目标：容器 `sparkle_db`、user `postgres`、db `sparkle`（docker-compose.celery.yml）

## 6. 缝隙盘点（不美化；全量三列版见 checklist.md §6）

1. **wt764 notes §7 计数失实未更正**（8/8,3/3,5/5 实为 7/1/4，用例实全绿）：wt772 §6-4 裁定的轻量更正项至今未落地——销账前须补注记。
2. **tasks.json J-02 status=`TODO` 与 fleet 实际 PARTIAL 脱节**（规格权威 vs 运行状态权威）：本卡不改 tasks.json，留集成会话收口。
3. **O3 桌面注册 tap 无效无 FIX 号无已证修复**：若门后复现将直接卡 Leg R 主链——runbook 已设诚实 fallback（API 注册+UI 登录，instrumented 披露、不计入 ≤3min 主张）。
4. **O10/O11 修复（5aaf2c1a）无实机端到端复测**：门后 R8 天然首验，不直接阻塞本卡。
5. **J-02 专属 dart 驱动不存在**（first3_measurement_test 是 J-01 wizard 路线）：runbook §2.2 明示执行会话第一步编写，J-01 同构、产品代码零改动。
6. **GJ01 journey JSON web 轮期望过时**（注册后 wait 学习目标 vs 软墙语义）：harness 陈旧，本卡 runbook 自带当前期望，GJ01 留 harness 维护卡。
7. N49 首聊破冰：wt772 已裁 post-RC 跨层卡，非销账前置。

## 7. 记账与纪律

- 本卡新缺陷登记备用号：**V3-FIX-533**（base e36fe444 grep `V3-FIX-533` = 0 命中，最新已用 532，亲证空闲）。预制施工未发现需登记的新真缺陷（G1-G7 均为既有事实盘点，非新发现）。
- 零触碰：flutter build/run 未执行、模拟器未启动、docker/:50051/:8000/:8080 未碰、`/tmp/northstar_ns001_real_drive_state.json` 未碰、DYNAMIC_ISSUES.md 未改、未 push。
- worktree 过程注：首次 `git worktree add` 因 shell cwd 重置落在 sparkle-cosmos 仓，即发现即移除（worktree remove + branch -D），重建于 Sparkle-project@e36fe444，无残留。
- final SHA：见分支 HEAD（commit 记录）。

*—— wt784 预备包完毕，READY_FOR_GATE（门后执行会话按 runbook.md 机械执行）。*
