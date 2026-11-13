"""Build the EMR-DAS chibi doctor main character from blender/references/chibi-doctor-character-sheet.png.

Run: blender -b -P blender/build_main_character.py
Exports client/public/game-assets/3d/doctor.glb (same bone names + walk/idle clips as before).
Coordinates are Babylon space (X right, Y up, character faces +Z), mapped with g().
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
sys.path.insert(0, HERE)
import build_hospital_assets as base  # noqa: E402

g, gs, mat, box, cyl, finish = base.g, base.gs, base.mat, base.box, base.cyl, base.finish

PAL = {
    "skin": "#e2a672", "hair": "#3a271f", "teal": "#1f9a8b", "tealDark": "#1a8578",
    "sole": "#2cb8a6", "coat": "#f2efeb", "coatShade": "#e3dfd9", "navy": "#232b4b",
    "amber": "#f2a32a", "steel": "#cfd4da", "iris": "#4b2717", "pupil": "#140a06",
    "mouth": "#8e3b2e", "blush": "#e58f70",
}

BONES = {
    "hips": ((0, 1.55, 0), (0, 1.95, 0), None),
    "torso": ((0, 1.95, 0), (0, 2.85, 0), "hips"),
    "head": ((0, 2.85, 0), (0, 4.6, 0), "torso"),
    "arm.L": ((0.8, 2.75, 0), (0.88, 1.6, 0), "torso"),
    "arm.R": ((-0.8, 2.75, 0), (-0.88, 1.6, 0), "torso"),
    "leg.L": ((0.3, 1.6, 0), (0.3, 0.85, 0), "hips"),
    "shin.L": ((0.3, 0.85, 0), (0.3, 0.1, 0), "leg.L"),
    "leg.R": ((-0.3, 1.6, 0), (-0.3, 0.85, 0), "hips"),
    "shin.R": ((-0.3, 0.85, 0), (-0.3, 0.1, 0), "leg.R"),
}


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.actions, bpy.data.curves):
        for d in list(coll):
            coll.remove(d)
    base._mats.clear()


def m(key, rough=0.55, metal=0.0):
    return mat(key, PAL[key], rough, metal)


def blob(name, r, pos, material, scale=(1, 1, 1), rot=(0, 0, 0), segs=20):
    """Ellipsoid. rot is Blender-space degrees (X=pitch, Y=roll, Z=yaw)."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2, radius=r, location=g(*pos))
    o = bpy.context.active_object
    o.scale = gs(*scale)
    o.rotation_euler = [math.radians(a) for a in rot]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    finish(o, name, material)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def rbox(name, size, pos, material, bevel=0.12, rot=(0, 0, 0)):
    o = box(name, size, pos, material, bevel=bevel)
    o.modifiers["bevel"].segments = 4
    if any(rot):
        o.rotation_euler = [math.radians(a) for a in rot]
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return o


def tube(name, pts, radius, material, caps=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    cu.use_fill_caps = caps
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = g(*p)
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    o.data.materials.append(material)
    o.name = name
    return o


def build_parts():
    P = []  # (object, bone)

    def add(o, bone):
        P.append((o, bone))

    skin, hair, teal = m("skin", 0.6), m("hair", 0.45), m("teal", 0.75)
    coat, navy = m("coat", 0.85), m("navy", 0.4)
    steel = m("steel", 0.25, 0.8)

    # ---- head (chibi: ~40% of height)
    add(blob("head", 0.96, (0, 3.72, 0), skin, (1.04, 0.92, 0.97), segs=32), "head")
    for s in (1, -1):
        add(blob(f"ear{s}", 0.17, (s * 0.98, 3.62, -0.02), skin, (0.5, 1.0, 0.8)), "head")
        # eyes: iris, pupil, two highlights
        x = s * 0.37
        add(blob(f"iris{s}", 0.22, (x, 3.56, 0.78), m("iris", 0.2), (0.88, 1.12, 0.4)), "head")
        add(blob(f"pupil{s}", 0.12, (x, 3.56, 0.825), m("pupil", 0.2), (0.9, 1.1, 0.5)), "head")
        add(blob(f"glintA{s}", 0.045, (x - 0.07, 3.67, 0.865), mat("glint", "#ffffff", 0.2, emit=0.4), (1, 1, 0.5), segs=10), "head")
        add(blob(f"glintB{s}", 0.025, (x + 0.08, 3.46, 0.865), mat("glint", "#ffffff", 0.2, emit=0.4), (1, 1, 0.5), segs=10), "head")
        # brows: thick, angled slightly down toward the nose
        add(blob(f"brow{s}", 0.1, (x + s * 0.02, 3.92, 0.76), hair, (1.8, 0.5, 0.55), rot=(0, s * 8, 0), segs=12), "head")
        add(blob(f"blush{s}", 0.15, (s * 0.6, 3.34, 0.6), m("blush", 0.8), (1.2, 0.8, 0.3), segs=12), "head")
    add(blob("nose", 0.09, (0, 3.44, 0.88), skin, (1, 0.8, 0.8), segs=12), "head")
    add(tube("mouth", [(-0.2, 3.33, 0.76), (0.0, 3.25, 0.8), (0.24, 3.35, 0.75)], 0.022, m("mouth", 0.5)), "head")
    add(cyl("neck", 0.2, 0.3, (0, 2.8, 0), skin), "torso")

    # ---- hair: cap, quiff, swept fringe, side tufts, nape
    add(blob("hairCap", 1.03, (0, 4.1, -0.22), hair, (1.04, 0.84, 1.0), segs=32), "head")
    add(blob("hairQuiff", 0.5, (0.14, 4.66, 0.2), hair, (1.4, 0.62, 1.2), rot=(0, -10, 0)), "head")
    add(blob("hairBack", 0.55, (0, 3.7, -0.78), hair, (1.6, 1.15, 0.8)), "head")
    for i, (x, y, z, sx, rr) in enumerate([(0.62, 4.22, 0.52, 1.6, -30), (0.2, 4.3, 0.62, 1.6, -14),
                                           (-0.25, 4.28, 0.6, 1.6, 10), (-0.68, 4.2, 0.5, 1.4, 32)]):
        add(blob(f"fringe{i}", 0.3, (x, y, z), hair, (sx, 0.65, 0.85), rot=(0, rr, 0), segs=14), "head")
    for s in (1, -1):
        add(blob(f"sideburn{s}", 0.3, (s * 0.93, 4.0, -0.1), hair, (0.55, 1.15, 1.25)), "head")

    # ---- torso: scrubs, open lab coat, pockets
    add(rbox("scrubTop", (1.0, 0.95, 0.66), (0, 2.4, 0), teal, 0.2), "torso")
    add(blob("vneck", 0.2, (0, 2.8, 0.32), skin, (1.0, 1.3, 0.35), segs=12), "torso")
    add(rbox("pelvis", (1.05, 0.5, 0.68), (0, 1.8, 0), teal, 0.15), "hips")
    add(rbox("coatBack", (1.3, 1.45, 0.2), (0, 2.18, -0.33), coat, 0.1), "torso")
    add(rbox("coatShoulders", (1.3, 0.3, 0.68), (0, 2.88, 0), coat, 0.12), "torso")
    for s in (1, -1):
        add(rbox(f"coatSide{s}", (0.2, 1.45, 0.72), (s * 0.62, 2.18, 0), coat, 0.08), "torso")
        add(rbox(f"coatFront{s}", (0.42, 1.4, 0.16), (s * 0.43, 2.18, 0.37), coat, 0.07, rot=(0, 0, s * 4)), "torso")
        add(rbox(f"pocket{s}", (0.38, 0.34, 0.07), (s * 0.43, 1.82, 0.49), m("coatShade", 0.9), 0.04), "torso")

    # ---- arms: short coat sleeves, skin forearms, hands
    for s, b in ((1, "L"), (-1, "R")):
        x = s * 0.82
        add(rbox(f"sleeve{b}", (0.42, 0.62, 0.48), (x, 2.62, 0), coat, 0.13), f"arm.{b}")
        add(rbox(f"forearm{b}", (0.3, 0.7, 0.32), (x, 2.0, 0), skin, 0.12), f"arm.{b}")
        add(blob(f"hand{b}", 0.22, (x, 1.58, 0.02), skin, (0.95, 1.05, 0.9)), f"arm.{b}")

    # ---- legs: cargo pants, cuffs, sneakers with teal soles
    for s, b in ((1, "L"), (-1, "R")):
        x = s * 0.32
        add(rbox(f"thigh{b}", (0.58, 0.8, 0.6), (x, 1.2, 0), teal, 0.14), f"leg.{b}")
        add(rbox(f"shin{b}", (0.52, 0.72, 0.54), (x, 0.55, 0), teal, 0.14), f"shin.{b}")
        add(rbox(f"cargo{b}", (0.14, 0.42, 0.38), (s * 0.64, 1.1, 0.02), m("tealDark", 0.8), 0.05), f"leg.{b}")
        add(rbox(f"shoe{b}", (0.62, 0.34, 0.95), (x, 0.28, 0.1), navy, 0.1), f"shin.{b}")
        add(blob(f"toe{b}", 0.31, (x, 0.28, 0.55), navy, (1.0, 0.75, 1.0)), f"shin.{b}")
        add(rbox(f"sole{b}", (0.68, 0.13, 1.08), (x, 0.065, 0.13), m("sole", 0.6), 0.05), f"shin.{b}")

    # ---- stethoscope + ID clip
    bpy.ops.mesh.primitive_torus_add(major_radius=0.4, minor_radius=0.045, location=g(0, 3.0, 0.04))
    ring = finish(bpy.context.active_object, "stethRing", navy)
    add(ring, "torso")
    add(tube("stethA", [(0.34, 2.97, 0.28), (0.4, 2.6, 0.5), (0.3, 2.22, 0.56)], 0.04, navy), "torso")
    add(tube("stethB", [(-0.34, 2.97, 0.28), (-0.38, 2.65, 0.5), (-0.26, 2.38, 0.55)], 0.04, navy), "torso")
    add(cyl("stethBell", 0.14, 0.06, (0.3, 2.16, 0.58), steel, verts=20, axis="z"), "torso")
    add(blob("stethTip", 0.07, (-0.26, 2.34, 0.56), steel, segs=10), "torso")
    add(rbox("idCard", (0.24, 0.34, 0.05), (-0.52, 2.3, 0.5), m("amber", 0.5), 0.03), "torso")
    add(rbox("idClip", (0.12, 0.09, 0.07), (-0.52, 2.5, 0.5), steel, 0.02), "torso")
    return P


def build():
    clear_scene()
    parts = build_parts()

    arm_data = bpy.data.armatures.new("doctorRig")
    rig = bpy.data.objects.new("doctorRig", arm_data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for bname, (h, t, parent) in BONES.items():
        eb = arm_data.edit_bones.new(bname)
        eb.head, eb.tail = g(*h), g(*t)
        if parent:
            eb.parent = arm_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")

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
    body.name = "doctorBody"
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    except (AttributeError, RuntimeError):
        bpy.ops.object.shade_smooth()
    body.parent = rig
    mod = body.modifiers.new("rig", "ARMATURE")
    mod.object = rig
    base.make_actions(rig)
    return rig


if __name__ == "__main__":
    build()
    base.export(os.path.join(base.OUT, "doctor.glb"), animations=True)
