"""One-shot read-only live-receipt/JSON/HTML acceptance for bounded VS05."""
from __future__ import annotations

import argparse
from pathlib import Path
from tbdy_next.reporting import build_complete_report, build_printable_html


def verify(root: Path, run_id: str) -> dict:
    r = build_complete_report(root, run_id)
    d = r.get('story_drift')
    assert isinstance(d, dict), 'STORY_DRIFT_NOT_IN_REPORT'
    assert d.get('check_id') == 'STORY_DRIFT', 'WRONG_CHECK_ID'
    assert d.get('dag_node_id') == 'STORY_DRIFT', 'WRONG_DAG_BINDING'
    assert d.get('execution_status') == 'EXECUTED_SOURCE_NUMERICAL', 'NUMERIC_NOT_EXECUTED'
    assert d.get('dag_execution_authority') == 'DENIED', 'UNSAFE_DAG_AUTHORITY'
    assert d.get('formal_compliance') == 'NOT_PROVEN', 'UNSAFE_FORMAL_STATUS'
    assert d.get('engineering_release') == 'NOT_READY', 'UNSAFE_RELEASE_STATUS'
    assert r.get('formal_compliance') == 'NOT_PROVEN', 'UNSAFE_REPORT_FORMAL_STATUS'
    assert r.get('engineering_release') == 'NOT_READY', 'UNSAFE_REPORT_RELEASE_STATUS'
    inv = r['check_inventory']
    ids = [x['check_id'] for x in inv['entries']]
    assert inv['count'] == len(ids) == len(set(ids)), 'CHECK_INVENTORY_CONFLICT'
    assert ids.count('STORY_DRIFT') == 1, 'STORY_DRIFT_NOT_IN_INVENTORY'
    assert len(d['items']) == d['evaluated_story_case_direction_count'], 'STORY_DRIFT_COUNT_MISMATCH'
    assert len(d['items'])+len(d['missing_story_case_direction']) == d['expected_story_case_direction_count'], 'STORY_DRIFT_COVERAGE_MISMATCH'
    assert any(x['story'] == '+14.5' for x in d['missing_story_case_direction']), 'TOP_STORY_OMITTED'
    assert not d.get('numerical_pass_issued'), 'UNSAFE_NUMERIC_PASS'
    html = build_printable_html(r)
    assert 'STORY_DRIFT' in html and 'NUMERIC_SOURCE_PARTIAL_STORY_COVERAGE' in html, 'HTML_NOT_UPDATED'
    assert '+14.5' in html and 'NOT_PROVEN' in html, 'HTML_MISSING_SCOPE_WARNING'
    return {'status':'VS05_SOURCE_NUMERICAL_RELEASE_ACCEPTANCE',
            'run_id':run_id,'check_count':inv['count'],
            'evaluated':d['evaluated_story_case_direction_count'],
            'expected':d['expected_story_case_direction_count'],
            'missing':len(d['missing_story_case_direction']),
            'formal_compliance':'NOT_PROVEN','engineering_release':'NOT_READY',
            'report_html_bytes':len(html.encode('utf-8'))}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path('.receipts'))
    p.add_argument('--run-id',default='RUN-e4a5376365c649b6b7469b0a778617ff')
    args=p.parse_args()
    result=verify(args.root,args.run_id)
    for key,value in result.items(): print(f'{key}: {value}')

if __name__=='__main__':main()
