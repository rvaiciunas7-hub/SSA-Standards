"""CR-14 scoped append-only governance records; no execution capability."""
import base64
import copy
import datetime as dt
import hashlib
import json
import os
import sqlite3
import uuid
import zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SPEC = 'SSA-RM-1 v1.1 §9.14 CR-14 (23 October 2026), pp. 7, 9, 11, 14'
STATES = {'ADMISSIBLE','NON_ADMISSIBLE','CONDITIONAL','SUSPENDED','REGULATORY_ANTINOMY'}
# Local pinned-policy implementation roles, not new normative SSA entities.
# Lifecycle approval/activation remain explicit governance-authority acts (§7).
RECORD_AUTHORITY_ROLES = {
    'ADMISSIBILITY_EVALUATION': 'ADMISSIBILITY_EVALUATION',
    'GOVERNANCE_DECISION': 'GOVERNANCE_DECISION',
    'LIFECYCLE_REGISTRATION': 'GOVERNANCE_DECISION',
    'LIFECYCLE_ATTESTATION': 'GOVERNANCE_DECISION',
    'CONTROLLED_EXECUTION_REQUEST': 'EXECUTION_OPERATOR',
}
POLICY_ROLES = frozenset(RECORD_AUTHORITY_ROLES.values())
def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
def stamp(s):
    if not isinstance(s,str): raise ValueError('A UTC timestamp is required.')
    t = dt.datetime.fromisoformat(s.replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('Timestamps must include a timezone.')
    return t.astimezone(dt.timezone.utc)
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(d):
    def check(x):
        if isinstance(x,float): raise ValueError('Signed documents must not contain floating-point numbers.')
        if isinstance(x,dict):
            for v in x.values(): check(v)
        elif isinstance(x,list):
            for v in x: check(v)
    check(d)
    return json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def strict_loads(s):
    def pairs(items):
        d = {}
        for k,v in items:
            if k in d: raise ValueError('Duplicate JSON key: '+k)
            d[k] = v
        return d
    return json.loads(s,object_pairs_hook=pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Non-finite JSON is not accepted.')))
def required(d,*keys):
    for k in keys:
        if not isinstance(d.get(k),str) or not d[k].strip(): raise ValueError('Required non-empty field: '+k)

class GovernanceStore:
    def __init__(self,appdir,outdir):
        self.outdir = outdir
        folder = os.path.join(appdir,'records')
        os.makedirs(folder,exist_ok=True)
        self.db = sqlite3.connect(os.path.join(folder,'governance.sqlite3'),timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT UNIQUE NOT NULL,
            record_type TEXT NOT NULL, subject_id TEXT, original_id TEXT,
            recorded_at TEXT NOT NULL, payload BLOB NOT NULL, payload_sha256 TEXT NOT NULL,
            previous_event_sha256 TEXT NOT NULL, event_sha256 TEXT NOT NULL);
          CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
            BEGIN SELECT RAISE(ABORT,'Governance records are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
            BEGIN SELECT RAISE(ABORT,'Governance records are append-only'); END;
        ''')
        self.verify()
        import material_change
        material_change.ensure_baselines(self)
    def all(self): return list(self.db.execute('SELECT * FROM events ORDER BY seq'))
    def get(self,rid):
        r = self.db.execute('SELECT * FROM events WHERE record_id=?',(rid,)).fetchone()
        if not r: raise ValueError('Unknown original/record identifier.')
        return r
    def verify(self):
        previous = '0'*64
        for r in self.all():
            if sha(bytes(r['payload'])) != r['payload_sha256'] or previous != r['previous_event_sha256']:
                raise ValueError('Governance ledger integrity check failed; execution remains blocked.')
            fields = {k:r[k] for k in ['record_id','record_type','subject_id','original_id','recorded_at','payload_sha256','previous_event_sha256']}
            if sha(canonical(fields)) != r['event_sha256']: raise ValueError('Governance event-chain verification failed.')
            previous = r['event_sha256']
        return True
    def _append(self,rid,kind,subject,original,payload):
        existing = self.db.execute('SELECT * FROM events WHERE record_id=?',(rid,)).fetchone()
        if existing:
            if bytes(existing['payload']) == payload and existing['record_type'] == kind: return existing
            raise ValueError('Record ID already exists. Existing records cannot be replaced or reinterpreted.')
        last = self.db.execute('SELECT event_sha256 FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        fields = dict(record_id=rid,record_type=kind,subject_id=subject,original_id=original,recorded_at=now(),payload_sha256=sha(payload),previous_event_sha256=last[0] if last else '0'*64)
        fields['event_sha256'] = sha(canonical(fields))
        self.db.execute('INSERT INTO events (record_id,record_type,subject_id,original_id,recorded_at,payload,payload_sha256,previous_event_sha256,event_sha256) VALUES (?,?,?,?,?,?,?,?,?)',tuple(fields[k] for k in ['record_id','record_type','subject_id','original_id','recorded_at'])+(payload,)+tuple(fields[k] for k in ['payload_sha256','previous_event_sha256','event_sha256']))
        return self.get(rid)
    def archive_legacy(self,path):
        if not os.path.isfile(path): return
        with open(path,'rb') as f: raw = f.read()
        d = strict_loads(raw.decode('utf-8'))
        if d.get('error'): return
        if d.get('assessment_id'):
            existing = self.db.execute('SELECT * FROM events WHERE record_id=?',(d['assessment_id'],)).fetchone()
            if existing and bytes(existing['payload']) != raw:
                # assessment.json is a convenience view; compare its parsed value to the immutable original.
                if strict_loads(bytes(existing['payload']).decode('utf-8')) != d: raise ValueError('Latest assessment differs from its immutable original; it cannot be used for governance.')
            if existing: return
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self._append('legacy-'+sha(raw),'LEGACY_SNAPSHOT',None,None,raw)
            self.db.commit()
        except Exception:
            self.db.rollback(); raise
    def record_assessment(self,d,subject):
        required({'subject_id':subject},'subject_id')
        original = copy.deepcopy(d)
        rid = 'assessment-'+str(uuid.uuid4())
        state = 'REGULATORY_ANTINOMY' if d.get('outcome_counts',{}).get('REGULATORY_ANTINOMY',0) else 'SUSPENDED'
        original.update(assessment_id=rid,subject_id=subject,created_at=now(),admissibility_result=state,admissibility_state=state+' — execution blocked; governance escalation required',governance_escalation_required=True,automatic_execution_allowed=False)
        original['admissibility_result_basis'] = 'Encoded regulatory antinomy detected.' if state == 'REGULATORY_ANTINOMY' else 'Conflict representation does not establish complete admissibility for execution; a full evaluation is outstanding.'
        import material_change
        self.db.execute('BEGIN IMMEDIATE')
        try:
            version,created = material_change.assessment_version(self,original,subject,rid)
            vd = material_change.decode(version)
            original.update(subject_version_id=vd['version_id'],subject_version_record_sha256=version['payload_sha256'],subject_snapshot_sha256=vd['snapshot_sha256'])
            payload = canonical(original)
            self._append(rid,'ORIGINAL_ASSESSMENT',subject,rid,payload)
            if not created:
                req = material_change.append_requirement(self,subject,rid,version,'A new blocking conflict assessment was recorded; it does not inherit an earlier complete evaluation.')
                material_change.suspend(self,subject,rid,version,'New blocking assessment requires a fresh evaluation before ACTIVE can be considered.',req['record_id'])
            escalation = {'escalation_id':'escalation-'+str(uuid.uuid4()),'record_type':'GOVERNANCE_ESCALATION','subject_id':subject,'original_assessment_id':rid,'original_assessment_sha256':sha(payload),'blocking_result':state,'created_at':now(),'trigger':'Automatic recording of blocking result, not automatic resolution','basis':SPEC,'original_result_effect':'UNCHANGED','execution_authorised':False,'automatic_execution_allowed':False,'new_evaluation_required':True,'authorised_governance_decision_required':True}
            self._append(escalation['escalation_id'],'GOVERNANCE_ESCALATION',subject,rid,canonical(escalation))
            self.db.commit()
        except Exception:
            self.db.rollback(); raise
        return original
    def _original(self,rid):
        r = self.get(rid)
        if r['record_type'] != 'ORIGINAL_ASSESSMENT': raise ValueError('Select a subject-identified original assessment. Legacy unassigned snapshots are read-only and cannot authorise a workflow.')
        return r
    def _policy(self,subject):
        row = self.db.execute("SELECT * FROM events WHERE record_type='TRUST_POLICY' AND subject_id=?",(subject,)).fetchone()
        if not row: raise ValueError('No pinned public-key authority policy for this subject; no document can be treated as authorised.')
        return strict_loads(bytes(row['payload']).decode('utf-8')),row
    def ingest(self,original_id,document):
        self.verify()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            original = self._original(original_id)
            subject = original['subject_id']
            if document.get('record_type') == 'TRUST_POLICY':
                required(document,'policy_id','subject_id','authority_reference','provisioned_by')
                if document['subject_id'] != subject: raise ValueError('Trust policy subject must exactly match the selected original subject.')
                if self.db.execute("SELECT 1 FROM events WHERE record_type='TRUST_POLICY' AND subject_id=?",(subject,)).fetchone(): raise ValueError('Subject authority policy is already pinned; replacement is forbidden. Contact your governance administrator for an externally controlled migration.')
                keys = document.get('keys')
                if not isinstance(keys,list) or not keys: raise ValueError('Provide at least one authorised public key. Templates authorise nobody.')
                seen = set()
                for key in keys:
                    required(key,'key_id','actor_id','public_key_base64','not_before','not_after')
                    if key['key_id'] in seen: raise ValueError('Policy key IDs must be unique.')
                    seen.add(key['key_id'])
                    Ed25519PublicKey.from_public_bytes(base64.b64decode(key['public_key_base64'],validate=True))
                    roles = key.get('roles')
                    if not isinstance(roles,list) or not roles or any(not isinstance(x,str) or x not in POLICY_ROLES for x in roles): raise ValueError('Keys need explicit ADMISSIBILITY_EVALUATION, GOVERNANCE_DECISION and/or EXECUTION_OPERATOR roles; no role implies another.')
                    if stamp(key['not_before']) >= stamp(key['not_after']): raise ValueError('Invalid key-validity interval.')
                body = dict(document)
                body['bootstrap_basis'] = 'Pinned by the authenticated app workspace user. Public-key authority and provisioned_by attribution are user-provisioned, not independently institutionally certified.'
                event = self._append('policy-'+str(uuid.uuid4()),'TRUST_POLICY',subject,original_id,canonical(body))
            else:
                payload = document.get('payload')
                if not isinstance(payload,dict): raise ValueError('A signed record requires payload and signature_base64. No free-text approval or checkbox authorises execution.')
                required(payload,'record_type','record_id','subject_id','original_assessment_id','original_assessment_sha256','key_id','actor_id','issued_at','rationale')
                kind = payload['record_type']
                from invariant_guards import control_problem, evidence_problem
                problem=control_problem(payload)
                if problem: raise ValueError(problem)
                if payload.get('original_assessment_effect') != 'UNCHANGED': raise ValueError('Signed records must explicitly assert original_assessment_effect=UNCHANGED; original result changes are forbidden.')
                if kind not in ['ADMISSIBILITY_EVALUATION','GOVERNANCE_DECISION','LIFECYCLE_ATTESTATION','LIFECYCLE_REGISTRATION']: raise ValueError('Unknown signed record type.')
                if payload['subject_id'] != subject or payload['original_assessment_id'] != original_id or payload['original_assessment_sha256'] != original['payload_sha256']: raise ValueError('Signed subject and exact original ID/hash must match the selected blocking assessment.')
                policy,policy_event = self._policy(subject)
                key = next((k for k in policy['keys'] if k['key_id'] == payload['key_id'] and k['actor_id'] == payload['actor_id']),None)
                authority_role = RECORD_AUTHORITY_ROLES[kind]
                if key is None or authority_role not in key['roles']: raise ValueError('Signer is not authorised for this record type under the pinned subject policy.')
                current,issued = stamp(now()),stamp(payload['issued_at'])
                if not (stamp(original['recorded_at']) < issued <= current): raise ValueError('The record must be issued strictly after the original blocking assessment and not in the future.')
                if not (stamp(key['not_before']) <= issued <= stamp(key['not_after']) and stamp(key['not_before']) <= current <= stamp(key['not_after'])): raise ValueError('Signer key is outside its permitted validity interval.')
                signature = base64.b64decode(document.get('signature_base64',''),validate=True)
                Ed25519PublicKey.from_public_bytes(base64.b64decode(key['public_key_base64'],validate=True)).verify(signature,canonical(payload))
                if payload['record_id'] == original_id: raise ValueError('A later evaluation/decision must have a different identifier from the original.')
                import material_change
                version = material_change.require_current_binding(self,original,payload,issued)
                latest_same_type = self.db.execute('SELECT payload FROM events WHERE subject_id=? AND record_type=? ORDER BY seq DESC LIMIT 1',(subject,kind)).fetchone()
                if latest_same_type:
                    previous_payload = strict_loads(bytes(latest_same_type[0]).decode('utf-8'))['payload']
                    if issued <= stamp(previous_payload['issued_at']): raise ValueError('Later records for a subject must have strictly later issue times; historical replay cannot replace the current chain.')
                if kind == 'ADMISSIBILITY_EVALUATION':
                    required(payload,'context','evaluation_basis')
                    if payload.get('result') not in STATES: raise ValueError('Evaluation result must be an SSA admissibility state.')
                    refs = payload.get('evidence')
                    if not isinstance(refs,list) or not refs: raise ValueError('A new evaluation must include evidence references and content hashes.')
                    problem=evidence_problem(payload)
                    if problem: raise ValueError(problem)
                    if payload.get('result') == 'ADMISSIBLE' and payload.get('evidence_sufficient') is not True: raise ValueError('ADMISSIBLE requires an explicitly signed evidence-sufficiency finding.')
                elif kind == 'GOVERNANCE_DECISION':
                    effect = payload.get('effect')
                    if effect not in ['REQUIRE_REEVALUATION','DECLINE','AUTHORISE_EXECUTION']: raise ValueError('Decision effect must be REQUIRE_REEVALUATION, DECLINE, or AUTHORISE_EXECUTION.')
                    if effect == 'AUTHORISE_EXECUTION':
                        if 'controlled_operation_scope' in payload:
                            from controlled_execution import validate_scope
                            validate_scope(payload['controlled_operation_scope'])
                        required(payload,'evaluation_id','evaluation_record_sha256')
                        evaluation = self.get(payload['evaluation_id'])
                        if evaluation['record_type'] != 'ADMISSIBILITY_EVALUATION': raise ValueError('An escalation, original or decision is not an Admissibility Evaluation.')
                        e = strict_loads(bytes(evaluation['payload']).decode('utf-8'))['payload']
                        if evaluation['record_type'] != 'ADMISSIBILITY_EVALUATION' or evaluation['subject_id'] != subject or evaluation['original_id'] != original_id or evaluation['payload_sha256'] != payload['evaluation_record_sha256']: raise ValueError('Execution decision must bind to the exact new evaluation of the same subject and original case.')
                        if e['result'] != 'ADMISSIBLE' or e.get('evidence_sufficient') is not True: raise ValueError('Non-admissible, conditional, suspended or antinomy evaluations cannot support execution authorisation.')
                        if evidence_problem(e) or control_problem(e): raise ValueError('Current reliance on an unevidenced or contradictory historical evaluation is forbidden; signed findings remain unchanged.')
                        evaluation_key=next((k for k in policy['keys'] if k['key_id']==e['key_id'] and k['actor_id']==e['actor_id'] and 'ADMISSIBILITY_EVALUATION' in k['roles']),None)
                        if not evaluation_key or not stamp(evaluation_key['not_before'])<=current<=stamp(evaluation_key['not_after']): raise ValueError('The evaluation signer is no longer authorised/current; fresh evaluation is required.')
                        latest = self.db.execute("SELECT record_id FROM events WHERE record_type='ADMISSIBILITY_EVALUATION' AND subject_id=? ORDER BY seq DESC LIMIT 1",(subject,)).fetchone()
                        if not latest or latest[0] != evaluation['record_id']: raise ValueError('A more recent subject evaluation exists; do not rely on an earlier evaluation.')
                        if issued < stamp(e['issued_at']) or issued < stamp(evaluation['recorded_at']): raise ValueError('An execution decision must be issued after the new evaluation was issued and recorded.')
                        current_version = material_change.binding(self,subject)
                        if any(e.get(k)!=v for k,v in current_version.items()): raise ValueError('A previous-version or unbound evaluation can never authorise the changed version.')
                        scope_state = material_change.status(self,subject)
                        if scope_state['reevaluation_required'] or scope_state['latest_evaluation_id'] != evaluation['record_id']: raise ValueError('Re-evaluation is outstanding for this version; an earlier evaluation cannot be reused.')
                else:
                    material_change.validate_active(self,original,payload)
                event = self._append(payload['record_id'],kind,subject,original_id,canonical(document))
                material_change.after_signed_record(self,event,payload,version)
                if kind == 'ADMISSIBILITY_EVALUATION' and payload['result'] in ['SUSPENDED','REGULATORY_ANTINOMY']:
                    esc = {'escalation_id':'escalation-for-'+payload['record_id'],'record_type':'GOVERNANCE_ESCALATION','subject_id':subject,'original_assessment_id':original_id,'original_assessment_sha256':original['payload_sha256'],'blocking_evaluation_id':payload['record_id'],'blocking_evaluation_sha256':event['payload_sha256'],'blocking_result':payload['result'],'created_at':event['recorded_at'],'basis':SPEC,'original_result_effect':'UNCHANGED','execution_authorised':False,'automatic_execution_allowed':False,'new_evaluation_required':True,'authorised_governance_decision_required':True}
                    self._append(esc['escalation_id'],'GOVERNANCE_ESCALATION',subject,original_id,canonical(esc))
            self.db.commit()
            return {'record_id':event['record_id'],'record_type':event['record_type'],'record_sha256':event['payload_sha256'],'message':'Record appended. Original assessment unchanged. Automatic execution remains blocked.'}
        except Exception as e:
            self.db.rollback()
            if type(e).__name__ == 'InvalidSignature': raise ValueError('Invalid Ed25519 signature; record rejected.')
            raise
    def version_binding(self,subject):
        import material_change
        return material_change.binding(self,subject)
    def declare_material_change(self,original_id,category,description,evidence_reference):
        import material_change
        return material_change.declare(self,original_id,category,description,evidence_reference)
    def view(self):
        self.verify()
        events = self.all()
        originals,escalations,evaluations,decisions,policies,legacy = [],[],[],[],[],[]
        for r in events:
            d = strict_loads(bytes(r['payload']).decode('utf-8'))
            item = {'record_id':r['record_id'],'subject_id':r['subject_id'],'original_id':r['original_id'],'recorded_at':r['recorded_at'],'sha256':r['payload_sha256'],'document':d,'event_sha256':r['event_sha256']}
            if r['record_type'] == 'ORIGINAL_ASSESSMENT':
                item.update(result=d['admissibility_result'],filename='original_'+r['record_id']+'.json')
                originals.append(item)
            elif r['record_type'] == 'LEGACY_SNAPSHOT':
                item['filename']='original_'+r['record_id']+'.json'; legacy.append(item)
            elif r['record_type'] == 'GOVERNANCE_ESCALATION': escalations.append(item)
            elif r['record_type'] == 'ADMISSIBILITY_EVALUATION': evaluations.append(item)
            elif r['record_type'] == 'GOVERNANCE_DECISION': decisions.append(item)
            elif r['record_type'] == 'TRUST_POLICY': policies.append(item)
        gates=[]
        for o in originals:
            subject = o['subject_id']
            evs = [r for r in events if r['record_type']=='ADMISSIBILITY_EVALUATION' and r['subject_id']==subject]
            ds = [r for r in events if r['record_type']=='GOVERNANCE_DECISION' and r['subject_id']==subject]
            latest_original = next(r for r in reversed(events) if r['record_type']=='ORIGINAL_ASSESSMENT' and r['subject_id']==subject)
            ready = False
            reason = 'A new signed ADMISSIBLE evaluation and a subsequent signed execution decision are required.'
            if latest_original['record_id'] != o['record_id']: reason = 'A later blocking original exists for this subject; earlier eligibility cannot be reused.'
            elif evs and ds:
                ev,decision = evs[-1],ds[-1]
                ep = strict_loads(bytes(ev['payload']).decode('utf-8'))['payload']
                dp = strict_loads(bytes(decision['payload']).decode('utf-8'))['payload']
                ready = ev['original_id']==o['record_id'] and decision['original_id']==o['record_id'] and ep.get('result')=='ADMISSIBLE' and ep.get('evidence_sufficient') is True and dp.get('effect')=='AUTHORISE_EXECUTION' and dp.get('evaluation_id')==ev['record_id'] and dp.get('evaluation_record_sha256')==ev['payload_sha256'] and decision['seq']>ev['seq']
                try:
                    policy,_ = self._policy(subject)
                    for signed in [ep,dp]:
                        key = next(k for k in policy['keys'] if k['key_id']==signed['key_id'] and k['actor_id']==signed['actor_id'])
                        if not stamp(key['not_before']) <= stamp(now()) <= stamp(key['not_after']): ready=False; reason='Signer authority has expired or is not yet valid.'
                except Exception: ready=False; reason='Authorisation policy cannot be verified.'
                if ready: reason='Documentary prerequisites are satisfied for this separate later chain. Original blocking result is unchanged; execution remains outside this tool.'
            gates.append({'original_id':o['record_id'],'subject_id':subject,'new_admissibility_and_authorised_decision_present':bool(ready),'automatic_execution_allowed':False,'reason':reason})
        import material_change
        version_view = material_change.view(self)
        for gate in gates:
            current = next((st for st in version_view['version_states'] if st['subject_id']==gate['subject_id']),None)
            current_case = bool(current and current['original_id']==gate['original_id'])
            gate['new_admissibility_and_authorised_decision_present'] = bool(current_case and current['new_admissibility_and_authorised_decision_present'])
            gate['reevaluation_required'] = current['reevaluation_required'] if current_case else True
            gate['current_version_id'] = current['version_id'] if current else None
            gate['active_entry_allowed'] = bool(current_case and current['active_entry_allowed'])
            gate['reason'] = current['reason'] if current_case else 'Historical original: later subject-version/case requirements cannot be satisfied by earlier evaluation records.'
        return {**version_view,'basis':SPEC,'integrity_verified':True,'automatic_execution_allowed':False,'originals':originals,'legacy_snapshots':legacy,'escalations':escalations,'evaluations':evaluations,'decisions':decisions,'policies':policies,'gates':gates,'event_count':len(events),'integrity_head':events[-1]['event_sha256'] if events else None,'limits':'Application-enforced append-only records with hashes and SQLite update/delete guards, not certified WORM storage. Owner-provisioned trust is not independent institutional identity verification. No execution connector or CL-3 conformity claim.'}
    def export(self):
        view = self.view()
        for r in self.all():
            if r['record_type'] in ['ORIGINAL_ASSESSMENT','LEGACY_SNAPSHOT','SUBJECT_VERSION']:
                prefix = 'version_' if r['record_type']=='SUBJECT_VERSION' else 'original_'
                path = os.path.join(self.outdir,prefix+r['record_id']+'.json')
                raw = bytes(r['payload'])
                if os.path.exists(path):
                    with open(path,'rb') as f:
                        if f.read()!=raw: raise ValueError('An archived original file has changed; refusing to overwrite it.')
                else:
                    with open(path,'xb') as f: f.write(raw)
        with open(os.path.join(self.outdir,'governance_registry.json'),'w',encoding='utf-8') as f: json.dump(view,f,ensure_ascii=False,indent=2)
        ledger=[{k:(bytes(r[k]).decode('utf-8') if k=='payload' else r[k]) for k in r.keys()} for r in self.all()]
        with zipfile.ZipFile(os.path.join(self.outdir,'governance_audit_bundle.zip'),'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('ledger.json',json.dumps(ledger,ensure_ascii=False,indent=2))
            z.writestr('governance_registry.json',json.dumps(view,ensure_ascii=False,indent=2))
            for item in view['originals']+view['legacy_snapshots']:
                z.write(os.path.join(self.outdir,item['filename']),'originals/'+item['filename'])
            for item in view['versions']:
                name='version_'+item['record_id']+'.json'
                z.write(os.path.join(self.outdir,name),'versions/'+name)
        return view
