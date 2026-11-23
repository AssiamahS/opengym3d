import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'studio'))
from goblet_validate import cylinder_distance
from equipment_verify import validate_samples
import copy

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

if __name__=='__main__':unittest.main()
