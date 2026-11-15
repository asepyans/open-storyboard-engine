# Open Storyboard Engine

A lightweight, provider-agnostic Python CLI that converts a narration script into a structured storyboard with scene timing, visual direction, and exports to JSON and Markdown. The core is deterministic and requires no AI API key.

## Quick start

```bash
python -m pip install -e ".[dev]"
storyboard-engine build examples/megalodon_id.txt --duration 90 --scene-seconds 10 --out output
pytest
```

The command creates `output/storyboard.json` and `output/storyboard.md`.

## How it works

- Split the input script into paragraphs.
- Group narration toward the target scene length (estimated at 130 words/minute).
- Allocate scene timestamps proportionally so the final scene ends at the requested total duration.
- Produce a visual prompt draft for each scene.
- Export structured JSON and a readable Markdown storyboard.

## CLI

```bash
storyboard-engine build SCRIPT --duration 90 --scene-seconds 10 --out output
```

Arguments: `--duration` (total video duration, seconds), `--scene-seconds` (target scene duration), `--title` (optional project title), `--out` (output folder).

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
- [ ] Optional visual style presets
- [ ] Editing-tool import/export adapters
- [ ] Community language presets

## Contributing

Issues and pull requests are welcome. Please add tests for behavior changes and keep the core provider-agnostic.

## License

MIT. See [LICENSE](LICENSE).
