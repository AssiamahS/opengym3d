"""Skeleton contact sheet from an exercise GLB — stdlib only, no Blender.

    python3 pipeline/sheet_glb.py site/assets/deadlift.glb          # -> deadlift.sheet.png
    python3 pipeline/sheet_glb.py site/assets/*.glb --frames 12

Two rows, front view above side view, one column per sampled frame across
the whole rep. The Blender strip shows what the camera saw from ONE side;
this shows the joints the QA gate measured from two orthogonal sides, so a
review can read the rear foot, the arm plane or a bar's path without a
render. Colour: left limbs orange, right limbs cyan, spine white, implement
magenta, floor line grey. Frame failing a critical QA check (from
<glb>.qa.json when it exists) gets a red border.
"""

import json
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_glb  # noqa: E402

CELL = 150            # px per tile (square)
PAD = 2
BG = (11, 13, 16)
COL = {"L": (255, 150, 40), "R": (60, 200, 255), "spine": (235, 235, 235),
       "prop": (255, 80, 220), "floor": (70, 74, 80), "fail": (230, 40, 40)}

# bone segments drawn, as (from node, to node)
SPINE = [("root", "spine03"), ("spine03", "spine01"), ("spine01", "neck01"),
         ("neck01", "head")]
LIMB = [("upperarm01", "upperarm02"), ("upperarm02", "lowerarm01"),
        ("lowerarm01", "lowerarm02"), ("lowerarm02", "wrist"),
        ("upperleg01", "upperleg02"), ("upperleg02", "lowerleg01"),
        ("lowerleg01", "lowerleg02"), ("lowerleg02", "foot")]
SHOULDER = [("spine01", "upperarm01.L"), ("spine01", "upperarm01.R"),
            ("root", "upperleg01.L"), ("root", "upperleg01.R")]


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def dot(self, x, y, c, r=1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                xx, yy = x + dx, y + dy
                if 0 <= xx < self.w and 0 <= yy < self.h:
                    i = (yy * self.w + xx) * 3
                    self.px[i:i + 3] = bytes(c)

    def line(self, x0, y0, x1, y1, c, r=1):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.dot(x0, y0, c, r)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def rect(self, x, y, w, h, c):
        self.line(x, y, x + w - 1, y, c, 0)
        self.line(x, y + h - 1, x + w - 1, y + h - 1, c, 0)
        self.line(x, y, x, y + h - 1, c, 0)
        self.line(x + w - 1, y, x + w - 1, y + h - 1, c, 0)

    def png(self):
        raw = b"".join(b"\x00" + bytes(self.px[y * self.w * 3:(y + 1) * self.w * 3])
                       for y in range(self.h))

        def chunk(tag, data):
            body = tag + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)
        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6))
                + chunk(b"IEND", b""))


def pick_frames(n_samples, n):
    return sorted({round(i * (n_samples - 1) / (n - 1)) for i in range(n)})


def sheet(glb_path, n_frames=12, out=None):
    gltf, names, times, frames, _ = qa_glb.sample_clip(glb_path, samples_per_sec=30)
    prop_nodes = [nm for nm in names if "mesh" in gltf["nodes"][names[nm]]
                  and nm.lower().startswith(("barbell", "dumbbell", "kettlebell"))]
    fails = set()
    qa_path = Path(str(glb_path) + ".qa.json")
    if qa_path.exists():
        for r in json.loads(qa_path.read_text())["results"]:
            if r["status"] == "FAIL" and r["critical"] and r.get("t") is not None:
                fails.add(r["t"])
    out = Path(out) if out else Path(str(glb_path).replace(".glb", ".sheet.png"))
    return draw(frames, times, out, n_frames=n_frames, prop_nodes=prop_nodes, fails=fails)


def draw(frames, times, out, n_frames=12, prop_nodes=(), fails=()):
    """Sheet from joint positions alone (glTF Y-up metres, MakeHuman names):
    a GLB's sampled skeleton or a normalized motion put through the
    canonical skeleton's FK (pipeline/motion.py) draw the same way."""
    idx = pick_frames(len(frames), n_frames)
    # one scale for the whole sheet so height reads across frames
    pts = [p for f in frames for p in f.values()]
    ys = [p[1] for p in pts]
    floor, top = min(ys), max(ys)
    height = max(top - floor, 0.5)
    scale = (CELL - 16) / height
    fails = set(fails)

    cv = Canvas(len(idx) * (CELL + PAD) + PAD, 2 * (CELL + PAD) + PAD, BG)
    for col, k in enumerate(idx):
        f = frames[k]
        cx0 = PAD + col * (CELL + PAD)
        # centre each view on the pelvis so the figure stays in the tile
        root = f["root"]
        for row, axes in enumerate(((0, 1), (2, 1))):          # front: x,y  side: z,y
            oy = PAD + row * (CELL + PAD)
            ax, ay = axes

            def P(p):
                x = cx0 + CELL // 2 + int((p[ax] - root[ax]) * scale)
                y = oy + CELL - 8 - int((p[ay] - floor) * scale)
                return x, y
            fy = oy + CELL - 8
            cv.line(cx0, fy, cx0 + CELL - 1, fy, COL["floor"], 0)
            for a, b in SPINE + SHOULDER:
                if a in f and b in f:
                    cv.line(*P(f[a]), *P(f[b]), COL["spine"])
            for side in ("L", "R"):
                for a, b in LIMB:
                    a, b = f"{a}.{side}", f"{b}.{side}"
                    if a in f and b in f:
                        cv.line(*P(f[a]), *P(f[b]), COL[side])
                for j in ("wrist", "foot", "lowerarm01", "lowerleg01"):
                    nm = f"{j}.{side}"
                    if nm in f:
                        cv.dot(*P(f[nm]), COL[side], 2)
            if "head" in f:
                cv.dot(*P(f["head"]), COL["spine"], 3)
            for pn in prop_nodes:
                cv.dot(*P(f[pn]), COL["prop"], 3)
            if any(abs(times[k] - t) < 0.5 / 15 for t in fails):
                cv.rect(cx0, oy, CELL, CELL, COL["fail"])
    out = Path(out)
    out.write_bytes(cv.png())
    return out, idx


def main(argv):
    n = 12
    if "--frames" in argv:
        i = argv.index("--frames")
        n = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    if not argv:
        print(__doc__)
        return 2
    for g in argv:
        out, idx = sheet(g, n)
        print(f"{out}  ({len(idx)} frames, front + side)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
