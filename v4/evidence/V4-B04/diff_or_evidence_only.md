# V4-B04 — diff_or_evidence_only

## 结论一句话

本卡零产品码 diff，纯证据交付：活栈视觉基线以降级渠道（web-admin）完成采集；产品移动端 UI 的 Web 渲染通道在本 SHA 被既有生成文件债务阻断（三份构建失败日志为证）；参考图与现状截图物理隔离；V3 B-04 既有证据未触碰。

## 差量明细（相对 base 3c4618cc）

新增文件全部位于 `v4/evidence/V4-B04/`：

- `healthz_before.json` / `healthz_before_capture.json` — 采集前后网关健康证据
- `resource_inventory.json` — mobile/assets（48 文件 155MB：45 audio + 2 icons + 1 images）、tokens_v2 运行时 6 文件、golden/emulator 工具盘点、参考图定位（NOT_PRESENT + 仓内 REFERENCE_ONLY.jpg 登记）
- `screenshots/01..05*.png` + 3 份文本转储 + `screenshots_sha256.txt` — 活栈截图（渠道、DPR、设备、route 见 run_manifest.json）
- `guest_auth_evidence_redacted.json` — guest JWT 通道可用性（token 脱敏）
- `build_logs/` — 三次 Flutter Web 构建失败完整日志（release/debug/run）
- `capture_results_docs_part.json` / `capture_results_expand_check.json` — 程序化 DOM 检查记录
- `run_manifest.json` / `test_results.json` / `diff_or_evidence_only.md`（本文件）/ `limitations.md` / `review_receipt.json`
- `tasks.json` 中 V4-B04 状态字段更新（唯一非 evidence 文件变更）

## 发现（非本卡制造、本卡举证）

1. **Flutter Web 全模式构建 FAIL（既有债务）**：`mobile/lib/core/offline/models/cached_list_snapshot.g.dart`（Hive 生成适配器）含 3 处 64-bit int 字面量（-3993110354800439673 / -5780496603892815176 / 1681328346514525477），dart2js CFE 拒绝（"can't be represented exactly in JavaScript"）。release/debug/`flutter run` 三条路径同因失败。修复属生成文件/产品码（红线外），建议单独债务卡（web 渠道恢复 + wasm 评估）。
2. **FastAPI /docs 自我 CSP 冲突（既有债务）**：引擎响应头 `content-security-policy: script-src 'self' 'unsafe-inline'…` 不含其 HTML 引用的 `cdn.jsdelivr.net`，导致 /docs 与 /redoc 的 UI 资产对任何访客都被浏览器拦截，页面无法渲染（本卡以自动化旁路 + 本地同字节资产副本完成采集，页面 HTML 与活 spec 未改动）。
3. **「9 张参考图」口径澄清**：9 是 `scripts/devtools/visual_baseline/states.py` 的 9 canonical surfaces（home/chat/galaxy/goal/task/settings/profile/memory/onboarding），不是 9 张图。参考图实体仅 `v4/02_design/REFERENCE_ONLY.jpg` 一张（已登记 PROPOSED / UNKNOWN_REFERENCE_ONLY / ship_in_product=false）。指定路径 `…/sparkle-cosmos/picture/ui设计/` 本机不存在（NOT_PRESENT）。

## 差量举证边界

- 未重跑 V3 golden 链路（v3-output/B-04 27 张 sha8=b8c94477 证据原样保留）；未新建第二套截图工具权威；现有 `mobile/test/goldens/b04_visual_baseline/` harness 登记在 resource_inventory.json 供后续卡复用。
- 采集产物无 Mock 冒充：所有截图来自 :8000/:8080 活进程；唯一的自动化旁路（CSP bypass + CDN 资产本地替换）已在 run_manifest.json capture_channel.viewer_plumbing 声明。
