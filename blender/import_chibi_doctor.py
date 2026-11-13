"""Turn the generated chibi doctor GLB into the game's player model.

Run: blender -b -P blender/import_chibi_doctor.py -- [src.glb] [out.glb] [tex_px]
Default: blender/source/chibi_doctor.glb -> doctor.glb at 1024 px. Also builds hub NPCs.
Scales to hub height, shrinks textures, adds `idle` and `walk` clips, exports
client/public/game-assets/3d/doctor.glb.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from uv_island_margin import repack  # noqa: E402
SRC = os.path.join(HERE, "source", "chibi_doctor.glb")
OUT = os.path.join(ROOT, "client", "public", "game-assets", "3d", "doctor.glb")
HEIGHT = 4.7  # matches the old procedural doctor in the Babylon hub
TEX_SIZE = 1024


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.actions, bpy.data.images):
        for d in list(coll):
            coll.remove(d)


def import_model(src):
    bpy.ops.import_scene.gltf(filepath=src)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    body = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm)
    for o in [o for o in bpy.data.objects if o not in (arm, body)]:
        bpy.data.objects.remove(o, do_unlink=True)  # stray helper meshes in the generated file
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)  # source clip is a single rest-pose frame
    arm.animation_data_clear()

    arm.scale = [v * HEIGHT / body.dimensions.z for v in arm.scale]
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return arm, body


def shrink_textures(size=TEX_SIZE):
    # UV islands are packed edge to edge, so shrinking the color map bleeds islands into visible cracks.
    color = set()
    for mat in bpy.data.materials:
        for node in (mat.node_tree.nodes if mat.node_tree else []):
            if node.type == "BSDF_PRINCIPLED":
                for link in node.inputs["Base Color"].links:
                    if link.from_node.type == "TEX_IMAGE":
                        color.add(link.from_node.image)
    for img in bpy.data.images:
        if img not in color and img.size[0] > size:
            img.scale(size, size)


def world_rot(arm, bone_name, axis, angle):
    """Pose-bone local quaternion for a rotation about a world axis (armature has identity transform)."""
    rest = arm.data.bones[bone_name].matrix_local.to_3x3()
    r = Matrix.Rotation(angle, 3, axis)
    return (rest.inverted() @ r @ rest).to_quaternion()


def make_clips(arm):
    pb = arm.pose.bones
    for b in pb:
        b.rotation_mode = "QUATERNION"
    arm.animation_data_create()

    def key(frame, pose):
        for b in pb:
            b.rotation_quaternion = Quaternion()
            b.location = (0, 0, 0)
        for name, val in pose.items():
            if name == "_bob":
                continue
            axis, angle = val
            pb[name].rotation_quaternion = world_rot(arm, name, axis, angle)
        hips_rest = arm.data.bones["Hips"].matrix_local.to_3x3()
        pb["Hips"].location = hips_rest.inverted() @ Vector((0, 0, pose.get("_bob", 0.0)))
        for b in pb:
            b.keyframe_insert("rotation_quaternion", frame=frame)
            b.keyframe_insert("location", frame=frame)

    # Rotation about world +X moves a hanging limb backward (+Y); the model faces -Y.
    def walk(t):
        p = t * 2 * math.pi
        s, c = math.sin(p), math.cos(p)
        amp = 0.5
        return {
            "LeftUpLeg": ("X", -s * amp),
            "RightUpLeg": ("X", s * amp),
            "LeftLeg": ("X", max(0.0, c) * amp * 1.4),
            "RightLeg": ("X", max(0.0, -c) * amp * 1.4),
            "LeftArm": ("X", s * amp * 0.8),
            "RightArm": ("X", -s * amp * 0.8),
            "LeftForeArm": ("X", -0.25),
            "RightForeArm": ("X", -0.25),
            "Spine": ("Z", s * 0.06),
            "_bob": abs(c) * 0.06,
        }

    def idle(t):
        p = t * 2 * math.pi
        return {
            "Spine01": ("X", math.sin(p) * 0.03),
            "Head": ("Z", math.sin(p) * 0.08),
            "LeftArm": ("Y", math.sin(p) * 0.04),
            "RightArm": ("Y", -math.sin(p) * 0.04),
        }

    for clip, length, fn in (("walk", 24, walk), ("idle", 48, idle)):
        action = bpy.data.actions.new(clip)
        action.use_fake_user = True
        arm.animation_data.action = action
        steps = 8
        for i in range(steps + 1):
            key(1 + i * length / steps, fn(i / steps))
        track = arm.animation_data.nla_tracks.new()
        track.name = clip
        track.strips.new(clip, 1, action)
        arm.animation_data.action = None


def export(path):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        export_yup=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_image_format="JPEG",
        export_jpeg_quality=85,
    )
    print("exported", path, os.path.getsize(path))


def build(src=SRC, tex=TEX_SIZE):
    clear_scene()
    arm, body = import_model(src)
    repack(body)
    shrink_textures(tex)
    make_clips(arm)
    return arm


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    build(argv[0] if argv else SRC, int(argv[2]) if len(argv) > 2 else TEX_SIZE)
    export(argv[1] if len(argv) > 1 else OUT)
