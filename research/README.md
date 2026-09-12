# Research notes

Sourced notes that feed the feasibility assessment, the architecture, and the editorial content. Nothing here is final; everything here is cited.

## Folders

| Folder | Question it answers |
|---|---|
| `geology/` | What happened, when, and what rock records it? |
| `tectonics/` | Which plate reconstruction datasets exist, at what scale, and under what license? |
| `elevation/` | Which present-day DEMs, imagery, and geological maps cover the area? |
| `glaciation/` | What data exists for the ice ages, current glaciers, uplift rates, and climate curves? |
| `prior-art/` | Who has built something similar, and what did they get right or wrong? |
| `tech/` | Which rendering, tiling, and site technologies fit? |
| `sources/` | Master bibliography and license register, built from the notes above. |

## Writing conventions

- One Markdown file per topic. Add new files rather than growing one file past about 500 lines.
- Every factual statement carries a verification tag:
  - `[verified YYYY-MM-DD]` - the source was opened and the claim checked against it.
  - `[from search, not opened]` - the source appeared in search results but was not read.
  - `[unverified - from memory]` - written without a source; must be verified or removed before use.
- Each file ends with `## Sources` (title, authors, year, URL, access date, license) and `## Open questions / gaps`.
- Datasets that look usable get a manifest in `data/manifests/` once downloaded, not before.
- Prefer primary sources: papers, dataset landing pages, official portals. Wikipedia is a starting point, never a citation.
