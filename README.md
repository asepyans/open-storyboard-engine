# Open Storyboard Engine

A lightweight, provider-agnostic Python CLI that converts narration scripts into a structured storyboard with scene timing, cinematic visual direction, and exports to JSON, Markdown, CSV, SRT subtitles, and Premiere-compatible XML timelines. The core is deterministic and requires no AI API key.

## Quick start

```bash
python -m pip install -e ".[dev]"
storyboard-engine build examples/megalodon_id.txt --duration 90 --scene-seconds 10 --preset documentary --out output
pytest
```

The command creates storyboard exports including `output/asset_manifest.json`, `output/image_prompts.json`, and `output/image_prompts.md`, plus standard asset directories under `output/assets/` (images, videos, audio, and fonts).

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

You can save your own visual direction in a JSON file and reuse it without editing Python source. A complete preset file contains a name and these fields: **style**, **aspect_ratio**, **mood**, **lighting**, **palette**, and a non-empty **shot_types** list. Aspect ratio must be \`16:9\`, \`9:16\`, or \`1:1\`; unknown or missing fields are rejected with a helpful validation error.

Example preset included in this repository: **examples/presets/thinkman-investigative.json**.

Run the engine with your preset file:

```bash
storyboard-engine build examples/megalodon_id.txt \
  --duration 90 --scene-seconds 10 \\
  --preset-file examples/presets/thinkman-investigative.json \\
  --out output
```

Custom preset files cannot be combined with \`--preset\` in the same command. You can still use individual CLI flags such as \`--mood\` or \`--palette\` to override a loaded preset's values. The preset's \`name\` is included in the storyboard's visual profile metadata.

## Exports

- **JSON**: structured project, visual profile, scene records, timestamps.
- **Markdown**: human-readable storyboard review.
- **CSV**: one row per scene with timing, narration, shot type, prompt, screen text, and SFX.
- **SRT**: subtitle cues generated from narration using each scene's timeline. Timestamps use the standard `HH:MM:SS,mmm` format. Scene-level cue timings are approximate; use a dedicated alignment tool for word-level timing.
- **Premiere XML**: FCP7/XMEML v5 sequence with per-scene markers containing narration, visual prompt, screen text, and SFX. This provides timeline markers for review, not generated video clips.
- **Asset manifest JSON**: per-scene asset slots with stable image/video filenames, scene timing, narration, visual prompts, aspect ratio, and planned status. The manifest describes placeholders; it does not generate the media files.\n- **Image prompt batch JSON/Markdown**: ready-to-copy image prompts per scene, matching output filenames, aspect ratio, narration references, and optional negative prompts for generators that support them.


## Asset folder setup and validation

A build automatically initializes these folders under the output directory:

- \`assets/images/\`
- \`assets/videos/\`
- \`assets/audio/\`
- \`assets/fonts/\`

The manifest contains planned image/video paths for each scene. Use the validator to check which media files exist yet. Missing planned assets are reported without treating them as a malformed manifest:

\`\`\`bash
storyboard-engine validate-assets output/asset_manifest.json --project-root output
\`\`\`

The validation report lists asset presence per scene and counts present/missing images and videos. Unsafe paths (absolute paths or parent traversal), malformed entries, and unsupported manifest schema versions are rejected.


## Image prompt batch export

Each storyboard build also writes a batch prompt sheet:

- \`output/image_prompts.json\`: structured prompt entries for downstream tools or batch workflows.
- \`output/image_prompts.md\`: human-readable prompt sheet with one scene section per image, including the intended filename and negative prompt.

The prompt export is provider-agnostic. It prepares prompt text and metadata; it does not call an image-generation API or create image files. Save generated images to the matching path under \`output/assets/images/\`.


## Portable project ZIP bundle

After building a storyboard, package the exports and any media files already present into a single ZIP:

\`\`\`bash
storyboard-engine bundle output
\`\`\`

By default, the archive is written to \`output/storyboard_bundle.zip\`. To choose a different destination:

\`\`\`bash
storyboard-engine bundle output --file deliverables/ocean-storyboard.zip
\`\`\`

The bundle preserves relative paths, including the generated JSON/Markdown/CSV/SRT/XML files, manifest, prompt sheets, and available files under the asset folders. It does not generate missing media.

## How it works

1. Split script into paragraphs and group narration toward the target scene length (estimated at 130 words/minute).
2. Allocate integer scene durations proportionally, with contiguous timestamps and the exact requested total duration.
3. Generate deterministic visual prompt drafts based on preset and shot sequence.
4. Export JSON, Markdown, CSV, SRT, Premiere XML, the asset manifest, and batch image prompt sheets.\n5. Initialize standard media folders, validate the manifest, and optionally package the project into a portable ZIP.

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
- [x] SRT subtitle export
- [x] Premiere-compatible XML timeline marker export
- [x] CLI, visual profiles, named presets, and tests
- [x] Optional custom preset files
- [x] Per-scene asset manifest with predictable filenames\n- [x] Batch image prompt JSON/Markdown export\n- [x] Portable ZIP project bundle
- [ ] Editing-tool import/export adapters
- [ ] Community language presets

## Contributing

Issues and pull requests are welcome. Please add tests for behavior changes and keep the core provider-agnostic.

## License

MIT. See [LICENSE](LICENSE).
