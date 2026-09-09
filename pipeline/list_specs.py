"""Print the exercise specs CI should render: everything not marked draft.

    python3 pipeline/list_specs.py exercises            # active specs
    python3 pipeline/list_specs.py exercises --drafts   # the hidden ones

A spec is a draft when it says so ("status": "draft"). Hand-keyed poses
went draft on 2026-09-09: they stay in the repo as metadata (muscles, form
steps) but are not rendered or listed until they get real motion.
"""
import json
import sys
from pathlib import Path


def active(src):
    for path in sorted(Path(src).glob("*.json")):
        spec = json.loads(path.read_text())
        yield path, spec, spec.get("status", "active") == "draft"


if __name__ == "__main__":
    want_drafts = "--drafts" in sys.argv[2:]
    for path, spec, draft in active(sys.argv[1]):
        if draft == want_drafts:
            print(path)
