# V4-B04 独立审查 receipt（一审 R1）

- 审查会话：wtB04R（未参与实现，独立会话）
- 审查时间：2026-09-28 18:0x +08:00
- 被审对象：分支 `agent/v4/b04`，commit `3d490f5c2c20a80ce61e3d0463bdfeafa3ac977d`（feat(v4): B04 视觉资源基线采集）
- 卡片：`v4/04_tasks/cards/V4-B04.md`（verification · normal · 独立审查 1 位 · HEAVY=True）
- 审查方式：只读复核 + 活栈只读 GET 复现（未改动被审交付物）

## 总裁决

**PARTIAL 成立，为合法交付（verdict: ACCEPT_AS_PARTIAL）。**

理由：交付自始至终如实标注降级渠道与 NOT_RUN 面；三项验收映射与证据一一对应、无夸大；两项"发现"（Flutter Web 构建债务、/docs 自我 CSP 冲突）均经本审查独立复现为真；无新增回归；V3 B-04 既有证据未触碰；红线（不手改生成文件/产品码）被遵守而非绕过。产品 UI dialog/sheet 顶层截图缺位已在 limitations #1/#2 如实归因并给出补采路径，属于诚实降级而非验收阈值下调。

## 逐项核验结果

### 1. 降级诚实性（web-admin 渠道声明 vs 构建失败证据）— PASS

- 抽验 `build_logs/flutter_build_web_release_FAIL.log.txt`：L224-L235 原文为 dart2js/CFE 三处 `Error: The integer literal ... can't be represented exactly in JavaScript`，行号与字面量逐一为 `cached_list_snapshot.g.dart:19:8`（-3993110354800439673）、`:49:12`（-5780496603892815176）、`:62:11`（1681328346514525477）。**「3 处 64-bit int 字面量被 dart2js 拒绝」与日志原文、行号完全一致。**
- 与仓内已提交生成文件比对（`mobile/lib/core/offline/models/cached_list_snapshot.g.dart`，git tracked）：L19/L49/L62 实际内容与三处错误逐一吻合（Isar CollectionSchema/IndexSchema 的 64-bit hash id）。归因真实，非臆造。
- `flutter_run_web_debug_FAIL.log.txt` 同样出现同三处错误（RUN_EXIT:1）；`flutter_build_web_release_first_FAIL.log.txt` 为首次 release 尝试完整日志（428 行，同因）。三条路径同因失败成立。
- 修复属生成文件/产品码红线外，交付方未手改、以降级渠道举证——处置正确。

### 2. 截图真实性 — PASS

- **sha256 复算：5/5 全部匹配**（`shasum -a 256 screenshots/*.png` 与 `screenshots_sha256.txt`、run_manifest.json 三方一致）。
- 目检抽验 3 张（超出要求的 2 张）：
  - `02_fastapi_docs_top.png`：Sparkle 1.0.0 / OAS 3.1 / openapi.json / 折叠端点列表，与声明 route `http://127.0.0.1:8000/docs` 内容相符；
  - `05_gateway_metrics_top.png`：Prometheus 文本面，`go_info{version="go1.25.7"}` 等运行时指标可见，与声明相符；
  - `03_fastapi_docs_endpoint_panel_expanded.png`（加验）：GET / Root 面板展开，Parameters/Responses/200/schema 像素可见，与 `capture_results_expand_check.json`（is-open=true、body 578px、textSample）相互印证。
- **guest JWT 脱敏复核：全证据包 `grep -rn "eyJ"` 零命中**；目检截图无 URL/header/页面 token 明文；`guest_auth_evidence_redacted.json` 仅记形状（access_len_431/refresh_len_432/token_type）。脱敏声明成立。

### 3. 参考图隔离 — PASS

- `v4/02_design/REFERENCE_ONLY.jpg` 实测 sha256=`0ca7299bc7f4105ec340eba64cc29e2a0dee456f22fa513ccce25f979eedc422`，与 resource_inventory.json 登记一致；登记字段 `status=PROPOSED`、`rights=UNKNOWN_REFERENCE_ONLY`、`ship_in_product=false` 齐备。
- 物理隔离核实：`v4/evidence/V4-B04/screenshots/` 内仅 5 png + 3 txt，**无任何 jpg/参考图**；REFERENCE_ONLY.jpg 仅存在于 `v4/02_design/`。
- coordinator 指定路径 `…/sparkle-cosmos/picture/ui设计/` 本审查实测不存在（`ls` 无 picture/ 目录），NOT_PRESENT 登记属实。
- **「9=canonical surfaces 非图数」澄清已写清**：在 resource_inventory.json `naming_clarification`、diff_or_evidence_only.md 发现#3、test_results.json T11 三处一致表述，且与 `scripts/devtools/visual_baseline/states.py` docstring（"9 surfaces"）及 `naming.SURFACES` 事实相符。

### 4. /docs CSP 发现 — PASS（发现为真；证据自足性见 CHALLENGED C2）

- 本审查对活栈独立复现（只读 GET）：`http://127.0.0.1:8000/docs` 响应头 `content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; …` **不含 cdn.jsdelivr.net**，而页面 HTML 引用 `https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css` 与 `…swagger-ui-bundle.js` 两项资产。CSP 拦截其自身引用的 CDN 资产、页面对普通访客无法渲染——**断言为真**。
- 「本地逐字节相同副本」：审查实测 `/tmp/b04_capture/assets/` 两份本地副本与本次新下载的 CDN 原件 sha256 完全一致（swagger-ui.css `1ac324f7dcd27e4b…`、swagger-ui-bundle.js `62df541529080464…`，字节数 186154 / 1585988 一致）。旁路声明（setBypassCSP + 仅替换 CDN 资产、页面 HTML 与 /openapi.json 未改）与 `capture2/3/4.js` 实现相符，且「截图不反映真实访客开箱所见」的反向声明已在 limitations #6 诚实写明。

### 5. HEAVY 纪律 — PASS

- run_manifest.json `heavy_discipline` 记录单 HEAVY 预约、`pgrep -fl 'qemu|emulator|gradle'` 开工前及每次重操作前无命中；三次 Web 构建为同一操作的诊断闭环、无并行第二重操作；模拟器未启动的归因（无 adb、5 分钟窗口不可行）已登记。
- 审查时点复跑 pgrep：无命中（exit 1）；`which adb` 不存在——与声明一致的现状佐证。
- 卡片第三条验收「profile 帧记录与截图检查分开」：本卡零帧率声称，无混记，成立。

## 验收映射复核（卡片三条 vs acceptance_mapping）

| 卡片验收 | 交付裁决 | 审查意见 |
| --- | --- | --- |
| 参考图标 PROPOSED；真实基线截图有 build/route/设备 | PASS（部分渠道） | route/DPR/设备/渠道齐备；build 维度以 FAIL 证据本身充当并如实声明——可接受 |
| 背景 RepaintBoundary 误捕获能失败，弹层内容可见 | PARTIAL（机制对照） | 折叠 0px/无 body → 仅背景采集必然 FAIL 的负对照 + 展开 578px 正对照成立；产品 UI 弹层 NOT_RUN 已归因，不冒充等价 |
| profile 帧记录与截图检查分开；一次仅一个 HEAVY | PASS | 见第 5 节 |

## CHALLENGED 列表（均为非阻塞，不推翻 PARTIAL 成立）

- **C1（证据归因轻缺陷）**：`flutter build web --debug`（manifest commands #6、test_results T06）与 `flutter run -d web-server` 共用同一份日志 `flutter_run_web_debug_FAIL.log.txt`，该日志内容仅含 `flutter run` 输出（"Launching lib/main.dart on Web Server in debug mode…"）；`--debug` 单独调用的失败无专属日志，T06 中「--enable-asserts -O1」flags 在任何日志中不可见。核心降级结论不受影响（release 与 run 两路已足证同因），但后续多模式构建应逐命令留独立日志。
- **C2（证据自足性缺口）**：「本地副本与 CDN 逐字节相同」的**声明为真**（本审查已复现 sha256 一致），但证据包内**没有在案的 hash 对照记录**；证明材料（本地副本）存于会话临时目录 `/tmp/b04_capture/assets/`，按仓库规范不入库、随临时目录失存。建议补一份 `viewer_assets_sha256.json`（本地 sha256 + 抓取时间 + CDN URL）入证据包，或在债务/后续卡中转登。
- **C3（瑕疵，装饰性）**：`resource_inventory.json` `generated_at` 记为 `2026-09-28T09:15:00Z+08:00`——Z 与 +08:00 并用，时区记法非法（按文件 mtime 推断本意为 17:15 +08:00 / 09:15Z）。
- **C4（瑕疵，装饰性）**：入库的 `capture_script_reference.js` 为早期版本（目标 guest 面板、产物名 `03_fastapi_docs_guest_endpoint_expanded.png`），与最终 `capture4.js` 流程（首可见端点 GET /）不一致；差异已在 limitations #7 如实披露，但"reference"命名易误导为最终脚本，建议注明版本关系。

## 附带核实

- commit `3d490f5c` 内容与 diff_or_evidence_only.md 差量清单一致：仅 `v4/evidence/V4-B04/**` 新增 + `v4/04_tasks/tasks.json` B04 条目（implementation_state→REVIEW_READY、evidence_pointer/note 如实含 NOT_RUN 声明、assigned_session=wtB04）。
- V3 B-04 证据（v3-output/B-04/ 27 张）未在任何被审变更中出现，no_duplicate_rule 遵守。
- 交付物五件套（diff_or_evidence_only.md / run_manifest.json / test_results.json / review_receipt.json / limitations.md）齐备；review_receipt.json 占位 reviewer 字段由本审查会话覆写。

## 结论

V4-B04 以 PARTIAL 交付：web-admin 渠道基线 + 资源盘点 + 两项既有债务的构建/运行时证据 + 机制等价对照，全部经独立复现核实，降级与脱敏声明诚实。**ACCEPT_AS_PARTIAL**；CHALLENGED C1/C2 建议随补采卡或债务卡落实（不阻塞本卡流转）。产品 UI dialog/sheet 顶层截图为遗留 NOT_RUN 项，待生成文件债务修复后补采。
