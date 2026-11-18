#!/usr/bin/env python3
"""Validate the delivery contracts and optional pinned source symbols.

This is documentation/integrity validation, not an engineering check runner.
Requires jsonschema. No production module is imported and no ETABS is attached.
"""
from __future__ import annotations
import argparse, ast, copy, hashlib, json, platform, re, sys
from pathlib import Path
from datetime import datetime, timezone
import jsonschema

def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value): return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def semantics(mapping,bank,manifest,chain):
    errors=[]
    def require(ok,msg):
        if not ok: errors.append(msg)
    ids=[r['check_id'] for r in mapping['checks']]
    require(len(ids)==73 and len(set(ids))==73,'Exactly73distinct original recipe identities are required.')
    require(ids==bank['primary_check_ids'],'Mapping and golden primary identities/order differ.')
    require('CHK-008' not in ids,'CHK-008 is not in the preserved identity catalogue.')
    cases=bank['cases']; cids=[c['case_id'] for c in cases]
    require(len(cids)==85 and len(set(cids))==85,'Exactly85distinct frozen case IDs are required.')
    primary=[c for c in cases if c['population']=='PRIMARY_CHECK_EXAMPLE']
    require(len(primary)==73 and {c['check_id'] for c in primary}==set(ids),'The73primary examples do not cover the73identities one-to-one.')
    require(sum(len(c['assertions']) for c in cases)==333,'Frozen recipe assertion population is not333.')
    source_by_id={s['source_id']:s for s in manifest['golden_sources']}
    file_by_path={s['path']:s for s in manifest['repository_files']}
    source_commit=manifest['review_boundary']['reviewed_remote_commit']
    require(bool(re.fullmatch('[0-9a-f]{40}',source_commit)),'Reviewed commit must be a full40-character SHA.')
    require(manifest['review_boundary']['local_worktree']=='NOT_INSPECTED','Unavailable local tree must remain NOT_INSPECTED.')
    all_assertions=set()
    for c in cases:
        aid=[a['assertion_id'] for a in c['assertions']]
        require(len(aid)==len(set(aid)) and not (all_assertions & set(aid)),c['case_id']+': duplicate assertion identity.')
        all_assertions.update(aid)
        require(set(c['scenario_coverage'])=={'positive','negative','boundary','missing_source'},c['case_id']+': missing scenario category.')
        for scenario in c['scenario_coverage'].values():
            require(set(scenario['assertion_refs'])<=set(aid),c['case_id']+': unknown scenario assertion reference.')
        for a in c['assertions']:
            require(a['formula_is_executable'] is False,c['case_id']+': formula text cannot be executable.')
            t=a['tolerance'];require(t['absolute']>=0 and t['relative']>=0 and bool(t['rationale']),c['case_id']+': invalid tolerance.')
        require(c['frozen_input_sha256']==canonical({'case_id':c['case_id'],'inputs':c['inputs'],'fixture':c['fixture']}),c['case_id']+': frozen input digest mismatch.')
        require(c['case_sha256']==canonical({k:v for k,v in c.items() if k!='case_sha256'}),c['case_id']+': complete case digest mismatch.')
        for r in c['source_references']:
            require(r['source_id'] in source_by_id,c['case_id']+': unknown source ID.')
            if r['source_id'] in source_by_id:require(r['sha256']==source_by_id[r['source_id']]['sha256'],c['case_id']+': source SHA mismatch.')
            for page in r['atlas_pages'] or []:
                matches=[p for p in manifest['atlas']['page_mappings'] if p['atlas_page']==page and p['source_id']==r['source_id'] and p['pdf_page'] in (r['original_pdf_pages'] or [])]
                require(bool(matches),c['case_id']+': atlas/source page link does not resolve.')
    for c in mapping['checks']:
        require(c['golden_example_id'] in cids,c['check_id']+': missing golden example.')
        local=c['current_local_binding']
        require(local['inspection_status']=='NOT_INSPECTED' and local['owner_mapping_status']=='UNMAPPED',c['check_id']+': unsupported local inspection claim.')
        binding=c['reviewed_snapshot_binding']
        require(binding['source_commit']==source_commit,c['check_id']+': owner snapshot identity differs.')
        require((bool(binding['owners']) and binding['mapping_status']=='MAPPED_PARTIAL') or (not binding['owners'] and binding['mapping_status']=='UNMAPPED'),c['check_id']+': mapping status and owner evidence disagree.')
        require(len(c['method_steps'])==3,c['check_id']+': original three-step contract changed.')
        for owner in binding['owners']+binding['related_source_functions']:
            f=file_by_path.get(owner['path'])
            require(f is not None,c['check_id']+': owner file missing from source manifest.')
            if f:
                require(owner['file_sha256']==f['sha256'] and owner['source_commit']==f['source_commit'],c['check_id']+': owner source identity mismatch.')
    require(set(chain['related_check_ids'])<=set(ids),'Priority chain references unknown recipe IDs.')
    public_source_ids={r['source_id'] for r in manifest['public_references']}
    for r in chain['source_refs']:
        sid=manifest.get('source_id_aliases',{}).get(r['source_id'],r['source_id'])
        require(sid in source_by_id or sid in public_source_ids,'Priority chain source reference does not resolve: '+sid)
        if sid in source_by_id:require(r['sha256']==source_by_id[sid]['sha256'],'Priority chain normative source digest differs.')
    require(chain['local_code_review_status']=='NOT_INSPECTED','Priority chain has an unsupported local review claim.')
    require(manifest['atlas']['total_pages']==42 and len(manifest['atlas']['page_mappings'])==39,'Atlas population differs from preserved original.')
    return errors

def source_symbols(mapping,manifest,repo):
    errors=[];checked=set();tree_cache={}
    for f in manifest['repository_files']:
        p=repo/f['path']
        if not p.is_file() or sha(p)!=f['sha256']:errors.append('Source bytes differ: '+f['path'])
    for c in mapping['checks']:
        b=c['reviewed_snapshot_binding']
        for o in b['owners']+b['related_source_functions']:
            key=(o['path'],o['symbol'])
            if key in checked:continue
            checked.add(key);path=repo/o['path']
            if not path.exists():continue
            tree=tree_cache.setdefault(o['path'],ast.parse(path.read_text(encoding='utf-8')))
            nodes=tree.body;found=None
            for name in o['symbol'].split('.'):
                found=next((n for n in nodes if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name),None)
                if found is None:break
                nodes=found.body
            if found is None:errors.append('Source symbol missing: '+str(key))
            elif found.lineno!=o['line_start'] or found.end_lineno!=o['line_end']:errors.append('Source symbol span differs: '+str(key))
    return errors,len(checked)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--repo',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--self-test',action='store_true')
    args=p.parse_args();root=args.root.resolve();errors=[];schema_results=[]
    for sp in sorted((root/'schemas').glob('*.schema.json')):
        target=root/(sp.name.replace('.schema.json','.json'))
        if not target.exists():errors.append('Schema target missing: '+target.name);continue
        schema=read(sp);jsonschema.Draft202012Validator.check_schema(schema)
        e=list(jsonschema.Draft202012Validator(schema).iter_errors(read(target)))
        errors.extend(target.name+': '+x.message for x in e)
        schema_results.append({'file':target.name,'file_sha256':None if target.name=='VERIFICATION_RESULTS.json' else sha(target),'digest_note':'The verification ledger references this validation record; its final digest is bound by DELIVERY_INDEX.json to avoid a self-referential hash cycle.' if target.name=='VERIFICATION_RESULTS.json' else 'Exact validated bytes.','schema':sp.name,'schema_sha256':sha(sp),'status':'VALID' if not e else 'INVALID'})
    mapping=read(root/'CHECK_MAPPING.json');bank=read(root/'GOLDEN_CASES.json');manifest=read(root/'SOURCE_MANIFEST.json');chain=read(root/'PRIORITY_CHAIN.json')
    errors.extend(semantics(mapping,bank,manifest,chain))
    symbols=None
    if args.repo:
        err,symbols=source_symbols(mapping,manifest,args.repo.resolve());errors.extend(err)
    static=[]
    for path in sorted((root/'tools').glob('*.py')):
        tree=ast.parse(path.read_text());bad=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {'eval','exec','compile'}:bad.append(node.lineno)
        if bad:errors.append(path.name+': dynamic expression execution found.')
        static.append({'file':'tools/'+path.name,'sha256':sha(path),'dynamic_formula_execution_calls':bad})
    privacy=[]
    for path in root.rglob('*'):
        if path.resolve()==Path(__file__).resolve():continue
        if path.is_file() and path.suffix in {'.md','.json','.py','.txt'}:
            text=path.read_text(encoding='utf-8')
            if re.search(r'https?://(?:drive\.google\.com|docs\.google\.com|github\.com/feridunfc)|C:[/\\]Users[/\\]|oai-library://|library-file:',text):privacy.append(str(path.relative_to(root)))
    if privacy:errors.append('Private access locations in public files: '+str(privacy))
    negatives=[]
    if args.self_test:
        trials=[]
        b=copy.deepcopy(bank);b['cases'][0]['source_references'][0]['sha256']='0'*64;trials.append(('changed_source_hash',mapping,b,manifest,chain))
        m=copy.deepcopy(mapping);m['checks'].pop();trials.append(('missing_original_id',m,bank,manifest,chain))
        b=copy.deepcopy(bank);b['cases'][1]['case_id']=b['cases'][0]['case_id'];trials.append(('duplicate_case_id',mapping,b,manifest,chain))
        b=copy.deepcopy(bank);b['cases'][0]['assertions'][0]['formula_is_executable']=True;trials.append(('executable_formula_flag',mapping,b,manifest,chain))
        m=copy.deepcopy(mapping);m['checks'][0]['current_local_binding']['inspection_status']='INSPECTED';trials.append(('unsupported_local_inspection',m,bank,manifest,chain))
        b=copy.deepcopy(bank);b['cases'][0]['scenario_coverage'].pop('missing_source');trials.append(('omitted_scenario_category',mapping,b,manifest,chain))
        for name,*objects in trials:
            detected=bool(semantics(*objects));negatives.append({'scenario':name,'detected':detected})
            if not detected:errors.append('Negative contract probe not detected: '+name)
    result={'schema_version':'yeni.integration.delivery-validation.v1','verification_level':'DOCUMENT_SCHEMA_CONSISTENCY','status':'VALID' if not errors else 'INVALID','executed_at_utc':datetime.now(timezone.utc).isoformat(),'command':[Path(sys.executable).name,*sys.argv],'environment':{'python':platform.python_version(),'platform':platform.platform(),'jsonschema':__import__('importlib.metadata',fromlist=['version']).version('jsonschema')},'validator_sha256':sha(Path(__file__)),'schemas':schema_results,'reviewed_source_files':len(manifest['repository_files']) if args.repo else 0,'distinct_source_symbols_verified':symbols,'source_symbol_check_status':'VERIFIED' if args.repo else 'NOT_RUN','negative_contract_probes':negatives,'static_tool_checks':static,'private_access_leaks':privacy,'errors':errors,'limits':['Documentation, schema, identity and optional source-symbol validation only.','No structural result or normative applicability is accepted.','No production pipeline or ETABS session is executed.','Unavailable local commit and unfinished changes remain NOT_INSPECTED.']}
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','reviewed_source_files','distinct_source_symbols_verified','errors']},indent=2))
    return 0 if not errors else 1

if __name__=='__main__':raise SystemExit(main())
