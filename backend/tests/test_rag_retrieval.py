import pytest
from app.services.rerank_service import RerankService
from unittest.mock import MagicMock

class MockItem:
    def __init__(self, id, name):
        self.id = id
        self.name = name

def test_reciprocal_rank_fusion():
    """测试 RRF 融合算法"""
    service = RerankService()
    
    # 模拟向量检索结果 (ID: 1, 2, 3)
    vector_results = [
        MockItem(1, "Item 1"),
        MockItem(2, "Item 2"),
        MockItem(3, "Item 3")
    ]
    
    # 模拟关键词检索结果 (ID: 3, 1, 4)
    # Item 3 在关键词检索中排名第一，在向量中排名第三 -> 应该获得高分
    # Item 1 在两个列表中都排名靠前 -> 应该获得最高分
    keyword_results = [
        MockItem(3, "Item 3"),
        MockItem(1, "Item 1"),
        MockItem(4, "Item 4")
    ]
    
    # 执行融合
    fused = service.reciprocal_rank_fusion([vector_results, keyword_results], k=1)
    
    # 计算预期分数 (k=1)
    # Item 1: 1/(1+0+1) + 1/(1+1+1) = 0.5 + 0.333 = 0.833
    # Item 3: 1/(1+2+1) + 1/(1+0+1) = 0.25 + 0.5 = 0.75
    # Item 2: 1/(1+1+1) = 0.333
    # Item 4: 1/(1+2+1) = 0.25
    
    # 验证排序
    assert fused[0][0].id == 1  # Item 1 first
    assert fused[1][0].id == 3  # Item 3 second
    
    # 验证分数顺序
    assert fused[0][1] > fused[1][1]
    assert fused[1][1] > fused[2][1]

def test_rrf_empty_lists():
    """测试空列表处理"""
    service = RerankService()
    fused = service.reciprocal_rank_fusion([], k=60)
    assert fused == []

def test_rrf_single_source():
    """测试单源列表处理"""
    service = RerankService()
    results = [MockItem(1, "A"), MockItem(2, "B")]
    fused = service.reciprocal_rank_fusion([results], k=1)
    
    assert len(fused) == 2
    assert fused[0][0].id == 1
    assert fused[0][1] > fused[1][1]
