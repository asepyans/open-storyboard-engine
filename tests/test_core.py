import pytest

from storyboard_engine.core import build_storyboard, export_markdown


def test_scene_timing_ends_at_requested_duration():
    result = build_storyboard(
        "Paragraph one contains a few words.\n\nParagraph two has some more words.",
        duration_seconds=40,
        scene_seconds=10,
        title="Test",
    )
    assert result["title"] == "Test"
    assert result["scene_count"] >= 1
    assert result["scenes"][0]["start_seconds"] == 0
    assert result["scenes"][-1]["end_seconds"] == 40
    assert all(scene["duration_seconds"] > 0 for scene in result["scenes"])


def test_empty_script_is_rejected():
    with pytest.raises(ValueError):
        build_storyboard("   ")


def test_nonpositive_duration_is_rejected():
    with pytest.raises(ValueError):
        build_storyboard("Some narration.", duration_seconds=0)


def test_markdown_export_contains_scene_content():
    data = build_storyboard("Narasi singkat.", 12, 10, "Demo")
    markdown = export_markdown(data)
    assert "# Demo" in markdown
    assert "**Visual prompt:**" in markdown
