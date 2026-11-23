import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'studio'))
from equipment_visual_check import compare


class MatchedViewRegression(unittest.TestCase):
    def test_local_grip_change_is_distinguished_from_camera_or_body_change(self):
        before=np.zeros((320,320,3),dtype=np.uint8);after=before.copy()
        after[130:150,110:130]=200
        self.assertEqual(compare(before,after)['outside_grip_pixels'],0)
        after[10:40,10:40]=200
        with self.assertRaises(AssertionError):compare(before,after)

    def test_stale_or_mismatched_screenshot_cannot_show_improvement(self):
        before=np.zeros((320,320,3),dtype=np.uint8)
        with self.assertRaises(AssertionError):compare(before,before.copy())
        with self.assertRaises(AssertionError):compare(before,np.zeros((640,640,3)))


if __name__=='__main__':unittest.main()
