"""Seal or independently replay G5 against one archived CLI run and the production HTTP handler."""
import argparse
from contextlib import ExitStack, contextmanager
from hashlib import sha256
from http.client import HTTPConnection
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch

from tbdy_next.archive_blobs import archive_bytes
from tbdy_next.engineering.cli_adapter import _write_new
from tbdy_next.engineering.g1_contract import require
from tbdy_next.engineering.g5_contract import g5_contract, verification
from tbdy_next.engineering.pipeline_snapshot import _digest, read_receipts, read_snapshot
from tbdy_next.web import WorkspaceHTTPServer, make_handler
from verify_g4_contract import verify as verify_parent


@contextmanager
def http_archive(root):
    def reject_capture(*args, **kwargs):
        raise AssertionError("G5 must use only the archived input")
    with WorkspaceHTTPServer(("127.0.0.1",0),make_handler(root,live_capture=reject_capture)) as server:
        worker=Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            yield server.server_port
        finally:
            server.shutdown()
            worker.join()


def request(port,path,body=None,expected=200):
    conn=HTTPConnection("127.0.0.1",port,timeout=180)
    try:
        conn.request("GET" if body is None else "POST",path,
                     body=None if body is None else json.dumps(body).encode(),
                     headers={"Content-Type":"application/json"})
        response=conn.getresponse()
        data=response.read()
        if response.status!=expected:
            raise ValueError(f"G5_HTTP_{response.status} {path} {data[:300]!r}")
        return data
    finally:
        conn.close()


def projection_trace(directory,base_id):
    # Patch the actual owner symbols at both adapter/engine and calculation boundaries.
    blocked=("engineering.pipeline.EnginePipelineRunner.run","engineering.pipeline.run_source_pipeline",
             "engineering.pipeline.calculate_modal","engineering.pipeline.evaluate_geometry_capture",
             "engineering.pipeline.evaluate_next_capture","engineering.pipeline.evaluate_analysis_numerics",
             "engineering.pipeline.evaluate_single_run_source_pipeline","story_drift_binding.bind_story_drift",
             "engineering.pipeline._run_column_axial","engineering.pipeline._run_column_pmm",
             "engineering.column_r08_local_live.project_column_r08_local_live",
             "engineering.column_r10_live.project_column_r10_live","engineering.beam_r10_live.project_beam_r10_live",
             "engineering.column_r14_closure.project_column_r14_and_r15_closure",
             "engineering.rebar_selection.select_column_rebar")
    with http_archive(directory.parent) as port, ExitStack() as guard:
        from tbdy_next.receipts import ReceiptRun
        normal={}
        def observe(owner,payload,*,case,run,input_sha,suite):
            normal.update(case=case,suite=suite,input_sha256=input_sha,prepared_payload_sha256=_digest(payload))
            raise ValueError("G5_STOP_AT_ORDINARY_WEB_RUNNER_BOUNDARY")
        with TemporaryDirectory() as temporary, patch("tbdy_next.web.ReceiptRun",lambda _:ReceiptRun(Path(temporary))), \
                patch("tbdy_next.engineering.pipeline.EnginePipelineRunner.run",autospec=True,side_effect=observe):
            interrupted=json.loads(request(port,"/api/apply-rebar-selection",{"base_run_id":base_id,
                                    "whole_building":True},expected=422))
            require(interrupted["result"]["reason"]=="G5_STOP_AT_ORDINARY_WEB_RUNNER_BOUNDARY","G5_WEB_DISPATCH_TRACE")
        spies=[guard.enter_context(patch("tbdy_next."+target,side_effect=AssertionError(target))) for target in blocked]
        ack=json.loads(request(port,"/api/apply-rebar-selection",{"base_run_id":base_id,
            "whole_building":True,"verified_run_id":directory.name}))
        require(ack["source"]=="VERIFIED_SAME_METHOD_ARCHIVE" and ack["run_id"]==directory.name,"G5_HTTP_REPLAY_MODE")
        exported=json.loads(request(port,"/api/export-checks?run_id="+directory.name))
        printed=request(port,"/report/print?run_id="+directory.name)
    digest=_digest(exported["building_design"])
    trace={"normal_web_runner_arguments":normal,"calculator_calls":sum(spy.call_count for spy in spies),"observed_owners":list(blocked),
           "export_matches":digest==ack["stage_projection"]["building_sha256"],
           "print_matches":printed==(directory/"report.html").read_bytes(),"print_sha256":sha256(printed).hexdigest()}
    return ack["stage_projection"],digest,trace


def compare_or_seal(path,value,seal):
    if seal and not path.exists():
        _write_new(path,value)
    require(json.loads(path.read_bytes())==value,"G5_VERIFICATION_CHANGED:"+path.name)


def verify(directory,base_id,seal=False):
    verify_parent(directory)
    raw=archive_bytes(directory/"input.source")
    digest=sha256(raw).hexdigest()
    records=read_receipts(directory,input_sha=digest)
    snapshot=read_snapshot(directory,input_sha=digest,receipts=records)
    cli=json.loads((directory/"cli-stage-projection.json").read_bytes())
    web,building,report=projection_trace(directory,base_id)
    packet=g5_contract(json.loads(raw),snapshot,records,cli,web,building,report)
    compare_or_seal(directory/"g5-contract.json",packet,seal)
    record=verification(directory,packet,snapshot)
    compare_or_seal(directory/"g5-verification.json",record,seal)
    return record


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run",type=Path)
    parser.add_argument("--source-run",default="RUN-3bb6a4d5d57c4af8af503a20c4d69bbd")
    parser.add_argument("--seal",action="store_true")
    options=parser.parse_args()
    record=verify(options.run.resolve(),options.source_run,options.seal)
    print(json.dumps(record,indent=2))
    raise SystemExit(int(not all(row["closure_ready"] for row in record["gaps"].values())))
