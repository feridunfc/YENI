"""Point action transport and scope checks used by the coupled first-order section."""
import unittest

from tbdy_next.engineering.coupled_wall_transition import _seismic_load_scope
from tbdy_next.engineering.gravity_wall_cut import joint_action_at_origin


class CutTransportTests(unittest.TestCase):
    def test_rotates_both_vectors_before_moving_the_moment(self):
        # Local 1 is +Y, local 2 is -X, local 3 is +Z. Apply at a non-coplanar point.
        rotation = [0, -1, 0, 1, 0, 0, 0, 0, 1]
        actual = joint_action_at_origin([2, 3, 4, 5, 6, 7], rotation, [2, 4, 5], [1, 2, 2])
        self.assertEqual(actual, (-3, 2, 4, -4, -8, 15))

    def test_changing_origin_leaves_a_pure_couple_unchanged(self):
        identity = [1, 0, 0, 0, 1, 0, 0, 0, 1]
        for origin in ([0, 0, 0], [1, 2, -3]):
            self.assertEqual(joint_action_at_origin([0,0,0,1,2,3], identity, [5,1,1], origin),
                             (0,0,0,1,2,3))

    def test_rejects_reflected_axes_and_nonfinite_moment(self):
        with self.assertRaisesRegex(ValueError, "RIGHT_HANDED"):
            joint_action_at_origin([1]*6,[-1,0,0,0,1,0,0,0,1],[0]*3,[0]*3)
        with self.assertRaisesRegex(ValueError, "CUT_ACTION"):
            joint_action_at_origin([0,0,0,0,float("nan"),0],[1,0,0,0,1,0,0,0,1],[0]*3,[0]*3)

    def test_automatic_load_requires_a_single_tower_and_excludes_both_cut_planes(self):
        scope = {"code":"TSC-2018","towers":1,"additional_object_loads":0,
                 "bottom_story":"base","top_story":"roof","levels_m":{"base":-3,"story":1,"roof":5}}
        self.assertTrue(_seismic_load_scope({"story_application":scope},-.5,.5))
        for lo, hi in ((0,1),(1,2),(0,2),(-4,-3.5)):
            self.assertFalse(_seismic_load_scope({"story_application":scope},lo,hi))
        for field, value in (("additional_object_loads",1),("towers",2)):
            self.assertFalse(_seismic_load_scope({"story_application":{**scope,field:value}},-.5,.5))
        self.assertFalse(_seismic_load_scope({},-.5,.5))
