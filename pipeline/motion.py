"""OpenGymMotion — the one motion format every source is converted into,
and the canonical skeleton that plays it without Blender.

    python3 pipeline/motion.py m2m  cc0/mesh2motion/human-addon-animations.glb#Pushup out.json
    python3 pipeline/motion.py cmu  motions/cmu/13.asf motions/cmu/13_29.amc out.json --start 3 --end 6
    python3 pipeline/motion.py show motions/video/lunge_demo.json          # -> lunge_demo.skeleton.png
    python3 pipeline/motion.py info motions/video/lunge_demo.json

Format `opengym3d-motion/1` (pipeline/video_mocap.py wrote it first):

    {"format": "opengym3d-motion/1", "fps": 30, "source": ..., "license": ...,
     "skeleton": "opengym3d_v1",
     "frames": [{"hip_height": m above the floor,
                 "root": [dx, dy, dz] pelvis travel since frame 0 (Blender, Z up),
                 "pelvis": {"left": [..], "forward": [..], "up": [..]},
                 "dirs":   {bone: [x, y, z] world unit direction, 16 bones},
                 "twists": {bone: [x, y, z] the bone's rolled reference}}]}

World frame is Blender's: +Z up, the figure faces -Y, its left is +X. The
16 bones are the canonical skeleton `opengym3d_v1` — the same driver rig
build_exercise.py aims the MakeHuman bones at (BONES there, CANONICAL here;
tests fail if they drift apart):

    pelvis → spine → chest → neck → head
    chest  → upper_arm.{L,R} → forearm → hand
    pelvis → thigh.{L,R} → shin → foot

Nothing downstream knows where a motion came from. Adapters:

    from_m2m(glb, clip)      Mesh2Motion / Quaternius packs (CC0, glTF Y-up)
    from_cmu(asf, amc, ...)  CMU mocap database (ASF/AMC, Y-up, 120 fps)
    video_mocap.py           phone / video (MediaPipe)
    Mixamo FBX               needs Blender's FBX importer — CI only, see
                             build_exercise.animate_mocap

`skeleton_frames(motion)` runs the canonical skeleton's FK on a motion and
returns joint positions under the MakeHuman names the gates use, in glTF
Y-up like a sampled GLB — so anatomy_qa.evaluate and sheet_glb.draw grade
and draw a motion before any render exists.
"""

import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_glb  # noqa: E402

FORMAT = "opengym3d-motion/1"
SKELETON = "opengym3d_v1"

# rest pose of the canonical skeleton: bone -> (head, tail), Blender metres.
# Mirror of build_exercise.BONES (left side; right is x-mirrored).
CANONICAL = {
    "pelvis":      ((0.00, 0.0, 0.95), (0.00, 0.0, 1.06)),
    "spine":       ((0.00, 0.0, 1.06), (0.00, 0.0, 1.30)),
    "chest":       ((0.00, 0.0, 1.30), (0.00, 0.0, 1.50)),
    "neck":        ((0.00, 0.0, 1.50), (0.00, 0.0, 1.58)),
    "head":        ((0.00, 0.0, 1.58), (0.00, 0.0, 1.76)),
    "upper_arm.L": ((0.18, 0.0, 1.46), (0.42, 0.0, 1.46)),
    "forearm.L":   ((0.42, 0.0, 1.46), (0.66, 0.0, 1.46)),
    "hand.L":      ((0.66, 0.0, 1.46), (0.78, 0.0, 1.46)),
    "thigh.L":     ((0.10, 0.0, 0.95), (0.10, 0.0, 0.52)),
    "shin.L":      ((0.10, 0.0, 0.52), (0.10, 0.0, 0.09)),
    "foot.L":      ((0.10, 0.0, 0.09), (0.10, -0.18, 0.02)),
}
DIR_BONES = ["spine", "chest", "neck", "head",
             "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R",
             "upper_arm.L", "forearm.L", "hand.L", "upper_arm.R", "forearm.R", "hand.R"]
REST_BASIS = ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0))   # left, forward, up


# ------------------------------------------------------------------ vectors

def _n(v):
    l = math.sqrt(sum(c * c for c in v)) or 1e-9
    return tuple(c / l for c in v)


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _mul(v, s):
    return tuple(c * s for c in v)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _mv(m, v):
    return tuple(sum(m[r][c] * v[c] for c in range(3)) for r in range(3))


def _mm(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)] for r in range(3)]


def _mt(m):
    return [[m[c][r] for c in range(3)] for r in range(3)]


def _rx(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def _ry(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def _rz(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def _rot_about(axis, ang):
    """Rodrigues rotation matrix about a unit axis (radians)."""
    x, y, z = axis
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    return [[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C]]


def yup_to_blender(v):
    """glTF / CMU (Y up, facing +Z) -> Blender (Z up, facing -Y)."""
    return (v[0], -v[2], v[1])


def blender_to_yup(v):
    return (v[0], v[2], -v[1])


def twist_ref(rest_dir):
    """build_exercise.twist_ref: the world vector a bone's roll is measured
    against — forward (-Y) for what stands or hangs, up (+Z) for the feet."""
    for ref in ((0, -1, 0), (0, 0, 1), (1, 0, 0)):
        side = _sub(ref, _mul(rest_dir, _dot(ref, rest_dir)))
        if math.sqrt(_dot(side, side)) > 0.3:
            return _n(side)
    return (0.0, -1.0, 0.0)


# ------------------------------------------------------------------ format

def load(path):
    m = json.loads(Path(path).read_text())
    if m.get("format") != FORMAT:
        raise ValueError(f"{path}: not {FORMAT}")
    return m


def save(motion, path):
    Path(path).write_text(json.dumps(motion, indent=None, separators=(",", ":")) + "\n")


def new(frames, fps, source, license, **meta):
    m = {"format": FORMAT, "skeleton": SKELETON, "fps": fps, "source": source,
         "license": license}
    m.update(meta)
    m["frames"] = frames
    return m


def _r(v, nd=5):
    return [round(float(c), nd) for c in v]


def make_frame(hip_height, root, left, forward, up, dirs, twists):
    return {"hip_height": round(float(hip_height), 5), "root": _r(root),
            "pelvis": {"left": _r(left), "forward": _r(forward), "up": _r(up)},
            "dirs": {k: _r(v) for k, v in dirs.items()},
            "twists": {k: _r(v) for k, v in twists.items()}}


# ------------------------------------------------------------------ FK

def _mirror(name):
    return name[:-2] + (".R" if name.endswith(".L") else ".L")


def rest_bones():
    out = {}
    for name, (h, t) in CANONICAL.items():
        out[name] = (h, t)
        if name.endswith(".L"):
            out[_mirror(name)] = ((-h[0], h[1], h[2]), (-t[0], t[1], t[2]))
    return out


def skeleton_frames(motion, samples_per_sec=None):
    """Play a motion on the canonical skeleton. Returns (frames, times,
    names): per frame a dict of MakeHuman joint names -> glTF Y-up position,
    exactly what qa_glb.sample_clip gives for a GLB, so the anatomy gate and
    the sheet take it unchanged."""
    bones = rest_bones()
    L = {b: math.dist(h, t) for b, (h, t) in bones.items()}
    fps = motion["fps"]
    step = max(1, int(round(fps / samples_per_sec))) if samples_per_sec else 1
    frames, times = [], []
    h0 = max(motion["frames"][0]["hip_height"], 1e-6)
    scale = CANONICAL["pelvis"][0][2] / h0           # capture height -> rig height
    for i, fr in enumerate(motion["frames"][::step]):
        d = {k: _n(v) for k, v in fr["dirs"].items()}
        left, fwd, up = (_n(fr["pelvis"][k]) for k in ("left", "forward", "up"))
        root = _add((0.0, 0.0, CANONICAL["pelvis"][0][2]), _mul(fr["root"], scale))
        P = {}
        P["root"] = root
        # pelvis: hips sit on the pelvis's own lateral axis
        hipL = _add(root, _mul(left, bones["thigh.L"][0][0]))
        hipR = _add(root, _mul(left, bones["thigh.R"][0][0]))
        P["upperleg01.L"], P["upperleg01.R"] = hipL, hipR
        for side, hip in (("L", hipL), ("R", hipR)):
            knee = _add(hip, _mul(d["thigh." + side], L["thigh." + side]))
            ank = _add(knee, _mul(d["shin." + side], L["shin." + side]))
            toe = _add(ank, _mul(d["foot." + side], L["foot." + side]))
            P["upperleg02." + side] = _add(hip, _mul(_sub(knee, hip), 0.5))
            P["lowerleg01." + side] = knee
            P["lowerleg02." + side] = _add(knee, _mul(_sub(ank, knee), 0.5))
            P["foot." + side] = ank
            P["toe." + side] = toe
        spine_h = _add(root, _mul(up, L["pelvis"]))
        chest_h = _add(spine_h, _mul(d["spine"], L["spine"]))
        neck_h = _add(chest_h, _mul(d["chest"], L["chest"]))
        head_h = _add(neck_h, _mul(d["neck"], L["neck"]))
        head_t = _add(head_h, _mul(d["head"], L["head"]))
        P["spine03"], P["spine01"], P["neck01"], P["head"] = spine_h, chest_h, neck_h, head_h
        P["head_top"] = head_t
        # shoulders ride the chest: its lateral axis is the pelvis's left
        # made perpendicular to the chest direction
        cd = d["chest"]
        lat = _n(_sub(left, _mul(cd, _dot(left, cd))))
        sh_up = bones["upper_arm.L"][0][2] - bones["chest"][0][2]      # 0.16 up the chest
        for side, sgn in (("L", 1.0), ("R", -1.0)):
            sh = _add(_add(chest_h, _mul(cd, sh_up)),
                      _mul(lat, sgn * bones["upper_arm.L"][0][0]))
            el = _add(sh, _mul(d["upper_arm." + side], L["upper_arm." + side]))
            wr = _add(el, _mul(d["forearm." + side], L["forearm." + side]))
            hd = _add(wr, _mul(d["hand." + side], L["hand." + side]))
            P["upperarm01." + side] = sh
            P["upperarm02." + side] = _add(sh, _mul(_sub(el, sh), 0.5))
            P["lowerarm01." + side] = el
            P["lowerarm02." + side] = _add(el, _mul(_sub(wr, el), 0.5))
            P["wrist." + side] = wr
            P["finger3-1." + side] = hd
        frames.append({k: blender_to_yup(v) for k, v in P.items()})
        times.append(i * step / fps)
    names = {k: i for i, k in enumerate(frames[0])}
    return frames, times, names


# ------------------------------------------------------------------ adapters

def _yaw_to_face_minus_y(fwd0):
    """Rotation about Z that turns the frame-0 forward onto -Y."""
    f = _n((fwd0[0], fwd0[1], 0.0))
    ang = math.atan2(-1.0, 0.0) - math.atan2(f[1], f[0])
    return _rz(math.degrees(ang))


def _finish(raw, fps, source, license, **meta):
    """raw: per frame {"pos": {joint: blender pos}, "rot": {joint: world 3x3},
    "rest_rot": {joint: 3x3}, "rest_pos": {joint: pos}} plus the SEG map
    (canonical bone -> (joint, child joint)) and PELVIS joint name. Turns
    joint positions into directions, rolls, pelvis basis and hip height —
    the same maths for every source."""
    SEG, pelvis, hips = raw["seg"], raw["pelvis"], raw["hips"]
    floor_pts = raw.get("floor", [])
    frames_out = []
    R = None
    for k, fr in enumerate(raw["frames"]):
        pos = fr["pos"]
        left = _n(_sub(pos[hips[0]], pos[hips[1]]))
        up_hint = _n(_sub(pos[SEG["spine"][1]], pos[pelvis]))
        fwd = _n(_cross(left, up_hint))
        if R is None:
            R = _yaw_to_face_minus_y(fwd)
        pos = {j: _mv(R, p) for j, p in pos.items()}
        left, fwd = _mv(R, left), _mv(R, fwd)
        up = _n(_cross(fwd, left))
        dirs, twists = {}, {}
        for bone, (j, child) in SEG.items():
            a, b = pos[j], pos[child]
            dirs[bone] = _n(_sub(b, a))
            rest_dir = _n(_sub(raw["rest_pos"][child], raw["rest_pos"][j]))
            delta = _mm(_mm(R, fr["rot"][j]), _mt(raw["rest_rot"][j]))
            twists[bone] = _n(_mv(delta, twist_ref(rest_dir)))
        floor = min(pos[j][2] for j in floor_pts) if floor_pts else 0.0
        hip_h = pos[pelvis][2] - floor
        if k == 0:
            p0 = pos[pelvis]
            hh0 = hip_h
        root = (0.0, 0.0, hip_h - hh0)          # in-place render: vertical travel only
        frames_out.append(make_frame(hip_h, root, left, fwd, up, dirs, twists))
    return new(frames_out, fps, source, license, **meta)


M2M_SEG = {
    "spine": ("spine_01", "spine_03"), "chest": ("spine_03", "neck_01"),
    "neck": ("neck_01", "head"), "head": ("head", "head_leaf"),
    "thigh.L": ("thigh_l", "calf_l"), "shin.L": ("calf_l", "foot_l"), "foot.L": ("foot_l", "ball_l"),
    "upper_arm.L": ("upperarm_l", "lowerarm_l"), "forearm.L": ("lowerarm_l", "hand_l"),
    "hand.L": ("hand_l", "middle_01_l"),
    "thigh.R": ("thigh_r", "calf_r"), "shin.R": ("calf_r", "foot_r"), "foot.R": ("foot_r", "ball_r"),
    "upper_arm.R": ("upperarm_r", "lowerarm_r"), "forearm.R": ("lowerarm_r", "hand_r"),
    "hand.R": ("hand_r", "middle_01_r"),
}


def from_m2m(glb_path, clip, fps=30, source=None, license="CC0-1.0"):
    """A Mesh2Motion pack clip (UE-mannequin names, glTF Y-up) -> motion."""
    gltf, blob = qa_glb.load_glb(glb_path)
    c = qa_glb.Clip(gltf, blob, animation=clip)
    names = c.by_name
    joints = {j for pair in M2M_SEG.values() for j in pair} | {"pelvis", "thigh_l", "thigh_r",
                                                                "ball_l", "ball_r"}
    rest = qa_glb.Clip(dict(gltf, animations=[]), blob).world(0)
    rest_pos = {j: yup_to_blender(qa_glb.m_pos(rest[names[j]])) for j in joints}
    Y2B = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
    rest_rot = {j: _mm(Y2B, qa_glb.m_rot(rest[names[j]])) for j in joints}
    n = max(2, int(round(c.duration * fps)) + 1)
    frames = []
    for i in range(n):
        w = c.world(i / fps)
        frames.append({"pos": {j: yup_to_blender(qa_glb.m_pos(w[names[j]])) for j in joints},
                       "rot": {j: _mm(Y2B, qa_glb.m_rot(w[names[j]])) for j in joints}})
    raw = {"seg": M2M_SEG, "pelvis": "pelvis", "hips": ("thigh_l", "thigh_r"),
           "floor": ["foot_l", "foot_r", "ball_l", "ball_r"],
           "rest_pos": rest_pos, "rest_rot": rest_rot, "frames": frames}
    return _finish(raw, fps, source or f"Mesh2Motion {Path(glb_path).name}#{clip}", license,
                   tool="pipeline/motion.py from_m2m", clip=clip, axial_rotation="from the source rig")


# canonical bone -> the CMU bone that IS that segment (second item unused,
# kept for reading: the next bone down the chain)
CMU_SEG = {
    "spine": ("lowerback", "upperback"), "chest": ("thorax", "lowerneck"),
    "neck": ("lowerneck", "upperneck"), "head": ("head", None),
    "thigh.L": ("lfemur", "ltibia"), "shin.L": ("ltibia", "lfoot"), "foot.L": ("lfoot", "ltoes"),
    "upper_arm.L": ("lhumerus", "lradius"), "forearm.L": ("lradius", "lwrist"),
    "hand.L": ("lhand", "lfingers"),
    "thigh.R": ("rfemur", "rtibia"), "shin.R": ("rtibia", "rfoot"), "foot.R": ("rfoot", "rtoes"),
    "upper_arm.R": ("rhumerus", "rradius"), "forearm.R": ("rradius", "rwrist"),
    "hand.R": ("rhand", "rfingers"),
}
CMU_SCALE = 0.0254 / 0.45     # ASF length unit -> metres


def parse_asf(text):
    units = re.search(r"length\s+([\d.]+)", text)
    scale = 0.0254 / float(units.group(1)) if units else CMU_SCALE
    bones = {}
    for m in re.finditer(r"begin\s+id\s+\d+\s+name\s+(\S+)\s+direction\s+([-\d.e ]+?)\s+length\s+"
                         r"([\d.e-]+)\s+axis\s+([-\d.e ]+?)\s+XYZ(?:\s+dof\s+([a-z ]+?))?\s+(?:limits.*?)?end",
                         text, re.S):
        name, d, ln, ax, dof = m.groups()
        bones[name] = {"dir": _n([float(x) for x in d.split()]), "len": float(ln) * scale,
                       "axis": [float(x) for x in ax.split()],
                       "dof": dof.split() if dof else []}
    hier = {}
    body = re.search(r":hierarchy\s+begin(.*?)end", text, re.S).group(1)
    for line in body.strip().splitlines():
        parts = line.split()
        for ch in parts[1:]:
            hier[ch] = parts[0]
    root = re.search(r":root.*?order\s+([A-Z ]+?)\n", text, re.S)
    return {"bones": bones, "parent": hier, "scale": scale,
            "root_order": root.group(1).split() if root else ["TX", "TY", "TZ", "RX", "RY", "RZ"]}


def parse_amc(text):
    frames, cur = [], None
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", ":")):
            continue
        if re.fullmatch(r"\d+", s):
            cur = {}
            frames.append(cur)
            continue
        parts = s.split()
        cur[parts[0]] = [float(x) for x in parts[1:]]
    return frames


def _cmu_pose(asf, amc_frame):
    """World (pos, rot) of every joint for one AMC frame, Y-up metres."""
    B, parent = asf["bones"], asf["parent"]
    rv = amc_frame["root"]
    order = asf["root_order"]
    t = [0.0, 0.0, 0.0]
    r = {"RX": 0.0, "RY": 0.0, "RZ": 0.0}
    for k, v in zip(order, rv):
        if k.startswith("T"):
            t["XYZ".index(k[1])] = v * asf["scale"]
        else:
            r[k] = v
    Rroot = _mm(_rz(r["RZ"]), _mm(_ry(r["RY"]), _rx(r["RX"])))
    pos = {"root": tuple(t)}
    rot = {"root": Rroot}

    def rec(name):
        b = B[name]
        p = parent[name]
        if p not in pos:
            rec(p)
        ax = b["axis"]
        C = _mm(_rz(ax[2]), _mm(_ry(ax[1]), _rx(ax[0])))
        vals = dict(zip(b["dof"], amc_frame.get(name, [])))
        M = _mm(_rz(vals.get("rz", 0.0)), _mm(_ry(vals.get("ry", 0.0)), _rx(vals.get("rx", 0.0))))
        Lm = _mm(C, _mm(M, _mt(C)))
        W = _mm(rot[p], Lm)
        rot[name] = W
        pos[name] = _add(pos[p], _mv(W, _mul(b["dir"], b["len"])))
    for name in B:
        if name not in pos:
            rec(name)
    return pos, rot


def from_cmu(asf_path, amc_path, start=0.0, end=None, fps=30, source=None,
             license="CMU-mocap"):
    """CMU ASF/AMC (120 fps, Y-up, inches/0.45) -> motion, trimmed to [start, end] s.
    Joint = the bone's TAIL (where the next bone starts), which is what the
    canonical segments need; the pelvis joint is the root position."""
    asf = parse_asf(Path(asf_path).read_text())
    amc = parse_amc(Path(amc_path).read_text())
    src_fps = 120.0
    i0 = int(start * src_fps)
    i1 = int(end * src_fps) if end else len(amc)
    step = src_fps / fps
    rest_pos, rest_rot = _cmu_pose(asf, {"root": [0, 0, 0, 0, 0, 0]})
    rest_pos = {j: yup_to_blender(p) for j, p in rest_pos.items()}
    Y2B = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
    rest_rot = {j: _mm(Y2B, m) for j, m in rest_rot.items()}
    frames = []
    k = float(i0)
    while k < i1:
        pos, rot = _cmu_pose(asf, amc[int(k)])
        pos = {j: yup_to_blender(p) for j, p in pos.items()}
        frames.append({"pos": pos, "rot": {j: _mm(Y2B, m) for j, m in rot.items()}})
        k += step
    # _cmu_pose stores each bone's TAIL under the bone's name, so a canonical
    # segment runs from its bone's parent tail (where the bone starts) to its
    # own tail: thigh.L = lhipjoint -> lfemur, shin.L = lfemur -> ltibia.
    seg = {bone: (asf["parent"][a], a) for bone, (a, _) in CMU_SEG.items()}
    raw = {"seg": seg, "pelvis": "root", "hips": ("lhipjoint", "rhipjoint"),
           "floor": ["lfoot", "rfoot", "ltoes", "rtoes"],
           "rest_pos": rest_pos, "rest_rot": rest_rot, "frames": frames}
    return _finish(raw, fps, source or f"CMU mocap {Path(amc_path).stem}", license,
                   tool="pipeline/motion.py from_cmu", range_s=[start, end],
                   axial_rotation="from the source rig")


# ------------------------------------------------------------------ CLI

def show(motion_path, out=None):
    import sheet_glb
    m = load(motion_path)
    frames, times, names = skeleton_frames(m)
    out = Path(out) if out else Path(str(motion_path).replace(".json", ".skeleton.png"))
    sheet_glb.draw(frames, times, out)
    return out


def info(motion_path):
    m = load(motion_path)
    n = len(m["frames"])
    hh = [f["hip_height"] for f in m["frames"]]
    print(f"{motion_path}: {m['skeleton'] if 'skeleton' in m else '?'} {n} frames @ {m['fps']} fps "
          f"= {n / m['fps']:.2f}s  licence {m.get('license')}  hip {min(hh):.2f}-{max(hh):.2f} m")
    print(f"  source: {m.get('source')}")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd, *rest = argv
    if cmd == "m2m":
        ref, out = rest[0], rest[1]
        file, clip = ref.split("#", 1)
        repo = Path(__file__).resolve().parent.parent
        m = from_m2m(repo / "motions" / file, clip)
        save(m, out)
        info(out)
        return 0
    if cmd == "cmu":
        asf, amc, out = rest[:3]
        opts = dict(zip(rest[3::2], rest[4::2]))
        m = from_cmu(asf, amc, start=float(opts.get("--start", 0)),
                     end=float(opts["--end"]) if "--end" in opts else None)
        save(m, out)
        info(out)
        return 0
    if cmd == "show":
        for p in rest:
            print(show(p))
        return 0
    if cmd == "info":
        for p in rest:
            info(p)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
