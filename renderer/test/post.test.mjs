import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cropStyle, slideHtml } from '../src/post.mjs';

const spec = { brand: 'robosystems', footer: 'Joseph French · robosystems.ai' };

test('a crop becomes an object-view-box with the crop aspect, and anything else is ignored', () => {
  assert.match(cropStyle([10, 20, 300, 100]), /object-view-box: xywh\(10px 20px 300px 100px\); aspect-ratio: 300 \/ 100/);
  assert.equal(cropStyle(undefined), '');
  assert.equal(cropStyle([1, 2, 3]), '');
});

test('a slide with a visual or an image defaults to the visual card', () => {
  assert.match(slideHtml({ title: 'T', visual: {} }, 0, 1, spec, '/work/v1.png'), /class="card visual-card"/);
  assert.match(slideHtml({ title: 'T', image: 'x.png' }, 0, 1, spec, '/spec/x.png'), /class="card shot-card"/);
});

test('a carousel numbers its pages and a single still does not', () => {
  assert.match(slideHtml({ kind: 'cover', title: 'T' }, 1, 4, spec, ''), /02 \/ 04/);
  assert.doesNotMatch(slideHtml({ kind: 'cover', title: 'T' }, 0, 1, spec, ''), /class="count"/);
});

test('spec text is escaped, never injected as markup', () => {
  const html = slideHtml({ kind: 'text', text: '<b>a & b</b>' }, 0, 1, spec, '');
  assert.match(html, /&lt;b&gt;a &amp; b&lt;\/b&gt;/);
});

test('an unknown kind fails loudly with the kinds it accepts', () => {
  assert.throws(() => slideHtml({ kind: 'poster' }, 0, 1, spec, ''), /unknown kind "poster"; expected cover, visual, number, text, end/);
});
