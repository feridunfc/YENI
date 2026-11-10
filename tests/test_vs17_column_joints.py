from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from column_joint_fixture import JointBank
from column_stability_fixture import StiffnessBank
from tbdy_next.column_engine.native_archive import NativeArchive,BankError
from tbdy_next.column_engine.source_bank import recover_column_bank
from tbdy_next.column_engine.demand_chain import build_demand_chain
from tbdy_next.column_engine.column_prechecks import build_column_prechecks
from tbdy_next.column_engine.column_stability import build_column_stability
from tbdy_next.column_engine.column_pmm import build_column_cages,_section
from tbdy_next.column_engine.column_transverse import build_column_transverse
from tbdy_next.column_engine.column_joints import build_column_joints,joint_tie_rows
from tbdy_next.column_engine.joint_kernel import width_reference,centered_joint_limit,joint_transverse_reference
from tbdy_next.column_engine.store import read_column_bank,save_column_bank
from tbdy_next.reporting import _column_cage_svg


def package(fixture=None):
    raw=(fixture or JointBank()).build();bank=recover_column_bank(raw)
    with closing(NativeArchive(raw)) as archive:
        chain=build_demand_chain(bank,archive);prechecks=build_column_prechecks(bank,chain)
        cages=build_column_cages(bank,chain,prechecks,archive)
        transverse=build_column_transverse(chain,cages,archive)
        result=build_column_joints(bank,chain,cages,transverse,archive)
    return result,cages,transverse


def joint(result,member='C_SYNTHETIC_1',end='J'):
    return next(r for r in result['rows'] if r['member_id']==member and r['end']==end)


class NativeAxisRegressionTests(unittest.TestCase):
    def test_asymmetric_native_b60x70_section_oracle_across_all_adapters(self):
        # Independent sealed observations: GetRectangle b0003708 and
        # GetSectProps b0003707, ZIP SHA3882b659...: I22=.0126, I33=.01715 m4.
        # This explicit oracle predates and does not call production geometry.
        fixture=StiffnessBank()
        fixture.calls[('PropFrame.GetRectangle','frame_section','RECT_SYNTHETIC')]['raw_response'][2:4]=[.7,.6]
        p=fixture.calls[('PropFrame.GetSectProps','frame_section','RECT_SYNTHETIC')]['raw_response']
        p[0]=.42;p[4:6]=[.012600000000000014,.01715000000000002]
        p[10:12]=[.1732050807568878,.20207259421636914]
        raw=fixture.build();bank=recover_column_bank(raw)
        with closing(NativeArchive(raw)) as a:
            chain=build_demand_chain(bank,a);pre=build_column_prechecks(bank,chain)
            stability=build_column_stability(bank,chain,pre,a);cages=build_column_cages(bank,chain,pre,a)
            ties=build_column_transverse(chain,cages,a)
        self.assertEqual(stability['native_property_match_count'],10)
        sec=stability['sections'][0]['section']
        self.assertAlmostEqual(sec['i22_mm4'],12.6e9);self.assertAlmostEqual(sec['i33_mm4'],17.15e9)
        self.assertEqual((sec['e_min_m2_mm'],sec['e_min_m3_mm']),('33','36'))
        cage=cages['candidates'][0];physical=_section(cages['profiles'][0],cage)
        self.assertEqual((physical.t2,physical.t3),(700,600))
        self.assertEqual({b['x2_mm'] for b in cage['bars']},{-286,-143,0,143,286})
        self.assertEqual({b['x3_mm'] for b in cage['bars']},{-236,-118,0,118,236})
        proposal=ties['proposals'][0];v2,v3=proposal['axes']['V2'],proposal['axes']['V3']
        self.assertEqual((v2['bw_mm'],v2['d_mm'],v2['bk_mm']),(600,636,508))
        self.assertEqual((v3['bw_mm'],v3['d_mm'],v3['bk_mm']),(700,536,608))
        self.assertEqual(proposal['layout']['core_area_mm2'],322400)
        self.assertIn('width="700.0" height="600.0"',_column_cage_svg(cage))
        self.assertEqual(cages['axis_convention'],'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3')


class JointKernelTests(unittest.TestCase):
    def test_three_quarter_boundary_includes_equality_without_expanding_inequality(self):
        self.assertTrue(width_reference(600,800))
        self.assertFalse(width_reference(math.nextafter(600,-math.inf),800))
        self.assertTrue(width_reference(math.nextafter(600,math.inf),800))

    def test_independent_800_square_geometric_limits_without_invented_ve(self):
        for enclosure,expected in [('ENCLOSED',6436.694804012),('UNENCLOSED',3786.291061184)]:
            r=centered_joint_limit(column_width_mm=800,column_depth_mm=800,beam_widths_mm=[600,600],fck_mpa=35,enclosure=enclosure)
            self.assertEqual(r['bj_mm'],800)
            self.assertAlmostEqual(r['geometric_limit_kn'],expected,places=8)
            self.assertIsNone(r['ve_kn']);self.assertIsNone(r['utilization'])
            self.assertFalse(r['physical_geometry_proven'])

    def test_centered_bj_keeps_beam_width_plus_depth_bound(self):
        r=centered_joint_limit(column_width_mm=1200,column_depth_mm=300,beam_widths_mm=[400,500],fck_mpa=25,enclosure='UNENCLOSED')
        self.assertEqual(r['bj_mm'],700)
        self.assertEqual(r['geometric_limit_kn'],1050)

    def test_joint_ties_transfer_density_not_area_and_keep_spacing_and_diameter_limits(self):
        base=dict(lower_required_ash_mm2=500,lower_spacing_mm=100,proposed_ash_mm2=200,
            joint_spacing_mm=150,tie_diameter_mm=8,enclosure='ENCLOSED')
        r=joint_transverse_reference(**base)
        self.assertEqual(r['required_ash_at_joint_spacing_mm2'],300)
        self.assertFalse(r['density_reference_met']);self.assertFalse(r['all_references_met'])
        self.assertTrue(joint_transverse_reference(**(base|{'proposed_ash_mm2':300}))['all_references_met'])
        for changes in ({'joint_spacing_mm':151,'proposed_ash_mm2':500},
                        {'tie_diameter_mm':7.999,'proposed_ash_mm2':500},
                        {'enclosure':'UNENCLOSED','proposed_ash_mm2':500}):
            self.assertFalse(joint_transverse_reference(**(base|changes))['all_references_met'])
        r=joint_transverse_reference(**(base|{'enclosure':'UNENCLOSED','joint_spacing_mm':100,'proposed_ash_mm2':300}))
        self.assertTrue(r['all_references_met']);self.assertEqual(r['fraction_of_lower_required_density'],.6)

    def test_invalid_or_unknown_inputs_do_not_authorize_any_reference(self):
        for value in (0,-1,True,None,float('inf'),float('nan')):
            with self.subTest(value=value),self.assertRaises(BankError):width_reference(value,800)
        with self.assertRaises(BankError):centered_joint_limit(column_width_mm=800,column_depth_mm=800,beam_widths_mm=[],fck_mpa=35,enclosure='ENCLOSED')
        with self.assertRaises(BankError):centered_joint_limit(column_width_mm=800,column_depth_mm=800,beam_widths_mm=[600],fck_mpa=35,enclosure='UNKNOWN')


class JointSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.result,cls.cages,cls.transverse=package()

    def test_complete_native_catalog_retains_every_selected_end_and_traces_sources(self):
        r=self.result;self.assertEqual((r['graph']['frame_count'],r['graph']['point_count'],r['joint_node_count'],r['column_end_count']),(6,7,3,4))
        self.assertEqual(r['enclosure_counts'],{'ENCLOSED':2})
        self.assertEqual(r['geometric_limit_count'],4);self.assertEqual(r['tie_reference_count'],12)
        self.assertEqual(r['status_counts'],{'NO_RECORDED_BEAM_AT_NODE':2,'JOINT_GEOMETRIC_REFERENCES_CALCULATED':2})
        row=joint(r)
        self.assertEqual({v['frame_id'] for v in row['faces'].values()},{'BX+','BX-','BY+','BY-'})
        self.assertTrue(all(v['width_reference_met'] for v in row['faces'].values()))
        self.assertEqual(row['lower_column_id'],'C_SYNTHETIC_1')
        for frame in r['graph']['frames']:
            for proof in frame['source_calls'].values():self.assertIn('shard_sha256',proof)
        self.assertFalse(r['physical_joint_population_proven']);self.assertEqual(r['scwb_status'],'NOT_PROVEN')
        self.assertTrue(all(row['joint_ve_kn'] is None and row['scwb_ratio'] is None for row in r['rows']))

    def test_ij_reversal_and_global_rotation_preserve_class_and_physical_limits(self):
        for angle in (0,45,90):
            f=JointBank();f.reverse('BX+');f.reverse('BY-');f.reverse(f.members[0]);f.rotate_global(angle)
            r,_,_=package(f);row=joint(r,end='I')
            self.assertEqual(r['enclosure_counts'],self.result['enclosure_counts'])
            self.assertEqual(row['lower_column_id'],'C_SYNTHETIC_1')
            self.assertEqual(sorted(a['calculation']['geometric_limit_kn'] for a in row['axes']),
                sorted(a['calculation']['geometric_limit_kn'] for a in joint(self.result)['axes']))

    def test_rotated_unequal_lower_column_maps_physical_axis_before_ash_transfer(self):
        f=JointBank();f.unequal_rotated_lower();r,_,_=package(f)
        row=joint(r,'C_SYNTHETIC_2','I')
        x=next(t for t in row['tie_references'] if t['axis']=='V2' and t['candidate_label']=='16Φ24')
        self.assertEqual(x['lower_axis'],'V3')
        self.assertEqual(row['geometry_column_id'],'C_SYNTHETIC_2')
        self.assertEqual(x['lower_column_id'],'C_SYNTHETIC_1')
        self.assertAlmostEqual(x['branches']['high']['lower_required_ash_mm2'],419.353846154,places=8)
        self.assertAlmostEqual(x['branches']['high']['required_ash_per_s_mm2_per_mm'],1.67741538462,places=10)
        self.assertIsNone(x['axial_branch_selected']);self.assertEqual(x['basis'],'EQ7_1_CONFINEMENT_BASELINE_ONLY')
        self.assertFalse(x['actual_joint_minimum_proven'])

    def test_narrow_beam_and_missing_face_do_not_get_enclosed_coefficient(self):
        for mode in ('narrow','missing'):
            f=JointBank()
            if mode=='narrow':f.calls[('PropFrame.GetRectangle','frame_section','BEAM_SYNTHETIC')]['raw_response'][3]=.5999999999999999
            else:
                f.point('PX_OUT',(10,0,4));f.calls[('FrameObj.GetPoints','frame','BX+')]['raw_response'][:2]=['PX+','PX_OUT']
            r,_,_=package(f);row=joint(r)
            self.assertEqual(row['enclosure_scenario'],'UNENCLOSED')
            self.assertEqual([a['calculation']['coefficient'] for a in row['axes']],[1,1])
            self.assertTrue(row['narrow_faces'] if mode=='narrow' else row['missing_faces'])

    def test_unobserved_catalog_or_endpoint_cannot_hide_a_neighbor(self):
        for key in [('FrameObj.GetNameList','frames',None),('PointObj.GetNameList','points',None),
                    ('FrameObj.GetPoints','frame','BX+'),('FrameObj.GetDesignOrientation','frame','BY-')]:
            f=JointBank();f.omitted.add(key);r,_,_=package(f)
            self.assertEqual(r['status_counts'],{'BLOCKED_INPUTS':4})
            self.assertEqual(r['geometric_limit_count'],0)
        r,_,_=package(StiffnessBank())
        self.assertEqual(r['column_end_count'],4);self.assertEqual(r['graph']['status'],'BLOCKED_INPUTS')

    def test_missing_or_wrong_global_request_blocks_geometry(self):
        for api,kind,name,last in [('FrameObj.GetTransformationMatrix','frame','BX+',False),
                                   ('PointObj.GetCoordCartesian','point','P1','Local')]:
            f=JointBank();f.calls[(api,kind,name)]['args'][-1]=last
            r,_,_=package(f);self.assertEqual(r['geometric_limit_count'],0)
            self.assertIn('NATIVE_REQUEST_ARGUMENTS_MISMATCH',str(r))

    def test_matrix_shape_orthogonality_handedness_and_ij_direction_are_all_guarded(self):
        for matrix in ([1]*8,[1]*9,[1,0,0,0,0,1,0,1,0],[-1,0,0,0,0,1,0,1,0],
                       [1,0,0,0,0,-1,0,1,float('inf')]):
            f=JointBank();f.calls[('FrameObj.GetTransformationMatrix','frame','BX+')]['raw_response'][0]=matrix
            r,_,_=package(f);self.assertEqual(joint(r)['status'],'BLOCKED_INPUTS')

    def test_native_decimal_meter_conversion_preserves_exact_width_boundary(self):
        f=JointBank()
        f.calls[('PropFrame.GetRectangle','frame_section','RECT_SYNTHETIC')]['raw_response'][2:4]=[.4008,.4008]
        f.calls[('PropFrame.GetRectangle','frame_section','BEAM_SYNTHETIC')]['raw_response'][3]=.3006
        r,_,_=package(f)
        self.assertEqual(joint(r)['enclosure_scenario'],'ENCLOSED')
        self.assertEqual(joint(r)['faces']['2+']['beam_width_mm'],300.6)

    def test_coincident_distinct_point_ids_are_not_merged(self):
        f=JointBank();f.point('DISTINCT',(0,0,4));r,_,_=package(f)
        self.assertEqual(joint(r)['reason'],'JOINT_COINCIDENT_DISTINCT_POINT_IDS')
        self.assertEqual(r['graph']['point_count'],8);self.assertEqual(r['joint_node_count'],3)

    def test_interior_crossing_and_unclassified_frames_are_not_silently_dropped(self):
        f=JointBank();f.point('A',(-3,-3,4));f.point('B',(3,3,4))
        f.frame('CROSSING','A','B',2,'BEAM_SYNTHETIC',[1,0,0,0,0,-1,0,1,0])
        r,_,_=package(f);self.assertEqual(joint(r)['reason'],'JOINT_INTERIOR_FRAME_CONNECTION_NOT_BOUND')
        f=JointBank();f.point('A',(3,3,5));f.frame('UNKNOWN','P1','A',4,'None',[1,0,0,0,1,0,0,0,1])
        r,_,_=package(f);self.assertEqual(joint(r)['reason'],'JOINT_OTHER_INCIDENT_FRAME_NOT_CLASSIFIED')

    def test_missing_beam_geometry_keeps_joint_and_both_column_end_rows_blocked(self):
        f=JointBank();f.omitted.add(('FrameObj.GetTransformationMatrix','frame','BX+'))
        r,_,_=package(f)
        self.assertEqual(r['column_end_count'],4);self.assertEqual(r['joint_node_count'],3)
        self.assertEqual(r['status_counts'],{'NO_RECORDED_BEAM_AT_NODE':2,'BLOCKED_INPUTS':2})

    def test_zero_or_nonzero_rebar_overrides_never_supply_actual_beam_capacity(self):
        f=JointBank();f.calls[('PropFrame.GetRebarBeam','beam_section','BEAM_SYNTHETIC')]['raw_response'][4:8]=[.002]*4
        r,_,_=package(f)
        self.assertTrue(all(x['scwb_ratio'] is None and x['joint_ve_kn'] is None for x in r['rows']))
        self.assertEqual(r['ve_status'],'NOT_PROVEN')
        self.assertIsNone(r['selected_design'])

    def test_source_binding_and_no_mutation(self):
        raw=JointBank().build();bank=recover_column_bank(raw)
        with closing(NativeArchive(raw)) as a:
            chain=build_demand_chain(bank,a);pre=build_column_prechecks(bank,chain)
            cages=build_column_cages(bank,chain,pre,a);ties=build_column_transverse(chain,cages,a)
            before=deepcopy((bank,chain,cages,ties))
            first=build_column_joints(bank,chain,cages,ties,a);second=build_column_joints(bank,chain,cages,ties,a)
            self.assertEqual(first['result_sha256'],second['result_sha256']);self.assertEqual(before,(bank,chain,cages,ties))
            ties['source_cages_result_sha256']='OTHER'
            with self.assertRaises(BankError):build_column_joints(bank,chain,cages,ties,a)

    def test_joint_pages_filter_and_do_not_run_pmm_or_grow_database(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);source=root/'bank.zip';source.write_bytes(JointBank().build())
            report=save_column_bank(source,root/'receipts');run=report['run_id']
            db=root/'receipts'/run/'column-bank.sqlite';before=sha256(db.read_bytes()).hexdigest()
            with patch('tbdy_next.column_engine.demand_view._pmm',side_effect=AssertionError('Unexpected PMM')):
                r=read_column_bank(root/'receipts',run,view='joints',member_id='C_SYNTHETIC_2',limit=1,offset=1)
                self.assertEqual((r['demand_page']['total'],len(r['demand_page']['rows'])),(2,1))
                self.assertNotIn('frames',r['column_joints']['graph']);self.assertNotIn('rows',r['column_joints'])
                ties=read_column_bank(root/'receipts',run,view='joint-ties',member_id='C_SYNTHETIC_2')
                self.assertEqual(ties['demand_page']['total'],7)
            for view in ('joints','joint-ties'):
                with self.assertRaises(BankError):read_column_bank(root/'receipts',run,view=view,output_case='SUM')
            self.assertEqual(before,sha256(db.read_bytes()).hexdigest())
            self.assertEqual(len(joint_tie_rows(self.result)),14)


if __name__=='__main__':unittest.main()
