"""New immutable remediation report; never replaces the earlier final audit."""
import json,os,uuid
from governance_store import now,sha,RECORD_AUTHORITY_ROLES
CHANGES={
'ABOUT.md':('modified','Documents the distinct operator role, explicit prerequisite mapping and fail-closed treatment of existing pinned policies.'),
'controlled_execution.py':('modified','Requires EXECUTION_OPERATOR for invocation; verifies every prerequisite with explicit expected record type, role and lifecycle state, without a generic fallback.'),
'governance_store.py':('modified','Adds the distinct pinned operator role and shared exhaustive record-role map; operator authority never implies governance or evaluator authority.'),
'cl3_suite.py':('modified','Uses separate evaluator, governor and operator keys; trace validation enforces the explicit role map. All 26 criteria and applicability obligations retained.'),
'execution_tests.py':('modified','Retains all 23 execution regressions and adds 14 role/type negatives, with no-operation/no-event/full-ledger-preservation assertions.'),
'remediation_report.py':('modified','Reports this authority-separation review, its exact changed files, role map, measured outcomes and unchanged-history evidence.'),
'notebook.ipynb':('modified','Requires the full 37-check execution regression set and operator-role mapping, then reruns all 26 mandatory tests and existing regressions.'),
'src/ControlledExecutionLayer.tsx':('modified','Explains mandatory operator-role invocation separately from governance decision and lifecycle prerequisites; old policies never gain permissions.'),
'src/GovernanceLayer.tsx':('modified','Provides three single-role key templates and documents the explicit governance/lifecycle mapping and no implicit operator permission.')} 

def write(appdir,outdir,conformity,execution_checks,contract_checks,material_checks,invariant_checks,preservation,semantic_report=None):
    rid='cl3-remediation-'+str(uuid.uuid4())
    files=[]
    for name,(change,summary) in CHANGES.items():
        with open(os.path.join(appdir,name),'rb') as f: digest=sha(f.read())
        files.append({'path':name,'change':change,'summary':summary,'sha256':digest})
    full=conformity['overall_result']=='PASS' and len(conformity['results'])==26 and all(r['evaluation_result']=='PASS' and r['mandatory'] is True and r['applicable'] is True and r['evidence_references'] for r in conformity['results']) and conformity['evidence_provenance_verified']
    limits=[
    'Scope is the frozen local CR-11–CR-15/Annex A suite, not independent certification or inherited CL-1/CL-2 conformity.',
    'Only EVIDENCE_DIGEST_V1 is implemented: an actual SHA-256 computation over verified canonical evidence (at most 1 MiB); no arbitrary external/business execution is claimed.',
    'Initial signed registration is CREATED or terminal REJECTED only, before any governed lifecycle history. REJECTED has no edge in the frozen §7.1 matrix; no edge is invented. All 110 distinct-state transitions use independent valid fixtures.',
    'Recorded lifecycle identity is distinct from a safety suspension. MODIFIED is preserved while its changed version is blocked pending fresh evaluation; it is not relabelled ADMISSIBLE or ACTIVE.',
    'Authority is a workspace-user-provisioned pinned Ed25519 policy, not independent institutional identity. Key expiry is enforced; rotation/revocation infrastructure remains outside scope.',
    'EXECUTION_OPERATOR is an explicit local technical permission, not a new normative SSA entity. It implies no evaluator/governance/lifecycle permission. Lifecycle registration and APPROVED/ACTIVE attestations explicitly require GOVERNANCE_DECISION as §7 governance acts; no generic fallback is used.',
    'Role separation is checked by explicit policy grants, not inferred identity. The regression fixtures use separate single-role keys. Existing pinned policies without EXECUTION_OPERATOR remain blocked; there is no silent migration or policy replacement.',
    'Four runtime prerequisite-role negative probes inject wrong-role signed envelopes at the verification seam, without altering stored rows or policies. They prove each verification gate aborts before the operation or any event.',
    'Request expiry is at most 300 seconds; evaluation/decision/lifecycle authority age at execution is at most 3600 seconds. Fresh exact version/evidence/approval and current ledger-head bindings are mandatory.',
    'A successful decision is single-use for this operation; repeat execution needs a new explicitly scoped decision, approval/ACTIVE proof and signed request.',
    'Operation and event are processed under a ledger write lock. A process/storage failure after pure computation but before commit may leave an unrecorded computation, never a false success event; no external side-effect exactly-once guarantee is claimed.',
    'SQLite/hash-chain guards provide application-level preservation, not certified WORM storage or protection from an administrator replacing code/storage.',
    'Conformity probes explicitly execute fabricated, isolated fixtures only. Results, detection, escalation, resolution and decision imports never trigger production execution.'
    ]
    d={'report_id':rid,'created_at':now(),'review_status':'FOR_USER_REVIEW','change_scope':'Explicit execution authority separation','record_authority_roles':RECORD_AUTHORITY_ROLES,'invariant':'representation != resolution != decision authority','scoped_26_test_result':'PASS' if full else 'FAIL','full_cl3_certification_claimed':False,'conformity_report_id':conformity['report_id'],'source_run_id':conformity['source_run_id'],'files':files,'results':conformity['results'],'execution_regressions':execution_checks,'cr14_regressions':contract_checks,'cr15_regressions':material_checks,'invariant_regressions':invariant_checks,'scientific_interoperability':semantic_report,'preservation':preservation,'limitations':limits,'evidence_package':conformity['exports'],'automatic_execution_allowed':False,'governance_authority_granted':False,'regulatory_precedence_resolved':False}
    with open(os.path.join(outdir,rid+'.json'),'x',encoding='utf-8') as f: json.dump(d,f,ensure_ascii=False,indent=2)
    lines=['# Authority-separation review results','',f"Recorded: {d['created_at']}",f"\nScoped 26-test result: **{d['scoped_26_test_result']}**. Full CL-3 certification is not claimed.",f"\nConformity report: `{conformity['report_id']}`; evidence run: `{conformity['source_run_id']}`.",'','## Explicit pinned-policy role mapping','','| Signed record | Required role |','|---|---|']+[f'| {kind} | {role} |' for kind,role in RECORD_AUTHORITY_ROLES.items()]+['','APPROVED and ACTIVE must be LIFECYCLE_ATTESTATION records with the exact corresponding state; neither is inferred from a decision. The separately signed evaluation-bound governance decision remains mandatory. These are local implementation permissions consistent with §7 governance acts, not new normative SSA entities. Existing pinned policies are unchanged.','','## Exact files modified in this review','','Paths below are relative to `user/apps/ssaAntinomyConflictAnalyzer/`. Earlier remediation reports remain immutable historical results.','']
    lines += [f"- `{x['path']}` — **{x['change']}**: {x['summary']} SHA-256: `{x['sha256']}`." for x in files]
    lines+=['','## Complete mandatory results and evidence','', '| Test ID | Requirement | Result | Evidence reference | SHA-256 |','|---|---|---|---|---|']
    for r in conformity['results']:
        refs=r['evidence_references']; lines.append('| '+r['test_id']+' | '+r['title']+' | '+r['evaluation_result']+' | '+('; '.join(x['reference'] for x in refs))+' | '+('; '.join(str(x['sha256']) for x in refs))+' |')
    lines+=['','Evidence locators resolve to the per-test JSON artifacts in the linked conformity ZIP (`evidence/<test ID>.json`); the evidence bundle retains exact run-bound content. Lifecycle coverage/matrix artifacts include each independent signed fixture trace. Execution PASS requires an actual completed operation and linked ledger event, not a documentary flag.','', '## Regression results','']
    for group,checks in [('CR-14 existing',contract_checks),('CR-15 existing',material_checks),('Invariant existing',invariant_checks),('Controlled execution positive/negative',execution_checks)]:
        lines.append(f"### {group}: {sum(c['status']=='PASS' for c in checks)}/{len(checks)} PASS")
        for c in checks: lines.append('- '+str(c.get('check',c.get('name')))+' — '+c['status']+(' — '+c['reason'] if c.get('reason') else ''))
    if semantic_report:
        lines+=['','### Scientific interoperability: '+str(sum(c['pass'] for c in semantic_report['synthetic_checks']))+'/'+str(len(semantic_report['synthetic_checks']))+' PASS','Evidence manifest/export: `'+semantic_report['export_id']+'`; independent mapped-field reconstruction and SHACL 1.0 validation retained.']
        lines+=['- '+c['test']+' — '+('PASS' if c['pass'] else 'FAIL') for c in semantic_report['synthetic_checks']]
    lines+=['','## Preservation','',json.dumps(preservation,ensure_ascii=False,indent=2),'','Prior audits, evaluations and governance records are retained unchanged. This is a new report, not a revised historical evaluation.','','## Remaining failures','']
    failures=[r for r in conformity['results'] if r['evaluation_result']!='PASS']
    lines+= [r['test_id']+': '+r['traceable_reason'] for r in failures] if failures else ['None in this scoped 26-test run.']
    lines+=['','## Limitations','']+['- '+v for v in limits]
    with open(os.path.join(outdir,rid+'.md'),'x',encoding='utf-8') as f: f.write('\n'.join(lines)+'\n')
    with open(os.path.join(outdir,'cl3_remediation_latest.json'),'w',encoding='utf-8') as f: json.dump({'report_id':rid,'result':d['scoped_26_test_result'],'exports':[rid+'.md',rid+'.json'],'conformity_exports':conformity['exports']},f,indent=2)
    return d
