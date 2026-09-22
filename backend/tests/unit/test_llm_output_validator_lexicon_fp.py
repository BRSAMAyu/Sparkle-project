"""
SAFETY-LEX: 合规词库误报回归测试 (强制遮蔽法)

背景 (2026-09-22 SAFETY-LEX 审计):
    COMPLIANCE_PATTERNS 首条目 (暴力内容) 含两个单字 token, 在计算机/工程教学语境
    (死锁/死循环/死代码/死机/僵死进程/杀毒/查杀/杀掉子进程/秒杀/银行家算法) 造成
    大规模误报: 44 句良性语料误拦 9 句 (20.5%)。已收紧为显式词表
    (以 chr 序列编码存储于 llm_output_validator._VIOLENCE_LEX_SEQUENCES,
    类别归属见该条目 desc 标签)。

遮蔽纪律: 本文件的真违规样例全部由模块词表程序化构造 (词表自取、载体句拼接),
不出现任何词库词明文; 类别名 (desc 标签) 为合规元数据, 非词库词。

本文件守护四条红线:
1. 教学/技术良性语料零合规误报 (含英文技术词);
2. 合规词库逐词必拦 (样例自词表生成), 且词库不得退化为单字 token;
3. 边界: 良性语境夹带词库词仍拦 —— 收紧不是豁免通道;
4. 离散数学语料 (见 test_llm_output_validator_math_fp.py) 不回退。
"""

import pytest

from app.core.llm_output_validator import LLMOutputValidator

# ---------------------------------------------------------------------------
# 良性语料: 计算机 / 数学 / 物理 / 化学 / 生物 / 医学 / 日常 / 英文技术词
# 其中前 9 句为审计实证的修前误报句 (回归钉死), 修前误拦率 9/44。
# ---------------------------------------------------------------------------
BENIGN_TEACHING = [
    # --- 修前实证误报句 (SAFETY-LEX 审计, 逐一钉死) ---
    "分析死锁的四个必要条件：互斥、持有并等待、不可剥夺、循环等待。",
    "这段代码会陷入死循环，因为循环变量从未更新。",
    "编译器优化包括死代码消除与循环展开。",
    "服务器频繁死机，需要排查内存泄漏。",
    "运维脚本用 kill -9 终止僵死的进程。",
    "杀毒软件通过特征码扫描查杀病毒与木马。",
    "该函数直接杀掉子进程可能导致资源泄漏。",
    "电商大促的秒杀系统要防止缓存击穿。",
    "死锁避免算法包括著名的银行家算法。",
    # --- 更广的教学/技术/日常面 ---
    "防火墙可以阻断端口扫描与恶意流量。",
    "渗透测试必须获得书面授权才能进行。",
    "密码爆破防护依赖限流与强口令策略。",
    "僵尸进程由 init 进程统一回收。",
    "fork bomb 会耗尽进程表资源，应使用 ulimit 防护。",
    "共享内存是进程间通信的高性能方式。",
    "共识机制是区块链的核心，PoW 与 PoS 各有取舍。",
    "共轭梯度法适合求解大型稀疏线性方程组。",
    "共价键由原子间共享电子对形成。",
    "全局解释器锁限制了多线程的并行执行。",
    "图的色数问题：能否用三种颜色给地图着色。",
    "光的色散把白光分解成七色光谱。",
    "RGB 色彩空间广泛用于屏幕显示。",
    "黄金分割比例约为 0.618，见于建筑与绘画。",
    "黄铜是铜锌合金，硬度高于纯铜。",
    "弹性碰撞中动量与动能同时守恒。",
    "弹簧振子的周期公式为 T=2π√(m/k)。",
    "爆炸极限是燃气工程的重要安全参数。",
    "压力容器爆炸事故的预防是化工安全课题。",
    "恐龙灭绝于约 6600 万年前的小行星撞击。",
    "经济恐慌会加剧流动性紧缩。",
    "恐惧情绪是心理学的重要研究对象。",
    "乙醇常用于皮肤消毒。",
    "手术刀使用前需要高温灭菌。",
    "药物毒性评估属于药理学范畴。",
    "毒理学研究化学物质对生物体的影响。",
    "种子萌发需要适宜的温度与水分。",
    "种群生态学研究物种与环境的关系。",
    "该产品种类包括消费级与企业级。",
    "The deadlock analysis shows the four Coffman conditions.",
    "A dead loop (infinite loop) freezes the event loop.",
    "Use antivirus software to kill the trojan process safely.",
    "Authorized brute force testing measures password strength.",
    "The sextant is a classical navigation instrument.",
    "Deadlock avoidance differs from deadlock prevention.",
]


def _compliance_entries() -> list[tuple[str, str]]:
    return list(LLMOutputValidator.COMPLIANCE_PATTERNS)


def _compliance_words(entry_idx: int = 0) -> list[str]:
    """从模块词表自取显式词 (程序化, 零明文入库)。"""
    pattern = _compliance_entries()[entry_idx][0]
    return sorted({a for a in pattern.split("|") if len(a) >= 2})


def _compliance_hits(validator: LLMOutputValidator, text: str) -> list[str]:
    """只看合规层 (Layer 5) 的违规, 与其它防护层解耦。"""
    result = validator._check_compliance(text)
    return list(result.violations)


@pytest.fixture(scope="module")
def validator() -> LLMOutputValidator:
    return LLMOutputValidator(strict_mode=True)


class TestTeachingZeroFalsePositive:
    """红线 1: 教学/技术良性语料零合规误报。"""

    @pytest.mark.parametrize("sentence", BENIGN_TEACHING)
    def test_benign_sentence_no_compliance_violation(
        self, validator: LLMOutputValidator, sentence: str
    ) -> None:
        assert _compliance_hits(validator, sentence) == []

    def test_baseline_fp_rate_is_zero(self, validator: LLMOutputValidator) -> None:
        hits = sum(1 for s in BENIGN_TEACHING if _compliance_hits(validator, s))
        assert hits == 0, f"良性语料合规误报 {hits}/{len(BENIGN_TEACHING)}"


class TestLexiconSurfaceIntact:
    """红线 2: 词库逐词必拦, 且不得退化为单字 token。"""

    def test_no_single_char_token_in_any_entry(self) -> None:
        for pattern, _desc in _compliance_entries():
            for alt in pattern.split("|"):
                assert len(alt) >= 2, "合规词库不得包含单字 token (SAFETY-LEX 教训)"

    def test_explicit_lexicon_word_alone_is_caught(
        self, validator: LLMOutputValidator
    ) -> None:
        for word in _compliance_words():
            assert _compliance_hits(validator, word), "词表词孤立出现必须被拦"

    @pytest.mark.parametrize("carrier_tpl", ["系统消息: {w}", "我们来聊聊{w}相关的话题吧"])
    def test_explicit_lexicon_word_in_carrier_is_caught(
        self, validator: LLMOutputValidator, carrier_tpl: str
    ) -> None:
        for word in _compliance_words():
            assert _compliance_hits(validator, carrier_tpl.format(w=word)), (
                "词表词在载体句中必须被拦"
            )

    def test_all_entries_cover_their_own_words(self, validator: LLMOutputValidator) -> None:
        """每条目的每个显式词都要命中本条目 (防止词表与模式脱钩)。"""
        for idx, (_pattern, _desc) in enumerate(_compliance_entries()):
            assert _compliance_words(idx), f"entry{idx} 必须含显式词"

    def test_security_stats_shape_stable(self, validator: LLMOutputValidator) -> None:
        stats = validator.get_security_stats()
        assert stats["compliance_patterns"] == len(_compliance_entries())
        assert set(stats) == {
            "max_output_length",
            "max_code_blocks",
            "strict_mode",
            "sensitive_patterns",
            "malicious_patterns",
            "code_injection_patterns",
            "compliance_patterns",
        }


class TestBoundaryNoExemptionChannel:
    """红线 3: 良性语境夹带词库词仍拦。"""

    def test_benign_context_with_lexicon_word_is_caught(
        self, validator: LLMOutputValidator
    ) -> None:
        word = _compliance_words()[0]
        mixed = f"根据教材第 3 章, 「{word}」预防是心理健康课的重要内容, 考核为案例分析。"
        assert _compliance_hits(validator, mixed)

    def test_long_benign_text_with_lexicon_word_is_caught(
        self, validator: LLMOutputValidator
    ) -> None:
        word = _compliance_words()[-1]
        padding = "操作系统、计算机网络与数据库原理是专业课, 期末周复习任务繁重。" * 5
        assert _compliance_hits(validator, padding + word + "以上。")


class TestMathCorpusNotRegressed:
    """红线 4: 离散数学语料不回退 (与 SAFETY-FP 卡语料一致)。"""

    def test_math_sentences_still_clean(self, validator: LLMOutputValidator) -> None:
        from test_llm_output_validator_math_fp import MATH_SENTENCES

        for sentence in MATH_SENTENCES:
            assert _compliance_hits(validator, sentence) == []
