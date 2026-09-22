# deploy/ — 部署物料

> 仓库部署相关产物的登记目录。规则：纯静态、零构建；会话产物/运行时数据不入本目录。

## 文档清单

| 条目 | 用途 | 说明 |
|---|---|---|
| `landing/` | 扫码落地页（D-LANDING 卡交付） | 单文件静态页 + 海报文案稿，见下 |

## landing/ — 扫码落地页 + 海报文案

- `landing/index.html` — 自包含单文件落地页（内联 CSS/JS，零外链依赖，离线可开，移动优先）。参展前只需改文件内 `CONFIG` 块（APK 直链/二维码图/联系方式占位/渠道文案）。
- `landing/poster-copy.md` — A2 竖版海报文案稿（主标语 3 选 + 副标 + 三特性 + 扫码引导语），供设计组出图。

### 部署说明（二选一，均零构建）

1. 任意静态服务器（最快验证）：

   ```bash
   cd deploy/landing && python3 -m http.server 8090
   # 浏览器开 http://localhost:8090 ；手机同一局域网访问 <本机IP>:8090 可验扫码链路
   ```

2. nginx（生产，挂在现有网关旁）：

   ```nginx
   location /landing/ { alias /srv/sparkle/landing/; index index.html; }
   # 二维码指向 https://<域名>/landing/?src=<渠道码>
   ```

### 渠道码纪律

每个渠道独立二维码，均指向本落地页，用 `?src=` 区分来源（如 `?src=expo0926`）；页面按 `CONFIG.channelCopy` 显示渠道专属文案。依据：`v3-output/DL-D-R1/GROWTH_ASSETS.md` §1.2。
