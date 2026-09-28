# 自托管文档资产来源与许可（FIX-559）

本目录资产为 `/docs`（Swagger UI）与 `/redoc`（ReDoc）页面自托管副本，
替换原先引用的 jsdelivr CDN 外链——CDN 资产被本应用 CSP
（`script-src`/`style-src 'self'`）拦截（FIX-559）。sha256 以 `shasum -a 256`
记录如下，其中 swagger-ui 两件资产与 V4-B04 旁路采集时逐字节核验的
本地副本 sha256 一致（见 `v4/evidence/V4-B04/`）。

| 文件 | 来源（jsdelivr） | 解析版本 | sha256 | 上游许可 |
| --- | --- | --- | --- | --- |
| swagger-ui.css | npm/swagger-ui-dist@5 | 5.33.0 | `1ac324f7dcd27e4b9386b4bd6421271ec147e922a22c05ba24b11515e9aa6321` | Apache-2.0 |
| swagger-ui-bundle.js | npm/swagger-ui-dist@5 | 5.33.0 | `62df541529080464a7660adc793eab7128c6193ce3be24ddc1e0e0a4a63edc2f` | Apache-2.0 |
| redoc.standalone.js | npm/redoc@2 | 2.5.4 | `dcaf76612bc4a3fbcc923a8966dee2f6146a5f32e5ce1b6f02dd60cbbf89500b` | MIT |
| favicon.png | fastapi.tiangolo.com/img/favicon.png | — | `d16f72cf5a2773eba499cc7f3db1923c6f5f73de990f739e3a05806aafec15b7` | MIT |

非 CDN 副本（本仓库手写，非第三方分发物）：

| 文件 | 说明 |
| --- | --- |
| swagger-init.js | Swagger UI 初始化脚本（自上游内联模板外置，见 FIX-559） |

更新方法：替换对应文件后刷新本表 sha256；若 swagger-ui/redoc 升级引入
模板行为变化，同步核对 `backend/app/api/docs_pages.py` 页面模板与
`swagger-init.js` 的初始化参数。
