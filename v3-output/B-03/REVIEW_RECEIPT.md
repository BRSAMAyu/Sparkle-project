# B-03 REVIEW RECEIPT —— R1+R2 合一验收回执

> 验收对象：B-03「三端 Journey Harness + 基线走查」（HEAVY，FieldTest 两轮接续交付 READY_FOR_REVIEW）
> 验收基点：wt7 @ 4c963ef4（= 主仓 42180162 的祖先，merge-base 确认）；主仓 main @ 42180162
> 验收人：B-03 唯一验收关口（R1+R2），2026-09-19
> 验收方式：LIGHT——纯证据审查（未重跑模拟器/构建）；全部实证在 /tmp 隔离克隆完成，wt7 只新增本回执

## 0. 总 Verdict：**ACCEPT（建议合入）**

四条 Worker 核心声称全部经独立实证成立，任务卡 Acceptance 三项全数满足，无阻塞项。
3 项建议级改进（O1-O3）均为 harness 健壮性与文档细节，不阻断合入。

---

## 1. 逐断言 Verdict

### 断言 1：三平台状态（macOS PASS / Web GJ01S PASS + GJ01 诚实 FAIL / Android 4/4 PASS）
**Verdict：属实（VERIFIED）**

| 平台 | 抽检 run | manifest 实测 | 独立验证 |
|---|---|---|---|
| macOS | `gj01_macos_20260919_131219_432f` | ok=true，05:12:19→05:14:34 UTC（=2m15s，与声称分秒吻合），base_sha=4c963ef4 | `screenshots/` 实数 **12 张**全步命名（01-login…12-after-logout）；`02-home-dashboard.png` 实看：真实中文 UI、访客体验b96d、7天连续推进、任务卡真实数据 |
| Web | `gj01s_web_20260919_143734_7410`（GJ01S） | ok=true，4 步全 PASS（open_app_login→register_entry_reachable→form_fields_accept_input→back_to_login） | GJ01S=4 步「最小壳」与 GJ01=18 步「全程」在 journey JSON 实测（`len(backends['web'])==18`，step10=submit_register）与 REPORT/HARNESS 的区分标注一致 |
| Web | `gj01_web_20260919_141821_84dc`（GJ01） | ok=**false**，9 连 PASS 后 submit_register FAIL | steps.json FAIL detail=「等待文本超时(60s): '学习目标' 未出现」；`api_log.jsonl` 实见 POST /api/v1/auth/register → **200**；FAIL 截图在册 |
| Android | `gj01_android_20260919_153033_72b3` | ok=true，4/4 PASS（install→launch→logcat→no_startup_fatal_errors），device=AVD:Medium_Phone_API_36.1 serial=emulator-5554（start 后补写实况 serial 机制生效） | 见断言 2 |

### 断言 2：Android 启动即崩修复（.gitignore 吞 .so → 上游恢复 + 白名单）
**Verdict：属实（VERIFIED），证据链完整闭合**

- **根因实锤（三方印证）**：主仓 `.gitignore:11` 确为全局 `*.so`；主仓 `git ls-files` 中 macOS `libisar.dylib`、iOS `libisar.a` **在库**而 Android jniLibs `.so` **不在**——「同包差异吞没」的叙事与 git 实况完全一致。
- **崩溃证据实看**：`150517_ef3f/screenshots/01-launch_frontend.png` 实看为 IsarError 错误屏，栈自 `main.dart:80 → LocalDatabase.init → Isar.open`；同 run logcat 第 402 行 `FATAL ERROR DURING STARTUP: IsarError ... dlopen failed: library "libisar.so" not found`。且该 run 当时判 PASS（前台判定假阳性）——Worker 将自己的假阳性如实写进 REPORT §4.4 与 EVIDENCE_INDEX（PASS* 标注），诚实性加分。
- **修复验证双通道**：`153033_72b3` 截图实看为**真实产品 UI**（访客体验cde3、Aurora 轻量感知、理解度 75% 卡、目标/任务指挥台、五 Tab 全渲染），截图内会话名「cde3」与 logcat 内 `guest_id=guest_53f5e3b5cde3` 精确互证；本 run 进程（pid 4164）994 行 logcat 中 `FATAL/IsarError` **零命中**，且 `POST /auth/guest → Response 200 → status: ok` 在册——启动→访客登录→网络回环全通。
- **二进制 Supply-Chain 实证**：见 §2 比对表，4 ABI 与 pub.dev 官方 tarball 逐字节一致。

### 断言 3：Web 注册静默假失败（P1 未修、五连复现、定界 Dart 侧）
**Verdict：属实（VERIFIED），定界证据充分，剩余不确定性已如实声明**

探针链 `web_register_defect_probes_20260919/` 实读四件：

| 探针 | 实读结果 | 支撑的排除项 |
|---|---|---|
| `proxy_trace_gateway_response_complete.json.log`（11.4KB） | REQ 全 body + `RESP(200)` 含完整 user 对象（id/username/email…） | 排除网关侧（响应完整写 socket）与代理侧 |
| `probe4_inpage_fetch_vs_xhr_vs_real_ui.log` | 页面内 `fetch` → 200 全量 2482B body；`XHR` → 400（复用已注册用户名的**业务**响应） | 排除传输层/浏览器通道（XHR 收到真实响应即通道健康） |
| `probe5_full_console_capture.log` | pre-submit/post-submit 全 console 无任何 JS 异常 | 支撑「异常被 Dart catch 吞掉」 |
| `probe3_t1_snackbar_visible_form_confirm_cleared.png`（实看） | SnackBar「网络连接不稳定，这次请求没有完整送达。」可见 + **确认密码框为空** + 停留注册页 | 现象本身的可视化铁证 |

- **代码侧印证**：`mobile/lib/core/errors/failures.dart:291` `case DioExceptionType.unknown` → 非 offline 特征归入 `NetworkFailure` → `failures.dart:98` 渲染出与截图逐字相同的文案。现象↔映射链闭合。
- **定界置信度**：网关/代理/传输/JS 四层排除均有实证，「Flutter Web Dart 侧（dio 适配/响应后处理/saveTokens）」的三选一精确落点需 debug 构建落异常栈——Worker 明确声明此剩余不确定性并建议单开诊断卡（主仓 86f3ed6d 已登记 V3-FIX-17），边界处理合格。
- **诚实性**：`141821` manifest ok=false、FAIL step 在册；EVIDENCE_INDEX 将 GJ01 标 **FAIL（诚实判定生效）** 而非 PASS；「最小壳 PASS / 全程 FAIL」双轨标注贯穿 REPORT/HARNESS/INDEX 三文档。注：五连复现=141821 主证 + 探针链多次复刻（proxy trace 与 probe3 为不同账号两次独立复现），另有 140012 首次暴露 run——「五连」计法可追溯，属实。

### 断言 4：31 run 全入索引 / manifest 字段齐全 / 失败非零退出 / simulator 不绕 UI
**Verdict：属实（VERIFIED），两处微小偏差（见 O2）**

- **索引覆盖**：程序化比对——`evidence/` 31 个目录全部在 EVIDENCE_INDEX 中有行，**零遗漏**。
- **manifest 抽检**：6 run 抽检（§3 清单）base_sha/final_sha(-dirty 声明式后缀)/device/started/finished/app_build 字段齐全。
- **失败语义**：runner 代码链路核实——`run_journey.py` `return 0 if manifest.ok else 1`；`driver.start()` 失败也落 FAIL manifest（124249_f491 实证该机制）；「没找到模拟器=FAIL」在 android_driver（AVD 不存在→StepFailure）、macos_driver（无 flutter/无 macOS 目标→StepFailure）均有代码级落实。抽检 FAIL run（141821）manifest ok=false 在案。
- **不绕 UI**：web_driver 实读——定位只读 `flt-semantics` 语义树（`document.querySelectorAll('flt-semantics')`），点击 `Input.dispatchMouseEvent`、输入 `Input.insertText` 真实事件通道；macos 走 finder 级 `flutter test`；android 基线不做 UI 步进并显式 `ui_steps: unsupported`（do_ui_steps_unsupported 直接 raise，不冒充）；api lane 标注 `non-ui lane`。

---

## 2. .so sha256 比对表（patch 载荷 ↔ wt7 工作树 ↔ pub.dev 官方 3.1.0+1）

下载源 `https://pub.dev/api/archives/isar_flutter_libs-3.1.0%2B1.tar.gz`（/tmp 解包比对，未入任何仓库）：

| ABI | sha256（patch 内 = 工作树 = 上游，三方一致） |
|---|---|
| arm64-v8a | `bcc9d0438b5209dd10c2d17c67876e5c0508fd5bd76a2500163599aa496ec050` |
| armeabi-v7a | `38d26dddf16c19c29c162e724b1bd65a81c66912d980b4fc20cf5fb4fa6f8870` |
| x86 | `7c5349a2c99b4d0d55d5b42ae0d66d15c82205292cc971f299a8bf625cdbefad` |
| x86_64 | `c76bed9718f2fa7b108b25558a472675a3c74f976aff4a73271919b5c8f37e35` |

额外验证：patch 经 `git apply --3way` 落盘后重新哈希，4 值不变——**二进制经 patch 传输无损**。版本对应：`mobile/pubspec.yaml:28 isar_flutter_libs: ^3.1.0+1`（vendored path 覆盖），上游版本选取正确。

## 3. 抽检 run 清单（6 项）

1. `gj01_macos_20260919_131219_432f` — manifest 全字段 + 12 截图清点 + home-dashboard 实看 ✓
2. `gj01s_web_20260919_143734_7410` — GJ01S 4 步 PASS manifest ✓
3. `gj01_web_20260919_141821_84dc` — 诚实 FAIL：steps.json FAIL detail + api_log POST 200 + FAIL 截图在册 ✓
4. `gj01_android_20260919_153033_72b3` — 截图实看（真实 UI）+ pid 级 logcat 零 FATAL + /auth/guest 200 ✓
5. `gj01_android_20260919_150517_ef3f` — 崩溃截图实看（IsarError 栈）+ logcat FATAL 行 ✓
6. `web_register_defect_probes_20260919` — proxy trace / probe4 / probe5 / probe3 截图四件实读 ✓

另核：EVIDENCE_INDEX 31/31 目录覆盖（程序化比对）；GJ01S 与 GJ01 journey 定义步数实测（4 vs 18）。

## 4. patch 审查结论

- **gitignore 白名单精确性** ✓：`!mobile/third_party_plugins/isar_flutter_libs/android/src/main/jniLibs/**/*.so` 唯一一条，只放行 isar jniLibs 路径。/tmp 合并树上 `git check-ignore` 双向实测：`jniLibs/.../libisar.so` 不再被忽略；`mobile/some_random/libfoo.so`、`backend/xyz/libtest.so` 仍被 `*.so` 忽略——无大开门。**注意白名单位置在文件尾部是 load-bearing**（gitignore last-match-wins，须排在第 11 行 `*.so` 之后）。
- **代码质量** ✓：全部 python `py_compile` 通过；runner 失败语义/DB 断言 SELECT-only 守卫/`backends` 作用域/badging 解析（从 APK 本体读包名不猜）/崩溃断言/宽松解码实现与声称一致；macos_driver 复用权威测试不重建第二套。无密钥、无主仓绝对路径（patch 中唯一 `/Users/brsama` 是**被删除**的旧硬编码行，属修复本体）、无会话残留（其余命中均为二进制 base85 噪声）。
- **macos_journey_test.dart 改动** ✓：截图路径 worktree 化（空间纪律）+ JOURNEY_SHOT_DEST 注入 + fresh-user 防降级（未见登录页即 failure）+ ErrorWidget.builder finally 还原——不削弱任何 journey 断言。

## 5. 必修项分级

**阻塞项（合入前必须处理）：无。**

**建议项（O，合入时顺手/下轮处理）：**
- **O1** `android_driver.do_launch_app` 焦点判定实现弱于注释语义：`if "mCurrentFocus" in focus and self.package in focus` 检查的是整份 dumpsys window 输出（包名出现在任意行即过），而非解析 mCurrentFocus 行本身。理论上有假焦点窗口；实际被崩溃断言+截图双兜底，本轮未造成误判。建议改为按行解析 `mCurrentFocus` 后判 `self.package in that_line`。
- **O2** 两个 run 目录无 `run_manifest.json`：`gj01_web_111312_605b`（INDEX 已明示「无 manifest」，合格）；`gj01_macos_125619_3774`（目录仅剩 screenshots，INDEX 未标注 manifest 缺失——建议补一句标注）。
- **O3** REPORT §4.4「防回归/防复发」两条 bullet 内容重复（同一句话写了两遍），建议合并。

**可选（N）：**
- **N1** HARNESS.md §3.2「driver 以 --accept-lang=en-US 固定语言」与「后续 journey 文本统一按 zh 书写」并存，读者易惑；建议补一句「accept-lang 只为钉死宿主 locale，步骤文本以 zh 实渲染为准」。
- **N2** logcat 快照为整机 buffer dump，含早于本 run started_at 的前轮流量（153033 含 152540 时段）——方向保守（只会多报不会漏报），且崩溃断言因此仍有效；如需精确可加 `-T <时间戳>`。

## 6. 合入操作建议

1. **在 integration HEAD 用 `git apply --3way` 落 patch**（已在 /tmp 对主仓 42180162 预演）：25/26 文件干净落盘，**唯一冲突点是 .gitignore 尾部**——主仓 d21d1579（`.fieldtest-shots/`）与本 patch 同在 EOF 追加。解法机械：**两个块都保留**（先 `.fieldtest-shots/` 块，后 isar 白名单块），白名单保持在文件尾部。
2. **二进制 patch 注意事项**：patch 为 GIT binary 格式（4 段），必须用 `git apply`（非 `patch -p1`）；落盘后按 §2 表抽验 sha256；`git add` 前确认 .gitignore 冲突已解（白名单生效后无需 `-f`；若先 add 后解冲突则需 `git add -f mobile/third_party_plugins/isar_flutter_libs/android/src/main/jniLibs/*/libisar.so`——即 wt8/PR#18 路线的由来）。
3. **与「组员 PR#18 isar 修复」对账**：① GitHub origin（BRSAMAyu/Sparkle-project）的 PR #18 实为无关的已关闭 retry-UI PR，编号所指应为舰队内部交付（wt8 工作树实测存在同一修复）；② **实测 wt8 的 4 个 .so 与本 patch sha256 完全相同**（`IDENTICAL_BINARY_SET`）——两路交付的二进制无冲突，谁先合入谁为准，后合方预计只剩 .gitignore 尾部文本冲突，同样机械可解。建议主会话二选一定为权威合入源（本 patch 附证据链与验证 run，建议以 B-03 patch 为准），避免双份重复节。
4. **合入后（任务卡协议要求）**：在 integration HEAD 重跑 `python3 run_journey.py --journey GJ01 --backend android`（最小壳含崩溃断言，~1 分钟级）+ `bash scripts/run_all_rule_guards.sh`；V3-FIX-17（Web 注册假失败）保持登记状态待诊断卡。

## 7. 实跑命令清单（验收全记录，均只读或 /tmp 隔离）

```
git -C wt7 log --oneline -5 / status --short          # 基点与工作区状态
git -C Sparkle-project rev-parse HEAD / merge-base     # 主仓 42180162、wt7 为祖先
git apply --stat changes.patch                         # patch 26 文件清点
python3 -m py_compile journey_harness/**.py            # 代码可编译
curl pub.dev/api/archives/isar_flutter_libs-3.1.0%2B1.tar.gz → /tmp 解包
shasum -a 256 两侧 jniLibs/*/libisar.so                # §2 四值比对
git clone Sparkle-project /tmp/b03_merge_test && git checkout 42180162
git apply --3way --check / git apply --3way changes.patch   # 合入预演（/tmp）
git check-ignore 双向测白名单精确性
manifests/steps/api_log/logcat 程序化抽检 6 run
grep FATAL/IsarError 153033 logcat（0 命中）+ pid 4164 隔离复核
实看截图×4（153033 真实 UI / 150517 崩溃屏 / probe3 snackbar / macOS dashboard）
grep DioExceptionType.unknown / 网络连接不稳定 / libisar（代码侧印证）
EVIDENCE_INDEX 31 目录程序化覆盖比对
```

## 8. 收工声明

- wt7 状态比对：会话前后均为 `M .gitignore / M mobile/integration_test/macos_journey_test.dart / ?? jniLibs / ?? journey_harness / ?? v3-output/B-03`——本验收**仅新增本回执**于 v3-output/B-03/，未触碰任何代码与 harness 文件，未 commit/stash/reset。
- /tmp 自清：`/tmp/b03_verify`（上游 tarball 与解包）、`/tmp/b03_merge_test`（合入预演克隆）已删除。
- 未重跑任何模拟器/构建（LIGHT 纪律）；未运行任何 HEAVY 操作。
