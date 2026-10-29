"""Explicit, deterministic, fail-closed execution of ONE bounded pure operation.
No network, shell, arbitrary file paths, deletion, subprocesses or callbacks.
The operation computes SHA-256 over the exact verified evaluation evidence bundle.
A successful operation is recorded only afterwards, inside an append-only transaction.
"""
import base64
from governance_store import canonical,strict_loads,sha,stamp,now,RECORD_AUTHORITY_ROLES
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
import material_change as mc
from invariant_guards import evidence_problem,control_problem
OPERATION='EVIDENCE_DIGEST_V1'
MAX_BYTES=1048576
MAX_REQUEST_SECONDS=300
MAX_CHAIN_SECONDS=3600
# Every prerequisite slot declares its exact persisted type and lifecycle state.
# No catch-all role: unknown slots/types fail closed before signature verification.
PREREQUISITE_RECORDS={
    'evaluation': ('ADMISSIBILITY_EVALUATION', None),
    'decision': ('GOVERNANCE_DECISION', None),
    'approval': ('LIFECYCLE_ATTESTATION', 'APPROVED'),
    'active': ('LIFECYCLE_ATTESTATION', 'ACTIVE'),
}
SCOPE_KEYS={'operation','evidence_bundle_sha256','parameters_sha256'}
REQUEST_KEYS={'record_type','record_id','subject_id','original_assessment_id','original_assessment_sha256','original_assessment_effect','subject_version_id','subject_version_record_sha256','subject_snapshot_sha256','evaluation_id','evaluation_record_sha256','decision_id','decision_record_sha256','approval_id','approval_record_sha256','active_id','active_record_sha256','evidence_bundle_sha256','operation','parameters','parameters_sha256','ledger_head_sha256','key_id','actor_id','issued_at','expires_at','rationale'}
def validate_scope(scope):
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS or scope['operation']!=OPERATION or scope['parameters_sha256']!=sha(canonical({})): raise ValueError('Only the exact empty-parameter EVIDENCE_DIGEST_V1 scope is allow-listed.')
    value=scope['evidence_bundle_sha256']
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value): raise ValueError('Scope requires exact lowercase evidence bundle SHA-256.')
    return scope

def verify_envelope(document,policy,role,current):
    if not isinstance(document,dict) or set(document)!={'payload','signature_base64'}: raise ValueError('A signed payload/signature envelope is required.')
    p=document['payload']
    if not isinstance(p,dict): raise ValueError('Signed payload must be an object.')
    key=next((k for k in policy['keys'] if k['key_id']==p.get('key_id') and k['actor_id']==p.get('actor_id') and role in k['roles']),None)
    if not key: raise ValueError('Signer lacks the required pinned subject-policy role: '+role)
    issued=stamp(p['issued_at'])
    if not stamp(key['not_before'])<=issued<=current<=stamp(key['not_after']): raise ValueError('Authority is expired, not yet valid, or request time is invalid.')
    Ed25519PublicKey.from_public_bytes(base64.b64decode(key['public_key_base64'],validate=True)).verify(base64.b64decode(document['signature_base64'],validate=True),canonical(p))
    if control_problem(p): raise ValueError(control_problem(p))
    return p

def verify_prerequisite(name,row_type,document,policy,current):
    if name not in PREREQUISITE_RECORDS: raise ValueError('Unknown execution prerequisite slot.')
    expected_type,expected_state=PREREQUISITE_RECORDS[name]
    if row_type!=expected_type or not isinstance(document,dict) or not isinstance(document.get('payload'),dict) or document['payload'].get('record_type')!=expected_type:
        raise ValueError('Wrong record type for '+name+'; requires '+expected_type)
    p=verify_envelope(document,policy,RECORD_AUTHORITY_ROLES[expected_type],current)
    if expected_state is not None and p.get('state')!=expected_state: raise ValueError('Wrong lifecycle state for '+name+'; requires '+expected_state)
    return p

def perform_operation(operation,parameters,evidence):
    """Real pure computation; never accepts an executable, path, URL, or function."""
    if operation!=OPERATION or type(parameters) is not dict or parameters: raise ValueError('Operation/parameters are not allow-listed.')
    raw=canonical(evidence)
    if not raw or len(raw)>MAX_BYTES: raise ValueError('Evidence operation exceeds the bounded input size.')
    # This is the allow-listed governed operation, not a simulated success flag.
    result={'operation':OPERATION,'evidence_digest_sha256':sha(raw),'byte_count':len(raw)}
    return result

def receipt_valid(event,evaluation,decision):
    try:
        evidence=evaluation['evidence']; scope=validate_scope(decision['controlled_operation_scope'])
        if evidence_problem(evaluation) or scope['evidence_bundle_sha256']!=sha(canonical(evidence)): return False
        result=perform_operation(event['operation'],event['parameters'],evidence)
        return event['operation_result']==result and event['operation_result_sha256']==sha(canonical(result)) and event['evidence_bundle_sha256']==scope['evidence_bundle_sha256'] and event['completed_at']>=event['started_at'] and event['explicit_invocation'] is True and event['automatic_execution_allowed'] is False
    except Exception: return False

def execute_explicit(s,original_id,envelope):
    """Only explicit calls enter here; no ingest, detection or result callback invokes it."""
    s.verify()
    if len(canonical(envelope))>MAX_BYTES: raise ValueError('Execution request too large.')
    s.db.execute('BEGIN IMMEDIATE')
    try:
        s.verify(); original=s._original(original_id); subject=original['subject_id']; current=stamp(now())
        policy,_=s._policy(subject); request=verify_envelope(envelope,policy,RECORD_AUTHORITY_ROLES['CONTROLLED_EXECUTION_REQUEST'],current)
        if set(request)!=REQUEST_KEYS or request['record_type']!='CONTROLLED_EXECUTION_REQUEST': raise ValueError('Execution requires the complete exact request schema; extra operative fields are forbidden.')
        if not isinstance(request['record_id'],str) or not request['record_id'].strip() or s.db.execute('SELECT 1 FROM events WHERE record_id=?',(request['record_id'],)).fetchone(): raise ValueError('Missing or replayed request ID.')
        issued=stamp(request['issued_at']); expires=stamp(request['expires_at'])
        if not issued<=current<expires or not 0<(expires-issued).total_seconds()<=MAX_REQUEST_SECONDS: raise ValueError('Execution request is stale or has an excessive validity window.')
        if request['subject_id']!=subject or request['original_assessment_id']!=original_id or request['original_assessment_sha256']!=original['payload_sha256'] or request['original_assessment_effect']!='UNCHANGED': raise ValueError('Exact subject/original binding required; originals remain unchanged.')
        if mc.latest_original(s,subject)['record_id']!=original_id: raise ValueError('A newer subject assessment exists.')
        if request['ledger_head_sha256']!=s.all()[-1]['event_sha256']: raise ValueError('The ledger changed after request preparation; submit a fresh request.')
        if any(request[k]!=v for k,v in mc.binding(s,subject).items()): raise ValueError('Changed or incomplete subject-version binding.')
        state=mc.status(s,subject)
        if state['current_admissibility_state']!='ADMISSIBLE' or state['reevaluation_required'] or not state['evidence_verified'] or not state['new_admissibility_and_authorised_decision_present'] or state['lifecycle_state']!='ACTIVE' or not state['approval_current']: raise ValueError('Current evidenced ADMISSIBLE evaluation, authorised decision and valid APPROVED/ACTIVE chain are mandatory.')
        expected={'evaluation_id':state['latest_evaluation_id'],'evaluation_record_sha256':state['latest_evaluation_sha256'],'decision_id':state['latest_decision_id'],'decision_record_sha256':state['latest_decision_sha256'],'approval_id':state['approval_record_id'],'active_id':state['recorded_lifecycle_record_id']}
        if any(request[k]!=v for k,v in expected.items()): raise ValueError('Stale or incomplete evaluation/decision/approval/ACTIVE request binding.')
        rows={name:s.get(request[name+'_id']) for name in ['evaluation','decision','approval','active']}
        payloads={}
        for name,row in rows.items():
            if row['subject_id']!=subject or row['original_id']!=original_id or row['payload_sha256']!=request[name+'_record_sha256']: raise ValueError('Exact trace ID/hash/subject binding failed: '+name)
            if len(bytes(row['payload']))>MAX_BYTES: raise ValueError('Bounded execution record size exceeded.')
            doc=strict_loads(bytes(row['payload']).decode('utf-8')); p=verify_prerequisite(name,row['record_type'],doc,policy,current)
            if any(p.get(k)!=v for k,v in mc.binding(s,subject).items()): raise ValueError('Referenced authority belongs to a changed version.')
            if not 0<=(current-stamp(p['issued_at'])).total_seconds()<=MAX_CHAIN_SECONDS: raise ValueError('Referenced evaluation/authority is stale; fresh evidence and approvals required.')
            payloads[name]=p
        ep,dp=payloads['evaluation'],payloads['decision']
        if ep.get('result')!='ADMISSIBLE' or ep.get('evidence_sufficient') is not True or evidence_problem(ep): raise ValueError('Missing, changed, insufficient or invalid evaluation evidence.')
        if dp.get('effect')!='AUTHORISE_EXECUTION' or dp.get('evaluation_id')!=rows['evaluation']['record_id'] or dp.get('evaluation_record_sha256')!=rows['evaluation']['payload_sha256']: raise ValueError('A separate exact evaluation-bound authorised decision is required.')
        if not rows['evaluation']['seq']<rows['decision']['seq']<rows['approval']['seq']<rows['active']['seq'] or issued<=stamp(rows['active']['recorded_at']): raise ValueError('Evaluation, decision, approval, ACTIVE and explicit request ordering invalid.')
        if payloads['approval'].get('state')!='APPROVED' or payloads['active'].get('state')!='ACTIVE': raise ValueError('Explicit lifecycle states required.')
        for name in ['approval','active']:
            if any(payloads[name].get(k)!=request[k] for k in ['evaluation_id','evaluation_record_sha256','decision_id','decision_record_sha256']): raise ValueError('Lifecycle proof binds a different evaluation or decision.')
        scope=validate_scope(dp.get('controlled_operation_scope'))
        if request['operation']!=scope['operation'] or request['evidence_bundle_sha256']!=scope['evidence_bundle_sha256'] or request['parameters_sha256']!=scope['parameters_sha256'] or request['parameters_sha256']!=sha(canonical(request['parameters'])) or scope['evidence_bundle_sha256']!=sha(canonical(ep['evidence'])): raise ValueError('Operation/evidence/parameters differ from independently signed decision scope.')
        for row in s.all():
            if row['record_type']=='EXECUTION_EVENT' and strict_loads(bytes(row['payload']).decode('utf-8')).get('decision_id')==request['decision_id']: raise ValueError('Execution decision already consumed; replay forbidden.')
        started=now()
        result=perform_operation(request['operation'],request['parameters'],ep['evidence'])
        completed=now()
        event={**{k:request[k] for k in ['record_id','subject_id','original_assessment_id','original_assessment_sha256','subject_version_id','subject_version_record_sha256','subject_snapshot_sha256','evaluation_id','evaluation_record_sha256','decision_id','decision_record_sha256','approval_id','approval_record_sha256','active_id','active_record_sha256','evidence_bundle_sha256','operation','parameters','parameters_sha256']},'record_type':'EXECUTION_EVENT','request_envelope':envelope,'started_at':started,'completed_at':completed,'operation_result':result,'operation_result_sha256':sha(canonical(result)),'explicit_invocation':True,'automatic_execution_allowed':False,'governance_authority_granted':False,'regulatory_precedence_resolved':False,'original_assessment_effect':'UNCHANGED','evaluation_result':'ADMISSIBLE','evidence_sufficient':True,'authorised_decision':True}
        if not receipt_valid(event,ep,dp): raise ValueError('Operation receipt verification failed; no success event appended.')
        s._append(event['record_id'],'EXECUTION_EVENT',subject,original_id,canonical(event)); s.db.commit()
        return event
    except Exception:
        s.db.rollback(); raise
