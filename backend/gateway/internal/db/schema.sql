--
-- PostgreSQL database dump
--


-- Dumped from database version 16.13 (Debian 16.13-1.pgdg12+1)
-- Dumped by pg_dump version 16.13 (Debian 16.13-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', 'public', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: achievementrarity; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE achievementrarity AS ENUM (
    'COMMON',
    'RARE',
    'EPIC',
    'LEGENDARY'
);


ALTER TYPE achievementrarity OWNER TO postgres;

--
-- Name: achievementtype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE achievementtype AS ENUM (
    'MILESTONE',
    'STREAK',
    'MASTERY',
    'TASK_COMPLETE',
    'HIDDEN',
    'SOCIAL',
    'CONTRACT',
    'STUDY_TIME',
    'NODE_EXPLORE',
    'SPRINT'
);


ALTER TYPE achievementtype OWNER TO postgres;

--
-- Name: analysisstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE analysisstatus AS ENUM (
    'PENDING',
    'PROCESSING',
    'COMPLETED',
    'FAILED'
);


ALTER TYPE analysisstatus OWNER TO postgres;

--
-- Name: avatarstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE avatarstatus AS ENUM (
    'APPROVED',
    'PENDING',
    'REJECTED'
);


ALTER TYPE avatarstatus OWNER TO postgres;

--
-- Name: contractstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE contractstatus AS ENUM (
    'ACTIVE',
    'COMPLETED',
    'FAILED',
    'EXPIRED'
);


ALTER TYPE contractstatus OWNER TO postgres;

--
-- Name: depthlevel; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE depthlevel AS ENUM (
    'SHALLOW',
    'MEDIUM',
    'DEEP'
);


ALTER TYPE depthlevel OWNER TO postgres;

--
-- Name: focusstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE focusstatus AS ENUM (
    'COMPLETED',
    'INTERRUPTED'
);


ALTER TYPE focusstatus OWNER TO postgres;

--
-- Name: focustype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE focustype AS ENUM (
    'POMODORO',
    'STOPWATCH'
);


ALTER TYPE focustype OWNER TO postgres;

--
-- Name: friendshipstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE friendshipstatus AS ENUM (
    'PENDING',
    'ACCEPTED',
    'BLOCKED'
);


ALTER TYPE friendshipstatus OWNER TO postgres;

--
-- Name: grouprole; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE grouprole AS ENUM (
    'OWNER',
    'ADMIN',
    'MEMBER'
);


ALTER TYPE grouprole OWNER TO postgres;

--
-- Name: grouptype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE grouptype AS ENUM (
    'SQUAD',
    'SPRINT',
    'OFFICIAL'
);


ALTER TYPE grouptype OWNER TO postgres;

--
-- Name: messagerole; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE messagerole AS ENUM (
    'USER',
    'ASSISTANT',
    'SYSTEM'
);


ALTER TYPE messagerole OWNER TO postgres;

--
-- Name: messagetype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE messagetype AS ENUM (
    'TEXT',
    'TASK_SHARE',
    'PLAN_SHARE',
    'FRAGMENT_SHARE',
    'CAPSULE_SHARE',
    'PRISM_SHARE',
    'FILE_SHARE',
    'PROGRESS',
    'ACHIEVEMENT',
    'CHECKIN',
    'SYSTEM',
    'BROADCAST'
);


ALTER TYPE messagetype OWNER TO postgres;

--
-- Name: moderationaction; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE moderationaction AS ENUM (
    'WARN',
    'MUTE',
    'KICK',
    'BAN'
);


ALTER TYPE moderationaction OWNER TO postgres;

--
-- Name: offlinemessagestatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE offlinemessagestatus AS ENUM (
    'PENDING',
    'SENT',
    'FAILED',
    'EXPIRED'
);


ALTER TYPE offlinemessagestatus OWNER TO postgres;

--
-- Name: planpriority; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE planpriority AS ENUM (
    'critical',
    'high',
    'normal',
    'low'
);


ALTER TYPE planpriority OWNER TO postgres;

--
-- Name: planstage; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE planstage AS ENUM (
    'sprint',
    'daily',
    'review',
    'paused'
);


ALTER TYPE planstage OWNER TO postgres;

--
-- Name: plantype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE plantype AS ENUM (
    'SPRINT',
    'GROWTH'
);


ALTER TYPE plantype OWNER TO postgres;

--
-- Name: reportreason; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE reportreason AS ENUM (
    'SPAM',
    'HARASSMENT',
    'VIOLENCE',
    'MISINFORMATION',
    'INAPPROPRIATE',
    'OTHER'
);


ALTER TYPE reportreason OWNER TO postgres;

--
-- Name: reportstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE reportstatus AS ENUM (
    'PENDING',
    'REVIEWED',
    'DISMISSED',
    'ACTIONED'
);


ALTER TYPE reportstatus OWNER TO postgres;

--
-- Name: searchvisibility; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE searchvisibility AS ENUM (
    'everyone',
    'friends',
    'nobody'
);


ALTER TYPE searchvisibility OWNER TO postgres;

--
-- Name: streakdaystatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE streakdaystatus AS ENUM (
    'active',
    'frozen',
    'missed'
);


ALTER TYPE streakdaystatus OWNER TO postgres;

--
-- Name: subtaskstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE subtaskstatus AS ENUM (
    'PENDING',
    'IN_PROGRESS',
    'COMPLETED'
);


ALTER TYPE subtaskstatus OWNER TO postgres;

--
-- Name: taskstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE taskstatus AS ENUM (
    'PENDING',
    'IN_PROGRESS',
    'COMPLETED',
    'ABANDONED'
);


ALTER TYPE taskstatus OWNER TO postgres;

--
-- Name: tasktype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE tasktype AS ENUM (
    'LEARNING',
    'TRAINING',
    'ERROR_FIX',
    'REFLECTION',
    'SOCIAL',
    'PLANNING',
    'OCR'
);


ALTER TYPE tasktype OWNER TO postgres;

--
-- Name: userstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE userstatus AS ENUM (
    'ONLINE',
    'OFFLINE',
    'INVISIBLE'
);


ALTER TYPE userstatus OWNER TO postgres;

--
-- Name: visualeffecttype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE visualeffecttype AS ENUM (
    'NONE',
    'BLACK_HOLE',
    'SUPERNOVA',
    'GRAVITY_WAVE',
    'NEBULA_TRANSFORM',
    'GALAXY_SKIN',
    'DUAL_STAR_CONNECTION'
);


ALTER TYPE visualeffecttype OWNER TO postgres;

--
-- Name: visualelementrarity; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE visualelementrarity AS ENUM (
    'common',
    'rare',
    'epic',
    'legendary'
);


ALTER TYPE visualelementrarity OWNER TO postgres;

--
-- Name: visualelementtype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE visualelementtype AS ENUM (
    'background',
    'particle',
    'effect',
    'bundle'
);


ALTER TYPE visualelementtype OWNER TO postgres;

--
-- Name: visualelementunlocksource; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE visualelementunlocksource AS ENUM (
    'system',
    'achievement',
    'shop',
    'event',
    'season'
);


ALTER TYPE visualelementunlocksource OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ab_experiment_assignments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE ab_experiment_assignments (
    experiment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    variant_id uuid NOT NULL,
    assignment_date timestamp without time zone NOT NULL,
    is_excluded boolean NOT NULL,
    exclusion_reason character varying(200),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE ab_experiment_assignments OWNER TO postgres;

--
-- Name: ab_experiment_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE ab_experiment_metrics (
    experiment_id uuid NOT NULL,
    variant_id uuid NOT NULL,
    user_id uuid,
    metric_name character varying(100) NOT NULL,
    metric_value double precision NOT NULL,
    metric_type character varying(50) NOT NULL,
    context_data jsonb,
    "timestamp" timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE ab_experiment_metrics OWNER TO postgres;

--
-- Name: ab_experiment_variants; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE ab_experiment_variants (
    experiment_id uuid NOT NULL,
    variant_name character varying(100) NOT NULL,
    description text,
    is_control boolean NOT NULL,
    prompt_version character varying(50),
    configuration jsonb,
    allocation_weight double precision NOT NULL,
    traffic_allocation_percentage double precision NOT NULL,
    extra_metadata jsonb,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE ab_experiment_variants OWNER TO postgres;

--
-- Name: ab_experiments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE ab_experiments (
    name character varying(200) NOT NULL,
    description text,
    hypothesis text NOT NULL,
    status character varying(20) NOT NULL,
    created_by uuid,
    sample_size_target integer,
    significance_level double precision NOT NULL,
    power double precision NOT NULL,
    minimum_detectable_effect double precision,
    start_date timestamp without time zone,
    end_date timestamp without time zone,
    conclusion text,
    winning_variant_id uuid,
    extra_metadata jsonb,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE ab_experiments OWNER TO postgres;

--
-- Name: achievements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE achievements (
    id character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(500),
    icon_url character varying(500),
    type achievementtype NOT NULL,
    rarity achievementrarity,
    trigger_code character varying(50) NOT NULL,
    trigger_config json,
    is_hidden boolean,
    hint character varying(200),
    prerequisites json,
    visual_effect_type visualeffecttype,
    visual_config json,
    reward_config json,
    total_unlocked integer,
    first_unlocker_id uuid,
    sort_order integer,
    category character varying(50),
    parent_id character varying(50),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    name_i18n json,
    description_i18n json,
    active_from timestamp without time zone,
    active_to timestamp without time zone,
    is_limited boolean DEFAULT false NOT NULL,
    event_tag character varying(50)
);


ALTER TABLE achievements OWNER TO postgres;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE alembic_version (
    version_num character varying(64) NOT NULL
);


ALTER TABLE alembic_version OWNER TO postgres;

--
-- Name: appeals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE appeals (
    appeal_id character varying(64) NOT NULL,
    review_id character varying(64) NOT NULL,
    user_id uuid,
    appeal_reason text NOT NULL,
    issues_with_review jsonb,
    status character varying(32) NOT NULL,
    assigned_to character varying(64),
    secondary_review_id character varying(64),
    secondary_decision character varying(32),
    secondary_score double precision,
    resolution text,
    resolved_by character varying(64),
    resolved_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE appeals OWNER TO postgres;

--
-- Name: arbitration_cases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE arbitration_cases (
    case_id character varying(64) NOT NULL,
    appeal_id character varying(64) NOT NULL,
    review_id character varying(64) NOT NULL,
    user_id uuid,
    escalation_reason character varying(64) NOT NULL,
    priority character varying(32) NOT NULL,
    status character varying(32) NOT NULL,
    assigned_to character varying(64),
    assigned_at timestamp without time zone,
    original_review_score double precision NOT NULL,
    secondary_review_score double precision,
    score_discrepancy double precision NOT NULL,
    resolution text,
    final_decision character varying(32),
    resolved_at timestamp without time zone,
    resolved_by character varying(64),
    notes jsonb,
    evidence jsonb,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE arbitration_cases OWNER TO postgres;

--
-- Name: arbitration_decisions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE arbitration_decisions (
    case_id character varying(64) NOT NULL,
    decision character varying(32) NOT NULL,
    explanation text NOT NULL,
    arbitrator_id character varying(64) NOT NULL,
    arbitrator_role character varying(32) NOT NULL,
    confidence double precision NOT NULL,
    feedback_for_model text,
    decided_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE arbitration_decisions OWNER TO postgres;

--
-- Name: auth_audit_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE auth_audit_log (
    user_id uuid,
    action character varying(64) NOT NULL,
    ip_address character varying(45),
    user_agent character varying(500),
    metadata json,
    occurred_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE auth_audit_log OWNER TO postgres;

--
-- Name: behavior_patterns; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE behavior_patterns (
    user_id uuid NOT NULL,
    pattern_name character varying(100) NOT NULL,
    pattern_type character varying(50) NOT NULL,
    description text,
    solution_text text,
    evidence_ids json,
    confidence_score double precision,
    frequency integer,
    is_archived boolean,
    last_observed_at timestamp without time zone,
    last_decay_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE behavior_patterns OWNER TO postgres;

--
-- Name: behavioral_outcomes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE behavioral_outcomes (
    user_id uuid NOT NULL,
    intervention_id uuid NOT NULL,
    outcome_type character varying(50) NOT NULL,
    time_to_outcome integer NOT NULL,
    success boolean NOT NULL,
    context json,
    "timestamp" timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE behavioral_outcomes OWNER TO postgres;

--
-- Name: broadcast_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE broadcast_messages (
    sender_id uuid NOT NULL,
    content text NOT NULL,
    content_data json,
    target_group_ids json NOT NULL,
    delivered_count integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE broadcast_messages OWNER TO postgres;

--
-- Name: calendar_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE calendar_events (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    is_all_day boolean DEFAULT false NOT NULL,
    location character varying(255),
    color character varying(32),
    recurrence_rule character varying(512),
    recurrence_end_date timestamp with time zone,
    reminder_minutes jsonb DEFAULT '[]'::jsonb NOT NULL,
    source character varying(32) DEFAULT 'manual'::character varying NOT NULL,
    source_metadata jsonb,
    task_id uuid,
    plan_id uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE calendar_events OWNER TO postgres;

--
-- Name: capsule_favorites; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE capsule_favorites (
    user_id uuid NOT NULL,
    capsule_id uuid NOT NULL,
    note text,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE capsule_favorites OWNER TO postgres;

--
-- Name: capsule_feedbacks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE capsule_feedbacks (
    user_id uuid NOT NULL,
    capsule_id uuid NOT NULL,
    rating integer,
    helpful boolean,
    category character varying(50),
    comment text,
    inferred_depth_delta double precision,
    inferred_curiosity_delta double precision,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE capsule_feedbacks OWNER TO postgres;

--
-- Name: capsule_generation_jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE capsule_generation_jobs (
    user_id uuid NOT NULL,
    status character varying(20) NOT NULL,
    generation_type character varying(50) NOT NULL,
    depth_preference double precision NOT NULL,
    curiosity_preference double precision NOT NULL,
    requested_count integer NOT NULL,
    actual_count integer,
    capsule_ids uuid[],
    progress double precision NOT NULL,
    error_message text,
    duration_ms integer,
    model_used character varying(100),
    scheduled_for timestamp without time zone,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE capsule_generation_jobs OWNER TO postgres;

--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(128),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages OWNER TO postgres;

--
-- Name: chat_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_sessions (
    user_id uuid NOT NULL,
    title character varying(200),
    is_active boolean DEFAULT true NOT NULL,
    last_message_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_sessions OWNER TO postgres;

--
-- Name: cognitive_fragments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE cognitive_fragments (
    user_id uuid NOT NULL,
    task_id uuid,
    analysis_status analysisstatus NOT NULL,
    error_message character varying(500),
    source_type character varying(20) NOT NULL,
    resource_type character varying(20) NOT NULL,
    resource_url character varying(512),
    content text NOT NULL,
    sentiment character varying(20),
    persona_version character varying(50),
    source_event_id character varying(64),
    sensitive_tags_encrypted text,
    sensitive_tags_version integer,
    sensitive_tags_key_id character varying(100),
    tags json,
    error_tags json,
    context_tags json,
    severity integer NOT NULL,
    embedding vector(1024),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE cognitive_fragments OWNER TO postgres;

--
-- Name: collaborative_galaxies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE collaborative_galaxies (
    name character varying(200) NOT NULL,
    description text,
    created_by uuid NOT NULL,
    visibility character varying(20) NOT NULL,
    subject_id integer,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE collaborative_galaxies OWNER TO postgres;

--
-- Name: compliance_check_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE compliance_check_logs (
    id uuid NOT NULL,
    check_type character varying(100) NOT NULL,
    check_name character varying(200) NOT NULL,
    standard character varying(100),
    status character varying(20) NOT NULL,
    details json,
    findings json,
    executed_by uuid,
    automated character varying(10) NOT NULL,
    executed_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE compliance_check_logs OWNER TO postgres;

--
-- Name: context_budget_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE context_budget_profiles (
    intent character varying(30) NOT NULL,
    bucket character varying(30) NOT NULL,
    multiplier double precision NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE context_budget_profiles OWNER TO postgres;

--
-- Name: context_pack_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE context_pack_feedback (
    pack_run_id uuid NOT NULL,
    feedback_type character varying(20) NOT NULL,
    reasons jsonb,
    score double precision,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE context_pack_feedback OWNER TO postgres;

--
-- Name: context_pack_runs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE context_pack_runs (
    user_id uuid NOT NULL,
    intent character varying(30) NOT NULL,
    budgets jsonb NOT NULL,
    token_usage jsonb NOT NULL,
    memory_counts jsonb NOT NULL,
    evidence_score_avg double precision,
    response_id uuid,
    request_id character varying(100),
    trace_id character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE context_pack_runs OWNER TO postgres;

--
-- Name: crdt_operation_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE crdt_operation_log (
    id bigint NOT NULL,
    galaxy_id uuid NOT NULL,
    user_id uuid NOT NULL,
    operation_type character varying(50),
    operation_data jsonb,
    "timestamp" timestamp without time zone NOT NULL
);


ALTER TABLE crdt_operation_log OWNER TO postgres;

--
-- Name: crdt_operation_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE crdt_operation_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE crdt_operation_log_id_seq OWNER TO postgres;

--
-- Name: crdt_operation_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE crdt_operation_log_id_seq OWNED BY crdt_operation_log.id;


--
-- Name: crdt_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE crdt_snapshots (
    galaxy_id uuid NOT NULL,
    state_data bytea NOT NULL,
    operation_count integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE crdt_snapshots OWNER TO postgres;

--
-- Name: crypto_shredding_certificates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE crypto_shredding_certificates (
    user_id uuid NOT NULL,
    key_id character varying(128) NOT NULL,
    destruction_time timestamp without time zone NOT NULL,
    cloud_provider_ack text,
    certificate_data jsonb,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE crypto_shredding_certificates OWNER TO postgres;

--
-- Name: curiosity_capsules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE curiosity_capsules (
    user_id uuid NOT NULL,
    title character varying(255) NOT NULL,
    content text NOT NULL,
    related_subject character varying(255),
    related_task_id uuid,
    is_read boolean NOT NULL,
    depth_level depthlevel,
    generation_method character varying(100),
    source_context jsonb,
    quality_score double precision,
    feedback_count integer NOT NULL,
    share_count integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    personalization_context json
);


ALTER TABLE curiosity_capsules OWNER TO postgres;

--
-- Name: data_access_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE data_access_logs (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    ip_address character varying(45),
    user_agent text,
    resource_type character varying(100) NOT NULL,
    resource_id character varying(100) NOT NULL,
    action character varying(50) NOT NULL,
    request_method character varying(10),
    request_path character varying(500),
    request_params json,
    response_status character varying(10),
    accessed_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE data_access_logs OWNER TO postgres;

--
-- Name: decision_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE decision_records (
    user_id uuid NOT NULL,
    module character varying(50) NOT NULL,
    action character varying(100) NOT NULL,
    preference_version integer NOT NULL,
    preferences_snapshot jsonb,
    outcome character varying(500),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE decision_records OWNER TO postgres;

--
-- Name: dictionary_entries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE dictionary_entries (
    word character varying(100) NOT NULL,
    phonetic character varying(100),
    pos character varying(50),
    definitions json NOT NULL,
    examples json,
    source character varying(50),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE dictionary_entries OWNER TO postgres;

--
-- Name: dlq_replay_audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE dlq_replay_audit_logs (
    message_id character varying(128) NOT NULL,
    admin_id uuid NOT NULL,
    approver_id uuid NOT NULL,
    reason_code character varying(64) NOT NULL,
    payload_hash character varying(128) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE dlq_replay_audit_logs OWNER TO postgres;

--
-- Name: document_chunks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE document_chunks (
    file_id uuid NOT NULL,
    user_id uuid NOT NULL,
    chunk_index integer NOT NULL,
    page_numbers json,
    section_title character varying(255),
    bbox json,
    quality_score double precision,
    pipeline_version character varying(50),
    content text NOT NULL,
    embedding vector(1024),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE document_chunks OWNER TO postgres;

--
-- Name: episodic_memories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE episodic_memories (
    user_id uuid NOT NULL,
    summary character varying(2000) NOT NULL,
    source_type character varying(30) NOT NULL,
    source_id character varying(100),
    occurred_at timestamp without time zone NOT NULL,
    importance_score double precision,
    evidence_score double precision NOT NULL,
    correction_count integer NOT NULL,
    tags jsonb,
    evidence_refs jsonb NOT NULL,
    evidence_missing boolean NOT NULL,
    evidence_checked_at timestamp without time zone,
    evidence_snapshot jsonb,
    retracted_at timestamp without time zone,
    embedding vector(1024),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    last_consumed_at timestamp without time zone,
    archived_at timestamp without time zone
);


ALTER TABLE episodic_memories OWNER TO postgres;

--
-- Name: error_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE error_records (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    subject_code character varying(50) NOT NULL,
    chapter character varying(100),
    question_text text,
    question_image_url character varying(500),
    user_answer text,
    correct_answer text,
    mastery_level double precision,
    easiness_factor double precision,
    review_count integer,
    interval_days double precision,
    next_review_at timestamp with time zone DEFAULT now(),
    last_reviewed_at timestamp with time zone,
    latest_analysis jsonb,
    cognitive_tags character varying[],
    ai_analysis_summary text,
    linked_knowledge_node_ids uuid[],
    suggested_concepts text[],
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    is_deleted boolean
);


ALTER TABLE error_records OWNER TO postgres;

--
-- Name: event_outbox; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE event_outbox (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    aggregate_type character varying(100) NOT NULL,
    aggregate_id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    event_version integer DEFAULT 1 NOT NULL,
    payload jsonb NOT NULL,
    metadata jsonb,
    sequence_number bigint DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    published_at timestamp with time zone
);


ALTER TABLE event_outbox OWNER TO postgres;

--
-- Name: event_sequence_counters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE event_sequence_counters (
    aggregate_type character varying(100) NOT NULL,
    aggregate_id uuid NOT NULL,
    next_sequence bigint DEFAULT 1 NOT NULL
);


ALTER TABLE event_sequence_counters OWNER TO postgres;

--
-- Name: event_store; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE event_store (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    aggregate_type character varying(100) NOT NULL,
    aggregate_id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    event_version integer NOT NULL,
    sequence_number bigint NOT NULL,
    payload jsonb NOT NULL,
    metadata jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE event_store OWNER TO postgres;

--
-- Name: evolution_predictions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE evolution_predictions (
    memory_id uuid NOT NULL,
    prediction_type character varying(50) NOT NULL,
    probability double precision NOT NULL,
    time_horizon integer,
    predicted_value jsonb,
    predicted_confidence double precision,
    factors jsonb,
    similar_evolutions integer[],
    created_at timestamp without time zone NOT NULL,
    actualized_at timestamp without time zone,
    actualization_error double precision,
    id uuid NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE evolution_predictions OWNER TO postgres;

--
-- Name: expansion_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE expansion_feedback (
    expansion_queue_id uuid,
    trigger_node_id uuid NOT NULL,
    user_id uuid NOT NULL,
    rating integer,
    implicit_score double precision,
    feedback_type character varying(20),
    prompt_version character varying(50),
    model_name character varying(50),
    meta_data json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE expansion_feedback OWNER TO postgres;

--
-- Name: focus_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE focus_sessions (
    user_id uuid NOT NULL,
    task_id uuid,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    duration_minutes integer NOT NULL,
    focus_type focustype NOT NULL,
    status focusstatus NOT NULL,
    white_noise_type integer,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE focus_sessions OWNER TO postgres;

--
-- Name: friendships; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE friendships (
    user_id uuid NOT NULL,
    friend_id uuid NOT NULL,
    status friendshipstatus NOT NULL,
    initiated_by uuid NOT NULL,
    match_reason json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE friendships OWNER TO postgres;

--
-- Name: galaxy_skins; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE galaxy_skins (
    id character varying(50) NOT NULL,
    name character varying(100),
    description character varying(500),
    preview_url character varying(500),
    unlock_type character varying(50),
    unlock_requirement json,
    skin_config json,
    rarity achievementrarity,
    sort_order integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE galaxy_skins OWNER TO postgres;

--
-- Name: galaxy_user_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE galaxy_user_permissions (
    galaxy_id uuid NOT NULL,
    user_id uuid NOT NULL,
    permission_level character varying(20) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE galaxy_user_permissions OWNER TO postgres;

--
-- Name: group_files; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE group_files (
    group_id uuid NOT NULL,
    file_id uuid NOT NULL,
    shared_by_id uuid NOT NULL,
    category character varying(64),
    tags json NOT NULL,
    view_role grouprole NOT NULL,
    download_role grouprole NOT NULL,
    manage_role grouprole NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE group_files OWNER TO postgres;

--
-- Name: group_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE group_members (
    group_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role grouprole NOT NULL,
    is_muted boolean NOT NULL,
    mute_until timestamp without time zone,
    warn_count integer NOT NULL,
    notifications_enabled boolean NOT NULL,
    flame_contribution integer NOT NULL,
    tasks_completed integer NOT NULL,
    checkin_streak integer NOT NULL,
    last_checkin_date timestamp without time zone,
    joined_at timestamp without time zone NOT NULL,
    last_active_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE group_members OWNER TO postgres;

--
-- Name: group_message_reads; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE group_message_reads (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    message_id uuid NOT NULL,
    user_id uuid NOT NULL,
    read_at timestamp without time zone NOT NULL
);


ALTER TABLE group_message_reads OWNER TO postgres;

--
-- Name: group_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE group_messages (
    group_id uuid NOT NULL,
    sender_id uuid,
    message_type messagetype NOT NULL,
    content text,
    content_data json,
    reply_to_id uuid,
    thread_root_id uuid,
    is_revoked boolean NOT NULL,
    revoked_at timestamp without time zone,
    edited_at timestamp without time zone,
    reactions json,
    mention_user_ids json,
    encrypted_content text,
    content_signature character varying(512),
    encryption_version integer,
    topic character varying(100),
    tags json,
    forwarded_from_id uuid,
    forward_count integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE group_messages OWNER TO postgres;

--
-- Name: group_task_claims; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE group_task_claims (
    group_task_id uuid NOT NULL,
    user_id uuid NOT NULL,
    personal_task_id uuid,
    is_completed boolean NOT NULL,
    completed_at timestamp without time zone,
    claimed_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE group_task_claims OWNER TO postgres;

--
-- Name: group_tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE group_tasks (
    group_id uuid NOT NULL,
    created_by uuid NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    tags json NOT NULL,
    estimated_minutes integer NOT NULL,
    difficulty integer NOT NULL,
    total_claims integer NOT NULL,
    total_completions integer NOT NULL,
    due_date timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE group_tasks OWNER TO postgres;

--
-- Name: groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE groups (
    name character varying(100) NOT NULL,
    description text,
    avatar_url character varying(500),
    type grouptype NOT NULL,
    focus_tags json NOT NULL,
    deadline timestamp without time zone,
    sprint_goal text,
    max_members integer NOT NULL,
    is_public boolean NOT NULL,
    join_requires_approval boolean NOT NULL,
    total_flame_power integer NOT NULL,
    today_checkin_count integer NOT NULL,
    total_tasks_completed integer NOT NULL,
    announcement text,
    announcement_updated_at timestamp without time zone,
    keyword_filters json,
    mute_all boolean NOT NULL,
    slow_mode_seconds integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE groups OWNER TO postgres;

--
-- Name: idempotency_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE idempotency_keys (
    key character varying(64) NOT NULL,
    user_id uuid NOT NULL,
    response json NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone NOT NULL
);


ALTER TABLE idempotency_keys OWNER TO postgres;

--
-- Name: intervention_audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE intervention_audit_logs (
    request_id uuid NOT NULL,
    user_id uuid NOT NULL,
    action character varying(40) NOT NULL,
    guardrail_result json,
    decision_trace json,
    evidence_refs json,
    requested_level character varying(40) NOT NULL,
    final_level character varying(40) NOT NULL,
    policy_version character varying(50),
    model_version character varying(80),
    schema_version character varying(50),
    occurred_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE intervention_audit_logs OWNER TO postgres;

--
-- Name: intervention_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE intervention_feedback (
    request_id uuid NOT NULL,
    user_id uuid NOT NULL,
    feedback_type character varying(40) NOT NULL,
    extra_data json,
    idempotency_key character varying(200) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE intervention_feedback OWNER TO postgres;

--
-- Name: intervention_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE intervention_requests (
    user_id uuid NOT NULL,
    dedupe_key character varying(200),
    topic character varying(120),
    requested_level character varying(40) NOT NULL,
    final_level character varying(40) NOT NULL,
    status character varying(40) NOT NULL,
    reason json,
    content json,
    cooldown_policy json,
    delivery_method character varying(20),
    template_id character varying(100),
    template_variant_id character varying(100),
    scaffolding_level integer,
    intent_type character varying(50),
    schema_version character varying(50) NOT NULL,
    policy_version character varying(50),
    model_version character varying(80),
    expires_at timestamp without time zone,
    is_retractable boolean NOT NULL,
    supersedes_id uuid,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE intervention_requests OWNER TO postgres;

--
-- Name: intervention_templates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE intervention_templates (
    template_id character varying(100) NOT NULL,
    intent_type character varying(50) NOT NULL,
    support_level integer NOT NULL,
    variants json NOT NULL,
    meta json,
    version integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE intervention_templates OWNER TO postgres;

--
-- Name: irt_item_parameters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE irt_item_parameters (
    question_id uuid NOT NULL,
    subject_id character varying(32),
    a double precision NOT NULL,
    b double precision NOT NULL,
    c double precision NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE irt_item_parameters OWNER TO postgres;

--
-- Name: jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE jobs (
    user_id uuid NOT NULL,
    type character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    params json,
    result json,
    error_message text,
    progress integer,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    timeout_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE jobs OWNER TO postgres;

--
-- Name: knowledge_nodes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE knowledge_nodes (
    subject_id integer,
    parent_id uuid,
    name character varying(255) NOT NULL,
    name_en character varying(255),
    description text,
    keywords jsonb,
    importance_level integer NOT NULL,
    is_seed boolean,
    source_type character varying(20),
    source_task_id uuid,
    source_file_id uuid,
    chunk_refs jsonb,
    status character varying(20),
    embedding vector(1024),
    position_x double precision,
    position_y double precision,
    global_spark_count integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE knowledge_nodes OWNER TO postgres;

--
-- Name: legal_holds; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE legal_holds (
    user_id uuid,
    device_id character varying(128),
    case_ref character varying(120) NOT NULL,
    reason text,
    admin_id uuid NOT NULL,
    is_active boolean NOT NULL,
    released_at timestamp without time zone,
    released_by uuid,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE legal_holds OWNER TO postgres;

--
-- Name: login_attempts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE login_attempts (
    user_id uuid,
    username character varying(100) NOT NULL,
    ip_address character varying(45) NOT NULL,
    user_agent character varying(500),
    success boolean NOT NULL,
    attempted_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE login_attempts OWNER TO postgres;

--
-- Name: ltm_daily_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE ltm_daily_snapshots (
    snapshot_date date NOT NULL,
    payload jsonb NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE ltm_daily_snapshots OWNER TO postgres;

--
-- Name: mastery_audit_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE mastery_audit_log (
    id integer NOT NULL,
    node_id uuid NOT NULL,
    user_id uuid NOT NULL,
    old_mastery integer NOT NULL,
    new_mastery integer NOT NULL,
    reason character varying(100) NOT NULL,
    request_id character varying(100),
    revision integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE mastery_audit_log OWNER TO postgres;

--
-- Name: mastery_audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE mastery_audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE mastery_audit_log_id_seq OWNER TO postgres;

--
-- Name: mastery_audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE mastery_audit_log_id_seq OWNED BY mastery_audit_log.id;


--
-- Name: memory_corrections; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE memory_corrections (
    user_id uuid NOT NULL,
    memory_type character varying(30) NOT NULL,
    memory_id uuid NOT NULL,
    action character varying(40) NOT NULL,
    reason character varying(500),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE memory_corrections OWNER TO postgres;

--
-- Name: memory_evolutions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE memory_evolutions (
    memory_id uuid NOT NULL,
    memory_type character varying(50) NOT NULL,
    old_value jsonb NOT NULL,
    new_value jsonb NOT NULL,
    change_type character varying(50) NOT NULL,
    change_reason character varying(100) NOT NULL,
    confidence_delta double precision NOT NULL,
    confidence_before double precision NOT NULL,
    confidence_after double precision NOT NULL,
    evidence_count_before integer NOT NULL,
    evidence_count_after integer NOT NULL,
    new_evidence_ids uuid[],
    impact_score double precision NOT NULL,
    affected_decisions uuid[],
    affected_memories uuid[],
    trigger_event character varying(100),
    trigger_source character varying(100),
    workflow_id character varying(100),
    created_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE memory_evolutions OWNER TO postgres;

--
-- Name: memory_goals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE memory_goals (
    user_id uuid NOT NULL,
    title character varying(255) NOT NULL,
    status character varying(30) NOT NULL,
    target_date date,
    expires_at timestamp without time zone,
    linked_task_id uuid,
    linked_plan_id uuid,
    evidence_score double precision NOT NULL,
    correction_count integer NOT NULL,
    evidence_refs jsonb NOT NULL,
    metadata jsonb,
    evidence_missing boolean NOT NULL,
    evidence_checked_at timestamp without time zone,
    retracted_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    last_consumed_at timestamp without time zone,
    archived_at timestamp without time zone
);


ALTER TABLE memory_goals OWNER TO postgres;

--
-- Name: memory_preferences; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE memory_preferences (
    user_id uuid NOT NULL,
    pref_key character varying(80) NOT NULL,
    pref_value jsonb NOT NULL,
    version integer NOT NULL,
    replaced_by_id uuid,
    confidence double precision,
    evidence_score double precision NOT NULL,
    correction_count integer NOT NULL,
    evidence_refs jsonb NOT NULL,
    evidence_missing boolean NOT NULL,
    evidence_checked_at timestamp without time zone,
    retracted_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    last_consumed_at timestamp without time zone,
    archived_at timestamp without time zone
);


ALTER TABLE memory_preferences OWNER TO postgres;

--
-- Name: memory_rank_policies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE memory_rank_policies (
    scope_type character varying(20) NOT NULL,
    scope_key character varying(120),
    weights jsonb NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE memory_rank_policies OWNER TO postgres;

--
-- Name: message_favorites; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE message_favorites (
    user_id uuid NOT NULL,
    group_message_id uuid,
    private_message_id uuid,
    note text,
    tags json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE message_favorites OWNER TO postgres;

--
-- Name: message_reports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE message_reports (
    reporter_id uuid NOT NULL,
    group_message_id uuid,
    private_message_id uuid,
    reason reportreason NOT NULL,
    description text,
    status reportstatus NOT NULL,
    reviewed_by uuid,
    reviewed_at timestamp without time zone,
    action_taken moderationaction,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE message_reports OWNER TO postgres;

--
-- Name: next_action_selections; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE next_action_selections (
    user_id uuid NOT NULL,
    task_id uuid NOT NULL,
    action_type character varying(50) NOT NULL,
    action_title character varying(255) NOT NULL,
    selected boolean NOT NULL,
    skipped boolean NOT NULL,
    display_position integer,
    displayed_actions_count integer,
    context jsonb,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE next_action_selections OWNER TO postgres;

--
-- Name: nightly_reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE nightly_reviews (
    user_id uuid NOT NULL,
    review_date date NOT NULL,
    summary_text character varying(2000),
    todo_items json,
    evidence_refs json,
    model_version character varying(50),
    status character varying(30) NOT NULL,
    reviewed_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE nightly_reviews OWNER TO postgres;

--
-- Name: node_expansion_queue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE node_expansion_queue (
    trigger_node_id uuid NOT NULL,
    trigger_task_id uuid,
    user_id uuid NOT NULL,
    expansion_context text NOT NULL,
    status character varying(20),
    expanded_nodes json,
    error_message text,
    prompt_version character varying(50),
    model_name character varying(50),
    processed_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE node_expansion_queue OWNER TO postgres;

--
-- Name: node_relations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE node_relations (
    source_node_id uuid NOT NULL,
    target_node_id uuid NOT NULL,
    relation_type character varying(30) NOT NULL,
    strength double precision,
    created_by character varying(20),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE node_relations OWNER TO postgres;

--
-- Name: notification_interactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE notification_interactions (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    user_id uuid NOT NULL,
    notification_type character varying(20) NOT NULL,
    notification_id uuid NOT NULL,
    action_type character varying(40) NOT NULL,
    action_time timestamp without time zone NOT NULL,
    time_to_action integer
);


ALTER TABLE notification_interactions OWNER TO postgres;

--
-- Name: COLUMN notification_interactions.notification_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN notification_interactions.notification_type IS 'system or intervention';


--
-- Name: COLUMN notification_interactions.action_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN notification_interactions.action_type IS 'viewed, clicked, dismissed';


--
-- Name: COLUMN notification_interactions.time_to_action; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN notification_interactions.time_to_action IS 'Seconds from creation to action';


--
-- Name: notification_preferences; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE notification_preferences (
    user_id uuid NOT NULL,
    enable_system boolean NOT NULL,
    enable_interventions boolean NOT NULL,
    notification_level character varying(20) NOT NULL,
    quiet_hours_enabled boolean NOT NULL,
    quiet_hours_start character varying(5),
    quiet_hours_end character varying(5),
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE notification_preferences OWNER TO postgres;

--
-- Name: COLUMN notification_preferences.quiet_hours_start; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN notification_preferences.quiet_hours_start IS 'HH:MM format';


--
-- Name: COLUMN notification_preferences.quiet_hours_end; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN notification_preferences.quiet_hours_end IS 'HH:MM format';


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE notifications (
    user_id uuid NOT NULL,
    title character varying(255) NOT NULL,
    content character varying(1000) NOT NULL,
    type character varying(50) NOT NULL,
    is_read boolean NOT NULL,
    read_at timestamp without time zone,
    data json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE notifications OWNER TO postgres;

--
-- Name: offline_message_queue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE offline_message_queue (
    user_id uuid NOT NULL,
    client_nonce character varying(100) NOT NULL,
    message_type character varying(50) NOT NULL,
    target_id uuid NOT NULL,
    payload json NOT NULL,
    status offlinemessagestatus NOT NULL,
    retry_count integer NOT NULL,
    last_retry_at timestamp without time zone,
    error_message text,
    expires_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE offline_message_queue OWNER TO postgres;

--
-- Name: passive_signals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE passive_signals (
    user_id uuid NOT NULL,
    signal_type character varying(50) NOT NULL,
    intervention_id uuid,
    "timestamp" timestamp without time zone NOT NULL,
    context json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE passive_signals OWNER TO postgres;

--
-- Name: persona_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE persona_snapshots (
    user_id uuid NOT NULL,
    persona_version character varying(50) NOT NULL,
    audit_token character varying(128),
    source_event_id character varying(64),
    snapshot_data jsonb NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE persona_snapshots OWNER TO postgres;

--
-- Name: photon_transaction_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE photon_transaction_history (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    transaction_type character varying(50) NOT NULL,
    amount integer NOT NULL,
    balance_before integer NOT NULL,
    balance_after integer NOT NULL,
    source character varying(255),
    related_item_id character varying(50),
    extra_data json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE photon_transaction_history OWNER TO postgres;

--
-- Name: COLUMN photon_transaction_history.amount; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN photon_transaction_history.amount IS '变动数量（正数为增加，负数为减少）';


--
-- Name: COLUMN photon_transaction_history.balance_before; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN photon_transaction_history.balance_before IS '交易前余额';


--
-- Name: COLUMN photon_transaction_history.balance_after; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN photon_transaction_history.balance_after IS '交易后余额';


--
-- Name: COLUMN photon_transaction_history.source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN photon_transaction_history.source IS '来源描述';


--
-- Name: COLUMN photon_transaction_history.related_item_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN photon_transaction_history.related_item_id IS '相关物品ID（如商城物品ID、成就ID等）';


--
-- Name: COLUMN photon_transaction_history.extra_data; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN photon_transaction_history.extra_data IS '额外元数据（JSON格式）';


--
-- Name: plan_execution_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE plan_execution_records (
    plan_id uuid NOT NULL,
    user_id uuid NOT NULL,
    validation_status character varying(20) NOT NULL,
    quality_score double precision,
    criteria_results jsonb,
    total_tools integer,
    successful_tools integer,
    failed_tools integer,
    issues jsonb,
    user_satisfaction integer,
    user_feedback text,
    applied_to_learning boolean,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE plan_execution_records OWNER TO postgres;

--
-- Name: plan_states; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE plan_states (
    plan_id uuid NOT NULL,
    user_id uuid NOT NULL,
    facts jsonb NOT NULL,
    milestones jsonb NOT NULL,
    task_index jsonb NOT NULL,
    task_summaries jsonb NOT NULL,
    feedback_log jsonb NOT NULL,
    constraints jsonb NOT NULL,
    version integer NOT NULL,
    consecutive_rejection_count integer NOT NULL,
    is_focus boolean NOT NULL,
    last_focus_time timestamp without time zone,
    parallel_priority integer NOT NULL,
    status character varying(20) NOT NULL,
    archived_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE plan_states OWNER TO postgres;

--
-- Name: plans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE plans (
    user_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    type plantype NOT NULL,
    description text,
    plan_stage planstage NOT NULL,
    target_date date,
    daily_available_minutes integer NOT NULL,
    total_estimated_hours double precision,
    subject character varying(100),
    mastery_level double precision NOT NULL,
    progress double precision NOT NULL,
    is_active boolean NOT NULL,
    priority planpriority NOT NULL,
    is_primary boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    source character varying(32),
    source_metadata jsonb
);


ALTER TABLE plans OWNER TO postgres;

--
-- Name: post_likes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE post_likes (
    user_id uuid NOT NULL,
    post_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE post_likes OWNER TO postgres;

--
-- Name: posts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE posts (
    user_id uuid NOT NULL,
    content text,
    image_urls json,
    topic character varying(100),
    visibility character varying(20) NOT NULL,
    like_count integer,
    comment_count integer,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE posts OWNER TO postgres;

--
-- Name: private_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE private_messages (
    sender_id uuid NOT NULL,
    receiver_id uuid NOT NULL,
    message_type messagetype NOT NULL,
    content text,
    content_data json,
    reply_to_id uuid,
    thread_root_id uuid,
    is_read boolean NOT NULL,
    read_at timestamp without time zone,
    is_revoked boolean NOT NULL,
    revoked_at timestamp without time zone,
    edited_at timestamp without time zone,
    reactions json,
    mention_user_ids json,
    encrypted_content text,
    content_signature character varying(512),
    encryption_version integer,
    topic character varying(100),
    tags json,
    forwarded_from_id uuid,
    forward_count integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE private_messages OWNER TO postgres;

--
-- Name: processed_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE processed_events (
    event_id character varying(100) NOT NULL,
    consumer_group character varying(100) NOT NULL,
    processed_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE processed_events OWNER TO postgres;

--
-- Name: projection_metadata; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE projection_metadata (
    projection_name character varying(100) NOT NULL,
    last_processed_position character varying(100),
    last_processed_at timestamp without time zone,
    version integer DEFAULT 1 NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    error_message text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE projection_metadata OWNER TO postgres;

--
-- Name: projection_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE projection_snapshots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    projection_name character varying(100) NOT NULL,
    aggregate_id uuid,
    snapshot_data jsonb NOT NULL,
    stream_position character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE projection_snapshots OWNER TO postgres;

--
-- Name: push_histories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE push_histories (
    user_id uuid NOT NULL,
    trigger_type character varying(50) NOT NULL,
    content_hash character varying(64),
    status character varying(50) NOT NULL,
    interaction_type character varying(50),
    interacted_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE push_histories OWNER TO postgres;

--
-- Name: push_preferences; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE push_preferences (
    user_id uuid NOT NULL,
    active_slots json,
    timezone character varying(50) NOT NULL,
    enable_curiosity boolean NOT NULL,
    persona_type character varying(50) NOT NULL,
    daily_cap integer NOT NULL,
    last_push_time timestamp without time zone,
    consecutive_ignores integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE push_preferences OWNER TO postgres;

--
-- Name: recommendation_cache; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE recommendation_cache (
    user_id uuid NOT NULL,
    recommendation_type character varying(50) NOT NULL,
    cached_recommendations json NOT NULL,
    generated_at timestamp without time zone NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    hit_count integer DEFAULT 0 NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE recommendation_cache OWNER TO postgres;

--
-- Name: response_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE response_feedback (
    user_id uuid NOT NULL,
    response_id uuid NOT NULL,
    trace_id character varying NOT NULL,
    workflow_id character varying(64),
    prompt_version character varying(50),
    feedback_type smallint NOT NULL,
    reasons jsonb,
    free_text character varying,
    meta jsonb,
    intervention_id uuid,
    scaffolding_level integer,
    template_variant_id character varying(100),
    time_to_response integer,
    action_taken character varying(40),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE response_feedback OWNER TO postgres;

--
-- Name: review_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE review_feedback (
    feedback_id character varying(64) NOT NULL,
    review_id character varying(64) NOT NULL,
    user_id uuid,
    feedback_type character varying(32) NOT NULL,
    rating integer,
    comment text,
    issues_reported jsonb,
    original_score double precision NOT NULL,
    original_decision character varying(32),
    was_reflected boolean NOT NULL,
    was_helpful boolean,
    was_accurate boolean,
    inaccurate_points jsonb,
    specificity_level character varying(32),
    tags jsonb,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE review_feedback OWNER TO postgres;

--
-- Name: review_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE review_history (
    review_id character varying(64) NOT NULL,
    target_id character varying(128) NOT NULL,
    target_type character varying(50) NOT NULL,
    user_id uuid,
    session_id character varying(128),
    decision character varying(32) NOT NULL,
    overall_score double precision NOT NULL,
    metrics jsonb,
    issues_count integer NOT NULL,
    critical_count integer NOT NULL,
    warning_count integer NOT NULL,
    reflection_round integer NOT NULL,
    reflection_outcome character varying(64),
    score_delta double precision NOT NULL,
    user_feedback character varying(64),
    user_satisfied boolean,
    feedback_timestamp timestamp without time zone,
    reviewer_model character varying(100),
    review_duration_ms integer NOT NULL,
    requires_reflection boolean NOT NULL,
    user_query text,
    content_snapshot text,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE review_history OWNER TO postgres;

--
-- Name: review_overrides; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE review_overrides (
    override_id character varying(64) NOT NULL,
    review_id character varying(64) NOT NULL,
    user_id uuid,
    original_decision character varying(32) NOT NULL,
    new_decision character varying(32) NOT NULL,
    override_type character varying(64) NOT NULL,
    reason text,
    was_correct boolean,
    admin_reviewed boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE review_overrides OWNER TO postgres;

--
-- Name: scaffolding_states; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE scaffolding_states (
    user_id uuid NOT NULL,
    capability_level double precision NOT NULL,
    current_zone character varying(20) NOT NULL,
    support_level integer NOT NULL,
    template_variant_id character varying(100),
    consecutive_successes integer NOT NULL,
    consecutive_failures integer NOT NULL,
    last_intervention_timestamp timestamp without time zone,
    history json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE scaffolding_states OWNER TO postgres;

--
-- Name: security_audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE security_audit_logs (
    id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    threat_level character varying(20) NOT NULL,
    user_id uuid,
    ip_address character varying(45),
    user_agent text,
    resource character varying(500),
    action character varying(100),
    details json,
    "timestamp" timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE security_audit_logs OWNER TO postgres;

--
-- Name: seed_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE seed_items (
    library_id uuid NOT NULL,
    item_type character varying(50) NOT NULL,
    title character varying(300),
    content text,
    content_data jsonb,
    subject character varying(100),
    difficulty_level character varying(20),
    tags jsonb,
    embedding vector(1024),
    order_index integer NOT NULL,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE seed_items OWNER TO postgres;

--
-- Name: seed_libraries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE seed_libraries (
    name character varying(200) NOT NULL,
    description text,
    category character varying(50) NOT NULL,
    visibility character varying(20) NOT NULL,
    owner_id uuid,
    language character varying(10) NOT NULL,
    tags jsonb,
    extra_metadata jsonb,
    is_official boolean NOT NULL,
    is_featured boolean NOT NULL,
    usage_count integer NOT NULL,
    quality_score double precision,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE seed_libraries OWNER TO postgres;

--
-- Name: semantic_links; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE semantic_links (
    source_type character varying(30) NOT NULL,
    source_id character varying(64) NOT NULL,
    target_type character varying(30) NOT NULL,
    target_id character varying(64) NOT NULL,
    relation_type character varying(40) NOT NULL,
    strength double precision NOT NULL,
    created_by character varying(20) NOT NULL,
    evidence_refs json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE semantic_links OWNER TO postgres;

--
-- Name: shared_resources; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE shared_resources (
    group_id uuid,
    target_user_id uuid,
    shared_by uuid NOT NULL,
    plan_id uuid,
    task_id uuid,
    cognitive_fragment_id uuid,
    curiosity_capsule_id uuid,
    behavior_pattern_id uuid,
    permission character varying(20) NOT NULL,
    comment text,
    view_count integer,
    save_count integer,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    knowledge_node_id uuid
);


ALTER TABLE shared_resources OWNER TO postgres;

--
-- Name: shop_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE shop_items (
    id character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    item_type character varying(50) NOT NULL,
    category character varying(50) NOT NULL,
    price_photons integer NOT NULL,
    original_price integer,
    discount_percent integer,
    is_available boolean NOT NULL,
    is_limited boolean NOT NULL,
    stock_quantity integer,
    icon_url character varying(500),
    rarity character varying(50) NOT NULL,
    item_config json,
    sort_order integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE shop_items OWNER TO postgres;

--
-- Name: COLUMN shop_items.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.id IS '物品ID（如：skin_galaxy_001）';


--
-- Name: COLUMN shop_items.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.name IS '物品名称';


--
-- Name: COLUMN shop_items.description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.description IS '物品描述';


--
-- Name: COLUMN shop_items.item_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.item_type IS '物品类型';


--
-- Name: COLUMN shop_items.category; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.category IS '分类（如：galaxy_skin、achievement_title等）';


--
-- Name: COLUMN shop_items.price_photons; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.price_photons IS '当前价格（光子）';


--
-- Name: COLUMN shop_items.original_price; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.original_price IS '原价（用于折扣显示）';


--
-- Name: COLUMN shop_items.discount_percent; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.discount_percent IS '折扣百分比（0-100）';


--
-- Name: COLUMN shop_items.is_available; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.is_available IS '是否可购买';


--
-- Name: COLUMN shop_items.is_limited; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.is_limited IS '是否限量';


--
-- Name: COLUMN shop_items.stock_quantity; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.stock_quantity IS '库存数量（限量物品使用）';


--
-- Name: COLUMN shop_items.icon_url; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.icon_url IS '物品图标URL';


--
-- Name: COLUMN shop_items.rarity; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.rarity IS '物品稀有度';


--
-- Name: COLUMN shop_items.item_config; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.item_config IS '物品配置（如皮肤ID、称号文本、消耗品效果等）';


--
-- Name: COLUMN shop_items.sort_order; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_items.sort_order IS '排序权重（越大越靠前）';


--
-- Name: shop_purchases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE shop_purchases (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    item_id character varying(50) NOT NULL,
    price_paid integer NOT NULL,
    photon_balance_before integer NOT NULL,
    photon_balance_after integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE shop_purchases OWNER TO postgres;

--
-- Name: COLUMN shop_purchases.price_paid; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_purchases.price_paid IS '实际支付价格';


--
-- Name: COLUMN shop_purchases.photon_balance_before; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_purchases.photon_balance_before IS '购买前光子余额';


--
-- Name: COLUMN shop_purchases.photon_balance_after; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN shop_purchases.photon_balance_after IS '购买后光子余额';


--
-- Name: smoke_document_vectors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE smoke_document_vectors (
    id uuid NOT NULL,
    file_name text NOT NULL,
    chunk_text text NOT NULL,
    embedding vector(1024) NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE smoke_document_vectors OWNER TO postgres;

--
-- Name: spark_contracts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE spark_contracts (
    user_id uuid NOT NULL,
    target_study_minutes integer,
    target_days integer,
    photon_stake integer,
    status contractstatus,
    start_date timestamp without time zone NOT NULL,
    end_date timestamp without time zone NOT NULL,
    current_days integer,
    current_minutes integer,
    completed_at timestamp without time zone,
    reward_multiplier double precision,
    failed_at timestamp without time zone,
    failure_reason character varying(200),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE spark_contracts OWNER TO postgres;

--
-- Name: stored_files; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE stored_files (
    user_id uuid NOT NULL,
    file_name character varying(255) NOT NULL,
    mime_type character varying(150) NOT NULL,
    file_size bigint NOT NULL,
    bucket character varying(128) NOT NULL,
    object_key character varying(512) NOT NULL,
    status character varying(32) NOT NULL,
    visibility character varying(32) NOT NULL,
    retention_policy character varying(32) NOT NULL,
    error_message character varying(255),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE stored_files OWNER TO postgres;

--
-- Name: strategy_nodes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE strategy_nodes (
    user_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    description character varying(2000),
    subject_code character varying(50),
    tags json,
    content_hash character varying(64),
    source_type character varying(20) NOT NULL,
    evidence_refs json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE strategy_nodes OWNER TO postgres;

--
-- Name: study_buddies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE study_buddies (
    user1_id uuid NOT NULL,
    user2_id uuid NOT NULL,
    status character varying(20),
    connection_strength double precision,
    mutual_study_days integer,
    last_mutual_study_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE study_buddies OWNER TO postgres;

--
-- Name: study_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE study_records (
    user_id uuid NOT NULL,
    node_id uuid NOT NULL,
    task_id uuid,
    study_minutes integer NOT NULL,
    mastery_delta double precision NOT NULL,
    initial_mastery double precision,
    record_type character varying(20),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE study_records OWNER TO postgres;

--
-- Name: subjects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE subjects (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    aliases json,
    category character varying(50),
    sector_code character varying(20) DEFAULT 'VOID'::character varying NOT NULL,
    hex_color character varying(7),
    glow_color character varying(7),
    position_angle double precision,
    icon_name character varying(50),
    is_active boolean,
    sort_order integer,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE subjects OWNER TO postgres;

--
-- Name: subjects_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE subjects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE subjects_id_seq OWNER TO postgres;

--
-- Name: subjects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE subjects_id_seq OWNED BY subjects.id;


--
-- Name: subtasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE subtasks (
    parent_task_id uuid NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    "order" integer NOT NULL,
    status subtaskstatus NOT NULL,
    completed_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    knowledge_node_id uuid,
    estimated_minutes integer DEFAULT 25,
    guide_content text
);


ALTER TABLE subtasks OWNER TO postgres;

--
-- Name: system_config_change_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE system_config_change_logs (
    id uuid NOT NULL,
    config_key character varying(200) NOT NULL,
    old_value json,
    new_value json NOT NULL,
    change_type character varying(50) NOT NULL,
    changed_by uuid NOT NULL,
    ip_address character varying(45),
    user_agent text,
    reason text,
    impact_level character varying(20),
    changed_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE system_config_change_logs OWNER TO postgres;

--
-- Name: task_feedbacks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE task_feedbacks (
    user_id uuid NOT NULL,
    task_id uuid NOT NULL,
    completion_quality integer,
    feedback_text text,
    category character varying(50),
    inferred_depth_delta double precision,
    inferred_difficulty_delta double precision,
    task_difficulty_snapshot integer,
    task_type_snapshot character varying(50),
    actual_minutes_snapshot integer,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    reflection_payload jsonb
);


ALTER TABLE task_feedbacks OWNER TO postgres;

--
-- Name: task_knowledge_links; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE task_knowledge_links (
    task_id uuid NOT NULL,
    knowledge_node_id uuid NOT NULL,
    relation_type character varying(50) NOT NULL,
    strength double precision,
    notes text,
    order_index integer NOT NULL,
    is_primary boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE task_knowledge_links OWNER TO postgres;

--
-- Name: task_resource_links; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE task_resource_links (
    task_id uuid NOT NULL,
    resource_type character varying(50) NOT NULL,
    resource_id uuid,
    title character varying(255),
    url character varying(500),
    summary text,
    metadata jsonb,
    order_index integer NOT NULL,
    is_primary boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE task_resource_links OWNER TO postgres;

--
-- Name: tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE tasks (
    user_id uuid NOT NULL,
    plan_id uuid,
    title character varying(255) NOT NULL,
    type tasktype NOT NULL,
    tags jsonb NOT NULL,
    estimated_minutes integer NOT NULL,
    difficulty integer NOT NULL,
    energy_cost integer NOT NULL,
    guide_content text,
    status taskstatus NOT NULL,
    started_at timestamp without time zone,
    confirmed_at timestamp without time zone,
    completed_at timestamp without time zone,
    tool_result_id character varying(50),
    actual_minutes integer,
    user_note text,
    priority integer NOT NULL,
    due_date date,
    knowledge_node_id uuid,
    auto_expand_enabled boolean,
    subtasks_total integer NOT NULL,
    subtasks_completed integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE tasks OWNER TO postgres;

--
-- Name: token_usage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE token_usage (
    user_id uuid NOT NULL,
    session_id character varying(100) NOT NULL,
    request_id character varying(100) NOT NULL,
    prompt_tokens integer NOT NULL,
    completion_tokens integer NOT NULL,
    total_tokens integer NOT NULL,
    model character varying(100) NOT NULL,
    cost double precision,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE token_usage OWNER TO postgres;

--
-- Name: tracking_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE tracking_events (
    event_id character varying(64) NOT NULL,
    user_id uuid NOT NULL,
    event_type character varying(120) NOT NULL,
    schema_version character varying(50) NOT NULL,
    source character varying(50) NOT NULL,
    ts_ms bigint NOT NULL,
    entities json,
    payload json,
    received_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE tracking_events OWNER TO postgres;

--
-- Name: user_achievements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_achievements (
    user_id uuid NOT NULL,
    achievement_id character varying(50) NOT NULL,
    progress double precision,
    progress_value integer,
    progress_target integer,
    unlocked_at timestamp without time zone,
    is_pinned boolean,
    share_count integer,
    is_first_unlocker boolean,
    last_progress_update timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_achievements OWNER TO postgres;

--
-- Name: user_blocks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_blocks (
    id uuid NOT NULL,
    blocker_id uuid NOT NULL,
    blocked_id uuid NOT NULL,
    reason character varying(500),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_blocks OWNER TO postgres;

--
-- Name: COLUMN user_blocks.blocker_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN user_blocks.blocker_id IS '执行拉黑的用户ID';


--
-- Name: COLUMN user_blocks.blocked_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN user_blocks.blocked_id IS '被拉黑的用户ID';


--
-- Name: COLUMN user_blocks.reason; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN user_blocks.reason IS '拉黑原因';


--
-- Name: COLUMN user_blocks.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN user_blocks.created_at IS '拉黑时间';


--
-- Name: COLUMN user_blocks.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN user_blocks.updated_at IS '更新时间';


--
-- Name: COLUMN user_blocks.deleted_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN user_blocks.deleted_at IS '软删除时间（解除拉黑）';


--
-- Name: user_consumables; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_consumables (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    consumable_id character varying(50) NOT NULL,
    effect_type character varying(50) NOT NULL,
    quantity integer NOT NULL,
    expires_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_consumables OWNER TO postgres;

--
-- Name: COLUMN user_consumables.effect_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN user_consumables.effect_type IS '效果类型';


--
-- Name: COLUMN user_consumables.quantity; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN user_consumables.quantity IS '数量';


--
-- Name: COLUMN user_consumables.expires_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN user_consumables.expires_at IS '过期时间（NULL表示永久有效）';


--
-- Name: user_daily_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_daily_metrics (
    user_id uuid NOT NULL,
    date date NOT NULL,
    total_focus_minutes integer,
    tasks_completed integer,
    tasks_created integer,
    nodes_studied integer,
    mastery_gained double precision,
    review_count integer,
    average_mood double precision,
    anxiety_score double precision,
    chat_messages_count integer,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_daily_metrics OWNER TO postgres;

--
-- Name: user_devices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_devices (
    user_id uuid NOT NULL,
    device_id character varying(255) NOT NULL,
    platform character varying(50) NOT NULL,
    push_token character varying(500) NOT NULL,
    token_type character varying(50) NOT NULL,
    device_name character varying(100),
    app_version character varying(50),
    os_version character varying(50),
    is_active boolean NOT NULL,
    last_used_at timestamp without time zone,
    device_metadata json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_devices OWNER TO postgres;

--
-- Name: user_encryption_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_encryption_keys (
    user_id uuid NOT NULL,
    public_key text NOT NULL,
    key_type character varying(50) NOT NULL,
    device_id character varying(100),
    is_active boolean NOT NULL,
    expires_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_encryption_keys OWNER TO postgres;

--
-- Name: user_galaxy_skins; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_galaxy_skins (
    user_id uuid NOT NULL,
    skin_id character varying(50) NOT NULL,
    unlocked_at timestamp without time zone NOT NULL,
    unlock_source character varying(50),
    is_equipped boolean,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_galaxy_skins OWNER TO postgres;

--
-- Name: user_intervention_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_intervention_settings (
    user_id uuid NOT NULL,
    interrupt_threshold double precision NOT NULL,
    daily_interrupt_budget integer NOT NULL,
    cooldown_minutes integer NOT NULL,
    quiet_hours json,
    topic_allowlist json,
    topic_blocklist json,
    do_not_disturb boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_intervention_settings OWNER TO postgres;

--
-- Name: user_irt_ability; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_irt_ability (
    user_id uuid NOT NULL,
    subject_id character varying(32),
    theta double precision NOT NULL,
    last_updated_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_irt_ability OWNER TO postgres;

--
-- Name: user_item_interactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_item_interactions (
    user_id uuid NOT NULL,
    item_id uuid NOT NULL,
    item_type character varying(50) NOT NULL,
    interaction_type character varying(50) NOT NULL,
    interaction_weight double precision DEFAULT '1'::double precision NOT NULL,
    subject_id uuid,
    session_id character varying(100),
    meta json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_item_interactions OWNER TO postgres;

--
-- Name: user_library_subscriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_library_subscriptions (
    user_id uuid NOT NULL,
    library_id uuid NOT NULL,
    is_enabled boolean NOT NULL,
    priority integer NOT NULL,
    notes text,
    subscribed_at timestamp without time zone NOT NULL,
    last_used_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_library_subscriptions OWNER TO postgres;

--
-- Name: user_memory_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_memory_settings (
    user_id uuid NOT NULL,
    enabled boolean NOT NULL,
    allow_preferences boolean NOT NULL,
    allow_goals boolean NOT NULL,
    allow_episodic boolean NOT NULL,
    capture_level character varying(20) NOT NULL,
    blocked_pref_keys jsonb NOT NULL,
    blocked_sources jsonb NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_memory_settings OWNER TO postgres;

--
-- Name: user_node_status; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_node_status (
    user_id uuid NOT NULL,
    node_id uuid NOT NULL,
    mastery_score double precision NOT NULL,
    bkt_mastery_prob double precision NOT NULL,
    bkt_last_updated_at timestamp without time zone,
    total_minutes integer NOT NULL,
    total_study_minutes integer NOT NULL,
    study_count integer,
    is_unlocked boolean NOT NULL,
    is_collapsed boolean,
    is_favorite boolean,
    last_study_at timestamp without time zone,
    last_interacted_at timestamp without time zone NOT NULL,
    decay_paused boolean,
    next_review_at timestamp without time zone,
    revision integer NOT NULL,
    first_unlock_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE user_node_status OWNER TO postgres;

--
-- Name: user_persona_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_persona_keys (
    user_id uuid NOT NULL,
    key_id character varying(128) NOT NULL,
    encrypted_key text,
    is_active boolean NOT NULL,
    destroyed_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_persona_keys OWNER TO postgres;

--
-- Name: user_preferences_center; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_preferences_center (
    user_id uuid NOT NULL,
    version integer NOT NULL,
    schema_version integer NOT NULL,
    explicit jsonb NOT NULL,
    inferred jsonb NOT NULL,
    last_explicit_update timestamp without time zone,
    last_inferred_update timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_preferences_center OWNER TO postgres;

--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_sessions (
    user_id uuid NOT NULL,
    session_id character varying(64) NOT NULL,
    device_id character varying(255),
    device_name character varying(255),
    device_type character varying(50),
    ip_address character varying(45),
    user_agent character varying(500),
    refresh_token_jti character varying(64),
    is_active boolean DEFAULT true NOT NULL,
    revoked_at timestamp without time zone,
    last_active_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_sessions OWNER TO postgres;

--
-- Name: user_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_settings (
    user_id uuid NOT NULL,
    transparency_level integer NOT NULL,
    system_update_level integer NOT NULL,
    task_reminders_enabled boolean NOT NULL,
    task_reminder_times json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_settings OWNER TO postgres;

--
-- Name: user_state_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_state_snapshots (
    user_id uuid NOT NULL,
    snapshot_at timestamp without time zone NOT NULL,
    window_start timestamp without time zone NOT NULL,
    window_end timestamp without time zone NOT NULL,
    cognitive_load double precision NOT NULL,
    interruptibility double precision NOT NULL,
    strain_index double precision NOT NULL,
    focus_mode boolean NOT NULL,
    sprint_mode boolean NOT NULL,
    knowledge_state json,
    time_context json,
    derived_event_ids json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_state_snapshots OWNER TO postgres;

--
-- Name: user_streak_days; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_streak_days (
    user_id uuid NOT NULL,
    day date NOT NULL,
    status streakdaystatus NOT NULL,
    used_freeze boolean DEFAULT false NOT NULL,
    source_event character varying(50),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_streak_days OWNER TO postgres;

--
-- Name: user_streak_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_streak_stats (
    user_id uuid NOT NULL,
    current_streak integer,
    max_streak integer,
    last_activity_date timestamp without time zone,
    freeze_charges integer,
    max_freeze_charges integer,
    last_freeze_used_at timestamp without time zone,
    total_checkin_days integer,
    longest_streak_start timestamp without time zone,
    longest_streak_end timestamp without time zone,
    longest_streak integer,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_streak_stats OWNER TO postgres;

--
-- Name: user_titles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_titles (
    user_id uuid NOT NULL,
    title_id character varying(50) NOT NULL,
    title_name character varying(100),
    title_display character varying(100),
    source_achievement_id character varying(50),
    is_equipped boolean,
    unlocked_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_titles OWNER TO postgres;

--
-- Name: user_tool_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_tool_history (
    id integer NOT NULL,
    user_id uuid NOT NULL,
    tool_name character varying(100) NOT NULL,
    tool_category character varying(50),
    success boolean NOT NULL,
    execution_time_ms integer,
    error_message character varying(500),
    error_type character varying(100),
    context_snapshot jsonb,
    input_args jsonb,
    output_summary text,
    user_satisfaction integer,
    was_helpful boolean,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE user_tool_history OWNER TO postgres;

--
-- Name: user_tool_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE user_tool_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE user_tool_history_id_seq OWNER TO postgres;

--
-- Name: user_tool_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE user_tool_history_id_seq OWNED BY user_tool_history.id;


--
-- Name: user_visual_configs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_visual_configs (
    user_id uuid NOT NULL,
    equipped_background_id character varying(50),
    equipped_particle_id character varying(50),
    equipped_effect_id character varying(50),
    background_equipped_at timestamp without time zone,
    particle_equipped_at timestamp without time zone,
    effect_equipped_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_visual_configs OWNER TO postgres;

--
-- Name: user_visual_elements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_visual_elements (
    user_id uuid NOT NULL,
    element_id character varying(50) NOT NULL,
    unlocked_at timestamp without time zone NOT NULL,
    unlock_source character varying(50) NOT NULL,
    source_id character varying(100),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_visual_elements OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE users (
    username character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(100),
    nickname character varying(100),
    avatar_url character varying(500),
    avatar_status avatarstatus NOT NULL,
    pending_avatar_url character varying(500),
    flame_level integer NOT NULL,
    flame_brightness double precision NOT NULL,
    depth_preference double precision NOT NULL,
    curiosity_preference double precision NOT NULL,
    schedule_preferences json,
    weather_preferences json,
    is_active boolean NOT NULL,
    is_superuser boolean NOT NULL,
    status userstatus NOT NULL,
    google_id character varying(255),
    apple_id character varying(255),
    wechat_unionid character varying(255),
    registration_source character varying(50) NOT NULL,
    last_login_at timestamp without time zone,
    is_minor boolean,
    age_verified boolean NOT NULL,
    age_verification_source character varying(50),
    age_verified_at timestamp without time zone,
    photon_balance integer NOT NULL,
    photon_updated_at timestamp without time zone,
    equipped_skin character varying(50),
    equipped_title character varying(50),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    equipped_skin_source character varying(20),
    equipped_title_source character varying(20),
    email_verified boolean DEFAULT false NOT NULL,
    token_revoked_before timestamp without time zone,
    password_login_enabled boolean DEFAULT true NOT NULL,
    agreed_to_tos_at timestamp without time zone,
    agreed_to_privacy_at timestamp without time zone,
    tos_version character varying(50),
    privacy_version character varying(50),
    agreed_locale character varying(20),
    searchable_by searchvisibility DEFAULT 'everyone'::searchvisibility NOT NULL
);


ALTER TABLE users OWNER TO postgres;

--
-- Name: COLUMN users.searchable_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN users.searchable_by IS '用户搜索隐私设置';


--
-- Name: visual_elements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE visual_elements (
    id character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    name_i18n jsonb,
    description_i18n jsonb,
    element_type visualelementtype NOT NULL,
    rarity visualelementrarity NOT NULL,
    unlock_source visualelementunlocksource,
    unlock_requirement jsonb,
    config jsonb NOT NULL,
    preview_url character varying(500),
    icon_url character varying(500),
    is_active boolean NOT NULL,
    is_default boolean NOT NULL,
    sort_order integer NOT NULL,
    category character varying(50),
    season_start character varying(10),
    season_end character varying(10),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE visual_elements OWNER TO postgres;

--
-- Name: word_books; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE word_books (
    user_id uuid NOT NULL,
    word character varying(100) NOT NULL,
    phonetic character varying(100),
    definition text NOT NULL,
    mastery_level integer,
    importance integer NOT NULL,
    consecutive_correct integer NOT NULL,
    correct_review_count integer NOT NULL,
    next_review_at timestamp without time zone,
    last_review_at timestamp without time zone,
    review_count integer,
    context_sentence text,
    source_task_id uuid,
    part_of_speech character varying(50),
    source_translation_id character varying(100),
    tags json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE word_books OWNER TO postgres;

--
-- Name: crdt_operation_log id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY crdt_operation_log ALTER COLUMN id SET DEFAULT nextval('crdt_operation_log_id_seq'::regclass);


--
-- Name: mastery_audit_log id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY mastery_audit_log ALTER COLUMN id SET DEFAULT nextval('mastery_audit_log_id_seq'::regclass);


--
-- Name: subjects id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY subjects ALTER COLUMN id SET DEFAULT nextval('subjects_id_seq'::regclass);


--
-- Name: user_tool_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_tool_history ALTER COLUMN id SET DEFAULT nextval('user_tool_history_id_seq'::regclass);


--
-- Name: ab_experiment_assignments ab_experiment_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiment_assignments
    ADD CONSTRAINT ab_experiment_assignments_pkey PRIMARY KEY (id);


--
-- Name: ab_experiment_metrics ab_experiment_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiment_metrics
    ADD CONSTRAINT ab_experiment_metrics_pkey PRIMARY KEY (id);


--
-- Name: ab_experiment_variants ab_experiment_variants_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiment_variants
    ADD CONSTRAINT ab_experiment_variants_pkey PRIMARY KEY (id);


--
-- Name: ab_experiments ab_experiments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiments
    ADD CONSTRAINT ab_experiments_pkey PRIMARY KEY (id);


--
-- Name: achievements achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY achievements
    ADD CONSTRAINT achievements_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: appeals appeals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY appeals
    ADD CONSTRAINT appeals_pkey PRIMARY KEY (id);


--
-- Name: arbitration_cases arbitration_cases_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY arbitration_cases
    ADD CONSTRAINT arbitration_cases_pkey PRIMARY KEY (id);


--
-- Name: arbitration_decisions arbitration_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY arbitration_decisions
    ADD CONSTRAINT arbitration_decisions_pkey PRIMARY KEY (id);


--
-- Name: auth_audit_log auth_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY auth_audit_log
    ADD CONSTRAINT auth_audit_log_pkey PRIMARY KEY (id);


--
-- Name: behavior_patterns behavior_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY behavior_patterns
    ADD CONSTRAINT behavior_patterns_pkey PRIMARY KEY (id);


--
-- Name: behavioral_outcomes behavioral_outcomes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY behavioral_outcomes
    ADD CONSTRAINT behavioral_outcomes_pkey PRIMARY KEY (id);


--
-- Name: broadcast_messages broadcast_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY broadcast_messages
    ADD CONSTRAINT broadcast_messages_pkey PRIMARY KEY (id);


--
-- Name: calendar_events calendar_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY calendar_events
    ADD CONSTRAINT calendar_events_pkey PRIMARY KEY (id);


--
-- Name: capsule_favorites capsule_favorites_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY capsule_favorites
    ADD CONSTRAINT capsule_favorites_pkey PRIMARY KEY (id);


--
-- Name: capsule_feedbacks capsule_feedbacks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY capsule_feedbacks
    ADD CONSTRAINT capsule_feedbacks_pkey PRIMARY KEY (id);


--
-- Name: capsule_generation_jobs capsule_generation_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY capsule_generation_jobs
    ADD CONSTRAINT capsule_generation_jobs_pkey PRIMARY KEY (id);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_sessions chat_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_sessions
    ADD CONSTRAINT chat_sessions_pkey PRIMARY KEY (id);


--
-- Name: cognitive_fragments cognitive_fragments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cognitive_fragments
    ADD CONSTRAINT cognitive_fragments_pkey PRIMARY KEY (id);


--
-- Name: collaborative_galaxies collaborative_galaxies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY collaborative_galaxies
    ADD CONSTRAINT collaborative_galaxies_pkey PRIMARY KEY (id);


--
-- Name: compliance_check_logs compliance_check_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY compliance_check_logs
    ADD CONSTRAINT compliance_check_logs_pkey PRIMARY KEY (id);


--
-- Name: context_budget_profiles context_budget_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY context_budget_profiles
    ADD CONSTRAINT context_budget_profiles_pkey PRIMARY KEY (id);


--
-- Name: context_pack_feedback context_pack_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY context_pack_feedback
    ADD CONSTRAINT context_pack_feedback_pkey PRIMARY KEY (id);


--
-- Name: context_pack_runs context_pack_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY context_pack_runs
    ADD CONSTRAINT context_pack_runs_pkey PRIMARY KEY (id);


--
-- Name: crdt_operation_log crdt_operation_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY crdt_operation_log
    ADD CONSTRAINT crdt_operation_log_pkey PRIMARY KEY (id);


--
-- Name: crdt_snapshots crdt_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY crdt_snapshots
    ADD CONSTRAINT crdt_snapshots_pkey PRIMARY KEY (galaxy_id);


--
-- Name: crypto_shredding_certificates crypto_shredding_certificates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY crypto_shredding_certificates
    ADD CONSTRAINT crypto_shredding_certificates_pkey PRIMARY KEY (id);


--
-- Name: curiosity_capsules curiosity_capsules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY curiosity_capsules
    ADD CONSTRAINT curiosity_capsules_pkey PRIMARY KEY (id);


--
-- Name: data_access_logs data_access_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY data_access_logs
    ADD CONSTRAINT data_access_logs_pkey PRIMARY KEY (id);


--
-- Name: decision_records decision_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY decision_records
    ADD CONSTRAINT decision_records_pkey PRIMARY KEY (id);


--
-- Name: dictionary_entries dictionary_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY dictionary_entries
    ADD CONSTRAINT dictionary_entries_pkey PRIMARY KEY (id);


--
-- Name: dlq_replay_audit_logs dlq_replay_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY dlq_replay_audit_logs
    ADD CONSTRAINT dlq_replay_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: document_chunks document_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY document_chunks
    ADD CONSTRAINT document_chunks_pkey PRIMARY KEY (id);


--
-- Name: episodic_memories episodic_memories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY episodic_memories
    ADD CONSTRAINT episodic_memories_pkey PRIMARY KEY (id);


--
-- Name: error_records error_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY error_records
    ADD CONSTRAINT error_records_pkey PRIMARY KEY (id);


--
-- Name: event_outbox event_outbox_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY event_outbox
    ADD CONSTRAINT event_outbox_pkey PRIMARY KEY (id);


--
-- Name: event_sequence_counters event_sequence_counters_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY event_sequence_counters
    ADD CONSTRAINT event_sequence_counters_pkey PRIMARY KEY (aggregate_type, aggregate_id);


--
-- Name: event_store event_store_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY event_store
    ADD CONSTRAINT event_store_pkey PRIMARY KEY (id);


--
-- Name: evolution_predictions evolution_predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY evolution_predictions
    ADD CONSTRAINT evolution_predictions_pkey PRIMARY KEY (id);


--
-- Name: expansion_feedback expansion_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY expansion_feedback
    ADD CONSTRAINT expansion_feedback_pkey PRIMARY KEY (id);


--
-- Name: focus_sessions focus_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY focus_sessions
    ADD CONSTRAINT focus_sessions_pkey PRIMARY KEY (id);


--
-- Name: friendships friendships_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY friendships
    ADD CONSTRAINT friendships_pkey PRIMARY KEY (id);


--
-- Name: galaxy_skins galaxy_skins_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY galaxy_skins
    ADD CONSTRAINT galaxy_skins_pkey PRIMARY KEY (id);


--
-- Name: galaxy_user_permissions galaxy_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY galaxy_user_permissions
    ADD CONSTRAINT galaxy_user_permissions_pkey PRIMARY KEY (galaxy_id, user_id);


--
-- Name: group_files group_files_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_files
    ADD CONSTRAINT group_files_pkey PRIMARY KEY (id);


--
-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (id);


--
-- Name: group_message_reads group_message_reads_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_message_reads
    ADD CONSTRAINT group_message_reads_pkey PRIMARY KEY (id);


--
-- Name: group_messages group_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_messages
    ADD CONSTRAINT group_messages_pkey PRIMARY KEY (id);


--
-- Name: group_task_claims group_task_claims_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_task_claims
    ADD CONSTRAINT group_task_claims_pkey PRIMARY KEY (id);


--
-- Name: group_tasks group_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_tasks
    ADD CONSTRAINT group_tasks_pkey PRIMARY KEY (id);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: idempotency_keys idempotency_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY idempotency_keys
    ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (key);


--
-- Name: intervention_audit_logs intervention_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_audit_logs
    ADD CONSTRAINT intervention_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: intervention_feedback intervention_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_feedback
    ADD CONSTRAINT intervention_feedback_pkey PRIMARY KEY (id);


--
-- Name: intervention_requests intervention_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_requests
    ADD CONSTRAINT intervention_requests_pkey PRIMARY KEY (id);


--
-- Name: intervention_templates intervention_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_templates
    ADD CONSTRAINT intervention_templates_pkey PRIMARY KEY (id);


--
-- Name: irt_item_parameters irt_item_parameters_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY irt_item_parameters
    ADD CONSTRAINT irt_item_parameters_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: knowledge_nodes knowledge_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY knowledge_nodes
    ADD CONSTRAINT knowledge_nodes_pkey PRIMARY KEY (id);


--
-- Name: legal_holds legal_holds_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY legal_holds
    ADD CONSTRAINT legal_holds_pkey PRIMARY KEY (id);


--
-- Name: login_attempts login_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY login_attempts
    ADD CONSTRAINT login_attempts_pkey PRIMARY KEY (id);


--
-- Name: ltm_daily_snapshots ltm_daily_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ltm_daily_snapshots
    ADD CONSTRAINT ltm_daily_snapshots_pkey PRIMARY KEY (id);


--
-- Name: mastery_audit_log mastery_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY mastery_audit_log
    ADD CONSTRAINT mastery_audit_log_pkey PRIMARY KEY (id);


--
-- Name: memory_corrections memory_corrections_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_corrections
    ADD CONSTRAINT memory_corrections_pkey PRIMARY KEY (id);


--
-- Name: memory_evolutions memory_evolutions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_evolutions
    ADD CONSTRAINT memory_evolutions_pkey PRIMARY KEY (id);


--
-- Name: memory_goals memory_goals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_goals
    ADD CONSTRAINT memory_goals_pkey PRIMARY KEY (id);


--
-- Name: memory_preferences memory_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_preferences
    ADD CONSTRAINT memory_preferences_pkey PRIMARY KEY (id);


--
-- Name: memory_rank_policies memory_rank_policies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_rank_policies
    ADD CONSTRAINT memory_rank_policies_pkey PRIMARY KEY (id);


--
-- Name: message_favorites message_favorites_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY message_favorites
    ADD CONSTRAINT message_favorites_pkey PRIMARY KEY (id);


--
-- Name: message_reports message_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY message_reports
    ADD CONSTRAINT message_reports_pkey PRIMARY KEY (id);


--
-- Name: next_action_selections next_action_selections_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY next_action_selections
    ADD CONSTRAINT next_action_selections_pkey PRIMARY KEY (id);


--
-- Name: nightly_reviews nightly_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY nightly_reviews
    ADD CONSTRAINT nightly_reviews_pkey PRIMARY KEY (id);


--
-- Name: node_expansion_queue node_expansion_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_pkey PRIMARY KEY (id);


--
-- Name: node_relations node_relations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY node_relations
    ADD CONSTRAINT node_relations_pkey PRIMARY KEY (id);


--
-- Name: notification_interactions notification_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY notification_interactions
    ADD CONSTRAINT notification_interactions_pkey PRIMARY KEY (id);


--
-- Name: notification_preferences notification_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY notification_preferences
    ADD CONSTRAINT notification_preferences_pkey PRIMARY KEY (user_id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: offline_message_queue offline_message_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY offline_message_queue
    ADD CONSTRAINT offline_message_queue_pkey PRIMARY KEY (id);


--
-- Name: passive_signals passive_signals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY passive_signals
    ADD CONSTRAINT passive_signals_pkey PRIMARY KEY (id);


--
-- Name: persona_snapshots persona_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY persona_snapshots
    ADD CONSTRAINT persona_snapshots_pkey PRIMARY KEY (id);


--
-- Name: photon_transaction_history photon_transaction_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY photon_transaction_history
    ADD CONSTRAINT photon_transaction_history_pkey PRIMARY KEY (id);


--
-- Name: plan_execution_records plan_execution_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plan_execution_records
    ADD CONSTRAINT plan_execution_records_pkey PRIMARY KEY (id);


--
-- Name: plan_states plan_states_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plan_states
    ADD CONSTRAINT plan_states_pkey PRIMARY KEY (id);


--
-- Name: plans plans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plans
    ADD CONSTRAINT plans_pkey PRIMARY KEY (id);


--
-- Name: post_likes post_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY post_likes
    ADD CONSTRAINT post_likes_pkey PRIMARY KEY (id);


--
-- Name: posts posts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY posts
    ADD CONSTRAINT posts_pkey PRIMARY KEY (id);


--
-- Name: private_messages private_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY private_messages
    ADD CONSTRAINT private_messages_pkey PRIMARY KEY (id);


--
-- Name: processed_events processed_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY processed_events
    ADD CONSTRAINT processed_events_pkey PRIMARY KEY (event_id, consumer_group);


--
-- Name: projection_metadata projection_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY projection_metadata
    ADD CONSTRAINT projection_metadata_pkey PRIMARY KEY (projection_name);


--
-- Name: projection_snapshots projection_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY projection_snapshots
    ADD CONSTRAINT projection_snapshots_pkey PRIMARY KEY (id);


--
-- Name: push_histories push_histories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY push_histories
    ADD CONSTRAINT push_histories_pkey PRIMARY KEY (id);


--
-- Name: push_preferences push_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY push_preferences
    ADD CONSTRAINT push_preferences_pkey PRIMARY KEY (id);


--
-- Name: recommendation_cache recommendation_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY recommendation_cache
    ADD CONSTRAINT recommendation_cache_pkey PRIMARY KEY (id);


--
-- Name: response_feedback response_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY response_feedback
    ADD CONSTRAINT response_feedback_pkey PRIMARY KEY (id);


--
-- Name: review_feedback review_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY review_feedback
    ADD CONSTRAINT review_feedback_pkey PRIMARY KEY (id);


--
-- Name: review_history review_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY review_history
    ADD CONSTRAINT review_history_pkey PRIMARY KEY (id);


--
-- Name: review_overrides review_overrides_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY review_overrides
    ADD CONSTRAINT review_overrides_pkey PRIMARY KEY (id);


--
-- Name: scaffolding_states scaffolding_states_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY scaffolding_states
    ADD CONSTRAINT scaffolding_states_pkey PRIMARY KEY (id);


--
-- Name: security_audit_logs security_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY security_audit_logs
    ADD CONSTRAINT security_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: seed_items seed_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY seed_items
    ADD CONSTRAINT seed_items_pkey PRIMARY KEY (id);


--
-- Name: seed_libraries seed_libraries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY seed_libraries
    ADD CONSTRAINT seed_libraries_pkey PRIMARY KEY (id);


--
-- Name: semantic_links semantic_links_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY semantic_links
    ADD CONSTRAINT semantic_links_pkey PRIMARY KEY (id);


--
-- Name: shared_resources shared_resources_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT shared_resources_pkey PRIMARY KEY (id);


--
-- Name: shop_items shop_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shop_items
    ADD CONSTRAINT shop_items_pkey PRIMARY KEY (id);


--
-- Name: shop_purchases shop_purchases_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shop_purchases
    ADD CONSTRAINT shop_purchases_pkey PRIMARY KEY (id);


--
-- Name: smoke_document_vectors smoke_document_vectors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY smoke_document_vectors
    ADD CONSTRAINT smoke_document_vectors_pkey PRIMARY KEY (id);


--
-- Name: spark_contracts spark_contracts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY spark_contracts
    ADD CONSTRAINT spark_contracts_pkey PRIMARY KEY (user_id, id);


--
-- Name: stored_files stored_files_object_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY stored_files
    ADD CONSTRAINT stored_files_object_key_key UNIQUE (object_key);


--
-- Name: stored_files stored_files_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY stored_files
    ADD CONSTRAINT stored_files_pkey PRIMARY KEY (id);


--
-- Name: strategy_nodes strategy_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY strategy_nodes
    ADD CONSTRAINT strategy_nodes_pkey PRIMARY KEY (id);


--
-- Name: study_buddies study_buddies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY study_buddies
    ADD CONSTRAINT study_buddies_pkey PRIMARY KEY (id);


--
-- Name: study_records study_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY study_records
    ADD CONSTRAINT study_records_pkey PRIMARY KEY (id);


--
-- Name: subjects subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY subjects
    ADD CONSTRAINT subjects_pkey PRIMARY KEY (id);


--
-- Name: subtasks subtasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY subtasks
    ADD CONSTRAINT subtasks_pkey PRIMARY KEY (id);


--
-- Name: system_config_change_logs system_config_change_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY system_config_change_logs
    ADD CONSTRAINT system_config_change_logs_pkey PRIMARY KEY (id);


--
-- Name: task_feedbacks task_feedbacks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_feedbacks
    ADD CONSTRAINT task_feedbacks_pkey PRIMARY KEY (id);


--
-- Name: task_knowledge_links task_knowledge_links_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_knowledge_links
    ADD CONSTRAINT task_knowledge_links_pkey PRIMARY KEY (id);


--
-- Name: task_resource_links task_resource_links_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_resource_links
    ADD CONSTRAINT task_resource_links_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: token_usage token_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY token_usage
    ADD CONSTRAINT token_usage_pkey PRIMARY KEY (id);


--
-- Name: token_usage token_usage_request_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY token_usage
    ADD CONSTRAINT token_usage_request_id_key UNIQUE (request_id);


--
-- Name: tracking_events tracking_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tracking_events
    ADD CONSTRAINT tracking_events_pkey PRIMARY KEY (id);


--
-- Name: capsule_favorites uq_capsule_favorite; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY capsule_favorites
    ADD CONSTRAINT uq_capsule_favorite UNIQUE (user_id, capsule_id);


--
-- Name: friendships uq_friendship; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY friendships
    ADD CONSTRAINT uq_friendship UNIQUE (user_id, friend_id);


--
-- Name: group_files uq_group_files_group_file; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_files
    ADD CONSTRAINT uq_group_files_group_file UNIQUE (group_id, file_id);


--
-- Name: group_members uq_group_member; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_members
    ADD CONSTRAINT uq_group_member UNIQUE (group_id, user_id);


--
-- Name: group_message_reads uq_group_message_read; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_message_reads
    ADD CONSTRAINT uq_group_message_read UNIQUE (message_id, user_id);


--
-- Name: intervention_feedback uq_intervention_feedback_idempotency; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_feedback
    ADD CONSTRAINT uq_intervention_feedback_idempotency UNIQUE (user_id, request_id, feedback_type, idempotency_key);


--
-- Name: offline_message_queue uq_offline_queue_nonce; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY offline_message_queue
    ADD CONSTRAINT uq_offline_queue_nonce UNIQUE (user_id, client_nonce);


--
-- Name: post_likes uq_post_like; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY post_likes
    ADD CONSTRAINT uq_post_like UNIQUE (user_id, post_id);


--
-- Name: response_feedback uq_response_feedback_user_response; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY response_feedback
    ADD CONSTRAINT uq_response_feedback_user_response UNIQUE (user_id, response_id);


--
-- Name: group_task_claims uq_task_claim; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_task_claims
    ADD CONSTRAINT uq_task_claim UNIQUE (group_task_id, user_id);


--
-- Name: user_blocks uq_user_blocks; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_blocks
    ADD CONSTRAINT uq_user_blocks UNIQUE (blocker_id, blocked_id);


--
-- Name: user_daily_metrics uq_user_daily_metric; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_daily_metrics
    ADD CONSTRAINT uq_user_daily_metric UNIQUE (user_id, date);


--
-- Name: word_books uq_user_word; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY word_books
    ADD CONSTRAINT uq_user_word UNIQUE (user_id, word);


--
-- Name: user_achievements user_achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_achievements
    ADD CONSTRAINT user_achievements_pkey PRIMARY KEY (user_id, achievement_id, id);


--
-- Name: user_blocks user_blocks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_blocks
    ADD CONSTRAINT user_blocks_pkey PRIMARY KEY (id);


--
-- Name: user_consumables user_consumables_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_consumables
    ADD CONSTRAINT user_consumables_pkey PRIMARY KEY (id);


--
-- Name: user_daily_metrics user_daily_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_daily_metrics
    ADD CONSTRAINT user_daily_metrics_pkey PRIMARY KEY (id);


--
-- Name: user_devices user_devices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_devices
    ADD CONSTRAINT user_devices_pkey PRIMARY KEY (id);


--
-- Name: user_encryption_keys user_encryption_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_encryption_keys
    ADD CONSTRAINT user_encryption_keys_pkey PRIMARY KEY (id);


--
-- Name: user_galaxy_skins user_galaxy_skins_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_galaxy_skins
    ADD CONSTRAINT user_galaxy_skins_pkey PRIMARY KEY (user_id, skin_id, id);


--
-- Name: user_intervention_settings user_intervention_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_intervention_settings
    ADD CONSTRAINT user_intervention_settings_pkey PRIMARY KEY (id);


--
-- Name: user_irt_ability user_irt_ability_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_irt_ability
    ADD CONSTRAINT user_irt_ability_pkey PRIMARY KEY (id);


--
-- Name: user_item_interactions user_item_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_item_interactions
    ADD CONSTRAINT user_item_interactions_pkey PRIMARY KEY (id);


--
-- Name: user_library_subscriptions user_library_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_library_subscriptions
    ADD CONSTRAINT user_library_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: user_memory_settings user_memory_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_memory_settings
    ADD CONSTRAINT user_memory_settings_pkey PRIMARY KEY (id);


--
-- Name: user_node_status user_node_status_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_node_status
    ADD CONSTRAINT user_node_status_pkey PRIMARY KEY (user_id, node_id);


--
-- Name: user_persona_keys user_persona_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_persona_keys
    ADD CONSTRAINT user_persona_keys_pkey PRIMARY KEY (id);


--
-- Name: user_preferences_center user_preferences_center_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_preferences_center
    ADD CONSTRAINT user_preferences_center_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_session_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_sessions
    ADD CONSTRAINT user_sessions_session_id_key UNIQUE (session_id);


--
-- Name: user_settings user_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_settings
    ADD CONSTRAINT user_settings_pkey PRIMARY KEY (id);


--
-- Name: user_state_snapshots user_state_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_state_snapshots
    ADD CONSTRAINT user_state_snapshots_pkey PRIMARY KEY (id);


--
-- Name: user_streak_days user_streak_days_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_streak_days
    ADD CONSTRAINT user_streak_days_pkey PRIMARY KEY (user_id, day);


--
-- Name: user_streak_stats user_streak_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_streak_stats
    ADD CONSTRAINT user_streak_stats_pkey PRIMARY KEY (user_id, id);


--
-- Name: user_titles user_titles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_titles
    ADD CONSTRAINT user_titles_pkey PRIMARY KEY (user_id, title_id, id);


--
-- Name: user_tool_history user_tool_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_tool_history
    ADD CONSTRAINT user_tool_history_pkey PRIMARY KEY (id);


--
-- Name: user_visual_configs user_visual_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_visual_configs
    ADD CONSTRAINT user_visual_configs_pkey PRIMARY KEY (user_id);


--
-- Name: user_visual_elements user_visual_elements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_visual_elements
    ADD CONSTRAINT user_visual_elements_pkey PRIMARY KEY (user_id, element_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: visual_elements visual_elements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY visual_elements
    ADD CONSTRAINT visual_elements_pkey PRIMARY KEY (id);


--
-- Name: word_books word_books_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY word_books
    ADD CONSTRAINT word_books_pkey PRIMARY KEY (id);


--
-- Name: idx_achievements_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_achievements_category ON achievements USING btree (category);


--
-- Name: idx_achievements_type_rarity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_achievements_type_rarity ON achievements USING btree (type, rarity);


--
-- Name: idx_auth_audit_user_occurred; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_auth_audit_user_occurred ON auth_audit_log USING btree (user_id, occurred_at);


--
-- Name: idx_chat_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_created_at ON chat_messages USING btree (created_at);


--
-- Name: idx_chat_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_role ON chat_messages USING btree (role);


--
-- Name: idx_chat_session_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_session_active ON chat_sessions USING btree (is_active);


--
-- Name: idx_chat_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_session_id ON chat_messages USING btree (session_id);


--
-- Name: idx_chat_session_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_session_user_id ON chat_sessions USING btree (user_id);


--
-- Name: idx_chat_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_task_id ON chat_messages USING btree (task_id);


--
-- Name: idx_chat_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_user_id ON chat_messages USING btree (user_id);


--
-- Name: idx_chat_user_session_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_user_session_created_at ON chat_messages USING btree (user_id, session_id, created_at);


--
-- Name: idx_claim_task; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_claim_task ON group_task_claims USING btree (group_task_id);


--
-- Name: idx_claim_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_claim_user ON group_task_claims USING btree (user_id);


--
-- Name: idx_context_budget_profiles_intent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_context_budget_profiles_intent ON context_budget_profiles USING btree (intent);


--
-- Name: idx_context_pack_runs_intent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_context_pack_runs_intent ON context_pack_runs USING btree (intent);


--
-- Name: idx_context_pack_runs_user_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_context_pack_runs_user_created ON context_pack_runs USING btree (user_id, created_at);


--
-- Name: idx_dict_word; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dict_word ON dictionary_entries USING btree (word);


--
-- Name: idx_episodic_memories_archived_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_archived_at ON episodic_memories USING btree (archived_at);


--
-- Name: idx_episodic_memories_evidence_missing; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_evidence_missing ON episodic_memories USING btree (evidence_missing);


--
-- Name: idx_episodic_memories_evidence_score; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_evidence_score ON episodic_memories USING btree (evidence_score);


--
-- Name: idx_episodic_memories_last_consumed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_last_consumed_at ON episodic_memories USING btree (last_consumed_at);


--
-- Name: idx_episodic_memories_user_occurred; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_user_occurred ON episodic_memories USING btree (user_id, occurred_at);


--
-- Name: idx_error_records_cognitive_tags; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_records_cognitive_tags ON error_records USING gin (cognitive_tags);


--
-- Name: idx_errors_subject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_subject ON error_records USING btree (subject_code);


--
-- Name: idx_errors_user_review; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_user_review ON error_records USING btree (user_id, next_review_at) WHERE (mastery_level < (1.0)::double precision);


--
-- Name: idx_event_store_aggregate; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_store_aggregate ON event_store USING btree (aggregate_type, aggregate_id, sequence_number);


--
-- Name: idx_execution_records_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_records_created ON plan_execution_records USING btree (created_at);


--
-- Name: idx_execution_records_plan_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_records_plan_user ON plan_execution_records USING btree (plan_id, user_id);


--
-- Name: idx_execution_records_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_records_status ON plan_execution_records USING btree (validation_status);


--
-- Name: idx_focus_user_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_focus_user_time ON focus_sessions USING btree (user_id, start_time);


--
-- Name: idx_friendship_friend; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_friendship_friend ON friendships USING btree (friend_id);


--
-- Name: idx_friendship_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_friendship_status ON friendships USING btree (status);


--
-- Name: idx_friendship_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_friendship_user ON friendships USING btree (user_id);


--
-- Name: idx_group_files_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_files_category ON group_files USING btree (category);


--
-- Name: idx_group_files_file; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_files_file ON group_files USING btree (file_id);


--
-- Name: idx_group_files_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_files_group ON group_files USING btree (group_id);


--
-- Name: idx_group_files_shared_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_files_shared_by ON group_files USING btree (shared_by_id);


--
-- Name: idx_group_message_read_message; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_message_read_message ON group_message_reads USING btree (message_id, read_at);


--
-- Name: idx_group_message_read_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_message_read_user ON group_message_reads USING btree (user_id, read_at);


--
-- Name: idx_group_public; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_public ON groups USING btree (is_public);


--
-- Name: idx_group_task_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_task_group ON group_tasks USING btree (group_id);


--
-- Name: idx_group_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_type ON groups USING btree (type);


--
-- Name: idx_idempotency_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_idempotency_expires ON idempotency_keys USING btree (expires_at);


--
-- Name: idx_jobs_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_jobs_status ON jobs USING btree (status);


--
-- Name: idx_jobs_status_timeout; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_jobs_status_timeout ON jobs USING btree (status, timeout_at) WHERE ((status)::text = 'running'::text);


--
-- Name: idx_jobs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_jobs_user_id ON jobs USING btree (user_id);


--
-- Name: idx_ltm_daily_snapshots_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_ltm_daily_snapshots_date ON ltm_daily_snapshots USING btree (snapshot_date);


--
-- Name: idx_mastery_audit_log_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mastery_audit_log_created_at ON mastery_audit_log USING btree (created_at DESC);


--
-- Name: idx_mastery_audit_log_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mastery_audit_log_node_id ON mastery_audit_log USING btree (node_id);


--
-- Name: idx_mastery_audit_log_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mastery_audit_log_user_id ON mastery_audit_log USING btree (user_id);


--
-- Name: idx_mastery_audit_log_user_node_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mastery_audit_log_user_node_time ON mastery_audit_log USING btree (user_id, node_id, created_at DESC);


--
-- Name: idx_member_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_member_group ON group_members USING btree (group_id);


--
-- Name: idx_member_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_member_user ON group_members USING btree (user_id);


--
-- Name: idx_memory_corrections_user_type_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_corrections_user_type_created ON memory_corrections USING btree (user_id, memory_type, created_at);


--
-- Name: idx_memory_goals_archived_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_goals_archived_at ON memory_goals USING btree (archived_at);


--
-- Name: idx_memory_goals_evidence_missing; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_goals_evidence_missing ON memory_goals USING btree (evidence_missing);


--
-- Name: idx_memory_goals_evidence_score; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_goals_evidence_score ON memory_goals USING btree (evidence_score);


--
-- Name: idx_memory_goals_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_goals_expires_at ON memory_goals USING btree (expires_at);


--
-- Name: idx_memory_goals_last_consumed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_goals_last_consumed_at ON memory_goals USING btree (last_consumed_at);


--
-- Name: idx_memory_goals_user_status_target; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_goals_user_status_target ON memory_goals USING btree (user_id, status, target_date);


--
-- Name: idx_memory_preferences_archived_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_preferences_archived_at ON memory_preferences USING btree (archived_at);


--
-- Name: idx_memory_preferences_evidence_missing; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_preferences_evidence_missing ON memory_preferences USING btree (evidence_missing);


--
-- Name: idx_memory_preferences_evidence_score; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_preferences_evidence_score ON memory_preferences USING btree (evidence_score);


--
-- Name: idx_memory_preferences_last_consumed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_preferences_last_consumed_at ON memory_preferences USING btree (last_consumed_at);


--
-- Name: idx_memory_preferences_user_pref; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_memory_preferences_user_pref ON memory_preferences USING btree (user_id, pref_key);


--
-- Name: idx_message_favorites_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_favorites_user ON message_favorites USING btree (user_id);


--
-- Name: idx_message_group_thread; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_group_thread ON group_messages USING btree (group_id, thread_root_id, created_at);


--
-- Name: idx_message_group_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_group_time ON group_messages USING btree (group_id, created_at);


--
-- Name: idx_message_reports_group_msg; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_reports_group_msg ON message_reports USING btree (group_message_id);


--
-- Name: idx_message_reports_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_reports_status ON message_reports USING btree (status);


--
-- Name: idx_offline_queue_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_offline_queue_user_status ON offline_message_queue USING btree (user_id, status);


--
-- Name: idx_outbox_aggregate; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_outbox_aggregate ON event_outbox USING btree (aggregate_type, aggregate_id, sequence_number);


--
-- Name: idx_outbox_unpublished; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_outbox_unpublished ON event_outbox USING btree (created_at) WHERE (published_at IS NULL);


--
-- Name: idx_plan_states_updated_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plan_states_updated_at ON plan_states USING btree (updated_at);


--
-- Name: idx_plan_states_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plan_states_user_status ON plan_states USING btree (user_id, status);


--
-- Name: idx_plans_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_is_active ON plans USING btree (is_active);


--
-- Name: idx_plans_is_primary; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_is_primary ON plans USING btree (is_primary);


--
-- Name: idx_plans_priority; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_priority ON plans USING btree (priority);


--
-- Name: idx_plans_stage; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_stage ON plans USING btree (plan_stage);


--
-- Name: idx_plans_target_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_target_date ON plans USING btree (target_date);


--
-- Name: idx_plans_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_type ON plans USING btree (type);


--
-- Name: idx_plans_user_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_user_active ON plans USING btree (user_id, is_active);


--
-- Name: idx_plans_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_user_id ON plans USING btree (user_id);


--
-- Name: idx_post_like_post; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_post_like_post ON post_likes USING btree (post_id);


--
-- Name: idx_post_like_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_post_like_user ON post_likes USING btree (user_id);


--
-- Name: idx_private_message_conversation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_private_message_conversation ON private_messages USING btree (sender_id, receiver_id, created_at);


--
-- Name: idx_private_message_receiver_unread; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_private_message_receiver_unread ON private_messages USING btree (receiver_id, is_read);


--
-- Name: idx_private_message_thread; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_private_message_thread ON private_messages USING btree (sender_id, receiver_id, thread_root_id, created_at);


--
-- Name: idx_projection_snapshots_projection_aggregate; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_projection_snapshots_projection_aggregate ON projection_snapshots USING btree (projection_name, aggregate_id);


--
-- Name: idx_rec_cache_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rec_cache_expires ON recommendation_cache USING btree (expires_at);


--
-- Name: idx_rec_cache_user_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rec_cache_user_type ON recommendation_cache USING btree (user_id, recommendation_type);


--
-- Name: idx_share_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_group ON shared_resources USING btree (group_id);


--
-- Name: idx_share_resource_capsule; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_resource_capsule ON shared_resources USING btree (curiosity_capsule_id);


--
-- Name: idx_share_resource_knowledge_node; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_resource_knowledge_node ON shared_resources USING btree (knowledge_node_id);


--
-- Name: idx_share_resource_pattern; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_resource_pattern ON shared_resources USING btree (behavior_pattern_id);


--
-- Name: idx_share_resource_plan; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_resource_plan ON shared_resources USING btree (plan_id);


--
-- Name: idx_share_target_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_target_user ON shared_resources USING btree (target_user_id);


--
-- Name: idx_subtasks_order; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_subtasks_order ON subtasks USING btree ("order");


--
-- Name: idx_subtasks_parent_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_subtasks_parent_task_id ON subtasks USING btree (parent_task_id);


--
-- Name: idx_subtasks_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_subtasks_status ON subtasks USING btree (status);


--
-- Name: idx_task_knowledge_links_task_node; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_knowledge_links_task_node ON task_knowledge_links USING btree (task_id, knowledge_node_id);


--
-- Name: idx_task_resource_links_task_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_resource_links_task_type ON task_resource_links USING btree (task_id, resource_type);


--
-- Name: idx_tasks_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_created_at ON tasks USING btree (created_at);


--
-- Name: idx_tasks_due_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_due_date ON tasks USING btree (due_date);


--
-- Name: idx_tasks_plan_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_plan_id ON tasks USING btree (plan_id);


--
-- Name: idx_tasks_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_status ON tasks USING btree (status);


--
-- Name: idx_tasks_user_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_user_created_at ON tasks USING btree (user_id, created_at);


--
-- Name: idx_tasks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_user_id ON tasks USING btree (user_id);


--
-- Name: idx_tasks_user_status_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_user_status_created_at ON tasks USING btree (user_id, status, created_at);


--
-- Name: idx_token_usage_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_token_usage_created_at ON token_usage USING btree (created_at);


--
-- Name: idx_token_usage_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_token_usage_session_id ON token_usage USING btree (session_id);


--
-- Name: idx_token_usage_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_token_usage_user_id ON token_usage USING btree (user_id);


--
-- Name: idx_user_achievements_unlocked_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_achievements_unlocked_at ON user_achievements USING btree (unlocked_at);


--
-- Name: idx_user_achievements_user_unlocked; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_achievements_user_unlocked ON user_achievements USING btree (user_id, unlocked_at);


--
-- Name: idx_user_blocks_blocked; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_blocks_blocked ON user_blocks USING btree (blocked_id, deleted_at);


--
-- Name: idx_user_blocks_blocker; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_blocks_blocker ON user_blocks USING btree (blocker_id, deleted_at);


--
-- Name: idx_user_encryption_keys_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_encryption_keys_user ON user_encryption_keys USING btree (user_id, is_active);


--
-- Name: idx_user_interaction_item; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_interaction_item ON user_item_interactions USING btree (item_id);


--
-- Name: idx_user_interaction_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_interaction_time ON user_item_interactions USING btree (created_at);


--
-- Name: idx_user_interaction_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_interaction_type ON user_item_interactions USING btree (interaction_type);


--
-- Name: idx_user_interaction_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_interaction_user ON user_item_interactions USING btree (user_id);


--
-- Name: idx_user_interaction_user_item; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_interaction_user_item ON user_item_interactions USING btree (user_id, item_id);


--
-- Name: idx_user_memory_settings_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_user_memory_settings_user ON user_memory_settings USING btree (user_id);


--
-- Name: idx_user_sessions_user_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_sessions_user_active ON user_sessions USING btree (user_id, is_active);


--
-- Name: idx_user_settings_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_user_settings_user ON user_settings USING btree (user_id);


--
-- Name: idx_user_streak_stats_last_activity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_streak_stats_last_activity ON user_streak_stats USING btree (last_activity_date);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_email ON users USING btree (email);


--
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_username ON users USING btree (username);


--
-- Name: idx_wordbook_review; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_wordbook_review ON word_books USING btree (user_id, next_review_at);


--
-- Name: ix_ab_experiment_assignments_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_assignments_deleted_at ON ab_experiment_assignments USING btree (deleted_at);


--
-- Name: ix_ab_experiment_assignments_experiment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_assignments_experiment_id ON ab_experiment_assignments USING btree (experiment_id);


--
-- Name: ix_ab_experiment_assignments_is_excluded; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_assignments_is_excluded ON ab_experiment_assignments USING btree (is_excluded);


--
-- Name: ix_ab_experiment_assignments_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_assignments_user_id ON ab_experiment_assignments USING btree (user_id);


--
-- Name: ix_ab_experiment_assignments_variant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_assignments_variant_id ON ab_experiment_assignments USING btree (variant_id);


--
-- Name: ix_ab_experiment_metrics_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_metrics_deleted_at ON ab_experiment_metrics USING btree (deleted_at);


--
-- Name: ix_ab_experiment_metrics_experiment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_metrics_experiment_id ON ab_experiment_metrics USING btree (experiment_id);


--
-- Name: ix_ab_experiment_metrics_metric_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_metrics_metric_name ON ab_experiment_metrics USING btree (metric_name);


--
-- Name: ix_ab_experiment_metrics_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_metrics_timestamp ON ab_experiment_metrics USING btree ("timestamp");


--
-- Name: ix_ab_experiment_metrics_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_metrics_user_id ON ab_experiment_metrics USING btree (user_id);


--
-- Name: ix_ab_experiment_metrics_variant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_metrics_variant_id ON ab_experiment_metrics USING btree (variant_id);


--
-- Name: ix_ab_experiment_variants_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_variants_deleted_at ON ab_experiment_variants USING btree (deleted_at);


--
-- Name: ix_ab_experiment_variants_experiment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_variants_experiment_id ON ab_experiment_variants USING btree (experiment_id);


--
-- Name: ix_ab_experiment_variants_is_control; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiment_variants_is_control ON ab_experiment_variants USING btree (is_control);


--
-- Name: ix_ab_experiments_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiments_created_by ON ab_experiments USING btree (created_by);


--
-- Name: ix_ab_experiments_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiments_deleted_at ON ab_experiments USING btree (deleted_at);


--
-- Name: ix_ab_experiments_start_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiments_start_date ON ab_experiments USING btree (start_date);


--
-- Name: ix_ab_experiments_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ab_experiments_status ON ab_experiments USING btree (status);


--
-- Name: ix_achievements_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_achievements_deleted_at ON achievements USING btree (deleted_at);


--
-- Name: ix_achievements_trigger_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_achievements_trigger_code ON achievements USING btree (trigger_code);


--
-- Name: ix_achievements_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_achievements_type ON achievements USING btree (type);


--
-- Name: ix_appeals_appeal_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_appeals_appeal_id ON appeals USING btree (appeal_id);


--
-- Name: ix_appeals_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appeals_deleted_at ON appeals USING btree (deleted_at);


--
-- Name: ix_appeals_review_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appeals_review_id ON appeals USING btree (review_id);


--
-- Name: ix_appeals_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appeals_status ON appeals USING btree (status);


--
-- Name: ix_appeals_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_appeals_user_id ON appeals USING btree (user_id);


--
-- Name: ix_arbitration_cases_appeal_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_arbitration_cases_appeal_id ON arbitration_cases USING btree (appeal_id);


--
-- Name: ix_arbitration_cases_case_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_arbitration_cases_case_id ON arbitration_cases USING btree (case_id);


--
-- Name: ix_arbitration_cases_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_arbitration_cases_deleted_at ON arbitration_cases USING btree (deleted_at);


--
-- Name: ix_arbitration_cases_escalation_reason; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_arbitration_cases_escalation_reason ON arbitration_cases USING btree (escalation_reason);


--
-- Name: ix_arbitration_cases_priority; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_arbitration_cases_priority ON arbitration_cases USING btree (priority);


--
-- Name: ix_arbitration_cases_review_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_arbitration_cases_review_id ON arbitration_cases USING btree (review_id);


--
-- Name: ix_arbitration_cases_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_arbitration_cases_status ON arbitration_cases USING btree (status);


--
-- Name: ix_arbitration_cases_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_arbitration_cases_user_id ON arbitration_cases USING btree (user_id);


--
-- Name: ix_arbitration_decisions_case_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_arbitration_decisions_case_id ON arbitration_decisions USING btree (case_id);


--
-- Name: ix_arbitration_decisions_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_arbitration_decisions_deleted_at ON arbitration_decisions USING btree (deleted_at);


--
-- Name: ix_auth_audit_log_action; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_auth_audit_log_action ON auth_audit_log USING btree (action);


--
-- Name: ix_auth_audit_log_occurred_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_auth_audit_log_occurred_at ON auth_audit_log USING btree (occurred_at);


--
-- Name: ix_auth_audit_log_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_auth_audit_log_user_id ON auth_audit_log USING btree (user_id);


--
-- Name: ix_behavior_patterns_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_behavior_patterns_deleted_at ON behavior_patterns USING btree (deleted_at);


--
-- Name: ix_behavior_patterns_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_behavior_patterns_user_id ON behavior_patterns USING btree (user_id);


--
-- Name: ix_behavioral_outcomes_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_behavioral_outcomes_deleted_at ON behavioral_outcomes USING btree (deleted_at);


--
-- Name: ix_behavioral_outcomes_intervention_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_behavioral_outcomes_intervention_id ON behavioral_outcomes USING btree (intervention_id);


--
-- Name: ix_behavioral_outcomes_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_behavioral_outcomes_user_id ON behavioral_outcomes USING btree (user_id);


--
-- Name: ix_broadcast_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_broadcast_messages_deleted_at ON broadcast_messages USING btree (deleted_at);


--
-- Name: ix_broadcast_messages_sender_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_broadcast_messages_sender_id ON broadcast_messages USING btree (sender_id);


--
-- Name: ix_calendar_events_plan_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_calendar_events_plan_id ON calendar_events USING btree (plan_id);


--
-- Name: ix_calendar_events_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_calendar_events_task_id ON calendar_events USING btree (task_id);


--
-- Name: ix_calendar_events_user_deleted; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_calendar_events_user_deleted ON calendar_events USING btree (user_id, deleted_at);


--
-- Name: ix_calendar_events_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_calendar_events_user_id ON calendar_events USING btree (user_id);


--
-- Name: ix_calendar_events_user_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_calendar_events_user_time ON calendar_events USING btree (user_id, start_time);


--
-- Name: ix_capsule_favorites_capsule_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_favorites_capsule_id ON capsule_favorites USING btree (capsule_id);


--
-- Name: ix_capsule_favorites_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_favorites_deleted_at ON capsule_favorites USING btree (deleted_at);


--
-- Name: ix_capsule_favorites_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_favorites_user_id ON capsule_favorites USING btree (user_id);


--
-- Name: ix_capsule_feedbacks_capsule_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_feedbacks_capsule_id ON capsule_feedbacks USING btree (capsule_id);


--
-- Name: ix_capsule_feedbacks_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_feedbacks_deleted_at ON capsule_feedbacks USING btree (deleted_at);


--
-- Name: ix_capsule_feedbacks_rating; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_feedbacks_rating ON capsule_feedbacks USING btree (rating);


--
-- Name: ix_capsule_feedbacks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_feedbacks_user_id ON capsule_feedbacks USING btree (user_id);


--
-- Name: ix_capsule_generation_jobs_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_generation_jobs_deleted_at ON capsule_generation_jobs USING btree (deleted_at);


--
-- Name: ix_capsule_generation_jobs_generation_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_generation_jobs_generation_type ON capsule_generation_jobs USING btree (generation_type);


--
-- Name: ix_capsule_generation_jobs_scheduled_for; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_generation_jobs_scheduled_for ON capsule_generation_jobs USING btree (scheduled_for);


--
-- Name: ix_capsule_generation_jobs_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_generation_jobs_status ON capsule_generation_jobs USING btree (status);


--
-- Name: ix_capsule_generation_jobs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_capsule_generation_jobs_user_id ON capsule_generation_jobs USING btree (user_id);


--
-- Name: ix_chat_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_messages_deleted_at ON chat_messages USING btree (deleted_at);


--
-- Name: ix_chat_messages_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_messages_session_id ON chat_messages USING btree (session_id);


--
-- Name: ix_chat_messages_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_messages_user_id ON chat_messages USING btree (user_id);


--
-- Name: ix_chat_sessions_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_sessions_deleted_at ON chat_sessions USING btree (deleted_at);


--
-- Name: ix_cognitive_fragments_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cognitive_fragments_deleted_at ON cognitive_fragments USING btree (deleted_at);


--
-- Name: ix_cognitive_fragments_source_event_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cognitive_fragments_source_event_id ON cognitive_fragments USING btree (source_event_id);


--
-- Name: ix_cognitive_fragments_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cognitive_fragments_user_id ON cognitive_fragments USING btree (user_id);


--
-- Name: ix_collaborative_galaxies_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_collaborative_galaxies_deleted_at ON collaborative_galaxies USING btree (deleted_at);


--
-- Name: ix_compliance_check_logs_check_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_compliance_check_logs_check_type ON compliance_check_logs USING btree (check_type);


--
-- Name: ix_compliance_check_logs_executed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_compliance_check_logs_executed_at ON compliance_check_logs USING btree (executed_at);


--
-- Name: ix_compliance_check_logs_executed_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_compliance_check_logs_executed_by ON compliance_check_logs USING btree (executed_by);


--
-- Name: ix_compliance_check_logs_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_compliance_check_logs_id ON compliance_check_logs USING btree (id);


--
-- Name: ix_context_budget_profiles_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_context_budget_profiles_deleted_at ON context_budget_profiles USING btree (deleted_at);


--
-- Name: ix_context_pack_feedback_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_context_pack_feedback_deleted_at ON context_pack_feedback USING btree (deleted_at);


--
-- Name: ix_context_pack_feedback_pack_run_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_context_pack_feedback_pack_run_id ON context_pack_feedback USING btree (pack_run_id);


--
-- Name: ix_context_pack_runs_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_context_pack_runs_deleted_at ON context_pack_runs USING btree (deleted_at);


--
-- Name: ix_context_pack_runs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_context_pack_runs_user_id ON context_pack_runs USING btree (user_id);


--
-- Name: ix_crdt_operation_log_galaxy_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_crdt_operation_log_galaxy_id ON crdt_operation_log USING btree (galaxy_id);


--
-- Name: ix_crdt_operation_log_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_crdt_operation_log_timestamp ON crdt_operation_log USING btree ("timestamp");


--
-- Name: ix_crypto_shredding_certificates_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_crypto_shredding_certificates_deleted_at ON crypto_shredding_certificates USING btree (deleted_at);


--
-- Name: ix_crypto_shredding_certificates_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_crypto_shredding_certificates_user_id ON crypto_shredding_certificates USING btree (user_id);


--
-- Name: ix_curiosity_capsules_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_curiosity_capsules_deleted_at ON curiosity_capsules USING btree (deleted_at);


--
-- Name: ix_curiosity_capsules_depth_level; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_curiosity_capsules_depth_level ON curiosity_capsules USING btree (depth_level);


--
-- Name: ix_curiosity_capsules_quality_score; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_curiosity_capsules_quality_score ON curiosity_capsules USING btree (quality_score);


--
-- Name: ix_curiosity_capsules_related_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_curiosity_capsules_related_task_id ON curiosity_capsules USING btree (related_task_id);


--
-- Name: ix_curiosity_capsules_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_curiosity_capsules_user_id ON curiosity_capsules USING btree (user_id);


--
-- Name: ix_data_access_logs_accessed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_data_access_logs_accessed_at ON data_access_logs USING btree (accessed_at);


--
-- Name: ix_data_access_logs_action; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_data_access_logs_action ON data_access_logs USING btree (action);


--
-- Name: ix_data_access_logs_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_data_access_logs_id ON data_access_logs USING btree (id);


--
-- Name: ix_data_access_logs_ip_address; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_data_access_logs_ip_address ON data_access_logs USING btree (ip_address);


--
-- Name: ix_data_access_logs_resource_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_data_access_logs_resource_id ON data_access_logs USING btree (resource_id);


--
-- Name: ix_data_access_logs_resource_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_data_access_logs_resource_type ON data_access_logs USING btree (resource_type);


--
-- Name: ix_data_access_logs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_data_access_logs_user_id ON data_access_logs USING btree (user_id);


--
-- Name: ix_decision_records_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_decision_records_deleted_at ON decision_records USING btree (deleted_at);


--
-- Name: ix_decision_records_module; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_decision_records_module ON decision_records USING btree (module);


--
-- Name: ix_decision_records_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_decision_records_user_id ON decision_records USING btree (user_id);


--
-- Name: ix_dictionary_entries_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_dictionary_entries_deleted_at ON dictionary_entries USING btree (deleted_at);


--
-- Name: ix_dictionary_entries_word; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_dictionary_entries_word ON dictionary_entries USING btree (word);


--
-- Name: ix_dlq_replay_audit_logs_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_dlq_replay_audit_logs_deleted_at ON dlq_replay_audit_logs USING btree (deleted_at);


--
-- Name: ix_dlq_replay_audit_logs_message_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_dlq_replay_audit_logs_message_id ON dlq_replay_audit_logs USING btree (message_id);


--
-- Name: ix_document_chunks_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_document_chunks_deleted_at ON document_chunks USING btree (deleted_at);


--
-- Name: ix_document_chunks_file_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_document_chunks_file_id ON document_chunks USING btree (file_id);


--
-- Name: ix_document_chunks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_document_chunks_user_id ON document_chunks USING btree (user_id);


--
-- Name: ix_episodic_memories_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_episodic_memories_deleted_at ON episodic_memories USING btree (deleted_at);


--
-- Name: ix_episodic_memories_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_episodic_memories_user_id ON episodic_memories USING btree (user_id);


--
-- Name: ix_evolution_predictions_actualized_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_evolution_predictions_actualized_at ON evolution_predictions USING btree (actualized_at);


--
-- Name: ix_evolution_predictions_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_evolution_predictions_created_at ON evolution_predictions USING btree (created_at);


--
-- Name: ix_evolution_predictions_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_evolution_predictions_deleted_at ON evolution_predictions USING btree (deleted_at);


--
-- Name: ix_evolution_predictions_memory_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_evolution_predictions_memory_id ON evolution_predictions USING btree (memory_id);


--
-- Name: ix_evolution_predictions_prediction_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_evolution_predictions_prediction_type ON evolution_predictions USING btree (prediction_type);


--
-- Name: ix_expansion_feedback_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_expansion_feedback_deleted_at ON expansion_feedback USING btree (deleted_at);


--
-- Name: ix_expansion_feedback_expansion_queue_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_expansion_feedback_expansion_queue_id ON expansion_feedback USING btree (expansion_queue_id);


--
-- Name: ix_expansion_feedback_trigger_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_expansion_feedback_trigger_node_id ON expansion_feedback USING btree (trigger_node_id);


--
-- Name: ix_expansion_feedback_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_expansion_feedback_user_id ON expansion_feedback USING btree (user_id);


--
-- Name: ix_focus_sessions_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_focus_sessions_deleted_at ON focus_sessions USING btree (deleted_at);


--
-- Name: ix_focus_sessions_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_focus_sessions_task_id ON focus_sessions USING btree (task_id);


--
-- Name: ix_focus_sessions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_focus_sessions_user_id ON focus_sessions USING btree (user_id);


--
-- Name: ix_friendships_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_friendships_deleted_at ON friendships USING btree (deleted_at);


--
-- Name: ix_friendships_friend_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_friendships_friend_id ON friendships USING btree (friend_id);


--
-- Name: ix_friendships_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_friendships_user_id ON friendships USING btree (user_id);


--
-- Name: ix_galaxy_skins_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_galaxy_skins_deleted_at ON galaxy_skins USING btree (deleted_at);


--
-- Name: ix_group_files_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_files_deleted_at ON group_files USING btree (deleted_at);


--
-- Name: ix_group_files_file_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_files_file_id ON group_files USING btree (file_id);


--
-- Name: ix_group_files_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_files_group_id ON group_files USING btree (group_id);


--
-- Name: ix_group_files_shared_by_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_files_shared_by_id ON group_files USING btree (shared_by_id);


--
-- Name: ix_group_members_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_members_deleted_at ON group_members USING btree (deleted_at);


--
-- Name: ix_group_members_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_members_group_id ON group_members USING btree (group_id);


--
-- Name: ix_group_members_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_members_user_id ON group_members USING btree (user_id);


--
-- Name: ix_group_message_reads_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_message_reads_deleted_at ON group_message_reads USING btree (deleted_at);


--
-- Name: ix_group_message_reads_message_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_message_reads_message_id ON group_message_reads USING btree (message_id);


--
-- Name: ix_group_message_reads_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_message_reads_user_id ON group_message_reads USING btree (user_id);


--
-- Name: ix_group_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_messages_deleted_at ON group_messages USING btree (deleted_at);


--
-- Name: ix_group_messages_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_messages_group_id ON group_messages USING btree (group_id);


--
-- Name: ix_group_messages_thread_root_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_messages_thread_root_id ON group_messages USING btree (thread_root_id);


--
-- Name: ix_group_task_claims_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_task_claims_deleted_at ON group_task_claims USING btree (deleted_at);


--
-- Name: ix_group_task_claims_group_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_task_claims_group_task_id ON group_task_claims USING btree (group_task_id);


--
-- Name: ix_group_task_claims_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_task_claims_user_id ON group_task_claims USING btree (user_id);


--
-- Name: ix_group_tasks_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_tasks_deleted_at ON group_tasks USING btree (deleted_at);


--
-- Name: ix_group_tasks_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_tasks_group_id ON group_tasks USING btree (group_id);


--
-- Name: ix_groups_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_groups_deleted_at ON groups USING btree (deleted_at);


--
-- Name: ix_idempotency_keys_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_idempotency_keys_expires_at ON idempotency_keys USING btree (expires_at);


--
-- Name: ix_idempotency_keys_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_idempotency_keys_user_id ON idempotency_keys USING btree (user_id);


--
-- Name: ix_intervention_audit_logs_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_audit_logs_deleted_at ON intervention_audit_logs USING btree (deleted_at);


--
-- Name: ix_intervention_audit_logs_occurred_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_audit_logs_occurred_at ON intervention_audit_logs USING btree (occurred_at);


--
-- Name: ix_intervention_audit_logs_request_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_audit_logs_request_id ON intervention_audit_logs USING btree (request_id);


--
-- Name: ix_intervention_audit_logs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_audit_logs_user_id ON intervention_audit_logs USING btree (user_id);


--
-- Name: ix_intervention_feedback_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_feedback_deleted_at ON intervention_feedback USING btree (deleted_at);


--
-- Name: ix_intervention_feedback_feedback_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_feedback_feedback_type ON intervention_feedback USING btree (feedback_type);


--
-- Name: ix_intervention_feedback_idempotency_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_feedback_idempotency_key ON intervention_feedback USING btree (idempotency_key);


--
-- Name: ix_intervention_feedback_request_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_feedback_request_id ON intervention_feedback USING btree (request_id);


--
-- Name: ix_intervention_feedback_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_feedback_user_id ON intervention_feedback USING btree (user_id);


--
-- Name: ix_intervention_requests_dedupe_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_requests_dedupe_key ON intervention_requests USING btree (dedupe_key);


--
-- Name: ix_intervention_requests_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_requests_deleted_at ON intervention_requests USING btree (deleted_at);


--
-- Name: ix_intervention_requests_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_requests_status ON intervention_requests USING btree (status);


--
-- Name: ix_intervention_requests_topic; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_requests_topic ON intervention_requests USING btree (topic);


--
-- Name: ix_intervention_requests_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_requests_user_id ON intervention_requests USING btree (user_id);


--
-- Name: ix_intervention_templates_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_templates_deleted_at ON intervention_templates USING btree (deleted_at);


--
-- Name: ix_intervention_templates_intent_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_intervention_templates_intent_type ON intervention_templates USING btree (intent_type);


--
-- Name: ix_intervention_templates_template_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_intervention_templates_template_id ON intervention_templates USING btree (template_id);


--
-- Name: ix_irt_item_parameters_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_irt_item_parameters_deleted_at ON irt_item_parameters USING btree (deleted_at);


--
-- Name: ix_irt_item_parameters_question_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_irt_item_parameters_question_id ON irt_item_parameters USING btree (question_id);


--
-- Name: ix_irt_item_parameters_subject_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_irt_item_parameters_subject_id ON irt_item_parameters USING btree (subject_id);


--
-- Name: ix_jobs_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_jobs_deleted_at ON jobs USING btree (deleted_at);


--
-- Name: ix_jobs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_jobs_user_id ON jobs USING btree (user_id);


--
-- Name: ix_knowledge_nodes_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_deleted_at ON knowledge_nodes USING btree (deleted_at);


--
-- Name: ix_knowledge_nodes_parent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_parent_id ON knowledge_nodes USING btree (parent_id);


--
-- Name: ix_knowledge_nodes_position_x; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_position_x ON knowledge_nodes USING btree (position_x);


--
-- Name: ix_knowledge_nodes_position_y; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_position_y ON knowledge_nodes USING btree (position_y);


--
-- Name: ix_knowledge_nodes_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_status ON knowledge_nodes USING btree (status);


--
-- Name: ix_knowledge_nodes_subject_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_subject_id ON knowledge_nodes USING btree (subject_id);


--
-- Name: ix_legal_holds_case_ref; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_legal_holds_case_ref ON legal_holds USING btree (case_ref);


--
-- Name: ix_legal_holds_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_legal_holds_deleted_at ON legal_holds USING btree (deleted_at);


--
-- Name: ix_legal_holds_device_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_legal_holds_device_id ON legal_holds USING btree (device_id);


--
-- Name: ix_legal_holds_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_legal_holds_user_id ON legal_holds USING btree (user_id);


--
-- Name: ix_login_attempts_attempted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_login_attempts_attempted_at ON login_attempts USING btree (attempted_at);


--
-- Name: ix_login_attempts_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_login_attempts_deleted_at ON login_attempts USING btree (deleted_at);


--
-- Name: ix_login_attempts_ip_address; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_login_attempts_ip_address ON login_attempts USING btree (ip_address);


--
-- Name: ix_login_attempts_success; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_login_attempts_success ON login_attempts USING btree (success);


--
-- Name: ix_login_attempts_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_login_attempts_user_id ON login_attempts USING btree (user_id);


--
-- Name: ix_login_attempts_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_login_attempts_username ON login_attempts USING btree (username);


--
-- Name: ix_ltm_daily_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ltm_daily_snapshots_deleted_at ON ltm_daily_snapshots USING btree (deleted_at);


--
-- Name: ix_ltm_daily_snapshots_snapshot_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_ltm_daily_snapshots_snapshot_date ON ltm_daily_snapshots USING btree (snapshot_date);


--
-- Name: ix_memory_corrections_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_corrections_deleted_at ON memory_corrections USING btree (deleted_at);


--
-- Name: ix_memory_corrections_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_corrections_user_id ON memory_corrections USING btree (user_id);


--
-- Name: ix_memory_evolutions_change_reason; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_evolutions_change_reason ON memory_evolutions USING btree (change_reason);


--
-- Name: ix_memory_evolutions_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_evolutions_created_at ON memory_evolutions USING btree (created_at);


--
-- Name: ix_memory_evolutions_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_evolutions_deleted_at ON memory_evolutions USING btree (deleted_at);


--
-- Name: ix_memory_evolutions_memory_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_evolutions_memory_id ON memory_evolutions USING btree (memory_id);


--
-- Name: ix_memory_evolutions_memory_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_evolutions_memory_type ON memory_evolutions USING btree (memory_type);


--
-- Name: ix_memory_goals_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_goals_deleted_at ON memory_goals USING btree (deleted_at);


--
-- Name: ix_memory_goals_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_goals_user_id ON memory_goals USING btree (user_id);


--
-- Name: ix_memory_preferences_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_preferences_deleted_at ON memory_preferences USING btree (deleted_at);


--
-- Name: ix_memory_preferences_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_preferences_user_id ON memory_preferences USING btree (user_id);


--
-- Name: ix_memory_rank_policies_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_memory_rank_policies_deleted_at ON memory_rank_policies USING btree (deleted_at);


--
-- Name: ix_message_favorites_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_message_favorites_deleted_at ON message_favorites USING btree (deleted_at);


--
-- Name: ix_message_favorites_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_message_favorites_user_id ON message_favorites USING btree (user_id);


--
-- Name: ix_message_reports_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_message_reports_deleted_at ON message_reports USING btree (deleted_at);


--
-- Name: ix_message_reports_reporter_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_message_reports_reporter_id ON message_reports USING btree (reporter_id);


--
-- Name: ix_next_action_selections_action_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_next_action_selections_action_type ON next_action_selections USING btree (action_type);


--
-- Name: ix_next_action_selections_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_next_action_selections_deleted_at ON next_action_selections USING btree (deleted_at);


--
-- Name: ix_next_action_selections_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_next_action_selections_task_id ON next_action_selections USING btree (task_id);


--
-- Name: ix_next_action_selections_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_next_action_selections_user_id ON next_action_selections USING btree (user_id);


--
-- Name: ix_nightly_reviews_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_nightly_reviews_deleted_at ON nightly_reviews USING btree (deleted_at);


--
-- Name: ix_nightly_reviews_review_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_nightly_reviews_review_date ON nightly_reviews USING btree (review_date);


--
-- Name: ix_nightly_reviews_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_nightly_reviews_user_id ON nightly_reviews USING btree (user_id);


--
-- Name: ix_node_expansion_queue_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_expansion_queue_deleted_at ON node_expansion_queue USING btree (deleted_at);


--
-- Name: ix_node_expansion_queue_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_expansion_queue_status ON node_expansion_queue USING btree (status);


--
-- Name: ix_node_expansion_queue_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_expansion_queue_user_id ON node_expansion_queue USING btree (user_id);


--
-- Name: ix_node_relations_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_relations_deleted_at ON node_relations USING btree (deleted_at);


--
-- Name: ix_node_relations_source_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_relations_source_node_id ON node_relations USING btree (source_node_id);


--
-- Name: ix_node_relations_target_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_relations_target_node_id ON node_relations USING btree (target_node_id);


--
-- Name: ix_notification_interactions_action_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notification_interactions_action_time ON notification_interactions USING btree (action_time);


--
-- Name: ix_notification_interactions_notification_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notification_interactions_notification_id ON notification_interactions USING btree (notification_id);


--
-- Name: ix_notification_interactions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notification_interactions_user_id ON notification_interactions USING btree (user_id);


--
-- Name: ix_notifications_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notifications_deleted_at ON notifications USING btree (deleted_at);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notifications_user_id ON notifications USING btree (user_id);


--
-- Name: ix_offline_message_queue_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_offline_message_queue_deleted_at ON offline_message_queue USING btree (deleted_at);


--
-- Name: ix_offline_message_queue_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_offline_message_queue_user_id ON offline_message_queue USING btree (user_id);


--
-- Name: ix_passive_signals_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_passive_signals_deleted_at ON passive_signals USING btree (deleted_at);


--
-- Name: ix_passive_signals_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_passive_signals_user_id ON passive_signals USING btree (user_id);


--
-- Name: ix_persona_snapshots_audit_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_persona_snapshots_audit_token ON persona_snapshots USING btree (audit_token);


--
-- Name: ix_persona_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_persona_snapshots_deleted_at ON persona_snapshots USING btree (deleted_at);


--
-- Name: ix_persona_snapshots_persona_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_persona_snapshots_persona_version ON persona_snapshots USING btree (persona_version);


--
-- Name: ix_persona_snapshots_source_event_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_persona_snapshots_source_event_id ON persona_snapshots USING btree (source_event_id);


--
-- Name: ix_persona_snapshots_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_persona_snapshots_user_id ON persona_snapshots USING btree (user_id);


--
-- Name: ix_photon_transaction_history_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_photon_transaction_history_deleted_at ON photon_transaction_history USING btree (deleted_at);


--
-- Name: ix_photon_transaction_history_transaction_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_photon_transaction_history_transaction_type ON photon_transaction_history USING btree (transaction_type);


--
-- Name: ix_photon_transaction_history_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_photon_transaction_history_user_id ON photon_transaction_history USING btree (user_id);


--
-- Name: ix_photon_transaction_history_user_id_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_photon_transaction_history_user_id_created_at ON photon_transaction_history USING btree (user_id, created_at);


--
-- Name: ix_plan_execution_records_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plan_execution_records_deleted_at ON plan_execution_records USING btree (deleted_at);


--
-- Name: ix_plan_execution_records_plan_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plan_execution_records_plan_id ON plan_execution_records USING btree (plan_id);


--
-- Name: ix_plan_execution_records_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plan_execution_records_user_id ON plan_execution_records USING btree (user_id);


--
-- Name: ix_plan_execution_records_validation_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plan_execution_records_validation_status ON plan_execution_records USING btree (validation_status);


--
-- Name: ix_plan_states_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plan_states_deleted_at ON plan_states USING btree (deleted_at);


--
-- Name: ix_plan_states_is_focus; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plan_states_is_focus ON plan_states USING btree (is_focus);


--
-- Name: ix_plan_states_last_focus_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plan_states_last_focus_time ON plan_states USING btree (last_focus_time);


--
-- Name: ix_plan_states_parallel_priority; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plan_states_parallel_priority ON plan_states USING btree (parallel_priority);


--
-- Name: ix_plan_states_plan_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_plan_states_plan_id ON plan_states USING btree (plan_id);


--
-- Name: ix_plan_states_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plan_states_status ON plan_states USING btree (status);


--
-- Name: ix_plan_states_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plan_states_user_id ON plan_states USING btree (user_id);


--
-- Name: ix_plans_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_deleted_at ON plans USING btree (deleted_at);


--
-- Name: ix_plans_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_is_active ON plans USING btree (is_active);


--
-- Name: ix_plans_is_primary; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_is_primary ON plans USING btree (is_primary);


--
-- Name: ix_plans_plan_stage; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_plan_stage ON plans USING btree (plan_stage);


--
-- Name: ix_plans_priority; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_priority ON plans USING btree (priority);


--
-- Name: ix_plans_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_user_id ON plans USING btree (user_id);


--
-- Name: ix_post_likes_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_post_likes_deleted_at ON post_likes USING btree (deleted_at);


--
-- Name: ix_posts_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_posts_deleted_at ON posts USING btree (deleted_at);


--
-- Name: ix_posts_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_posts_user_id ON posts USING btree (user_id);


--
-- Name: ix_private_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_private_messages_deleted_at ON private_messages USING btree (deleted_at);


--
-- Name: ix_private_messages_receiver_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_private_messages_receiver_id ON private_messages USING btree (receiver_id);


--
-- Name: ix_private_messages_sender_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_private_messages_sender_id ON private_messages USING btree (sender_id);


--
-- Name: ix_private_messages_thread_root_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_private_messages_thread_root_id ON private_messages USING btree (thread_root_id);


--
-- Name: ix_push_histories_content_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_push_histories_content_hash ON push_histories USING btree (content_hash);


--
-- Name: ix_push_histories_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_push_histories_deleted_at ON push_histories USING btree (deleted_at);


--
-- Name: ix_push_histories_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_push_histories_user_id ON push_histories USING btree (user_id);


--
-- Name: ix_push_preferences_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_push_preferences_deleted_at ON push_preferences USING btree (deleted_at);


--
-- Name: ix_push_preferences_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_push_preferences_user_id ON push_preferences USING btree (user_id);


--
-- Name: ix_recommendation_cache_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_recommendation_cache_deleted_at ON recommendation_cache USING btree (deleted_at);


--
-- Name: ix_response_feedback_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_response_feedback_created_at ON response_feedback USING btree (created_at);


--
-- Name: ix_response_feedback_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_response_feedback_deleted_at ON response_feedback USING btree (deleted_at);


--
-- Name: ix_response_feedback_response_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_response_feedback_response_id ON response_feedback USING btree (response_id);


--
-- Name: ix_response_feedback_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_response_feedback_user_id ON response_feedback USING btree (user_id);


--
-- Name: ix_response_feedback_workflow_prompt_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_response_feedback_workflow_prompt_created ON response_feedback USING btree (workflow_id, prompt_version, created_at);


--
-- Name: ix_review_feedback_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_feedback_deleted_at ON review_feedback USING btree (deleted_at);


--
-- Name: ix_review_feedback_feedback_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_review_feedback_feedback_id ON review_feedback USING btree (feedback_id);


--
-- Name: ix_review_feedback_feedback_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_feedback_feedback_type ON review_feedback USING btree (feedback_type);


--
-- Name: ix_review_feedback_review_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_feedback_review_id ON review_feedback USING btree (review_id);


--
-- Name: ix_review_feedback_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_feedback_user_id ON review_feedback USING btree (user_id);


--
-- Name: ix_review_history_decision; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_history_decision ON review_history USING btree (decision);


--
-- Name: ix_review_history_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_history_deleted_at ON review_history USING btree (deleted_at);


--
-- Name: ix_review_history_review_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_review_history_review_id ON review_history USING btree (review_id);


--
-- Name: ix_review_history_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_history_session_id ON review_history USING btree (session_id);


--
-- Name: ix_review_history_target_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_history_target_id ON review_history USING btree (target_id);


--
-- Name: ix_review_history_target_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_history_target_type ON review_history USING btree (target_type);


--
-- Name: ix_review_history_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_history_user_id ON review_history USING btree (user_id);


--
-- Name: ix_review_overrides_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_overrides_deleted_at ON review_overrides USING btree (deleted_at);


--
-- Name: ix_review_overrides_override_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_review_overrides_override_id ON review_overrides USING btree (override_id);


--
-- Name: ix_review_overrides_review_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_overrides_review_id ON review_overrides USING btree (review_id);


--
-- Name: ix_review_overrides_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_review_overrides_user_id ON review_overrides USING btree (user_id);


--
-- Name: ix_scaffolding_states_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_scaffolding_states_deleted_at ON scaffolding_states USING btree (deleted_at);


--
-- Name: ix_scaffolding_states_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_scaffolding_states_user_id ON scaffolding_states USING btree (user_id);


--
-- Name: ix_security_audit_logs_event_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_security_audit_logs_event_type ON security_audit_logs USING btree (event_type);


--
-- Name: ix_security_audit_logs_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_security_audit_logs_id ON security_audit_logs USING btree (id);


--
-- Name: ix_security_audit_logs_ip_address; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_security_audit_logs_ip_address ON security_audit_logs USING btree (ip_address);


--
-- Name: ix_security_audit_logs_resource; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_security_audit_logs_resource ON security_audit_logs USING btree (resource);


--
-- Name: ix_security_audit_logs_threat_level; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_security_audit_logs_threat_level ON security_audit_logs USING btree (threat_level);


--
-- Name: ix_security_audit_logs_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_security_audit_logs_timestamp ON security_audit_logs USING btree ("timestamp");


--
-- Name: ix_security_audit_logs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_security_audit_logs_user_id ON security_audit_logs USING btree (user_id);


--
-- Name: ix_seed_items_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_items_deleted_at ON seed_items USING btree (deleted_at);


--
-- Name: ix_seed_items_difficulty_level; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_items_difficulty_level ON seed_items USING btree (difficulty_level);


--
-- Name: ix_seed_items_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_items_is_active ON seed_items USING btree (is_active);


--
-- Name: ix_seed_items_item_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_items_item_type ON seed_items USING btree (item_type);


--
-- Name: ix_seed_items_library_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_items_library_id ON seed_items USING btree (library_id);


--
-- Name: ix_seed_items_subject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_items_subject ON seed_items USING btree (subject);


--
-- Name: ix_seed_libraries_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_libraries_category ON seed_libraries USING btree (category);


--
-- Name: ix_seed_libraries_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_libraries_deleted_at ON seed_libraries USING btree (deleted_at);


--
-- Name: ix_seed_libraries_is_featured; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_libraries_is_featured ON seed_libraries USING btree (is_featured);


--
-- Name: ix_seed_libraries_is_official; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_libraries_is_official ON seed_libraries USING btree (is_official);


--
-- Name: ix_seed_libraries_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_libraries_name ON seed_libraries USING btree (name);


--
-- Name: ix_seed_libraries_owner_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_libraries_owner_id ON seed_libraries USING btree (owner_id);


--
-- Name: ix_seed_libraries_visibility; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_libraries_visibility ON seed_libraries USING btree (visibility);


--
-- Name: ix_semantic_links_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_links_deleted_at ON semantic_links USING btree (deleted_at);


--
-- Name: ix_semantic_links_relation_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_links_relation_type ON semantic_links USING btree (relation_type);


--
-- Name: ix_semantic_links_source_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_links_source_id ON semantic_links USING btree (source_id);


--
-- Name: ix_semantic_links_source_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_links_source_type ON semantic_links USING btree (source_type);


--
-- Name: ix_semantic_links_target_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_links_target_id ON semantic_links USING btree (target_id);


--
-- Name: ix_semantic_links_target_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_links_target_type ON semantic_links USING btree (target_type);


--
-- Name: ix_shared_resources_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shared_resources_deleted_at ON shared_resources USING btree (deleted_at);


--
-- Name: ix_shared_resources_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shared_resources_group_id ON shared_resources USING btree (group_id);


--
-- Name: ix_shared_resources_target_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shared_resources_target_user_id ON shared_resources USING btree (target_user_id);


--
-- Name: ix_shop_items_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shop_items_deleted_at ON shop_items USING btree (deleted_at);


--
-- Name: ix_shop_items_item_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shop_items_item_type ON shop_items USING btree (item_type);


--
-- Name: ix_shop_items_item_type_is_available; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shop_items_item_type_is_available ON shop_items USING btree (item_type, is_available);


--
-- Name: ix_shop_items_rarity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shop_items_rarity ON shop_items USING btree (rarity);


--
-- Name: ix_shop_items_sort_order; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shop_items_sort_order ON shop_items USING btree (sort_order);


--
-- Name: ix_shop_purchases_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shop_purchases_deleted_at ON shop_purchases USING btree (deleted_at);


--
-- Name: ix_shop_purchases_item_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shop_purchases_item_id ON shop_purchases USING btree (item_id);


--
-- Name: ix_shop_purchases_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shop_purchases_user_id ON shop_purchases USING btree (user_id);


--
-- Name: ix_shop_purchases_user_id_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shop_purchases_user_id_created_at ON shop_purchases USING btree (user_id, created_at);


--
-- Name: ix_spark_contracts_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_spark_contracts_deleted_at ON spark_contracts USING btree (deleted_at);


--
-- Name: ix_stored_files_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_deleted_at ON stored_files USING btree (deleted_at);


--
-- Name: ix_stored_files_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_user_id ON stored_files USING btree (user_id);


--
-- Name: ix_strategy_nodes_content_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_strategy_nodes_content_hash ON strategy_nodes USING btree (content_hash);


--
-- Name: ix_strategy_nodes_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_strategy_nodes_deleted_at ON strategy_nodes USING btree (deleted_at);


--
-- Name: ix_strategy_nodes_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_strategy_nodes_user_id ON strategy_nodes USING btree (user_id);


--
-- Name: ix_study_buddies_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_study_buddies_deleted_at ON study_buddies USING btree (deleted_at);


--
-- Name: ix_study_records_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_study_records_deleted_at ON study_records USING btree (deleted_at);


--
-- Name: ix_study_records_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_study_records_node_id ON study_records USING btree (node_id);


--
-- Name: ix_study_records_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_study_records_user_id ON study_records USING btree (user_id);


--
-- Name: ix_subjects_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subjects_category ON subjects USING btree (category);


--
-- Name: ix_subjects_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subjects_is_active ON subjects USING btree (is_active);


--
-- Name: ix_subjects_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_subjects_name ON subjects USING btree (name);


--
-- Name: ix_subtasks_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subtasks_deleted_at ON subtasks USING btree (deleted_at);


--
-- Name: ix_subtasks_knowledge_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subtasks_knowledge_node_id ON subtasks USING btree (knowledge_node_id);


--
-- Name: ix_subtasks_parent_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subtasks_parent_task_id ON subtasks USING btree (parent_task_id);


--
-- Name: ix_subtasks_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subtasks_status ON subtasks USING btree (status);


--
-- Name: ix_system_config_change_logs_changed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_system_config_change_logs_changed_at ON system_config_change_logs USING btree (changed_at);


--
-- Name: ix_system_config_change_logs_changed_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_system_config_change_logs_changed_by ON system_config_change_logs USING btree (changed_by);


--
-- Name: ix_system_config_change_logs_config_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_system_config_change_logs_config_key ON system_config_change_logs USING btree (config_key);


--
-- Name: ix_system_config_change_logs_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_system_config_change_logs_id ON system_config_change_logs USING btree (id);


--
-- Name: ix_task_feedbacks_completion_quality; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_task_feedbacks_completion_quality ON task_feedbacks USING btree (completion_quality);


--
-- Name: ix_task_feedbacks_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_task_feedbacks_deleted_at ON task_feedbacks USING btree (deleted_at);


--
-- Name: ix_task_feedbacks_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_task_feedbacks_task_id ON task_feedbacks USING btree (task_id);


--
-- Name: ix_task_feedbacks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_task_feedbacks_user_id ON task_feedbacks USING btree (user_id);


--
-- Name: ix_task_knowledge_links_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_task_knowledge_links_deleted_at ON task_knowledge_links USING btree (deleted_at);


--
-- Name: ix_task_knowledge_links_knowledge_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_task_knowledge_links_knowledge_node_id ON task_knowledge_links USING btree (knowledge_node_id);


--
-- Name: ix_task_knowledge_links_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_task_knowledge_links_task_id ON task_knowledge_links USING btree (task_id);


--
-- Name: ix_task_resource_links_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_task_resource_links_deleted_at ON task_resource_links USING btree (deleted_at);


--
-- Name: ix_task_resource_links_resource_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_task_resource_links_resource_id ON task_resource_links USING btree (resource_id);


--
-- Name: ix_task_resource_links_resource_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_task_resource_links_resource_type ON task_resource_links USING btree (resource_type);


--
-- Name: ix_task_resource_links_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_task_resource_links_task_id ON task_resource_links USING btree (task_id);


--
-- Name: ix_tasks_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_deleted_at ON tasks USING btree (deleted_at);


--
-- Name: ix_tasks_plan_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_plan_id ON tasks USING btree (plan_id);


--
-- Name: ix_tasks_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_status ON tasks USING btree (status);


--
-- Name: ix_tasks_tool_result_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_tool_result_id ON tasks USING btree (tool_result_id);


--
-- Name: ix_tasks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_user_id ON tasks USING btree (user_id);


--
-- Name: ix_token_usage_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_token_usage_deleted_at ON token_usage USING btree (deleted_at);


--
-- Name: ix_token_usage_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_token_usage_session_id ON token_usage USING btree (session_id);


--
-- Name: ix_token_usage_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_token_usage_user_id ON token_usage USING btree (user_id);


--
-- Name: ix_tracking_events_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tracking_events_deleted_at ON tracking_events USING btree (deleted_at);


--
-- Name: ix_tracking_events_event_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tracking_events_event_id ON tracking_events USING btree (event_id);


--
-- Name: ix_tracking_events_event_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tracking_events_event_type ON tracking_events USING btree (event_type);


--
-- Name: ix_tracking_events_ts_ms; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tracking_events_ts_ms ON tracking_events USING btree (ts_ms);


--
-- Name: ix_tracking_events_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tracking_events_user_id ON tracking_events USING btree (user_id);


--
-- Name: ix_user_achievements_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_achievements_deleted_at ON user_achievements USING btree (deleted_at);


--
-- Name: ix_user_achievements_unlocked_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_achievements_unlocked_at ON user_achievements USING btree (unlocked_at);


--
-- Name: ix_user_blocks_blocked_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_blocks_blocked_id ON user_blocks USING btree (blocked_id);


--
-- Name: ix_user_blocks_blocker_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_blocks_blocker_id ON user_blocks USING btree (blocker_id);


--
-- Name: ix_user_consumables_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_consumables_deleted_at ON user_consumables USING btree (deleted_at);


--
-- Name: ix_user_consumables_effect_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_consumables_effect_type ON user_consumables USING btree (effect_type);


--
-- Name: ix_user_consumables_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_consumables_user_id ON user_consumables USING btree (user_id);


--
-- Name: ix_user_consumables_user_id_consumable_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_consumables_user_id_consumable_id ON user_consumables USING btree (user_id, consumable_id);


--
-- Name: ix_user_consumables_user_id_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_consumables_user_id_expires_at ON user_consumables USING btree (user_id, expires_at);


--
-- Name: ix_user_daily_metrics_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_daily_metrics_date ON user_daily_metrics USING btree (date);


--
-- Name: ix_user_daily_metrics_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_daily_metrics_deleted_at ON user_daily_metrics USING btree (deleted_at);


--
-- Name: ix_user_daily_metrics_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_daily_metrics_user_id ON user_daily_metrics USING btree (user_id);


--
-- Name: ix_user_devices_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_devices_deleted_at ON user_devices USING btree (deleted_at);


--
-- Name: ix_user_devices_device_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_devices_device_id ON user_devices USING btree (device_id);


--
-- Name: ix_user_devices_push_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_devices_push_token ON user_devices USING btree (push_token);


--
-- Name: ix_user_devices_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_devices_user_id ON user_devices USING btree (user_id);


--
-- Name: ix_user_encryption_keys_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_encryption_keys_deleted_at ON user_encryption_keys USING btree (deleted_at);


--
-- Name: ix_user_encryption_keys_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_encryption_keys_user_id ON user_encryption_keys USING btree (user_id);


--
-- Name: ix_user_galaxy_skins_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_galaxy_skins_deleted_at ON user_galaxy_skins USING btree (deleted_at);


--
-- Name: ix_user_intervention_settings_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_intervention_settings_deleted_at ON user_intervention_settings USING btree (deleted_at);


--
-- Name: ix_user_intervention_settings_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_user_intervention_settings_user_id ON user_intervention_settings USING btree (user_id);


--
-- Name: ix_user_irt_ability_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_irt_ability_deleted_at ON user_irt_ability USING btree (deleted_at);


--
-- Name: ix_user_irt_ability_subject_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_irt_ability_subject_id ON user_irt_ability USING btree (subject_id);


--
-- Name: ix_user_irt_ability_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_irt_ability_user_id ON user_irt_ability USING btree (user_id);


--
-- Name: ix_user_item_interactions_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_item_interactions_deleted_at ON user_item_interactions USING btree (deleted_at);


--
-- Name: ix_user_library_subscriptions_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_library_subscriptions_deleted_at ON user_library_subscriptions USING btree (deleted_at);


--
-- Name: ix_user_library_subscriptions_is_enabled; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_library_subscriptions_is_enabled ON user_library_subscriptions USING btree (is_enabled);


--
-- Name: ix_user_library_subscriptions_library_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_library_subscriptions_library_id ON user_library_subscriptions USING btree (library_id);


--
-- Name: ix_user_library_subscriptions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_library_subscriptions_user_id ON user_library_subscriptions USING btree (user_id);


--
-- Name: ix_user_memory_settings_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_memory_settings_deleted_at ON user_memory_settings USING btree (deleted_at);


--
-- Name: ix_user_memory_settings_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_user_memory_settings_user_id ON user_memory_settings USING btree (user_id);


--
-- Name: ix_user_node_status_next_review_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_node_status_next_review_at ON user_node_status USING btree (next_review_at);


--
-- Name: ix_user_persona_keys_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_persona_keys_deleted_at ON user_persona_keys USING btree (deleted_at);


--
-- Name: ix_user_persona_keys_key_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_persona_keys_key_id ON user_persona_keys USING btree (key_id);


--
-- Name: ix_user_persona_keys_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_persona_keys_user_id ON user_persona_keys USING btree (user_id);


--
-- Name: ix_user_preferences_center_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_preferences_center_deleted_at ON user_preferences_center USING btree (deleted_at);


--
-- Name: ix_user_preferences_center_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_user_preferences_center_user_id ON user_preferences_center USING btree (user_id);


--
-- Name: ix_user_sessions_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_sessions_deleted_at ON user_sessions USING btree (deleted_at);


--
-- Name: ix_user_sessions_device_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_sessions_device_id ON user_sessions USING btree (device_id);


--
-- Name: ix_user_sessions_device_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_sessions_device_type ON user_sessions USING btree (device_type);


--
-- Name: ix_user_sessions_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_sessions_is_active ON user_sessions USING btree (is_active);


--
-- Name: ix_user_sessions_last_active_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_sessions_last_active_at ON user_sessions USING btree (last_active_at);


--
-- Name: ix_user_sessions_refresh_token_jti; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_sessions_refresh_token_jti ON user_sessions USING btree (refresh_token_jti);


--
-- Name: ix_user_sessions_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_sessions_session_id ON user_sessions USING btree (session_id);


--
-- Name: ix_user_sessions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_sessions_user_id ON user_sessions USING btree (user_id);


--
-- Name: ix_user_settings_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_settings_deleted_at ON user_settings USING btree (deleted_at);


--
-- Name: ix_user_settings_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_user_settings_user_id ON user_settings USING btree (user_id);


--
-- Name: ix_user_state_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_state_snapshots_deleted_at ON user_state_snapshots USING btree (deleted_at);


--
-- Name: ix_user_state_snapshots_snapshot_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_state_snapshots_snapshot_at ON user_state_snapshots USING btree (snapshot_at);


--
-- Name: ix_user_state_snapshots_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_state_snapshots_user_id ON user_state_snapshots USING btree (user_id);


--
-- Name: ix_user_streak_days_user_day; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_user_streak_days_user_day ON user_streak_days USING btree (user_id, day);


--
-- Name: ix_user_streak_stats_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_streak_stats_deleted_at ON user_streak_stats USING btree (deleted_at);


--
-- Name: ix_user_titles_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_titles_deleted_at ON user_titles USING btree (deleted_at);


--
-- Name: ix_user_tool_history_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_tool_history_created_at ON user_tool_history USING btree (created_at);


--
-- Name: ix_user_tool_history_metrics; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_tool_history_metrics ON user_tool_history USING btree (user_id, tool_name, success, created_at);


--
-- Name: ix_user_tool_history_success; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_tool_history_success ON user_tool_history USING btree (user_id, tool_name, success);


--
-- Name: ix_user_tool_history_tool_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_tool_history_tool_name ON user_tool_history USING btree (tool_name);


--
-- Name: ix_user_tool_history_user_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_tool_history_user_created ON user_tool_history USING btree (user_id, created_at);


--
-- Name: ix_user_tool_history_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_tool_history_user_id ON user_tool_history USING btree (user_id);


--
-- Name: ix_user_visual_configs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_visual_configs_user_id ON user_visual_configs USING btree (user_id);


--
-- Name: ix_user_visual_elements_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_visual_elements_user_id ON user_visual_elements USING btree (user_id);


--
-- Name: ix_users_apple_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_apple_id ON users USING btree (apple_id);


--
-- Name: ix_users_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_deleted_at ON users USING btree (deleted_at);


--
-- Name: ix_users_equipped_skin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_equipped_skin ON users USING btree (equipped_skin);


--
-- Name: ix_users_equipped_skin_source; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_equipped_skin_source ON users USING btree (equipped_skin_source);


--
-- Name: ix_users_equipped_title; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_equipped_title ON users USING btree (equipped_title);


--
-- Name: ix_users_equipped_title_source; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_equipped_title_source ON users USING btree (equipped_title_source);


--
-- Name: ix_users_google_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_google_id ON users USING btree (google_id);


--
-- Name: ix_users_wechat_unionid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_wechat_unionid ON users USING btree (wechat_unionid);


--
-- Name: ix_visual_elements_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visual_elements_active ON visual_elements USING btree (is_active);


--
-- Name: ix_visual_elements_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visual_elements_category ON visual_elements USING btree (category);


--
-- Name: ix_visual_elements_type_rarity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visual_elements_type_rarity ON visual_elements USING btree (element_type, rarity);


--
-- Name: ix_word_books_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_word_books_deleted_at ON word_books USING btree (deleted_at);


--
-- Name: ix_word_books_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_word_books_user_id ON word_books USING btree (user_id);


--
-- Name: ix_word_books_word; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_word_books_word ON word_books USING btree (word);


--
-- Name: uq_memory_preferences_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_memory_preferences_version ON memory_preferences USING btree (user_id, pref_key, version);


--
-- Name: uq_memory_rank_policies_scope; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_memory_rank_policies_scope ON memory_rank_policies USING btree (scope_type, scope_key);


--
-- Name: ab_experiment_assignments ab_experiment_assignments_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiment_assignments
    ADD CONSTRAINT ab_experiment_assignments_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES ab_experiments(id) ON DELETE CASCADE;


--
-- Name: ab_experiment_assignments ab_experiment_assignments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiment_assignments
    ADD CONSTRAINT ab_experiment_assignments_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: ab_experiment_assignments ab_experiment_assignments_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiment_assignments
    ADD CONSTRAINT ab_experiment_assignments_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES ab_experiment_variants(id) ON DELETE CASCADE;


--
-- Name: ab_experiment_metrics ab_experiment_metrics_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiment_metrics
    ADD CONSTRAINT ab_experiment_metrics_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES ab_experiments(id) ON DELETE CASCADE;


--
-- Name: ab_experiment_metrics ab_experiment_metrics_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiment_metrics
    ADD CONSTRAINT ab_experiment_metrics_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: ab_experiment_metrics ab_experiment_metrics_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiment_metrics
    ADD CONSTRAINT ab_experiment_metrics_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES ab_experiment_variants(id) ON DELETE CASCADE;


--
-- Name: ab_experiment_variants ab_experiment_variants_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiment_variants
    ADD CONSTRAINT ab_experiment_variants_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES ab_experiments(id) ON DELETE CASCADE;


--
-- Name: ab_experiments ab_experiments_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiments
    ADD CONSTRAINT ab_experiments_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: achievements achievements_first_unlocker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY achievements
    ADD CONSTRAINT achievements_first_unlocker_id_fkey FOREIGN KEY (first_unlocker_id) REFERENCES users(id);


--
-- Name: achievements achievements_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY achievements
    ADD CONSTRAINT achievements_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES achievements(id);


--
-- Name: auth_audit_log auth_audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY auth_audit_log
    ADD CONSTRAINT auth_audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: behavior_patterns behavior_patterns_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY behavior_patterns
    ADD CONSTRAINT behavior_patterns_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: behavioral_outcomes behavioral_outcomes_intervention_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY behavioral_outcomes
    ADD CONSTRAINT behavioral_outcomes_intervention_id_fkey FOREIGN KEY (intervention_id) REFERENCES intervention_requests(id);


--
-- Name: behavioral_outcomes behavioral_outcomes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY behavioral_outcomes
    ADD CONSTRAINT behavioral_outcomes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: broadcast_messages broadcast_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY broadcast_messages
    ADD CONSTRAINT broadcast_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: calendar_events calendar_events_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY calendar_events
    ADD CONSTRAINT calendar_events_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE SET NULL;


--
-- Name: calendar_events calendar_events_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY calendar_events
    ADD CONSTRAINT calendar_events_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL;


--
-- Name: calendar_events calendar_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY calendar_events
    ADD CONSTRAINT calendar_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: capsule_favorites capsule_favorites_capsule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY capsule_favorites
    ADD CONSTRAINT capsule_favorites_capsule_id_fkey FOREIGN KEY (capsule_id) REFERENCES curiosity_capsules(id) ON DELETE CASCADE;


--
-- Name: capsule_favorites capsule_favorites_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY capsule_favorites
    ADD CONSTRAINT capsule_favorites_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: capsule_feedbacks capsule_feedbacks_capsule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY capsule_feedbacks
    ADD CONSTRAINT capsule_feedbacks_capsule_id_fkey FOREIGN KEY (capsule_id) REFERENCES curiosity_capsules(id) ON DELETE CASCADE;


--
-- Name: capsule_feedbacks capsule_feedbacks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY capsule_feedbacks
    ADD CONSTRAINT capsule_feedbacks_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: capsule_generation_jobs capsule_generation_jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY capsule_generation_jobs
    ADD CONSTRAINT capsule_generation_jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages
    ADD CONSTRAINT chat_messages_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);


--
-- Name: chat_messages chat_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages
    ADD CONSTRAINT chat_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: chat_sessions chat_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_sessions
    ADD CONSTRAINT chat_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: cognitive_fragments cognitive_fragments_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cognitive_fragments
    ADD CONSTRAINT cognitive_fragments_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);


--
-- Name: cognitive_fragments cognitive_fragments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cognitive_fragments
    ADD CONSTRAINT cognitive_fragments_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: collaborative_galaxies collaborative_galaxies_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY collaborative_galaxies
    ADD CONSTRAINT collaborative_galaxies_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id);


--
-- Name: collaborative_galaxies collaborative_galaxies_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY collaborative_galaxies
    ADD CONSTRAINT collaborative_galaxies_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES subjects(id);


--
-- Name: compliance_check_logs compliance_check_logs_executed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY compliance_check_logs
    ADD CONSTRAINT compliance_check_logs_executed_by_fkey FOREIGN KEY (executed_by) REFERENCES users(id);


--
-- Name: crdt_operation_log crdt_operation_log_galaxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY crdt_operation_log
    ADD CONSTRAINT crdt_operation_log_galaxy_id_fkey FOREIGN KEY (galaxy_id) REFERENCES collaborative_galaxies(id);


--
-- Name: crdt_operation_log crdt_operation_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY crdt_operation_log
    ADD CONSTRAINT crdt_operation_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: crdt_snapshots crdt_snapshots_galaxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY crdt_snapshots
    ADD CONSTRAINT crdt_snapshots_galaxy_id_fkey FOREIGN KEY (galaxy_id) REFERENCES collaborative_galaxies(id);


--
-- Name: crypto_shredding_certificates crypto_shredding_certificates_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY crypto_shredding_certificates
    ADD CONSTRAINT crypto_shredding_certificates_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: curiosity_capsules curiosity_capsules_related_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY curiosity_capsules
    ADD CONSTRAINT curiosity_capsules_related_task_id_fkey FOREIGN KEY (related_task_id) REFERENCES tasks(id);


--
-- Name: curiosity_capsules curiosity_capsules_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY curiosity_capsules
    ADD CONSTRAINT curiosity_capsules_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: data_access_logs data_access_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY data_access_logs
    ADD CONSTRAINT data_access_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: decision_records decision_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY decision_records
    ADD CONSTRAINT decision_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: dlq_replay_audit_logs dlq_replay_audit_logs_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY dlq_replay_audit_logs
    ADD CONSTRAINT dlq_replay_audit_logs_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES users(id);


--
-- Name: dlq_replay_audit_logs dlq_replay_audit_logs_approver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY dlq_replay_audit_logs
    ADD CONSTRAINT dlq_replay_audit_logs_approver_id_fkey FOREIGN KEY (approver_id) REFERENCES users(id);


--
-- Name: document_chunks document_chunks_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY document_chunks
    ADD CONSTRAINT document_chunks_file_id_fkey FOREIGN KEY (file_id) REFERENCES stored_files(id) ON DELETE CASCADE;


--
-- Name: document_chunks document_chunks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY document_chunks
    ADD CONSTRAINT document_chunks_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: episodic_memories episodic_memories_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY episodic_memories
    ADD CONSTRAINT episodic_memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: error_records error_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY error_records
    ADD CONSTRAINT error_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: expansion_feedback expansion_feedback_expansion_queue_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY expansion_feedback
    ADD CONSTRAINT expansion_feedback_expansion_queue_id_fkey FOREIGN KEY (expansion_queue_id) REFERENCES node_expansion_queue(id);


--
-- Name: expansion_feedback expansion_feedback_trigger_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY expansion_feedback
    ADD CONSTRAINT expansion_feedback_trigger_node_id_fkey FOREIGN KEY (trigger_node_id) REFERENCES knowledge_nodes(id);


--
-- Name: expansion_feedback expansion_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY expansion_feedback
    ADD CONSTRAINT expansion_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: ab_experiments fk_ab_experiments_winning_variant_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ab_experiments
    ADD CONSTRAINT fk_ab_experiments_winning_variant_id FOREIGN KEY (winning_variant_id) REFERENCES ab_experiment_variants(id) ON DELETE SET NULL;


--
-- Name: subtasks fk_subtasks_knowledge_node_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY subtasks
    ADD CONSTRAINT fk_subtasks_knowledge_node_id FOREIGN KEY (knowledge_node_id) REFERENCES knowledge_nodes(id) ON DELETE SET NULL;


--
-- Name: focus_sessions focus_sessions_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY focus_sessions
    ADD CONSTRAINT focus_sessions_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);


--
-- Name: focus_sessions focus_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY focus_sessions
    ADD CONSTRAINT focus_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: friendships friendships_friend_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY friendships
    ADD CONSTRAINT friendships_friend_id_fkey FOREIGN KEY (friend_id) REFERENCES users(id);


--
-- Name: friendships friendships_initiated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY friendships
    ADD CONSTRAINT friendships_initiated_by_fkey FOREIGN KEY (initiated_by) REFERENCES users(id);


--
-- Name: friendships friendships_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY friendships
    ADD CONSTRAINT friendships_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: galaxy_user_permissions galaxy_user_permissions_galaxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY galaxy_user_permissions
    ADD CONSTRAINT galaxy_user_permissions_galaxy_id_fkey FOREIGN KEY (galaxy_id) REFERENCES collaborative_galaxies(id);


--
-- Name: galaxy_user_permissions galaxy_user_permissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY galaxy_user_permissions
    ADD CONSTRAINT galaxy_user_permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: group_files group_files_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_files
    ADD CONSTRAINT group_files_file_id_fkey FOREIGN KEY (file_id) REFERENCES stored_files(id) ON DELETE CASCADE;


--
-- Name: group_files group_files_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_files
    ADD CONSTRAINT group_files_group_id_fkey FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE;


--
-- Name: group_files group_files_shared_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_files
    ADD CONSTRAINT group_files_shared_by_id_fkey FOREIGN KEY (shared_by_id) REFERENCES users(id);


--
-- Name: group_members group_members_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_members
    ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE;


--
-- Name: group_members group_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_members
    ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: group_message_reads group_message_reads_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_message_reads
    ADD CONSTRAINT group_message_reads_message_id_fkey FOREIGN KEY (message_id) REFERENCES group_messages(id) ON DELETE CASCADE;


--
-- Name: group_message_reads group_message_reads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_message_reads
    ADD CONSTRAINT group_message_reads_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: group_messages group_messages_forwarded_from_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_messages
    ADD CONSTRAINT group_messages_forwarded_from_id_fkey FOREIGN KEY (forwarded_from_id) REFERENCES group_messages(id);


--
-- Name: group_messages group_messages_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_messages
    ADD CONSTRAINT group_messages_group_id_fkey FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE;


--
-- Name: group_messages group_messages_reply_to_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_messages
    ADD CONSTRAINT group_messages_reply_to_id_fkey FOREIGN KEY (reply_to_id) REFERENCES group_messages(id);


--
-- Name: group_messages group_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_messages
    ADD CONSTRAINT group_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES users(id);


--
-- Name: group_messages group_messages_thread_root_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_messages
    ADD CONSTRAINT group_messages_thread_root_id_fkey FOREIGN KEY (thread_root_id) REFERENCES group_messages(id);


--
-- Name: group_task_claims group_task_claims_group_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_task_claims
    ADD CONSTRAINT group_task_claims_group_task_id_fkey FOREIGN KEY (group_task_id) REFERENCES group_tasks(id) ON DELETE CASCADE;


--
-- Name: group_task_claims group_task_claims_personal_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_task_claims
    ADD CONSTRAINT group_task_claims_personal_task_id_fkey FOREIGN KEY (personal_task_id) REFERENCES tasks(id);


--
-- Name: group_task_claims group_task_claims_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_task_claims
    ADD CONSTRAINT group_task_claims_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: group_tasks group_tasks_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_tasks
    ADD CONSTRAINT group_tasks_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id);


--
-- Name: group_tasks group_tasks_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_tasks
    ADD CONSTRAINT group_tasks_group_id_fkey FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE;


--
-- Name: idempotency_keys idempotency_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY idempotency_keys
    ADD CONSTRAINT idempotency_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: intervention_audit_logs intervention_audit_logs_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_audit_logs
    ADD CONSTRAINT intervention_audit_logs_request_id_fkey FOREIGN KEY (request_id) REFERENCES intervention_requests(id);


--
-- Name: intervention_audit_logs intervention_audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_audit_logs
    ADD CONSTRAINT intervention_audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: intervention_feedback intervention_feedback_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_feedback
    ADD CONSTRAINT intervention_feedback_request_id_fkey FOREIGN KEY (request_id) REFERENCES intervention_requests(id);


--
-- Name: intervention_feedback intervention_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_feedback
    ADD CONSTRAINT intervention_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: intervention_requests intervention_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_requests
    ADD CONSTRAINT intervention_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: jobs jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: knowledge_nodes knowledge_nodes_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY knowledge_nodes
    ADD CONSTRAINT knowledge_nodes_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES knowledge_nodes(id);


--
-- Name: knowledge_nodes knowledge_nodes_source_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY knowledge_nodes
    ADD CONSTRAINT knowledge_nodes_source_file_id_fkey FOREIGN KEY (source_file_id) REFERENCES stored_files(id);


--
-- Name: knowledge_nodes knowledge_nodes_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY knowledge_nodes
    ADD CONSTRAINT knowledge_nodes_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES subjects(id);


--
-- Name: legal_holds legal_holds_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY legal_holds
    ADD CONSTRAINT legal_holds_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES users(id);


--
-- Name: legal_holds legal_holds_released_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY legal_holds
    ADD CONSTRAINT legal_holds_released_by_fkey FOREIGN KEY (released_by) REFERENCES users(id);


--
-- Name: legal_holds legal_holds_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY legal_holds
    ADD CONSTRAINT legal_holds_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: login_attempts login_attempts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY login_attempts
    ADD CONSTRAINT login_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: mastery_audit_log mastery_audit_log_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY mastery_audit_log
    ADD CONSTRAINT mastery_audit_log_node_id_fkey FOREIGN KEY (node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE;


--
-- Name: mastery_audit_log mastery_audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY mastery_audit_log
    ADD CONSTRAINT mastery_audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: memory_corrections memory_corrections_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_corrections
    ADD CONSTRAINT memory_corrections_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: memory_goals memory_goals_linked_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_goals
    ADD CONSTRAINT memory_goals_linked_plan_id_fkey FOREIGN KEY (linked_plan_id) REFERENCES plans(id);


--
-- Name: memory_goals memory_goals_linked_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_goals
    ADD CONSTRAINT memory_goals_linked_task_id_fkey FOREIGN KEY (linked_task_id) REFERENCES tasks(id);


--
-- Name: memory_goals memory_goals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_goals
    ADD CONSTRAINT memory_goals_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: memory_preferences memory_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_preferences
    ADD CONSTRAINT memory_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: message_favorites message_favorites_group_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY message_favorites
    ADD CONSTRAINT message_favorites_group_message_id_fkey FOREIGN KEY (group_message_id) REFERENCES group_messages(id) ON DELETE CASCADE;


--
-- Name: message_favorites message_favorites_private_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY message_favorites
    ADD CONSTRAINT message_favorites_private_message_id_fkey FOREIGN KEY (private_message_id) REFERENCES private_messages(id) ON DELETE CASCADE;


--
-- Name: message_favorites message_favorites_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY message_favorites
    ADD CONSTRAINT message_favorites_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: message_reports message_reports_group_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY message_reports
    ADD CONSTRAINT message_reports_group_message_id_fkey FOREIGN KEY (group_message_id) REFERENCES group_messages(id) ON DELETE SET NULL;


--
-- Name: message_reports message_reports_private_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY message_reports
    ADD CONSTRAINT message_reports_private_message_id_fkey FOREIGN KEY (private_message_id) REFERENCES private_messages(id) ON DELETE SET NULL;


--
-- Name: message_reports message_reports_reporter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY message_reports
    ADD CONSTRAINT message_reports_reporter_id_fkey FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: message_reports message_reports_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY message_reports
    ADD CONSTRAINT message_reports_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: nightly_reviews nightly_reviews_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY nightly_reviews
    ADD CONSTRAINT nightly_reviews_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: node_expansion_queue node_expansion_queue_trigger_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_trigger_node_id_fkey FOREIGN KEY (trigger_node_id) REFERENCES knowledge_nodes(id);


--
-- Name: node_expansion_queue node_expansion_queue_trigger_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_trigger_task_id_fkey FOREIGN KEY (trigger_task_id) REFERENCES tasks(id);


--
-- Name: node_expansion_queue node_expansion_queue_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: node_relations node_relations_source_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY node_relations
    ADD CONSTRAINT node_relations_source_node_id_fkey FOREIGN KEY (source_node_id) REFERENCES knowledge_nodes(id);


--
-- Name: node_relations node_relations_target_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY node_relations
    ADD CONSTRAINT node_relations_target_node_id_fkey FOREIGN KEY (target_node_id) REFERENCES knowledge_nodes(id);


--
-- Name: notification_interactions notification_interactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY notification_interactions
    ADD CONSTRAINT notification_interactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: notification_preferences notification_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY notification_preferences
    ADD CONSTRAINT notification_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: offline_message_queue offline_message_queue_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY offline_message_queue
    ADD CONSTRAINT offline_message_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: passive_signals passive_signals_intervention_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY passive_signals
    ADD CONSTRAINT passive_signals_intervention_id_fkey FOREIGN KEY (intervention_id) REFERENCES intervention_requests(id);


--
-- Name: passive_signals passive_signals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY passive_signals
    ADD CONSTRAINT passive_signals_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: persona_snapshots persona_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY persona_snapshots
    ADD CONSTRAINT persona_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: photon_transaction_history photon_transaction_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY photon_transaction_history
    ADD CONSTRAINT photon_transaction_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: plan_execution_records plan_execution_records_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plan_execution_records
    ADD CONSTRAINT plan_execution_records_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE;


--
-- Name: plan_execution_records plan_execution_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plan_execution_records
    ADD CONSTRAINT plan_execution_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: plan_states plan_states_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plan_states
    ADD CONSTRAINT plan_states_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE;


--
-- Name: plan_states plan_states_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plan_states
    ADD CONSTRAINT plan_states_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: plans plans_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plans
    ADD CONSTRAINT plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: post_likes post_likes_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY post_likes
    ADD CONSTRAINT post_likes_post_id_fkey FOREIGN KEY (post_id) REFERENCES posts(id);


--
-- Name: post_likes post_likes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY post_likes
    ADD CONSTRAINT post_likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: posts posts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY posts
    ADD CONSTRAINT posts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: private_messages private_messages_forwarded_from_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY private_messages
    ADD CONSTRAINT private_messages_forwarded_from_id_fkey FOREIGN KEY (forwarded_from_id) REFERENCES private_messages(id);


--
-- Name: private_messages private_messages_receiver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY private_messages
    ADD CONSTRAINT private_messages_receiver_id_fkey FOREIGN KEY (receiver_id) REFERENCES users(id);


--
-- Name: private_messages private_messages_reply_to_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY private_messages
    ADD CONSTRAINT private_messages_reply_to_id_fkey FOREIGN KEY (reply_to_id) REFERENCES private_messages(id);


--
-- Name: private_messages private_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY private_messages
    ADD CONSTRAINT private_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES users(id);


--
-- Name: private_messages private_messages_thread_root_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY private_messages
    ADD CONSTRAINT private_messages_thread_root_id_fkey FOREIGN KEY (thread_root_id) REFERENCES private_messages(id);


--
-- Name: push_histories push_histories_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY push_histories
    ADD CONSTRAINT push_histories_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: push_preferences push_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY push_preferences
    ADD CONSTRAINT push_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: recommendation_cache recommendation_cache_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY recommendation_cache
    ADD CONSTRAINT recommendation_cache_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: scaffolding_states scaffolding_states_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY scaffolding_states
    ADD CONSTRAINT scaffolding_states_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: security_audit_logs security_audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY security_audit_logs
    ADD CONSTRAINT security_audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: seed_items seed_items_library_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY seed_items
    ADD CONSTRAINT seed_items_library_id_fkey FOREIGN KEY (library_id) REFERENCES seed_libraries(id) ON DELETE CASCADE;


--
-- Name: seed_libraries seed_libraries_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY seed_libraries
    ADD CONSTRAINT seed_libraries_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: shared_resources shared_resources_behavior_pattern_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT shared_resources_behavior_pattern_id_fkey FOREIGN KEY (behavior_pattern_id) REFERENCES behavior_patterns(id);


--
-- Name: shared_resources shared_resources_cognitive_fragment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT shared_resources_cognitive_fragment_id_fkey FOREIGN KEY (cognitive_fragment_id) REFERENCES cognitive_fragments(id);


--
-- Name: shared_resources shared_resources_curiosity_capsule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT shared_resources_curiosity_capsule_id_fkey FOREIGN KEY (curiosity_capsule_id) REFERENCES curiosity_capsules(id);


--
-- Name: shared_resources shared_resources_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT shared_resources_group_id_fkey FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE;


--
-- Name: shared_resources shared_resources_knowledge_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT shared_resources_knowledge_node_id_fkey FOREIGN KEY (knowledge_node_id) REFERENCES knowledge_nodes(id);


--
-- Name: shared_resources shared_resources_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT shared_resources_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES plans(id);


--
-- Name: shared_resources shared_resources_shared_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT shared_resources_shared_by_fkey FOREIGN KEY (shared_by) REFERENCES users(id);


--
-- Name: shared_resources shared_resources_target_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT shared_resources_target_user_id_fkey FOREIGN KEY (target_user_id) REFERENCES users(id);


--
-- Name: shared_resources shared_resources_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT shared_resources_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);


--
-- Name: shop_purchases shop_purchases_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shop_purchases
    ADD CONSTRAINT shop_purchases_item_id_fkey FOREIGN KEY (item_id) REFERENCES shop_items(id) ON DELETE RESTRICT;


--
-- Name: shop_purchases shop_purchases_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shop_purchases
    ADD CONSTRAINT shop_purchases_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: spark_contracts spark_contracts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY spark_contracts
    ADD CONSTRAINT spark_contracts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: stored_files stored_files_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY stored_files
    ADD CONSTRAINT stored_files_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: strategy_nodes strategy_nodes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY strategy_nodes
    ADD CONSTRAINT strategy_nodes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: study_buddies study_buddies_user1_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY study_buddies
    ADD CONSTRAINT study_buddies_user1_id_fkey FOREIGN KEY (user1_id) REFERENCES users(id);


--
-- Name: study_buddies study_buddies_user2_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY study_buddies
    ADD CONSTRAINT study_buddies_user2_id_fkey FOREIGN KEY (user2_id) REFERENCES users(id);


--
-- Name: study_records study_records_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY study_records
    ADD CONSTRAINT study_records_node_id_fkey FOREIGN KEY (node_id) REFERENCES knowledge_nodes(id);


--
-- Name: study_records study_records_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY study_records
    ADD CONSTRAINT study_records_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);


--
-- Name: study_records study_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY study_records
    ADD CONSTRAINT study_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: subtasks subtasks_parent_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY subtasks
    ADD CONSTRAINT subtasks_parent_task_id_fkey FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE CASCADE;


--
-- Name: system_config_change_logs system_config_change_logs_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY system_config_change_logs
    ADD CONSTRAINT system_config_change_logs_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES users(id);


--
-- Name: task_feedbacks task_feedbacks_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_feedbacks
    ADD CONSTRAINT task_feedbacks_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;


--
-- Name: task_feedbacks task_feedbacks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_feedbacks
    ADD CONSTRAINT task_feedbacks_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: task_knowledge_links task_knowledge_links_knowledge_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_knowledge_links
    ADD CONSTRAINT task_knowledge_links_knowledge_node_id_fkey FOREIGN KEY (knowledge_node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE;


--
-- Name: task_knowledge_links task_knowledge_links_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_knowledge_links
    ADD CONSTRAINT task_knowledge_links_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;


--
-- Name: task_resource_links task_resource_links_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_resource_links
    ADD CONSTRAINT task_resource_links_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_knowledge_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tasks
    ADD CONSTRAINT tasks_knowledge_node_id_fkey FOREIGN KEY (knowledge_node_id) REFERENCES knowledge_nodes(id);


--
-- Name: tasks tasks_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tasks
    ADD CONSTRAINT tasks_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES plans(id);


--
-- Name: tasks tasks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tasks
    ADD CONSTRAINT tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: token_usage token_usage_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY token_usage
    ADD CONSTRAINT token_usage_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: tracking_events tracking_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tracking_events
    ADD CONSTRAINT tracking_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_achievements user_achievements_achievement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_achievements
    ADD CONSTRAINT user_achievements_achievement_id_fkey FOREIGN KEY (achievement_id) REFERENCES achievements(id);


--
-- Name: user_achievements user_achievements_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_achievements
    ADD CONSTRAINT user_achievements_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_blocks user_blocks_blocked_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_blocks
    ADD CONSTRAINT user_blocks_blocked_id_fkey FOREIGN KEY (blocked_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_blocks user_blocks_blocker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_blocks
    ADD CONSTRAINT user_blocks_blocker_id_fkey FOREIGN KEY (blocker_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_consumables user_consumables_consumable_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_consumables
    ADD CONSTRAINT user_consumables_consumable_id_fkey FOREIGN KEY (consumable_id) REFERENCES shop_items(id) ON DELETE RESTRICT;


--
-- Name: user_consumables user_consumables_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_consumables
    ADD CONSTRAINT user_consumables_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_daily_metrics user_daily_metrics_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_daily_metrics
    ADD CONSTRAINT user_daily_metrics_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_devices user_devices_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_devices
    ADD CONSTRAINT user_devices_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_encryption_keys user_encryption_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_encryption_keys
    ADD CONSTRAINT user_encryption_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_galaxy_skins user_galaxy_skins_skin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_galaxy_skins
    ADD CONSTRAINT user_galaxy_skins_skin_id_fkey FOREIGN KEY (skin_id) REFERENCES galaxy_skins(id);


--
-- Name: user_galaxy_skins user_galaxy_skins_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_galaxy_skins
    ADD CONSTRAINT user_galaxy_skins_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_intervention_settings user_intervention_settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_intervention_settings
    ADD CONSTRAINT user_intervention_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_irt_ability user_irt_ability_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_irt_ability
    ADD CONSTRAINT user_irt_ability_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_item_interactions user_item_interactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_item_interactions
    ADD CONSTRAINT user_item_interactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_library_subscriptions user_library_subscriptions_library_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_library_subscriptions
    ADD CONSTRAINT user_library_subscriptions_library_id_fkey FOREIGN KEY (library_id) REFERENCES seed_libraries(id) ON DELETE CASCADE;


--
-- Name: user_library_subscriptions user_library_subscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_library_subscriptions
    ADD CONSTRAINT user_library_subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_memory_settings user_memory_settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_memory_settings
    ADD CONSTRAINT user_memory_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_node_status user_node_status_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_node_status
    ADD CONSTRAINT user_node_status_node_id_fkey FOREIGN KEY (node_id) REFERENCES knowledge_nodes(id);


--
-- Name: user_node_status user_node_status_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_node_status
    ADD CONSTRAINT user_node_status_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_persona_keys user_persona_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_persona_keys
    ADD CONSTRAINT user_persona_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_preferences_center user_preferences_center_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_preferences_center
    ADD CONSTRAINT user_preferences_center_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_settings user_settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_settings
    ADD CONSTRAINT user_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_state_snapshots user_state_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_state_snapshots
    ADD CONSTRAINT user_state_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_streak_days user_streak_days_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_streak_days
    ADD CONSTRAINT user_streak_days_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_streak_stats user_streak_stats_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_streak_stats
    ADD CONSTRAINT user_streak_stats_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_titles user_titles_source_achievement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_titles
    ADD CONSTRAINT user_titles_source_achievement_id_fkey FOREIGN KEY (source_achievement_id) REFERENCES achievements(id);


--
-- Name: user_titles user_titles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_titles
    ADD CONSTRAINT user_titles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_tool_history user_tool_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_tool_history
    ADD CONSTRAINT user_tool_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_visual_configs user_visual_configs_equipped_background_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_visual_configs
    ADD CONSTRAINT user_visual_configs_equipped_background_id_fkey FOREIGN KEY (equipped_background_id) REFERENCES visual_elements(id);


--
-- Name: user_visual_configs user_visual_configs_equipped_effect_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_visual_configs
    ADD CONSTRAINT user_visual_configs_equipped_effect_id_fkey FOREIGN KEY (equipped_effect_id) REFERENCES visual_elements(id);


--
-- Name: user_visual_configs user_visual_configs_equipped_particle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_visual_configs
    ADD CONSTRAINT user_visual_configs_equipped_particle_id_fkey FOREIGN KEY (equipped_particle_id) REFERENCES visual_elements(id);


--
-- Name: user_visual_configs user_visual_configs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_visual_configs
    ADD CONSTRAINT user_visual_configs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_visual_elements user_visual_elements_element_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_visual_elements
    ADD CONSTRAINT user_visual_elements_element_id_fkey FOREIGN KEY (element_id) REFERENCES visual_elements(id) ON DELETE CASCADE;


--
-- Name: user_visual_elements user_visual_elements_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_visual_elements
    ADD CONSTRAINT user_visual_elements_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: word_books word_books_source_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY word_books
    ADD CONSTRAINT word_books_source_task_id_fkey FOREIGN KEY (source_task_id) REFERENCES tasks(id);


--
-- Name: word_books word_books_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY word_books
    ADD CONSTRAINT word_books_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- PostgreSQL database dump complete
--


