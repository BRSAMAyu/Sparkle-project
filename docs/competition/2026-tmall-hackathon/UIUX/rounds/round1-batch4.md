# Round 1 · 批次 4 — W-5 语义树 + 存量失败测试清偿 + TextTheme 补齐

> 上游：`round1-batch3.md` §7 移交表 + web 走查 `多端实测/web-round1.md`（W-5/W-6/W-9）。
> 本批边界：**登录页语义树（W-5）、glass-pane 0×0 定性与缓解（W-6）、批次 3 移交项（存量失败测试 /
> _experience.py 正名 / TextTheme 补齐映射）、W-9 定性**。
> 基线：main `b21dce46`（批次 3 已落 ac16dc7b）。wt3 经 `worktree add --force` 重置后开工。
> 纪律：零构建 web；`lib/gen` 与 `backend/app/gen` 为 gitignore 产物（自主 checkout 复制以支撑
> 定向测试/导入链验证，不入库不入 patch）。

---

## 0. 结果速览

| 指标 | 值 |
| --- | --- |
| 改动 | 19 文件（代码 17：mobile 14 + backend 3，含 1 次文件正名与 1 个新测试；+ 记录文档 2） |
| W-5 | 登录页语义树补全：web 端常开语义 + 3 个无名社交按钮 + 密码可见性 tooltip（新增 arb 键 ×2×2 语言）+ 语义树测试 4 用例绿 |
| W-6 | 定性为**引擎级高嫌疑**（3.41 平台视图 DOM 变更后 glass-pane 尺寸/生命周期）；应用层缓解 = web 端 `ensureSemantics()`（随 W-5 落地）；升级评估与验证协议见 §3 |
| 存量失败测试 | **7 例修复**：批次 3 登记的 3 例（main_actions ×2 / router_smoke ×1）+ 过程中确诊同根因的 4 例（main_pages_load_smoke ×4，主题未挂载） |
| TextTheme | SparkleTypography 补齐 15 角色（6 个派生 getter，零新增 fontSize）；`_buildTextTheme` 全角色映射，Material 组件不再回落 Flutter 默认字阶 |
| _experience.py | 正名 `experience_readouts.py`（活路由去私有化前缀）；注册守卫 3/3 绿 + 导入链实证（4 条路由） |
| W-9 | 定性为 go_router 13.2.5 URL 上报路径问题，非一行级可修；升级评估移交（§4） |
| 验证 | 全仓 `flutter analyze` 错误/警告数与基线**逐字相等（245=245，Δ0）**，改动文件 0 error / 0 warning（仅存量 info）；UI-TOKENS 棘轮 **PASS（color=275/275, fontSize=727/727）**；定向测试：test/app 46 全绿（3 连跑）、test/features/auth 18 全绿、i18n 13/13 绿；test/widget 失败数与基线逐字相等（-65=-65，存量债） |

---

## 1. W-5：登录页语义树（P1 a11y）

### 1.1 根因双层

走查实测「整页只暴露 1 个匿名 textbox + 隐藏 Submit、焦点遍历才懒生成节点」。拆成两层：

1. **树未启用（主因）**：Flutter web 的语义 DOM 默认懒构建——仅当浏览器侧辅助技术被探测
   （点击 `flt-semantics-placeholder`、Tab 焦点遍历、`SemanticsBinding.ensureSemantics()`）才生成。
   CDP 级自动化与部分读屏路径拿到的就是空壳。widget 层的 label（`labelText`、按钮文字）本来就会进
   语义——走查看到「无名字」的直因不是 widget 缺 label，而是树根本没建。
2. **widget 层真实缺口（次因）**：三个社交登录按钮是 `InkWell + 纯图标`——语义树中是**无名 button
   节点**；密码可见性 `IconButton` 纯图标无 tooltip——无名。

### 1.2 修复

| 层 | 改动 |
| --- | --- |
| 引擎层缓解 | `main.dart`：`kIsWeb` 时 `SemanticsBinding.instance.ensureSemantics()`——web 端常开语义；移动端维持按需构建（不白付构建开销） |
| 社交按钮 | `_SocialLoginButton` 显式 `Semantics(button: true, label:, onTap:, excludeSemantics: true)`——自包含节点：名称 + button 标志 + tap 动作（读屏可激活），并消除内部图标的匿名子节点 |
| 可见性切换 | IconButton 加 `tooltip`（新增 `authShowPassword`/`authHidePassword` arb 键，zh/en 双语；`flutter gen-l10n` 实测仅 +28 行，批次 3 手工 zh-first 重排**未被破坏**） |
| 测试 | 新增 `login_screen_semantics_test.dart` 4 用例：输入框 accessible name + isTextField 标志；登录/访客命名 button；社交按钮 名称+button+tap 三断言；tooltip 名称随切换状态翻转 |

测试基建注记：本 SDK 测试绑定下 `SemanticsFinder`（`find.semantics.byLabel`）依赖的
`rootSemanticsNode` 不落地（恒 null），语义断言统一走 `bySemanticsLabel` + `tester.getSemantics`；
`SemanticsHandle` 必须在测试终检前 dispose（`addTearDown` 晚于终检，用 try/finally，同 c18 先例）。

---

## 2. 批次 3 移交项处置

### 2.1 存量失败测试：3 例登记 → 7 例确诊 → 7 例全修

| 测试 | 真实根因 | 修复 |
| --- | --- | --- |
| main_actions「create group」/「create post」 | `_pumpPage`/`_pumpRouterPage` 的 MaterialApp **未钉 locale**——文案随宿主系统解析，en 宿主下 `创建社群`/`发布` finder 全部落空（finds 0） | 两 helper 钉 `locale: Locale('zh')`（测试断言与布局基线以 zh 为准） |
| router_smoke「loads critical secondary routes」 | **产品侧真实缺陷**：`SparkleCardSkeleton`（固有高 96 + 自身 padding/边框 34 ≈ 130）被塞进 72px 定高槽（sync_center loading 占位；dashboard 40/48px 同类）→ 晚到帧 58px 瞬态溢出。全数字吻合（96=38+58、offset 17=padding16+边框1） | `SparkleCardSkeleton` 槽位自适应：`LayoutBuilder` 判定可用高度不足时退化为单行骨架（骨架是非信息性占位，行数不影响语义）；宽槽位路径逐字保留 |
| main_actions「edit profile」 | 非 base 失败——en 宿主下 `find.text('Save')` 碰巧命中；locale 钉 zh 后暴露硬编码英文 finder | `find.text('保存')` + 注记 |
| main_pages_load_smoke ×4 | **过程确诊**：该文件 `_pumpPage` 经 `testMaterialApp` 但**未传 theme** → `SparkleThemeExtension is not registered`，页面构建即抛（dashboard ×2 / community / login-semantics） | 传 `theme: AppThemes.lightTheme`；6/6 全绿 |

附带稳态加固：router_smoke/logout 与 edit-profile 在多文件并发下偶发
`Asset 'shaders/ink_sparkle.frag' not found`（flutter_tester 片元着色器资产竞态，基线 2×0 次 /
改动后随机出现；单跑冷启动也复现，热跑必绿）。处置：两个测试文件的测试主题
`copyWith(splashFactory: NoSplash.splashFactory)`——这些测试断言交互与路由，不依赖装饰性墨水。
3 连跑全绿。

### 2.2 `_experience.py` 正名（P3-engine-sweep 遗留③）

`backend/app/api/v1/_experience.py` → **`experience_readouts.py`**。原下划线前缀暗示私有/死代码，
实为活路由（understanding-snapshot + corrections + goal-detail + growth-dashboard 四端点，经
`experience/__init__.py` 间接注册）。选择就地正名而非迁入 `experience/` 包：包内 `*_router.py` 会被
`_include_experience_routers()` glob 自动加载，与 `experience.router` 显式 include 形成双执行（有
路由级去重但模块跑两遍），就地正名零注册语义变化。守卫
`tests/api/test_no_unregistered_routers.py` ALLOWLIST 与注释同步更新；**3/3 绿**；导入链实证：
`experience.router` 暴露全部 4 条路由。

### 2.3 SparkleTypography 15 角色扩展 + TextTheme 补齐映射（L1 §4.1）

- **新增 6 个派生角色**（全部复用既有锚定字阶 46/30/24/19/16/14/12，零新增 fontSize 字面量）：
  `displayMedium→displayLarge`（M3 45→46 收敛）、`displaySmall→headingLarge`（M3 36 就近取 30）、
  `headlineSmall→headingMedium`（M3 24 恒等）、`titleMedium→bodyLarge+copyWith(w500)`（M3 16/w500
  恒等）、`titleSmall→labelLarge`（M3 14/w500 恒等）、`labelMedium→labelSmall`（元数据下限 12）。
- **`_buildTextTheme` 8 → 15 角色全映射**：Material 组件（AppBar/Card/ListTile/Tooltip 等）此前在
  未映射角色上回落 Flutter 默认字阶（Roboto 尺度混入渲染）——补齐后整树单一来源。
- **`DS.titleMedium` shim 有意保留**（仍转发 titleLarge 19）：该 shim 有 34 个存量消费点，切到新的
  16/w500 会在无视觉终验的批次里平移 34 处版式；随批次 3 移交的「DS 冻结数值层逐屏横扫」一并迁移
  （届时直接改用 `context.typo.titleMedium`）。
- `emotion_responsive_theme` 的 15 角色 lift 从此全部吃到真实映射（此前一半映射到 M3 默认值）。

---

## 3. W-6：`flt-glass-pane` 0×0 点击穿透（P2）——定性与缓解

**定性：引擎级高嫌疑，应用层无 CSS/DOM 干预证据。**

- 架构事实：`flt-glass-pane` 是 Flutter web 引擎的指针拦截层，应铺满 `flutter-view` 宿主；3.41 的
  平台视图 DOM 变更（platform views 改为 `flt-glass-pane` 直接子元素）使其成为事件/合成层中枢。
  走查实测其渲染 0×0，而键盘事件（独立通道）正常——与「指针拦截层尺寸/生命周期失效」吻合。
- 上游检索：未找到与「3.41 + glass-pane 0×0」精确对口的 issue（检索面覆盖 flutter/flutter、
  engine、"pointer-router"、"semantics 后不重建"组合）；已知近邻包括 M3 平台视图 slots 破坏性变更
  文档与「web 语义启用后指针事件改经 flt-semantics 节点路由」的行为变化——后者与走查「语义未激活
  状态下点击全落空」的现象自洽，也解释了为什么语义懒激活会改变事件路由。
- **应用层缓解（已落地，随 W-5）**：web 端启动即 `ensureSemantics()`——语义启用驱动引擎重建
  语义/事件宿主层，是对「semantics enable 后 glass-pane 不重建」问题类的定向试探。**未经真机
  验证**（本批零构建 web）。
- **升级评估**：本机 Flutter 3.41.3（2026-02-27，7 个月前）。建议下一 web 会话先用最新 stable
  patch 复测 glass-pane 尺寸（引擎升级不在 UIUX 批次内执行）；同时在修复验证时执行下述协议。
- **验证协议（下一轮 web 走查执行）**：
  1. 加载后量测 `document.querySelector('flt-glass-pane').getBoundingClientRect()`（启用语义前后各一次）；
  2. 真实鼠标（非 CDP 合成）点击「登录」按钮，网关日志交叉验证；
  3. 若升级后仍 0×0：以 minimal repro（`flutter create` 空应用 + 计数器）分层定责引擎 vs 应用。

---

## 4. W-9：会话恢复后 URL hash 停留 `/#/login`（P3）——定性

源码级定性（go_router 13.2.5 `information_provider.dart`）：URL 更新走
`routerReportsNewRouteInformation`，`none` 类型下 `replace = (_valueInEngine == _kEmptyRouteInformation)`；
引擎初始上报（state=null）会把 `_valueInEngine` 重置回空占位。会话恢复路径（isLoading 期停 /login →
认证完成后 refreshListenable 触发 redirect → /home）理论上应带 `replace: true` 重写 hash，实测未重写
——嫌疑收敛在 Router 的 reportable-configuration 判定或引擎侧 replace 应用，**非一行级可修**。
go_router 14.x 重写了该上报路径，升级评估（含 13→14 破坏面盘点）移交独立单；刷新行为正常，
仅观感问题，不阻塞。

---

## 5. 验证

- **全仓 `flutter analyze`**：错误/警告 **245 = 245（与 stash 基线逐字相等，Δ0）**；改动文件口径
  0 error / 0 warning（仅存量 info：main.dart 3 例、skeleton discarded_futures 1 例均为改动前存在，
  经 stash 对照确认）。
- **UI-TOKENS 棘轮**（wt3 树上 `run_all_rule_guards.sh --rule UI-TOKENS`，PYTHON_BIN=python3.11）：
  **PASS — color=275/275, fontSize=727/727**。本批零新增字面量（新角色全部 copyWith 派生）。
- **定向测试**：
  - `test/app/` + `test/features/auth/`：**46/46 全绿**（含新语义测试 4 例；3 连跑稳定，覆盖本批全部
    触点与 7 例修复）；
  - i18n 双文件 **13/13 绿**（l10n gen 后回归）；
  - `test/widget/`：-65 失败与 stash 基线**逐字相等**（存量债，与本批无关）；
  - backend 注册守卫 **3/3 绿**（SECRET_KEY 环境变量注入）+ 正名模块导入链实证。
- 纪律：零构建 web；`lib/gen`、`backend/app/gen` gitignore 产物自主 checkout 复制，不入库不入 patch。

## 6. 残留与移交（批次 5 / 独立单边界）

| 项 | 现状 | 去向 |
| --- | --- | --- |
| W-6 真机验证 | 缓解已落（ensureSemantics），未经真机 | 下一 web 走查按 §3 协议验证；必要时 Flutter patch 升级评估 |
| W-9 hash 重写 | 定性完成，非一行级 | go_router 13→14 升级独立单（含破坏面盘点） |
| `DS.titleMedium` shim（34 消费） | 有意保留转发 titleLarge | DS 冻结数值层逐屏横扫时切 `context.typo.titleMedium`（16/w500，注意版式平移） |
| dashboard 40/48px 骨架槽位 | 已被 SparkleCardSkeleton 自适应兜底 | 视觉终验时复核单行骨架观感是否需专用紧凑占位 |
| test/widget 存量失败 65 例 | 与基线逐字相等，未处置 | 独立修复单（批量基线复扫） |
| features 层名字键调色板 / galaxy decor 横扫 / textTertiary 静态化 / CB 浅色档重校 | batch3 §7 原样 | batch4 未及，继续顺延 |
| 语义树可视化回归（SemanticsFinder 全屏巡检） | 本批仅登录页 | 逐屏横扫时按登录页测试模板复制 |
