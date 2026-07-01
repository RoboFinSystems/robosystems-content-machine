#!/usr/bin/env node
/*
 * rs-render — the content-machine local renderer.
 *
 *   rs-render capture [--base-url URL] [--config PATH | --email E --password P]
 *                     [--scenes home,transactions,close,statements,reports,agents]
 *                     [--out DIR] [--viewport WxH] [--full-page]
 *
 *   rs-render short   --spec scenes/driftline.short.json [--out DIR] [--keep-frames]
 *
 * Python stays the orchestrator and owns audio (VO/music); this emits the
 * silent visual layer (stills for `capture`, an mp4 for `short`).
 */
import { capture } from './capture.mjs';
import { short } from './short.mjs';

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      if (key.includes('=')) {
        const [k, ...v] = key.split('=');
        args[k] = v.join('=');
      } else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
        args[key] = argv[++i];
      } else {
        args[key] = true; // boolean flag
      }
    } else {
      args._.push(a);
    }
  }
  return args;
}

async function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  const args = parseArgs(rest);

  switch (cmd) {
    case 'capture':
      await capture(args);
      break;
    case 'short':
      await short(args);
      break;
    default:
      console.error(
        `Unknown command: ${cmd ?? '(none)'}\n` +
          `Usage:\n  rs-render capture [options]\n  rs-render short --spec <file> [options]`
      );
      process.exit(1);
  }
}

main().catch((e) => {
  console.error(e?.stack || String(e));
  process.exit(1);
});
