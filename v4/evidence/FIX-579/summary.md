# FIX-579 summary — CI perf 阈值环境容差校准（P2）

**结论**：V3-FIX-579 成立并已修（显式治理变更，非静默放宽）。两例已证 flaky 的绝对
perf 阈值断言（galaxy 100 节点布局 <200ms、S01 G+ 语义族滚帧 <70000μs）改为环境感知：
CI 环境（`GITHUB_ACTIONS`）×`kCiPerfTolerance=1.5`，本地 ×1.0 严格口径逐字节不变。
三例数据（CI49 244ms、CI50 70241μs、CI52 81496μs）+ 本地余量 2.4–2.8x + CI/本地比
2.5–2.9x（全矩阵 2.37–3.30x）定性为共享 runner 噪声带环境 flake，非产品回归。

**修法**：`threshold × ((ciEnvironment ?? _runningOnCi) ? 1.5 : 1.0)`——混合式选型：
env 检测可行故缺省走真实检测；`Platform.environment` 只读故正例经 `ciEnvironment:`
参数注入模拟 CI。常量处注释签三例数据+比值依据+日期（2026-09-29）；两文件各新增
一正一反机制测试（正=模拟 CI 放宽界生效并吸收实测峰值，反=严格界逐值等于原阈值且
判别力仍在）。仅动两处已证 flaky 断言；同模式其余阈值 7+ 文件只登记不修
（perf_threshold_candidates.md）。

**验证**：本地两文件各 3 连跑全绿且打印阈值实证严格原值（200ms/70000us，S01 实测
19119–30492μs、galaxy 61–110ms）；两文件 analyze 零；mutation（去 CI 分支恒严格）
→ 两模拟 CI 正例红（300→200、105000→70000）→ 还原绿；`GITHUB_ACTIONS=true` 进程级
e2e → 13+24 全过且阈值实证放宽界（300ms/105000us）。

**移交**：真实托管 runner 下一轮自然运行观察 CI49/50/52 同位置复跑不再红为终证；
候选清单 A 类（galaxy_semantics_perf 50000μs 最优先）待 flake 实证后由 owner 套用
同模式；测量法加固（warm-up/多采样）属 perf 基建卡范畴。台账 V3-FIX-579
OPEN→FIXED@ad1dd9c4（代码修复 commit；分支头含证据与台账闭账）。

证据五件套：run_manifest / verification（含对照表+比值推导+mutation 记录）/
perf_threshold_candidates / limitations / summary。
