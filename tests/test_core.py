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


def test_scene_intervals_are_contiguous_and_positive():
    result = build_storyboard(
        "A.\n\nB.\n\nC.\n\nD.",
        duration_seconds=4,
        scene_seconds=1,
    )
    scenes = result["scenes"]
    assert len(scenes) <= 4
    assert scenes[0]["start_seconds"] == 0
    assert all(scene["duration_seconds"] >= 1 for scene in scenes)
    assert all(left["end_seconds"] == right["start_seconds"]
               for left, right in zip(scenes, scenes[1:]))
    assert scenes[-1]["end_seconds"] == 4


def test_scene_count_does_not_exceed_duration():
    script = "\n\n".join(f"Paragraph {index} has a few words here." for index in range(20))
    result = build_storyboard(script, duration_seconds=3, scene_seconds=1)
    assert result["scene_count"] <= 3
    assert sum(scene["duration_seconds"] for scene in result["scenes"]) == 3


def test_empty_script_is_rejected():
    with pytest.raises(ValueError):
        build_storyboard("   ")


def test_nonpositive_duration_is_rejected():
    with pytest.raises(ValueError):
        build_storyboard("Some narration.", duration_seconds=0)


def test_nonpositive_scene_target_is_rejected():
    with pytest.raises(ValueError):
        build_storyboard("Some narration.", scene_seconds=0)


def test_markdown_export_contains_scene_content():
    data = build_storyboard("Narasi singkat.", 12, 10, "Demo")
    markdown = export_markdown(data)
    assert "# Demo" in markdown
    assert "**Visual prompt:**" in markdown
