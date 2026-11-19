"""Source-bound offline scenarios; negative gates without ETABS or duplicate solvers."""
from contextlib import redirect_stdout
from copy import deepcopy
from hashlib import sha256
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tbdy_next.engineering.design_scenario import (
    PARENT_FILE, SCHEMA, create_design_scenario, design_dependency_ledger,
    prepare_pipeline_source, selected_candidate_ledger, validate_design_scenario,
    verify_archived_scenario, verify_parent,
)
from tbdy_next.engineering.pipeline_snapshot import (
    REQUIRED_KEYS, SCHEMA as SNAPSHOT_SCHEMA, compare_runs, read_snapshot, record_snapshot,
)
from tbdy_next.receipts import ReceiptRun


def request(raw, **updates):
    return {"schema": SCHEMA, "scenario_id": "offline-test-v1", "parent_input_sha256": sha256(raw).hexdigest(),
            "beam_selection": "default", "column_selection": "default", **updates}


def scope_fixture():
    pair = {"element_id": "C1", "combination": "G", "force_semantics": "STATIC_SIGNED_VECTOR",
            "execution_status": "NUMERICAL_COMPLETE", "section_rows_evaluated": 4,
            "configured_cut_coverage": {"required_count": 4, "matched_count": 4,
                                         "missing_cuts": [], "ambiguous_cuts": []},
            "analysis_element_coverage": {"roster_bound": True, "reason": None,
                                           "missing_analysis_element_ids": [], "unmapped_analysis_element_ids": []}}
    return {"schema": "tbdy.next.column-pmm-expected-instances.v1", "input_sha256": "input-hash",
            "expected_member_combination_count": 1, "known_member_combination_scope": True,
            "dependency_blockers": [], "instances": [pair]}


class ScenarioSourceContracts(unittest.TestCase):
    def setUp(self):
        self.raw = b'{ "source_mode":"LIVE_ETABS", "column_axial":{"request":{"pmm_member":"ALL"}}, "native":{"N":42} }'

    def test_source_is_preserved_and_no_authority_is_granted(self):
        raw = create_design_scenario(self.raw, request(self.raw))
        value = json.loads(raw)
        verify_parent(value, self.raw)
        self.assertEqual(value["native"], {"N": 42})
        self.assertEqual(value["design_scenario"]["parent_input_sha256"], sha256(self.raw).hexdigest())
        self.assertEqual(value["design_scenario"]["selection_role"], "ALGORITHM_SELECTED_CANDIDATE")
        self.assertEqual(value["design_scenario"]["engineering_approval"], "NOT_GRANTED")
        self.assertEqual(raw, create_design_scenario(self.raw, request(self.raw)))

    def test_policy_revision_changes_identity_not_native_source_digest(self):
        a = json.loads(create_design_scenario(self.raw, request(self.raw)))
        b = json.loads(create_design_scenario(self.raw, request(self.raw, column_selection={"min_rho": .02})))
        self.assertNotEqual(a["design_scenario"]["scenario_sha256"], b["design_scenario"]["scenario_sha256"])
        self.assertEqual(a["design_scenario"]["source_data_sha256"], b["design_scenario"]["source_data_sha256"])

    def test_invalid_requests_fail_before_derivation(self):
        mutations = [{"parent_input_sha256": "wrong"}, {"schema": "wrong"}, {"scenario_id": "../bad"},
                     {"beam_selection": None, "column_selection": None}, {"extra": True},
                     {"column_selection": {"min_rhoo": .01}}, {"column_selection": {"min_rho": .005}},
                     {"column_selection": {"strictly_exceed_required": "false"}},
                     {"beam_selection": {"stirrup_span": {"leggs": 4}}},
                     {"column_selection": {"schema": "invented"}}]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                create_design_scenario(self.raw, request(self.raw, **mutation))

    def test_native_mutation_and_policy_mutation_are_rejected(self):
        original = json.loads(create_design_scenario(self.raw, request(self.raw)))
        for kind in ("native", "policy", "approval", "digest"):
            value = deepcopy(original)
            if kind == "native": value["native"]["N"] += 1
            elif kind == "policy": value["column_selection"]["min_rho"] = .02
            elif kind == "approval": value["design_scenario"]["engineering_approval"] = "APPROVED"
            else: value["design_scenario"]["scenario_sha256"] = "bad"
            with self.subTest(kind=kind), self.assertRaises(ValueError): validate_design_scenario(value)

    def test_missing_corrupt_or_linked_parent_is_rejected(self):
        value = json.loads(create_design_scenario(self.raw, request(self.raw)))
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError): verify_archived_scenario(root, value)
            parent = root / PARENT_FILE
            parent.write_bytes(b"{}")
            with self.assertRaises(ValueError): verify_archived_scenario(root, value)
            parent.write_bytes(self.raw)
            self.assertEqual(verify_archived_scenario(root, value), value["design_scenario"])

    def test_nested_scenarios_are_not_new_captures(self):
        raw = create_design_scenario(self.raw, request(self.raw))
        with self.assertRaisesRegex(ValueError, "NESTING"):
            create_design_scenario(raw, request(raw))

    def test_null_policy_never_activates_an_implicit_selection(self):
        value = json.loads(create_design_scenario(self.raw, request(self.raw, beam_selection=None)))
        self.assertNotIn("beam_selection", value)
        self.assertIsNone(value["design_scenario"]["policies"]["beam_selection"])

    def test_duplicate_and_nonfinite_source_json_is_rejected(self):
        for raw in (b'{"source_mode":"LIVE_ETABS","source_mode":"other"}', b'{"value":NaN}'):
            with self.assertRaises(ValueError): create_design_scenario(raw, request(raw))

    def test_adapter_preparation_preserves_original_bytes_and_inherits_omitted_policy(self):
        plain = prepare_pipeline_source(self.raw)
        self.assertEqual(plain.raw, self.raw)
        self.assertIsNone(plain.parent_raw)
        first = prepare_pipeline_source(self.raw, selection_overrides={
            "beam_selection": "default", "column_selection": {"min_rho": .02}})
        with TemporaryDirectory() as temp:
            root = Path(temp)
            first.archive_parent(root)
            source = root / "input.source"
            source.write_bytes(first.raw)
            replay = prepare_pipeline_source(source.read_bytes(), source_directory=root)
            self.assertEqual(replay.raw, first.raw)
            unchanged = prepare_pipeline_source(first.raw, source_directory=root, selection_overrides={})
            self.assertEqual(unchanged.raw, first.raw)
            revised = prepare_pipeline_source(first.raw, source_directory=root,
                selection_overrides={"beam_selection": {"allowed_additional_diameters_mm": [16, 20]}})
            self.assertEqual(revised.payload["column_selection"], first.payload["column_selection"])
            self.assertEqual(revised.parent_raw, self.raw)
            self.assertEqual(revised.payload["design_scenario"]["parent_input_sha256"], sha256(self.raw).hexdigest())
            self.assertNotEqual(revised.payload["design_scenario"]["scenario_sha256"],
                                first.payload["design_scenario"]["scenario_sha256"])
            self.assertEqual(source.read_bytes(), first.raw)
            self.assertEqual((root / PARENT_FILE).read_bytes(), self.raw)
            verify_parent(revised.payload, self.raw)

    def test_adapter_preparation_validates_existing_lineage_before_any_policy_change(self):
        first = prepare_pipeline_source(self.raw, selection_overrides={"column_selection": "default"})
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "PARENT_SOURCE"):
                prepare_pipeline_source(first.raw, source_directory=root,
                                        selection_overrides={"column_selection": {"min_rho": .02}})
            first.archive_parent(root)
            mutated = deepcopy(first.payload)
            mutated["native"]["N"] += 1
            with self.assertRaisesRegex(ValueError, "SOURCE_OR_POLICY_CHANGED"):
                prepare_pipeline_source(json.dumps(mutated).encode(), source_directory=root,
                                        selection_overrides={"column_selection": "default"})
            (root / PARENT_FILE).write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError, "PARENT_HASH_MISMATCH"):
                prepare_pipeline_source(first.raw, source_directory=root,
                                        selection_overrides={"column_selection": "default"})

    def test_adapter_explicit_request_uses_verified_native_parent_not_scenario_bytes(self):
        first = prepare_pipeline_source(self.raw, selection_overrides={"column_selection": "default"})
        with TemporaryDirectory() as temp:
            root = Path(temp)
            first.archive_parent(root)
            revised = prepare_pipeline_source(first.raw, source_directory=root,
                                              request=request(self.raw, column_selection={"min_rho": .02}))
            verify_parent(revised.payload, self.raw)
            self.assertEqual(revised.parent_raw, self.raw)
            with self.assertRaisesRegex(ValueError, "PARENT_HASH_MISMATCH"):
                prepare_pipeline_source(first.raw, source_directory=root, request=request(first.raw))

    def test_adapter_explicit_null_disables_one_policy_without_an_implicit_default(self):
        first = prepare_pipeline_source(self.raw, selection_overrides={
            "beam_selection": "default", "column_selection": "default"})
        with TemporaryDirectory() as temp:
            root = Path(temp)
            first.archive_parent(root)
            revised = prepare_pipeline_source(first.raw, source_directory=root,
                                              selection_overrides={"beam_selection": None})
            self.assertNotIn("beam_selection", revised.payload)
            self.assertEqual(revised.payload["column_selection"], first.payload["column_selection"])
            self.assertIsNone(revised.payload["design_scenario"]["policies"]["beam_selection"])

    def test_adapter_unknown_fields_and_conflicting_requests_are_rejected(self):
        for overrides in ({"column_selection": {"min_rhoo": .02}}, {"invented_selection": "default"}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                prepare_pipeline_source(self.raw, selection_overrides=overrides)
        with self.assertRaisesRegex(ValueError, "EXCLUSIVE"):
            prepare_pipeline_source(self.raw, request=request(self.raw), selection_overrides={})


class CandidateDependencyContracts(unittest.TestCase):
    def test_complete_subset_can_run_only_a_reference_candidate(self):
        result = design_dependency_ledger(scope_fixture(), input_sha="input-hash")
        self.assertTrue(result["candidate_execution_allowed"])
        self.assertFalse(result["independent_cut_census_proven"])
        self.assertEqual(result["engineering_release"], "NOT_READY")

    def test_partial_inputs_block_and_never_shrink_expected_denominator(self):
        mutations = ("blocked", "missing_cut", "ambiguous_cut", "missing_mesh", "duplicate", "count", "source", "scope")
        for kind in mutations:
            scope = scope_fixture()
            row = scope["instances"][0]
            if kind == "blocked": row["execution_status"] = "BLOCKED"
            elif kind == "missing_cut": row["configured_cut_coverage"]["matched_count"] = 3
            elif kind == "ambiguous_cut": row["configured_cut_coverage"]["ambiguous_cuts"] = [{"analysis_element_id": "E2"}]
            elif kind == "missing_mesh": row["analysis_element_coverage"]["missing_analysis_element_ids"] = ["E2"]
            elif kind == "duplicate": scope["instances"].append(deepcopy(row))
            elif kind == "count": scope["expected_member_combination_count"] = 2
            elif kind == "source": scope["input_sha256"] = "other-source"
            elif kind == "scope": scope["known_member_combination_scope"] = False
            result = design_dependency_ledger(scope, input_sha="input-hash")
            with self.subTest(kind=kind):
                self.assertFalse(result["candidate_execution_allowed"])
                self.assertEqual(result["expected_member_combination_count"], scope["expected_member_combination_count"])

    def test_unsigned_envelope_is_not_promoted_to_signed_pmm(self):
        scope = scope_fixture(); row = scope["instances"][0]
        row.update(force_semantics="SCALAR_COMPONENT_ENVELOPE", execution_status="OUT_OF_SCOPE",
                   reason="COMPONENT_ENVELOPE_HAS_NO_SIGNED_PMM_VECTOR", section_rows_evaluated=0)
        result = design_dependency_ledger(scope, input_sha="input-hash")
        self.assertTrue(result["candidate_execution_allowed"])
        row["execution_status"] = "NUMERICAL_COMPLETE"
        self.assertFalse(design_dependency_ledger(scope, input_sha="input-hash")["candidate_execution_allowed"])

    def test_missing_scope_cannot_pass(self):
        self.assertFalse(design_dependency_ledger(None, input_sha="input-hash")["candidate_execution_allowed"])

    def test_selected_cage_must_be_the_r10_object_not_a_copied_claim(self):
        from tbdy_next.column_engine.section_capacity import Bar, Material, Section
        from tbdy_next.engineering.column_r10_live import SelectedColumnCage
        section = Section(300, 400, (Bar(-50, -50, 314), Bar(50, 50, 314)), Material(30, 20, 365))
        selection = {"member_id": "C1", "selected": {"label": "test-candidate"}}
        cage = SelectedColumnCage(selection, section)
        r10 = {"member_id": "C1", "engineer_column_selection": selection}
        scope = scope_fixture()
        valid = selected_candidate_ledger(scope, {"C1": cage}, r10, input_sha="input-hash")
        self.assertTrue(valid["downstream_execution_allowed"])
        self.assertEqual(len(valid["rows"][0]["candidate_sha256"]), 64)
        for cages, reported in (({}, r10), ({"C1": cage}, deepcopy(r10)), ({"C1": cage, "extra": cage}, r10)):
            self.assertFalse(selected_candidate_ledger(scope, cages, reported, input_sha="input-hash")["downstream_execution_allowed"])


class ScenarioSnapshotContracts(unittest.TestCase):
    def test_parent_is_part_of_finalized_integrity_and_policy_changes_compare_different(self):
        raw = b'{"source_mode":"LIVE_ETABS","column_axial":{"request":{"pmm_member":"ALL"}}}'
        with TemporaryDirectory() as temp:
            roots = []
            for rho in (.01, .02):
                derived = create_design_scenario(raw, request(raw, column_selection={"min_rho": rho}))
                payload = json.loads(derived); h = sha256(derived).hexdigest()
                run = ReceiptRun(Path(temp)); run.archive_input(derived, expected_sha256=h)
                (run.root / PARENT_FILE).write_bytes(raw)
                run.record("schema-discovery", {}, input_sha256=h, receipt_schema=SNAPSHOT_SCHEMA)
                run.record("modal", {}, input_sha256=h)
                result = dict.fromkeys(REQUIRED_KEYS)
                result["report_evidence"] = {"design_scenario": payload["design_scenario"]}
                link = record_snapshot(run, input_sha=h, results=result, registry=[])
                run.record("live-capture", {"engine_snapshot": link}, input_sha256=h)
                self.assertIsNotNone(read_snapshot(run.root, input_sha=h))
                roots.append((run.root, h))
            self.assertEqual(compare_runs(roots[0][0], roots[1][0])["status"], "DIFFERENT")
            (roots[0][0] / PARENT_FILE).unlink()
            with self.assertRaisesRegex(ValueError, "PARENT_SOURCE"):
                read_snapshot(roots[0][0], input_sha=roots[0][1])


class ScenarioPipelineContracts(unittest.TestCase):
    def test_missing_subset_blocks_linked_design_owners_and_report_reads_saved_result(self):
        import test_column_axial_live as live
        from tbdy_next.engineering.cli_adapter import _run_pipeline_replay
        from tbdy_next.engineering.pipeline import EnginePipelineRunner
        from tbdy_next.reporting import build_complete_report
        fixture = live.ColumnAxialIntegration()
        fixture.setUp()
        try:
            query = fixture.query("ETABS_STRENGTH")
            query.update(check="column-pmm", member="C1")
            run_id = fixture.post(query)["run_id"]
            raw = (fixture.root / run_id / "input.source").read_bytes()
        finally:
            fixture.tearDown()
        with TemporaryDirectory() as temp:
            root = Path(temp); source = root / "input.source"; source.write_bytes(raw)
            scenario = root / "scenario.json"; scenario.write_text(json.dumps(request(raw)))
            args = SimpleNamespace(source=source, case="Modal", out=root / "runs", compare_run=None,
                                   beam_selection=None, column_selection=None, design_scenario=scenario)
            with patch("tbdy_next.engineering.beam_r10_live.project_beam_r10_live") as beam, patch(
                    "tbdy_next.engineering.column_r10_live.project_column_r10_live") as r10, patch(
                    "tbdy_next.engineering.column_r08_local_live.project_column_r08_local_live") as r08:
                text = io.StringIO()
                with redirect_stdout(text): self.assertEqual(_run_pipeline_replay(args), 0)
                beam.assert_not_called(); r10.assert_not_called(); r08.assert_not_called()
            summary = json.loads(text.getvalue())
            self.assertFalse(summary["design_dependencies"]["candidate_execution_allowed"])
            self.assertEqual(source.read_bytes(), raw)
            run_dir = Path(summary["run_dir"])
            with patch.object(EnginePipelineRunner, "run", side_effect=AssertionError("report must not run")):
                report = build_complete_report(run_dir.parent, run_dir.name)
            self.assertEqual(report["r14_closure"]["design_scenario"], summary["design_scenario"])
            self.assertNotEqual(report["r14_closure"]["status"], "R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES")
            # The replay must carry the original parent without another selection override.
            args.source = run_dir / "input.source"; args.design_scenario = None; args.compare_run = run_dir
            with redirect_stdout(io.StringIO()): self.assertEqual(_run_pipeline_replay(args), 0)
            (run_dir / PARENT_FILE).write_bytes(b"{}")
            with self.assertRaises(ValueError): _run_pipeline_replay(args)


if __name__ == "__main__":
    unittest.main()
