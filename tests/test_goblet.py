"""Two-link reach regression for the isolated equipment-use adapter."""
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'studio'))
from goblet_build import elbow_position,palm_rotation


class GobletReachTests(unittest.TestCase):
    def test_reachable_hands_preserve_both_segment_lengths(self):
        shoulder=np.array([.2,0,1.4]);wrist=np.array([.04,-.3,1.25])
        elbow=elbow_position(shoulder,wrist,.26,.27,[.3,-.1,.8])
        self.assertAlmostEqual(np.linalg.norm(elbow-shoulder),.26,places=12)
        self.assertAlmostEqual(np.linalg.norm(wrist-elbow),.27,places=12)
        self.assertLess(elbow[2],wrist[2])

    def test_unreachable_grip_is_rejected_instead_of_stretching_arm(self):
        with self.assertRaises(ValueError):elbow_position([0,0,0],[1,0,0],.2,.2,[0,0,-1])

    def test_symmetric_targets_produce_symmetric_elbows(self):
        a=elbow_position([.2,0,1.4],[.04,-.3,1.25],.26,.27,[.3,-.1,.8])
        b=elbow_position([-.2,0,1.4],[-.04,-.3,1.25],.26,.27,[-.3,-.1,.8])
        np.testing.assert_allclose(a*np.array([-1,1,1]),b,atol=1e-12)

    def test_palm_roll_uses_knuckle_plane_not_world_forward(self):
        # The actual MPFB palm is tilted in rest; assuming world -Y gave flat,
        # interleaved hands even though the wrist longitudinal aim was correct.
        for side in (1,-1):
            longitudinal=np.array([side*.048,-.086,-.054]);longitudinal/=np.linalg.norm(longitudinal)
            span=np.array([side*.01,.02,-.07])
            normal=np.cross(longitudinal,span)*side;normal/=np.linalg.norm(normal)
            rotation=palm_rotation(longitudinal,span,side)
            np.testing.assert_allclose(rotation@longitudinal,[0,-1,0],atol=1e-12)
            np.testing.assert_allclose(rotation@normal,[-side,0,0],atol=1e-12)
            np.testing.assert_allclose(rotation.T@rotation,np.eye(3),atol=1e-12)


if __name__=='__main__':unittest.main()
