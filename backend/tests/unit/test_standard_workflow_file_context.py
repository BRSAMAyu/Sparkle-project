from types import SimpleNamespace

from app.agents.standard_workflow import (
    _first_document_page_number,
    _should_use_slim_standard_context,
)
from app.orchestration.statechart_engine import WorkflowState


def test_standard_chat_with_attached_files_keeps_full_context():
    state = WorkflowState(messages=[{"role": "user", "content": "请总结我上传的文件"}])
    state.context_data = {
        "chat_mode": "standard",
        "file_ids": ["file-1"],
    }

    assert _should_use_slim_standard_context(state, "请总结我上传的文件") is False


def test_first_document_page_number_reads_page_numbers_list():
    chunk = SimpleNamespace(page_numbers=[3, 4], page_number=None)

    assert _first_document_page_number(chunk) == 3
