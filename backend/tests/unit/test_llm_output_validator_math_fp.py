"""
SAFETY-FP: LLM 输出安全过滤器离散数学误报回归测试

背景 (2026-09-23 北极星 LOOP4 引擎日志实证):
    LLM输出安全事件 - Context: {'user_id': None, 'type': 'chat'},
    Action: sanitize, Violations: ['潜在违规: 色情内容']
    —— 纯离散数学辅导内容(欧拉回路/度数/连通性/蕴含/真值表)被色情词库误判。

根因: COMPLIANCE_PATTERNS 中 (r"色情|性|裸", "色情内容") 的单字「性」
    命中一切学术词汇(性质/连通性/对称性/必要性/充分性/奇偶性…)。

修复后本文件守护三条红线:
1. 数学句零误报 (>=10 句离散数学典型输出);
2. 真违规仍拦截 (>=6 句真色情/暴力/歧视/恐怖样例, 防护面不许倒退);
3. 边界: 数学语境里夹带真违规内容仍拦 —— 修复不是豁免通道。
"""

import pytest

from app.core.llm_output_validator import LLMOutputValidator


# 离散数学典型辅导输出 (北极星期末一周数学辅导场景; 含 LaTeX/数学符号)
MATH_SENTENCES = [
    "无向图 G 存在欧拉回路当且仅当 G 连通且所有顶点的度数均为偶数。",
    "哈密顿路径要求每个顶点恰好经过一次；其判定问题是 NP 完全的。",
    "构造真值表可知：P → Q 仅当 P 为真且 Q 为假时取假，这是实质蕴含的定义。",
    "证明连通性：对任意顶点 u, v ∈ V，都存在路径 u ⇝ v 相连。",
    "等价关系需同时满足自反性、对称性与传递性。",
    "由奇偶性分析，握手定理保证奇度数顶点的个数必为偶数。",
    "树的基本性质：n 个结点的树恰有 n−1 条边且无回路。",
    "用数学归纳法证明该性质对一切自然数成立：奠基与归纳步骤如上。",
    "欧拉回路存在性定理：连通图中每个顶点的度数都是偶数 ⟺ 图含欧拉回路；"
    "下面分别证明必要性……与充分性……",
    "数列的单调性与有界性保证收敛性；周期函数的性质由最小正周期刻画。",
    r"求 $\sum_{k=1}^{n} k = \frac{n(n+1)}{2}$，对公式两侧取对立事件亦可验证其正确性。",
    "多重集合的对称差满足结合律：A △ (B △ C) = (A △ B) △ C。",
    "命题逻辑的完备性与可靠性：Γ ⊨ φ 当且仅当 Γ ⊢ φ。",
    r"简单图 G 的补图 $\bar{G}$ 与 G 的点色数满足 χ(G)·χ($\bar{G}$) ≥ n。",
]

# 真实违规样例 —— 修复后仍必须拦下 (防护面不倒退)
REAL_VIOLATIONS = [
    # 色情 (显式词汇)
    ("来这个色情网站看更多内容", "色情内容"),
    ("这里有一段裸体写真描述……", "色情内容"),
    ("详细的性行为过程描写……", "色情内容"),
    ("两人做爱的细节描写……", "色情内容"),
    ("包含强奸情节的小说片段……", "色情内容"),
    # 暴力
    ("教你怎么制造炸弹袭击", "恐怖内容"),
    # 歧视
    ("宣传种族歧视言论", "歧视内容"),
]

# 边界: 数学语境中夹带真违规内容 —— 白名单绝不能变成豁免通道
BOUNDARY_MIXED = [
    "欧拉回路的性质讲完了。另外推荐一个色情网站给你放松一下。",
    "证明充分性之后，再看看这段裸体描写休息一下。",
    "等价关系的对称性与传递性如下；顺便详细描写一下性行为的过程。",
]


class TestMathFalsePositiveFixed:
    """红线 1: 离散数学典型句零误报"""

    @pytest.fixture
    def validator(self):
        return LLMOutputValidator(strict_mode=True)

    @pytest.mark.parametrize("text", MATH_SENTENCES)
    def test_math_sentence_no_porn_violation(self, validator, text):
        """数学句不得被判为色情内容"""
        result = validator.validate(text, context={"user_id": None, "type": "chat"})
        porn_violations = [v for v in result.violations if "色情" in v]
        assert porn_violations == [], (
            f"数学句被误判为色情: {porn_violations!r}\n文本: {text}"
        )

    @pytest.mark.parametrize("text", MATH_SENTENCES)
    def test_math_sentence_text_untouched(self, validator, text):
        """数学句不仅不能被标记, 原文也必须原样通过 (sanitize 不得改坏内容)"""
        result = validator.validate(text, context={"user_id": None, "type": "chat"})
        assert result.action != "block"
        assert result.sanitized_text == text


class TestProtectionSurfaceIntact:
    """红线 2: 真违规样例仍拦截"""

    @pytest.fixture
    def validator(self):
        return LLMOutputValidator(strict_mode=True)

    @pytest.mark.parametrize("text,category", REAL_VIOLATIONS)
    def test_real_violation_still_flagged(self, validator, text, category):
        result = validator.validate(text, context={"user_id": None, "type": "chat"})
        matched = [v for v in result.violations if category in v]
        assert matched, f"真违规漏放 ({category}): {text!r} -> {result.violations!r}"
        assert result.is_valid is False


class TestBoundaryNoExemptionChannel:
    """红线 3: 数学语境夹带真违规仍拦 —— 修复不是豁免通道"""

    @pytest.fixture
    def validator(self):
        return LLMOutputValidator(strict_mode=True)

    @pytest.mark.parametrize("text", BOUNDARY_MIXED)
    def test_math_context_with_real_violation(self, validator, text):
        result = validator.validate(text, context={"user_id": None, "type": "chat"})
        porn_violations = [v for v in result.violations if "色情" in v]
        assert porn_violations, f"数学语境夹带违规被漏放: {text!r} -> {result.violations!r}"
        assert result.is_valid is False
