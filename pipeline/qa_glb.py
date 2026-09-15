"""Joint-integrity QA on an exported exercise GLB — no Blender, stdlib only.

    python3 pipeline/qa_glb.py site/assets/snatch.glb exercises/snatch.json
    python3 pipeline/qa_glb.py site/assets/*.glb          # specs looked up by id

The GLB is the thing the viewer shows, so it is the thing to grade: the
skinned skeleton (every MakeHuman bone as a node) and the baked animation
both ship inside it. This samples the clip, rebuilds every joint's world
position per frame, and measures what a human reviewer would otherwise
squint at in a 240 px GIF:

  bone length      a limb segment that changes length is a joint coming apart
  joint angles     elbows and knees are hinges: no hyperextension past 180
  spikes           a joint that jumps between adjacent frames (root-relative;
                   a warning — landings look the same to a position check)
  twist            a bone whose local rotation whips frame to frame; past
                   90°/sample it is a roll flip (the shortest-arc aim's
                   known failure mode) and critical
  foot slide       the planted foot travels while it carries the body
  prop contact     the implement stays on the hands, every frame
  loop             last frame returns near the first (clips are looped)
  anatomy          the movement pattern the spec declares actually happens
                   (pipeline/anatomy_qa.py: depth, hinge, arm plane, ...)

Writes <glb>.qa.json next to the GLB and prints a PASS/FAIL table. Exit 1
when any critical check fails, so CI can gate on it.
"""

import json
import math
import struct
import sys
from pathlib import Path

CRITICAL = {"bone_length", "prop_present", "prop_contact", "hinge",
            "twist_flip", "anatomy"}

# joint = (name, parent segment head, child that defines the segment's tail)
HINGES = {
    "elbow.L": ("upperarm02.L", "lowerarm01.L", "lowerarm02.L"),
    "elbow.R": ("upperarm02.R", "lowerarm01.R", "lowerarm02.R"),
    "knee.L": ("upperleg02.L", "lowerleg01.L", "lowerleg02.L"),
    "knee.R": ("upperleg02.R", "lowerleg01.R", "lowerleg02.R"),
}
# limb chain, proximal -> distal (heads of these nodes are the joints)
CHAINS = {
    "arm.L": ["upperarm01.L", "upperarm02.L", "lowerarm01.L", "lowerarm02.L",
              "wrist.L"],
    "arm.R": ["upperarm01.R", "upperarm02.R", "lowerarm01.R", "lowerarm02.R",
              "wrist.R"],
    "leg.L": ["upperleg01.L", "upperleg02.L", "lowerleg01.L", "lowerleg02.L",
              "foot.L"],
    "leg.R": ["upperleg01.R", "upperleg02.R", "lowerleg01.R", "lowerleg02.R",
              "foot.R"],
}
WATCH = ["root", "spine03", "spine01", "neck01", "head",
         "upperarm01.L", "lowerarm01.L", "wrist.L",
         "upperarm01.R", "lowerarm01.R", "wrist.R",
         "upperleg01.L", "lowerleg01.L", "foot.L",
         "upperleg01.R", "lowerleg01.R", "foot.R"]
HAND_TIP = {"L": "finger3-1.L", "R": "finger3-1.R"}   # middle finger base

THRESH = {
    "bone_length_pct": 2.0,     # % change of a segment's length over the clip
    "hinge_hyper_deg": 8.0,     # wrong-way bend past straight beyond this = hyperext
    "hinge_wrong_way": 0.3,     # ...and only when clearly in the hinge plane
    "hinge_min_deg": 25.0,      # tighter than this = limb folded through itself
    "spike_m": 0.06,            # travel beyond the neighbouring samples' trend (m)
    "twist_deg": 35.0,          # local rotation change between samples (deg)
    "twist_flip_deg": 90.0,     # beyond this it is a roll flip, not motion
    "foot_slide_m": 0.03,       # planted-foot travel per sample (m)
    "prop_contact_m": 0.06,     # hand-to-grip-point distance (m)
    "loop_m": 0.08,             # first/last pose mismatch, summed over WATCH
    "samples_per_sec": 15,
}


# ------------------------------------------------------------------ glTF

def load_glb(path):
    b = Path(path).read_bytes()
    assert b[:4] == b"glTF", f"{path}: not a GLB"
    n = struct.unpack_from("<I", b, 12)[0]
    gltf = json.loads(b[20:20 + n])
    off = 20 + n
    bins = []
    while off < len(b):
        ln, typ = struct.unpack_from("<II", b, off)
        bins.append(b[off + 8:off + 8 + ln])
        off += 8 + ln
    return gltf, bins[0]


FMT = {5126: ("f", 4), 5123: ("H", 2), 5125: ("I", 4), 5121: ("B", 1)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_accessor(gltf, blob, idx):
    acc = gltf["accessors"][idx]
    view = gltf["bufferViews"][acc["bufferView"]]
    ch, size = FMT[acc["componentType"]]
    n = NCOMP[acc["type"]]
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = view.get("byteStride", size * n)
    out = []
    for i in range(acc["count"]):
        o = start + i * stride
        out.append(struct.unpack_from("<" + ch * n, blob, o))
    if acc["componentType"] != 5126 and acc.get("normalized"):
        m = {5123: 65535.0, 5121: 255.0}[acc["componentType"]]
        out = [tuple(c / m for c in v) for v in out]
    return [v[0] if n == 1 else v for v in out]


# ------------------------------------------------------------------ maths

def q_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def q_norm(q):
    l = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / l for c in q)


def q_slerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b, d = tuple(-c for c in b), -d
    if d > 0.9995:
        return q_norm(tuple(x + (y - x) * t for x, y in zip(a, b)))
    th = math.acos(d)
    s = math.sin(th)
    wa, wb = math.sin((1 - t) * th) / s, math.sin(t * th) / s
    return tuple(wa * x + wb * y for x, y in zip(a, b))


def q_angle(a, b):
    """Angle (deg) between two rotations."""
    d = abs(sum(x * y for x, y in zip(q_norm(a), q_norm(b))))
    return math.degrees(2 * math.acos(min(1.0, d)))


def trs(t, q, s):
    x, y, z, w = q
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz, wx, wy, wz = x * y, x * z, y * z, w * x, w * y, w * z
    sx, sy, sz = s
    return [
        [(1 - 2 * (yy + zz)) * sx, 2 * (xy - wz) * sy, 2 * (xz + wy) * sz, t[0]],
        [2 * (xy + wz) * sx, (1 - 2 * (xx + zz)) * sy, 2 * (yz - wx) * sz, t[1]],
        [2 * (xz - wy) * sx, 2 * (yz + wx) * sy, (1 - 2 * (xx + yy)) * sz, t[2]],
        [0, 0, 0, 1]]


def m_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)]
            for i in range(4)]


def m_rot(m):
    """3x3 rotation part of a world matrix (rows)."""
    return [[m[r][c] for c in range(3)] for r in range(3)]


def m_pos(m):
    return (m[0][3], m[1][3], m[2][3])


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def angle_between(u, v):
    lu = math.sqrt(sum(c * c for c in u)) or 1e-9
    lv = math.sqrt(sum(c * c for c in v)) or 1e-9
    d = max(-1.0, min(1.0, sum(x * y for x, y in zip(u, v)) / (lu * lv)))
    return math.degrees(math.acos(d))


# ------------------------------------------------------------------ scene

class Clip:
    """Evaluate the GLB's node hierarchy at any time, for every animation."""

    def __init__(self, gltf, blob, animation=None):
        """animation: None = every clip in the file (an exported exercise
        holds one); a name or index picks one clip out of a pack."""
        self.gltf, self.blob = gltf, blob
        self.nodes = gltf["nodes"]
        self.parent = {}
        for i, n in enumerate(self.nodes):
            for c in n.get("children", []):
                self.parent[c] = i
        self.by_name = {n.get("name", ""): i for i, n in enumerate(self.nodes)}
        self.tracks = {}         # node -> path -> (times, values, interp)
        self.duration = 0.0
        anims = gltf.get("animations", [])
        if animation is not None:
            if isinstance(animation, int):
                anims = [anims[animation]]
            else:
                anims = [a for a in anims if a.get("name") == animation]
                if not anims:
                    raise KeyError(f"no animation named {animation!r}")
        for anim in anims:
            for ch in anim["channels"]:
                s = anim["samplers"][ch["sampler"]]
                times = read_accessor(gltf, blob, s["input"])
                vals = read_accessor(gltf, blob, s["output"])
                node, path = ch["target"]["node"], ch["target"]["path"]
                if path == "weights":
                    continue
                self.tracks.setdefault(node, {})[path] = (
                    times, vals, s.get("interpolation", "LINEAR"))
                self.duration = max(self.duration, times[-1])

    def _sample(self, times, vals, interp, t, is_quat):
        if t <= times[0]:
            return vals[0]
        if t >= times[-1]:
            return vals[-1]
        lo, hi = 0, len(times) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if times[mid] <= t:
                lo = mid
            else:
                hi = mid
        if interp == "STEP":
            return vals[lo]
        f = (t - times[lo]) / max(times[hi] - times[lo], 1e-9)
        a, b = vals[lo], vals[hi]
        if is_quat:
            return q_slerp(a, b, f)
        return tuple(x + (y - x) * f for x, y in zip(a, b))

    def local(self, i, t):
        n = self.nodes[i]
        tr = tuple(n.get("translation", (0, 0, 0)))
        ro = tuple(n.get("rotation", (0, 0, 0, 1)))
        sc = tuple(n.get("scale", (1, 1, 1)))
        for path, (times, vals, interp) in self.tracks.get(i, {}).items():
            v = self._sample(times, vals, interp, t, path == "rotation")
            if path == "translation":
                tr = v
            elif path == "rotation":
                ro = v
            elif path == "scale":
                sc = v
        return tr, ro, sc

    def world(self, t):
        """World matrices of every node at time t."""
        out = {}

        def rec(i):
            if i in out:
                return out[i]
            tr, ro, sc = self.local(i, t)
            m = trs(tr, ro, sc)
            p = self.parent.get(i)
            out[i] = m_mul(rec(p), m) if p is not None else m
            return out[i]
        for i in range(len(self.nodes)):
            rec(i)
        return out


# ------------------------------------------------------------------ checks

def sample_clip(glb_path, samples_per_sec=None):
    """Sample the GLB's clip: (gltf, names, times, frames, locals_) where
    frames[k] maps node name -> world position and locals_[k] maps node
    name -> local quaternion. Shared by the joint gate, the anatomy gate
    and the skeleton sheet so all three grade the same samples."""
    gltf, blob = load_glb(glb_path)
    clip = Clip(gltf, blob)
    names = clip.by_name
    step = 1.0 / (samples_per_sec or THRESH["samples_per_sec"])
    n_samples = max(2, int(round(clip.duration / step)) + 1)
    times = [i * clip.duration / (n_samples - 1) for i in range(n_samples)]

    frames = []                        # per sample: name -> world position
    locals_ = []                       # per sample: name -> local quaternion
    for t in times:
        w = clip.world(t)
        frames.append({nm: m_pos(w[i]) for nm, i in names.items()})
        locals_.append({nm: clip.local(i, t)[1] for nm, i in names.items()})
    return gltf, names, times, frames, locals_


def run_qa(glb_path, spec=None):
    gltf, names, times, frames, locals_ = sample_clip(glb_path)

    results = []

    def add(check, joint, ok, detail, value=None, t=None):
        results.append({"check": check, "joint": joint,
                        "status": "PASS" if ok else "FAIL",
                        "critical": check in CRITICAL,
                        "detail": detail, "value": value,
                        "t": None if t is None else round(t, 3)})

    missing = [b for chain in CHAINS.values() for b in chain if b not in names]
    if missing:
        add("skeleton", "rig", False, f"bones missing from GLB: {missing}")
        return results, times

    # 1. bone length constancy along every limb chain
    for chain_name, chain in CHAINS.items():
        for a, b in zip(chain, chain[1:]):
            lens = [dist(f[a], f[b]) for f in frames]
            lo, hi = min(lens), max(lens)
            pct = (hi - lo) / max(hi, 1e-6) * 100
            add("bone_length", f"{a}->{b}", pct <= THRESH["bone_length_pct"],
                f"length {lo:.3f}-{hi:.3f} m ({pct:.1f}% drift)", round(pct, 2))

    # 2. hinge angles: elbow / knee stay between folded and straight, and
    #    bend the way anatomy allows. The interior angle alone cannot tell a
    #    knee bent backwards from one bent forwards (both read 140°), so the
    #    bend direction is signed against the body's own lateral axis: knees
    #    fold the shin back. Elbows get the range test only: their hinge
    #    axis turns with the humerus (a sumo high pull's flared elbows read
    #    "backwards" against the shoulder line while being perfectly sound),
    #    so a wrong-way elbow needs the humeral roll, not a body axis.
    for joint, (prox, mid, distal) in HINGES.items():
        angs, wrong = [], []
        for f in frames:
            up = sub(f[mid], f[prox])         # down the limb into the joint
            lo = sub(f[distal], f[mid])       # on down past it
            angs.append(180.0 - angle_between(up, lo))     # 180 = straight
            if joint.startswith("knee"):
                lateral = sub(f["upperleg01.L"], f["upperleg01.R"])
                c = cross(up, lo)
                n = (norm(up) * norm(lo) * norm(lateral)) or 1e-9
                wrong.append(-dot(c, lateral) / n)         # +ve = wrong way
            else:
                wrong.append(0.0)
        worst_lo = min(angs)
        hyper = max(w for w in wrong)
        hyper_i = wrong.index(hyper)
        hyper_ok = not (hyper > THRESH["hinge_wrong_way"]
                        and angs[hyper_i] < 180 - THRESH["hinge_hyper_deg"])
        fold_ok = worst_lo >= THRESH["hinge_min_deg"]
        ok = hyper_ok and fold_ok
        fi = hyper_i if not hyper_ok else angs.index(worst_lo)
        add("hinge", joint, ok,
            f"angle range {worst_lo:.0f}-{max(angs):.0f} deg"
            + ("" if hyper_ok else
               f", bends the wrong way {180 - angs[hyper_i]:.0f} deg at t={times[hyper_i]:.2f}s")
            + ("" if fold_ok else f", folded through itself at t={times[fi]:.2f}s"),
            [round(worst_lo, 1), round(max(angs), 1)], times[fi])

    # 3. positional spikes: a joint whose travel in one sample departs from
    #    its neighbours' trend, measured relative to the root so a jump's
    #    whole-body launch does not count. What remains — a foot decelerating
    #    on landing, a hand catching a bar — is genuine, so this is a warning
    #    that points the inspector at the frame; the retarget's real pops are
    #    direction flips, which the twist check catches as critical.
    for nm in WATCH:
        if nm not in names:
            continue
        rel = [sub(f[nm], f["root"]) if nm != "root" else f[nm] for f in frames]
        jumps = [dist(a, b) for a, b in zip(rel, rel[1:])]
        worst, fi = 0.0, 0
        for k in range(1, len(jumps) - 1):
            expected = (jumps[k - 1] + jumps[k + 1]) / 2
            excess = jumps[k] - expected
            if excess > worst:
                worst, fi = excess, k
        add("spike", nm, worst <= THRESH["spike_m"],
            f"max unexplained travel/sample {worst * 100:.1f} cm"
            + ("" if worst <= THRESH["spike_m"] else f" at t={times[fi]:.2f}s"),
            round(worst, 3), times[fi])

    # 4. twist: local rotation whipping between samples (roll flips)
    for nm in WATCH:
        if nm not in names or nm == "root":
            continue
        deltas = [q_angle(a[nm], b[nm]) for a, b in zip(locals_, locals_[1:])]
        worst = max(deltas) if deltas else 0.0
        fi = deltas.index(worst) if deltas else 0
        flip = worst > THRESH["twist_flip_deg"]
        add("twist_flip" if flip else "twist", nm,
            worst <= THRESH["twist_deg"],
            f"max local rotation/sample {worst:.0f} deg"
            + ("" if worst <= THRESH["twist_deg"] else f" at t={times[fi]:.2f}s")
            + (" — roll flip" if flip else ""),
            round(worst, 1), times[fi])

    # 5. foot slide: a foot on the floor (lowest of the clip, +tolerance)
    #    must not travel horizontally between samples. Y is up in glTF.
    floor = min(min(f["foot.L"][1], f["foot.R"][1]) for f in frames)
    for foot in ("foot.L", "foot.R"):
        worst, worst_i = 0.0, 0
        for k, (a, b) in enumerate(zip(frames, frames[1:])):
            planted = a[foot][1] < floor + 0.04 and b[foot][1] < floor + 0.04
            if planted:
                travel = math.hypot(a[foot][0] - b[foot][0], a[foot][2] - b[foot][2])
                if travel > worst:
                    worst, worst_i = travel, k
        add("foot_slide", foot, worst <= THRESH["foot_slide_m"],
            f"max planted travel/sample {worst * 100:.1f} cm", round(worst, 3),
            times[worst_i])

    # 6. props: required by the spec, present in the GLB, on the hands
    prop = (spec or {}).get("prop")
    if prop:
        ptype = prop["type"]
        prop_nodes = [nm for nm in names
                      if nm.lower().startswith(ptype) and "mesh" in gltf["nodes"][names[nm]]]
        add("prop_present", ptype, bool(prop_nodes),
            f"{len(prop_nodes)} {ptype} object(s) in GLB: {prop_nodes}")
        for pn in prop_nodes:
            side = pn[-1] if pn.endswith((".L", ".R")) else None
            worst, fi = 0.0, 0
            for k, f in enumerate(frames):
                if side:
                    d = dist(f[pn], f["wrist." + side])
                else:
                    # bar / bell / two-hand hold: the grip point is between the hands
                    mid = tuple((x + y) / 2 for x, y in zip(f["wrist.L"], f["wrist.R"]))
                    d = dist(f[pn], mid)
                if d > worst:
                    worst, fi = d, k
            # wrist.tail (the true grip point) sits ~7 cm past the wrist head,
            # so allow that offset on top of the contact tolerance
            tol = THRESH["prop_contact_m"] + 0.08
            add("prop_contact", pn, worst <= tol,
                f"max hand-to-implement gap {worst * 100:.1f} cm"
                + ("" if worst <= tol else f" at t={times[fi]:.2f}s"),
                round(worst, 3), times[fi])
    elif spec is not None:
        add("prop_present", "none", True, "bodyweight exercise, no implement")

    # 7. loop closure: last sample near first, summed over the watched joints
    gap = sum(dist(frames[0][nm], frames[-1][nm]) for nm in WATCH if nm in names)
    add("loop", "clip", gap <= THRESH["loop_m"] * len(WATCH),
        f"first/last pose gap {gap:.2f} m summed over {len(WATCH)} joints",
        round(gap, 3))

    # 8. anatomy: does the figure perform THIS exercise's movement pattern?
    #    A deadlift that squats, a lateral raise that swings forward, a curl
    #    whose shoulder flies up all pass 1-7 — the joints are sound, the
    #    exercise is wrong. Rules live in anatomy_qa.py keyed by the spec's
    #    "movement": {"pattern": ...}; a spec without one is not graded.
    if spec and spec.get("movement"):
        import anatomy_qa
        for r in anatomy_qa.evaluate(frames, times, names, spec):
            add("anatomy", r["rule"], r["ok"], r["detail"], r.get("value"),
                r.get("t"))

    return results, times


def summarise(results):
    fails = [r for r in results if r["status"] == "FAIL"]
    crit = [r for r in fails if r["critical"]]
    return {"pass": not crit, "fails": len(fails), "critical_fails": len(crit)}


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    repo = Path(__file__).resolve().parent.parent
    glbs, spec_path = [], None
    for a in argv:
        if a.endswith(".json"):
            spec_path = a
        else:
            glbs.append(a)
    exit_code = 0
    for glb in glbs:
        gid = Path(glb).stem
        sp = Path(spec_path) if spec_path else repo / "exercises" / f"{gid}.json"
        spec = json.loads(sp.read_text()) if sp.exists() else None
        results, times = run_qa(glb, spec)
        summary = summarise(results)
        report = {"id": gid, "duration": round(times[-1], 3),
                  "samples": len(times), "summary": summary,
                  "thresholds": THRESH, "results": results}
        Path(glb + ".qa.json").write_text(json.dumps(report, indent=1))
        verdict = "PASS" if summary["pass"] else "FAIL"
        print(f"\n== {gid}: {verdict} ({summary['critical_fails']} critical, "
              f"{summary['fails']} total fails, {len(times)} samples over "
              f"{times[-1]:.2f}s)")
        for r in results:
            if r["status"] == "FAIL":
                flag = "CRIT" if r["critical"] else "warn"
                print(f"  {flag} {r['check']:13s} {r['joint']:26s} {r['detail']}")
        if not summary["pass"]:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
