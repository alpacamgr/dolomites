# Sources register

Two files, both built from the topic notes in `research/*/` once those are stable:

- `bibliography.md` - every paper, book, map, and web page cited anywhere in the project. The site derives short citations ("Tarquini et al. 2023") from the reference cell, which must start with "Surname I., Surname I. YYYY."; for institutions and portals fill the last column, `Short cite`, instead. Maintainer notes go in the section below the table, never in a reference cell, because reference cells are shown publicly. One entry per source with a citation key (`author-year`, e.g. `bosellini-2003`), full reference, URL or DOI, access date, and open-access status. Content files reference sources by this key.
- `license-register.md` - every dataset we use or plan to use, with license name, license URL, required attribution text, whether derivatives are allowed, and whether share-alike applies. One row per dataset manifest id.

Rules:
- A key is never reused or renamed once content references it.
- Unverified entries carry the same tags as the research notes and are removed rather than left unverified.
