# 0002 - Primary scope is the Dolomites, with the Alps and Tethys as context

Date: 2026-09-05 - Status: proposed

## Context

The owner asked whether to cover the Dolomites, South Tyrol, or the whole Alps.

## Decision

Primary geographic scope is the Dolomites (roughly the UNESCO World Heritage area and surroundings, 10.5-12.5 E, 46.0-47.0 N). The Alps and the western Tethys appear as context layers in the plate-tectonic chapters, where regional scale is the only honest scale anyway.

## Reasoning

- The Triassic platform-and-basin story is uniquely well documented in the Dolomites; this is why they are a World Heritage site. It gives the site a narrative spine that South Tyrol as an administrative region or the Alps as a whole do not.
- The province of Bolzano publishes some of the best open elevation data in Europe, and Trentino and Veneto have comparable data, so present-day terrain can be shown at very high resolution.
- Plate-scale chapters need the whole Mediterranean region regardless of primary scope, so widening the primary scope adds data work without adding story.
- The scope can be widened later chapter by chapter (for example an Oetztal basement chapter for wider South Tyrol) without changing the architecture.

## Consequences

Data pipelines target the Dolomites bounding box at high resolution and the Alps or Mediterranean at coarse resolution. Narrative chapters outside the Dolomites are out of scope for the first release.
