import json
import re
from pathlib import Path

WORDS_PER_MINUTE = 130


def word_count(text: str) -> int:
    """Count approximate narration words."""
    return len(re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE))


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

    weights = [max(1, word_count(chunk)) for chunk in chunks]
    total_weight = sum(weights)
    scenes, elapsed = [], 0

    for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        start = elapsed
        if index == len(chunks):
            end = duration_seconds
        else:
            end = min(
                duration_seconds - (len(chunks) - index),
                start + max(1, round(duration_seconds * weight / total_weight)),
            )
        elapsed = end
        scenes.append({
            "scene": index,
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": end - start,
            "narration": chunk,
            "visual_prompt": f"Cinematic documentary visual illustrating: {chunk}",
            "on_screen_text": "",
            "sfx": "",
        })

    scenes[-1]["end_seconds"] = duration_seconds
    scenes[-1]["duration_seconds"] = duration_seconds - scenes[-1]["start_seconds"]
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
