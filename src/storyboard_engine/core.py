import csv
import json
import re
from pathlib import Path

WORDS_PER_MINUTE = 130
SUPPORTED_ASPECT_RATIOS = {"16:9", "9:16", "1:1"}
DEFAULT_SHOT_TYPES = ("wide establishing shot", "medium shot", "close-up", "detail shot")

VISUAL_PRESETS = {
    "documentary": {"style": "cinematic documentary", "aspect_ratio": "16:9", "mood": "engaging, investigative, cinematic", "lighting": "natural cinematic lighting with realistic shadows", "palette": "earthy neutrals, deep navy, restrained amber accents", "shot_types": ["wide establishing shot", "medium shot", "close-up", "detail shot"]},
    "dark-cinematic": {"style": "dark cinematic realism", "aspect_ratio": "16:9", "mood": "ominous, tense, mysterious", "lighting": "low-key lighting, volumetric beams, dramatic rim light", "palette": "pitch black, deep slate navy, crimson accents", "shot_types": ["dramatic wide shot", "silhouette shot", "slow close-up", "evidence detail"]},
    "photorealistic": {"style": "photorealistic documentary photography", "aspect_ratio": "16:9", "mood": "credible, immersive, natural", "lighting": "physically plausible natural light", "palette": "true-to-life colors, balanced contrast", "shot_types": ["wide location shot", "medium observational shot", "close-up", "macro detail"]},
    "2d-animation": {"style": "clean 2D animated illustration", "aspect_ratio": "9:16", "mood": "expressive, clear, story-driven", "lighting": "soft stylized lighting with simple shadow shapes", "palette": "bold cohesive colors, high readability", "shot_types": ["wide establishing illustration", "character medium shot", "expressive close-up", "prop detail"]},
    "vertical-shorts": {"style": "cinematic vertical documentary", "aspect_ratio": "9:16", "mood": "high-impact, engaging, dramatic", "lighting": "cinematic directional lighting, subject separated from background", "palette": "deep contrast, vibrant controlled highlights", "shot_types": ["vertical establishing shot", "medium portrait shot", "tight close-up", "dramatic detail"]},
}




PRESET_FIELDS = {"style", "aspect_ratio", "mood", "lighting", "palette", "shot_types"}


def load_preset_file(path: str | Path) -> tuple[str, dict]:
    """Load and validate a user-authored JSON visual preset."""
    preset_path = Path(path)
    try:
        data = json.loads(preset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read preset file '{preset_path}': {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("preset file must contain a JSON object")
    name = data.get("name", preset_path.stem)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("preset name must be a non-empty string")
    unknown = set(data) - (PRESET_FIELDS | {"name"})
    if unknown:
        raise ValueError(f"Unknown preset fields: {', '.join(sorted(unknown))}")
    required = PRESET_FIELDS
    missing = required - set(data)
    if missing:
        raise ValueError(f"Missing preset fields: {', '.join(sorted(missing))}")
    for field in required - {"shot_types", "aspect_ratio"}:
        if not isinstance(data[field], str) or not data[field].strip():
            raise ValueError(f"'{field}' must be a non-empty string")
    if data["aspect_ratio"] not in SUPPORTED_ASPECT_RATIOS:
        raise ValueError(f"aspect_ratio must be one of: {', '.join(sorted(SUPPORTED_ASPECT_RATIOS))}")
    shots = data["shot_types"]
    if not isinstance(shots, list) or not shots or any(not isinstance(shot, str) or not shot.strip() for shot in shots):
        raise ValueError("shot_types must be a non-empty list of non-empty strings")
    return name.strip(), {key: data[key] for key in PRESET_FIELDS}


def word_count(text: str) -> int:
    """Count approximate narration words."""
    return len(re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE))


def _merge_chunks(chunks: list[str], limit: int) -> list[str]:
    """Merge adjacent chunks when there are more scenes than available seconds."""
    if len(chunks) <= limit:
        return chunks
    merged = [""] * limit
    for index, chunk in enumerate(chunks):
        bucket = min(limit - 1, index * limit // len(chunks))
        merged[bucket] = (merged[bucket] + " " + chunk).strip()
    return [chunk for chunk in merged if chunk]


def _allocate_durations(weights: list[int], total_seconds: int) -> list[int]:
    """Allocate integer durations, with at least one second per scene."""
    scene_count = len(weights)
    if scene_count > total_seconds:
        raise ValueError("scene count cannot exceed total duration in seconds")
    remaining = total_seconds - scene_count
    total_weight = sum(weights)
    quotas = [remaining * weight / total_weight for weight in weights]
    extras = [int(quota) for quota in quotas]
    leftover = remaining - sum(extras)
    order = sorted(range(scene_count), key=lambda i: (quotas[i] - extras[i], -i), reverse=True)
    for index in order[:leftover]:
        extras[index] += 1
    return [1 + extra for extra in extras]


def build_storyboard(
    script: str, duration_seconds: int = 90, scene_seconds: int = 10,
    title: str = "Untitled Storyboard", *, preset: str = "documentary",
    style: str | None = None, aspect_ratio: str | None = None,
    mood: str | None = None, lighting: str | None = None,
    palette: str | None = None, shot_types: list[str] | tuple[str, ...] | None = None,
    preset_config: dict | None = None,
    preset_label: str | None = None,
) -> dict:
    """Build a timed storyboard with deterministic cinematic visual prompts."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than zero")
    if scene_seconds <= 0:
        raise ValueError("scene_seconds must be greater than zero")
    if preset not in (*VISUAL_PRESETS.keys(), "custom"):
        raise ValueError(f"Unknown preset '{preset}'. Choose from: {', '.join((*VISUAL_PRESETS.keys(), 'custom'))}")
    base = preset_config if preset_config is not None else VISUAL_PRESETS.get(preset, VISUAL_PRESETS["documentary"])
    style = style if style is not None else base["style"]
    aspect_ratio = aspect_ratio if aspect_ratio is not None else base["aspect_ratio"]
    mood = mood if mood is not None else base["mood"]
    lighting = lighting if lighting is not None else base["lighting"]
    palette = palette if palette is not None else base["palette"]
    shots = tuple(shot_types) if shot_types is not None else tuple(base["shot_types"])
    if aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
        raise ValueError(f"aspect_ratio must be one of: {', '.join(sorted(SUPPORTED_ASPECT_RATIOS))}")
    if not shots or any(not shot.strip() for shot in shots):
        raise ValueError("shot_types must contain at least one non-empty shot type")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", script.strip()) if part.strip()]
    if not paragraphs:
        raise ValueError("script must contain at least one non-empty paragraph")
    target_words = max(1, round(scene_seconds * WORDS_PER_MINUTE / 60))
    chunks, current, count = [], [], 0
    for paragraph in paragraphs:
        size = word_count(paragraph)
        if current and count + size > target_words:
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(paragraph)
        count += size
    if current:
        chunks.append(" ".join(current))
    chunks = _merge_chunks(chunks, duration_seconds)
    durations = _allocate_durations([max(1, word_count(chunk)) for chunk in chunks], duration_seconds)
    visual_profile = {"preset": preset_label or preset, "style": style, "aspect_ratio": aspect_ratio, "mood": mood, "lighting": lighting, "palette": palette, "shot_types": list(shots)}
    scenes, elapsed = [], 0
    for index, (chunk, scene_duration) in enumerate(zip(chunks, durations), start=1):
        start, end = elapsed, elapsed + scene_duration
        elapsed = end
        shot_type = shots[(index - 1) % len(shots)]
        visual_prompt = (
            f"{style}; {shot_type}; aspect ratio {aspect_ratio}; mood: {mood}; lighting: {lighting}; color palette: {palette}. "
            f"Visualize the following narration as a cinematic scene: {chunk}. Detailed composition, coherent subject, realistic environmental details. "
            "No captions, no typography, no watermark."
        )
        scenes.append({"scene": index, "start_seconds": start, "end_seconds": end, "duration_seconds": scene_duration,
                       "narration": chunk, "shot_type": shot_type, "visual_prompt": visual_prompt, "on_screen_text": "", "sfx": ""})
    return {"title": title, "duration_seconds": duration_seconds, "language": "id", "visual_profile": visual_profile, "scene_count": len(scenes), "scenes": scenes}


def export_markdown(storyboard: dict) -> str:
    lines = [f"# {storyboard['title']}", "", f"**Total duration:** {storyboard['duration_seconds']} seconds", f"**Scene count:** {storyboard['scene_count']}", ""]
    if "visual_profile" in storyboard:
        profile = storyboard["visual_profile"]
        lines.extend(["## Visual profile", "", f"- **Preset:** {profile.get('preset', 'custom')}", f"- **Style:** {profile['style']}",
                      f"- **Aspect ratio:** {profile['aspect_ratio']}", f"- **Mood:** {profile['mood']}", f"- **Lighting:** {profile['lighting']}", f"- **Palette:** {profile['palette']}", ""])
    for scene in storyboard["scenes"]:
        lines.extend([f"## Scene {scene['scene']:02d} — {scene['start_seconds']}s–{scene['end_seconds']}s", "",
                      f"**Shot type:** {scene.get('shot_type', '—')}", "", f"**Narration:** {scene['narration']}", "",
                      f"**Visual prompt:** {scene['visual_prompt']}", "", f"**On-screen text:** {scene['on_screen_text'] or '—'}", "",
                      f"**SFX:** {scene['sfx'] or '—'}", ""])
    return "\n".join(lines)


def export_csv(storyboard: dict) -> str:
    """Export scene data as CSV for spreadsheet/editor workflows."""
    from io import StringIO
    columns = ["scene", "start_seconds", "end_seconds", "duration_seconds", "shot_type", "narration", "visual_prompt", "on_screen_text", "sfx"]
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(storyboard["scenes"])
    return buffer.getvalue()


def _srt_timestamp(seconds: float) -> str:
    """Format seconds as an SRT timestamp (HH:MM:SS,mmm)."""
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def export_srt(storyboard: dict) -> str:
    """Create subtitle cues from scene narration using the scene's timeline."""
    cues = []
    for index, scene in enumerate(storyboard["scenes"], start=1):
        narration = scene["narration"].strip()
        if not narration:
            continue
        cues.append(
            f"{index}\n{_srt_timestamp(scene['start_seconds'])} --> {_srt_timestamp(scene['end_seconds'])}\n{narration}"
        )
    return "\n\n".join(cues) + ("\n" if cues else "")




def _safe_filename(value: str) -> str:
    """Convert a title into a portable lowercase filename stem."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "storyboard"


def export_asset_manifest(storyboard: dict) -> dict:
    """Create a stable JSON manifest describing per-scene visual asset slots."""
    project_slug = _safe_filename(storyboard.get("title", "storyboard"))
    profile = storyboard.get("visual_profile", {})
    ratio = profile.get("aspect_ratio", "16:9")
    assets = []
    for scene in storyboard["scenes"]:
        scene_number = int(scene["scene"])
        filename_stem = f"{project_slug}-scene-{scene_number:02d}"
        assets.append({
            "scene": scene_number,
            "start_seconds": scene["start_seconds"],
            "end_seconds": scene["end_seconds"],
            "duration_seconds": scene.get("duration_seconds", scene["end_seconds"] - scene["start_seconds"]),
            "narration": scene.get("narration", ""),
            "shot_type": scene.get("shot_type", ""),
            "visual_prompt": scene.get("visual_prompt", ""),
            "aspect_ratio": ratio,
            "image_asset": f"assets/images/{filename_stem}.png",
            "video_asset": f"assets/videos/{filename_stem}.mp4",
            "status": "planned",
        })
    return {
        "schema_version": "1.0",
        "project_title": storyboard.get("title", "Untitled Storyboard"),
        "project_slug": project_slug,
        "duration_seconds": storyboard["duration_seconds"],
        "scene_count": len(assets),
        "visual_profile": profile,
        "assets": assets,
    }


def write_exports(storyboard: dict, output_dir: str | Path, fps: int = 25) -> tuple[Path, ...]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "storyboard.json"
    markdown_path = output / "storyboard.md"
    csv_path = output / "storyboard.csv"
    srt_path = output / "subtitles.srt"
    xml_path = output / "storyboard_premiere.xml"
    manifest_path = output / "asset_manifest.json"
    prompts_json_path = output / "image_prompts.json"
    prompts_markdown_path = output / "image_prompts.md"

    json_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(export_markdown(storyboard), encoding="utf-8")
    csv_path.write_text(export_csv(storyboard), encoding="utf-8-sig")
    srt_path.write_text(export_srt(storyboard), encoding="utf-8-sig")
    xml_path.write_text(export_fcp7_xml(storyboard, fps=fps), encoding="utf-8")
    manifest_path.write_text(json.dumps(export_asset_manifest(storyboard), ensure_ascii=False, indent=2), encoding="utf-8")
    prompts_json_path.write_text(json.dumps(export_image_prompt_batch(storyboard), ensure_ascii=False, indent=2), encoding="utf-8")
    prompts_markdown_path.write_text(export_image_prompt_batch_markdown(storyboard), encoding="utf-8")
    return (
        json_path, markdown_path, csv_path, srt_path, xml_path, manifest_path,
        prompts_json_path, prompts_markdown_path,
    )

def export_fcp7_xml(storyboard: dict, fps: int = 25) -> str:
    """Export an XMEML v5 sequence with scene markers for Premiere Pro / compatible NLEs."""
    import xml.etree.ElementTree as ET

    if not isinstance(fps, int) or fps <= 0:
        raise ValueError("fps must be a positive integer")
    root = ET.Element("xmeml", version="5")
    sequence = ET.SubElement(root, "sequence", id="sequence-1")
    ET.SubElement(sequence, "name").text = storyboard["title"]
    total_frames = round(storyboard["duration_seconds"] * fps)
    ET.SubElement(sequence, "duration").text = str(total_frames)
    rate = ET.SubElement(sequence, "rate")
    ET.SubElement(rate, "timebase").text = str(fps)
    ET.SubElement(rate, "ntsc").text = "FALSE"
    timecode = ET.SubElement(sequence, "timecode")
    tc_rate = ET.SubElement(timecode, "rate")
    ET.SubElement(tc_rate, "timebase").text = str(fps)
    ET.SubElement(tc_rate, "ntsc").text = "FALSE"
    ET.SubElement(timecode, "string").text = "00:00:00:00"
    ET.SubElement(timecode, "frame").text = "0"
    ET.SubElement(timecode, "displayformat").text = "NDF"

    for scene in storyboard["scenes"]:
        start = round(scene["start_seconds"] * fps)
        end = round(scene["end_seconds"] * fps)
        marker = ET.SubElement(sequence, "marker")
        ET.SubElement(marker, "name").text = f"Scene {scene['scene']:02d} — {scene.get('shot_type', 'Shot')}"
        ET.SubElement(marker, "comment").text = (
            f"NARRATION: {scene.get('narration', '')}\n"
            f"VISUAL PROMPT: {scene.get('visual_prompt', '')}\n"
            f"ON-SCREEN TEXT: {scene.get('on_screen_text', '')}\n"
            f"SFX: {scene.get('sfx', '')}"
        )
        ET.SubElement(marker, "in").text = str(start)
        ET.SubElement(marker, "out").text = str(end)

    media = ET.SubElement(sequence, "media")
    video = ET.SubElement(media, "video")
    video_format = ET.SubElement(video, "format")
    sample_characteristics = ET.SubElement(video_format, "samplecharacteristics")
    ET.SubElement(sample_characteristics, "width").text = "1920"
    ET.SubElement(sample_characteristics, "height").text = "1080"
    video_track = ET.SubElement(video, "track")
    ET.SubElement(video_track, "enabled").text = "TRUE"
    ET.SubElement(video_track, "locked").text = "FALSE"
    audio = ET.SubElement(media, "audio")
    audio_track = ET.SubElement(audio, "track")
    ET.SubElement(audio_track, "enabled").text = "TRUE"
    ET.SubElement(audio_track, "locked").text = "FALSE"

    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def validate_asset_manifest(manifest: dict, project_root: str | Path) -> dict:
    """Validate manifest structure and report which referenced media files exist."""
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    if manifest.get("schema_version") != "1.0":
        raise ValueError("unsupported or missing manifest schema_version")
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValueError("manifest 'assets' must be a list")
    root = Path(project_root).resolve()
    checked = []
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            raise ValueError(f"asset entry {index} must be an object")
        scene = asset.get("scene")
        if not isinstance(scene, int) or scene < 1:
            raise ValueError(f"asset entry {index} has invalid scene number")
        paths = {}
        for field in ("image_asset", "video_asset"):
            raw = asset.get(field)
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(f"asset entry {index} is missing '{field}'")
            relative = Path(raw)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"asset entry {index} has unsafe path in '{field}'")
            resolved = (root / relative).resolve()
            if resolved != root and root not in resolved.parents:
                raise ValueError(f"asset entry {index} path escapes project root")
            paths[field] = {"path": raw, "exists": resolved.is_file()}
        checked.append({"scene": scene, "image": paths["image_asset"], "video": paths["video_asset"]})
    missing_images = sum(not entry["image"]["exists"] for entry in checked)
    missing_videos = sum(not entry["video"]["exists"] for entry in checked)
    return {
        "project_title": manifest.get("project_title", "Untitled Storyboard"),
        "scene_count": len(checked),
        "checked_assets": len(checked) * 2,
        "present_assets": len(checked) * 2 - missing_images - missing_videos,
        "missing_images": missing_images,
        "missing_videos": missing_videos,
        "assets": checked,
    }


def initialize_asset_folders(manifest: dict, project_root: str | Path) -> list[Path]:
    """Create standard project asset directories for a validated manifest."""
    validate_asset_manifest(manifest, project_root)
    root = Path(project_root)
    folders = [
        root / "assets" / "images",
        root / "assets" / "videos",
        root / "assets" / "audio",
        root / "assets" / "fonts",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def export_image_prompt_batch(storyboard: dict) -> dict:
    """Prepare per-scene image prompts for batch copy/paste into image generators."""
    manifest = export_asset_manifest(storyboard)
    prompts = []
    for asset in manifest["assets"]:
        prompts.append({
            "scene": asset["scene"],
            "filename": Path(asset["image_asset"]).name,
            "aspect_ratio": asset["aspect_ratio"],
            "prompt": asset["visual_prompt"],
            "negative_prompt": "text, captions, watermark, logo, low resolution, blurry, distorted anatomy, duplicate subjects",
            "narration": asset["narration"],
            "start_seconds": asset["start_seconds"],
            "end_seconds": asset["end_seconds"],
        })
    return {
        "schema_version": "1.0",
        "project_title": storyboard.get("title", "Untitled Storyboard"),
        "scene_count": len(prompts),
        "prompts": prompts,
    }


def export_image_prompt_batch_markdown(storyboard: dict) -> str:
    """Render a human-friendly batch prompt sheet, one copyable prompt block per scene."""
    batch = export_image_prompt_batch(storyboard)
    lines = [
        f"# Image Prompt Batch — {batch['project_title']}",
        "",
        f"Scenes: {batch['scene_count']}",
        "",
        "Generate one image per scene. Save each result using the listed filename.",
        "",
    ]
    for item in batch["prompts"]:
        lines.extend([
            f"## Scene {item['scene']:02d} — {item['start_seconds']}s to {item['end_seconds']}s",
            "",
            f"**Filename:** {item['filename']}",
            f"**Aspect ratio:** {item['aspect_ratio']}",
            "",
            "**Prompt:**",
            "",
            item["prompt"],
            "",
            "**Negative prompt (if supported):**",
            "",
            item["negative_prompt"],
            "",
            "**Narration reference:**",
            "",
            item["narration"],
            "",
        ])
    return "\n".join(lines)


def create_project_bundle(output_dir: str | Path, bundle_path: str | Path | None = None) -> Path:
    """Package generated exports and any present media assets into a portable ZIP."""
    import zipfile

    root = Path(output_dir).resolve()
    if not root.is_dir():
        raise ValueError(f"output directory does not exist: {output_dir}")
    destination = Path(bundle_path).resolve() if bundle_path is not None else root / "storyboard_bundle.zip"
    if destination == root or root not in destination.parents:
        # An external destination is allowed, but a destination inside the output
        # directory must not be the same directory itself.
        if destination == root:
            raise ValueError("bundle destination must be a file path")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination_abs = destination
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.resolve() != destination_abs)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root).as_posix())
    return destination


def _vtt_timestamp(seconds: float) -> str:
    """Format seconds as a WebVTT timestamp (HH:MM:SS.mmm)."""
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"


def export_vtt(storyboard: dict) -> str:
    """Export scene narration as WebVTT subtitle cues."""
    cues = ["WEBVTT", ""]
    for scene in storyboard["scenes"]:
        narration = scene["narration"].strip()
        if not narration:
            continue
        cues.append(
            f"{_vtt_timestamp(scene['start_seconds'])} --> {_vtt_timestamp(scene['end_seconds'])}\n{narration}\n"
        )
    return "\n".join(cues).rstrip() + "\n"
