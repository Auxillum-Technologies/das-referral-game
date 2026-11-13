"""Repack UV islands with a gap, then remap each texture texel-for-texel.

Generated UVs pack islands edge to edge, so filtered samples bleed neighbour
colour across seams. Remap copies raw texel values, so colours stay exact.
"""
import bpy
import numpy as np

REPACK_UV = "UVRepack"
MARGIN = 0.001  # fraction of UV space, 2 texels at 2048 px
PACK_SCALES = (0.66, 0.62, 0.58, 0.54, 0.5)  # island scale before packing, largest that fits 0..1
GAP_FILL_STEPS = 16  # px of gap filled around each island


def _copy_uv_layer(me, src_name, dst_name, scale=1.0):
    src = me.uv_layers[src_name]
    dst = me.uv_layers.new(name=dst_name)
    for i, loop in enumerate(src.data):
        dst.data[i].uv = loop.uv * scale


def _pack_islands(obj, margin):
    me = obj.data
    me.uv_layers.active = me.uv_layers[REPACK_UV]
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    # rotate=False: rotated islands would need tangent-space normal map rotation.
    bpy.ops.uv.pack_islands(margin=margin, scale=False, rotate=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def _texel_map(obj, old_uv, new_uv, w, h):
    """Return (dst_flat, src_flat) texel index pairs for every covered texel."""
    me = obj.data
    me.calc_loop_triangles()
    scale = np.array([w, h], dtype=np.float64)
    dst_parts, src_parts = [], []
    for tri in me.loop_triangles:
        loops = np.array(tri.loops)
        n = new_uv[loops] * scale
        o = old_uv[loops] * scale
        x0 = max(int(np.floor(n[:, 0].min())), 0)
        x1 = min(int(np.ceil(n[:, 0].max())), w - 1)
        y0 = max(int(np.floor(n[:, 1].min())), 0)
        y1 = min(int(np.ceil(n[:, 1].max())), h - 1)
        if x1 < x0 or y1 < y0:
            continue
        d = (n[1, 1] - n[2, 1]) * (n[0, 0] - n[2, 0]) + (n[2, 0] - n[1, 0]) * (n[0, 1] - n[2, 1])
        if abs(d) < 1e-12:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((n[1, 1] - n[2, 1]) * (X - n[2, 0]) + (n[2, 0] - n[1, 0]) * (Y - n[2, 1])) / d
        w1 = ((n[2, 1] - n[0, 1]) * (X - n[2, 0]) + (n[0, 0] - n[2, 0]) * (Y - n[2, 1])) / d
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if not inside.any():
            continue
        ox = (w0 * o[0, 0] + w1 * o[1, 0] + w2 * o[2, 0])[inside]
        oy = (w0 * o[0, 1] + w1 * o[1, 1] + w2 * o[2, 1])[inside]
        sx = np.clip(np.floor(ox).astype(np.int64), 0, w - 1)
        sy = np.clip(np.floor(oy).astype(np.int64), 0, h - 1)
        py, px = np.nonzero(inside)
        dst_parts.append((y0 + py) * w + (x0 + px))
        src_parts.append(sy * w + sx)
    return np.concatenate(dst_parts), np.concatenate(src_parts)


def _fill_gaps(out, cov, steps):
    """Spread covered colours into uncovered texels, averaging covered neighbours."""
    for _ in range(steps):
        acc = np.zeros_like(out)
        cnt = np.zeros(cov.shape, dtype=np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh_cov = np.roll(cov, (dy, dx), axis=(0, 1))
            sh_out = np.roll(out, (dy, dx), axis=(0, 1))
            acc += sh_out * sh_cov[..., None]
            cnt += sh_cov
        fill = (~cov) & (cnt > 0)
        if not fill.any():
            break
        out[fill] = acc[fill] / cnt[fill][:, None]
        cov = cov | fill
    return out


def _read_pixels(img):
    arr = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    return arr.reshape(img.size[1], img.size[0], 4)


def _pack_within_unit(obj, old_name):
    """Pack at the largest scale whose layout stays inside 0..1."""
    me = obj.data
    for scale in PACK_SCALES:
        if REPACK_UV in me.uv_layers:
            me.uv_layers.active = me.uv_layers[old_name]
            me.uv_layers.remove(me.uv_layers[REPACK_UV])
        _copy_uv_layer(me, old_name, REPACK_UV, scale)
        _pack_islands(obj, MARGIN)
        uv = np.array([l.uv for l in me.uv_layers[REPACK_UV].data], dtype=np.float64)
        if uv.min() >= 0.0 and uv.max() <= 1.0:
            print("repack pack scale", scale)
            return uv
    raise RuntimeError("UV repack does not fit 0..1 at any PACK_SCALES value")


def repack(obj):
    me = obj.data
    old_name = me.uv_layers.active.name
    old_uv = np.array([l.uv for l in me.uv_layers[old_name].data], dtype=np.float64)
    new_uv = _pack_within_unit(obj, old_name)

    mat = obj.data.materials[0]
    nodes = [n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image]
    w, h = nodes[0].image.size
    dst_flat, src_flat = _texel_map(obj, old_uv, new_uv, w, h)
    cov = np.zeros(h * w, dtype=bool)
    cov[dst_flat] = True
    cov = cov.reshape(h, w)

    for node in nodes:
        src = node.image
        space = src.colorspace_settings.name
        src_px = _read_pixels(src).reshape(-1, 4)
        out = np.zeros((h * w, 4), dtype=np.float32)
        out[:, 3] = 1.0
        out[dst_flat] = src_px[src_flat]
        out = _fill_gaps(out.reshape(h, w, 4), cov.copy(), GAP_FILL_STEPS)
        dst = bpy.data.images.new(src.name + "_rp", width=w, height=h, alpha=True)
        dst.pixels.foreach_set(out.reshape(-1))
        dst.pack()  # pack before colorspace change, which otherwise drops pixels
        dst.colorspace_settings.name = space
        node.image = dst
        bpy.data.images.remove(src)

    me.uv_layers.remove(me.uv_layers[old_name])
    me.uv_layers[REPACK_UV].name = old_name
    me.uv_layers.active = me.uv_layers[old_name]
