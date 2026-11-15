import argparse
from pathlib import Path

from .core import VISUAL_PRESETS, build_storyboard, write_exports


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a narration script into a timed cinematic storyboard."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Build storyboard exports")
    build.add_argument("script", type=Path)
    build.add_argument("--duration", type=int, default=90)
    build.add_argument("--scene-seconds", type=int, default=10)
    build.add_argument("--title", default=None)
    build.add_argument("--out", type=Path, default=Path("output"))
    build.add_argument("--preset", choices=[*VISUAL_PRESETS.keys(), "custom"], default="documentary")
    build.add_argument("--style", default=None)
    build.add_argument("--aspect-ratio", choices=["16:9", "9:16", "1:1"], default=None)
    build.add_argument("--mood", default=None)
    build.add_argument("--lighting", default=None)
    build.add_argument("--palette", default=None)
    build.add_argument(
        "--shot-types",
        default=None,
        help="Comma-separated shot types; overrides the preset's shot list",
    )
    args = parser.parse_args()

    script = args.script.read_text(encoding="utf-8")
    shot_types = None
    if args.shot_types is not None:
        shot_types = [shot.strip() for shot in args.shot_types.split(",") if shot.strip()]

    storyboard = build_storyboard(
        script,
        args.duration,
        args.scene_seconds,
        args.title or args.script.stem.replace("_", " ").title(),
        preset=args.preset,
        style=args.style,
        aspect_ratio=args.aspect_ratio,
        mood=args.mood,
        lighting=args.lighting,
        palette=args.palette,
        shot_types=shot_types,
    )
    for path in write_exports(storyboard, args.out):
        print(f"Exported: {path}")


if __name__ == "__main__":
    main()
