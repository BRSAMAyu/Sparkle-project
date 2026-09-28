# V4-B02 局限性

1. **静态分析口径**：入边计数来自源码静态扫描（字符串导航/常量引用/helper 函数/Uri 构造/route 配置/深链表）。运行时动态构造的导航目标（如服务端下发 `destination_route` 字符串经 push_navigation_service 直达任意已注册路由）不产生静态入边——这使 active_entry 判定为下界、registered_no_ui_entry 判定偏保守（"无静态 UI 入边"而非"运行时绝对不可达"）。深链/推送仍可触达 10 条孤儿路由（与 NAV-IA P-3 摘除动机一致）。
2. **未运行 App**：不跑 HEAVY、无模拟器/真机。可达性为"注册+静态入边"证据层级，非截图级运行时证据；无 UI 截图（本卡无可视新产物）。
3. **人工复核抽样制**：6 项静态未达经人工复核重分类（17 项抽样总量）；136 条路由未逐条人核，其余依赖程序化判定（工具链与命令见 run_manifest.json）。
4. **矩阵复核范围**：本卡核验矩阵的"目录集合/路由面/入口锚点"维度；jtbd/journey_map/data_truth 行数据（后端行数、探测结果）不在本卡复测范围（B-01Δ 注明"不碰运行栈"，本卡同样未触碰运行栈）。
5. **行号易腐**：entry_evidence 的 file:line 锚定 @ 3c4618cc；后续改动会使行号漂移（feature 路径锚点不受影响）。
6. **named-route 动态名**：`pushNamed` 仅 2 个名字 7 处调用（community friends 两入口）被捕获；若未来以运行时拼名调用会漏计（当前全库无此模式）。
7. **深链 id-less 歧义（DF-08/09）为静态推演**：`/achievements/milestone` 命中 `/achievements/:id` 的行为依 GoRouter 路径匹配语义推断，未在运行时触发验证；404 兜底（node id-less）由 errorBuilder 存在性推定。
