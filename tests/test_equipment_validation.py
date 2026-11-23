import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'studio'))
from goblet_validate import cylinder_distance
from equipment_verify import validate_samples
import equipment_verify
from unittest.mock import patch
import copy
import struct
from goblet_validate import validate_grip_preservation,load,ROOT

class CylinderContactTests(unittest.TestCase):
    def test_signed_distance_distinguishes_contact_gap_and_penetration(self):
        points=np.array([[0,.017,0],[0,.020,0],[0,.010,0],[.075,0,0],[.080,0,0]])
        np.testing.assert_allclose(cylinder_distance(points,0,.075,.017),[0,.003,-.007,0,.005],atol=1e-12)

    def test_head_center_and_corner_do_not_use_shaft_distance(self):
        points=np.array([[.098,0,0],[.135,.065,0]])
        distance=cylinder_distance(points,.098,.0275,.055)
        self.assertAlmostEqual(distance[0],-.0275)
        self.assertAlmostEqual(distance[1],np.hypot(.0095,.01))

class ExportedCoverageTests(unittest.TestCase):
    def fixture(self):
        names=('Dumbbell','wristL','wristR','footL','footR','finger2-1L','finger2-1R')
        return [dict(phase=p,positions={n:[0,0,0] for n in names}) for p in (0,.25,.5,.75,1,.123,.337)]

    def test_all_required_poses_and_equipment_are_required(self):
        records=self.fixture();validate_samples(records)
        with self.assertRaises(AssertionError):validate_samples(records[:1])
        del records[0]['positions']['Dumbbell']
        with self.assertRaises(AssertionError):validate_samples(records)

    def test_nonfinite_equipment_coordinate_cannot_disappear_in_maximum(self):
        records=self.fixture();records[0]['positions']['Dumbbell'][0]=float('nan')
        with self.assertRaises(AssertionError):validate_samples(records)


class CatalogEvidenceTests(unittest.TestCase):
    def test_missing_failed_or_stale_browser_evidence_cannot_pass(self):
        assets=('catalog.json','dumbbell.glb','kettlebell.glb','barbell.glb','goblet.glb')
        files=tuple('studio/equipment/'+n for n in ('index.html','style.css','viewer.js','preview.html'))+('studio/equipment_capture.mjs','studio/equipment_catalog_check.mjs')
        report=dict(status='PASS',catalog_sha256='current',glb_sha256='current',
                    asset_sha256={n:'current' for n in assets},file_sha256={n:'current' for n in files})
        with patch.object(equipment_verify,'sha',return_value='current'):
            equipment_verify.validate_catalog_browser(report)
            failed=copy.deepcopy(report);failed['status']='FAIL'
            with self.assertRaises(AssertionError):equipment_verify.validate_catalog_browser(failed)
            stale=copy.deepcopy(report);stale['file_sha256']['studio/equipment/viewer.js']='old'
            with self.assertRaises(AssertionError):equipment_verify.validate_catalog_browser(stale)
            missing=copy.deepcopy(report);del missing['asset_sha256']['barbell.glb']
            with self.assertRaises(AssertionError):equipment_verify.validate_catalog_browser(missing)


class GripPreservationTests(unittest.TestCase):
    def test_mesh_or_nonfinger_motion_changes_cannot_hide_a_grip_fix(self):
        path=ROOT/'outputs/equipment-use/goblet.glb'
        if not path.exists():self.skipTest('Checkpoint GLB is required')
        g,b=load(path);validate_grip_preservation(g,b)
        body_node=next(n for n in g['nodes'] if 'skin' in n)
        primitive=g['meshes'][body_node['mesh']]['primitives'][0]
        track=next(c for c in g['animations'][0]['channels'] if not g['nodes'][c['target']['node']]['name'].startswith('finger'))
        motion=g['animations'][0]['samplers'][track['sampler']]['output']
        for index in (primitive['attributes']['POSITION'],motion):
            modified=bytearray(b);a=g['accessors'][index];self.assertEqual(a['componentType'],5126)
            offset=g['bufferViews'][a['bufferView']].get('byteOffset',0)+a.get('byteOffset',0)
            value=struct.unpack_from('<f',modified,offset)[0];struct.pack_into('<f',modified,offset,value+.001)
            with self.assertRaises(AssertionError):validate_grip_preservation(g,bytes(modified))

if __name__=='__main__':unittest.main()
