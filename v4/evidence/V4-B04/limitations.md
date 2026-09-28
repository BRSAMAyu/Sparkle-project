# V4-B04 — limitations

## 渠道限制（如实声明）

1. **产品 UI 现状截图缺位**：卡片要求的「当前实际路由含 dialog/sheet 顶层」在**产品 UI 层**未采集。归因：Flutter Web 在本 SHA 全模式构建失败（见 build_logs/），Android 模拟器路径不可用（无 adb CLI、无 qemu 进程、无既有 AVD 证据，评估 5 分钟窗口不可行）。已按授权降级 web-admin 面采集并全程标注渠道。产品 UI 基线截图需在生成文件债务修复后补采（建议随 V4-F05 style-preview/HEAVY 卡或独立债务卡）。
2. **dialog/sheet 顶层验收以机制对照替代**：「背景误捕获能失败、弹层内容可见」用 Swagger 面板的折叠/展开做了可失败性对照（折叠 0px → 检查必然 FAIL；展开 578px 内容可见）。这不是产品 dialog/sheet 的等价验证；产品弹层的 RepaintBoundary 边界行为仍属 NOT_RUN。
3. **build/route/设备 三要素的 build 维度**：被采集面（FastAPI/网关）是已运行服务，无本次构建产物可标；Flutter 侧 build 维度记录的是失败证据（构建模式、SDK 版本、exit code、错误行），不是成功构建 ID。
4. **DPR/字号**：DPR=2、viewport 1280×800 属采集浏览器事实；应用内字号缩放设置未被触及（渠道限制），字号记录为浏览器默认 16px root。
5. **运行栈 SHA 归属为推断**：网关/engine 进程启动于本 worktree 创建前（09:55 vs 17:0x），无法从进程回溯精确构建 SHA；记录为「Sparkle-project main @3c4618cc 时代」的如实推断。
6. **自动化旁路的存在**：/docs 采集使用 setBypassCSP + CDN 资产本地替换（逐字节相同副本）。页面 HTML、/openapi.json、交互均来自活引擎，但该旁路意味着截图不反映「真实访客开箱所见」（真实访客见到的是被 CSP 拦截的空白 UI——这本身是发现 #2）。
7. **Swagger 端点列表渲染不全**：901 path 的 spec 在 headless 渲染中仅稳定呈现前 10 个 opblock；展开正/负对照取首个可见端点（GET / Root）而非 guest 端点。guest 端点的存在性与可用性以 API 层证据（curl 200）与 spec 路径清单佐证。
8. **guest token 脱敏**：响应形状已记录（access/refresh 长度、token_type），token 本体不入任何交付物。

## 不构成限制的声明

- HEAVY 单槽纪律全程保持（无并行重操作；三次构建失败为同一操作的重试闭环）。
- V3 B-04 证据未重置、未重跑；无第二截图权威被制造。
- 所有 FAIL 均保留原始日志，未删断言、未降阈值。
