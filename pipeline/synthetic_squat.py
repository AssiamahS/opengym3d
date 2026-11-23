"""Deterministic engineering fixture, NOT captured or validated exercise technique.

Original analytic motion, licensed MIT under the repository LICENSE.
No footage, Mixamo motion or public-video demonstration is used.
"""
import math
from pathlib import Path
import motion


def generate():
    frames = []
    for i in range(91):  # 3 seconds + matching endpoint, 30 Hz
        s = (1 - math.cos(2 * math.pi * i / 90)) / 2
        hy, hz = .20 * s, .95 - .40 * s
        dy, dz = -hy, .09 - hz
        distance = math.hypot(dy, dz)
        offset = math.sqrt(max(0, .43 ** 2 - (distance / 2) ** 2))
        ky = hy / 2 + dz / distance * offset
        kz = (hz + .09) / 2 - dy / distance * offset
        lean = math.radians(25 * s)
        dirs = {b: motion._n(motion._sub(t, h))
                for b, (h, t) in motion.rest_bones().items() if b != "pelvis"}
        for b in ("spine", "chest", "neck", "head"):
            dirs[b] = (0, -math.sin(lean), math.cos(lean))
        for side, sign in (("L", 1), ("R", -1)):
            dirs["thigh." + side] = motion._n((0, ky - hy, kz - hz))
            dirs["shin." + side] = motion._n((0, -ky, .09 - kz))
            for b in ("upper_arm", "forearm", "hand"):
                dirs[b + "." + side] = motion._n((sign * .12, -1, -.12))
        frames.append(motion.make_frame(hz, (0, hy, hz - .95),
                      *motion.REST_BASIS, dirs, {}))
    return motion.new(frames, 30,
        source={"kind": "synthetic", "generator": "pipeline/synthetic_squat.py",
                "description": "Analytic two-link legs, cosine hip path; no capture input"},
        license="MIT", technical_preview=True,
        limitations=["No movement/anatomy approval", "Canonical proportions approximate MPFB"])


if __name__ == "__main__":
    dest = Path(__file__).resolve().parent.parent / "motions/synthetic/squat.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    motion.save(generate(), dest)
    print(dest)
