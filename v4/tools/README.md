# 包工具说明

默认工具仅依赖 Python 标准库；不启动 Agent、不开模型、不变更 Sparkle 仓库。

- `python tools/validate_pack.py`：结构/依赖/模块/场景/原始来源副本/配色数值检查。
- `python -m unittest discover -s tests -v`：离线参考语义与包工具测试。
- `python tools/next_tasks.py`：建议当前可领取任务；不是调度器，不替代已有共享状态和路径锁。
- `python tools/test_design_lab.py`：**可选**，需要 Playwright 与 Chromium。环境变量 `CHROMIUM_PATH` 可指定本地浏览器。仅在浏览器中测试本包HTML草图，截图和JSON写到 evidence/。这不是Flutter测试。

若浏览器不允许 file://，此测试用 set_content 装载同一HTML；页面无远程资源。手动体验可以直接打开HTML，也可以在本目录以 `python -m http.server 8765 --bind 127.0.0.1` 启动仅本地服务后打开 prototype/DESIGN_LAB.html。不要暴露此预览服务到公网。

`packlib.check_receipt` 只核对证据结构、相对路径、哈希和不同会话声明，不能鉴别伪造运行结果；独立审查/实际复跑仍必需。参考代码不是授权、数据一致性或模型效果的完整生产实现。
