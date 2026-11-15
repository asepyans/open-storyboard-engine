# Open Storyboard Engine

A lightweight, provider-agnostic Python CLI that converts narration scripts into a structured storyboard with scene timing, cinematic visual direction, and exports to JSON and Markdown. The core is deterministic and requires no AI API key.

## Quick start

```bash
python -m pip install -e ".[dev]"
storyboard-engine build examples/megalodon_id.txt --duration 90 --scene-seconds 10 --out output
pytest
```

The command creates `output/storyboard.json` and `output/storyboard.md`.

## Build a cinematic storyboard

```bash
storyboard-engine build examples/megalodon_id.txt \
  --duration 90 \
  --scene-seconds 10 \
  --style "cinematic documentary" \
  --aspect-ratio 16:9 \
  --mood ominous \
  --lighting "volumetric blue light" \
  --palette "deep navy and amber" \
  --out output
```

Available style-profile options:

- `--style`: visual medium/style, e.g. cinematic documentary, photorealistic, 2D animation
- `--aspect-ratio`: `16:9`, `9:16`, or `1:1`
- `--mood`: atmosphere / emotional tone
- `--lighting`: lighting direction and quality
- `--palette`: color palette description
- `--shot-types`: comma-separated shot list; scenes rotate through it

The JSON includes the shared `visual_profile` and per-scene `shot_type`, `visual_prompt`, timestamps, narration, on-screen text, and SFX fields.

## How it works

- Split the input script into paragraphs.
- Group narration toward the target scene length (estimated at 130 words/minute).
- Allocate integer scene durations proportionally, ensuring contiguous timestamps and exact total duration.
- Generate deterministic visual prompt drafts using the selected style profile and shot types.
- Export structured JSON and a readable Markdown storyboard.

## CLI

```bash
storyboard-engine build SCRIPT --duration 90 --scene-seconds 10 --out output
```

Arguments: `--duration` (total video duration, seconds), `--scene-seconds` (target scene duration), `--title` (optional project title), `--out` (output folder), plus the optional visual profile flags above.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

## Roadmap

- [x] Script-to-scene parsing
- [x] Timing estimation and scene metadata
- [x] JSON and Markdown export
- [x] CLI and unit tests
- [x] Cinematic visual style profile and shot rotation
- [ ] Optional named visual presets
- [ ] Editing-tool import/export adapters
- [ ] Community language presets

## Contributing

Issues and pull requests are welcome. Please add tests for behavior changes and keep the core provider-agnostic.

## License

MIT. See [LICENSE](LICENSE).
