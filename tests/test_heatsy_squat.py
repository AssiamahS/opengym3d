"""Target-specific animation regressions, without rebuilding either baseline."""
import copy
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'studio'))
from heatsy_squat import from_matrix, aim, append_animation, BASE, MOTION, motion, sample, timing
from heatsy_squat_validate import channels_gate, hierarchy_gate
from heatsy_gltf import load


class RotationTests(unittest.TestCase):
    def test_matrix_quaternion_roundtrip(self):
        import qa_glb
        for q in ([0,0,0,1],[1,0,0,0],[.3,.4,.5,.6]):
            q=np.array(q)/np.linalg.norm(q)
            matrix=np.array(qa_glb.trs([0,0,0],q,[1,1,1]))
            self.assertAlmostEqual(abs(np.dot(from_matrix(matrix),q)),1,places=12)

    def test_aim_handles_antipode(self):
        import qa_glb
        for b in ([0,-1,0],[0,0,1],[.3,.4,.5]):
            q=aim([0,1,0],b);r=np.array(qa_glb.trs([0,0,0],q,[1,1,1]))[:3,:3]
            np.testing.assert_allclose(r@[0,1,0],np.array(b)/np.linalg.norm(b),atol=1e-12)


@unittest.skipUnless((BASE/'roundtrip.glb').exists(),'Static Heatsy baseline required')
class SquatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.static,cls.blob=load(BASE/'roundtrip.glb')
        cls.g,cls.b,cls.report=append_animation(cls.static,cls.blob,motion.load(MOTION))

    def test_appending_preserves_mesh_and_anatomy_bytes(self):
        self.assertEqual(bytes(self.b[:len(self.blob)]),self.blob)
        for key in ('nodes','skins','meshes','materials'):
            self.assertEqual(self.static[key],self.g[key])
        channels_gate(self.g,bytes(self.b))

    def test_parent_translation_is_rejected(self):
        g=copy.deepcopy(self.g)
        g['animations'][0]['channels'][0]['target']={'node':57,'path':'translation'}
        with self.assertRaises(AssertionError):hierarchy_gate(g)

    def test_source_timing_is_used_without_fixed_duration(self):
        source=motion.load(MOTION)
        source['fps']=24
        g,b,report=append_animation(self.static,self.blob,source)
        self.assertEqual(report['duration'],3.75)
        channels_gate(g,bytes(b),source)
        np.testing.assert_allclose(sample(g,bytes(b),1.875,indices=[1000])[0],
                                   sample(self.g,bytes(self.b),1.5,indices=[1000])[0],atol=1e-6)

    def test_scale_track_is_rejected(self):
        g=copy.deepcopy(self.g);g['animations'][0]['channels'][0]['target']['path']='scale'
        with self.assertRaises(AssertionError):hierarchy_gate(g)

    def test_motion_has_closed_loop_and_stationary_feet(self):
        a,w0=sample(self.g,bytes(self.b),0,indices=[0,1000,50000])
        b,w1=sample(self.g,bytes(self.b),3,indices=[0,1000,50000])
        np.testing.assert_allclose(a,b,atol=1e-7)
        _,bottom=sample(self.g,bytes(self.b),1.5,indices=[0])
        names={n['name']:i for i,n in enumerate(self.g['nodes'])}
        for side in ('L','R'):
            i=names['foot.'+side]
            self.assertLess(np.linalg.norm(bottom[i][:3,3]-w0[i][:3,3]),.002)
        self.assertLess(bottom[names['pelvis']][1,3],w0[names['pelvis']][1,3]-.3)


if __name__=='__main__':unittest.main()
