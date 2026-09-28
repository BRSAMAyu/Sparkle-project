from __future__ import annotations
import unittest,sys,json,tempfile,hashlib
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timedelta,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'reference'),str(ROOT/'tools')]
from contract_reference import Candidate,Context,select_optional,Receipt,PresentationEvent,Preferences,FeedbackPolicy,safe_rate
from packlib import check_dag,ready,check_receipt
NOW=datetime(2026,9,28,tzinfo=timezone.utc)
class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.c=Candidate('m1','u1','g1','practice',.9,.9,confirmed=True)
        self.ctx=Context('u1','g1','practice',NOW)
    def select(self,**kw):return select_optional([replace(self.c,**kw)],self.ctx)
    def test_relevant_confirmed_selected(self):self.assertEqual(self.select()[0],['m1'])
    def test_wrong_owner_excluded(self):self.assertEqual(self.select(owner='u2')[1]['m1'],'owner')
    def test_revocation_excluded(self):self.assertFalse(self.select(revoked=True)[0])
    def test_dead_source_excluded(self):self.assertFalse(self.select(source_alive=False)[0])
    def test_expiry_boundary_excluded(self):self.assertEqual(self.select(expires_at=NOW)[1]['m1'],'expired')
    def test_future_expiry_allowed(self):self.assertEqual(self.select(expires_at=NOW+timedelta(hours=1))[0],['m1'])
    def test_other_goal_excluded(self):self.assertFalse(self.select(goal='g2')[0])
    def test_other_task_type_excluded(self):self.assertFalse(self.select(task_type='proof')[0])
    def test_global_requires_consent(self):self.assertFalse(self.select(goal=None)[0]);self.assertTrue(self.select(goal=None,global_consent=True)[0])
    def test_external_material_not_user_memory(self):self.assertFalse(self.select(source_kind='external_material')[0])
    def test_conflict_not_ranked_away(self):self.assertFalse(self.select(conflict=True)[0])
    def test_negative_transfer_can_reject(self):self.assertFalse(self.select(relevance=.4,decision_relevance=.4,negative_transfer=1)[0])
    def test_token_budget_enforced(self):self.assertFalse(self.select(tokens=1000)[0])
    def test_top_k_limit(self):
        cs=[replace(self.c,ref=str(i)) for i in range(10)]
        self.assertEqual(len(select_optional(cs,replace(self.ctx,top_k=2))[0]),2)
    def test_duplicate_reference_rejected(self):
        with self.assertRaises(ValueError):select_optional([self.c,self.c],self.ctx)
    def test_nan_score_rejected(self):
        with self.assertRaises(ValueError):self.select(relevance=float('nan'))
    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):select_optional([self.c],replace(self.ctx,now=datetime(2026,9,28)))
    def test_zero_denominator_na(self):self.assertIsNone(safe_rate(0,0));self.assertEqual(safe_rate(9,20),.45)
    def test_invalid_rate_not_hidden(self):
        with self.assertRaises(ValueError):safe_rate(2,1)
class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.r={'r1':Receipt('r1','u1','t1',2,'committed')}
        self.e=PresentationEvent('e1','u1','t1',2,'action_committed','r1')
        self.p=Preferences(audio=True,haptic=True);self.f=FeedbackPolicy()
    def test_committed_success(self):self.assertTrue(self.f.project(self.e,self.r,self.p)['audio'])
    def test_pending_cannot_celebrate(self):
        self.r['r1']=replace(self.r['r1'],status='applying')
        self.assertEqual(self.f.project(self.e,self.r,self.p)['visual'],'unverified')
    def test_wrong_user_cannot_celebrate(self):self.assertFalse(self.f.project(replace(self.e,owner='u2'),self.r,self.p)['audio'])
    def test_wrong_version_cannot_celebrate(self):self.assertFalse(self.f.project(replace(self.e,version=3),self.r,self.p)['haptic'])
    def test_missing_receipt_cannot_celebrate(self):self.assertFalse(self.f.project(self.e,{},self.p)['audio'])
    def test_replay_preserves_text_not_effect(self):
        d=self.f.project(replace(self.e,replay=True),self.r,self.p)
        self.assertEqual(d['visual'],'committed');self.assertFalse(d['audio']);self.assertFalse(d['motion'])
    def test_different_event_same_receipt_deduped(self):
        self.f.project(self.e,self.r,self.p)
        self.assertFalse(self.f.project(replace(self.e,event_id='e2'),self.r,self.p)['haptic'])
    def test_muted_still_visible(self):
        d=self.f.project(self.e,self.r,Preferences());self.assertEqual(d['visual'],'committed');self.assertFalse(d['audio'])
    def test_reduced_motion(self):self.assertFalse(self.f.project(self.e,self.r,replace(self.p,reduced_motion=True))['motion'])
    def test_unsupported_haptic(self):self.assertFalse(self.f.project(self.e,self.r,replace(self.p,haptic_supported=False))['haptic'])
    def test_background_silent(self):self.assertFalse(self.f.project(self.e,self.r,replace(self.p,foreground=False))['audio'])
    def test_memory_save_not_action_success(self):
        d=self.f.project(replace(self.e,kind='memory_saved'),self.r,self.p)
        self.assertEqual(d['visual'],'memory_saved');self.assertFalse(d['audio'])
class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tasks=json.loads((ROOT/'04_tasks/tasks.json').read_text())['tasks']
    def test_real_dag(self):self.assertEqual(check_dag(self.tasks),[])
    def test_six_initial_slots(self):self.assertEqual(len(ready(self.tasks)),6)
    def test_heavy_slot_respected(self):self.assertNotIn('V4-B04',ready(self.tasks,heavy_active=True))
    def test_failed_dependency_not_ready(self):
        s={t['id']:{'implementation_state':'INTEGRATED','evidence_verdict':'FAIL'} for t in self.tasks}
        self.assertNotIn('V4-Q08',ready(self.tasks,s))
    def test_zero_slots(self):self.assertEqual(ready(self.tasks,slots=0),[])
    def test_cycle_rejected(self):self.assertTrue(check_dag([{'id':'a','depends_on':['b']},{'id':'b','depends_on':['a']}]))
    def test_missing_dependency_rejected(self):self.assertTrue(check_dag([{'id':'a','depends_on':['missing']}]))
    def test_duplicate_id_rejected(self):self.assertTrue(check_dag([{'id':'a'},{'id':'a'}]))
    def test_every_module_owned(self):
        for m in json.loads((ROOT/'01_product/MODULE_MATRIX.json').read_text())['features']:self.assertTrue(m['task_ids'],m['name'])
    def test_receipt_consistency_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'log.txt';p.write_text('actual log sample')
            data={'verdict':'PASS','source_sha':'a'*40,'build_id':'b1','implementation_session':'author',
                  'reviews':[{'session':'reviewer','source_sha':'a'*40,'verdict':'APPROVE'}],
                  'runs':[{'command':'example command','exit_code':0,'failed':0,'skipped':0}],
                  'artifacts':[{'path':'log.txt','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}
            self.assertEqual(check_receipt(data,Path(d)),[])
            p.write_text('changed');self.assertIn('artifact hash mismatch',check_receipt(data,Path(d)))
    def test_author_cannot_self_review(self):
        d={'verdict':'PASS','source_sha':'a'*40,'implementation_session':'same','reviews':[{'session':'same','source_sha':'a'*40,'verdict':'APPROVE'}]}
        self.assertIn('author cannot self-review',check_receipt(d,ROOT))
    def test_skipped_run_not_pass(self):
        d={'runs':[{'command':'test','exit_code':0,'skipped':1}]}
        self.assertIn('failed, skipped or incomplete run',check_receipt(d,ROOT))
if __name__=='__main__':unittest.main()
