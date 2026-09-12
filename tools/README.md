# Tools

Maintenance and QA scripts that are not part of the data pipeline or the app.

| Tool | What it does | Run |
|---|---|---|
| `qa/screenshot-chapters.mjs` | Launches headless Chrome (GPU) over the DevTools protocol, scrolls to each chapter of the running site, and saves screenshots plus console errors. Use it for visual QA; the in-app browser pane returns blank screenshots when hidden. | `node tools/qa/screenshot-chapters.mjs --base http://localhost:4332 --lang en --out <dir> [--width 1440 --height 900] [--progress 0.3,0.85] [--only ice-ages] [--port 9333]` |
| `build_license_register.py` | Regenerates `research/sources/license-register.md` from `data/manifests/*.yaml` and lists manifests with a missing license, missing attribution, or invalid YAML. | `.venv/Scripts/python.exe tools/build_license_register.py` |

Planned:

- `validate-manifests` - check every manifest against the template fields and its checksum against `data/raw/`.
- `check-citations` - check that every `source_ref` and `[@key]` in `content/` exists in the bibliography.
- `check-links` - check that URLs in research notes and the bibliography still resolve.
