# Open Storyboard Engine

A lightweight, provider-agnostic Python CLI that converts narration scripts into a structured storyboard with scene timing, cinematic visual direction, and exports to JSON, Markdown, CSV, SRT subtitles, and Premiere-compatible XML timelines. The core is deterministic and requires no AI API key.

## Quick start

```bash
python -m pip install -e ".[dev]"
storyboard-engine build examples/megalodon_id.txt --duration 90 --scene-seconds 10 --preset documentary --out output
pytest
```

The command creates `output/storyboard.json`, `output/storyboard.md`, `output/storyboard.csv`, `output/subtitles.srt`, and `output/storyboard_premiere.xml`.

## Visual presets

| Preset | Look | Default ratio |
| --- | --- | --- |
| `documentary` | Cinematic investigative documentary | 16:9 |
| `dark-cinematic` | Dark, tense, dramatic realism | 16:9 |
| `photorealistic` | Realistic documentary photography | 16:9 |
| `2d-animation` | Clean expressive 2D illustration | 9:16 |
| `vertical-shorts` | High-impact vertical documentary | 9:16 |
| `custom` | Documentary base with user-specified overrides | 16:9 |

Vertical short sample:

```bash
storyboard-engine build examples/megalodon_id.txt --duration 90 --scene-seconds 10 --preset vertical-shorts --out output
```

Customized cinematic sample:

```bash
storyboard-engine build examples/megalodon_id.txt \
  --duration 90 --preset dark-cinematic --aspect-ratio 9:16 \
  --mood "mysterious underwater dread" --lighting "volumetric blue light" \
  --palette "deep navy and amber" --out output
```

Optional flags: `--style`, `--aspect-ratio` (`16:9`, `9:16`, `1:1`), `--mood`, `--lighting`, `--palette`, `--shot-types` (comma-separated override list), and `--fps` (24, 25, 30, 50, or 60; default 25 for XML).


## Custom preset files

You can save your own visual direction in a JSON file and reuse it without editing Python source. A complete preset file contains a name and these fields: \`style\`, \`aspect_ratio\`, \`mood\`, \`lighting\`, \`palette\`, and a non-empty \`shot_types\` list. Aspect ratio must be \`16:9\`, \`9:16\`, or \`1:1\`; unknown or missing fields are rejected with a helpful validation error.

Example preset included in this repository: \`examples/presets/thinkman-investigative.json\`.

Run the engine with your preset file:

\`\`\`bash
storyboard-engine build examples/megalodon_id.txt \\
  --duration 90 --scene-seconds 10 \\
  --preset-file examples/presets/thinkman-investigative.json \\
  --out output
\`\`\`

Custom preset files cannot be combined with \`--preset\` in the same command. You can still use individual CLI flags such as \`--mood\` or \`--palette\` to override a loaded preset's values. The preset's \`name\` is included in the storyboard's visual profile metadata.

## Exports

- **JSON**: structured project, visual profile, scene records, timestamps.
- **Markdown**: human-readable storyboard review.
- **CSV**: one row per scene with timing, narration, shot type, prompt, screen text, and SFX.
- **SRT**: subtitle cues generated from narration using each scene's timeline. Timestamps use the standard `HH:MM:SS,mmm` format. Scene-level cue timings are approximate; use a dedicated alignment tool for word-level timing.\n- **Premiere XML**: FCP7/XMEML v5 sequence with per-scene markers containing narration, visual prompt, screen text, and SFX. This provides timeline markers for review, not generated video clips.

## How it works

1. Split script into paragraphs and group narration toward the target scene length (estimated at 130 words/minute).
2. Allocate integer scene durations proportionally, with contiguous timestamps and the exact requested total duration.
3. Generate deterministic visual prompt drafts based on preset and shot sequence.
4. Export JSON, Markdown, CSV, and SRT.

## CLI

```bash
storyboard-engine build SCRIPT --duration 90 --scene-seconds 10 --preset documentary --out output
```

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

## Roadmap

- [x] Script-to-scene parsing and timing
- [x] JSON / Markdown / CSV exports
- [x] SRT subtitle export\n- [x] Premiere-compatible XML timeline marker export
- [x] CLI, visual profiles, named presets, and tests
- [ ] Optional custom preset files
- [ ] Editing-tool import/export adapters
- [ ] Community language presets

## Contributing

Issues and pull requests are welcome. Please add tests for behavior changes and keep the core provider-agnostic.

## License

MIT. See [LICENSE](LICENSE).
