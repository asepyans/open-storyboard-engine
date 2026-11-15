import json
import re
from pathlib import Path

WORDS_PER_MINUTE = 130


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
) -> dict:
    """Build a timed storyboard from script paragraphs."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than zero")
    if scene_seconds <= 0:
        raise ValueError("scene_seconds must be greater than zero")

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

    scenes, elapsed = [], 0
    for index, (chunk, scene_duration) in enumerate(zip(chunks, durations), start=1):
        start = elapsed
        end = start + scene_duration
        elapsed = end
        scenes.append({
            "scene": index,
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": scene_duration,
            "narration": chunk,
            "visual_prompt": f"Cinematic documentary visual illustrating: {chunk}",
            "on_screen_text": "",
            "sfx": "",
        })

    return {
        "title": title,
        "duration_seconds": duration_seconds,
        "language": "id",
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
    for scene in storyboard["scenes"]:
        lines.extend([
            f"## Scene {scene['scene']:02d} — {scene['start_seconds']}s–{scene['end_seconds']}s",
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


def write_exports(storyboard: dict, output_dir: str | Path) -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "storyboard.json"
    markdown_path = output / "storyboard.md"
    json_path.write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown_path.write_text(export_markdown(storyboard), encoding="utf-8")
    return json_path, markdown_path
