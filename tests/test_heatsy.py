"""Focused independent decoder and fail-closed preservation regressions."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'studio'))
import numpy as np
from heatsy_gltf import fixture, load, accessor
from heatsy_patch import patched_source
from heatsy_validate import asset, compare, SOURCE, OUT


class DecoderTests(unittest.TestCase):
    def test_signed_and_unsigned_normalization_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.glb'
            fixture(path, ('_PART_ID', '_FIBER', '_TENDON'))
            g, b = load(path)
            attrs = g['meshes'][0]['primitives'][0]['attributes']
            np.testing.assert_array_equal(accessor(g, b, attrs['_PART_ID']).ravel(), [1, 2, 238])
            np.testing.assert_allclose(accessor(g, b, attrs['_TENDON']).ravel(), [0, 128/255, 1])
            np.testing.assert_allclose(accessor(g, b, attrs['_FIBER'])[0], [-1, 64/127, 1])
            self.assertEqual(accessor(g, b, attrs['_FIBER'], decoded=False)[0, 0], -128)

    def test_patch_rejects_unknown_source(self):
        with self.assertRaisesRegex(RuntimeError, 'context mismatch'):
            patched_source('unexpected importer revision')


@unittest.skipUnless(SOURCE.exists() and (OUT / 'roundtrip.glb').exists(), 'Run studio/heatsy_build.py for asset integration tests')
class PreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = asset(SOURCE)
        cls.target = asset(OUT / 'roundtrip.glb')

    def test_roundtrip_reordering_and_splitting(self):
        target = copy.deepcopy(self.target)
        rng = np.random.default_rng(712)
        permutation = rng.permutation(len(target['positions']))
        inverse = np.argsort(permutation)
        for key in ('positions', 'weights', 'hp'):
            target[key] = target[key][permutation]
        for key in target['attrs']:
            target['attrs'][key] = target['attrs'][key][permutation]
        target['triangles'] = inverse[target['triangles']]
        # Duplicate a referenced vertex and redirect one corner to the copy.
        vertex = target['triangles'][0, 0]
        count = len(target['positions'])
        for key in ('positions', 'weights', 'hp'):
            target[key] = np.vstack([target[key], target[key][vertex]])
        for key in target['attrs']:
            target['attrs'][key] = np.vstack([target['attrs'][key], target['attrs'][key][vertex]])
        target['triangles'][0, 0] = count
        self.assertEqual(compare(self.source, target)['status'], 'PASS')

    def test_attribute_corruption_fails(self):
        for name in ('_PART_ID', '_FIBER', '_TENDON'):
            with self.subTest(attribute=name):
                target = copy.deepcopy(self.target)
                target['attrs'][name][0, 0] += 1
                with self.assertRaisesRegex(AssertionError, 'No preserved source vertex'):
                    compare(self.source, target)

    def test_left_right_swap_fails(self):
        target = copy.deepcopy(self.target)
        ids = target['attrs']['_PART_ID'][:, 0]
        mask = ids > 0
        ids[mask] += np.where(ids[mask] % 2 == 1, 1, -1)
        with self.assertRaisesRegex(AssertionError, 'No preserved source vertex'):
            compare(self.source, target)

    def test_missing_attribute_fails(self):
        target = copy.deepcopy(self.target)
        del target['attrs']['_FIBER']
        with self.assertRaisesRegex(AssertionError, 'Attribute names'):
            compare(self.source, target)

    def test_weights_geometry_and_bind_corruption_fail(self):
        for key in ('weights', 'positions'):
            with self.subTest(field=key):
                target = copy.deepcopy(self.target)
                target[key][0, 0] += .1
                with self.assertRaisesRegex(AssertionError, 'No preserved source vertex'):
                    compare(self.source, target)
        target = copy.deepcopy(self.target)
        target['operators'][:, 0, 3] += .1
        with self.assertRaisesRegex(AssertionError, 'bind contribution'):
            compare(self.source, target)

    def test_triangle_winding_change_fails(self):
        target = copy.deepcopy(self.target)
        target['triangles'][0] = target['triangles'][0][::-1]
        with self.assertRaisesRegex(AssertionError, 'triangle/corner'):
            compare(self.source, target)


if __name__ == '__main__':
    unittest.main()
