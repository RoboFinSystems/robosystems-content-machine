"""
The hero shot of the RoboSystems ad, built in Blender from nothing: scattered facts fly
home onto a sphere, link into a graph around a polished core, and the graph turns over a
reflective floor.

  Blender -b -P graph_hero.py -- <out_dir> [--stills 1,90,180] [--engine eevee|cycles]
                                 [--frames 180] [--samples 64]

Everything is a function of the frame number, so the same call renders the same picture.
Type is not set here: the HTML renderer lays it over the plate (see the ad's assembly).

With --push F the shot is the filing ident, shared by every film that opens on a filing
(just film-ident): a denser sphere (--facts N points), and from frame F the graph stops
turning and the camera leaves the whole of it for one fact on its near face.
"""

import math
import random
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
OUT = argv[0] if argv else "//renders/"


def opt(k, d):
  return argv[argv.index(k) + 1] if k in argv else d


STILLS = [int(x) for x in opt("--stills", "").split(",") if x]
ENGINE = opt("--engine", "eevee")
FRAMES = int(opt("--frames", "180"))
SAMPLES = int(opt("--samples", "64"))
FILM = opt(
  "--film", ""
)  # a film folder: the shot takes its length and frame shape from its timeline
TALL = "--tall" in argv
FACTS, PUSH = int(opt("--facts", "0")), int(opt("--push", "0"))  # the filing ident
if FILM:
  import json
  from pathlib import Path

  _tl = json.loads((Path(FILM) / "timeline.json").read_text())
  FRAMES = next(s["frames"] for s in _tl["scenes"] if s["name"] == "reveal")
  TALL = _tl["format"] == "tall"

random.seed(11)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = 30
scene.render.resolution_x, scene.render.resolution_y = (
  (1080, 1920) if TALL else (1920, 1080)
)
scene.render.resolution_percentage = 100


def hexc(h, a=1.0):
  """sRGB hex to the linear RGBA Blender shades in."""

  def lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

  h = h.lstrip("#")
  return tuple(lin(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4)) + (a,)


def emission(name, color, strength):
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  nt = m.node_tree
  nt.nodes.clear()
  e = nt.nodes.new("ShaderNodeEmission")
  e.inputs["Color"].default_value = hexc(color)
  e.inputs["Strength"].default_value = strength
  o = nt.nodes.new("ShaderNodeOutputMaterial")
  nt.links.new(e.outputs[0], o.inputs["Surface"])
  return m


def principled(name, color, metallic, roughness):
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  b = m.node_tree.nodes["Principled BSDF"]
  b.inputs["Base Color"].default_value = hexc(color)
  b.inputs["Metallic"].default_value = metallic
  b.inputs["Roughness"].default_value = roughness
  return m


def add(obj):
  scene.collection.objects.link(obj)
  return obj


def sphere_mesh(name, radius, subdiv):
  bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=radius)
  o = bpy.context.active_object
  me = o.data
  me.name = name
  for p in me.polygons:
    p.use_smooth = True
  bpy.data.objects.remove(o)
  return me


# ── world: near black, the stage colour of the site ─────────────────────────────
world = bpy.data.worlds.new("world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = hexc("#04070c")
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
scene.world = world

# ── the globe: everything that turns together ───────────────────────────────────
globe = add(bpy.data.objects.new("globe", None))
R = 3.4
N = FACTS or 150
K = max(0.42, (150 / N) ** 0.5)  # more points, each smaller, so the sphere stays a surface

core_me = sphere_mesh("core", 2.75, 5)
core = add(bpy.data.objects.new("core", core_me))
core.data.materials.append(principled("core", "#0a1830", 1.0, 0.16))
core.parent = globe
core.scale = (0.001, 0.001, 0.001)
core.keyframe_insert("scale", frame=30)
core.scale = (1, 1, 1)
core.keyframe_insert("scale", frame=84)

node_me = sphere_mesh("node", 0.075 * K, 2)
hub_me = sphere_mesh("hub", 0.13 * K, 3)
node_mat = emission("node", "#dff9ff", 5)
hub_mat = emission("hub", "#67E8F9", 9)
node_me.materials.append(node_mat)
hub_me.materials.append(hub_mat)

home, objs = [], []
for i in range(N):
  z = 1 - (i / (N - 1)) * 2
  r = math.sqrt(max(0.0, 1 - z * z))
  a = i * 2.39996
  h = Vector((math.cos(a) * r * R, math.sin(a) * r * R, z * R))
  home.append(h)
  hub = random.random() > 0.82
  o = add(bpy.data.objects.new(f"n{i}", hub_me if hub else node_me))
  o.parent = globe
  # scattered through the depth of the stage, some of it behind the camera's focus
  o.location = (random.uniform(-22, 22), random.uniform(-8, 30), random.uniform(-9, 11))
  start = 1 + int(random.random() * 22)
  o.keyframe_insert("location", frame=start)
  o.location = h
  o.keyframe_insert("location", frame=start + 62)
  objs.append(o)

# ── the links: each fact to its three nearest, drawn after the facts land ───────
pairs = set()
for i, h in enumerate(home):
  # points sit along a spiral, so a point's neighbours are near it in the list too
  near = sorted(
    range(max(0, i - 400), min(N, i + 400)) if N > 800 else range(N),
    key=lambda j: (h - home[j]).length_squared,
  )[1:4]
  for j in near:
    pairs.add((min(i, j), max(i, j)))
cu = bpy.data.curves.new("links", "CURVE")
cu.dimensions = "3D"
cu.bevel_depth = 0.011 * K
cu.bevel_resolution = 2
cu.bevel_factor_mapping_end = "SPLINE"
for i, j in sorted(pairs):
  s = cu.splines.new("POLY")
  s.points.add(1)
  s.points[0].co = (*home[i], 1)
  s.points[1].co = (*home[j], 1)
cu.materials.append(emission("link", "#67E8F9", 1.8))
links = add(bpy.data.objects.new("links", cu))
links.parent = globe
cu.bevel_factor_end = 0.0
cu.keyframe_insert("bevel_factor_end", frame=80)
cu.bevel_factor_end = 1.0
cu.keyframe_insert("bevel_factor_end", frame=128)
links.hide_render = True
links.keyframe_insert("hide_render", frame=79)
links.hide_render = False
links.keyframe_insert("hide_render", frame=80)

globe.rotation_euler = (math.radians(14), math.radians(-8), 0)
globe.keyframe_insert("rotation_euler", frame=1)
TURN = (math.radians(14), math.radians(-8), math.radians(70 if not PUSH else 46))
globe.rotation_euler = TURN
globe.keyframe_insert("rotation_euler", frame=PUSH or FRAMES)  # an opener holds still to be read

# ── dust: small lights through the depth, for the lens to throw out of focus ────
dust_me = sphere_mesh("dust", 0.03, 1)
dust_me.materials.append(emission("dust", "#22D3EE", 5))
for i in range(420):
  d = add(bpy.data.objects.new(f"d{i}", dust_me))
  d.location = (
    random.uniform(-26, 26),
    random.uniform(-10, 40),
    random.uniform(-3.6, 13),
  )
  s = random.uniform(0.6, 2.2)
  d.scale = (s, s, s)

# ── the floor: dark and polished, so the graph has something to stand over ──────
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -4.4))
floor = bpy.context.active_object
floor.data.materials.append(principled("floor", "#05080f", 0.85, 0.3))
floor.hide_render = (
  True  # its only visible effect was a stray reflection of the rim light
)


# ── light: the brand's cyan from the left, its indigo behind and to the right ───
def area(name, color, power, loc, size):
  lamp = bpy.data.lights.new(name, "AREA")
  lamp.color = hexc(color)[:3]
  lamp.energy = power
  lamp.shape = "DISK"
  lamp.size = size
  o = add(bpy.data.objects.new(name, lamp))
  o.location = loc
  c = o.constraints.new("TRACK_TO")
  c.target = globe
  c.track_axis, c.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
  return o


area("key", "#22D3EE", 5200, (-10, -8, 8), 8)
area("rim", "#6366F1", 7000, (11, 9, 5), 9)
area("fill", "#2563EB", 1600, (6, -15, 8), 12).data.specular_factor = 0.0

# ── camera: a slow dolly in, focused on the near face of the graph ──────────────
target = add(bpy.data.objects.new("target", None))
target.location = (0, 0, -3.1) if TALL else (-4.7, 0, -0.5)
cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 46
cam_data.dof.use_dof = True
cam_data.dof.focus_object = globe
cam_data.dof.aperture_fstop = 1.1
cam = add(bpy.data.objects.new("cam", cam_data))
c = cam.constraints.new("TRACK_TO")
c.target = target
c.track_axis, c.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
cam.location = (-1.6, -27.0, 2.2) if TALL else (-9.0, -25.5, 2.6)
cam.keyframe_insert("location", frame=1)
cam.location = (1.1, -22.0, 0.4) if TALL else (-3.2, -21.0, 0.6)
cam.keyframe_insert("location", frame=PUSH or FRAMES)
scene.camera = cam

# ── the opener's push: from the whole filing to the one fact the film is about ───
if PUSH:
  from mathutils import Euler

  rot = Euler(TURN, "XYZ").to_matrix()
  eye = Vector(cam.location)
  # the fact that faces the camera once the graph has stopped turning
  fi = max(range(N), key=lambda j: (rot @ home[j]).normalized().dot(eye.normalized()))
  fact = rot @ home[fi]
  one = objs[fi]
  one.data = sphere_mesh("fact", 0.13 * K, 3)
  one.data.materials.append(emission("fact", "#ffffff", 14))
  one.scale = (1, 1, 1)
  one.keyframe_insert("scale", frame=PUSH)
  one.scale = (2.6, 2.6, 2.6)
  one.keyframe_insert("scale", frame=FRAMES)
  target.keyframe_insert("location", frame=PUSH)
  target.location = fact
  target.keyframe_insert("location", frame=PUSH + round((FRAMES - PUSH) * 0.55))
  focus = add(bpy.data.objects.new("focus", None))
  focus.keyframe_insert("location", frame=PUSH)
  focus.location = fact
  focus.keyframe_insert("location", frame=PUSH + round((FRAMES - PUSH) * 0.55))
  cam_data.dof.focus_object = focus
  cam.location = fact + (eye - fact).normalized() * 2.4
  cam.keyframe_insert("location", frame=FRAMES)

# ── render settings ─────────────────────────────────────────────────────────────
if ENGINE == "cycles":
  scene.render.engine = "CYCLES"
  scene.cycles.samples = SAMPLES
  scene.cycles.use_denoising = True
  try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
      d.use = True
    scene.cycles.device = "GPU"
  except Exception as e:  # falls back to the CPU
    print("cycles gpu unavailable:", e)
else:
  ids = [
    e.identifier
    for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
  ]
  scene.render.engine = (
    "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in ids else "BLENDER_EEVEE"
  )
  ee = scene.eevee
  for k, v in (
    ("taa_render_samples", SAMPLES),
    ("use_raytracing", True),
    ("use_gtao", True),
  ):
    if hasattr(ee, k):
      setattr(ee, k, v)
scene.view_settings.view_transform = "AgX"
try:
  scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
  pass
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False


# ── bloom in the compositor: the lights bleed the way a lens would ──────────────
def bloom():
  tree = bpy.data.node_groups.new("ad_comp", "CompositorNodeTree")
  if hasattr(scene, "compositing_node_group"):
    scene.compositing_node_group = tree
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    out = tree.nodes.new("NodeGroupOutput")
  else:
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("CompositorNodeComposite")
  rl = tree.nodes.new("CompositorNodeRLayers")
  gl = tree.nodes.new("CompositorNodeGlare")
  for k, v in (
    ("Type", "Bloom"),
    ("Threshold", 1.6),
    ("Strength", 0.22),
    ("Size", 0.45),
    ("Saturation", 1.0),
  ):
    if k in gl.inputs:
      try:
        gl.inputs[k].default_value = v
      except Exception as e:
        print("glare input", k, e)
  if hasattr(gl, "glare_type"):
    gl.glare_type = "BLOOM"
  tree.links.new(rl.outputs["Image"], gl.inputs["Image"])
  tree.links.new(gl.outputs["Image"], out.inputs[0])


try:
  bloom()
except Exception as e:
  print("bloom skipped:", e)

if STILLS:
  for f in STILLS:
    scene.frame_set(f)
    scene.render.filepath = f"{OUT}/still-{f:04d}.png"
    bpy.ops.render.render(write_still=True)
else:
  scene.render.filepath = f"{OUT}/frame-"
  bpy.ops.render.render(animation=True)
