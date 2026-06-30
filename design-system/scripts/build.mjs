#!/usr/bin/env node
/*
 * Regenerate _ds_bundle.js from the component sources, in the exact format the
 * Claude Design project (window.RoboSystemsContentDesignSystem_746ae7) consumes:
 * a Babel-transpiled (classic React.createElement runtime) IIFE that registers
 * each component on the namespace, wrapped per-component in a try/catch, with an
 * `@ds-bundle` header carrying sourceHashes. This is what makes component .jsx
 * edits round-trip — rebuild, then push _ds_bundle.js back via DesignSync.
 *
 *   npm run build      (or: just design-build)
 */
import { transformAsync } from '@babel/core';
import presetReact from '@babel/preset-react';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const NS = 'RoboSystemsContentDesignSystem_746ae7';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const COMPONENTS = path.join(ROOT, 'components');

// Babel plugin: drop `import React`, rewrite sibling DS component imports to
// `__ds_scope.X` references, and strip `export` so each module is a bare
// declaration we then register on __ds_scope.
function dsPlugin({ types: t }) {
  return {
    visitor: {
      ImportDeclaration(p) {
        const src = p.node.source.value;
        if (src === 'react' || src === 'react-dom') { p.remove(); return; }
        if (src.startsWith('.')) {
          for (const spec of p.node.specifiers) {
            const local = spec.local.name;
            const imported = t.isImportSpecifier(spec) ? spec.imported.name : local;
            const binding = p.scope.getBinding(local);
            if (binding) {
              for (const ref of binding.referencePaths) {
                ref.replaceWith(
                  t.memberExpression(t.identifier('__ds_scope'), t.identifier(imported))
                );
              }
            }
          }
          p.remove();
        }
      },
      ExportNamedDeclaration(p) {
        if (p.node.declaration) p.replaceWith(p.node.declaration);
        else p.remove();
      },
      ExportDefaultDeclaration(p) {
        p.replaceWith(p.node.declaration);
      },
    },
  };
}

async function discover() {
  const groups = (await readdir(COMPONENTS, { withFileTypes: true }))
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort();
  const comps = [];
  for (const group of groups) {
    const files = (await readdir(path.join(COMPONENTS, group)))
      .filter((f) => f.endsWith('.jsx'))
      .sort();
    for (const file of files) {
      comps.push({
        name: file.replace(/\.jsx$/, ''),
        sourcePath: `components/${group}/${file}`,
      });
    }
  }
  return comps;
}

async function build() {
  const comps = await discover();
  const sourceHashes = {};
  const modules = [];

  for (const c of comps) {
    const src = await readFile(path.join(ROOT, c.sourcePath), 'utf8');
    sourceHashes[c.sourcePath] = createHash('sha256').update(src).digest('hex').slice(0, 12);
    // Pass 1: JSX -> React.createElement (so element-type refs become plain
    // identifiers). Pass 2: strip imports/exports + rewrite sibling DS refs to
    // __ds_scope.X (now valid, since they are no longer JSX element names).
    const pass1 = await transformAsync(src, {
      configFile: false,
      babelrc: false,
      sourceType: 'module',
      comments: true,
      compact: false,
      presets: [[presetReact, { runtime: 'classic' }]],
    });
    const pass2 = await transformAsync(pass1.code, {
      configFile: false,
      babelrc: false,
      sourceType: 'module',
      comments: true,
      compact: false,
      plugins: [dsPlugin],
    });
    const body = pass2.code.trim();
    modules.push(
      `// ${c.sourcePath}\n` +
        `try { (() => {\n${body}\nObject.assign(__ds_scope, { ${c.name} });\n})(); } ` +
        `catch (e) { __ds_ns.__errors.push({ path: ${JSON.stringify(c.sourcePath)}, error: String((e && e.message) || e) }); }`
    );
  }

  const header = `/* @ds-bundle: ${JSON.stringify({
    format: 3,
    namespace: NS,
    components: comps.map((c) => ({ name: c.name, sourcePath: c.sourcePath })),
    sourceHashes,
    inlinedExternals: [],
    unexposedExports: [],
  })} */`;

  const exposes = comps.map((c) => `__ds_ns.${c.name} = __ds_scope.${c.name};`).join('\n\n');

  const bundle =
    `${header}\n\n` +
    `(() => {\n\n` +
    `const __ds_ns = (window.${NS} = window.${NS} || {});\n\n` +
    `const __ds_scope = {};\n\n` +
    `(__ds_ns.__errors = __ds_ns.__errors || []);\n\n` +
    modules.join('\n\n') +
    '\n\n' +
    exposes +
    '\n\n' +
    `})();\n`;

  await writeFile(path.join(ROOT, '_ds_bundle.js'), bundle);
  await writeFile(path.join(ROOT, '_ds_bundle.css'), '');
  console.log(`Built _ds_bundle.js — ${comps.length} components: ${comps.map((c) => c.name).join(', ')}`);
}

build().catch((e) => {
  console.error(e);
  process.exit(1);
});
