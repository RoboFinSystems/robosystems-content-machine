// node --test renderer/test: the walkthrough planner's cue pinning and the goto crossfade.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import sharp from 'sharp';
import { planBeat, cueTime, Recorder } from '../src/demo.mjs';

const words = [['Ask', 0.0], ['why', 0.3], ['cash', 0.6], ['is', 0.9], ['down,', 1.0], ['then', 1.6], ['approve.', 2.0]];

test('cueTime finds a phrase, ignoring case and punctuation', () => {
  assert.equal(cueTime(words, 'cash is down'), 0.6);
  assert.equal(cueTime(words, 'Approve'), 2.0);
  assert.equal(cueTime(words, 'not said'), null);
});

test('a cued action starts on its word and elastic dwells take only the rest', () => {
  const warns = [];
  const beat = {
    id: 'b', durationMs: 3000, _words: words,
    actions: [{ kind: 'move', ms: 300 }, { kind: 'click', cue: 'approve', ms: 300 }, { kind: 'dwell' }],
  };
  const plan = planBeat(beat, 30, (m) => warns.push(m));
  let pos = 0;
  const starts = plan.map((p) => { const at = pos; pos += p.frames; return [p.kind, at, p.frames]; });
  const click = starts.find(([k]) => k === 'click');
  assert.equal(click[1], 60, 'click starts at 2.0s = frame 60');
  assert.equal(pos, 90, 'the beat still fills its 3s exactly');
  assert.deepEqual(warns, []);
});

test('a missing cue warns and the beat still plays in order', () => {
  const warns = [];
  const plan = planBeat({ id: 'b', durationMs: 1000, actions: [{ kind: 'click', cue: 'x' }] }, 30, (m) => warns.push(m));
  assert.equal(plan.reduce((s, p) => s + p.frames, 0), 30);
  assert.match(warns[0], /no word timings/);
});

test('goto crossfade blends the previous frame into the next ones', async () => {
  const dir = await mkdtemp(path.join(tmpdir(), 'rec-'));
  const solid = (r, g, b) => sharp({ create: { width: 64, height: 36, channels: 3, background: { r, g, b } } }).png().toBuffer();
  let current = await solid(0, 0, 0);
  const page = { screenshot: async () => current };
  const rec = new Recorder(page, { W: 64, H: 36, fps: 30, dsf: 1, maxZoom: 1, framesDir: dir });
  rec.clip = () => ({ x: 0, y: 0, width: 64, height: 36 });
  await rec.shoot(); // black
  await rec.fadeFromLast(3);
  current = await solid(255, 255, 255);
  for (let i = 0; i < 4; i++) await rec.shoot();
  await rec.flush();
  const lum = async (n) => {
    const { data } = await sharp(await readFile(path.join(dir, `frame-${String(n).padStart(5, '0')}.png`))).raw().toBuffer({ resolveWithObject: true });
    return data[0];
  };
  const l = [await lum(0), await lum(1), await lum(2), await lum(3), await lum(4)];
  assert.equal(l[0], 0);
  assert.ok(l[1] > 0 && l[1] < l[2] && l[2] < l[3] && l[3] < 255, `ramps up: ${l}`);
  assert.equal(l[4], 255);
});
