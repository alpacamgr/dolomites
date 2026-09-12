/**
 * Read `app/public/data/ics-chart.json` at build time if it exists.
 * The file is produced by a pipeline agent; when it is missing the rail
 * shows only the age readout and no coloured period band. We never
 * fabricate stage names or ages.
 */
import fs from 'node:fs';
import path from 'node:path';
import { PUBLIC_DATA_DIR } from './paths';

export interface IcsInterval {
  name: string;
  type: string;
  parent?: string;
  start_ma: number;
  end_ma: number;
  color?: string;
}

export interface IcsChart {
  version: string;
  source_ref: string;
  intervals: IcsInterval[];
}

let cache: IcsChart | null | undefined;

export function loadIcs(): IcsChart | null {
  if (cache !== undefined && !import.meta.env.DEV) return cache;
  const file = path.join(PUBLIC_DATA_DIR, 'ics-chart.json');
  if (!fs.existsSync(file)) {
    cache = null;
    return null;
  }
  try {
    const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (!parsed || !Array.isArray(parsed.intervals)) {
      cache = null;
      return null;
    }
    cache = parsed as IcsChart;
    return cache;
  } catch {
    cache = null;
    return null;
  }
}
