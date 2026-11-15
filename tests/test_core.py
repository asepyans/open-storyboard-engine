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


def test_visual_style_profile_adds_cinematic_prompt_details():
    data = build_storyboard(
        "Seekor hiu berenang di laut dalam.",
        20,
        10,
        "Megalodon",
        style="cinematic documentary",
        aspect_ratio="16:9",
        mood="ominous",
        lighting="volumetric blue light",
        palette="deep navy and amber",
        shot_types=["wide establishing shot", "close-up"],
    )
    scene = data["scenes"][0]
    assert data["visual_profile"]["style"] == "cinematic documentary"
    assert data["visual_profile"]["aspect_ratio"] == "16:9"
    assert "cinematic documentary" in scene["visual_prompt"]
    assert "16:9" in scene["visual_prompt"]
    assert "volumetric blue light" in scene["visual_prompt"]
    assert "deep navy and amber" in scene["visual_prompt"]
    assert scene["shot_type"] == "wide establishing shot"


def test_invalid_aspect_ratio_rejected():
    with pytest.raises(ValueError):
        build_storyboard("Narasi.", aspect_ratio="4:3")


def test_invalid_shot_types_rejected():
    with pytest.raises(ValueError):
        build_storyboard("Narasi.", shot_types=[])
