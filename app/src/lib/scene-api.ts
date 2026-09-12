/**
 * Contract between the story controller and the two rendering engines.
 * See docs/04-data-contracts.md section 6. Do not add engine-specific
 * members here; put them behind the engine's own options object.
 */

export type HonestyLabel = 'observed' | 'modeled' | 'interpreted' | 'illustrative';

export interface LayerRef {
  /** dataset id, matches data/manifests/<id>.yaml and meta.json */
  id: string;
  label: HonestyLabel;
  /** bibliography key(s) in research/sources/bibliography.md; a list for layers merged from several sources */
  source_ref: string | string[];
  /** engine-specific style name, optional */
  style?: string;
  /** 0..1, default 1 */
  opacity?: number;
}

export interface GlobeCamera {
  lat: number;
  lon: number;
  /** distance from Earth centre in Earth radii (1 = surface). Typical 2.2..3.5 */
  distance: number;
}

export interface TerrainCamera {
  lon: number;
  lat: number;
  zoom: number;
  pitch: number;
  bearing: number;
}

export type TimeUnit = 'ma' | 'ka';

export interface SceneState {
  view: 'globe' | 'terrain';
  time: { unit: TimeUnit; value: number };
  camera: { globe?: GlobeCamera; terrain?: TerrainCamera };
  layers: LayerRef[];
  /**
   * Optional age interval to emphasise (Ma, older first). Engines that draw data coloured
   * by age (terrain geology) emphasise units whose mapped age range lies within it and dim
   * the rest; other engines ignore it.
   */
  emphasis?: { start_ma: number; end_ma: number };
}

export interface EngineStatus {
  /** true while textures / tiles for the current state are still loading */
  loading: boolean;
  /** attribution strings the engine wants shown for the visible layers */
  attributions: string[];
}

/**
 * A rendering engine bound to a container element. Implementations must:
 *  - be cheap to construct; heavy assets load on first `setState`
 *  - not allocate per frame; run their render loop only while something changes
 *  - resolve `setState` when the state is visually applied (assets loaded)
 *  - cap devicePixelRatio at 2
 */
export interface SceneEngine {
  readonly kind: 'globe' | 'terrain';
  mount(container: HTMLElement): Promise<void>;
  /** Apply a full state. Called at most once per animation frame by the controller. */
  setState(state: SceneState): Promise<void>;
  /** Cheap partial update used while scrolling: only time changes. */
  setTime(unit: TimeUnit, value: number): void;
  /** Cheap partial update: camera only; the engine eases toward it. */
  setCamera(camera: GlobeCamera | TerrainCamera, durationMs?: number): void;
  /** Ask the engine to fetch what it will need for `state` without showing it. */
  preload(state: SceneState): Promise<void>;
  /** Stop the render loop and release GPU resources that are not needed to resume quickly. */
  pause(): void;
  resume(): void;
  onStatus(cb: (status: EngineStatus) => void): () => void;
  resize(): void;
  dispose(): void;
}

export interface EngineFactory {
  (options?: Record<string, unknown>): SceneEngine;
}
