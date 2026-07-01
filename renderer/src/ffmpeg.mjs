/*
 * frames → mp4 via the system ffmpeg (already a content-machine dependency).
 * Silent video only — the Python pipeline muxes VO + ducked music downstream.
 */
import { spawn } from 'node:child_process';

/**
 * @param {object} opts
 * @param {string} opts.framePattern - printf pattern, e.g. frames/frame-%05d.png
 * @param {number} opts.fps
 * @param {string} opts.out - output .mp4 path
 */
export function framesToMp4({ framePattern, fps, out }) {
  const args = [
    '-y',
    '-framerate', String(fps),
    '-start_number', '0',
    '-i', framePattern,
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart',
    out,
  ];
  return new Promise((resolve, reject) => {
    const ff = spawn('ffmpeg', args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let err = '';
    ff.stderr.on('data', (d) => (err += d));
    ff.on('error', reject);
    ff.on('close', (code) =>
      code === 0 ? resolve(out) : reject(new Error(`ffmpeg exited ${code}\n${err.slice(-2000)}`))
    );
  });
}
