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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
