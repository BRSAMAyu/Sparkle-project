import pytest

from app.services.galaxy.rag_router import RagRouter


def test_rag_router_short_query():
    router = RagRouter()
    strategy = router.select("hi")
    assert strategy.name == "short_query"
    assert strategy.enable_hyde is False
    assert strategy.enable_graph is False


def test_rag_router_keyword_trigger():
    router = RagRouter()
    strategy = router.select("请分析这个知识点")
    assert strategy.name == "analytical"
    assert strategy.enable_hyde is True
    assert strategy.enable_graph is True


def test_rag_router_default():
    router = RagRouter()
    strategy = router.select("regular query without trigger")
    assert strategy.name == "default"
