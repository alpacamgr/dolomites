# Content

Editorial content, kept apart from code so that a geologist can review it without touching the app.

## `timeline/`

One YAML file per chapter, ordered by age. Draft schema (to be finalized in the architecture doc):

```yaml
id: ladinian-platforms
title:
  de: ""
  it: ""
  en: ""
age_start_ma: 242.0        # older bound
age_end_ma: 237.0          # younger bound
ics_stage: Ladinian        # from the ICS chart version named in research/sources
ics_chart_version: ""
summary:
  de: ""
  it: ""
  en: ""
map_state:                 # what the map shows during this chapter
  layers:
    - id: ""               # references a dataset manifest id
      label: interpreted   # observed | modeled | interpreted | illustrative
      source_ref: ""       # citation key from research/sources
facts:
  - text: { de: "", it: "", en: "" }
    value: ""              # optional number with unit
    source_ref: ""         # citation key, required
    confidence: established   # established | debated
localities:
  - name: ""
    lat: 0.0
    lon: 0.0
    what_to_see: { de: "", it: "", en: "" }
    source_ref: ""
review:
  reviewer: ""
  date: ""
```

## `narrative/`

Longer prose per chapter, one folder per language: `narrative/de/`, `narrative/it/`, `narrative/en/`. Markdown with front matter linking to the chapter id. Citations use `[@key]` where `key` is defined in `research/sources/`.
