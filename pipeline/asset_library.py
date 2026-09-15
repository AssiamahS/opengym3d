"""The asset library: every human, motion and implement the pipeline may
use, with its source and licence, in one machine-readable manifest.

    python3 pipeline/asset_library.py                 # print the library
    python3 pipeline/asset_library.py motion squat    # search motions
    python3 pipeline/asset_library.py check exercises # every spec's motion resolves
    python3 pipeline/asset_library.py resolve cc0/mesh2motion/human-addon-animations.glb#Pushup

Or from Python (stdlib only, no Blender):

    from asset_library import Library
    lib = Library()
    lib.find_motion("push")                    # -> [Asset, ...] by name/tags
    lib.find_human(rig="makehuman-default")    # -> [Asset]
    lib.find_equipment("dumbbell")
    lib.motion_for_spec(spec)                  # the Asset a spec's "mocap" uses
    lib.redistributable(asset)                 # may the rendered GLB be sold/shipped?

Why this exists (2026-09-15): the pipeline had been treating "no clip for
lunges" as "buy a pack". The library makes the free sources first-class —
CC0 packs vendored under motions/cc0/, phone captures under motions/video/ —
and turns licensing into data the manifest can act on: a Mixamo-driven
exercise stays out of the sold pack automatically, a CC0- or own-capture one
goes in. Adding an asset = adding an entry here; a spec whose motion is not
in the library fails tests/test_specs.py.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIBRARY_PATH = REPO / "assets" / "ASSET_LIBRARY.json"

# licences under which a rendered GLB may be redistributed (sold, bundled)
REDISTRIBUTABLE = {"CC0-1.0", "CC-BY-4.0", "MIT", "own"}


class Asset(dict):
    @property
    def id(self):
        return self["id"]

    @property
    def type(self):
        return self["type"]

    @property
    def license(self):
        return self["license"]

    def __repr__(self):
        return f"<{self['type']} {self['id']} [{self['license']}]>"


class Library:
    def __init__(self, path=LIBRARY_PATH):
        self.path = Path(path)
        doc = json.loads(self.path.read_text())
        self.meta = {k: v for k, v in doc.items() if k != "assets"}
        self.assets = [Asset(a) for a in doc["assets"]]
        ids = [a.id for a in self.assets]
        dupes = {i for i in ids if ids.count(i) > 1}
        assert not dupes, f"duplicate asset ids: {sorted(dupes)}"

    # -- queries ----------------------------------------------------------
    def of_type(self, kind):
        return [a for a in self.assets if a.type == kind]

    def _search(self, kind, query=None, **filters):
        out = []
        q = (query or "").lower().replace("-", "_").replace(" ", "_")
        for a in self.of_type(kind):
            if any(a.get(k) != v for k, v in filters.items()):
                continue
            hay = " ".join([a.id, a.get("name", ""), a.get("clip", "") or "",
                            " ".join(a.get("tags", []))]).lower()
            hay = hay.replace("-", "_").replace(" ", "_")
            if q and q not in hay:
                continue
            out.append(a)
        return sorted(out, key=lambda a: (-a.get("quality", 0), a.id))

    def find_human(self, query=None, **filters):
        return self._search("human", query, **filters)

    def find_motion(self, query=None, **filters):
        return self._search("motion", query, **filters)

    def find_equipment(self, query=None, **filters):
        return self._search("equipment", query, **filters)

    def by_id(self, asset_id):
        for a in self.assets:
            if a.id == asset_id:
                return a
        raise KeyError(asset_id)

    # -- specs ------------------------------------------------------------
    def motion_for_ref(self, ref):
        """The motion asset a spec's "mocap" string names. A pack entry
        ("file": ..., "clip": ...) matches "file#clip"; a single-file entry
        matches its file."""
        for a in self.of_type("motion"):
            if a.get("clip"):
                if ref == f"{a['file']}#{a['clip']}":
                    return a
            elif ref == a.get("file"):
                return a
        return None

    def motion_for_spec(self, spec):
        ref = spec.get("mocap")
        return self.motion_for_ref(ref) if ref else None

    def redistributable(self, asset):
        return asset is not None and asset.get("license") in REDISTRIBUTABLE \
            and asset.get("commercial_use", False)

    def check_specs(self, exercises_dir):
        """(spec id, mocap ref, asset or None) for every non-draft spec —
        the test suite fails on any None."""
        rows = []
        for path in sorted(Path(exercises_dir).glob("*.json")):
            spec = json.loads(path.read_text())
            ref = spec.get("mocap")
            if not ref:
                continue
            rows.append((spec["id"], ref, self.motion_for_ref(ref),
                         spec.get("status", "active")))
        return rows


def main(argv):
    lib = Library()
    if not argv:
        print(f"{lib.path.name}: {len(lib.assets)} assets")
        for kind in ("human", "motion", "equipment", "reference"):
            items = lib.of_type(kind)
            if items:
                print(f"\n{kind.upper()} ({len(items)})")
                for a in items:
                    flag = "pack" if lib.redistributable(a) else "app-only"
                    print(f"  {a.id:44s} {a['license']:10s} {flag:8s} {a.get('name', '')}")
        return 0
    cmd, *rest = argv
    if cmd in ("human", "motion", "equipment"):
        finder = getattr(lib, f"find_{cmd}")
        for a in finder(rest[0] if rest else None):
            print(f"{a.id:44s} {a['license']:10s} {a.get('file', '')}"
                  f"{'#' + a['clip'] if a.get('clip') else ''}")
        return 0
    if cmd == "resolve":
        a = lib.motion_for_ref(rest[0])
        print(json.dumps(a, indent=2) if a else f"NOT IN LIBRARY: {rest[0]}")
        return 0 if a else 1
    if cmd == "check":
        bad = 0
        for sid, ref, asset, status in lib.check_specs(rest[0] if rest else REPO / "exercises"):
            if asset is None:
                bad += 1
                print(f"MISSING  {sid:28s} {ref}")
            else:
                flag = "pack" if lib.redistributable(asset) else "app-only"
                print(f"{status:7s}  {sid:28s} {asset['license']:10s} {flag:8s} {ref}")
        print(f"{bad} spec(s) reference motion that is not in the library")
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
