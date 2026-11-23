"""Regressions for weight-gradient tearing and experimental cross-limb leakage."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'studio'))
from heatsy_repair import Rig, OUT, BROKEN, coherent_weights, compact_weights
from heatsy_gltf import load,accessor
from heatsy_squat import sample


class SupportTests(unittest.TestCase):
    def test_top_four_rank_swap_does_not_create_a_weight_step(self):
        weights=np.array([[.6,.2,.1,.05-1e-6,.05+1e-6],[.6,.2,.1,.05+1e-6,.05-1e-6]])
        abrupt=compact_weights(weights)
        self.assertGreater(abs(abrupt[0]-abrupt[1]).max(),.05)
        smooth=compact_weights(weights,continuous=True)
        self.assertLess(abs(smooth[0]-smooth[1]).max(),1e-5)
        self.assertTrue(np.all(np.sum(smooth>0,axis=1)<=4))
        np.testing.assert_allclose(smooth.sum(1),1,atol=1e-12)

    def test_nearby_hand_and_thigh_do_not_gain_each_others_bones(self):
        # Rest arms are close to thighs. Pure Euclidean smoothing leaked thigh
        # weights into hand muscles, creating new tears when the arm was lifted.
        x=np.array([[.2,.8,0],[.21,.8,0],[.2,.81,0],
                    [.2,.8,.001],[.21,.8,.001],[.2,.81,.001]])
        r=SimpleNamespace(x=x,rest=x,tri=np.array([[0,1,2],[3,4,5]]),area=np.array([.00005,.00005]),
            w=np.array([[1.,0]]*3+[[0.,1]]*3),ids=np.array([235]*3+[119]*3),
            edges=np.array([[0,1],[1,2],[0,2],[3,4],[4,5],[3,5]]),names=['hand.L','thigh.L'])
        unsafe=coherent_weights(r,25,support_guard=False)
        self.assertGreater(unsafe[0,1],.4)
        safe=coherent_weights(r,25,support_guard=True)
        np.testing.assert_allclose(safe,r.w,atol=1e-12)


@unittest.skipUnless((OUT/'heatsy-squat.glb').exists(),'Run isolated repair build first')
class RepairArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=Rig();cls.g,cls.b=load(OUT/'heatsy-squat.glb')

    def test_known_weight_gradient_tears_are_reduced_under_identical_pose(self):
        for edge in ([51179,51848],[75629,75643],[77507,78146]):
            before,_=sample(self.r.bg,self.r.bb,1.5,indices=edge)
            after,_=sample(self.g,self.b,1.5,indices=edge)
            rest=np.linalg.norm(self.r.rest[edge[1]]-self.r.rest[edge[0]])
            self.assertGreater(np.linalg.norm(before[1]-before[0])/rest,4)
            self.assertLess(np.linalg.norm(after[1]-after[0]),np.linalg.norm(before[1]-before[0])*.65)

    def test_geometry_anatomy_binds_and_motion_are_unchanged(self):
        old,blob=load(BROKEN)
        self.assertEqual(self.b[:len(blob)],blob)
        for key in ('nodes','skins','animations','materials','scenes'):
            self.assertEqual(old[key],self.g[key])
        a=old['meshes'][0]['primitives'][0];b=self.g['meshes'][0]['primitives'][0]
        self.assertEqual(a['indices'],b['indices'])
        for name,index in a['attributes'].items():
            if name not in ('JOINTS_0','WEIGHTS_0'):
                self.assertEqual(index,b['attributes'][name])
                np.testing.assert_array_equal(accessor(old,blob,index),accessor(self.g,self.b,index))

    def test_zero_length_source_edges_are_not_reported_as_material_strain(self):
        y,_=sample(self.r.bg,self.r.bb,1.5)
        result=self.r.metrics(y)
        self.assertEqual(result['source_degenerate_edges']['count'],59)
        self.assertIsNone(result['source_degenerate_edges']['ratio'])
        self.assertEqual(result['all']['edges'],221662)
        self.assertAlmostEqual(result['all']['maximum'],33.288817183354936,places=5)
        self.assertGreater(result['edge_length_bands']['below_0.1mm']['maximum'],100000)

    def test_closed_loop_and_unchanged_feet(self):
        ids=np.flatnonzero(self.r.rest[:,1]<.1)
        for t in (0,.75,1.5,2.25,3):
            before,_=sample(self.r.bg,self.r.bb,t,indices=ids)
            after,_=sample(self.g,self.b,t,indices=ids)
            np.testing.assert_allclose(after,before,atol=2e-6)
        a,_=sample(self.g,self.b,0,indices=[100,51179,77507])
        b,_=sample(self.g,self.b,3,indices=[100,51179,77507])
        np.testing.assert_allclose(a,b,atol=1e-7)


if __name__=='__main__':unittest.main()
