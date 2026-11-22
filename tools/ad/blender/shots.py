"""
The trace and sharing shots of the RoboSystems ad, built in Blender from nothing and timed
from the film's own timeline (films/<name>/timeline.json), so every build lands on the word that
names it.

  Blender -b -P shots.py -- <out_dir> --shot trace|share --film <film_dir> [--stills 1,90] [--samples 32]

Writes frames to <out_dir>/frame-NNNN.png and <out_dir>/anchors.json: the screen position,
per frame, of each point the HTML layer hangs a label on. Type is never set here.

trace   Revenue for the year opens into its four accounts, and each account into one point
        per posted entry (the real counts from the demo company's compiled report).
share   A published report leaves the company's graph, crosses, and takes its place among
        the companies in the investor's graph.
"""

import json
import math
import random
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
OUT = argv[0]


def opt(k, d):
  return argv[argv.index(k) + 1] if k in argv else d


SHOT = opt("--shot", "trace")
STILLS = [int(x) for x in opt("--stills", "").split(",") if x]
SAMPLES = int(opt("--samples", "32"))
FPS = 30

FILM = Path(
  opt(
    "--film",
    str(
      Path(__file__).resolve().parents[3]
      / "showcase"
      / "robosystems_ad"
      / "films"
      / "main"
    ),
  )
)
TL = json.loads((FILM / "timeline.json").read_text())
C, A = TL["cues"], TL["acts"]
_sc = next(s for s in TL["scenes"] if s["name"] == SHOT)
WINDOW = (_sc["start"], _sc["end"])
S0, FRAMES = _sc["frame"], _sc["frames"]


def fr(t):
  return (t * FPS - S0) + 1  # film seconds -> this shot's frame number


random.seed(23)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = FPS
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080


def hexc(h, a=1.0):
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
  m["strength"] = e.inputs["Strength"].path_from_id("default_value")
  return m


def glow(mat, keys):
  """Keyframe an emission material's strength: [(film seconds, strength), ...]."""
  s = mat.node_tree.nodes["Emission"].inputs["Strength"]
  for t, v in keys:
    s.default_value = v
    s.keyframe_insert("default_value", frame=fr(t))


def principled(name, color, metallic, roughness):
  m = bpy.data.materials.new(name)
  m.use_nodes = True
  b = m.node_tree.nodes["Principled BSDF"]
  b.inputs["Base Color"].default_value = hexc(color)
  b.inputs["Metallic"].default_value = metallic
  b.inputs["Roughness"].default_value = roughness
  return m


def add(obj, parent=None):
  scene.collection.objects.link(obj)
  if parent:
    obj.parent = parent
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


def empty(name, loc=(0, 0, 0), parent=None):
  o = add(bpy.data.objects.new(name, None), parent)
  o.location = loc
  return o


def key(obj, prop, value, t):
  setattr(obj, prop, value)
  obj.keyframe_insert(prop, frame=fr(t))


def links(name, segments, mat, depth, parent=None, bulge=0.0):
  """One curve object; each segment is a gentle arc, so a bevel factor draws them all together."""
  cu = bpy.data.curves.new(name, "CURVE")
  cu.dimensions = "3D"
  cu.bevel_depth = depth
  cu.bevel_resolution = 2
  cu.bevel_factor_mapping_end = "SPLINE"
  n = 14
  for a, b in segments:
    a, b = Vector(a), Vector(b)
    mid = (a + b) / 2 + Vector((0, 0, bulge * (b - a).length))
    s = cu.splines.new("POLY")
    s.points.add(n - 1)
    for i in range(n):
      p = i / (n - 1)
      s.points[i].co = (*((1 - p) ** 2 * a + 2 * (1 - p) * p * mid + p**2 * b), 1)
  cu.materials.append(mat)
  return add(bpy.data.objects.new(name, cu), parent), cu


def draw(cu, t0, t1):
  cu.bevel_factor_end = 0.0
  cu.keyframe_insert("bevel_factor_end", frame=fr(t0))
  cu.bevel_factor_end = 1.0
  cu.keyframe_insert("bevel_factor_end", frame=fr(t1))


def fib(n, r):
  out = []
  for i in range(n):
    z = 1 - (i / (n - 1)) * 2
    q = math.sqrt(max(0.0, 1 - z * z))
    a = i * 2.39996
    out.append(Vector((math.cos(a) * q * r, math.sin(a) * q * r, z * r)))
  return out


CORE = None


def globe(
  name, loc, r, n, node_mat, link_mat, node_me, parent=None, core=0.8, link_depth=0.011
):
  """A graph on a sphere around a polished core: the film's recurring object."""
  g = empty(name, loc, parent)
  pts = fib(n, r)
  if core:
    c = add(
      bpy.data.objects.new(name + "_core", sphere_mesh(name + "_core", r * core, 4)), g
    )
    c.data.materials.append(CORE)
  for i, p in enumerate(pts):
    o = add(bpy.data.objects.new(f"{name}_n{i}", node_me), g)
    o.location = p
  pairs = set()
  for i, p in enumerate(pts):
    for j in sorted(range(n), key=lambda j: (p - pts[j]).length)[1:4]:
      pairs.add((min(i, j), max(i, j)))
  _, cu = links(
    name + "_links",
    [(pts[i], pts[j]) for i, j in sorted(pairs)],
    link_mat,
    link_depth,
    g,
  )
  cu.materials.clear()
  cu.materials.append(link_mat)
  return g


# ── stage ───────────────────────────────────────────────────────────────────────
world = bpy.data.worlds.new("world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = hexc("#04070c")
scene.world = world
CORE = principled("core", "#0a1830", 1.0, 0.16)

dust_me = sphere_mesh("dust", 0.03, 1)
dust_me.materials.append(emission("dust", "#22D3EE", 5))
for i in range(460):
  d = add(bpy.data.objects.new(f"d{i}", dust_me))
  d.location = (
    random.uniform(-28, 28),
    random.uniform(-9, 46),
    random.uniform(-13, 13),
  )
  s = random.uniform(0.6, 2.2)
  d.scale = (s, s, s)

origin = empty("origin")


def area(name, color, power, loc, size, spec=1.0):
  lamp = bpy.data.lights.new(name, "AREA")
  lamp.color = hexc(color)[:3]
  lamp.energy = power
  lamp.shape = "DISK"
  lamp.size = size
  lamp.specular_factor = spec
  o = add(bpy.data.objects.new(name, lamp))
  o.location = loc
  c = o.constraints.new("TRACK_TO")
  c.target = origin
  c.track_axis, c.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"


area("key", "#22D3EE", 5200, (-10, -8, 8), 8)
area("rim", "#6366F1", 7000, (11, 9, 5), 9)
area("fill", "#2563EB", 1600, (6, -15, 8), 12, spec=0.0)

target = empty("target")
cam_data = bpy.data.cameras.new("cam")
cam_data.sensor_fit = "VERTICAL"
cam_data.sensor_height = 24
cam_data.lens = 12 / math.tan(
  math.radians(19)
)  # the 38 degree lens the rest of the film uses
cam_data.dof.use_dof = True
cam = add(bpy.data.objects.new("cam", cam_data))
ct = cam.constraints.new("TRACK_TO")
ct.target = target
ct.track_axis, ct.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
scene.camera = cam
T0, T1 = WINDOW
ANCHORS = {}  # name -> object, or a fixed point

if SHOT == "trace":
  # Driftline Coffee Roasters (a demo company), year ended 2026-09-30, from its compiled
  # report's lineage: revenue 1,173,239.88 = four accounts; the leaf counts are the posted
  # entries behind each.
  GROUPS = [36, 43, 12, 32]
  root_p = Vector((-1.9, 0, 0.375))
  root = add(bpy.data.objects.new("root", sphere_mesh("root", 0.34, 4)))
  root.location = root_p
  root.data.materials.append(emission("root", "#67E8F9", 9))
  halo = add(bpy.data.objects.new("halo", sphere_mesh("halo", 0.62, 4)))
  halo.location = root_p
  halo.data.materials.append(CORE)
  halo.scale = (
    1,
    0.12,
    1,
  )  # a polished disc behind the figure's node, catching the lights
  leaf_me = sphere_mesh("leaf", 0.055, 2)
  grp_me = sphere_mesh("grp", 0.17, 3)
  grp_me.materials.append(emission("grp", "#dff9ff", 8))
  e0 = C["every"]
  gpos = []
  for g, n in enumerate(GROUPS):
    gp = Vector((2.3, 1.2, 3.0 - g * 1.75))
    gpos.append(gp)
    o = add(bpy.data.objects.new(f"g{g}", grp_me))
    o.location = gp
    key(o, "scale", (0.001,) * 3, e0 + 0.45 + g * 0.1)
    key(o, "scale", (1, 1, 1), e0 + 0.95 + g * 0.1)
    ANCHORS[f"g{g}"] = gp
    lm = emission(f"leaf{g}", "#67E8F9", 0.25)
    me = leaf_me.copy()
    me.materials.append(lm)
    t_leaf = e0 + 1.0 + g * 0.22
    glow(lm, [(t_leaf, 0.25), (t_leaf + 0.9, 7)])
    segs = []
    for k in range(n):
      lp = Vector(
        (
          5.0 + random.random() * 8.5,
          2.5 + random.random() * 19,
          gp.z - 0.08 - random.random() * 1.05,
        )
      )  # below its node: the space above is the label's
      add(bpy.data.objects.new(f"l{g}_{k}", me)).location = lp
      segs.append((gp, lp))
    _, cu = links(
      f"fan{g}", segs, emission(f"fan{g}", "#22D3EE", 2.2), 0.007, bulge=0.04
    )
    draw(cu, t_leaf, t_leaf + 1.0)
  _, cu = links(
    "stem", [(root_p, gp) for gp in gpos], emission("stem", "#67E8F9", 4), 0.014
  )
  draw(cu, e0 + 0.15, e0 + 0.85)
  ANCHORS["root"] = root_p
  target.location = (1.0, 3.0, -0.3)
  key(cam, "location", (-2.6, -19.0, 0.3), T0)
  key(cam, "location", (0.9, -14.6, 0.9), T1)
  cam_data.dof.focus_object = root
  cam_data.dof.aperture_fstop = 1.6

if SHOT == "share":
  node_me = sphere_mesh("node", 0.075, 2)
  node_me.materials.append(emission("node", "#dff9ff", 5))
  link_mat = emission("link", "#67E8F9", 1.8)
  CO, INV = Vector((-5.6, 0, 0)), Vector((5.1, 0, 0))
  co = globe("co", CO, 3.4, 150, None, link_mat, node_me)
  co.scale = (0.62,) * 3
  key(co, "rotation_euler", (math.radians(14), math.radians(-8), 0), T0)
  key(co, "rotation_euler", (math.radians(14), math.radians(-8), math.radians(60)), T1)

  small_me = sphere_mesh("small", 0.05, 2)
  small_me.materials.append(emission("small", "#dff9ff", 5))
  hub = globe("hub", INV, 0.95, 44, None, link_mat, small_me, link_depth=0.007)
  key(hub, "rotation_euler", (0.2, 0, 0), T0)
  key(hub, "rotation_euler", (0.2, 0, math.radians(-50)), T1)

  slots = []
  for i in range(5):
    a = math.pi * (0.5 + (i - 2) * 0.36) + math.pi / 2
    k = 1.05 if i == 2 else 1.0
    slots.append(
      Vector(
        (
          INV.x + math.cos(a) * 3.1 * k,
          0 if i == 2 else 1.5 - (i % 2) * 2.2,
          math.sin(a) * 3.1,
        )
      )
    )
  other_me = sphere_mesh("other", 0.045, 2)
  other_mat = emission("other", "#67E8F9", 0.9)
  other_me.materials.append(other_mat)
  other_link = emission("other_link", "#22D3EE", 0.5)
  glow(other_mat, [(C["hold"] - 0.25, 0.9), (C["hold"] + 0.6, 6)])
  glow(other_link, [(C["hold"] - 0.25, 0.5), (C["hold"] + 0.6, 1.8)])
  for i in (0, 1, 3, 4):
    g = globe(
      f"pc{i}", slots[i], 0.62, 26, None, other_link, other_me, link_depth=0.006
    )
    key(g, "rotation_euler", (0, 0, i), T0)
    key(g, "rotation_euler", (0, 0, i + 0.9), T1)
  landed = globe(
    "landed", slots[2], 0.62, 26, None, link_mat, small_me, link_depth=0.006
  )
  key(landed, "scale", (0.001,) * 3, C["lands"] + 0.2)
  key(landed, "scale", (1, 1, 1), C["lands"] + 0.75)

  _, cu = links("ours", [(slots[2], INV)], emission("ours", "#67E8F9", 4), 0.016)
  draw(cu, C["lands"] + 0.3, C["lands"] + 0.9)
  _, cu = links(
    "theirs",
    [(slots[i], INV) for i in (0, 1, 3, 4)],
    emission("theirs", "#22D3EE", 3),
    0.012,
  )
  draw(cu, C["hold"] - 0.1, C["hold"] + 0.8)

  # the report: a page of statements, an object in its own right
  rep = empty("report")
  bpy.ops.mesh.primitive_cube_add(size=1)
  page = bpy.context.active_object
  page.scale = (1.0, 0.035, 1.36)
  page.parent = rep
  rep_size = 1.7
  page.data.materials.append(principled("page", "#0d2038", 0.55, 0.22))
  bv = page.modifiers.new("bevel", "BEVEL")
  bv.width, bv.segments = 0.02, 3
  bar = emission("bar", "#f3f6fb", 5)
  head = emission("head", "#22D3EE", 7)
  for r, w in enumerate([0.46, 0.74, 0.62, 0.74, 0.5, 0.74]):
    bpy.ops.mesh.primitive_cube_add(size=1)
    b = bpy.context.active_object
    b.scale = (w, 0.012, 0.055 if r else 0.09)
    b.location = (-0.37 + w / 2, -0.03, 0.5 - r * 0.2)
    b.parent = rep
    b.data.materials.append(bar if r else head)
  p0 = CO + Vector((3.5, -1.2, 0.2))
  born, go0, go1 = C["publish"] + 0.1, C["shareit"] + 0.25, C["lands"] + 0.35
  rep.location = p0
  key(rep, "scale", (0.001,) * 3, born)
  key(rep, "scale", (rep_size,) * 3, born + 0.8)
  key(rep, "rotation_euler", (0, 0, math.radians(-28)), born)
  key(rep, "rotation_euler", (0, 0, math.radians(-12)), go0)
  key(rep, "location", p0, go0)
  key(rep, "location", (-0.2, -2.6, 2.9), (go0 + go1) / 2)
  key(rep, "rotation_euler", (math.radians(8), 0, math.radians(14)), (go0 + go1) / 2)
  key(rep, "scale", (rep_size,) * 3, (go0 + go1) / 2)
  key(rep, "location", slots[2], go1)
  key(rep, "rotation_euler", (0, 0, math.radians(30)), go1)
  key(rep, "scale", (0.34,) * 3, go1)
  key(rep, "scale", (0.001,) * 3, go1 + 0.3)

  ANCHORS.update(
    {
      "company": CO + Vector((0, 0, -2.75)),
      "investor": INV + Vector((0, 0, 4.6)),
      "report": rep,
    }
  )
  target.location = (0, 0, 0.35)
  key(cam, "location", (-0.8, -17.5, 0.4), T0)
  key(cam, "location", (0.8, -15.6, 0.4), T1)
  cam_data.dof.focus_object = origin
  cam_data.dof.aperture_fstop = 2.0

# ── render settings ─────────────────────────────────────────────────────────────
ids = [
  e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
]
scene.render.engine = (
  "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in ids else "BLENDER_EEVEE"
)
for k, v in (
  ("taa_render_samples", SAMPLES),
  ("use_raytracing", True),
  ("use_gtao", True),
):
  if hasattr(scene.eevee, k):
    setattr(scene.eevee, k, v)
scene.view_settings.view_transform = "AgX"
try:
  scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
  pass
scene.render.image_settings.file_format = "PNG"

try:
  tree = bpy.data.node_groups.new("ad_comp", "CompositorNodeTree")
  scene.compositing_node_group = tree
  tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
  out = tree.nodes.new("NodeGroupOutput")
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
      gl.inputs[k].default_value = v
  tree.links.new(rl.outputs["Image"], gl.inputs["Image"])
  tree.links.new(gl.outputs["Image"], out.inputs[0])
except Exception as e:
  print("bloom skipped:", e)

# ── anchors: where each label hangs, frame by frame ─────────────────────────────
Path(OUT).mkdir(parents=True, exist_ok=True)
anchors = {k: [] for k in ANCHORS}
for f in range(1, FRAMES + 1):
  scene.frame_set(f)
  bpy.context.view_layer.update()
  for k, v in ANCHORS.items():
    co = v.matrix_world.translation if hasattr(v, "matrix_world") else v
    p = world_to_camera_view(scene, cam, co)
    anchors[k].append([round(p.x * 1920, 1), round((1 - p.y) * 1080, 1)])
(Path(OUT) / "anchors.json").write_text(
  json.dumps({"start": S0, "frames": FRAMES, "anchors": anchors})
)
print(f"{SHOT}: frames {FRAMES} from film frame {S0}")

if STILLS:
  for f in STILLS:
    scene.frame_set(f)
    scene.render.filepath = f"{OUT}/still-{f:04d}.png"
    bpy.ops.render.render(write_still=True)
else:
  scene.render.filepath = f"{OUT}/frame-"
  bpy.ops.render.render(animation=True)
