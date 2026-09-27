# WT787 审计核验实录（notes）

- 审计对象：v3/V3-COMPLETE-STATUS-FOR-V4.md @ main 16ac17b4（「state(fleet): 轮#274 v0.6 达成 13/13 线+看门狗上岗+补位 wt786/787」）
- worktree：/Users/brsama/code/GitHub/Sparkle-sysrev/wt787-docaudit，分支 agent/node-b/wt787/docaudit
- 结论文件：同目录 report.md（34 条：缺口 11/矛盾 11/断链 4/可用性 8；P0=5/P1=14/P2=15）

## 核验命令与结果（按执行顺序）

1. `git log --oneline -1`（Sparkle-project）→ 16ac17b4 ✓ 符合任务前提。
2. `git worktree add -b agent/node-b/wt787/docaudit .../wt787-docaudit main` ✓
3. 文档 147 行，全文通读。
4. **被引路径存在性（ls/find）**：14/14 存在——v3-output/WT759-RECON/report.md、WT769-DOC-BC/{B,C}-line.md、WT774-DOC-AJ/{A,J}-line.md、WT770-DOC-MX/{M,X}-line.md、WT776-DOC-DE/{D,E}-line.md、WT775-DOC-UPSG/U-line.md、WT779-DOC-OQ/{O,Q}-line.md、WT780-METRICS/metrics.md、WT783-HUMANINBOX/notes.md。
   - **发现**：WT775-DOC-UPSG/ 下另有 P-line.md、S-line.md、G-line.md 存在，主文档 §4 该三线未给路径（report L2）。
5. v3/.sparkle_v3_fleet_state.json 存在 ✓；HUMAN_INBOX 实际路径 v3/08_operations/HUMAN_INBOX.md（文档未给路径）；backend/alembic/versions/wt598_20260927_mastery_audit_effect_kind.py 存在 ✓（「单头」属性未跑 alembic，待核）。
6. ADR-0011：全仓 grep --include=*.md 仅本文档命中 → 仓内无登记文件（report L4）。
7. **tasks.json 机读**：total=107；prefix 14 组（B6,U10,D8,M10,C8,X10,A8,J8,E8,P6,G5,S5,O7,Q8）；stream 14 值（BASELINE/UX/DATA/MEMORY/CONTEXT/ACTION/AURORA/JOURNEY/AI/PROACTIVE/GALAXY/COMMUNITY/OPS/QUALITY）；status=done 102/TODO 5（J-02,E-08,O-01,Q-07,Q-08）。
   - → 文档「13 条产品线」「11/13」错误坐实（report C3）；102/107 坐实（C2）。
8. **FIX 台账（DYNAMIC_ISSUES.md）机读**：物理 407 行；`| V3-FIX-NNN |` 数据行 **362**、号段 1→532、无重号。行首状态机读：FIXED 283（计 OPEN→FIXED 为 288）/OPEN 70~75/CLOSED 3/WONTFIX 1——与文档 §5「FIXED 273」、§9「FIXED 270/OPEN 58」均不一致，计数口径文档未给（report C4）。**「P1 OPEN 仅 FIX-530」机读成立 ✓**（唯一 P1+OPEN=530）。
9. **FIX-53/512 故事复核**：台账 L58 FIX-53 状态格已为 FIXED@10d3d7e8（wt779 纠指补记在案）；L407 FIX-512 行存在且叙事与文档一致 ✓。混合格样例仍见 L65（FIX-61「OPEN 补记FIXED@5236e68d」）——是 C4 计数口径问题的实例。
10. **FIX-498 断链**：`grep "FIX-498"` 台账与全仓均无对应行（命中的 498 均为代码行号/wt498 子串）；台账号段跳号无 498 → report L1。
11. **被引 FIX 号抽样 60+** 全部在台账命中（01/35/36/40/53/193/256/257/258/259/260/275/276/289/290/291/329/330/331/334/356/385/417/418/419/427/439/443/447/449/451/457/461/465/467/469/479/480/482/483/484/487/489/490/491/492/493/495/502/503/504/505/506/507/508/509/510/511/512/513/514/528/530/531/532）✓
12. **SHA 核验（git cat-file -t）**：1680d16c、43942d23、3b5a99bc、f2e9f22e、1e3b6ebf、52fbed29、9a4ea3d4、a1418084、c0306be1、10d3d7e8 全部为 commit ✓；分支 agent/node-b/wt755/slo 存在、938e845c 为其上 commit ✓。
13. **wt755 notes 位置**：main 的 v3-output 无 WT755 目录；`git ls-tree agent/node-b/wt755/slo` 显示分支上有 v3-output/WT755-SLO/ → 文档「wt755 notes 有完整归因」主干不可达（report L3）。
14. **A-08 口径源**：v3-output/WT774-DOC-AJ/A-line.md L146：「accuracy 0.45/0.55/0.45/0.30（full/no_memory/no_experience/fixed_policy）」——主文档 L72 缺臂序/指标名（report G1 修法出处）。
15. **wt759「90 张」出处**：WT759-RECON/report.md L5/L258：90=fleet done 名单时点数（63 字符串+27 dict）→ 主文档 §0 未标时点（已并入 report C2 修法注）。
16. **§9 vs 其引用源**：metrics.md L101/L131/L132/L134/L197 与 §9 的 13,799/746/2,628/70.8% 逐数吻合 ✓；metrics.md L140 台账基线「396 行/351 数据行/至 511」@9a4ea3d4——与 §9「360 条数据行」差异未在文档说明（并入 C4）。
17. **Q-07/Q-08 计划位置**：v3-output/WT779-DOC-OQ/Q-line.md L124（Q-07 执行计划草案）、L135（Q-08 逐 gate 证据图）→ report G10。
18. **H-002/H-009**：v3/08_operations/HUMAN_INBOX.md L12/L19/L21-26 存在且与文档表述一致 ✓；L12 证实 TCC=「阿里云 TCC 开关确认+ZCode 重启（浏览器取凭据前置）」本机权限语义（report G4）。
19. **M1-M4**：全仓 grep 仅本文档与 fleet state json 命中，无定义处（report G7）。
20. **节内算术抽验（全部自洽）**：§3 15+84+1=100；B-01 759=690+55+12+2；D-01 40=29+10+1；J-01 11=5+6；Q-01 260=54+122+84；§9 533+564+38≈113.5 万行；FIXED 270/360=75%；100/107=93.5%。
21. **更新日志时序**：文件序 v0.6→v0.5.1→v0.1→v0.2→v0.3→v0.5→v0.4；时间戳 v0.1=03:00 晚于 v0.2=02:10/v0.3=02:40 → 版本序与时间序矛盾（report C7）。

## FIX-533+ 新缺陷 grep 复核（按纪律只记本 notes）

- `grep -o "V3-FIX-5[3-9][0-9]" DYNAMIC_ISSUES.md` → 仅 530/531/532；
- `grep -rn "FIX-533\|FIX-534\|FIX-535" v3/ --include=*.md --include=*.json` → 0 命中。
- **结论：截至基线 16ac17b4，台账在册最高 V3-FIX-532，无 533+ 新登记。本审计亦未发现需新立 FIX 号的台账级账实不符（FIX-53/512 的纠指故事与台账现状一致）。**

## 待核项（不影响报告结论）

- alembic「单头 wt598_20260927」的「单头」属性需 `alembic heads` 运行级验证（本审计仅验证文件存在）。
- §6「gateway 13 包」的包计数、§9「CI 侧基线 380 平台代际差」成因——未深挖（report G9 已列）。
- 文档时间戳均在 2026-09-28 凌晨，与审计日（09-27/28 之交）的口径以仓库为准，未作为问题立目。

## 纪律遵守

- 未改动主文档 v3/V3-COMPLETE-STATUS-FOR-V4.md、未改动台账、未 push、未碰运行栈与 /tmp/northstar_ns001_real_drive_state.json。
- 全部问题仅评「文档作为唯一信息源的质量」，不含产品价值判断。
