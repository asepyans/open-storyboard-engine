import argparse
import json
from pathlib import Path

from .core import (
    VISUAL_PRESETS,
    build_storyboard,
    create_project_bundle,
    initialize_asset_folders,
    load_preset_file,
    validate_asset_manifest,
    write_exports,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert narration into a timed cinematic storyboard.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build storyboard exports")
    build.add_argument("script", type=Path)
    build.add_argument("--duration", type=int, default=90)
    build.add_argument("--scene-seconds", type=int, default=10)
    build.add_argument("--title", default=None)
    build.add_argument("--out", type=Path, default=Path("output"))
    build.add_argument("--preset", choices=[*VISUAL_PRESETS.keys(), "custom"], default="documentary")
    build.add_argument("--preset-file", type=Path, default=None, help="Load a custom visual preset from a JSON file")
    build.add_argument("--style", default=None)
    build.add_argument("--aspect-ratio", choices=["16:9", "9:16", "1:1"], default=None)
    build.add_argument("--mood", default=None)
    build.add_argument("--lighting", default=None)
    build.add_argument("--palette", default=None)
    build.add_argument("--shot-types", default=None, help="Comma-separated shot types; overrides preset shot list")
    build.add_argument("--fps", type=int, choices=[24, 25, 30, 50, 60], default=25, help="Frame rate for Premiere XML export")

    validate = subparsers.add_parser("validate-assets", help="Validate referenced files in an asset manifest")
    validate.add_argument("manifest", type=Path, help="Path to asset_manifest.json")
    validate.add_argument("--project-root", type=Path, default=Path("."), help="Root directory used to resolve manifest asset paths")

    bundle = subparsers.add_parser("bundle", help="Package project exports and available assets into a ZIP")
    bundle.add_argument("output_dir", type=Path, help="Storyboard output directory")
    bundle.add_argument("--file", type=Path, default=None, help="Optional destination ZIP file path")

    args = parser.parse_args()
    if args.command == "bundle":
        archive_path = create_project_bundle(args.output_dir, args.file)
        print(f"Created project bundle: {archive_path}")
        return

    if args.command == "validate-assets":
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        report = validate_asset_manifest(manifest, args.project_root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    script = args.script.read_text(encoding="utf-8")
    shot_types = None if args.shot_types is None else [shot.strip() for shot in args.shot_types.split(",") if shot.strip()]
    preset_config = None
    preset_name = args.preset
    if args.preset_file is not None:
        if args.preset != "documentary":
            parser.error("--preset-file cannot be combined with --preset")
        preset_name, preset_config = load_preset_file(args.preset_file)
    storyboard = build_storyboard(
        script, args.duration, args.scene_seconds,
        args.title or args.script.stem.replace("_", " ").title(),
        preset="custom" if preset_config is not None else args.preset,
        preset_config=preset_config,
        preset_label=preset_name if preset_config is not None else None,
        style=args.style, aspect_ratio=args.aspect_ratio,
        mood=args.mood, lighting=args.lighting, palette=args.palette, shot_types=shot_types,
    )
    for path in write_exports(storyboard, args.out, fps=args.fps):
        print(f"Exported: {path}")
    manifest = json.loads((args.out / "asset_manifest.json").read_text(encoding="utf-8"))
    for folder in initialize_asset_folders(manifest, args.out):
        print(f"Created asset folder: {folder}")


if __name__ == "__main__":
    main()
