import csv
from io import StringIO

import pytest

from storyboard_engine.core import VISUAL_PRESETS, build_storyboard, export_csv, export_markdown, export_srt


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
    result = build_storyboard("A.\n\nB.\n\nC.\n\nD.", duration_seconds=4, scene_seconds=1)
    scenes = result["scenes"]
    assert len(scenes) <= 4
    assert scenes[0]["start_seconds"] == 0
    assert all(scene["duration_seconds"] >= 1 for scene in scenes)
    assert all(left["end_seconds"] == right["start_seconds"] for left, right in zip(scenes, scenes[1:]))
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
        preset="documentary",
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


def test_all_named_visual_presets_are_available():
    assert {"documentary", "dark-cinematic", "photorealistic", "2d-animation", "vertical-shorts"} <= set(VISUAL_PRESETS)


@pytest.mark.parametrize(
    ("preset", "expected_style", "expected_ratio"),
    [
        ("documentary", "cinematic documentary", "16:9"),
        ("dark-cinematic", "dark cinematic realism", "16:9"),
        ("photorealistic", "photorealistic documentary photography", "16:9"),
        ("2d-animation", "clean 2D animated illustration", "9:16"),
        ("vertical-shorts", "cinematic vertical documentary", "9:16"),
    ],
)
def test_preset_defaults_are_applied(preset, expected_style, expected_ratio):
    data = build_storyboard("Narasi singkat.", duration_seconds=20, preset=preset)
    profile = data["visual_profile"]
    assert profile["preset"] == preset
    assert profile["style"] == expected_style
    assert profile["aspect_ratio"] == expected_ratio
    assert len(profile["shot_types"]) >= 1


def test_explicit_options_override_preset_values():
    data = build_storyboard(
        "Narasi singkat.",
        duration_seconds=20,
        preset="dark-cinematic",
        style="custom style",
        aspect_ratio="1:1",
        mood="calm",
    )
    profile = data["visual_profile"]
    assert profile["style"] == "custom style"
    assert profile["aspect_ratio"] == "1:1"
    assert profile["mood"] == "calm"
    assert profile["lighting"] == VISUAL_PRESETS["dark-cinematic"]["lighting"]


def test_unknown_preset_is_rejected():
    with pytest.raises(ValueError, match="Unknown preset"):
        build_storyboard("Narasi.", preset="not-a-preset")


def test_invalid_aspect_ratio_rejected():
    with pytest.raises(ValueError):
        build_storyboard("Narasi.", aspect_ratio="4:3")


def test_invalid_shot_types_rejected():
    with pytest.raises(ValueError):
        build_storyboard("Narasi.", shot_types=[])


def test_csv_export_has_header_and_scene_rows():
    data = build_storyboard("Narasi pertama.\n\nNarasi kedua.", duration_seconds=20)
    exported = export_csv(data)
    rows = list(csv.DictReader(StringIO(exported)))
    assert len(rows) == data["scene_count"]
    assert rows[0]["scene"] == "1"
    assert "visual_prompt" in rows[0]
    assert rows[-1]["end_seconds"] == "20"


def test_csv_export_quotes_multiline_or_comma_content():
    data = build_storyboard(
        "Narasi dengan koma, dan kalimat kedua.",
        duration_seconds=20,
        mood="misterius, menegangkan",
    )
    rows = list(csv.DictReader(StringIO(export_csv(data))))
    assert rows[0]["narration"] == "Narasi dengan koma, dan kalimat kedua."

from storyboard_engine.core import export_srt


def test_srt_export_uses_scene_timestamps_and_narration():
    data = build_storyboard("Narasi pembuka.\\n\\nNarasi kedua.", duration_seconds=20, scene_seconds=1)
    srt = export_srt(data)
    assert "1\\n00:00:00,000 --> 00:00:10,000\\nNarasi pembuka." in srt
    assert "2\\n00:00:10,000 --> 00:00:20,000\\nNarasi kedua." in srt


def test_srt_timestamp_handles_hour_boundary():
    data = {
        "scenes": [{"scene": 1, "start_seconds": 3599.5, "end_seconds": 3601,
                    "narration": "Crosses an hour boundary."}]
    }
    srt = export_srt(data)
    assert "00:59:59,500 --> 01:00:01,000" in srt


def test_srt_export_skips_empty_narration():
    data = {"scenes": [{"scene": 1, "start_seconds": 0, "end_seconds": 5, "narration": " "}]}
    assert export_srt(data) == ""
