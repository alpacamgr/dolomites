/**
 * Fetches globe/dolomites-path.json at runtime and linearly interpolates
 * the paleolatitude for a given age in Ma. Returns null when the file is
 * missing (pipeline agent has not produced it yet) or the age is outside
 * the samples: the UI then shows an em dash rather than a fabricated
 * number.
 */
export interface PaleoPathSample {
  ma: number;
  lat: number;
  lon: number;
}

export interface PaleoPath {
  reference_point: { lat: number; lon: number };
  plate_id: number;
  model: string;
  samples: PaleoPathSample[];
}

let cache: Promise<PaleoPath | null> | null = null;

export function loadPaleoPath(base = '/data'): Promise<PaleoPath | null> {
  if (cache) return cache;
  cache = fetch(`${base}/globe/dolomites-path.json`, { cache: 'force-cache' })
    .then(async (r) => {
      if (!r.ok) return null;
      const raw = (await r.json()) as PaleoPath;
      if (!raw || !Array.isArray(raw.samples)) return null;
      // Sort ascending by ma for predictable interpolation
      raw.samples = [...raw.samples].sort((a, b) => a.ma - b.ma);
      return raw;
    })
    .catch(() => null);
  return cache;
}

export function paleoLatAt(path: PaleoPath | null, ma: number): number | null {
  if (!path || path.samples.length === 0) return null;
  const s = path.samples;
  if (ma <= s[0].ma) return s[0].lat;
  if (ma >= s[s.length - 1].ma) return s[s.length - 1].lat;
  for (let i = 0; i < s.length - 1; i++) {
    const a = s[i];
    const b = s[i + 1];
    if (ma >= a.ma && ma <= b.ma) {
      const t = (ma - a.ma) / (b.ma - a.ma);
      return a.lat + (b.lat - a.lat) * t;
    }
  }
  return null;
}
