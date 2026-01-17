"""
测试：文档质量检测 (Phase 5B)

验证质量门禁逻辑的有效性
"""
import pytest
from app.services.document_service import DocumentService, VectorChunk, QualityResult


def test_quality_check_empty_content():
    """测试：空内容应失败"""
    service = DocumentService()

    result = service.check_quality([])

    assert not result.passed
    assert result.score == 0.0
    assert "No text content" in result.issues[0]


def test_quality_check_too_short():
    """测试：内容过短应失败"""
    service = DocumentService()

    chunks = [VectorChunk(content="Hi", page_numbers=[1], section_title=None)]

    result = service.check_quality(chunks)

    assert not result.passed
    assert result.score < 0.5
    assert any("too short" in issue.lower() for issue in result.issues)


def test_quality_check_high_garbled_ratio():
    """测试：高乱码率应失败"""
    service = DocumentService()

    # 创建包含大量替换字符的内容
    garbled_content = "正常文字" + "�" * 50 + "更多文字" + "□" * 30

    chunks = [
        VectorChunk(
            content=garbled_content,
            page_numbers=[1],
            section_title=None
        )
    ]

    result = service.check_quality(chunks)

    assert not result.passed
    assert "garbled" in " ".join(result.issues).lower()


def test_quality_check_clean_document():
    """测试：干净的文档应通过"""
    service = DocumentService()

    clean_content = """
    这是一篇正常的中文文档，包含完整的句子和段落。
    内容清晰，没有乱码，格式良好。

    第二段继续描述文档内容，确保有足够的长度来通过质量检测。
    文档结构合理，符合预期的格式要求。
    """

    chunks = [
        VectorChunk(
            content=clean_content,
            page_numbers=[1],
            section_title="简介"
        ),
        VectorChunk(
            content=clean_content,
            page_numbers=[2],
            section_title="正文"
        )
    ]

    result = service.check_quality(chunks)

    assert result.passed
    assert result.score > 0.7
    assert len(result.issues) == 0


def test_quality_check_academic_document():
    """测试：学术论文应容忍数学符号"""
    service = DocumentService()

    academic_content = """
    Abstract: This paper presents a novel approach to deep learning.
    Introduction: We propose a method based on ∑(x²) and ∫f(x)dx.
    The formula α + β = γ demonstrates the relationship.

    References:
    [1] Smith et al. (2023). DOI: 10.1234/abc
    """

    chunks = [
        VectorChunk(
            content=academic_content,
            page_numbers=[1],
            section_title="Abstract"
        )
    ]

    result = service.check_quality(chunks, doc_type="academic")

    # 学术文档的数学符号不应被认为是乱码
    assert result.passed or result.score > 0.6


def test_quality_check_mixed_language():
    """测试：中英混合文档"""
    service = DocumentService()

    mixed_content = """
    这是一篇中英文混合的文档 (Mixed Language Document)。
    内容包含 Chinese characters 和 English words，这是很常见的场景。

    例如：Machine Learning（机器学习）是一个重要的研究方向。
    Deep Learning（深度学习）更是热门话题。
    """

    chunks = [
        VectorChunk(
            content=mixed_content,
            page_numbers=[1],
            section_title=None
        )
    ]

    result = service.check_quality(chunks)

    assert result.passed
    assert result.score > 0.5


def test_quality_check_repeated_headers():
    """测试：重复的页眉页脚应被检测"""
    service = DocumentService()

    # 模拟带有重复页眉的多页文档
    header = "Document Title - Page Header - Company Name"

    chunks = [
        VectorChunk(
            content=f"{header}\n这是第一页的内容，包含一些有价值的信息。",
            page_numbers=[1],
            section_title=None
        ),
        VectorChunk(
            content=f"{header}\n这是第二页的内容，也包含一些信息。",
            page_numbers=[2],
            section_title=None
        ),
        VectorChunk(
            content=f"{header}\n这是第三页的内容，继续描述。",
            page_numbers=[3],
            section_title=None
        )
    ]

    result = service.check_quality(chunks)

    # 应该检测到重复的页眉页脚
    has_repeat_warning = any(
        "repeated" in issue.lower() or "headers" in issue.lower()
        for issue in result.issues
    )

    # 注意：重复页眉不一定导致失败，只是警告
    assert has_repeat_warning or result.passed


def test_quality_check_table_fragments():
    """测试：表格碎片应被检测"""
    service = DocumentService()

    # 模拟表格解析产生的短切片
    chunks = [
        VectorChunk(content="列1", page_numbers=[1], section_title=None),
        VectorChunk(content="列2", page_numbers=[1], section_title=None),
        VectorChunk(content="123", page_numbers=[1], section_title=None),
        VectorChunk(content="456", page_numbers=[1], section_title=None),
        VectorChunk(content="A", page_numbers=[1], section_title=None),
        VectorChunk(content="B", page_numbers=[1], section_title=None),
    ]

    result = service.check_quality(chunks)

    # 应该检测到过多的短切片
    has_short_chunk_warning = any(
        "short chunks" in issue.lower()
        for issue in result.issues
    )

    assert has_short_chunk_warning or not result.passed


def test_document_type_detection():
    """测试：文档类型检测"""
    service = DocumentService()

    # 学术论文
    academic_chunks = [
        VectorChunk(
            content="Abstract: This paper presents... Introduction: We propose... References: [1] DOI: 10.1234",
            page_numbers=[1],
            section_title=None
        )
    ]

    doc_type = service._detect_document_type(academic_chunks)
    assert doc_type == "academic"

    # 代码文档
    code_chunks = [
        VectorChunk(
            content="def main():\n    import os\n    class MyClass:\n        pass",
            page_numbers=[1],
            section_title=None
        )
    ]

    doc_type = service._detect_document_type(code_chunks)
    assert doc_type == "code"

    # 发票
    invoice_chunks = [
        VectorChunk(
            content="Invoice #12345\nAmount: $100\nTax: $10\nTotal: $110",
            page_numbers=[1],
            section_title=None
        )
    ]

    doc_type = service._detect_document_type(invoice_chunks)
    assert doc_type == "invoice"


def test_quality_check_with_configuration():
    """测试：质量检测使用配置参数"""
    from app.config.phase5_config import phase5_config

    service = DocumentService()

    # 验证配置被使用
    min_length = phase5_config.DOC_QUALITY_MIN_LENGTH

    short_content = "A" * (min_length - 1)

    chunks = [VectorChunk(content=short_content, page_numbers=[1], section_title=None)]

    result = service.check_quality(chunks)

    # 应该因为低于最小长度而失败
    assert not result.passed


def test_quality_check_ocr_confidence():
    """测试：OCR 置信度检测"""
    service = DocumentService()

    # 高置信度 OCR 内容
    high_conf_chunks = [
        VectorChunk(
            content="清晰扫描的文本内容",
            page_numbers=[1],
            section_title=None,
            ocr_confidence=0.9
        ),
        VectorChunk(
            content="更多清晰内容",
            page_numbers=[2],
            section_title=None,
            ocr_confidence=0.85
        )
    ]

    result = service.check_quality(high_conf_chunks)
    # 高置信度应该通过
    assert result.passed

    # 低置信度 OCR 内容
    low_conf_chunks = [
        VectorChunk(
            content="模糊扫描的文本内容",
            page_numbers=[1],
            section_title=None,
            ocr_confidence=0.3
        ),
        VectorChunk(
            content="更多模糊内容",
            page_numbers=[2],
            section_title=None,
            ocr_confidence=0.4
        )
    ]

    result = service.check_quality(low_conf_chunks)
    # 低置信度应该失败或至少有问题
    has_low_conf_issue = any(
        "confidence" in issue.lower() or "ocr" in issue.lower()
        for issue in result.issues
    )
    assert has_low_conf_issue or not result.passed


def test_quality_check_mixed_ocr_non_ocr():
    """测试：混合 OCR 和非 OCR 内容"""
    service = DocumentService()

    chunks = [
        # 非 OCR 内容（原生 PDF 文本）
        VectorChunk(
            content="原生 PDF 文本，高质量",
            page_numbers=[1],
            section_title=None,
            ocr_confidence=None
        ),
        # OCR 内容
        VectorChunk(
            content="扫描页面的 OCR 文本",
            page_numbers=[2],
            section_title=None,
            ocr_confidence=0.8
        ),
        # 低质量 OCR
        VectorChunk(
            content="低质量扫描 OCR 文本",
            page_numbers=[3],
            section_title=None,
            ocr_confidence=0.6
        )
    ]

    result = service.check_quality(chunks)
    # 混合内容应该根据平均置信度评估
    assert result.passed or result.score > 0.5


def test_quality_check_ocr_threshold_config():
    """测试：OCR 置信度阈值配置"""
    from app.config.phase5_config import phase5_config

    service = DocumentService()

    # 创建刚好低于阈值的 OCR 内容
    threshold = phase5_config.DOC_QUALITY_OCR_CONFIDENCE_THRESHOLD
    just_below_threshold = threshold - 0.01

    chunks = [
        VectorChunk(
            content=f"OCR 置信度刚好低于阈值 {threshold:.2f}",
            page_numbers=[1],
            section_title=None,
            ocr_confidence=just_below_threshold
        )
    ]

    result = service.check_quality(chunks)
    # 应该报告 OCR 置信度问题
    has_ocr_issue = any(
        "confidence" in issue.lower() or "ocr" in issue.lower()
        for issue in result.issues
    )
    assert has_ocr_issue or not result.passed


def test_quality_metrics_integration():
    """测试：质量检测与指标集成"""
    service = DocumentService()

    # 创建测试数据
    chunks = [
        VectorChunk(
            content="测试文档内容，足够长以通过长度检查",
            page_numbers=[1],
            section_title=None,
            ocr_confidence=0.9
        )
    ]

    result = service.check_quality(chunks)

    # 验证返回结果结构
    assert hasattr(result, "passed")
    assert hasattr(result, "score")
    assert hasattr(result, "issues")
    assert isinstance(result.issues, list)

    # 验证 score 在 0-1 范围内
    assert 0 <= result.score <= 1

    # 如果是通过的，issues 应该为空
    if result.passed:
        assert len(result.issues) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
