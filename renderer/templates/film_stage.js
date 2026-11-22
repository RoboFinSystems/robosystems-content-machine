/*
 * The film stage: what every page built on the brand film's form shares, so the look lives in
 * one place. A page (ad.html, research_film.html, the next lane's) imports this, takes the
 * stage, and keeps only its own scenes.
 *
 *   import { stage, fonts, seg, eo, eio, lerp, show, $ } from './film_stage.js'
 *   const S = stage({ W, H, canvas: $('gl') })     // once
 *   ... in seek(t): set S.scene.background, what is visible, the camera; then S.composer.render()
 *
 * The stage holds the renderer with its bloom, the lens (points that blur off the focal plane),
 * the dust, the graph (150 facts, scattered or at home on a sphere), the floor grid, and the
 * three backgrounds: DARK (the stage), BLACK (under a Blender plate, which is screened over it)
 * and FLOOD (the blue to indigo field, held for a film's turn). Colours are tokens/film.css
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

  return { THREE, renderer, scene, cam, composer, bloom, DARK, BLACK, FLOOD, rnd, pointMat, cloud, dust, nodes, home, edgeMat, globe, setNodes, floor, floorMat }
}
