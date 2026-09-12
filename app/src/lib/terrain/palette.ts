/**
 * Palettes for the terrain engine.
 *
 * Elevation tint: a muted alpine hypsometric tint in the tradition of printed
 * Swiss/Austrian atlases. It is a cartographic height ramp, not land cover:
 * soft green valley floors (< 900 m), muted olive-green slopes (900-1800 m),
 * pale sage/khaki alpine meadow (1800-2400 m), warm light grey rock (2400-3000 m)
 * and very light grey to near-white above ~3100 m. It deliberately departs from
 * the globe palette, which covers a 0-6500 m range at a much smaller scale; on
 * that ramp the Dolomites would sit entirely in its ochre-brown band.
 *
 * The DEM encodes nodata as exactly 0 m (see terrain meta.json), and no ground in
 * the bbox is that low, so heights below 1 m are drawn transparent.
 */

export type ColorStop = [elevation_m: number, color: string];

export const ALPINE_STOPS: ColorStop[] = [
  [1, '#c6d3a8'],     // plain and lowest valley floors
  [400, '#bfd0a0'],   // valley floors: soft green
  [900, '#afc390'],   // lower slopes
  [1300, '#a5b886'],  // muted olive-green forest belt
  [1800, '#b2b98f'],  // upper slopes
  [2100, '#c6c59f'],  // pale sage / khaki alpine meadow
  [2400, '#d3cdb5'],  // meadow to rock transition
  [2700, '#dbd6ca'],  // warm light grey rock
  [3000, '#e6e3dc'],
  [3150, '#eeede9'],  // very light grey
  [3400, '#f8f7f4'],  // near-white summits
];

/** `color-relief-color` expression; nodata (0 m) stays transparent. */
export function elevationExpression(stops: ColorStop[] = ALPINE_STOPS): unknown[] {
  const expr: unknown[] = ['interpolate', ['linear'], ['elevation'], 0.5, 'rgba(0,0,0,0)'];
  for (const [h, c] of stops) {
    if (h > (expr[expr.length - 2] as number)) expr.push(h, c);
  }
  return expr;
}

/**
 * Geology: a unit is coloured by age only when the source names an age that maps to an
 * ICS interval (`color` is that interval's official colour). Units without one get a
 * light cool neutral that no ICS colour in the 300 Ma window uses, so they read as
 * "mapped, age not given" rather than as missing data; the legend key shows the same swatch.
 */
export const GEOLOGY_UNDATED_FILL = '#e4e7e8';

export const geologyIsDatedExpression = ['==', ['typeof', ['get', 'color']], 'string'];

export function geologyFillColorExpression(): unknown[] {
  return ['case', geologyIsDatedExpression, ['to-color', ['get', 'color'], GEOLOGY_UNDATED_FILL], GEOLOGY_UNDATED_FILL];
}

export function isDatedColor(color: unknown): color is string {
  return typeof color === 'string' && /^#[0-9a-f]{3,8}$/i.test(color);
}

/** DISS 3.3.1 source types: individual (polygon), composite_top / debated (lines). */
export function faultColorExpression(): unknown[] {
  return ['match', ['get', 'type'],
    'individual', '#8a3324',
    'composite', '#a44a2a',
    'composite_top', '#a44a2a',
    'debated', '#7d7466',
    '#6b5d4f'];
}

/**
 * Display ramp for modelled ice thickness (metres -> RGBA, alpha 0..1): bright
 * white-blue, thin ice translucent so the bed relief still reads, thick ice
 * nearly opaque. Applied on the client to the published frames by inverting
 * their own `thickness_stops_m` (see ice.ts), so no thickness value is invented.
 */
export const ICE_DISPLAY_STOPS: Array<[number, [number, number, number, number]]> = [
  // thin ice: near-white and translucent; thick trunk glaciers: deeper blue, so ice-filled
  // valleys read darker than thinly covered ridges and ice-free nunataks stay bare rock
  [0, [240, 246, 251, 0]],
  [10, [240, 246, 251, 0.35]],
  [80, [232, 241, 249, 0.55]],
  [250, [212, 229, 245, 0.72]],
  [600, [184, 211, 236, 0.82]],
  [1200, [156, 191, 225, 0.87]],
  [2000, [138, 178, 218, 0.9]],
];
