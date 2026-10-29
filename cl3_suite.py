"""SSA-RM-1-CTS-CL3 v1.1 Annex A: fixed mandatory tests, sandbox probes, evidence replay.
No production GovernanceStore is opened. Explicit operation probes invoke only the bounded production adapter in isolated fixture stores; conformity results never trigger execution.
"""
import base64, copy, csv, hashlib, io, json, os, tempfile, uuid, zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from governance_store import GovernanceStore, canonical, strict_loads, sha, now, RECORD_AUTHORITY_ROLES
import material_change as mc
from conflict_engine import analyze, DEMO_CONTEXT

SPEC={'identifier':'SSA-RM-1-CTS-CL3','version':'v1.1','source':'SSA-RM-1-v1.1-Governance-Reference-Model.pdf','source_sha256':'143d2b6b6deb9066b0b03dc88dd7753155f9ad6ab34f2273f1a7d7ff52510f68','clauses':'§§6–9.15; Annex A, pp.14–15'}
STATES=['ADMISSIBLE','NON_ADMISSIBLE','CONDITIONAL','SUSPENDED','REGULATORY_ANTINOMY']
LIFE=['CREATED','REGISTERED','UNDER_REVIEW','EVALUATED','APPROVED','ACTIVE','MODIFIED','REEVALUATED','SUSPENDED','REJECTED','RETIRED']
EDGES=[('CREATED','REGISTERED'),('REGISTERED','UNDER_REVIEW'),('UNDER_REVIEW','EVALUATED'),('EVALUATED','APPROVED'),('APPROVED','ACTIVE'),('ACTIVE','MODIFIED'),('MODIFIED','REEVALUATED'),('REEVALUATED','APPROVED'),('ACTIVE','SUSPENDED'),('SUSPENDED','UNDER_REVIEW'),('ACTIVE','RETIRED')]
GROUPS={
'11':[('Lifecycle State Coverage','Every §7 state is accepted and persisted without collapsing its identity.'),('Valid Transition Enforcement','All 110 distinct-state transitions must match the §7.1 paths; forbidden transitions must be rejected.'),('ACTIVE Entry','ACTIVE needs approval, admissibility, traceability, sufficient evidence and no outstanding re-evaluation, not merely an admissible finding.'),('Lifecycle Traceability','Lifecycle changes must have reconstructable, attributed, immutable and hash-linked records.')],
'12':[('State Coverage','All five §6 admissibility states must be separately represented and persisted.'),('ADMISSIBLE Execution','A positive controlled Execution Event must be evidenced and linked to an ADMISSIBLE evaluation, sufficient evidence and an authorised decision.'),('Blocking States','Each of the four blocking states must independently be unable to authorise execution.'),('State Distinction','ADMISSIBLE is not APPROVED or ACTIVE; final/non-final and blocking outcomes remain distinct.')],
'13':[('Antinomy Detection','A jointly applicable, evidence-anchored obligation/prohibition challenge must be detected and represented as REGULATORY_ANTINOMY.'),('Automatic Execution Blocking','Detected antinomy blocks automatic execution and cannot by itself support an execution-authorising decision.'),('Conflict Traceability','Both authorities, rules, exact Context and verifiable objective source quotations/hashes must survive.'),('State Integrity','Antinomy remains explicit; missing evidence stays unresolved and never induces automatic precedence or rule invalidation.')],
'14':[('Escalation Availability','Both SUSPENDED and REGULATORY_ANTINOMY must produce traceable non-authorising escalation records.'),('Original Result Preservation','Resolution and later findings must not alter original assessment bytes or production history.'),('New Evaluation','Continuation requires a genuinely later same-subject evaluation; wrong-subject and stale records must be rejected.'),('Resolution Does Not Imply ADMISSIBLE','A resolution/re-evaluation decision alone cannot relabel the blocking original or make its subject ADMISSIBLE.'),('Post-Resolution Execution','A positive post-resolution Execution Event needs a new same-subject ADMISSIBLE evaluation and authorised linked decision.')],
'15':[('Material Change Detection','Each of the eight specified material-change domains must produce a new linked version and explicit change trace.'),('ACTIVE Blocking','A previously ACTIVE subject must be suspended on material change and barred from re-entry while re-evaluation is outstanding.'),('Previous Evaluation Invalidity','An earlier-version evaluation or decision cannot authorise the changed version, including the same original case anchor.'),('Re-evaluation Requirements','Change creates an explicit fresh-evaluation requirement; blocking findings cannot fulfil it and fresh final findings do not automatically activate.'),('Historical Preservation','All earlier assessment, governance, lifecycle and version bytes/hashes remain immutable after change.')],
'INT':[('Normal Governance Path','Reconstruct the normal permitted lifecycle/evaluation/decision/controlled-execution path end to end.'),('Antinomy Path','Detect, block, escalate and govern antinomy without changing its original result or treating resolution as admissibility.'),('Material Change Path','A complete ACTIVE → material-change → blocked re-evaluation → fresh evaluation/decision chain must not reuse old authority.'),('Traceability Reconstruction','Reconstruct the complete authority/rule/Context/evidence/evaluation/decision/Execution Event chain from objective records.')]
}
CATALOG=[]
for group,entries in GROUPS.items():
    for i,(title,criterion) in enumerate(entries,1):
        rid=['CR-'+group] if group!='INT' else ['CR-11','CR-12','CR-13','CR-14','CR-15']
        CATALOG.append({'test_id':('CL3-T'+group if group!='INT' else 'CL3-INT')+'-'+str(i).zfill(2),'requirement_id':', '.join(rid),'requirement_ids':rid,'title':title,'mandatory':True,'applicable':True,'criterion':criterion,'normative_reference':('Annex A pp.14–15; §9.'+group if group!='INT' else 'Annex A p.15; §§6–9.15')})

class Harness:
    def __init__(self,folder,initial_state='CREATED'):
        self.folder=folder; os.makedirs(folder,exist_ok=True)
        self.out=os.path.join(folder,'output'); os.makedirs(self.out,exist_ok=True)
        self.s=GovernanceStore(folder,self.out); self.subject='synthetic-cl3-subject'; self.n=0; self.logs=[]
        self.analysis=analyze({'inputMode':'file','useDemoData':True,'useDemoEvidence':True,'context':DEMO_CONTEXT})
        self.analysis['subject_details']='Fabricated subject for isolated implementation challenges'
        self.o=self.s.record_assessment(self.analysis,self.subject)
        self.key=Ed25519PrivateKey.generate()
        self.role_keys={'ADMISSIBILITY_EVALUATION':('test-key','test-evaluator',self.key),'GOVERNANCE_DECISION':('decision-key','test-governor',Ed25519PrivateKey.generate()),'EXECUTION_OPERATOR':('operator-key','test-operator',Ed25519PrivateKey.generate())}
        self.signing_keys={key_id:private for key_id,actor,private in self.role_keys.values()}
        keys=[{'key_id':key_id,'actor_id':actor,'public_key_base64':base64.b64encode(private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode(),'roles':[role],'not_before':'2020-01-01T00:00:00Z','not_after':'2100-01-01T00:00:00Z'} for role,(key_id,actor,private) in self.role_keys.items()]
        self.s.ingest(self.o['assessment_id'],{'record_type':'TRUST_POLICY','policy_id':'synthetic-policy','subject_id':self.subject,'authority_reference':'Synthetic isolated test authority','provisioned_by':'CL3 test harness only','keys':keys})
        self.must(self.make('LIFECYCLE_REGISTRATION',state=initial_state))
    def make(self,kind,**extra):
        self.n+=1; o=mc.latest_original(self.s,self.subject)
        key_id,actor,_=self.role_keys[RECORD_AUTHORITY_ROLES[kind]]
        return dict(record_type=kind,record_id='probe-'+str(self.n),subject_id=self.subject,original_assessment_id=o['record_id'],original_assessment_sha256=o['payload_sha256'],original_assessment_effect='UNCHANGED',key_id=key_id,actor_id=actor,issued_at=now(),rationale='Synthetic CL3 behavioral challenge; no real authority',**self.s.version_binding(self.subject),**extra)
    def attempt(self,payload):
        doc=self.seal(payload)
        try:
            response=self.s.ingest(mc.latest_original(self.s,self.subject)['record_id'],doc)
            self.logs.append({'request':doc,'accepted':True,'response':response}); return True
        except Exception as e:
            self.logs.append({'request':doc,'accepted':False,'exception_type':type(e).__name__,'rejection_reason':str(e)}); return False
    def must(self,p):
        if not self.attempt(p): raise ValueError('Valid setup rejected: '+self.logs[-1]['rejection_reason'])
        return p
    def evaluation(self,result='ADMISSIBLE',**extra):
        fields={'result':result,'context':mc.decode(mc.latest_version(self.s,self.subject))['snapshot']['context'],'evaluation_basis':'Fresh synthetic external evaluator finding','evidence_sufficient':result=='ADMISSIBLE','evidence':[{'reference':'synthetic source bundle','sha256':sha(canonical(self.analysis['evidence_sources'])),'content':self.analysis['evidence_sources']}]}
        if result=='CONDITIONAL': fields['conditions']=['A further evidenced evaluation must establish condition fulfilment.']
        fields.update(extra)
        return self.must(self.make('ADMISSIBILITY_EVALUATION',**fields))
    def decision(self,ev=None,effect='AUTHORISE_EXECUTION'):
        fields={'effect':effect}
        if ev:
            from controlled_execution import OPERATION
            fields.update(evaluation_id=ev['record_id'],evaluation_record_sha256=self.s.get(ev['record_id'])['payload_sha256'],controlled_operation_scope={'operation':OPERATION,'evidence_bundle_sha256':sha(canonical(ev['evidence'])),'parameters_sha256':sha(canonical({}))})
        return self.must(self.make('GOVERNANCE_DECISION',**fields))
    def qualify(self,prepare=True):
        e=self.evaluation(); d=self.decision(e)
        if prepare: self.prepare_review(e,d)
        return e,d
    def prepare_review(self,e,d):
        from lifecycle_control import cursor
        _,state=cursor(self.s,self.subject)
        if state=='CREATED': self.must(self.attestation('REGISTERED',e,d)); state='REGISTERED'
        if state in ['REGISTERED','SUSPENDED']: self.must(self.attestation('UNDER_REVIEW',e,d)); state='UNDER_REVIEW'
        if state=='UNDER_REVIEW': self.must(self.attestation('EVALUATED',e,d))
        elif state=='MODIFIED': self.must(self.attestation('REEVALUATED',e,d))
    def reach(self,target):
        from lifecycle_control import cursor
        if target in ['CREATED','REJECTED']: return None,None
        e,d=self.qualify(prepare=False)
        path=['REGISTERED','UNDER_REVIEW','EVALUATED','APPROVED','ACTIVE']
        for state in path:
            self.must(self.attestation(state,e,d))
            if state==target: return e,d
        if target in ['SUSPENDED','RETIRED']:
            self.must(self.attestation(target,e,d)); return e,d
        self.must(self.attestation('MODIFIED',e,d))
        e,d=self.qualify(prepare=False)
        if target=='REEVALUATED': self.must(self.attestation('REEVALUATED',e,d))
        return e,d
    def fork(self,folder):
        import sqlite3
        os.makedirs(os.path.join(folder,'records')); os.makedirs(os.path.join(folder,'output'))
        db=sqlite3.connect(os.path.join(folder,'records','governance.sqlite3')); self.s.db.backup(db); db.close()
        other=object.__new__(Harness); other.folder=folder; other.out=os.path.join(folder,'output'); other.subject=self.subject; other.n=self.n; other.logs=copy.deepcopy(self.logs); other.analysis=copy.deepcopy(self.analysis); other.o=self.o; other.key=self.key; other.role_keys=self.role_keys.copy(); other.signing_keys=self.signing_keys.copy()
        other.s=GovernanceStore(folder,other.out); return other
    def execution_request(self,e,d):
        from datetime import timedelta
        from controlled_execution import OPERATION
        st=self.state(); a=self.s.get(st['approval_record_id']); active=self.s.get(st['recorded_lifecycle_record_id'])
        p=self.make('CONTROLLED_EXECUTION_REQUEST',evaluation_id=e['record_id'],evaluation_record_sha256=self.s.get(e['record_id'])['payload_sha256'],decision_id=d['record_id'],decision_record_sha256=self.s.get(d['record_id'])['payload_sha256'],approval_id=a['record_id'],approval_record_sha256=a['payload_sha256'],active_id=active['record_id'],active_record_sha256=active['payload_sha256'],evidence_bundle_sha256=sha(canonical(e['evidence'])),operation=OPERATION,parameters={},parameters_sha256=sha(canonical({})),ledger_head_sha256=self.s.all()[-1]['event_sha256'])
        from governance_store import stamp
        p['expires_at']=(stamp(p['issued_at'])+timedelta(seconds=60)).isoformat().replace('+00:00','Z')
        return self.seal(p)
    def seal(self,p): return {'payload':p,'signature_base64':base64.b64encode(self.signing_keys[p['key_id']].sign(canonical(p))).decode()}
    def execute(self,request):
        from controlled_execution import execute_explicit
        try:
            event=execute_explicit(self.s,mc.latest_original(self.s,self.subject)['record_id'],request)
            self.logs.append({'operation':'explicit_controlled_execution','request':request,'accepted':True,'response':event}); return event
        except Exception as ex:
            self.logs.append({'operation':'explicit_controlled_execution','request':request,'accepted':False,'exception_type':type(ex).__name__,'rejection_reason':str(ex)}); raise
    def execute_current(self):
        e,d=self.activate(); return e,d,self.execute(self.execution_request(e,d))
    def attestation(self,state,e=None,d=None):
        extra={'state':state}
        if e: extra.update(evaluation_id=e['record_id'],evaluation_record_sha256=self.s.get(e['record_id'])['payload_sha256'])
        if d: extra.update(decision_id=d['record_id'],decision_record_sha256=self.s.get(d['record_id'])['payload_sha256'])
        return self.make('LIFECYCLE_ATTESTATION',**extra)
    def activate(self):
        e,d=self.qualify(); self.must(self.attestation('APPROVED',e,d)); self.must(self.attestation('ACTIVE',e,d)); return e,d
    def change(self):
        before=self.state(); out=self.s.declare_material_change(mc.latest_original(self.s,self.subject)['record_id'],'EVIDENCE_BASIS','Synthetic withdrawal after evaluation','Synthetic source-withdrawal notice')
        self.logs.append({'operation':'declare_material_change','request':{'domain':'EVIDENCE_BASIS','description':'Synthetic withdrawal after evaluation'},'response':out,'state_before':before,'state_after':self.state()})
    def state(self): return mc.status(self.s,self.subject)
    def preserve(self): return {r['record_id']:sha(bytes(r['payload'])) for r in self.s.all()}
    def unchanged(self,before): return all(sha(bytes(self.s.get(k)['payload']))==v for k,v in before.items())
    def capture(self):
        rows=[{**{k:r[k] for k in ['seq','record_id','record_type','subject_id','original_id','recorded_at','payload_sha256','previous_event_sha256','event_sha256']},'payload_utf8':bytes(r['payload']).decode('utf-8')} for r in self.s.all()]
        return {'operation_log':self.logs,'ledger':rows,'state':self.state(),'analysis':self.analysis,'execution_adapter_available':True,'execution_events':[mc.decode(r) for r in self.s.all() if r['record_type']=='EXECUTION_EVENT']}
    def reanalyze(self,d):
        path=os.path.join(self.folder,'challenge-evidence.json')
        with open(path,'w',encoding='utf-8') as f: json.dump({'documents':d['evidence_sources']},f,ensure_ascii=False)
        a=analyze({'inputMode':'editor','rulesJson':json.dumps({'rules':d['normative_rules']}),'useDemoEvidence':False,'context':d['context']},evidence_path=path)
        a['subject_details']=d.get('subject_details'); return a

def check_chain(rows):
    if not rows: return False
    previous='0'*64; ids=set()
    for r in rows:
        if r['record_id'] in ids or sha(r['payload_utf8'].encode('utf-8'))!=r['payload_sha256'] or r['previous_event_sha256']!=previous: return False
        fields={k:r[k] for k in ['record_id','record_type','subject_id','original_id','recorded_at','payload_sha256','previous_event_sha256']}
        if sha(canonical(fields))!=r['event_sha256']: return False
        ids.add(r['record_id']); previous=r['event_sha256']
    return True

def validate_trace(trace):
    rows=trace.get('ledger',[])
    if not check_chain(rows): return False
    records={r['record_id']:r for r in rows}; keys={}
    for row in rows:
        doc=strict_loads(row['payload_utf8'])
        if row['record_type']=='TRUST_POLICY':
            for key in doc.get('keys',[]): keys[key['key_id']]=key
        if row['record_type'] in ['ADMISSIBILITY_EVALUATION','GOVERNANCE_DECISION','LIFECYCLE_ATTESTATION','LIFECYCLE_REGISTRATION','EXECUTION_EVENT']:
            if row['record_type']=='EXECUTION_EVENT': doc=doc['request_envelope']
            payload=doc.get('payload',{}); key=keys.get(payload.get('key_id'))
            if not key or payload.get('actor_id')!=key.get('actor_id'): return False
            kind=payload.get('record_type')
            if kind not in RECORD_AUTHORITY_ROLES: return False
            if row['record_type']=='EXECUTION_EVENT':
                if kind!='CONTROLLED_EXECUTION_REQUEST': return False
            elif kind!=row['record_type']: return False
            role=RECORD_AUTHORITY_ROLES[kind]
            if role not in key.get('roles',[]): return False
            Ed25519PublicKey.from_public_bytes(base64.b64decode(key['public_key_base64'],validate=True)).verify(base64.b64decode(doc['signature_base64'],validate=True),canonical(payload))
    for log in trace.get('operation_log',[]):
        doc=log.get('request',{}); payload=doc.get('payload') if isinstance(doc,dict) else None
        if not isinstance(payload,dict): continue
        row=records.get(payload.get('record_id'))
        if log.get('accepted') is True:
            if log.get('operation')=='explicit_controlled_execution':
                if not row or row['record_type']!='EXECUTION_EVENT' or strict_loads(row['payload_utf8']).get('request_envelope')!=doc: return False
            elif not row or row['payload_sha256']!=sha(canonical(doc)): return False
        elif log.get('accepted') is False:
            if row or not log.get('rejection_reason') or not log.get('exception_type'): return False
        else: return False
    return True

def anchored(a):
    if not a.get('authority_sources') or not a.get('context') or not a.get('evidence'): return False
    docs={d['source_id']:d for d in a.get('evidence_sources',[])}
    for pair in a['evidence']:
        if len(pair.get('rules_preserved',[]))!=2: return False
        for side,rule in zip(['a','b'],pair['rules_preserved']):
            tr=pair['evidence']['trace_'+side]; source=docs.get(tr.get('source_id')); text=source['text'] if source else ''
            start,end=tr.get('start_codepoint'),tr.get('end_codepoint_exclusive')
            if not source or tr['status']!='TEXT_ANCHORED' or start is None or end is None or text[start:end]!=rule['text'] or sha(text.encode())!=tr['source_text_sha256']: return False
            if not rule.get('authority') or not rule.get('reference') or pair['context']!=a['context']: return False
    return True

def probe(test_id,h):
    suffix=test_id.split('-')[-1]; group=test_id.split('-')[1]; n=int(suffix)
    if group=='T11':
        if n==1:
            seen=[]
            for state in LIFE:
                child=Harness(os.path.join(h.folder,'coverage-'+state),initial_state='REJECTED' if state=='REJECTED' else 'CREATED')
                try:
                    child.reach(state)
                    seen.append({'requested':state,'accepted':True,'persisted':child.state()['recorded_lifecycle_state'],'trace':child.capture()})
                finally: child.s.db.close()
            return {'coverage':seen,'identity_not_execution_gate':True}
        if n==2:
            trials=[]
            for start in LIFE:
                base=Harness(os.path.join(h.folder,'from-'+start),initial_state='REJECTED' if start=='REJECTED' else 'CREATED')
                try:
                    e,d=base.reach(start)
                    if e is None: e,d=base.qualify(prepare=False)
                    for end in LIFE:
                        if start==end: continue
                        child=base.fork(os.path.join(h.folder,'trial-'+start+'-'+end))
                        try:
                            actual=child.state()['recorded_lifecycle_state']; accepted=child.attempt(child.attestation(end,e,d))
                            trials.append({'from':start,'to':end,'established_from':actual,'accepted':accepted,'trace':child.capture()})
                        finally: child.s.db.close()
                finally: base.s.db.close()
            return {'transitions':trials}
        if n==3:
            pending_denied=not h.attempt(h.attestation('ACTIVE'))
            insufficient=h.make('ADMISSIBILITY_EVALUATION',result='ADMISSIBLE',context=DEMO_CONTEXT,evaluation_basis='Insufficient evidence challenge',evidence_sufficient=False,evidence=[{'reference':'test','sha256':sha(b'Insufficient synthetic evidence'),'content_utf8':'Insufficient synthetic evidence'}])
            insufficient_denied=not h.attempt(insufficient)
            e,d=h.qualify(); prior=h.state()['lifecycle_state']
            no_approval_denied=not h.attempt(h.attestation('ACTIVE',e,d))
            h.must(h.attestation('APPROVED',e,d)); approved_allowed=h.attempt(h.attestation('ACTIVE',e,d))
            return {'pending_entry_denied':pending_denied,'insufficient_evidence_denied':insufficient_denied,'prior_to_unapproved_entry':prior,'unapproved_entry_denied':no_approval_denied,'approved_entry_accepted':approved_allowed}
        e,d=h.qualify(); h.must(h.attestation('APPROVED',e,d)); h.must(h.attestation('ACTIVE',e,d)); denied=[]
        for sql in ['UPDATE events SET record_type=record_type','DELETE FROM events']:
            try: h.s.db.execute(sql)
            except Exception as ex: h.s.db.rollback(); denied.append({'statement':sql,'rejected':True,'reason':str(ex)})
            else: denied.append({'statement':sql,'rejected':False})
        return {'ledger_guards':denied}
    if group=='T12':
        if n in [1,3,4]:
            outcomes=[]
            for state in STATES:
                ev=h.evaluation(state); status=h.state()
                attempt=h.make('GOVERNANCE_DECISION',effect='AUTHORISE_EXECUTION',evaluation_id=ev['record_id'],evaluation_record_sha256=h.s.get(ev['record_id'])['payload_sha256'])
                accepted=h.attempt(attempt)
                outcomes.append({'requested':state,'persisted':mc.decode(h.s.get(ev['record_id']))['payload']['result'],'state':status,'execution_decision_accepted':accepted})
            return {'outcomes':outcomes}
        e,d,event=h.execute_current(); return {'evaluation_id':e['record_id'],'decision_id':d['record_id'],'documentary_state':h.state(),'execution_adapter_available':True,'execution_events':[event]}
    if group=='T13':
        a=h.analysis
        if n==1: return {'positive_assessment':a,'blocking_result':h.o['admissibility_result']}
        if n==2:
            refused=not h.attempt(h.make('GOVERNANCE_DECISION',effect='AUTHORISE_EXECUTION',evaluation_id=h.o['assessment_id'],evaluation_record_sha256=h.s.get(h.o['assessment_id'])['payload_sha256']))
            return {'analysis':a,'blocked_origin_decision_rejected':refused,'state':h.state()}
        if n==3: return {'analysis':a}
        missing=copy.deepcopy(a); missing['evidence_sources']=[]; unresolved=h.reanalyze(missing)
        same=copy.deepcopy(a); same['normative_rules'][1]['modality']='obligation'; same['normative_rules'][1]['text']=same['normative_rules'][0]['text']; same['evidence_sources'][1]['text']=same['normative_rules'][0]['text']; compatible=h.reanalyze(same)
        return {'analysis':a,'missing_evidence':unresolved,'same_modality_control':compatible}
    if group=='T14':
        before=h.preserve()
        if n==1:
            blocked=h.evaluation('SUSPENDED'); ant=h.evaluation('REGULATORY_ANTINOMY')
            return {'escalations':h.s.view()['escalations'],'required_evaluation_ids':[blocked['record_id'],ant['record_id']]}
        if n==2:
            h.decision(effect='REQUIRE_REEVALUATION'); h.qualify()
            return {'original_record_id':h.o['assessment_id'],'hashes_before':before,'hashes_after':h.preserve()}
        if n==3:
            wrong=h.make('ADMISSIBILITY_EVALUATION',result='ADMISSIBLE',context=DEMO_CONTEXT,evaluation_basis='Cross-subject challenge',evidence_sufficient=True,evidence=[{'reference':'test','sha256':'a'*64}]); wrong['subject_id']='different-subject'
            rejected=not h.attempt(wrong); ev=h.evaluation(); replay=copy.deepcopy(ev); replay['record_id']='old-replay'; replay_rejected=not h.attempt(replay)
            return {'original':mc.decode(h.s.get(h.o['assessment_id'])),'evaluation':mc.decode(h.s.get(ev['record_id']))['payload'],'wrong_subject_rejected':rejected,'replay_rejected':replay_rejected,'state':h.state()}
        if n==4:
            h.decision(effect='REQUIRE_REEVALUATION')
            return {'original':mc.decode(h.s.get(h.o['assessment_id'])),'state':h.state(),'hashes_before':before,'hashes_after':h.preserve()}
        h.decision(effect='REQUIRE_REEVALUATION')
        e,d,event=h.execute_current(); return {'evaluation':e,'decision':d,'state':h.state(),'execution_adapter_available':True,'execution_events':[event]}
    if group=='T15':
        if n==1:
            changes=[]
            for domain in mc.CATEGORIES:
                d=copy.deepcopy(h.analysis)
                if domain=='SUBJECT': d['subject_details']='Revised synthetic subject'
                elif domain=='NORMATIVE_RULE': d['normative_rules'][0]['action']='retain different records'
                elif domain=='AUTHORITY_SOURCE': d['normative_rules'][0]['authority']='Revised authority'
                elif domain=='APPLICABILITY_CONDITION': d['normative_rules'][0]['applicability_conditions']='Revised applicability'
                elif domain=='JURISDICTION': d['normative_rules'][0]['jurisdiction']='Revised jurisdiction'
                elif domain=='EFFECTIVE_PERIOD': d['normative_rules'][0]['valid_to']='2027-12-31'
                elif domain=='EVIDENCE_BASIS': d['evidence_sources'][0]['text']+=' Additional source evidence.'
                else: d['context']='Revised synthetic Context'
                prior=h.state(); saved=h.s.record_assessment(h.reanalyze(d),h.subject); state=h.state(); delta=h.s.view()['material_changes'][-1]
                changes.append({'domain':domain,'old_version':prior['version_id'],'new_version':state['version_id'],'requirement':state['reevaluation_required'],'change':delta})
            return {'changes':changes}
        e,d=h.activate(); before=h.preserve(); old=h.state(); h.change(); changed=h.state()
        old_payload=h.attestation('ACTIVE',e,d); old_entry_denied=not h.attempt(old_payload)
        if n==2: return {'before':old,'after':changed,'old_entry_denied':old_entry_denied}
        if n==3:
            old_dec=h.make('GOVERNANCE_DECISION',effect='AUTHORISE_EXECUTION',evaluation_id=e['record_id'],evaluation_record_sha256=h.s.get(e['record_id'])['payload_sha256']); dec_denied=not h.attempt(old_dec)
            ev_copy=copy.deepcopy(e); ev_copy['record_id']='replay-old-version'; ev_denied=not h.attempt(ev_copy)
            return {'before':old,'after':changed,'old_evaluation_rejected':ev_denied,'old_decision_rejected':dec_denied,'old_active_rejected':old_entry_denied}
        if n==4:
            intermediate=[]
            for outcome in ['CONDITIONAL','SUSPENDED','REGULATORY_ANTINOMY']:
                h.evaluation(outcome); intermediate.append(h.state())
            h.evaluation('NON_ADMISSIBLE'); non=h.state(); h.evaluation(); final=h.state()
            return {'after_change':changed,'blocking_states':intermediate,'final_non_admissible':non,'final_admissible':final,'requirements':h.s.view()['reevaluation_requirements']}
        h.qualify(); h.s.export()
        originals=[]
        for row in h.s.all():
            if row['record_type'] in ['SUBJECT_VERSION','ORIGINAL_ASSESSMENT']:
                prefix='version_' if row['record_type']=='SUBJECT_VERSION' else 'original_'
                with open(os.path.join(h.out,prefix+row['record_id']+'.json'),'rb') as f: originals.append({'record_id':row['record_id'],'file_sha256':sha(f.read()),'ledger_sha256':row['payload_sha256']})
        return {'hashes_before':before,'hashes_after':h.preserve(),'immutable_exports':originals}
    if n==1:
        path=[]
        e,d=h.qualify(prepare=False)
        for state in ['CREATED','REGISTERED','UNDER_REVIEW','EVALUATED','APPROVED','ACTIVE']:
            path.append({'state':state,'accepted':h.attempt(h.attestation(state,e,d)),'persisted':h.state()['recorded_lifecycle_state']})
        event=h.execute(h.execution_request(e,d))
        return {'normal_path':path,'evaluation':e,'decision':d,'execution_adapter_available':True,'execution_events':[event]}
    if n==2:
        original=h.preserve(); initial=h.state(); h.decision(effect='REQUIRE_REEVALUATION'); after_resolution=h.state(); e,d=h.qualify()
        return {'analysis':h.analysis,'initial':initial,'after_resolution':after_resolution,'after_fresh_evaluation_decision':h.state(),'original_hashes_before':original,'hashes_after':h.preserve(),'escalations':h.s.view()['escalations'],'evaluation':e,'decision':d}
    if n==3:
        e,d=h.activate(); old=h.state(); h.change(); changed=h.state()
        denied=not h.attempt(h.attestation('ACTIVE',e,d)); fresh=h.evaluation(); eval_only=h.state(); decision=h.decision(fresh); ready=h.state()
        return {'before':old,'after_change':changed,'old_active_rejected':denied,'after_evaluation_only':eval_only,'after_decision':ready,'evaluation':fresh,'decision':decision}
    e,d,event=h.execute_current(); h.s.export()
    return {'analysis':h.analysis,'evaluation':e,'decision':d,'execution_adapter_available':True,'execution_events':[event]}

def expect(test_id,o,trace):
    """Fixed oracles. Evidence supplies observations, never expected values or result overrides."""
    group=test_id.split('-')[1]; n=int(test_id.split('-')[-1]); issues=[]
    def need(ok,message):
        if not ok: issues.append(message)
    def preserved(a,b): return bool(a) and all(b.get(k)==v for k,v in a.items())
    def execution():
        need(o.get('execution_adapter_available') is True,'Missing implemented controlled-execution adapter and positive Execution Event evidence; mandatory test cannot be NOT_APPLICABLE.')
        events=o.get('execution_events',[])
        need(bool(events),'No actual controlled Execution Event supplied; documentary readiness is not execution.')
        records={r['record_id']:r for r in trace.get('ledger',[])}
        for e in events:
            need(e.get('evaluation_result')=='ADMISSIBLE' and e.get('evidence_sufficient') is True and e.get('authorised_decision') is True and bool(e.get('evaluation_id')) and bool(e.get('decision_id')) and bool(e.get('record_id')),'Execution Event lacks ADMISSIBLE/evidence/authorised-decision/trace identity links.')
            event=records.get(e.get('record_id')); evaluation=records.get(e.get('evaluation_id')); decision=records.get(e.get('decision_id'))
            linked=bool(event and evaluation and decision and event['record_type']=='EXECUTION_EVENT' and evaluation['record_type']=='ADMISSIBILITY_EVALUATION' and decision['record_type']=='GOVERNANCE_DECISION')
            need(linked,'Positive execution observations are not backed by actual linked Execution Event/evaluation/decision ledger records.')
            if linked:
                ep=strict_loads(event['payload_utf8']); ep=ep.get('payload',ep)
                vp=strict_loads(evaluation['payload_utf8'])['payload']; dp=strict_loads(decision['payload_utf8'])['payload']
                need(vp.get('result')=='ADMISSIBLE' and vp.get('evidence_sufficient') is True and dp.get('effect')=='AUTHORISE_EXECUTION' and dp.get('evaluation_id')==evaluation['record_id'] and dp.get('evaluation_record_sha256')==evaluation['payload_sha256'],'Actual evaluation/authorised decision graph does not support execution.')
                from controlled_execution import receipt_valid
                need(receipt_valid(ep,vp,dp),'Execution receipt does not reproduce the actual allow-listed operation over the bound verified evidence.')
                need(ep.get('evaluation_id')==evaluation['record_id'] and ep.get('decision_id')==decision['record_id'] and ep.get('evaluation_record_sha256')==evaluation['payload_sha256'] and ep.get('decision_record_sha256')==decision['payload_sha256'],'Execution Event lacks exact evaluation/decision ID and hash bindings.')
                need(event['seq']>decision['seq']>evaluation['seq'] and event['subject_id']==decision['subject_id']==evaluation['subject_id'] and ep.get('subject_version_id')==dp.get('subject_version_id')==vp.get('subject_version_id'),'Execution ordering, subject identity or version scope is inconsistent.')
    if group=='T11':
        if n==1:
            rows=o.get('coverage',[]); need(len(rows)==len(LIFE) and {r.get('requested') for r in rows}==set(LIFE),'Lifecycle state coverage is incomplete.')
            need(all(r.get('accepted') is True and r.get('persisted')==r.get('requested') for r in rows),'A defined lifecycle state was rejected or collapsed.')
            need(all(validate_trace(r.get('trace',{})) for r in rows),'Independent state fixtures lack reconstructable signed production traces.')
        elif n==2:
            rows=o.get('transitions',[]); need({(r.get('from'),r.get('to')) for r in rows}=={(a,b) for a in LIFE for b in LIFE if a!=b} and len(rows)==110,'All 110 distinct-state transition challenges are mandatory.')
            wrong=[f"{r.get('from')} → {r.get('to')}" for r in rows if r.get('established_from')!=r.get('from') or type(r.get('accepted')) is not bool or r['accepted']!=((r['from'],r['to']) in EDGES)]
            need(all(validate_trace(r.get('trace',{})) for r in rows),'Independent transition fixtures lack reconstructable production traces.')
            need(not wrong,'Transition constraints violated: '+', '.join(wrong[:12])+(' …' if len(wrong)>12 else ''))
        elif n==3:
            for k in ['pending_entry_denied','insufficient_evidence_denied','unapproved_entry_denied','approved_entry_accepted']: need(o.get(k) is True,'ACTIVE prerequisite challenge failed: '+k)
        else:
            need(len(o.get('ledger_guards',[]))==2 and all(x.get('rejected') is True for x in o.get('ledger_guards',[])),'Lifecycle records lack enforced UPDATE/DELETE protection.')
            need(check_chain(trace.get('ledger',[])),'Lifecycle trace chain cannot be reconstructed.')
            lifecycle=[strict_loads(r['payload_utf8']).get('payload',{}) for r in trace.get('ledger',[]) if r['record_type']=='LIFECYCLE_ATTESTATION']
            need(bool(lifecycle) and all(p.get('actor_id') and p.get('issued_at') and p.get('subject_version_id') for p in lifecycle),'Missing attributed/versioned lifecycle trace records.')
    elif group=='T12':
        if n==2: execution()
        else:
            rows=o.get('outcomes',[]); need(len(rows)==5 and {r.get('requested') for r in rows}==set(STATES),'All five admissibility states require objective challenge evidence.')
            need(all(r.get('persisted')==r.get('requested') for r in rows),'Admissibility state identity was lost.')
            if n==3:
                need(all(r.get('execution_decision_accepted') is False and r.get('state',{}).get('automatic_execution_allowed') is False for r in rows if r.get('requested')!='ADMISSIBLE'),'A blocking state independently authorised execution.')
            if n==4:
                need(all(r.get('state',{}).get('lifecycle_state')!='ACTIVE' for r in rows),'An evaluation automatically implied ACTIVE.')
                for r in rows:
                    need(r.get('state',{}).get('reevaluation_required')==(r.get('requested') not in ['ADMISSIBLE','NON_ADMISSIBLE']),'Final/blocking-state re-evaluation semantics collapsed.')
    elif group=='T13':
        a=o.get('positive_assessment',o.get('analysis',{})); pairs=a.get('evidence',[])
        need(bool(pairs),'Missing actual comparator output.')
        if n==1:
            need(o.get('blocking_result')=='REGULATORY_ANTINOMY' and any(p.get('outcome')=='REGULATORY_ANTINOMY' for p in pairs),'Positive antinomy challenge was not explicitly detected and represented.')
        if n==2:
            need(a.get('automatic_execution_allowed') is False and all(p.get('automatic_execution_allowed') is False and p.get('execution_state')=='BLOCKED' for p in pairs),'Automatic execution is not blocked.')
            need(o.get('blocked_origin_decision_rejected') is True,'A blocking original supported an authorising decision.')
        if n==3: need(anchored(a),'Incomplete authority/rule/Context or invalid objective quotation/hash trace.')
        if n==4:
            need(any(p.get('outcome')=='REGULATORY_ANTINOMY' for p in pairs),'Antinomy state was collapsed.')
            resolution=a.get('resolution',{}); need(resolution.get('performed') is False and resolution.get('prevailing_rule') is None and resolution.get('invalidated_rules')==[] and resolution.get('ranked_authorities')==[],'Automatic resolution, invalidation or authority ranking occurred or is not evidenced absent.')
            need(o.get('missing_evidence',{}).get('outcome_counts',{}).get('POTENTIAL_CONFLICT',0)>0,'Missing evidence was not retained as unresolved.')
            need(o.get('same_modality_control',{}).get('outcome_counts',{}).get('NO_CONFLICT',0)>0,'Same-modality negative control failed.')
    elif group=='T14':
        if n==1:
            esc=o.get('escalations',[]); ids=o.get('required_evaluation_ids',[])
            need(len(ids)==2 and all(any(x.get('document',{}).get('blocking_evaluation_id')==rid and x['document'].get('execution_authorised') is False and x['document'].get('original_result_effect')=='UNCHANGED' for x in esc) for rid in ids),'Missing separately traceable non-authorising escalations for both blocking outcomes.')
        elif n==2: need(preserved(o.get('hashes_before',{}),o.get('hashes_after',{})),'Prior original/governance record hash missing or modified.')
        elif n==3:
            a=o.get('original',{}); e=o.get('evaluation',{})
            need(bool(a) and bool(e) and a.get('subject_id')==e.get('subject_id') and e.get('record_id')!=a.get('assessment_id') and e.get('issued_at','')>a.get('created_at',''),'A distinct later same-subject evaluation is not established.')
            need(o.get('wrong_subject_rejected') is True and o.get('replay_rejected') is True,'Wrong-subject or stale evaluation reuse was not rejected.')
            need(o.get('state',{}).get('new_admissibility_and_authorised_decision_present') is False,'Evaluation alone implied authority.')
        elif n==4:
            need(o.get('original',{}).get('admissibility_result')=='REGULATORY_ANTINOMY' and o.get('state',{}).get('current_admissibility_state')!='ADMISSIBLE' and o.get('state',{}).get('reevaluation_required') is True,'Resolution alone implied ADMISSIBLE or removed re-evaluation.')
            need(preserved(o.get('hashes_before',{}),o.get('hashes_after',{})),'Resolution modified original history.')
        else: execution()
    elif group=='T15':
        if n==1:
            rows=o.get('changes',[]); need(len(rows)==8 and {r.get('domain') for r in rows}==set(mc.CATEGORIES),'All eight material-change domains must be challenged.')
            for r in rows:
                need(r.get('old_version')!=r.get('new_version') and bool(r.get('new_version')) and r.get('requirement') is True and any(c.get('category')==r.get('domain') for c in r.get('change',{}).get('document',{}).get('changes',[])),'Change was not detected, versioned or made subject to re-evaluation: '+str(r.get('domain')))
        elif n in [2,3]:
            a=o.get('before',{}); b=o.get('after',{}); need(a.get('lifecycle_state')=='ACTIVE' and a.get('version_id')!=b.get('version_id') and b.get('reevaluation_required') is True and b.get('lifecycle_state')=='SUSPENDED' and b.get('active_entry_allowed') is False,'A changed ACTIVE subject was not suspended and blocked.')
            keys=['old_entry_denied'] if n==2 else ['old_evaluation_rejected','old_decision_rejected','old_active_rejected']
            for k in keys: need(o.get(k) is True,'Old authority was reused or rejection evidence absent: '+k)
        elif n==4:
            need(o.get('after_change',{}).get('reevaluation_required') is True and bool(o.get('requirements')),'Missing new-evaluation requirement after change.')
            need(len(o.get('blocking_states',[]))==3 and all(s.get('reevaluation_required') is True and s.get('lifecycle_state')!='ACTIVE' for s in o.get('blocking_states',[])),'Blocking/conditional findings incorrectly fulfilled re-evaluation.')
            for key,result in [('final_non_admissible','NON_ADMISSIBLE'),('final_admissible','ADMISSIBLE')]:
                s=o.get(key,{}); need(s.get('current_admissibility_state')==result and s.get('reevaluation_required') is False and s.get('lifecycle_state')!='ACTIVE' and s.get('automatic_execution_allowed') is False,'Fresh final evaluation semantics not evidenced: '+key)
        else:
            need(preserved(o.get('hashes_before',{}),o.get('hashes_after',{})),'Previous governance history was lost or modified.')
            exports=o.get('immutable_exports',[]); need(bool(exports) and all(x.get('file_sha256')==x.get('ledger_sha256') for x in exports),'Immutable prior/version exports differ from ledger bytes.')
            need(check_chain(trace.get('ledger',[])),'Historical chain verification failed.')
    else:
        if n==1:
            path=o.get('normal_path',[]); need([r.get('state') for r in path]==['CREATED','REGISTERED','UNDER_REVIEW','EVALUATED','APPROVED','ACTIVE'] and all(r.get('accepted') is True and r.get('persisted')==r.get('state') for r in path),'Normal lifecycle path is incomplete.')
            execution()
        elif n==2:
            need(anchored(o.get('analysis',{})) and o.get('initial',{}).get('current_admissibility_state')=='REGULATORY_ANTINOMY','Antinomy path lacks detection or objective conflict trace.')
            need(bool(o.get('escalations')) and o.get('after_resolution',{}).get('reevaluation_required') is True and o.get('after_resolution',{}).get('current_admissibility_state')!='ADMISSIBLE','Escalation/resolution bypassed evaluation.')
            need(preserved(o.get('original_hashes_before',{}),o.get('hashes_after',{})),'The original blocking result changed.')
            need(o.get('after_fresh_evaluation_decision',{}).get('new_admissibility_and_authorised_decision_present') is True and o['after_fresh_evaluation_decision'].get('automatic_execution_allowed') is False,'Fresh separate chain missing or automatically executed.')
        elif n==3:
            need(o.get('before',{}).get('lifecycle_state')=='ACTIVE' and o.get('after_change',{}).get('reevaluation_required') is True and o['after_change'].get('lifecycle_state')=='SUSPENDED','Material-change integrated suspension failed.')
            need(o.get('old_active_rejected') is True,'Old ACTIVE authority was reused.')
            need(o.get('after_evaluation_only',{}).get('new_admissibility_and_authorised_decision_present') is False and o['after_evaluation_only'].get('lifecycle_state')!='ACTIVE','New evaluation alone conferred authority or ACTIVE.')
            need(o.get('after_decision',{}).get('new_admissibility_and_authorised_decision_present') is True and o['after_decision'].get('automatic_execution_allowed') is False and o['after_decision'].get('lifecycle_state')!='ACTIVE','Fresh decision autoactivated or bypassed prerequisites.')
        else:
            need(anchored(o.get('analysis',{})) and check_chain(trace.get('ledger',[])),'Authority/rule/Context/evidence or governance ledger cannot be reconstructed.')
            execution()
    return issues

def identity(appdir):
    names=['lifecycle_control.py','controlled_execution.py','execution_tests.py','remediation_report.py','governance_tests.py','material_change_tests.py','src/ControlledExecutionLayer.tsx','conflict_engine.py','governance_store.py','material_change.py','invariant_guards.py','invariant_tests.py','cl3_suite.py','notebook.ipynb','src/App.tsx','src/GovernanceLayer.tsx','src/MaterialChangeLayer.tsx','src/ConformityLayer.tsx']
    files=[]
    for name in names:
        path=os.path.join(appdir,name)
        if os.path.isfile(path):
            with open(path,'rb') as f: files.append({'path':name,'sha256':sha(f.read())})
    return {'implementation_id':'SSA Antinomy Conflict Analyzer','implementation_digest':sha(canonical(files)),'source_files':files,'declared_scope':'Current local implementation, CR-11–CR-15 Annex A behavioral suite; no CL-1/CL-2 certification'}

def production_hashes(appdir,outdir):
    files=[]; root=os.path.join(appdir,'records')
    if os.path.isdir(root):
        for path,dirs,names in os.walk(root):
            for name in names: files.append(os.path.join(path,name))
    if os.path.isdir(outdir): files.extend(os.path.join(outdir,n) for n in os.listdir(outdir) if n.startswith(('original_','version_')) and n.endswith('.json'))
    result={}
    for name in files:
        with open(name,'rb') as f: result[os.path.relpath(name,appdir)]=sha(f.read())
    return result

def collect(appdir,outdir):
    run_id='cl3-'+str(uuid.uuid4()); impl=identity(appdir); entries=[]; before=production_hashes(appdir,outdir)
    with tempfile.TemporaryDirectory(prefix='ssa-cl3-isolated-') as root:
        for test in CATALOG:
            h=None; observation={}; trace={}
            try:
                h=Harness(os.path.join(root,test['test_id']))
                observation=probe(test['test_id'],h); trace=h.capture()
            except Exception as ex:
                observation={'probe_exception_type':type(ex).__name__,'probe_failure_reason':str(ex)}
                if h:
                    try: trace=h.capture()
                    except Exception: trace={'capture_failure':'Behavior trace could not be recovered.'}
            finally:
                if h: h.s.db.close()
            content={'test_id':test['test_id'],'run_id':run_id,'implementation_digest':impl['implementation_digest'],'evidence_kind':'behavioral_probe_trace','observations':observation,'trace':trace}
            entries.append({'test_id':test['test_id'],'reference':run_id+'/evidence/'+test['test_id']+'.json','sha256':sha(canonical(content)),'content':content})
    after=production_hashes(appdir,outdir)
    return {'schema_version':1,'run_id':run_id,'captured_at':now(),'implementation':impl,'specification':SPEC,'evidence_origin':'Local behavioral probes with fabricated fixtures; real production functions, isolated stores and disposable signing keys','production_records_unchanged':before==after,'production_record_hashes_before':before,'production_record_hashes_after':after,'test_evidence':entries}

def evaluate(bundle,mode='local',provenance_verified=False):
    global_issues=[]
    if not provenance_verified: global_issues.append('Behavioral provenance is uncorroborated: hashes and self-signed fixture logs cannot prove that supplied observations were measured. An unchanged known local capture or configured independent trusted runner is required; mandatory tests cannot be inferred PASS.')
    if not isinstance(bundle,dict): bundle={}; global_issues.append('Expected an evidence-bundle object.')
    impl=bundle.get('implementation',{}); run_id=bundle.get('run_id','')
    if not isinstance(impl,dict): impl={}
    if bundle.get('capture_parse_failure'): global_issues.append('Required objective evidence could not be read: '+str(bundle['capture_parse_failure']))
    if bundle.get('schema_version')!=1: global_issues.append('Missing or unsupported evidence schema_version (expected 1).')
    digest=impl.get('implementation_digest')
    if not isinstance(run_id,str) or not run_id.strip() or not isinstance(impl.get('implementation_id'),str) or not impl.get('implementation_id') or not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest) or not isinstance(impl.get('declared_scope'),str) or not impl.get('declared_scope'): global_issues.append('Missing exact implementation identity/SHA-256 digest, declared scope or run identity.')
    baseline=bundle.get('specification'); baseline=baseline if isinstance(baseline,dict) else {}
    if baseline.get('source_sha256')!=SPEC['source_sha256'] or baseline.get('version')!=SPEC['version']: global_issues.append('Normative baseline/version binding is missing or mismatched.')
    before=bundle.get('production_record_hashes_before'); after=bundle.get('production_record_hashes_after')
    if not isinstance(before,dict) or not isinstance(after,dict) or before!=after: global_issues.append('Missing or unequal before/after production-record fingerprint manifests; preservation is not inferred from a boolean.')
    entries=bundle.get('test_evidence',[])
    if not isinstance(entries,list): entries=[]; global_issues.append('test_evidence must be an array.')
    known={t['test_id'] for t in CATALOG}
    if any(not isinstance(e,dict) or e.get('test_id') not in known for e in entries): global_issues.append('Unknown or invalid test evidence record; fixed mandatory catalog cannot be replaced.')
    results=[]
    for t in CATALOG:
        issues=list(global_issues); candidates=[x for x in entries if isinstance(x,dict) and x.get('test_id')==t['test_id']]; refs=[]
        if len(candidates)!=1: issues.append('Exactly one objective evidence artifact is required for this mandatory test; evidence is absent or duplicated.')
        else:
            e=candidates[0]; content=e.get('content',{}); ref=e.get('reference'); digest=e.get('sha256')
            if ref: refs.append({'reference':ref,'sha256':digest})
            if not isinstance(ref,str) or not ref.strip() or not isinstance(content,dict) or not content: issues.append('Missing objective evidence reference or artifact content; a locator/hash alone is insufficient.')
            else:
                try:
                    if digest!=sha(canonical(content)): issues.append('Objective evidence artifact SHA-256 does not match its supplied content.')
                    if content.get('test_id')!=t['test_id'] or content.get('run_id')!=run_id or content.get('implementation_digest')!=impl.get('implementation_digest'): issues.append('Artifact is bound to another test, run or implementation version.')
                    if e.get('mandatory') is False or e.get('evaluation_result')=='NOT_APPLICABLE' or e.get('applicable') is False: issues.append('NOT_APPLICABLE or exclusion cannot bypass this mandatory CL-3 test.')
                    trace=content.get('trace'); obs=content.get('observations')
                    if not isinstance(obs,dict) or not obs or not isinstance(trace,dict) or not trace.get('ledger') or not validate_trace(trace): issues.append('Missing/invalid actual behavioral observations, signed records, operation-to-record links or reconstructable objective ledger trace.')
                    else: issues.extend(expect(t['test_id'],obs,trace))
                except Exception as ex: issues.append('Evidence insufficient for the fixed test oracle: '+type(ex).__name__+': '+str(ex))
        if bundle.get('production_records_unchanged') is not True: issues.append('No evidence that conformity assessment left prior production records unchanged.')
        result='FAIL' if issues else 'PASS'
        results.append({**t,'evaluation_result':result,'objective_evidence_reference':'; '.join(r['reference'] for r in refs) or 'MISSING — '+t['test_id'],'evidence_references':refs,'traceable_reason':' '.join(issues) if issues else 'Observed behavior satisfies the fixed criterion: '+t['criterion']})
    summary=[]
    for group in GROUPS:
        subset=[r for r in results if r['test_id'].startswith('CL3-'+('T'+group if group!='INT' else 'INT')+'-')]
        summary.append({'requirement_id':'CR-'+group if group!='INT' else 'INTEGRATION','test_ids':[r['test_id'] for r in subset],'evaluation_result':'PASS' if all(r['evaluation_result']=='PASS' for r in subset) else 'FAIL','pass_count':sum(r['evaluation_result']=='PASS' for r in subset),'test_count':len(subset),'objective_evidence_reference':'; '.join(r['objective_evidence_reference'] for r in subset),'traceable_reason':'All mandatory group tests are PASS.' if all(r['evaluation_result']=='PASS' for r in subset) else 'Mandatory group tests with FAIL: '+', '.join(r['test_id'] for r in subset if r['evaluation_result']=='FAIL')})
    return {'suite':SPEC,'report_id':'report-'+str(uuid.uuid4()),'created_at':now(),'source_run_id':run_id or None,'evidence_mode':mode,'implementation':impl,'overall_result':'PASS' if len(results)==26 and all(r['evaluation_result']=='PASS' for r in results) else 'FAIL','results':results,'requirement_results':summary,'mandatory_test_count':26,'not_applicable_count':0,'aggregation_rule':'All 26 mandatory Annex A tests must be PASS; missing/insufficient evidence and attempted mandatory NOT_APPLICABLE are FAIL. Filters never affect aggregation.','conformity_scope':'CR-11 through CR-15 and Annex A integration tests only. CL-3 inherits CL-1/CL-2; their prerequisite conformity is not established here.','full_cl3_certification_claimed':False,'automatic_execution_allowed':False,'governance_authority_granted':False,'regulatory_precedence_resolved':False,'prior_records_modified':False if bundle.get('production_records_unchanged') is True else None,'evidence_provenance_verified':bool(provenance_verified),'evidence_authenticity':'Only fresh local probes or exact known local capture receipts corroborate measured behavior. Unknown/modified uploaded observations fail closed; no independent external runner is configured.'}

def capture_receipt(appdir,bundle,create=False):
    try:
        digest=sha(canonical(bundle)); folder=os.path.join(appdir,'conformity_receipts'); path=os.path.join(folder,'receipt-'+digest+'.json')
        if create:
            os.makedirs(folder,exist_ok=True)
            receipt={'capture_sha256':digest,'run_id':bundle['run_id'],'implementation_digest':bundle['implementation']['implementation_digest'],'recorded_at':now(),'effect':'Provenance only; no governance or execution authority'}
            with open(path,'xb') as f: f.write(canonical(receipt))
        with open(path,encoding='utf-8') as f: receipt=strict_loads(f.read())
        return receipt.get('capture_sha256')==digest and receipt.get('run_id')==bundle.get('run_id') and receipt.get('implementation_digest')==bundle.get('implementation',{}).get('implementation_digest')
    except Exception: return False

def write_suite(appdir,outdir,bundle=None,mode='local'):
    local_generated=bundle is None
    if local_generated: bundle=collect(appdir,outdir)
    provenance=capture_receipt(appdir,bundle,create=local_generated)
    report=evaluate(bundle,mode,provenance_verified=provenance); report['run_settings']={'useDemoCl3':mode=='local'}
    report['current_implementation_digest']=identity(appdir)['implementation_digest']
    rid=report['report_id']; names={'report':rid+'.json','evidence':rid+'.evidence.json','csv':rid+'.csv','audit':rid+'.zip'}
    report['exports']=names
    report['overall_traceable_reason']='Every mandatory applicable Annex A test is PASS.' if report['overall_result']=='PASS' else 'Mandatory tests with FAIL: '+', '.join(r['test_id'] for r in report['results'] if r['evaluation_result']=='FAIL')
    blobs={names['report']:json.dumps(report,ensure_ascii=False,indent=2).encode(),names['evidence']:json.dumps(bundle,ensure_ascii=False,indent=2).encode()}
    stream=io.StringIO(); fields=['requirement_id','test_id','mandatory','evaluation_result','objective_evidence_reference','traceable_reason']; writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
    for r in report['results']:
        row={k:r[k] for k in fields}
        writer.writerow({k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()})
    blobs[names['csv']]=stream.getvalue().encode()
    for name,raw in blobs.items():
        with open(os.path.join(outdir,name),'xb') as f: f.write(raw)
    with zipfile.ZipFile(os.path.join(outdir,names['audit']),'x',zipfile.ZIP_DEFLATED) as z:
        for name,raw in blobs.items(): z.writestr(name,raw)
        z.writestr('catalog.json',json.dumps(CATALOG,ensure_ascii=False,indent=2))
        entries=bundle.get('test_evidence',[]) if isinstance(bundle,dict) else []
        emitted=set()
        for e in entries if isinstance(entries,list) else []:
            if isinstance(e,dict) and e.get('test_id') in {t['test_id'] for t in CATALOG} and isinstance(e.get('content'),dict) and e['test_id'] not in emitted:
                try: raw=canonical(e['content'])
                except Exception: continue
                z.writestr('evidence/'+e['test_id']+'.json',raw); emitted.add(e['test_id'])
    with open(os.path.join(outdir,'cl3_latest.json'),'w',encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2)
    return report

def verify_evidence_policy(report,outdir):
    """Harness guard tests; never affect an implementation verdict or create authority."""
    with open(os.path.join(outdir,report['exports']['evidence']),encoding='utf-8') as f: bundle=strict_loads(f.read())
    empty=evaluate({},'replay')
    assert len(empty['results'])==26 and all(r['evaluation_result']=='FAIL' for r in empty['results'])
    first=CATALOG[0]['test_id']
    for mutation in ['missing','mandatory_na','tampered','duplicate']:
        b=copy.deepcopy(bundle)
        if mutation=='missing': b['test_evidence']=[e for e in b['test_evidence'] if e['test_id']!=first]
        elif mutation=='mandatory_na': b['test_evidence'][0].update(evaluation_result='NOT_APPLICABLE',mandatory=False,applicable=False)
        elif mutation=='tampered': b['test_evidence'][0]['sha256']='0'*64
        else: b['test_evidence'].append(copy.deepcopy(b['test_evidence'][0]))
        r=evaluate(b,'replay',provenance_verified=True)
        assert r['overall_result']=='FAIL' and next(x for x in r['results'] if x['test_id']==first)['evaluation_result']=='FAIL'
        assert len(r['results'])==26 and all(x['evaluation_result'] in ['PASS','FAIL','NOT_APPLICABLE'] for x in r['results'])
    return True
