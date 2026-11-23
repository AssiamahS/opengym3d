"""All equipment continuation writes stay outside preserved baseline directories."""
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def output_path(value=None):
    path=(ROOT/(value if value is not None else os.environ.get('FMS_EQUIPMENT_OUTPUT','outputs/equipment-library'))).resolve()
    allowed=(ROOT/'outputs/equipment-library').resolve()
    if not path.is_relative_to(allowed):
        raise ValueError('Equipment continuation output must stay under outputs/equipment-library; baseline outputs are read-only')
    return path


OUT=output_path()
