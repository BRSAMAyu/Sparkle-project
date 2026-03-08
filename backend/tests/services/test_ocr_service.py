import base64
from unittest.mock import AsyncMock

import pytest

from app.services.ocr_service import OCRService


@pytest.mark.asyncio
async def test_ocr_from_base64_delegates_to_ocr_from_url():
    service = OCRService()
    service.ocr_from_url = AsyncMock(return_value="recognized text")

    result = await service.ocr_from_base64("YWJjMTIz")

    assert result == "recognized text"
    service.ocr_from_url.assert_awaited_once_with("YWJjMTIz")


def test_build_payload_preserves_data_uri():
    service = OCRService()

    payload = service._build_payload(
        "data:image/png;base64,YWJjMTIz",
        need_layout_visualization=True,
        return_crop_images=False,
    )

    assert payload["model"] == service.model
    assert payload["file"] == "data:image/png;base64,YWJjMTIz"
    assert payload["need_layout_visualization"] is True
    assert payload["return_crop_images"] is False
    assert payload["request_id"].startswith("ocr_")


def test_build_payload_wraps_raw_base64_as_data_uri():
    service = OCRService()
    raw_png = base64.b64encode(b"\x89PNG\r\n\x1a\nfakepng").decode("utf-8")

    payload = service._build_payload(raw_png)

    assert payload["file"] == f"data:image/png;base64,{raw_png}"


def test_extract_text_prefers_markdown_results():
    service = OCRService()

    text = service._extract_text(
        {
            "md_results": "# Title\nBody text",
            "layout_details": [[{"index": 2, "content": "fallback"}]],
        }
    )

    assert text == "# Title\nBody text"


def test_extract_text_falls_back_to_layout_details():
    service = OCRService()

    text = service._extract_text(
        {
            "layout_details": [
                [
                    {"index": 2, "content": "Second"},
                    {"index": 1, "content": "First"},
                ],
                [
                    {"index": 1, "content": "Page two"},
                ],
            ]
        }
    )

    assert text == "First\nSecond\n\nPage two"
