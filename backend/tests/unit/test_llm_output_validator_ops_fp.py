"""
SAFETY-OPS: 运维教学句 malicious 层误报修复回归 (强制遮蔽法)

背景 (2026-09-22 SAFETY-OPS 审计):
    MALICIOUS_PATTERNS 末条目 (entry[7], L81) 为 12 字节宽匹配:
    "kill" + 空白 + "-9" + 空白 (掩码形态 ####\\#+-9\\#+)。
    任何含 "kill -9 <空白>" 的文本一律 block —— 运维/操作系统教学场景
    (容器僵死兜底 / SIGKILL 讲解 / pkill / killall) 高频误拦,
    直接打击 CS 学生学操作系统课的北极星场景。
    修后收紧为破坏性目标信号: kill -9 作用于 pid 0/1 或 -1
    (杀 init / 全进程组), 普通进程 PID 教学语境不涉及。

遮蔽纪律:
    本卡涉及的运维命令类为低敏感类别, 载体句允许明文;
    其余 malicious 类别的违规样例一律由模块词表程序化构造 (零明文入库),
    类别名 (desc 标签) 为合规元数据, 非词库词。

本文件守护四条红线:
1. 运维/OS 教学语料 malicious 层零误报 (kill -9/kill -15/pkill/killall/SIGKILL);
2. 破坏性目标 (pid 0/1/-1) 仍拦 —— 收紧不是放行通道;
3. kill 叙述与其他 malicious 词表信号共现仍拦 (程序化构造, 防组合漏放);
4. kill 条目仍留在 malicious 层且锚定破坏性目标 (防整条删除导致漏放)。
"""

import re

import pytest

from app.core.llm_output_validator import LLMOutputValidator

# ---------------------------------------------------------------------------
# 良性运维/OS 教学语料
# 前 8 句为修前实证误报句 (均含 "kill -9" + 空白, 修前 malicious 层必拦);
# 后 4 句为同域回归钉死 (pkill/killall/SIGTERM, 修前即通过)。
# ---------------------------------------------------------------------------
OPS_TEACHING_BENIGN = [
    # --- 修前实证误报句 (SAFETY-OPS 审计, 逐一钉死) ---
    "容器僵死时可以用 kill -9 兜底。",
    "kill -9 是 SIGKILL 信号的命令行写法。",
    "操作系统课讲到 kill -9 与 kill -15 的区别。",
    "排查僵尸进程时, 先用 ps 找 PID, 再用 kill -9 清理。",
    "man kill 文档里写着 kill -9 对应 SIGKILL。",
    "Docker 容器卡死且无法 docker stop 时, 只能 kill -9 处理。",
    "面试高频题: 为什么数据库进程不能随便用 kill -9 呢?",
    "When a process hangs, use kill -9 as the last resort.",
    # --- 同域回归钉死 ---
    "用 pkill -f 匹配命令行批量结束进程。",
    "killall 命令按进程名终止所有同名进程。",
    "SIGKILL 无法被捕获, 服务应优先响应 SIGTERM。",
    "kill -15 发送的是可拦截的 SIGTERM 信号。",
]

# 破坏性目标: 杀 init(pid 1)/全进程(-1)/进程组 0, 无良性教学载体, 必须仍拦
DESTRUCTIVE_TARGETS = [
    "kill -9 1",
    "kill -9 -1",
    "kill -9 0",
    "服务不听话? 直接 kill -9 1 干掉系统第一个进程",
]


def _malicious_hits(validator: LLMOutputValidator, text: str) -> list[str]:
    """只看恶意指令层 (Layer 3) 的违规, 与其它防护层解耦。"""
    result = validator._filter_malicious_instructions(text)
    return list(result.violations)


def _kill_entry_pattern() -> str:
    """取 kill 条目的模式串 (本卡目标条目, 运维命令类低敏感)。"""
    kill_patterns = [p for p, _ in LLMOutputValidator.MALICIOUS_PATTERNS if "kill" in p]
    assert len(kill_patterns) == 1, "malicious 层必须恰有一条 kill 条目"
    return kill_patterns[0]


def _co_occurrence_carriers(validator: LLMOutputValidator) -> list[str]:
    """程序化构造共现样例: 其他 malicious 条目的字面核心嵌入 kill 教学载体句。

    零明文入库 —— 词表词只存在于运行时内存, 不落任何测试/报告文本。
    只保留经真实编译模式验证能独立命中的载波 (自校验)。
    """
    carriers: list[str] = []
    for pat, _desc in LLMOutputValidator.MALICIOUS_PATTERNS:
        if "kill" in pat:
            continue  # 跳过本卡修改的条目本身
        runs = [r for r in re.split(r"[\\(){}\[\]|+*?.^$\s]", pat) if len(r) >= 3]
        for run in runs:
            carrier = f"教学演示: 先 kill -9 结束卡住的进程, 再执行 {run} 破坏整个系统"
            if re.search(pat, carrier, re.IGNORECASE):
                carriers.append(carrier)
                break
    return carriers


@pytest.fixture(scope="module")
def validator() -> LLMOutputValidator:
    return LLMOutputValidator(strict_mode=True)


class TestOpsTeachingZeroFalsePositive:
    """红线 1: 运维/OS 教学语料 malicious 层零误报。"""

    @pytest.mark.parametrize("sentence", OPS_TEACHING_BENIGN)
    def test_ops_teaching_no_malicious_hit(self, validator: LLMOutputValidator, sentence: str) -> None:
        assert _malicious_hits(validator, sentence) == []

    def test_full_pipeline_allows_core_ops_teaching(self, validator: LLMOutputValidator) -> None:
        """全管线 (非仅单层): 教学句必须放行, 不降级为 sanitize。"""
        for sentence in OPS_TEACHING_BENIGN:
            result = validator.validate(sentence)
            assert result.is_valid is True, f"教学句被误处理: {sentence}"
            assert result.action == "allow", f"教学句被降级: {sentence}"

    def test_ops_fp_rate_is_zero(self, validator: LLMOutputValidator) -> None:
        hits = sum(1 for s in OPS_TEACHING_BENIGN if _malicious_hits(validator, s))
        assert hits == 0, f"运维教学语料 malicious 误报 {hits}/{len(OPS_TEACHING_BENIGN)}"


class TestDestructiveTargetsStillBlocked:
    """红线 2: 破坏性目标仍拦 —— 收紧不是放行通道。"""

    @pytest.mark.parametrize("text", DESTRUCTIVE_TARGETS)
    def test_destructive_kill_target_is_blocked(self, validator: LLMOutputValidator, text: str) -> None:
        assert _malicious_hits(validator, text), f"破坏性目标必须拦 (Layer 3): {text}"
        result = validator.validate(text)
        assert result.is_valid is False
        assert result.action == "block"

    def test_generic_pid_kill_is_not_malicious_signal(self, validator: LLMOutputValidator) -> None:
        """普通 PID (任意非 0/1 结尾) 不是恶意信号 —— 防止 [01] 退化成尾字匹配。"""
        for pid in ("5234", "10", "100", "1231", "99991", "$PID", "<pid>"):
            text = f"终止进程: kill -9 {pid}"
            assert _malicious_hits(validator, text) == [], f"普通 PID 不应拦: {text}"


class TestCoOccurrenceStillBlocked:
    """红线 3: kill 叙述与真实恶意信号共现仍拦 (程序化构造, 零明文入库)。"""

    def test_programmatic_co_occurrence_carriers_block(self, validator: LLMOutputValidator) -> None:
        carriers = _co_occurrence_carriers(validator)
        assert len(carriers) >= 2, f"仅 {len(carriers)} 个其他条目可程序化构造共现样例 (需≥2)"
        for carrier in carriers:
            result = validator.validate(carrier)
            assert result.is_valid is False, "共现样例必须拦"
            assert result.action == "block", "共现样例必须 block (恶意层或更严)"


class TestKillEntryShapeGuard:
    """红线 4: kill 条目仍在 malicious 层且职责锚定破坏性目标。"""

    def test_kill_entry_remains_in_malicious_layer(self) -> None:
        pat = _kill_entry_pattern()
        assert "-9" in pat, "kill 条目必须仍锚定 SIGKILL 语义"

    def test_kill_entry_targets_destructive_only(self) -> None:
        compiled = re.compile(_kill_entry_pattern(), re.IGNORECASE)
        assert compiled.search("kill -9 1"), "破坏性目标必须仍在条目职责内"
        assert compiled.search("kill -9 -1"), "-1 (全进程) 必须仍在条目职责内"
        assert not compiled.search("kill -9 5234"), "普通 PID 不再是条目匹配对象"

    def test_malicious_entry_count_unchanged(self, validator: LLMOutputValidator) -> None:
        stats = validator.get_security_stats()
        assert stats["malicious_patterns"] == len(LLMOutputValidator.MALICIOUS_PATTERNS)
        assert stats["malicious_patterns"] > 0
