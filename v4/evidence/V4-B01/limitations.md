# V4-B01 限制与未竟事项（如实登记）

## NOT_RUN / BLOCKED

1. **独立审查 NOT_RUN**——按验收模型需未参与会话审查；本卡证据为自证面，review_receipt.json=PENDING。合并前须审查 + 集成 SHA 复验。
2. **产品测试 NOT_RUN**——验证卡无产品代码变更；未跑 backend/gateway/mobile 测试，未跑全量守卫。包自检（validate_pack/43 unittest）仅覆盖 v4/ 包本身。
3. **RF-06 本地深检 NOT_RUN**——本机 sparkle-cosmos 无该分支对象。为守「sparkle-cosmos 一律只读」红线未执行 `git fetch`（fetch 会写 .git/refs 与对象库）；远端核查走 `git ls-remote` + GitHub compare API（只读）。因此 RF-06 补丁与 Sparkle-project main 的**逐行 3-way 冲突模拟未做**，冲突面预判止于文件级同名双改 + 语义同域，实际合并冲突以未来移植卡实测为准。
4. **RF-06 交接文档 SHA 未本地验证**——`8c6b8c17`/`af0ff8fa`/`04214f44`/`e3f85eb3` 均为本机对象库不存在的远端 SHA，其存在性证据来自 GitHub API 与交接文档自述，未逐 commit 拉取核对。
5. **O-01/Q-07/Q-08 不在本卡处置范围**——卡面明示「继承原义务」；三卡状态沿用 TODO，未推进、未阻塞、未重开。

## 口径限制

6. 台账「最终 OPEN=46」是机器重算口径（同号多行取已解行优先）；台账行序非严格追加式，若 Leader 以台账某具体行为准可能得出 ±1~2 差异——与 Q-08 一审勘误的 46 交叉吻合，但不替代 Q-08 终审的权威口径。23 行非标准状态格按 unknown 保留，本卡不代裁。
7. 「SP main mobile/ 近窗 163 commits/690 文件」以 `--since=2026-09-24` 近似 RF-06 分叉窗口（sync 分支名 sparkle-project-20260924@f305e15d；该 SHA 在两仓对象库均不存在，无法精确取 merge-base——两仓不同根，本就不存在 merge-base）。
8. RF-06 mobile/ 差异规模（+635/−649）为 compare API 全量统计的文件级汇总，未做逐 hunk 归类；docs/ 8 文件未逐字审阅。

## 不做声明的面

9. 本卡不宣称：RF-06 视觉验收状态变化、任何产品行为改善、真实设备证据补齐、V4 F 线可开工时间。F 线动 mobile 前以 §3.3 建议与交接文档 §10 为准。
10. 对比度数字（validate_pack 输出的 paper_day/dusk/quiet）是**提案令牌**的包内测量，非产品 UI 实测，勿外推。
