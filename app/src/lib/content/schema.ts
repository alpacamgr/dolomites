/**
 * Zod schemas for editorial content. Applied at build time by
 * `chapters.ts` so a malformed chapter file fails `astro build`
 * rather than surfacing as an empty page.
 * See `content/README.md` and `docs/04-data-contracts.md` sections 5 and 6.
 */
import { z } from 'zod';

export const LOCALES = ['en', 'de', 'it'] as const;
export type Locale = (typeof LOCALES)[number];

export const honestyLabel = z.enum(['observed', 'modeled', 'interpreted', 'illustrative']);
export type HonestyLabel = z.infer<typeof honestyLabel>;

const localizedString = z
  .object({
    en: z.string().optional(),
    de: z.string().optional(),
    it: z.string().optional(),
  })
  .refine((v) => LOCALES.some((k) => v[k] && v[k]!.trim().length > 0), {
    message: 'at least one locale must be filled',
  });

export const layerRefSchema = z.object({
  id: z.string().min(1),
  label: honestyLabel,
  /** bibliography key, or a list of keys for a layer merged from several sources */
  source_ref: z.union([z.string().min(1), z.array(z.string().min(1)).min(1)]),
  style: z.string().optional(),
  opacity: z.number().min(0).max(1).optional(),
});

const globeCamera = z.object({
  lat: z.number(),
  lon: z.number(),
  distance: z.number().positive(),
});

const terrainCamera = z.object({
  lon: z.number(),
  lat: z.number(),
  zoom: z.number(),
  pitch: z.number(),
  bearing: z.number(),
});

const sceneSchema = z.object({
  view: z.enum(['globe', 'terrain']),
  time: z.object({
    unit: z.enum(['ma', 'ka']),
    start: z.number(),
    end: z.number(),
  }),
  camera: z.object({
    globe: globeCamera.optional(),
    terrain: terrainCamera.optional(),
  }),
  layers: z.array(layerRefSchema).min(1),
  /** optional: emphasise geological units whose mapped age range lies within this interval */
  emphasis: z
    .object({ age_start_ma: z.number(), age_end_ma: z.number() })
    .refine((e) => e.age_start_ma > e.age_end_ma, { message: 'age_start_ma must be older (larger) than age_end_ma' })
    .optional(),
});

const factSchema = z.object({
  text: localizedString,
  value: z.union([z.string(), z.number()]).optional(),
  source_ref: z.string().min(1),
  confidence: z.enum(['established', 'debated']).optional(),
  verification: z.enum(['pending', 'verified']).optional(),
});

const localitySchema = z.object({
  id: z.string().optional(),
  name: z.string().optional(),
  lat: z.number().optional(),
  lon: z.number().optional(),
  what_to_see: localizedString.optional(),
  source_ref: z.string().optional(),
});

export const chapterSchema = z.object({
  id: z.string().min(1),
  title: localizedString,
  age_start_ma: z.number().optional(),
  age_end_ma: z.number().optional(),
  age_start_ka: z.number().optional(),
  age_end_ka: z.number().optional(),
  /** chapters that show today's terrain but discuss a past interval */
  subject_age_start_ma: z.number().optional(),
  subject_age_end_ma: z.number().optional(),
  ics_stage: z.string().optional(),
  ics_chart_version: z.string().optional(),
  summary: localizedString.optional(),
  map_state: z.object({ layers: z.array(layerRefSchema).optional() }).optional(),
  facts: z.array(factSchema).optional(),
  localities: z.array(localitySchema).optional(),
  review: z
    .object({ reviewer: z.string().optional(), date: z.string().optional() })
    .optional(),
  scene: sceneSchema,
});

export type Chapter = z.infer<typeof chapterSchema>;
export type LayerRef = z.infer<typeof layerRefSchema>;
export type Scene = z.infer<typeof sceneSchema>;
