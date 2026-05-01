from __future__ import annotations

import pytest

from app.config import settings
from app.services.document_service import DocumentService, VectorChunk


@pytest.mark.asyncio
async def test_contextual_embedding_texts_add_context_header_once(monkeypatch):
    service = DocumentService()
    chunks = [
        VectorChunk(
            content="The scheduler runs processes in round-robin order.",
            page_numbers=[12],
            section_title="Chapter 3: CPU Scheduling",
        ),
        VectorChunk(
            content="Shortest job first selects the process with the smallest next CPU burst.",
            page_numbers=[13],
            section_title="Chapter 3: CPU Scheduling",
        ),
    ]

    class FakeLLMService:
        def __init__(self):
            self.calls = 0

        async def chat(self, messages, temperature=0.7, **kwargs):
            self.calls += 1
            assert "OS_Textbook.pdf" in messages[1]["content"]
            return "This is an undergraduate Operating Systems textbook about CPU scheduling algorithms."

    fake_llm_service = FakeLLMService()
    from app.services import llm_service as llm_module

    monkeypatch.setattr(settings, "ENABLE_CONTEXTUAL_CHUNK_ENRICHMENT", True)
    monkeypatch.setattr(llm_module, "llm_service", fake_llm_service)

    texts = await service.build_contextual_embedding_texts("OS_Textbook.pdf", chunks)

    assert fake_llm_service.calls == 1
    assert texts[0].startswith(
        "[From: OS_Textbook.pdf | Section: Chapter 3: CPU Scheduling | "
        "This is an undergraduate Operating Systems textbook"
    )
    assert texts[0].endswith(chunks[0].content)
    assert texts[1].endswith(chunks[1].content)
    assert chunks[0].content == "The scheduler runs processes in round-robin order."


@pytest.mark.asyncio
async def test_contextual_embedding_texts_can_be_disabled(monkeypatch):
    service = DocumentService()
    chunks = [
        VectorChunk(
            content="The scheduler runs processes in round-robin order.",
            page_numbers=[12],
            section_title="Chapter 3: CPU Scheduling",
        )
    ]

    monkeypatch.setattr(settings, "ENABLE_CONTEXTUAL_CHUNK_ENRICHMENT", False)

    texts = await service.build_contextual_embedding_texts("OS_Textbook.pdf", chunks)

    assert texts == [chunks[0].content]
