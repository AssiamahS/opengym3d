import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'studio'))
from equipment_catalog import definitions,validate_catalog
from equipment_catalog_validate import contact_distance
from equipment_paths import output_path,ROOT


class CatalogContracts(unittest.TestCase):
    def fixture(self):
        return dict(schema='equipment-catalog/1',items=definitions())

    def test_catalog_requires_three_distinct_inspection_assets(self):
        catalog=self.fixture();validate_catalog(catalog)
        catalog['items'][2]=copy.deepcopy(catalog['items'][0])
        with self.assertRaises(AssertionError):validate_catalog(catalog)

    def test_substitution_cannot_create_an_approved_variation(self):
        catalog=self.fixture();catalog['items'][1]['compatibleVariations']=['goblet-squat-experimental']
        with self.assertRaises(AssertionError):validate_catalog(catalog)

    def test_invalid_dimensions_and_contact_coordinates_fail_closed(self):
        for bad in (-.01,float('nan'),float('inf')):
            catalog=self.fixture();catalog['items'][0]['dimensions']['length']=bad
            with self.assertRaises(AssertionError):validate_catalog(catalog)
        catalog=self.fixture();catalog['items'][1]['contactPoints'][0]['position']=[0,0]
        with self.assertRaises(AssertionError):validate_catalog(catalog)

    def test_nominal_targets_lie_on_actual_generator_handle_surfaces(self):
        for item in definitions():
            points=[c['position'] for c in item['contactPoints']]
            self.assertLess(max(contact_distance(item['id'],points)),1e-12)
        self.assertGreater(contact_distance('kettlebell',[[0,.10,0]])[0],.01)

    def test_asset_paths_cannot_escape_bundle(self):
        catalog=self.fixture();catalog['items'][0]['geometry']='../other.glb'
        with self.assertRaises(AssertionError):validate_catalog(catalog)

    def test_output_override_cannot_write_old_proofs(self):
        for path in ('outputs/equipment-use','outputs/heatsy-repair','outputs/bodyweight','outputs/equipment-library/../equipment-use',str(ROOT/'motions/synthetic')):
            with self.assertRaises(ValueError):output_path(path)
        self.assertEqual(output_path('outputs/equipment-library/grip-experiments/candidate'),ROOT/'outputs/equipment-library/grip-experiments/candidate')


if __name__=='__main__':unittest.main()
