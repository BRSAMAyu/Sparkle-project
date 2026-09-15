from __future__ import annotations

from pathlib import Path

from app.core.ingestion.ingestion_service import IngestionService


def test_process_markdown_extracts_structured_chunks(tmp_path: Path) -> None:
    file_path = tmp_path / "os_notes.md"
    file_path.write_text(
        "# CPU Scheduling\n\n"
        "- Round robin uses a time quantum to rotate running processes fairly.\n\n"
        "## Process States\n\n"
        "When a process is preempted, it moves from Running back to Ready.\n",
        encoding="utf-8",
    )

    chunks = IngestionService().process_file(str(file_path))

    assert len(chunks) == 2
    assert chunks[0].source == "markdown"
    assert chunks[0].metadata.get("title") == "CPU Scheduling"
    assert "Round robin uses a time quantum" in chunks[0].text
    assert chunks[1].metadata.get("title") == "Process States"
    assert "Running back to Ready" in chunks[1].text


def test_process_text_file_is_supported(tmp_path: Path) -> None:
    file_path = tmp_path / "memory_notes.txt"
    file_path.write_text(
        "Virtual memory gives each process an isolated address space.\n\n"
        "Page tables map virtual addresses to physical frames.\n",
        encoding="utf-8",
    )

    chunks = IngestionService().process_file(str(file_path))

    assert len(chunks) >= 1
    assert chunks[0].source == "text"
    assert "isolated address space" in chunks[0].text
