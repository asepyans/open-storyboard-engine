import csv
import json
from io import StringIO

import pytest

from storyboard_engine.core import VISUAL_PRESETS, build_storyboard, export_csv, export_markdown, export_srt, load_preset_file, export_fcp7_xml, export_asset_manifest, write_exports, validate_asset_manifest, initialize_asset_folders, export_image_prompt_batch, export_image_prompt_batch_markdown, create_project_bundle


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

from storyboard_engine.core import export_srt, export_vtt


def test_srt_export_uses_scene_timestamps_and_narration():
    data = build_storyboard("Narasi pembuka.\n\nNarasi kedua.", duration_seconds=20, scene_seconds=1)
    srt = export_srt(data)
    assert "1\n00:00:00,000 --> 00:00:10,000\nNarasi pembuka." in srt
    assert "2\n00:00:10,000 --> 00:00:20,000\nNarasi kedua." in srt


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


def _custom_preset_payload():
    return {
        "name": "Thinkman Investigative",
        "style": "cinematic investigative editorial",
        "aspect_ratio": "16:9",
        "mood": "cold, focused, tense",
        "lighting": "hard side light with shadow",
        "palette": "charcoal, white, amber",
        "shot_types": ["evidence wide shot", "document close-up"],
    }


def test_load_custom_preset_file_and_build_storyboard(tmp_path):
    preset_file = tmp_path / "thinkman.json"
    preset_file.write_text(json.dumps(_custom_preset_payload()), encoding="utf-8")
    name, config = load_preset_file(preset_file)
    data = build_storyboard("Narasi investigasi.", duration_seconds=12, preset="custom",
                            preset_config=config, preset_label=name)
    assert data["visual_profile"]["preset"] == "Thinkman Investigative"
    assert data["visual_profile"]["palette"] == "charcoal, white, amber"
    assert data["scenes"][0]["shot_type"] == "evidence wide shot"


def test_custom_preset_rejects_missing_fields(tmp_path):
    preset_file = tmp_path / "incomplete.json"
    preset_file.write_text(json.dumps({"name": "Incomplete"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Missing preset fields"):
        load_preset_file(preset_file)


def test_custom_preset_rejects_unknown_fields(tmp_path):
    payload = _custom_preset_payload()
    payload["unexpected"] = "value"
    preset_file = tmp_path / "unknown.json"
    preset_file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown preset fields"):
        load_preset_file(preset_file)


def test_custom_preset_rejects_invalid_ratio(tmp_path):
    payload = _custom_preset_payload()
    payload["aspect_ratio"] = "4:3"
    preset_file = tmp_path / "bad-ratio.json"
    preset_file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="aspect_ratio"):
        load_preset_file(preset_file)


def test_custom_preset_rejects_empty_shot_list(tmp_path):
    payload = _custom_preset_payload()
    payload["shot_types"] = []
    preset_file = tmp_path / "no-shots.json"
    preset_file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="shot_types"):
        load_preset_file(preset_file)


def test_custom_preset_reports_invalid_json(tmp_path):
    preset_file = tmp_path / "invalid.json"
    preset_file.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Could not read preset file"):
        load_preset_file(preset_file)


def test_fcp7_xml_export_contains_sequence_rate_and_scene_markers():
    data = build_storyboard("Opening narration.\\n\\nSecond narration.", duration_seconds=20, scene_seconds=1, title="XML Demo")
    xml = export_fcp7_xml(data, fps=25)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    sequence = root.find("sequence")
    assert sequence is not None
    assert sequence.findtext("name") == "XML Demo"
    assert sequence.findtext("duration") == "500"
    assert sequence.findtext("rate/timebase") == "25"
    markers = sequence.findall("marker")
    assert len(markers) == data["scene_count"]
    assert "VISUAL PROMPT:" in markers[0].findtext("comment")


def test_fcp7_xml_rejects_invalid_fps():
    data = build_storyboard("Narration.", duration_seconds=10)
    with pytest.raises(ValueError, match="fps"):
        export_fcp7_xml(data, fps=0)


def test_asset_manifest_has_stable_paths_and_scene_metadata():
    data = build_storyboard(
        "Narration for first scene.\\n\\nNarration for second scene.",
        duration_seconds=20,
        scene_seconds=1,
        title="Thinkman: Ocean Investigation",
        preset="vertical-shorts",
    )
    manifest = export_asset_manifest(data)
    assert manifest["schema_version"] == "1.0"
    assert manifest["project_slug"] == "thinkman-ocean-investigation"
    assert manifest["scene_count"] == data["scene_count"]
    first = manifest["assets"][0]
    assert first["scene"] == 1
    assert first["image_asset"] == "assets/images/thinkman-ocean-investigation-scene-01.png"
    assert first["video_asset"] == "assets/videos/thinkman-ocean-investigation-scene-01.mp4"
    assert first["aspect_ratio"] == "9:16"
    assert first["status"] == "planned"
    assert first["visual_prompt"] == data["scenes"][0]["visual_prompt"]


def test_write_exports_creates_asset_manifest(tmp_path):
    data = build_storyboard("Some narration.", duration_seconds=10, title="Sample")
    paths = write_exports(data, tmp_path, fps=30)
    manifest_path = tmp_path / "asset_manifest.json"
    assert manifest_path in paths
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded["project_title"] == "Sample"
    assert loaded["scene_count"] == data["scene_count"]
    assert (tmp_path / "storyboard_premiere.xml").exists()


def test_validate_asset_manifest_reports_missing_files(tmp_path):
    data = build_storyboard("Test narration.", duration_seconds=10, title="Asset Audit")
    manifest = export_asset_manifest(data)
    report = validate_asset_manifest(manifest, tmp_path)
    assert report["scene_count"] == data["scene_count"]
    assert report["checked_assets"] == data["scene_count"] * 2
    assert report["present_assets"] == 0
    assert report["missing_images"] == data["scene_count"]
    assert report["missing_videos"] == data["scene_count"]


def test_validate_asset_manifest_counts_existing_assets(tmp_path):
    data = build_storyboard("Test narration.", duration_seconds=10, title="Asset Audit")
    manifest = export_asset_manifest(data)
    first = manifest["assets"][0]
    image_path = tmp_path / first["image_asset"]
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"test image placeholder")
    report = validate_asset_manifest(manifest, tmp_path)
    assert report["present_assets"] == 1
    assert report["missing_images"] == data["scene_count"] - 1
    assert report["missing_videos"] == data["scene_count"]


def test_validate_asset_manifest_rejects_path_traversal(tmp_path):
    data = build_storyboard("Test narration.", duration_seconds=10, title="Asset Audit")
    manifest = export_asset_manifest(data)
    manifest["assets"][0]["image_asset"] = "../outside.png"
    with pytest.raises(ValueError, match="unsafe path"):
        validate_asset_manifest(manifest, tmp_path)


def test_validate_asset_manifest_rejects_wrong_schema(tmp_path):
    data = export_asset_manifest(build_storyboard("Test narration.", duration_seconds=10))
    data["schema_version"] = "2.0"
    with pytest.raises(ValueError, match="schema_version"):
        validate_asset_manifest(data, tmp_path)


def test_initialize_asset_folders_creates_expected_directories(tmp_path):
    manifest = export_asset_manifest(build_storyboard("Test narration.", duration_seconds=10))
    folders = initialize_asset_folders(manifest, tmp_path)
    assert len(folders) == 4
    assert all(folder.is_dir() for folder in folders)
    assert (tmp_path / "assets" / "images").is_dir()
    assert (tmp_path / "assets" / "videos").is_dir()
    assert (tmp_path / "assets" / "audio").is_dir()
    assert (tmp_path / "assets" / "fonts").is_dir()


def test_image_prompt_batch_export_preserves_scene_prompts_and_filenames():
    data = build_storyboard(
        "Opening scene narration.\\n\\nSecond scene narration.",
        duration_seconds=20,
        title="Batch Demo",
        preset="vertical-shorts",
    )
    batch = export_image_prompt_batch(data)
    assert batch["schema_version"] == "1.0"
    assert batch["scene_count"] == data["scene_count"]
    first = batch["prompts"][0]
    assert first["filename"] == "batch-demo-scene-01.png"
    assert first["aspect_ratio"] == "9:16"
    assert first["prompt"] == data["scenes"][0]["visual_prompt"]
    assert first["negative_prompt"]
    markdown = export_image_prompt_batch_markdown(data)
    assert "# Image Prompt Batch — Batch Demo" in markdown
    assert "**Filename:** batch-demo-scene-01.png" in markdown
    assert "**Negative prompt (if supported):**" in markdown


def test_write_exports_creates_batch_prompt_files(tmp_path):
    data = build_storyboard("Batch export narration.", duration_seconds=10, title="Batch Output")
    paths = write_exports(data, tmp_path)
    json_path = tmp_path / "image_prompts.json"
    markdown_path = tmp_path / "image_prompts.md"
    assert json_path in paths
    assert markdown_path in paths
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["project_title"] == "Batch Output"
    assert payload["prompts"][0]["filename"] == "batch-output-scene-01.png"
    assert "Image Prompt Batch" in markdown_path.read_text(encoding="utf-8")


def test_create_project_bundle_includes_exports_and_assets(tmp_path):
    data = build_storyboard("Bundle sample narration.", duration_seconds=10, title="Bundle Sample")
    write_exports(data, tmp_path)
    initialize_asset_folders(export_asset_manifest(data), tmp_path)
    image_file = tmp_path / "assets" / "images" / "sample.png"
    image_file.write_bytes(b"image fixture")
    bundle_path = create_project_bundle(tmp_path)
    assert bundle_path == tmp_path.resolve() / "storyboard_bundle.zip"
    import zipfile
    with zipfile.ZipFile(bundle_path) as archive:
        names = set(archive.namelist())
    assert "storyboard.json" in names
    assert "image_prompts.md" in names
    assert "assets/images/sample.png" in names
    assert "assets/videos" not in names


def test_create_project_bundle_rejects_directory_as_destination(tmp_path):
    with pytest.raises(ValueError, match="file path"):
        create_project_bundle(tmp_path, tmp_path)


def test_vtt_export_has_header_and_webvtt_timestamps():
    data = build_storyboard("Opening narration.\n\nSecond narration.", duration_seconds=20, scene_seconds=1)
    vtt = export_vtt(data)
    assert vtt.startswith("WEBVTT\n")
    assert "00:00:00.000 --> 00:00:10.000\nOpening narration." in vtt
    assert "00:00:10.000 --> 00:00:20.000\nSecond narration." in vtt


def test_vtt_export_skips_empty_narration_and_keeps_header():
    data = {"scenes": [{"scene": 1, "start_seconds": 0, "end_seconds": 5, "narration": " "}]}
    assert export_vtt(data) == "WEBVTT\n"


def test_write_exports_creates_vtt_file(tmp_path):
    data = build_storyboard("VTT file narration.", duration_seconds=10)
    paths = write_exports(data, tmp_path)
    vtt_path = tmp_path / "subtitles.vtt"
    assert vtt_path in paths
    assert vtt_path.read_text(encoding="utf-8").startswith("WEBVTT")
