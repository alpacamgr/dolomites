/**
 * Client-side chapter shape used by the story controller. This is the
 * scene subset of the full editorial chapter, plus what the shell needs
 * to render the legend and the age readout. Kept small so it can travel
 * as JSON in the initial HTML and does not depend on Zod at runtime.
 */
import type { SceneState, HonestyLabel } from '../scene-api';

export interface ClientLayer {
  id: string;
  label: HonestyLabel;
  source_ref: string | string[];
  style?: string;
  opacity?: number;
  /** short author-year citation resolved at build time from the bibliography (single source) */
  cite?: string;
  /** short citations of every source, in order, when `source_ref` is a list */
  cites?: string[];
}

export interface ClientChapter {
  id: string;
  index: number;
  /** localized chapter title, for the chapter navigation */
  title: string;
  view: 'globe' | 'terrain';
  time: { unit: 'ma' | 'ka'; start: number; end: number };
  camera: {
    globe?: { lat: number; lon: number; distance: number };
    terrain?: { lon: number; lat: number; zoom: number; pitch: number; bearing: number };
  };
  layers: ClientLayer[];
  source_refs: string[];
  /** past interval discussed while the scene shows another time (Ma, older first) */
  subject?: { start_ma: number; end_ma: number };
  /** scene.emphasis: age interval whose units the terrain geology emphasises (Ma, older first) */
  emphasis?: { start_ma: number; end_ma: number };
}

export function toSceneState(ch: ClientChapter, timeValue: number): SceneState {
  return {
    view: ch.view,
    time: { unit: ch.time.unit, value: timeValue },
    camera: ch.camera,
    layers: ch.layers,
    emphasis: ch.emphasis,
  };
}
