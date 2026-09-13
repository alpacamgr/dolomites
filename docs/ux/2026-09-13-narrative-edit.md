# Narrative edit, 2026-09-13

Editor: Claude (Fable 5.1). Scope: content/narrative/{en,de,it}/*.md and, if needed, the chapter `summary` strings in content/timeline/*.yaml. No new facts, no changes to code or ui strings.

## Voice
- One idea per sentence. Aim under 25 words. No exclamation marks, no imperatives to "imagine".
- Warm, precise, museum-panel tone. Plain words over jargon; keep a technical term only when it names the thing (dolomite, carbonate platform, thrust, nunatak, ignimbrite) and gloss it once.
- Every chapter: first sentence is a hook the reader can see on the screen at that moment (globe view vs terrain vs modelled ice vs today's glaciers).
- Second sentence sets the frame in one line. Body paragraphs unpack it.

## Facts rule
- Do not add any claim, number, place or interpretation that is not already in the chapter's markdown or in its facts list in content/timeline/*.yaml.
- The fact cards under the prose carry precision. Prose may say "for about five million years" or "close to the equator" and refer to the cards for exact values. High-precision dates and uncertainties (e.g. 242.653 +/- 0.036 Ma, +/- 43 km3) belong on the cards, not in the prose.
- Do not weaken hedges: model, reconstruction, contested, verification pending stay. A modelled result must not become an observed one.

## Structure
- Paragraph count stays roughly the same (2-5 per chapter). No headings, no bullet lists. Plain paragraphs.
- Intro: hook first, then the four honesty labels in two or three plain sentences, then a short methods paragraph that names the elevation and geology sources.

## Trilingual
- Each language written natively, not translated word for word. Same content, same hooks.
- Bilingual place names as already used: Schlern/Sciliar in en and de, Sciliar/Schlern in it. Rosengarten/Catinaccio in en and de, Catinaccio/Rosengarten in it. Bozen and Bolzano/Bozen used as appropriate.
- Number formats: en uses period as decimal, comma as thousands; de and it use comma as decimal, period as thousands.

## Log of numbers moved from prose to "refer to the card"

Chapter 02 (world-triassic)
- ICS base of Middle Triassic "247.0 Ma" -> "just after 247 million years ago" (card keeps 247.0).
- Muttoni 1997 Seceda paleolatitude kept as "sixteen to eighteen" (deg N) rather than "16 to 18 degrees north" - same value, plainer.

Chapter 05 (triassic-reefs)
- Storck 2019 high-precision zircon U-Pb dates: dropped every date and uncertainty from prose (242.653 +/- 0.036 Ma, 238.646 +/- 0.037 Ma, 238.190 +/- 0.055 Ma, 238.075 +/- 0.087 Ma, 237.680 +/- 0.047 Ma, 237.579 +/- 0.042 Ma). Prose now says the pulse ran "at least five million years", giving the qualitative sequence silicic -> basaltic -> silicic tuffs. Card carries every exact age.
- Storck 2019 "5.07 +/- 0.06 million years" -> "at least five million years" (card keeps precision).

Chapter 07 (ice-ages)
- Ivy-Ochs 2017 Marocche di Dro 36Cl ages: "5300 +/- 860" -> "about 5300 years ago"; "1080 +/- 160" -> "about 1080 years ago". Card keeps uncertainties.

Chapter 08 (today)
- Reinthaler & Paul 2025 Alps: "4244 km2 (1850) to 1806 km2 (2015), -57%" -> "fallen by more than half since the Little Ice Age peak around 1850".
- Same: "280 to 100 km3, -64%" -> "almost two thirds"; "-43.7 m" -> "over forty metres". The count "1938 vanished" kept in prose (it is memorable, integer, and specific).
- Securo 2025 Dolomites: "4.11 to 1.81 km2, -56%" -> "more than halved"; "-0.64 +/- 0.06 m w.e./yr" dropped from prose (card keeps it).

Left unchanged and why
- Chapter 01 keeps the qualitative range "roughly between 285 and 274 million years ago" (Marocchi 2008) and the Athesian Volcanic Group as "largest Permian volcanic district in Europe" (Chiaro 2024). Both are already round and central to the story.
- Chapter 04, 06, 08 keep the ALPS2017 GNSS rate "about 1.0 to 1.5 mm/yr" (spoken as "one to one and a half millimetres a year"). It is the headline present-day claim; the exact digits also live on the card.
- Chapter 07 keeps "about 2150 metres" for the modelled ice thickness above Bolzano, always paired with the hedge that this is model output for one grid cell, not a measurement.
- Chapter 07 keeps "about seventeen thousand years ago" for the start of high-valley deglaciation in Alta Badia (Rossato 2025); the later re-advance windows (15.8-15.4 ka; 14.4-13.3 ka) live only in the card, as before.
- Chapter 02 keeps the three model paleolatitudes (about seven, one, twelve degrees north) because the whole point of the paragraph is that the three disagree.

Hedges preserved everywhere: "contested" (02, 05), "model output ... not a measurement" (07), "unresolved" (05), "not on their own settle the question" (04), "reconstruction" and "model" everywhere they were used.


## Progress
- [x] Notes file
- [x] 00 intro (en/de/it)
- [x] 01 world-permian (en/de/it)
- [x] 02 world-triassic (en/de/it)
- [x] 03 world-jurassic-cretaceous (en/de/it)
- [x] 04 world-cenozoic (en/de/it)
- [x] 05 triassic-reefs (en/de/it)
- [x] 06 collision-uplift (en/de/it)
- [x] 07 ice-ages (en/de/it)
- [x] 08 today (en/de/it)
