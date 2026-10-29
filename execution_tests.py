"""Isolated operation-backed positive/negative regression checks. No production execution."""
import copy,os,tempfile
from datetime import timedelta
from unittest.mock import patch
from governance_store import sha,canonical,stamp,now
from cl3_suite import Harness
import controlled_execution as ce
import material_change as mc

def run_checks(appdir):
    checks=[]
    with tempfile.TemporaryDirectory(prefix='ssa-explicit-execution-') as folder:
        h=Harness(folder)
        try:
            e,d=h.activate(); request=h.execution_request(e,d)
            assert not [r for r in h.s.all() if r['record_type']=='EXECUTION_EVENT']
            checks.append({'check':'Detection, escalation, evaluation, decision and approval/ACTIVE do not execute automatically','status':'PASS'})
            before={r['record_id']:sha(canonical({**dict(r),'payload':bytes(r['payload']).decode()})) for r in h.s.all()}
            def reject(document,name,before_operation=True,role_failure=False):
                saved=[tuple(r) for r in h.s.all()]
                event_count=sum(r['record_type']=='EXECUTION_EVENT' for r in h.s.all())
                with patch('controlled_execution.perform_operation',wraps=ce.perform_operation) as operation:
                    try: ce.execute_explicit(h.s,h.o['assessment_id'],document)
                    except Exception as ex:
                        assert [tuple(r) for r in h.s.all()]==saved
                        if before_operation: operation.assert_not_called()
                        if role_failure: assert 'required pinned subject-policy role' in str(ex)
                        after_count=sum(r['record_type']=='EXECUTION_EVENT' for r in h.s.all())
                        assert after_count==event_count
                        checks.append({'check':name,'status':'PASS','rejection_type':type(ex).__name__,'reason':str(ex),'execution_events_before':event_count,'execution_events_after':after_count,'complete_ledger_unchanged':True,'operation_invoked':operation.called})
                    else: raise AssertionError('Unsafe execution request accepted: '+name)
            def as_role(payload,role):
                p=copy.deepcopy(payload); p['key_id'],p['actor_id'],_=h.role_keys[role]
                policy,_=h.s._policy(h.subject)
                assert next(k for k in policy['keys'] if k['key_id']==p['key_id'])['roles']==[role]
                return h.seal(p)
            reject(as_role(request['payload'],'GOVERNANCE_DECISION'),'GOVERNANCE_DECISION-only key cannot sign CONTROLLED_EXECUTION_REQUEST',role_failure=True)
            reject(as_role(request['payload'],'ADMISSIBILITY_EVALUATION'),'Evaluator-only key cannot invoke controlled execution',role_failure=True)
            def reject_ingest(payload,role,name):
                saved=[tuple(r) for r in h.s.all()]; document=as_role(payload,role)
                event_count=sum(r['record_type']=='EXECUTION_EVENT' for r in h.s.all())
                with patch('controlled_execution.perform_operation',wraps=ce.perform_operation) as operation:
                    try: h.s.ingest(h.o['assessment_id'],document)
                    except ValueError as ex:
                        assert 'Signer is not authorised for this record type' in str(ex)
                        assert [tuple(r) for r in h.s.all()]==saved
                        operation.assert_not_called()
                        assert sum(r['record_type']=='EXECUTION_EVENT' for r in h.s.all())==event_count
                        checks.append({'check':name,'status':'PASS','reason':str(ex),'execution_events_before':event_count,'execution_events_after':event_count,'complete_ledger_unchanged':True,'operation_invoked':False})
                    else: raise AssertionError('Incorrect record role accepted: '+name)
            reject_ingest(h.make('GOVERNANCE_DECISION',effect='REQUIRE_REEVALUATION'),'EXECUTION_OPERATOR','EXECUTION_OPERATOR-only key cannot create a governance decision')
            reject_ingest(h.make('ADMISSIBILITY_EVALUATION',result='ADMISSIBLE'),'EXECUTION_OPERATOR','EXECUTION_OPERATOR-only key cannot create an evaluation')
            reject_ingest(h.make('LIFECYCLE_REGISTRATION',state='CREATED'),'EXECUTION_OPERATOR','EXECUTION_OPERATOR-only key cannot register lifecycle state')
            for state in ['APPROVED','ACTIVE']:
                for role in ['EXECUTION_OPERATOR','ADMISSIBILITY_EVALUATION']:
                    reject_ingest(h.attestation(state,e,d),role,role+'-only key cannot sign '+state+' lifecycle attestation')
            # Exercise every adapter slot, including ACTIVE after a valid approval.
            # Wrong-role signed envelopes are injected at the signature-verification
            # seam only; no immutable row or pinned policy is rewritten.
            real_verify=ce.verify_envelope
            ids={'evaluation':e['record_id'],'decision':d['record_id'],'approval':request['payload']['approval_id'],'active':request['payload']['active_id']}
            for slot,ident in ids.items():
                def wrong_role(document,policy,role,current,ident=ident):
                    if document.get('payload',{}).get('record_id')==ident:
                        document=as_role(document['payload'],'EXECUTION_OPERATOR')
                    return real_verify(document,policy,role,current)
                with patch('controlled_execution.verify_envelope',side_effect=wrong_role):
                    reject(request,'Runtime '+slot+' wrong-role envelope rejected before operation/event (injected verification seam)',role_failure=True)
            # Unknown/mismatched record types cannot fall through to governance.
            policy,_=h.s._policy(h.subject); saved=[tuple(r) for r in h.s.all()]
            for slot,kind in [('approval','GOVERNANCE_DECISION'),('active','ADMISSIBILITY_EVALUATION')]:
                try: ce.verify_prerequisite(slot,kind,h.seal(d if slot=='approval' else e),policy,stamp(now()))
                except ValueError as ex: assert 'Wrong record type' in str(ex)
                else: raise AssertionError('Wrong prerequisite type accepted')
            assert [tuple(r) for r in h.s.all()]==saved
            checks.append({'check':'Approval/ACTIVE wrong record types rejected without a generic role fallback or event','status':'PASS','execution_events_before':0,'execution_events_after':0,'complete_ledger_unchanged':True,'operation_invoked':False})
            def changed(**extra):
                p=copy.deepcopy(request['payload']); p.update(extra); return h.seal(p)
            reject(changed(operation='SHELL',parameters={'command':'anything'}),'Unlisted operation, command and parameter input rejected')
            reject(changed(parameters={'path':'arbitrary-path'}),'Arbitrary filesystem/path parameters rejected')
            missing=copy.deepcopy(request['payload']); missing.pop('evidence_bundle_sha256'); reject(h.seal(missing),'Missing exact evidence binding rejected')
            reject(changed(evidence_bundle_sha256='0'*64),'Changed evidence bundle binding rejected')
            reject(changed(evaluation_record_sha256='0'*64),'Changed evaluation hash rejected')
            reject(changed(subject_id='other-subject'),'Cross-subject request rejected')
            unsigned=copy.deepcopy(request); unsigned['signature_base64']=''; reject(unsigned,'Unsigned execution request rejected')
            reject(changed(expires_at=request['payload']['issued_at']),'Expired request rejected')
            with patch('controlled_execution.now',return_value='2101-01-01T00:00:00Z'):
                reject(request,'Expired signing authority rejected')
            future=stamp(now())+timedelta(hours=2)
            stale=changed(issued_at=future.isoformat(),expires_at=(future+timedelta(seconds=60)).isoformat())
            with patch('controlled_execution.now',return_value=future.isoformat()):
                reject(stale,'Stale evaluation/decision/approval chain rejected even with a fresh signed request')
            invalid=h.make('ADMISSIBILITY_EVALUATION',result='ADMISSIBLE',context=h.analysis['context'],evaluation_basis='Negative fixture',evidence_sufficient=True,evidence=[])
            assert not h.attempt(invalid)
            checks.append({'check':'Missing evidence cannot establish an ADMISSIBLE evaluation','status':'PASS'})
            with patch('controlled_execution.perform_operation',side_effect=RuntimeError('Injected operation failure before completion')):
                reject(request,'Operation failure cannot produce a success Execution Event',before_operation=False)
            event=h.execute(request)
            row=h.s.get(event['record_id']); assert row['record_type']=='EXECUTION_EVENT'
            assert ce.receipt_valid(event,e,d)
            assert event['operation_result']['evidence_digest_sha256']==sha(canonical(e['evidence'])) and event['operation_result']['byte_count']==len(canonical(e['evidence']))
            assert stamp(event['completed_at'])<=stamp(row['recorded_at'])
            checks.append({'check':'Real deterministic evidence digest completes before its exactly bound append-only Execution Event','status':'PASS','event':event,'event_payload_sha256':row['payload_sha256']})
            reject(request,'Successful request replay rejected')
            reissued=copy.deepcopy(request['payload']); reissued.update(record_id='reissued-'+request['payload']['record_id'],ledger_head_sha256=h.s.all()[-1]['event_sha256'],issued_at=now()); reissued['expires_at']=(stamp(reissued['issued_at'])+timedelta(seconds=60)).isoformat()
            reject(h.seal(reissued),'Fresh request cannot reuse a consumed execution decision')
            h.evaluation('REGULATORY_ANTINOMY')
            blocked=copy.deepcopy(reissued); blocked.update(record_id='blocked-request',ledger_head_sha256=h.s.all()[-1]['event_sha256'],issued_at=now()); blocked['expires_at']=(stamp(blocked['issued_at'])+timedelta(seconds=60)).isoformat()
            reject(h.seal(blocked),'A later blocking evaluation invalidates earlier execution authority')
            for state in ['NON_ADMISSIBLE','CONDITIONAL','SUSPENDED']:
                h.evaluation(state)
                blocked.update(record_id='blocked-'+state,ledger_head_sha256=h.s.all()[-1]['event_sha256'],issued_at=now()); blocked['expires_at']=(stamp(blocked['issued_at'])+timedelta(seconds=60)).isoformat()
                reject(h.seal(blocked),'Current '+state+' independently blocks controlled execution')
            e2,d2=h.activate(); old=h.execution_request(e2,d2); h.change()
            oldp=copy.deepcopy(old['payload']); oldp['ledger_head_sha256']=h.s.all()[-1]['event_sha256']
            reject(h.seal(oldp),'Changed version rejects old requests despite refreshed ledger head')
            assert not h.attempt(h.attestation('ACTIVE',e2,d2))
            assert not h.attempt(h.attestation('RETIRED',e2,d2))
            checks.append({'check':'Forbidden lifecycle jumps cannot bypass material-change or ACTIVE controls','status':'PASS'})
            assert all(sha(canonical({**dict(h.s.get(k)),'payload':bytes(h.s.get(k)['payload']).decode()}))==v for k,v in before.items())
            assert h.s.verify() and mc.decode(h.s.get(h.o['assessment_id']))['admissibility_result']=='REGULATORY_ANTINOMY'
            assert len([r for r in h.s.all() if r['record_type']=='EXECUTION_EVENT'])==1
            checks.append({'check':'Original blocking result and every pre-existing complete ledger row survive all positive and negative operations','status':'PASS','preexisting_rows':len(before)})
        finally: h.s.db.close()
    return checks
