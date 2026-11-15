import argparse
from pathlib import Path

from .core import build_storyboard, write_exports


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a narration script into a timed storyboard."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Build storyboard exports")
    build.add_argument("script", type=Path)
    build.add_argument("--duration", type=int, default=90)
    build.add_argument("--scene-seconds", type=int, default=10)
    build.add_argument("--title", default=None)
    build.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()

    script = args.script.read_text(encoding="utf-8")
    storyboard = build_storyboard(
        script,
        args.duration,
        args.scene_seconds,
        args.title or args.script.stem.replace("_", " ").title(),
    )
    for path in write_exports(storyboard, args.out):
        print(f"Exported: {path}")


if __name__ == "__main__":
    main()
