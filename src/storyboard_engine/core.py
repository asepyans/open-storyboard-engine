import csv
import json
import re
from pathlib import Path

WORDS_PER_MINUTE = 130
SUPPORTED_ASPECT_RATIOS = {"16:9", "9:16", "1:1"}
DEFAULT_SHOT_TYPES = (
    "wide establishing shot",
    "medium shot",
    "close-up",
    "detail shot",
)

VISUAL_PRESETS = {
    "documentary": {
        "style": "cinematic documentary",
        "aspect_ratio": "16:9",
        "mood": "engaging, investigative, cinematic",
        "lighting": "natural cinematic lighting with realistic shadows",
        "palette": "earthy neutrals, deep navy, restrained amber accents",
        "shot_types": ["wide establishing shot", "medium shot", "close-up", "detail shot"],
    },
    "dark-cinematic": {
        "style": "dark cinematic realism",
        "aspect_ratio": "16:9",
        "mood": "ominous, tense, mysterious",
        "lighting": "low-key lighting, volumetric beams, dramatic rim light",
        "palette": "pitch black, deep slate navy, crimson accents",
        "shot_types": ["dramatic wide shot", "silhouette shot", "slow close-up", "evidence detail"],
    },
    "photorealistic": {
        "style": "photorealistic documentary photography",
        "aspect_ratio": "16:9",
        "mood": "credible, immersive, natural",
        "lighting": "physically plausible natural light",
        "palette": "true-to-life colors, balanced contrast",
        "shot_types": ["wide location shot", "medium observational shot", "close-up", "macro detail"],
    },
    "2d-animation": {
        "style": "clean 2D animated illustration",
        "aspect_ratio": "9:16",
        "mood": "expressive, clear, story-driven",
        "lighting": "soft stylized lighting with simple shadow shapes",
        "palette": "bold cohesive colors, high readability",
        "shot_types": ["wide establishing illustration", "character medium shot", "expressive close-up", "prop detail"],
    },
    "vertical-shorts": {
        "style": "cinematic vertical documentary",
        "aspect_ratio": "9:16",
        "mood": "high-impact, engaging, dramatic",
        "lighting": "cinematic directional lighting, subject separated from background",
        "palette": "deep contrast, vibrant controlled highlights",
        "shot_types": ["vertical establishing shot", "medium portrait shot", "tight close-up", "dramatic detail"],
    },
}


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

    order = sorted(
        range(scene_count),
        key=lambda index: (quotas[index] - extras[index], -index),
        reverse=True,
    )
    for index in order[:leftover]:
        extras[index] += 1
    return [1 + extra for extra in extras]


def build_storyboard(
    script: str,
    duration_seconds: int = 90,
    scene_seconds: int = 10,
    title: str = "Untitled Storyboard",
    *,
    preset: str = "documentary",
    style: str | None = None,
    aspect_ratio: str | None = None,
    mood: str | None = None,
    lighting: str | None = None,
    palette: str | None = None,
    shot_types: list[str] | tuple[str, ...] | None = None,
) -> dict:
    """Build a timed storyboard with deterministic cinematic visual prompts."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than zero")
    if scene_seconds <= 0:
        raise ValueError("scene_seconds must be greater than zero")
    if preset not in (*VISUAL_PRESETS.keys(), "custom"):
        raise ValueError(
            f"Unknown preset '{preset}'. Choose from: {', '.join((*VISUAL_PRESETS.keys(), 'custom'))}"
        )

    base = VISUAL_PRESETS.get(preset, VISUAL_PRESETS["documentary"])
    style = style if style is not None else base["style"]
    aspect_ratio = aspect_ratio if aspect_ratio is not None else base["aspect_ratio"]
    mood = mood if mood is not None else base["mood"]
    lighting = lighting if lighting is not None else base["lighting"]
    palette = palette if palette is not None else base["palette"]
    shots = tuple(shot_types) if shot_types is not None else tuple(base["shot_types"])

    if aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
        raise ValueError(
            f"aspect_ratio must be one of: {', '.join(sorted(SUPPORTED_ASPECT_RATIOS))}"
        )
    if not shots or any(not shot.strip() for shot in shots):
        raise ValueError("shot_types must contain at least one non-empty shot type")

    paragraphs = [
        part.strip()
        for part in re.split(r"\n\s*\n", script.strip())
        if part.strip()
    ]
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
    weights = [max(1, word_count(chunk)) for chunk in chunks]
    durations = _allocate_durations(weights, duration_seconds)

    visual_profile = {
        "preset": preset,
        "style": style,
        "aspect_ratio": aspect_ratio,
        "mood": mood,
        "lighting": lighting,
        "palette": palette,
        "shot_types": list(shots),
    }

    scenes, elapsed = [], 0
    for index, (chunk, scene_duration) in enumerate(zip(chunks, durations), start=1):
        start = elapsed
        end = start + scene_duration
        elapsed = end
        shot_type = shots[(index - 1) % len(shots)]
        visual_prompt = (
            f"{style}; {shot_type}; aspect ratio {aspect_ratio}; "
            f"mood: {mood}; lighting: {lighting}; color palette: {palette}. "
            f"Visualize the following narration as a cinematic scene: {chunk}. "
            "Detailed composition, coherent subject, realistic environmental details. "
            "No captions, no typography, no watermark."
        )
        scenes.append({
            "scene": index,
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": scene_duration,
            "narration": chunk,
            "shot_type": shot_type,
            "visual_prompt": visual_prompt,
            "on_screen_text": "",
            "sfx": "",
        })

    return {
        "title": title,
        "duration_seconds": duration_seconds,
        "language": "id",
        "visual_profile": visual_profile,
        "scene_count": len(scenes),
        "scenes": scenes,
    }


def export_markdown(storyboard: dict) -> str:
    lines = [
        f"# {storyboard['title']}",
        "",
        f"**Total duration:** {storyboard['duration_seconds']} seconds",
        f"**Scene count:** {storyboard['scene_count']}",
        "",
    ]
    if "visual_profile" in storyboard:
        profile = storyboard["visual_profile"]
        lines.extend([
            "## Visual profile",
            "",
            f"- **Preset:** {profile.get('preset', 'custom')}",
            f"- **Style:** {profile['style']}",
            f"- **Aspect ratio:** {profile['aspect_ratio']}",
            f"- **Mood:** {profile['mood']}",
            f"- **Lighting:** {profile['lighting']}",
            f"- **Palette:** {profile['palette']}",
            "",
        ])
    for scene in storyboard["scenes"]:
        lines.extend([
            f"## Scene {scene['scene']:02d} — {scene['start_seconds']}s–{scene['end_seconds']}s",
            "",
            f"**Shot type:** {scene.get('shot_type', '—')}",
            "",
            f"**Narration:** {scene['narration']}",
            "",
            f"**Visual prompt:** {scene['visual_prompt']}",
            "",
            f"**On-screen text:** {scene['on_screen_text'] or '—'}",
            "",
            f"**SFX:** {scene['sfx'] or '—'}",
            "",
        ])
    return "\n".join(lines)


def export_csv(storyboard: dict) -> str:
    """Export scene data as UTF-8-friendly CSV for spreadsheet/editor workflows."""
    from io import StringIO

    columns = [
        "scene", "start_seconds", "end_seconds", "duration_seconds",
        "shot_type", "narration", "visual_prompt", "on_screen_text", "sfx",
    ]
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(storyboard["scenes"])
    return buffer.getvalue()


def write_exports(storyboard: dict, output_dir: str | Path) -> tuple[Path, Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "storyboard.json"
    markdown_path = output / "storyboard.md"
    csv_path = output / "storyboard.csv"
    json_path.write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown_path.write_text(export_markdown(storyboard), encoding="utf-8")
    csv_path.write_text(export_csv(storyboard), encoding="utf-8-sig")
    return json_path, markdown_path, csv_path
