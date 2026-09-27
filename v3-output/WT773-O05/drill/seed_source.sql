-- WT773 O-05 一次性演练播种（合成数据，零 ns001 数据）
BEGIN;

-- 2 个合成用户（演练凭据，非真实身份）
INSERT INTO users (id, username, email, hashed_password, avatar_status, flame_level, flame_brightness,
                   depth_preference, curiosity_preference, is_active, is_superuser, status,
                   registration_source, age_verified, photon_balance, created_at, updated_at)
VALUES
 ('11111111-1111-4111-8111-111111111111','wt773_drill_u1','wt773_u1@drill.invalid','$2b$12$4TegU9g4G0veuF6Rk4q6bu5AYQ./SAZMkQqxroas18w/AkTjva1Ga','APPROVED',1,0.5,0.5,0.5,true,false,'OFFLINE','email',true,0,now(),now()),
 ('22222222-2222-4222-8222-222222222222','wt773_drill_u2','wt773_u2@drill.invalid','drill-not-a-real-hash','APPROVED',1,0.5,0.5,0.5,true,false,'OFFLINE','email',true,0,now(),now());

-- episodic_memories：active / archived(墓碑@备份时) / retracted(墓碑@备份时) / 待备份后硬删
INSERT INTO episodic_memories (id, user_id, summary, source_type, occurred_at, retracted_at, evidence_score, correction_count, evidence_refs, evidence_missing, subject_type, created_at, updated_at)
VALUES
 ('aaaa1111-0000-4000-8000-000000000001','11111111-1111-4111-8111-111111111111','合成：偏好晨间学习','chat',now()-interval '2 day',NULL,0.9,0,'[]'::jsonb,false,'self',now()-interval '2 day',now()-interval '2 day'),
 ('aaaa1111-0000-4000-8000-000000000002','11111111-1111-4111-8111-111111111111','合成：旧偏好（已归档）','chat',now()-interval '3 day',NULL,0.5,1,'[]'::jsonb,false,'self',now()-interval '3 day',now()-interval '1 day'),
 ('aaaa1111-0000-4000-8000-000000000003','11111111-1111-4111-8111-111111111111','合成：已撤回记忆','chat',now()-interval '4 day',now()-interval '1 day',0.4,0,'[]'::jsonb,false,'self',now()-interval '4 day',now()-interval '1 day'),
 ('aaaa1111-0000-4000-8000-000000000004','22222222-2222-4222-8222-222222222222','合成：备份后将硬删的记忆','chat',now()-interval '1 day',NULL,0.8,0,'[]'::jsonb,false,'self',now()-interval '1 day',now()-interval '1 day');
UPDATE episodic_memories SET archived_at = now()-interval '1 day' WHERE id='aaaa1111-0000-4000-8000-000000000002';

-- memory_preferences：版本链 + 墓碑
INSERT INTO memory_preferences (id, user_id, pref_key, pref_value, version, retracted_at, evidence_score, correction_count, evidence_refs, evidence_missing, created_at, updated_at)
VALUES
 ('bbbb1111-0000-4000-8000-000000000001','11111111-1111-4111-8111-111111111111','study_time','"morning"'::jsonb,2,NULL,0.9,0,'[]'::jsonb,false,now()-interval '5 day',now()-interval '1 day'),
 ('bbbb1111-0000-4000-8000-000000000002','11111111-1111-4111-8111-111111111111','study_time','"evening"'::jsonb,1,now()-interval '2 day',0.5,1,'[]'::jsonb,false,now()-interval '6 day',now()-interval '2 day');

-- agent_runs：terminal / active(EXECUTING) / awaiting_user + transitions + counters + outbox
INSERT INTO agent_runs (id, user_id, kind, objective, context_refs, allowed_tools, permissions, budget,
                        completion_condition, status, attempt, steps_done, steps, heartbeat_at, created_at, updated_at)
VALUES
 ('cccc1111-0000-4000-8000-000000000001','11111111-1111-4111-8111-111111111111','execution','合成：已完成 run','[]'::jsonb,'[]'::jsonb,'{}'::jsonb,'{}'::jsonb,'{}'::jsonb,'SUCCEEDED',1,3,'[]'::jsonb,now()-interval '2 hour',now()-interval '3 hour',now()-interval '2 hour'),
 ('cccc1111-0000-4000-8000-000000000002','11111111-1111-4111-8111-111111111111','execution','合成：执行中 run','[]'::jsonb,'[]'::jsonb,'{}'::jsonb,'{}'::jsonb,'{}'::jsonb,'RUNNING',1,1,'[]'::jsonb,now()-interval '5 minute',now()-interval '1 hour',now()-interval '5 minute'),
 ('cccc1111-0000-4000-8000-000000000003','22222222-2222-4222-8222-222222222222','execution','合成：等待用户 run','[]'::jsonb,'[]'::jsonb,'{}'::jsonb,'{}'::jsonb,'{}'::jsonb,'AWAITING_USER',1,0,'[]'::jsonb,now()-interval '30 minute',now()-interval '40 minute',now()-interval '30 minute');
UPDATE agent_runs SET terminal_reason='completed' WHERE id='cccc1111-0000-4000-8000-000000000001';
UPDATE agent_runs SET wait_kind='user_step' WHERE id='cccc1111-0000-4000-8000-000000000003';

INSERT INTO agent_run_transitions (id, run_id, from_status, to_status, event_name, actor, occurred_at, created_at, updated_at)
VALUES
 ('dddd1111-0000-4000-8000-000000000001','cccc1111-0000-4000-8000-000000000001',NULL,'QUEUED','run.created','system',now()-interval '3 hour',now(),now()),

 ('dddd1111-0000-4000-8000-000000000002','cccc1111-0000-4000-8000-000000000001','QUEUED','RUNNING','run.status_changed','system',now()-interval '2 hour 30 minute',now(),now()),

 ('dddd1111-0000-4000-8000-000000000003','cccc1111-0000-4000-8000-000000000001','RUNNING','EXECUTING','run.status_changed','system',now()-interval '2 hour 15 minute',now(),now()),
 ('dddd1111-0000-4000-8000-000000000008','cccc1111-0000-4000-8000-000000000001','EXECUTING','SUCCEEDED','run.status_changed','system',now()-interval '1 hour 59 minute',now(),now()),

 ('dddd1111-0000-4000-8000-000000000004','cccc1111-0000-4000-8000-000000000002',NULL,'QUEUED','run.created','system',now()-interval '1 hour',now(),now()),

 ('dddd1111-0000-4000-8000-000000000005','cccc1111-0000-4000-8000-000000000002','QUEUED','RUNNING','run.status_changed','system',now()-interval '50 minute',now(),now()),

 ('dddd1111-0000-4000-8000-000000000006','cccc1111-0000-4000-8000-000000000003',NULL,'QUEUED','run.created','system',now()-interval '40 minute',now(),now()),

 ('dddd1111-0000-4000-8000-000000000007','cccc1111-0000-4000-8000-000000000003','QUEUED','AWAITING_USER','run.awaiting_user','system',now()-interval '30 minute',now(),now());

INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence)
VALUES ('agent_run','cccc1111-0000-4000-8000-000000000001',4),
       ('agent_run','cccc1111-0000-4000-8000-000000000002',3),
       ('agent_run','cccc1111-0000-4000-8000-000000000003',2);

-- event_outbox：已发布（published_at 非空，恢复后不得重播）+ 未发布（恢复后仍待发布）
INSERT INTO event_outbox (id, aggregate_type, aggregate_id, event_type, event_version, payload, metadata, sequence_number, created_at, published_at)
VALUES
 ('eeee1111-0000-4000-8000-000000000001','agent_run','cccc1111-0000-4000-8000-000000000001','run.created',1,'{"drill":1}'::jsonb,'{"service":"wt773-drill"}'::jsonb,1,now()-interval '3 hour',now()-interval '2 hour 59 minute'),
 ('eeee1111-0000-4000-8000-000000000002','agent_run','cccc1111-0000-4000-8000-000000000001','run.state_changed',1,'{"drill":2}'::jsonb,'{"service":"wt773-drill"}'::jsonb,2,now()-interval '2 hour',now()-interval '1 hour 59 minute'),
 ('eeee1111-0000-4000-8000-000000000003','agent_run','cccc1111-0000-4000-8000-000000000001','run.completed',1,'{"drill":3}'::jsonb,'{"service":"wt773-drill"}'::jsonb,3,now()-interval '2 hour',now()-interval '1 hour 58 minute'),
 ('eeee1111-0000-4000-8000-000000000004','agent_run','cccc1111-0000-4000-8000-000000000002','run.created',1,'{"drill":4}'::jsonb,'{"service":"wt773-drill"}'::jsonb,1,now()-interval '1 hour',NULL),
 ('eeee1111-0000-4000-8000-000000000005','agent_run','cccc1111-0000-4000-8000-000000000002','run.state_changed',1,'{"drill":5}'::jsonb,'{"service":"wt773-drill"}'::jsonb,2,now()-interval '50 minute',NULL);

-- processed_events：消费去重门（恢复后同 key 不得重复处理）
INSERT INTO processed_events (event_id, consumer_group, processed_at)
VALUES ('evt_drill0000000000000000000000000000000000000000000000000000a1','gj03',now()-interval '2 hour'),
       ('evt_drill0000000000000000000000000000000000000000000000000000a2','run_projection',now()-interval '1 hour');

COMMIT;
