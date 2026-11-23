"""Regression checks for evidence that distinguishes folding from rigid blending."""
import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'studio'))
from heatsy_attachment import edge_terms, sharpen, soften


class AttachmentDiagnostics(unittest.TestCase):
    def test_gradient_can_collapse_edge_under_rigid_translations(self):
        x=np.array([[0.,0,0],[1.,0,0]])
        w=np.array([[1.,0],[0.,1]])
        ops=np.repeat(np.eye(4)[None],2,axis=0);ops[1,0,3]=-.9
        geometric,gradient,singular=edge_terms(x,w,ops,np.array([[0,1]]))
        np.testing.assert_allclose(geometric,[[1,0,0]])
        np.testing.assert_allclose(gradient,[[-.9,0,0]])
        np.testing.assert_allclose(geometric+gradient,[[.1,0,0]])
        np.testing.assert_allclose(singular,1)

    def test_constant_weights_isolate_rotation_cancellation(self):
        x=np.array([[0.,0,0],[1.,0,0]])
        w=np.array([[.5,.5],[.5,.5]])
        ops=np.repeat(np.eye(4)[None],2,axis=0);ops[1,:3,:3]=np.diag([-1,-1,1])
        geometric,gradient,singular=edge_terms(x,w,ops,np.array([[0,1]]))
        np.testing.assert_allclose(geometric,0)
        np.testing.assert_allclose(gradient,0)
        np.testing.assert_allclose(singular,[[1,0,0]])

    def test_candidate_transforms_preserve_support_and_soles(self):
        weights=np.array([[.8,.2,0,0,0],[.3,.2,.4,.1,0],[1.,0,0,0,0]])
        for transform,parameter in ((sharpen,1.25),(soften,.5)):
            result=transform(weights,np.array([.05,1.,1.]),parameter)
            np.testing.assert_array_equal(result[0],weights[0])
            np.testing.assert_array_equal(result==0,weights==0)
            np.testing.assert_allclose(result.sum(1),1)
            self.assertTrue(np.isfinite(result).all())


if __name__=='__main__':unittest.main()
