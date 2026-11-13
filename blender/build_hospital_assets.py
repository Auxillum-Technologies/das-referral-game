"""Build hospital hub world + characters and export GLBs for the Babylon hub.

Run: blender -b -P blender/build_hospital_assets.py
Coordinates are authored in Babylon space (X right, Y up, Z down the corridor)
and mapped to Blender with g(); the glTF exporter + Babylon loader map them back.
"""
import math
import os
import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "client", "public", "game-assets", "3d")
os.makedirs(OUT, exist_ok=True)

CORRIDOR_WIDTH = 20.0
CORRIDOR_LENGTH = 76.0
DOORS = [(-1, 12), (1, 24), (-1, 36), (1, 48), (-1, 60)]


def g(x, y, z):
    """Babylon (x, y, z) -> Blender location."""
    return (-x, -z, y)


def gs(w, h, d):
    """Babylon box size (width x, height y, depth z) -> Blender scale."""
    return (w, d, h)


_mats = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()


def mat(name, hex_color, rough=0.7, metal=0.0, emit=0.0):
    key = (name, hex_color)
    if key in _mats:
        return _mats[key]
    h = hex_color.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*lin, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit > 0:
        bsdf.inputs["Emission Color"].default_value = (*lin, 1)
        bsdf.inputs["Emission Strength"].default_value = emit
    _mats[key] = m
    return m


def finish(obj, name, material, parent=None, bevel=0.0):
    obj.name = name
    obj.data.materials.append(material)
    if bevel > 0:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    if parent:
        obj.parent = parent
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj


def box(name, size, pos, material, bevel=0.0, parent=None, rot_y=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=g(*pos))
    o = bpy.context.active_object
    o.scale = gs(*size)
    o.rotation_euler[2] = -rot_y
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, material, parent, bevel)


def cyl(name, radius, height, pos, material, verts=16, parent=None, axis="y"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=height, location=g(*pos))
    o = bpy.context.active_object
    if axis == "x":
        o.rotation_euler[1] = math.pi / 2
    elif axis == "z":
        o.rotation_euler[0] = math.pi / 2
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return finish(o, name, material, parent)


def sphere(name, radius, pos, material, scale=(1, 1, 1), parent=None, segs=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2, radius=radius, location=g(*pos))
    o = bpy.context.active_object
    o.scale = gs(*scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o = finish(o, name, material, parent)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def export(path, animations=False):
    bpy.ops.object.select_all(action="SELECT")
    kwargs = dict(
        filepath=path,
        export_format="GLB",
        use_selection=False,
        export_apply=True,
        export_yup=True,
        export_animations=animations,
    )
    if animations:
        kwargs["export_animation_mode"] = "ACTIONS"
    bpy.ops.export_scene.gltf(**kwargs)
    print("exported", path, os.path.getsize(path))


def join_and_export(path):
    # One mesh, one primitive per material: keeps Babylon draw calls low.
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in meshes:
        bpy.context.view_layer.objects.active = o
        for mod in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.join()
    bpy.context.active_object.name = os.path.splitext(os.path.basename(path))[0]
    for o in [o for o in bpy.context.scene.objects if o.type == "EMPTY"]:
        bpy.data.objects.remove(o)
    export(path)


# ---------------------------------------------------------------- world

def build_world():
    reset()
    floor_a = mat("floorTileA", "#e3d6bd", 0.55)
    floor_b = mat("floorTileB", "#cdbd9e", 0.55)
    stripe = mat("floorStripe", "#3f7f8c", 0.5)
    blue = mat("wallBlue", "#547f99", 0.8)
    cream = mat("wallCream", "#eee6d3", 0.9)
    mint = mat("wallMint", "#9eb9ad", 0.9)
    rail = mat("handrail", "#c9d3d6", 0.3, 0.6)
    wood = mat("wood", "#a8774c", 0.6)
    steel = mat("steel", "#aeb7bd", 0.35, 0.8)
    dark = mat("darkTrim", "#2d4552", 0.6)
    lamp = mat("ceilingLamp", "#fff4cc", 0.4, emit=3.0)
    leaf = mat("leaf", "#4f8a55", 0.8)
    leaf2 = mat("leafLight", "#79ab5f", 0.8)
    pot = mat("pot", "#c96f4a", 0.7)
    seat = mat("seatTeal", "#2f8f8a", 0.5)
    glass = mat("windowGlass", "#bfe3ef", 0.1, emit=1.2)
    sheet = mat("bedSheet", "#f6f4ee", 0.9)
    blanket = mat("blanket", "#7fb3c8", 0.9)
    screen = mat("monitorScreen", "#3fe0a8", 0.2, emit=2.5)
    counter = mat("counter", "#f1ece0", 0.5)

    # Checkered floor tiles (2x2 units) and a guide stripe down the middle.
    tile = 4.0
    for ix in range(int(CORRIDOR_WIDTH / tile)):
        for iz in range(int(CORRIDOR_LENGTH / tile)):
            m = floor_a if (ix + iz) % 2 == 0 else floor_b
            x = -CORRIDOR_WIDTH / 2 + tile / 2 + ix * tile
            z = tile / 2 + iz * tile
            box(f"floor_{ix}_{iz}", (tile, 0.1, tile), (x, -0.05, z), m)
    box("guideStripe", (0.6, 0.02, CORRIDOR_LENGTH - 4), (0, 0.01, CORRIDOR_LENGTH / 2), stripe)

    # Side walls in three colour bands, with gaps cut around the doors.
    door_half = 2.6
    for side in (-1, 1):
        wall_x = side * 9.75
        cuts = sorted(z for s, z in DOORS if s == side)
        segments, start = [], 0.0
        for z in cuts:
            segments.append((start, z - door_half))
            start = z + door_half
        segments.append((start, CORRIDOR_LENGTH))
        for i, (z0, z1) in enumerate(segments):
            length, mid = z1 - z0, (z0 + z1) / 2
            box(f"wallBlue_{side}_{i}", (0.5, 2.2, length), (wall_x, 1.1, mid), blue)
            box(f"wallCream_{side}_{i}", (0.5, 2.2, length), (wall_x, 3.3, mid), cream)
            box(f"wallMint_{side}_{i}", (0.5, 1.9, length), (wall_x, 5.35, mid), mint)
            box(f"skirting_{side}_{i}", (0.12, 0.25, length), (wall_x - side * 0.3, 0.125, mid), dark)
            # Handrail on brackets.
            box(f"rail_{side}_{i}", (0.12, 0.12, length - 0.6), (wall_x - side * 0.5, 2.4, mid), rail, bevel=0.03)
            n = max(1, int(length // 4))
            for b in range(n + 1):
                bz = z0 + 0.3 + b * (length - 0.6) / n
                box(f"railBracket_{side}_{i}_{b}", (0.4, 0.08, 0.08), (wall_x - side * 0.35, 2.4, bz), steel)
        # Wall above each door opening (the hub draws the door itself).
        for z in cuts:
            box(f"doorHeader_{side}_{z}", (0.5, 1.2, door_half * 2), (wall_x, 6.3 - 0.6, z), mint)
            box(f"doorBack_{side}_{z}", (0.5, 6.3, door_half * 2), (wall_x + side * 0.6, 3.15, z), dark)

    # End wall with a bright window, and a short entrance wall behind the start.
    box("endWallBlue", (CORRIDOR_WIDTH, 2.2, 0.5), (0, 1.1, CORRIDOR_LENGTH), blue)
    box("endWallCream", (CORRIDOR_WIDTH, 4.1, 0.5), (0, 4.25, CORRIDOR_LENGTH), cream)
    box("endWindowFrame", (8.4, 3.0, 0.3), (0, 4.0, CORRIDOR_LENGTH - 0.3), dark, bevel=0.04)
    box("endWindow", (7.8, 2.5, 0.32), (0, 4.0, CORRIDOR_LENGTH - 0.3), glass)
    for wx in (-1.3, 1.3):
        box(f"endWindowMullion{wx}", (0.12, 2.5, 0.34), (wx, 4.0, CORRIDOR_LENGTH - 0.3), dark)

    # Ceiling light fixtures.
    for z in range(7, int(CORRIDOR_LENGTH), 10):
        box(f"lampHousing{z}", (5.8, 0.14, 1.3), (0, 9.2, z), steel)
        box(f"lampPanel{z}", (5.4, 0.06, 1.0), (0, 9.1, z), lamp)

    def bench(name, x, z, facing):
        root = bpy.data.objects.new(name, None)
        bpy.context.collection.objects.link(root)
        box(f"{name}_seat", (1.1, 0.18, 3.6), (x, 0.95, z), seat, bevel=0.05, parent=root)
        box(f"{name}_back", (0.18, 1.0, 3.6), (x + facing * 0.55, 1.5, z), seat, bevel=0.05, parent=root)
        for lz in (-1.5, 1.5):
            box(f"{name}_leg{lz}", (0.9, 0.85, 0.12), (x, 0.43, z + lz), steel, parent=root)
        return root

    def plant(name, x, z):
        cyl(f"{name}_pot", 0.55, 1.0, (x, 0.5, z), pot, verts=12)
        sphere(f"{name}_bush", 0.9, (x, 1.6, z), leaf, scale=(1, 1.2, 1), segs=10)
        sphere(f"{name}_top", 0.55, (x + 0.2, 2.4, z - 0.1), leaf2, segs=10)

    def iv_stand(name, x, z):
        cyl(f"{name}_pole", 0.05, 3.6, (x, 1.8, z), steel, verts=8)
        cyl(f"{name}_base", 0.5, 0.08, (x, 0.05, z), steel, verts=10)
        box(f"{name}_bag", (0.35, 0.55, 0.12), (x, 3.3, z), mat("ivBag", "#dff3f7", 0.2), bevel=0.04)

    def bed(name, x, z, rot):
        root_mats = (steel, sheet, blanket)
        box(f"{name}_frame", (2.0, 0.25, 4.4), (x, 0.9, z), root_mats[0], bevel=0.05)
        box(f"{name}_mattress", (1.9, 0.35, 4.2), (x, 1.2, z), root_mats[1], bevel=0.1)
        box(f"{name}_blanket", (1.95, 0.2, 2.6), (x, 1.42, z + 0.7), root_mats[2], bevel=0.08)
        box(f"{name}_pillow", (1.4, 0.3, 0.8), (x, 1.5, z - 1.6), sheet, bevel=0.12)
        box(f"{name}_headboard", (2.1, 1.4, 0.15), (x, 1.5, z - 2.2), steel, bevel=0.04)
        for lx in (-0.85, 0.85):
            for lz in (-1.9, 1.9):
                cyl(f"{name}_leg{lx}{lz}", 0.07, 0.8, (x + lx, 0.4, z + lz), steel, verts=8)

    def monitor(name, x, z):
        cyl(f"{name}_pole", 0.06, 2.6, (x, 1.3, z), steel, verts=8)
        box(f"{name}_case", (0.9, 0.7, 0.2), (x, 2.8, z), dark, bevel=0.05)
        box(f"{name}_screen", (0.75, 0.55, 0.05), (x, 2.8, z + 0.11), screen)

    # Waiting areas between doors (opposite walls from the doors).
    for side, z in DOORS:
        bench(f"bench_{z}", -side * 8.6, z, -side)
        plant(f"plant_{z}a", -side * 8.6, z - 3.4)
        plant(f"plant_{z}b", -side * 8.6, z + 3.4)
    # Gurneys parked along walls with monitors.
    for i, (side, z) in enumerate([(1, 3.6), (-1, 30), (1, 42), (-1, 54), (1, 66)]):
        bed(f"gurney_{i}", side * 8.3, z, 0)
        monitor(f"monitor_{i}", side * 8.9, z - 2.8)
        iv_stand(f"iv_{i}", side * 7.0, z - 2.4)

    # Nurse station near the far end.
    box("stationDesk", (8.0, 1.6, 1.4), (0, 0.8, 70), counter, bevel=0.06)
    box("stationTop", (8.4, 0.12, 1.8), (0, 1.66, 70), wood, bevel=0.03)
    box("stationKick", (8.0, 0.3, 1.45), (0, 0.15, 70), stripe)
    box("stationSide", (1.4, 1.6, 3.0), (-3.3, 0.8, 71.8), counter, bevel=0.06)
    box("stationSide2", (1.4, 1.6, 3.0), (3.3, 0.8, 71.8), counter, bevel=0.06)
    monitor("stationMonitorA", -1.6, 70.6)
    monitor("stationMonitorB", 1.6, 70.6)
    box("stationSignBar", (6.0, 0.6, 0.15), (0, 5.4, 69.4), stripe, bevel=0.04)

    join_and_export(os.path.join(OUT, "hospital-world.glb"))


# ---------------------------------------------------------------- ward bay (inside each level room)

WARD_BAY_WIDTH = 60.0
WARD_BED_X = [7.4, 18.4, 29.15, 40.05, 51.1]  # keep in sync with LevelBuilder BED_X_IN_TILE
WARD_BED_Z = 9.0


def build_ward():
    """One 60-unit ward bay, floor at y=0, x 0..60, back wall at z=12.5. Tiled by the game."""
    reset()
    floor_a = mat("wardFloorA", "#d9e2e0", 0.5)
    floor_b = mat("wardFloorB", "#c6d3d1", 0.5)
    wall = mat("wardWallTint", "#cfe0e4", 0.9)  # tinted per level in Babylon
    dado = mat("wardDado", "#4f7d95", 0.8)
    trim = mat("wardTrim", "#2d4552", 0.6)
    steel = mat("steel", "#aeb7bd", 0.35, 0.8)
    sheet = mat("bedSheet", "#f6f4ee", 0.9)
    blanket = mat("blanket", "#7fb3c8", 0.9)
    curtain = mat("curtain", "#8cc7b8", 0.95)
    glass = mat("windowGlass", "#bfe3ef", 0.1, emit=1.4)
    screen = mat("monitorScreen", "#3fe0a8", 0.2, emit=2.5)
    lamp = mat("bedLamp", "#fff4cc", 0.4, emit=2.0)
    wood = mat("wood", "#a8774c", 0.6)
    cabinet = mat("cabinet", "#eee6d3", 0.6)
    chair = mat("chairTeal", "#2f8f8a", 0.5)
    gas = mat("gasPanel", "#dfe7ea", 0.4)

    tile = 4.0
    for ix in range(int(WARD_BAY_WIDTH / tile)):
        for iz in range(4):
            m = floor_a if (ix + iz) % 2 == 0 else floor_b
            box(f"wf_{ix}_{iz}", (tile, 0.1, tile), (tile / 2 + ix * tile, -0.05, -2 + tile / 2 + iz * tile), m)

    wz = 12.5
    box("wallBack", (WARD_BAY_WIDTH, 10.0, 0.4), (WARD_BAY_WIDTH / 2, 5.0, wz + 0.2), wall)
    box("wallDado", (WARD_BAY_WIDTH, 2.4, 0.1), (WARD_BAY_WIDTH / 2, 1.2, wz - 0.05), dado)
    box("wallRail", (WARD_BAY_WIDTH, 0.15, 0.2), (WARD_BAY_WIDTH / 2, 2.45, wz - 0.1), trim)
    box("wallSkirting", (WARD_BAY_WIDTH, 0.3, 0.15), (WARD_BAY_WIDTH / 2, 0.15, wz - 0.12), trim)
    box("ceilingTrim", (WARD_BAY_WIDTH, 0.4, 0.3), (WARD_BAY_WIDTH / 2, 9.6, wz - 0.1), trim)

    # Windows between beds.
    for i in range(len(WARD_BED_X) - 1):
        x = (WARD_BED_X[i] + WARD_BED_X[i + 1]) / 2
        box(f"winFrame{i}", (3.6, 3.4, 0.2), (x, 5.6, wz - 0.1), trim, bevel=0.04)
        box(f"winGlass{i}", (3.2, 3.0, 0.22), (x, 5.6, wz - 0.12), glass)
        box(f"winMullion{i}", (0.1, 3.0, 0.24), (x, 5.6, wz - 0.13), trim)
        box(f"winSill{i}", (4.0, 0.15, 0.5), (x, 3.85, wz - 0.3), cabinet)

    for i, x in enumerate(WARD_BED_X):
        z = WARD_BED_Z
        # Bed: head against back wall.
        box(f"bed{i}_frame", (2.4, 0.3, 4.6), (x, 1.0, z), steel, bevel=0.05)
        box(f"bed{i}_mattress", (2.2, 0.4, 4.4), (x, 1.35, z), sheet, bevel=0.12)
        box(f"bed{i}_blanket", (2.3, 0.22, 2.6), (x, 1.6, z - 0.8), blanket, bevel=0.1)
        box(f"bed{i}_pillow", (1.5, 0.35, 0.8), (x, 1.75, z + 1.7), sheet, bevel=0.14)
        box(f"bed{i}_head", (2.5, 2.0, 0.18), (x, 1.9, z + 2.3), steel, bevel=0.05)
        box(f"bed{i}_foot", (2.5, 1.2, 0.18), (x, 1.5, z - 2.3), steel, bevel=0.05)
        for lx in (-1.0, 1.0):
            for lz in (-2.0, 2.0):
                cyl(f"bed{i}_wheel{lx}{lz}", 0.16, 0.12, (x + lx, 0.16, z + lz), trim, verts=10, axis="x")
                cyl(f"bed{i}_leg{lx}{lz}", 0.06, 0.8, (x + lx, 0.6, z + lz), steel, verts=8)
        # Wall services: gas panel, monitor, reading lamp.
        box(f"bed{i}_gas", (3.6, 0.6, 0.15), (x, 3.3, wz - 0.12), gas, bevel=0.03)
        for k, c in enumerate(("#3f8fd0", "#3fbf7a", "#e0c040")):
            cyl(f"bed{i}_outlet{k}", 0.09, 0.1, (x - 0.8 + k * 0.8, 3.3, wz - 0.22), mat(f"outlet{k}", c, 0.4), verts=8, axis="z")
        box(f"bed{i}_monCase", (1.3, 0.95, 0.25), (x + 1.9, 5.0, wz - 0.2), trim, bevel=0.05)
        box(f"bed{i}_monScreen", (1.1, 0.75, 0.05), (x + 1.9, 5.0, wz - 0.34), screen)
        box(f"bed{i}_lamp", (1.6, 0.18, 0.5), (x, 7.4, wz - 0.3), lamp, bevel=0.04)
        # Privacy curtain on a ceiling rail, drawn to the left of the bed.
        box(f"bed{i}_rail", (0.08, 0.08, 6.0), (x - 2.9, 9.0, z - 0.5), steel)
        for f in range(5):
            box(f"bed{i}_curtain{f}", (0.12, 7.6, 0.75), (x - 2.9 + (0.08 if f % 2 else -0.08), 5.0, z + 2.3 - f * 0.7), curtain)
        # Bedside cabinet, IV stand, visitor chair.
        box(f"bed{i}_cab", (1.0, 1.6, 1.0), (x + 1.9, 0.8, z + 1.6), cabinet, bevel=0.06)
        box(f"bed{i}_cabTop", (1.1, 0.08, 1.1), (x + 1.9, 1.64, z + 1.6), wood)
        box(f"bed{i}_cup", (0.2, 0.3, 0.2), (x + 1.8, 1.83, z + 1.4), mat("cup", "#e86f4f", 0.5))
        cyl(f"bed{i}_ivPole", 0.05, 4.0, (x - 1.7, 2.0, z + 1.2), steel, verts=8)
        cyl(f"bed{i}_ivBase", 0.5, 0.08, (x - 1.7, 0.05, z + 1.2), steel, verts=10)
        box(f"bed{i}_ivBag", (0.4, 0.6, 0.14), (x - 1.7, 3.7, z + 1.2), mat("ivBag", "#dff3f7", 0.2), bevel=0.04)
        box(f"bed{i}_chairSeat", (1.0, 0.18, 1.0), (x + 2.4, 1.0, z - 1.4), chair, bevel=0.05)
        box(f"bed{i}_chairBack", (1.0, 1.0, 0.16), (x + 2.4, 1.55, z - 0.95), chair, bevel=0.05)
        for lx in (-0.4, 0.4):
            for lz in (-0.4, 0.4):
                box(f"bed{i}_chairLeg{lx}{lz}", (0.08, 0.92, 0.08), (x + 2.4 + lx, 0.46, z - 1.4 + lz), steel)

    join_and_export(os.path.join(OUT, "ward-bay.glb"))


# ---------------------------------------------------------------- characters

BONES = {
    # name: (head, tail, parent) in Babylon space, character faces +Z.
    "hips": ((0, 1.9, 0), (0, 2.3, 0), None),
    "torso": ((0, 2.3, 0), (0, 3.3, 0), "hips"),
    "head": ((0, 3.3, 0), (0, 4.2, 0), "torso"),
    "arm.L": ((0.62, 3.15, 0), (0.68, 1.95, 0), "torso"),
    "arm.R": ((-0.62, 3.15, 0), (-0.68, 1.95, 0), "torso"),
    "leg.L": ((0.25, 1.95, 0), (0.25, 1.0, 0), "hips"),
    "shin.L": ((0.25, 1.0, 0), (0.25, 0.1, 0), "leg.L"),
    "leg.R": ((-0.25, 1.95, 0), (-0.25, 1.0, 0), "hips"),
    "shin.R": ((-0.25, 1.0, 0), (-0.25, 0.1, 0), "leg.R"),
}


def build_character(name, palette, extras):
    reset()
    skin = mat("skin", palette["skin"], 0.6)
    hair = mat("hair", palette["hair"], 0.7)
    top = mat("top", palette["top"], 0.8)
    pants = mat("pants", palette["pants"], 0.8)
    shoe = mat("shoe", palette["shoe"], 0.5)
    eye = mat("eye", "#1d2630", 0.3)
    coat = mat("coat", palette.get("coat", palette["top"]), 0.85)

    parts = []  # (object, bone)

    def add(obj, bone):
        parts.append((obj, bone))

    # Chibi-ish proportions: big head, compact body.
    add(sphere("head", 0.62, (0, 3.85, 0), skin, segs=20), "head")
    add(sphere("hairCap", 0.66, (0, 4.05, -0.08), hair, scale=(1, 0.8, 1), segs=20), "head")
    for ex in (-0.22, 0.22):
        add(sphere(f"eye{ex}", 0.08, (ex, 3.88, 0.57), eye, segs=8), "head")
    add(sphere("nose", 0.07, (0, 3.75, 0.62), skin, segs=8), "head")
    add(box("neck", (0.3, 0.3, 0.3), (0, 3.25, 0), skin), "torso")
    add(box("torso", (1.05, 1.15, 0.6), (0, 2.75, 0), top, bevel=0.15), "torso")
    add(box("pelvis", (0.95, 0.45, 0.58), (0, 2.05, 0), pants, bevel=0.12), "hips")
    for side, bone in ((1, "L"), (-1, "R")):
        x = side * 0.68
        add(box(f"sleeve{bone}", (0.32, 0.65, 0.34), (x, 2.85, 0), coat, bevel=0.1), f"arm.{bone}")
        add(box(f"forearm{bone}", (0.26, 0.6, 0.28), (x, 2.25, 0), skin if palette.get("short_sleeve") else coat, bevel=0.08), f"arm.{bone}")
        add(sphere(f"hand{bone}", 0.16, (x, 1.88, 0), skin, segs=10), f"arm.{bone}")
        lx = side * 0.25
        add(box(f"thigh{bone}", (0.38, 0.95, 0.42), (lx, 1.45, 0), pants, bevel=0.1), f"leg.{bone}")
        add(box(f"shin{bone}", (0.34, 0.85, 0.38), (lx, 0.55, 0), pants, bevel=0.1), f"shin.{bone}")
        add(box(f"shoe{bone}", (0.4, 0.22, 0.62), (lx, 0.11, 0.1), shoe, bevel=0.08), f"shin.{bone}")
    extras(add, {"skin": skin, "hair": hair, "top": top, "coat": coat, "pants": pants})

    # Armature.
    arm_data = bpy.data.armatures.new(f"{name}Rig")
    rig = bpy.data.objects.new(f"{name}Rig", arm_data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for bname, (h, t, parent) in BONES.items():
        eb = arm_data.edit_bones.new(bname)
        eb.head, eb.tail = g(*h), g(*t)
        if parent:
            eb.parent = arm_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")

    # Join parts into one rigid-skinned mesh.
    for obj, bone in parts:
        vg = obj.vertex_groups.new(name=bone)
        vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
        bpy.context.view_layer.objects.active = obj
        for mod in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.select_all(action="DESELECT")
    for obj, _ in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0][0]
    bpy.ops.object.join()
    body = bpy.context.active_object
    body.name = f"{name}Body"
    body.parent = rig
    mod = body.modifiers.new("rig", "ARMATURE")
    mod.object = rig

    make_actions(rig)
    export(os.path.join(OUT, f"{name}.glb"), animations=True)


def make_actions(rig):
    rig.animation_data_create()
    pb = rig.pose.bones
    for b in pb:
        b.rotation_mode = "XYZ"

    def key(frame, poses):
        for b in pb:
            b.rotation_euler = poses.get(b.name, (0, 0, 0))
            b.location = (0, 0, 0)
        if "_hips_y" in poses:
            pb["hips"].location = (0, poses["_hips_y"], 0)
        for b in pb:
            b.keyframe_insert("rotation_euler", frame=frame)
            b.keyframe_insert("location", frame=frame)

    # Bone-local X rotation swings limbs forward/back.
    def walk_pose(phase, amp):
        s = math.sin(phase)
        knee = lambda v: (max(0.0, v) * amp * 1.3, 0, 0)
        return {
            "leg.L": (s * amp, 0, 0),
            "leg.R": (-s * amp, 0, 0),
            "shin.L": knee(-math.cos(phase)),
            "shin.R": knee(math.cos(phase)),
            "arm.L": (-s * amp * 0.9, 0, 0),
            "arm.R": (s * amp * 0.9, 0, 0),
            "torso": (0, s * 0.08, 0),
            "_hips_y": abs(math.cos(phase)) * 0.08,
        }

    clips = {
        "walk": (24, lambda t: walk_pose(t * 2 * math.pi, 0.55)),
        "idle": (48, lambda t: {
            "torso": (math.sin(t * 2 * math.pi) * 0.03, 0, 0),
            "head": (0, math.sin(t * 2 * math.pi) * 0.12, 0),
            "arm.L": (0, 0, math.sin(t * 2 * math.pi) * 0.04),
            "arm.R": (0, 0, -math.sin(t * 2 * math.pi) * 0.04),
        }),
    }
    for clip, (length, fn) in clips.items():
        action = bpy.data.actions.new(clip)
        action.use_fake_user = True
        rig.animation_data.action = action
        steps = 8
        for i in range(steps + 1):
            key(1 + i * length / steps, fn(i / steps))
        track = rig.animation_data.nla_tracks.new()
        track.name = clip
        track.strips.new(clip, 1, action)
        rig.animation_data.action = None


def doctor_extras(add, m):
    white = mat("labCoat", "#f7f7f2", 0.85)
    steel = mat("stethoscope", "#2b3a44", 0.3, 0.5)
    add(box("coatBody", (1.12, 1.55, 0.66), (0, 2.6, -0.01), white, bevel=0.15), "torso")
    add(box("coatLapelGap", (0.32, 1.0, 0.02), (0, 2.85, 0.33), m["top"]), "torso")
    add(box("badge", (0.22, 0.28, 0.02), (0.32, 2.95, 0.34), mat("badge", "#2f8f8a", 0.4)), "torso")
    bpy.ops.mesh.primitive_torus_add(major_radius=0.32, minor_radius=0.035, location=g(0, 3.1, 0.12))
    torus = bpy.context.active_object
    torus.rotation_euler[0] = 1.2
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    add(finish(torus, "stethoscope", steel), "torso")
    add(sphere("stethBell", 0.09, (0.1, 2.55, 0.36), steel, segs=10), "torso")


def nurse_extras(add, m):
    cap = mat("nurseCap", "#ffffff", 0.8)
    add(box("cap", (0.7, 0.2, 0.5), (0, 4.45, 0.05), cap, bevel=0.06), "head")
    add(sphere("bun", 0.25, (0, 3.95, -0.6), m["hair"], segs=12), "head")
    add(box("clipboard", (0.45, 0.6, 0.05), (0.62, 2.1, 0.25), mat("clipboard", "#b8875a", 0.6)), "arm.L")


def patient_extras(add, m):
    gown_dots = mat("gownDots", "#4f7fa0", 0.8)
    for i, (x, y) in enumerate([(-0.3, 3.0), (0.25, 2.7), (-0.1, 2.4), (0.35, 3.05)]):
        add(sphere(f"dot{i}", 0.06, (x, y, 0.31), gown_dots, segs=6), "torso")
    add(box("wristband", (0.3, 0.08, 0.3), (-0.68, 2.0, 0), mat("wristband", "#ffd166", 0.5)), "arm.R")


if __name__ == "__main__":
    build_world()
    build_ward()
    build_character("doctor", {
        "skin": "#e9b98f", "hair": "#3a2a22", "top": "#2f8f8a", "coat": "#f7f7f2",
        "pants": "#2f8f8a", "shoe": "#2b3a44",
    }, doctor_extras)
    build_character("nurse", {
        "skin": "#a8714a", "hair": "#1f1612", "top": "#7fb3c8", "pants": "#5d8fa8",
        "shoe": "#f2f2f2", "short_sleeve": True,
    }, nurse_extras)
    build_character("patient", {
        "skin": "#d9a27a", "hair": "#8a8a8a", "top": "#c9dfe8", "pants": "#c9dfe8",
        "shoe": "#6b5a4a", "short_sleeve": True,
    }, patient_extras)
