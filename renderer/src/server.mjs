/*
 * A tiny static file server for the `short` render harness. It serves the
 * design-system assets (tokens, fonts, the component bundle) and the React UMD
 * builds by URL, so the harness page can <link>/<script> them and @font-face
 * relative URLs resolve. In-memory HTML is served at '/'.
 */
import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.ttf': 'font/ttf',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

/**
 * @param {object} opts
 * @param {string} opts.html  - the harness HTML served at '/'
 * @param {Record<string,string>} opts.mounts - urlPrefix -> filesystem root
 * @returns {Promise<{url: string, close: () => Promise<void>}>}
 */
export async function serve({ html, mounts }) {
  const server = http.createServer(async (req, res) => {
    try {
      const url = decodeURIComponent((req.url || '/').split('?')[0]);
      if (url === '/' || url === '/index.html') {
        res.writeHead(200, { 'Content-Type': MIME['.html'] });
        res.end(html);
        return;
      }
      for (const [prefix, root] of Object.entries(mounts)) {
        if (url.startsWith(prefix)) {
          const rel = url.slice(prefix.length).replace(/^\/+/, '');
          const abs = path.join(root, rel);
          // contain traversal within root
          if (!abs.startsWith(path.resolve(root))) break;
          const s = await stat(abs).catch(() => null);
          if (s && s.isFile()) {
            const body = await readFile(abs);
            res.writeHead(200, { 'Content-Type': MIME[path.extname(abs)] || 'application/octet-stream' });
            res.end(body);
            return;
          }
        }
      }
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end(`404 ${url}`);
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end(String(e));
    }
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address();
  return {
    url: `http://127.0.0.1:${port}`,
    close: () => new Promise((r) => server.close(r)),
  };
}
