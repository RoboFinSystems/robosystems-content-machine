/*
 * The film stage: what every page built on the brand film's form shares, so the look lives in
 * one place. A page (ad.html, film.html) imports this, takes the
 * stage, and keeps only its own scenes.
 *
 *   import { stage, fonts, seg, eo, eio, lerp, show, $ } from './film_stage.js'
 *   const S = stage({ W, H, canvas: $('gl') })     // once
 *   ... in seek(t): set S.scene.background, what is visible, the camera; then S.composer.render()
 *
 * The stage holds the renderer with its bloom, the lens (points that blur off the focal plane),
 * the dust, the graph (150 facts, scattered or at home on a sphere), the floor grid, and the
 * three backgrounds: DARK (the stage), BLACK (under a Blender plate, which is screened over it)
 * and FLOOD (the blue to indigo field, held for a film's turn). It also holds the clusters: the
 * knowledge graph as it is drawn on robosystems.ai, hidden until a page shows it
 * (S.clusters.group, .set(t, home), .look({ alpha, links, focus, aperture })). Colours are tokens/film.css
 * written out, because three.js cannot read CSS. The page's stylesheet half is film_stage.css.
 *
 * Everything is seeded: `rnd` is one sequence, drawn first for the dust, then for the graph.
 * A page that scatters things of its own draws from S.rnd after that, so a film renders the
 * same picture every time.
 */
import * as THREE from 'three'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'

export const clamp = (x) => Math.max(0, Math.min(1, x))
export const seg = (t, a, b) => clamp((t - a) / (b - a))
export const eo = (x) => 1 - Math.pow(1 - clamp(x), 3)
export const eio = (x) => ((x = clamp(x)), x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2)
export const lerp = (a, b, p) => a + (b - a) * p
export const $ = (id) => document.getElementById(id)
// in: 0..1 entrance; out: 0..1 exit. Blur to sharp on the way in, a plain fade on the way out.
export const show = (el, pin, pout = 0, dy = 24) => { const e = eo(pin); el.style.opacity = clamp(pin * 1.4) * (1 - eo(pout)); el.style.filter = e < 1 ? `blur(${(1 - e) * 14}px)` : ''; el.style.translate = `0 ${(1 - e) * dy}px` }

// the faces a film's type is set in, loaded before the first frame
export const fonts = async () => {
  await Promise.all(['900 40px Orbitron', '500 40px "Space Grotesk"', '700 40px "Space Grotesk"'].map((f) => document.fonts.load(f)))
  await document.fonts.ready
}

export function stage({ W, H, canvas }) {
  let sd = 11
  const rnd = () => ((sd = (sd * 16807) % 2147483647), sd / 2147483647)

  const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, preserveDrawingBuffer: true })
  renderer.setPixelRatio(1); renderer.setSize(W, H, false)
  const scene = new THREE.Scene()
  const cam = new THREE.PerspectiveCamera(38, W / H, 0.1, 400)
  const composer = new EffectComposer(renderer)
  composer.addPass(new RenderPass(scene, cam))
  const bloom = new UnrealBloomPass(new THREE.Vector2(W, H), 0.55, 0.7, 0.82)
  composer.addPass(bloom); composer.addPass(new OutputPass())

  const DARK = new THREE.Color('#04070c'), BLACK = new THREE.Color('#000000')
  const gc = Object.assign(document.createElement('canvas'), { width: 512, height: 288 })
  const gx = gc.getContext('2d'); const gr = gx.createLinearGradient(0, 0, 512, 288)
  gr.addColorStop(0, '#0891B2'); gr.addColorStop(0.52, '#2563EB'); gr.addColorStop(1, '#6366F1'); gx.fillStyle = gr; gx.fillRect(0, 0, 512, 288)
  const FLOOD = new THREE.CanvasTexture(gc); FLOOD.colorSpace = THREE.SRGBColorSpace

  // points with a lens: off the focal plane a point grows and thins, so depth reads as bokeh
  const pointMat = (color, boost) => new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uFocus: { value: 12 }, uAperture: { value: 0.08 }, uColor: { value: new THREE.Color(color).multiplyScalar(boost) }, uAlpha: { value: 1 } },
    vertexShader: `attribute float size; uniform float uFocus, uAperture; varying float vA;
      void main(){ vec4 mv = modelViewMatrix * vec4(position,1.); float d = -mv.z; float coc = abs(d-uFocus)*uAperture;
        gl_PointSize = (size + coc*5.) * 60. / d; gl_Position = projectionMatrix * mv; vec2 n = abs(gl_Position.xy / gl_Position.w);
        vA = smoothstep(1.5, 5., d) * smoothstep(1.02, 0.84, max(n.x, n.y)) / (1. + coc*coc*1.6); }`,
    fragmentShader: `uniform vec3 uColor; uniform float uAlpha; varying float vA;
      void main(){ float r = length(gl_PointCoord-.5); float a = smoothstep(.5,.32,r); gl_FragColor = vec4(uColor, a*vA*uAlpha); }`,
  })
  const cloud = (n, mat) => { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3)); g.setAttribute('size', new THREE.BufferAttribute(new Float32Array(n), 1)); const p = new THREE.Points(g, mat); p.frustumCulled = false; scene.add(p); return p }

  const ND = 1600, dust = cloud(ND, pointMat('#22D3EE', 1.3))
  for (let i = 0; i < ND; i++) { dust.geometry.attributes.position.setXYZ(i, (rnd() - 0.5) * 60, (rnd() - 0.5) * 34, -rnd() * 110 + 8); dust.geometry.attributes.size.setX(i, 0.3 + rnd() * 0.8) }

  // the graph: scattered at first, at home on a sphere
  const N = 150, R = 3.4, nodes = cloud(N, pointMat('#ffffff', 2.2))
  const scat = [], home = []
  for (let i = 0; i < N; i++) {
    scat.push(new THREE.Vector3((rnd() - 0.5) * 44, (rnd() - 0.5) * 24, -rnd() * 46 + 4))
    const y = 1 - (i / (N - 1)) * 2, r = Math.sqrt(1 - y * y), a = i * 2.39996
    home.push(new THREE.Vector3(Math.cos(a) * r * R, y * R, Math.sin(a) * r * R))
    nodes.geometry.attributes.size.setX(i, rnd() > 0.82 ? 3.4 : 1.9)
  }
  const pairs = []
  home.forEach((h, i) => home.map((m, j) => [h.distanceTo(m), j]).sort((a, b) => a[0] - b[0]).slice(1, 4).forEach(([, j]) => i < j && pairs.push([i, j])))
  const ev = []; pairs.forEach(([i, j]) => ev.push(home[i].x, home[i].y, home[i].z, home[j].x, home[j].y, home[j].z))
  const edgeMat = new THREE.LineBasicMaterial({ color: new THREE.Color('#ffffff'), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false })
  const edges = new THREE.LineSegments(new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(ev, 3)), edgeMat); edges.frustumCulled = false
  const globe = new THREE.Group(); globe.add(edges); globe.add(nodes); scene.add(globe)
  const setNodes = (p) => { home.forEach((h, i) => { const s = scat[i]; nodes.geometry.attributes.position.setXYZ(i, lerp(s.x, h.x, p), lerp(s.y, h.y, p), lerp(s.z, h.z, p)) }); nodes.geometry.attributes.position.needsUpdate = true }

  // the floor: a ledger grid running to the horizon
  const fl = []; for (let i = -40; i <= 40; i++) { fl.push(i * 1.5, 0, 0, i * 1.5, 0, -120); if (i >= 0) fl.push(-60, 0, -i * 1.5, 60, 0, -i * 1.5) }
  const floorMat = new THREE.LineBasicMaterial({ color: new THREE.Color('#22D3EE'), transparent: true, opacity: 0.6 })
  const floor = new THREE.LineSegments(new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(fl, 3)), floorMat); scene.add(floor)

  // the knowledge graph in clusters: the picture in robosystems.ai's hero, node for node (the
  // same seed and the same draws as robosystems-app's graphStageGl.ts; change one and change
  // the other). Nodes sit in clusters about white hubs, drift a little, and a pulse of light
  // travels each link between hubs. It keeps a sequence of its own and stays hidden until a
  // page shows it, so it moved nothing in the films made before it.
  const clusters = (() => {
    let sd2 = 11; const r = () => ((sd2 = (sd2 * 16807) % 2147483647), sd2 / 2147483647)
    for (let i = 0; i < 900 * 4; i++) r() // the site draws its dust first
    const DEF = [[46, '#66E8FA'], [42, '#3B7AF5'], [38, '#828CF7'], [34, '#21D4ED'], [32, '#61A6FA'], [28, '#6366F2'], [24, '#66E8FA'], [20, '#3B7AF5']]
    const scat = [], at = [], size = [], drift = [], kind = [], pairs = [], hubs = []
    const near = (i, among, n) => among.filter((j) => j !== i).sort((p, q) => at[i].distanceToSquared(at[p]) - at[i].distanceToSquared(at[q])).slice(0, n)
    DEF.forEach(([count], c) => {
      const y = 1 - ((c + 0.5) / DEF.length) * 2, q = Math.sqrt(1 - y * y), a = c * 2.39996 + 0.6
      const centre = new THREE.Vector3(Math.cos(a) * q * 3.0, y * 2.6, Math.sin(a) * q * 2.6), spread = 0.46 + count * 0.011, members = []
      for (let m = 0; m < count; m++) {
        const hub = m === 0, off = () => (hub ? 0 : (r() + r() + r() - 1.5) * spread)
        scat.push(new THREE.Vector3((r() - 0.5) * 44, (r() - 0.5) * 24, -r() * 46 + 4))
        at.push(new THREE.Vector3(centre.x + off(), centre.y + off(), centre.z + off()))
        size.push(hub ? 4.4 : 1.4 + r() * 1.3); drift.push(hub ? 0.03 : 0.05 + r() * 0.07); kind.push(hub ? DEF.length : c); members.push(at.length - 1)
      }
      hubs.push(members[0])
      members.slice(1).forEach((n) => {
        if (r() < 0.62) pairs.push([members[0], n]); else pairs.push([n, near(n, members.slice(1), 1)[0]])
        if (r() < 0.3) pairs.push([n, near(n, members.slice(1), 2)[1]])
      })
    })
    const fit = Math.min(1, 3.25 / Math.max(...at.map((v) => v.length()))); at.forEach((v) => v.multiplyScalar(fit))
    const routes = []
    hubs.forEach((h) => near(h, hubs, 2).forEach((o) => routes.some(([p, q]) => p === o && q === h) || routes.push([h, o])))
    pairs.push(...routes)

    const group = new THREE.Group(); group.visible = false; scene.add(group)
    // one cloud per colour, the hubs in white, and the pulses
    const tints = [...DEF.map(([, hex]) => [hex, 1.9]), ['#ffffff', 2.2]]
    const clouds = tints.map(([hex, boost], c) => { const ids = kind.map((k, i) => (k === c ? i : -1)).filter((i) => i >= 0), cl = cloud(ids.length, pointMat(hex, boost))
      ids.forEach((i, k) => cl.geometry.attributes.size.setX(k, size[i])); group.add(cl); return { cl, ids } })
    const pulse = cloud(routes.length, pointMat('#ffffff', 2.4)); for (let k = 0; k < routes.length; k++) pulse.geometry.attributes.size.setX(k, 2.4); group.add(pulse)
    const lgeo = new THREE.BufferGeometry(), lcol = new Float32Array(pairs.length * 6), white = new THREE.Color('#ffffff')
    pairs.forEach((pr, k) => pr.forEach((i, e) => (kind[i] === DEF.length ? white : new THREE.Color(DEF[kind[i]][1])).toArray(lcol, k * 6 + e * 3)))
    lgeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pairs.length * 6), 3)); lgeo.setAttribute('color', new THREE.BufferAttribute(lcol, 3))
    const lineMat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending, depthWrite: false })
    const links = new THREE.LineSegments(lgeo, lineMat); links.frustumCulled = false; group.add(links)
    const now = at.map(() => new THREE.Vector3())
    // t: seconds, for the drift and the pulses. p: 0 scattered .. 1 at home in the clusters.
    const set = (t, p = 1) => {
      at.forEach((h, i) => { const w = drift[i], s0 = scat[i]
        now[i].set(lerp(s0.x, h.x + w * Math.sin(t * 0.6 + i), p), lerp(s0.y, h.y + w * Math.cos(t * 0.5 + i * 1.3), p), lerp(s0.z, h.z + w * Math.sin(t * 0.4 + i * 0.7), p)) })
      clouds.forEach(({ cl, ids }) => { ids.forEach((i, k) => cl.geometry.attributes.position.setXYZ(k, now[i].x, now[i].y, now[i].z)); cl.geometry.attributes.position.needsUpdate = true })
      const lp = lgeo.attributes.position; pairs.forEach(([a, b], k) => { lp.setXYZ(k * 2, now[a].x, now[a].y, now[a].z); lp.setXYZ(k * 2 + 1, now[b].x, now[b].y, now[b].z) }); lp.needsUpdate = true
      routes.forEach(([a, b], k) => { const v = new THREE.Vector3().lerpVectors(now[a], now[b], (t * 0.16 + k * 0.37) % 1); pulse.geometry.attributes.position.setXYZ(k, v.x, v.y, v.z) }); pulse.geometry.attributes.position.needsUpdate = true
    }
    // how it is lit: the nodes' strength, the links', and the lens (the plane in focus, how fast it blurs off it)
    const look = ({ alpha = 1, links: la = 0.4, focus = 14, aperture = 0.05 } = {}) => {
      ;[...clouds.map((c) => c.cl), pulse].forEach((cl) => { const u = cl.material.uniforms; u.uAlpha.value = alpha; u.uFocus.value = focus; u.uAperture.value = aperture }); lineMat.opacity = la
    }
    set(0); look()
    return { group, set, look }
  })()

  return { THREE, renderer, scene, cam, composer, bloom, DARK, BLACK, FLOOD, rnd, pointMat, cloud, dust, nodes, home, edgeMat, globe, setNodes, floor, floorMat, clusters }
}
