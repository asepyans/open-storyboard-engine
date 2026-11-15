# Open Storyboard Engine

A lightweight, provider-agnostic Python CLI that converts narration scripts into a structured storyboard with scene timing, cinematic visual direction, and exports to JSON, Markdown, and CSV. The core is deterministic and requires no AI API key.

## Quick start

```bash
python -m pip install -e ".[dev]"
storyboard-engine build examples/megalodon_id.txt --duration 90 --scene-seconds 10 --preset documentary --out output
pytest
```

The command creates `output/storyboard.json`, `output/storyboard.md`, and `output/storyboard.csv`.

## Visual presets

Choose a named preset to get a cohesive style, mood, lighting, palette, aspect ratio, and shot sequence:

| Preset | Look | Default ratio |
| --- | --- | --- |
| `documentary` | Cinematic investigative documentary | 16:9 |
| `dark-cinematic` | Dark, tense, dramatic realism | 16:9 |
| `photorealistic` | Realistic documentary photography | 16:9 |
| `2d-animation` | Clean expressive 2D illustration | 9:16 |
| `vertical-shorts` | High-impact vertical documentary | 9:16 |
| `custom` | Starts with documentary values; customize individual flags | 16:9 |

Example: use the vertical shorts preset

```bash
storyboard-engine build examples/megalodon_id.txt \
  --duration 90 \
  --scene-seconds 10 \
  --preset vertical-shorts \
  --out output
```

Example: override preset values for a custom cinematic look

```bash
storyboard-engine build examples/megalodon_id.txt \
  --duration 90 \
  --preset dark-cinematic \
  --aspect-ratio 9:16 \
  --mood "mysterious underwater dread" \
  --lighting "volumetric blue light" \
  --palette "deep navy and amber" \
  --out output
```

### Optional profile flags

- `--style`: visual medium/style
- `--aspect-ratio`: `16:9`, `9:16`, or `1:1`
- `--mood`: atmosphere / emotional tone
- `--lighting`: lighting direction and quality
- `--palette`: color palette description
- `--shot-types`: comma-separated shot list; scenes rotate through it, replacing preset shot types

Explicit flags override values from the selected preset. JSON contains the complete project/profile, Markdown is readable for review, and CSV gives scene rows with timestamps, narration, shot types, prompts, on-screen text, and SFX for spreadsheet/editor workflows.

## How it works

- Split the input script into paragraphs.
- Group narration toward the target scene length (estimated at 130 words/minute).
- Allocate integer scene durations proportionally, ensuring contiguous timestamps and exact total duration.
- Generate deterministic visual prompt drafts using the selected preset and shot types.
- Export structured JSON, readable Markdown, and scene-oriented CSV.

## CLI

```bash
storyboard-engine build SCRIPT --duration 90 --scene-seconds 10 --preset documentary --out output
```

Arguments: `--duration` (total video duration, seconds), `--scene-seconds` (target scene duration), `--title` (optional project title), `--out` (output folder), `--preset` (visual preset), plus the optional profile flags above.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

## Roadmap

- [x] Script-to-scene parsing
- [x] Timing estimation and scene metadata
- [x] JSON and Markdown export
- [x] CSV scene export
- [x] CLI and unit tests
- [x] Cinematic visual profile and shot rotation
- [x] Named visual presets
- [ ] Optional custom preset files
- [ ] Editing-tool import/export adapters
- [ ] Community language presets

## Contributing

Issues and pull requests are welcome. Please add tests for behavior changes and keep the core provider-agnostic.

## License

MIT. See [LICENSE](LICENSE).
