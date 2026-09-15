from app.orchestration.prompts import _SafeFormatDict


def test_safe_format_dict_surfaces_missing_placeholder() -> None:
    rendered = "Hello {name} {missing_key}".format_map(
        _SafeFormatDict(name="Sparkle"),
    )

    assert rendered == "Hello Sparkle {missing:missing_key}"
