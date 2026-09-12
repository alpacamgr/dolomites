#!/usr/bin/env node
/**
 * Visual QA: screenshot every chapter of the running site in headless Chrome.
 * No dependencies (Node >= 22 for the global WebSocket). Drives Chrome over the
 * DevTools protocol, scrolls to each chapter at the given progress fractions,
 * waits in real time so the WebGL engines load and render, and saves PNGs plus
 * a console-error log.
 *
 * Usage:
 *   node tools/qa/screenshot-chapters.mjs --base http://localhost:4332 --lang en \
 *     --out <dir> [--width 1440 --height 900 --dpr 1] [--progress 0.35,0.8] \
 *     [--wait 7000] [--only ice-ages,today] [--port 9333] [--chrome "C:/Program Files/Google/Chrome/Application/chrome.exe"]
 *     [--mid 300]  extra capture 300 ms after each scroll (motion mid-transition, suffix -t300)
 *     [--hover ".gkey li:nth-child(2) .gkey-row" | --hover 900,500]  extra capture while hovering (suffix -hover)
 * Use a distinct --port when several agents run it at the same time.
 */
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => (a.startsWith('--') ? [...acc, [a.slice(2), all[i + 1]]] : acc), []),
);
const base = (args.base ?? 'http://localhost:4332').replace(/\/+$/, '');
const lang = args.lang ?? 'en';
const out = args.out ?? join(tmpdir(), 'dolomites-qa');
const width = Number(args.width ?? 1440);
const height = Number(args.height ?? 900);
const dpr = Number(args.dpr ?? 1);
const waitMs = Number(args.wait ?? 7000);
const progress = (args.progress ?? '0.35').split(',').map(Number);
const only = args.only ? new Set(args.only.split(',')) : null;
const chrome = args.chrome ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const port = Number(args.port ?? 9333);
/** optional extra capture this many ms after the scroll (motion mid-transition), e.g. --mid 300 */
const midMs = Number(args.mid ?? 0);
/** optional hover after the settled capture: a CSS selector or "x,y", e.g. --hover ".gkey li:nth-child(2) .gkey-row" */
const hover = args.hover ?? null;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

mkdirSync(out, { recursive: true });
const profile = join(out, '.chrome-profile');
const proc = spawn(chrome, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  `--window-size=${width},${height}`, '--ignore-gpu-blocklist', '--enable-gpu-rasterization',
  '--no-first-run', '--no-default-browser-check', 'about:blank',
], { stdio: 'ignore' });

let ws;
let nextId = 1;
const pending = new Map();
const errors = [];

function send(method, params = {}) {
  const id = nextId++;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

async function connect() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* chrome still starting */ }
    await sleep(200);
  }
  throw new Error('Chrome DevTools endpoint did not come up');
}

async function evaluate(expression) {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text);
  return r.result.value;
}

async function main() {
  ws = new WebSocket(await connect());
  await new Promise((r) => ws.addEventListener('open', r, { once: true }));
  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? p.reject(new Error(msg.error.message)) : p.resolve(msg.result);
    } else if (msg.method === 'Runtime.exceptionThrown') {
      errors.push(`exception: ${msg.params.exceptionDetails.exception?.description ?? msg.params.exceptionDetails.text}`);
    } else if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') {
      errors.push(`log: ${msg.params.entry.text} ${msg.params.entry.url ?? ''}`);
    } else if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
      errors.push(`console: ${msg.params.args.map((a) => a.value ?? a.description).join(' ')}`);
    }
  });

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Log.enable');
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: dpr, mobile: false });
  await send('Page.navigate', { url: `${base}/${lang}/` });
  await sleep(waitMs + 3000);

  const gpu = await evaluate(`(() => { const c = document.createElement('canvas').getContext('webgl2'); const e = c && c.getExtension('WEBGL_debug_renderer_info'); return e ? c.getParameter(e.UNMASKED_RENDERER_WEBGL) : String(!!c); })()`);
  const chapters = await evaluate(`[...document.querySelectorAll('[data-chapter]')].map(s => s.dataset.chapter)`);
  console.log(`renderer: ${gpu}`);
  console.log(`chapters: ${chapters.join(', ')}`);

  for (const [index, id] of chapters.entries()) {
    if (only && !only.has(id)) continue;
    for (const p of progress) {
      await evaluate(`(() => {
        const s = document.querySelector('[data-chapter="${id}"]');
        const top = s.getBoundingClientRect().top + window.scrollY;
        window.scrollTo(0, Math.round(top + ${p} * Math.max(0, s.offsetHeight - window.innerHeight)));
      })()`);
      const stem = join(out, `${String(index).padStart(2, '0')}-${id}-p${Math.round(p * 100)}`);
      const save = async (suffix) => {
        // age readout plus the legend footprint: share of the stage, internal scrolling, overlap with the time rail
        const state = await evaluate(`(() => {
          const r = (s) => document.querySelector(s)?.getBoundingClientRect();
          const st = r('.stage'), lg = r('.legend'), rl = r('.timerail'), b = document.querySelector('.legend-body');
          const layout = st && lg ? 'legend ' + Math.round((lg.height / st.height) * 100) + '%'
            + (b && b.scrollHeight > b.clientHeight + 1 ? ' SCROLLS' : '') + (rl && lg.top < rl.bottom ? ' OVERLAPS-RAIL' : '') : '';
          return { age: document.querySelector('.age')?.textContent?.trim() ?? null, layout };
        })()`);
        const shot = await send('Page.captureScreenshot', { format: 'png' });
        writeFileSync(`${stem}${suffix}.png`, Buffer.from(shot.data, 'base64'));
        console.log(`saved ${stem}${suffix}.png  age=${state.age}  ${state.layout}`);
      };
      if (midMs > 0 && midMs < waitMs) {
        await sleep(midMs);
        await save(`-t${midMs}`);
        await sleep(waitMs - midMs);
      } else await sleep(waitMs);
      await save('');
      if (hover) {
        // "x,y" hovers a stage point; anything else is a CSS selector hovered at its centre
        const xy = /^\d+,\d+$/.test(hover) ? hover.split(',').map(Number) : null;
        const pt = xy ? { x: xy[0], y: xy[1] } : await evaluate(`(() => { const el = document.querySelector(${JSON.stringify(hover)}); if (!el) return null; const r = el.getBoundingClientRect(); return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) }; })()`);
        if (pt) {
          await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: pt.x, y: pt.y });
          await sleep(1500);
          await save('-hover');
          await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 2, y: 2 });
          await sleep(300);
        } else console.log(`hover target not found: ${hover}`);
      }
    }
  }

  writeFileSync(join(out, 'console-errors.txt'), errors.join('\n') || '(none)');
  console.log(`console errors: ${errors.length}`);
}

main()
  .catch((e) => { console.error(e); process.exitCode = 1; })
  .finally(() => { try { ws?.close(); } catch {} proc.kill(); });
