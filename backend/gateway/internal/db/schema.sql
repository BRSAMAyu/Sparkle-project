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
-- Name: ag_catalog; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA ag_catalog;


ALTER SCHEMA ag_catalog OWNER TO postgres;

--
-- Name: sparkle_galaxy; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA sparkle_galaxy;


ALTER SCHEMA sparkle_galaxy OWNER TO postgres;

--
-- Name: age; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS age WITH SCHEMA ag_catalog;


--
-- Name: EXTENSION age; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION age IS 'AGE database extension';


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
-- Name: accountabilityslottype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE accountabilityslottype AS ENUM (
    'core'
);


ALTER TYPE accountabilityslottype OWNER TO postgres;

--
-- Name: accountabilitystatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE accountabilitystatus AS ENUM (
    'pending',
    'active',
    'paused',
    'ended'
);


ALTER TYPE accountabilitystatus OWNER TO postgres;

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
    'SPRINT',
    'planning'
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
-- Name: backgroundtaskstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE backgroundtaskstatus AS ENUM (
    'PENDING',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'CANCELLED'
);


ALTER TYPE backgroundtaskstatus OWNER TO postgres;

--
-- Name: backgroundtasktype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE backgroundtasktype AS ENUM (
    'AI_GENERATION',
    'DATA_SYNC',
    'PLAN_GENERATION',
    'GALAXY_EXPANSION',
    'TASK_BATCH'
);


ALTER TYPE backgroundtasktype OWNER TO postgres;

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
-- Name: delivery_channel_enum; Type: TYPE; Schema: public; Owner: brsama
--

CREATE TYPE delivery_channel_enum AS ENUM (
    'CHAT',
    'PUSH',
    'IN_APP',
    'FOCUS_MODE'
);


ALTER TYPE delivery_channel_enum OWNER TO brsama;

--
-- Name: delivery_strategy_enum; Type: TYPE; Schema: public; Owner: brsama
--

CREATE TYPE delivery_strategy_enum AS ENUM (
    'CURIOUS',
    'SUPPORTIVE',
    'DIRECT',
    'MICRO_RESTART'
);


ALTER TYPE delivery_strategy_enum OWNER TO brsama;

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
    'REJECTED',
    'CANCELLED',
    'BLOCKED'
);


ALTER TYPE friendshipstatus OWNER TO postgres;

--
-- Name: groupfiletrustlevel; Type: TYPE; Schema: public; Owner: brsama
--

CREATE TYPE groupfiletrustlevel AS ENUM (
    'official',
    'verified',
    'member'
);


ALTER TYPE groupfiletrustlevel OWNER TO brsama;

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
-- Name: intervention_acceptance_enum; Type: TYPE; Schema: public; Owner: brsama
--

CREATE TYPE intervention_acceptance_enum AS ENUM (
    'CREATED',
    'DELIVERED',
    'SEEN',
    'DISMISSED',
    'SNOOZED',
    'ACCEPTED',
    'ACTED'
);


ALTER TYPE intervention_acceptance_enum OWNER TO brsama;

--
-- Name: intervention_outcome_enum; Type: TYPE; Schema: public; Owner: brsama
--

CREATE TYPE intervention_outcome_enum AS ENUM (
    'PENDING',
    'EFFECTIVE',
    'INEFFECTIVE',
    'UNKNOWN'
);


ALTER TYPE intervention_outcome_enum OWNER TO brsama;

--
-- Name: intervention_trigger_enum; Type: TYPE; Schema: public; Owner: brsama
--

CREATE TYPE intervention_trigger_enum AS ENUM (
    'CONCEPT_GAP',
    'PLAN_RISK',
    'STALL_PATTERN',
    'OVERLOAD',
    'MISALIGNMENT'
);


ALTER TYPE intervention_trigger_enum OWNER TO brsama;

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
    'OTHER',
    'HATE_SPEECH'
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
    'ABANDONED',
    'STUCK',
    'PAUSED',
    'RESTORE'
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

--
-- Name: admin_audit_log_prevent_mutation(); Type: FUNCTION; Schema: public; Owner: brsama
--

CREATE FUNCTION admin_audit_log_prevent_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            BEGIN
                RAISE EXCEPTION 'admin_audit_log is append-only';
            END;
            $$;


ALTER FUNCTION admin_audit_log_prevent_mutation() OWNER TO brsama;

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
-- Name: accountability_checkin; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE accountability_checkin (
    id uuid NOT NULL,
    partnership_id uuid NOT NULL,
    user_id uuid NOT NULL,
    content text NOT NULL,
    mood integer DEFAULT 3 NOT NULL,
    minutes integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    likes integer DEFAULT 0 NOT NULL,
    encouragements jsonb DEFAULT '[]'::jsonb NOT NULL,
    liked_by jsonb DEFAULT '[]'::jsonb NOT NULL
);


ALTER TABLE accountability_checkin OWNER TO postgres;

--
-- Name: accountability_partnership; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE accountability_partnership (
    id uuid NOT NULL,
    initiator_id uuid NOT NULL,
    partner_id uuid NOT NULL,
    friendship_id uuid,
    initiator_goal text NOT NULL,
    partner_goal text,
    check_in_days integer DEFAULT 1 NOT NULL,
    status accountabilitystatus DEFAULT 'pending'::accountabilitystatus NOT NULL,
    started_at timestamp with time zone,
    ended_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    slot_type accountabilityslottype DEFAULT 'core'::accountabilityslottype NOT NULL
);


ALTER TABLE accountability_partnership OWNER TO postgres;

--
-- Name: accountability_policies; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE accountability_policies (
    policy_id character varying(128) NOT NULL,
    user_id uuid NOT NULL,
    commitment_id uuid NOT NULL,
    policy_version character varying(32) NOT NULL,
    policy_type character varying(64) NOT NULL,
    trigger_type character varying(64) NOT NULL,
    action_type character varying(64) NOT NULL,
    ir_payload json NOT NULL,
    ir_hash character varying(64) NOT NULL,
    next_trigger_at timestamp without time zone,
    last_triggered_at timestamp without time zone,
    cooldown_until timestamp without time zone,
    last_event_key character varying(128),
    execution_count integer DEFAULT 0 NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    is_shadow boolean DEFAULT false NOT NULL,
    revoked_at timestamp without time zone,
    last_skip_reason character varying(64),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE accountability_policies OWNER TO brsama;

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
-- Name: admin_audit_log; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE admin_audit_log (
    id uuid NOT NULL,
    admin_user_id uuid,
    action character varying(160) NOT NULL,
    category character varying(80) NOT NULL,
    risk character varying(20) NOT NULL,
    method character varying(10) NOT NULL,
    path character varying(500) NOT NULL,
    query_hash character varying(64),
    status_code integer NOT NULL,
    outcome character varying(20) NOT NULL,
    duration_ms double precision NOT NULL,
    ip_address character varying(45),
    user_agent text,
    request_id character varying(100),
    trace_id character varying(100),
    actor_claims json,
    error_message text,
    details json,
    occurred_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    retention_until timestamp without time zone DEFAULT (CURRENT_TIMESTAMP + '90 days'::interval) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE admin_audit_log OWNER TO brsama;

--
-- Name: agent_execution_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE agent_execution_stats (
    id integer NOT NULL,
    user_id uuid NOT NULL,
    session_id character varying(255) NOT NULL,
    request_id character varying(255) NOT NULL,
    agent_type character varying(50) NOT NULL,
    agent_name character varying(100),
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    duration_ms integer,
    status character varying(20) NOT NULL,
    tool_name character varying(100),
    operation character varying(255),
    extra_metadata jsonb,
    error_message text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE agent_execution_stats OWNER TO postgres;

--
-- Name: agent_execution_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE agent_execution_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE agent_execution_stats_id_seq OWNER TO postgres;

--
-- Name: agent_execution_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE agent_execution_stats_id_seq OWNED BY agent_execution_stats.id;


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
-- Name: asset_suggestion_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE asset_suggestion_logs (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    user_id uuid NOT NULL,
    session_id character varying(64),
    policy_id character varying(50) NOT NULL,
    trigger_event character varying(100) NOT NULL,
    evidence_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    decision character varying(20) NOT NULL,
    decision_reason character varying(255),
    user_response character varying(20) DEFAULT 'PENDING'::character varying,
    response_at timestamp without time zone,
    cooldown_until timestamp without time zone,
    asset_id uuid
);


ALTER TABLE asset_suggestion_logs OWNER TO postgres;

--
-- Name: aurora_core_session_snapshots; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE aurora_core_session_snapshots (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    session_id character varying(128) NOT NULL,
    user_id character varying(128) NOT NULL,
    conversation_id character varying(128),
    surface character varying(64) NOT NULL,
    status character varying(32) NOT NULL,
    stage character varying(32) NOT NULL,
    resume_token_hash character varying(64),
    last_activity_at timestamp without time zone NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    payload jsonb NOT NULL,
    metadata jsonb NOT NULL
);


ALTER TABLE aurora_core_session_snapshots OWNER TO brsama;

--
-- Name: aurora_decision_telemetry; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE aurora_decision_telemetry (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    decision_id character varying(36) NOT NULL,
    user_id uuid NOT NULL,
    surface character varying(64) NOT NULL,
    conversation_id character varying(128) NOT NULL,
    request_id character varying(128),
    decided_at timestamp without time zone NOT NULL,
    wake_score double precision DEFAULT '0'::double precision NOT NULL,
    energy_level character varying(16) DEFAULT 'light'::character varying NOT NULL,
    strategy_payload jsonb NOT NULL,
    expression_payload jsonb NOT NULL,
    context_mask jsonb NOT NULL,
    action character varying(64) NOT NULL,
    chat_directive_core jsonb NOT NULL,
    standard_layer_contract jsonb NOT NULL,
    strategy_confidence double precision DEFAULT '0.7'::double precision NOT NULL,
    outcome character varying(32),
    outcome_filled_at timestamp without time zone,
    outcome_reason text
);


ALTER TABLE aurora_decision_telemetry OWNER TO brsama;

--
-- Name: aurora_judgment_records; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE aurora_judgment_records (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    task_sufficiency_score double precision NOT NULL,
    task_missing_dimensions json DEFAULT '[]'::json NOT NULL,
    context_sufficiency_score double precision NOT NULL,
    context_missing_dimensions json DEFAULT '[]'::json NOT NULL,
    judge_version character varying(16) DEFAULT 'v1'::character varying NOT NULL,
    computed_at timestamp without time zone NOT NULL
);


ALTER TABLE aurora_judgment_records OWNER TO brsama;

--
-- Name: aurora_policy_versions; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE aurora_policy_versions (
    id character varying(128) NOT NULL,
    version character varying(64) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    author character varying(64) NOT NULL,
    changelog jsonb NOT NULL,
    persona_invariants jsonb NOT NULL,
    audit_invariants jsonb NOT NULL,
    proactive_policy jsonb NOT NULL,
    reconciliation_policy jsonb NOT NULL,
    continuous_learning_policy jsonb NOT NULL,
    parameter_write_authority jsonb NOT NULL,
    interaction_model_registry jsonb NOT NULL,
    materiality_threshold double precision NOT NULL,
    default_rollback_anchor_schema jsonb NOT NULL
);


ALTER TABLE aurora_policy_versions OWNER TO brsama;

--
-- Name: aurora_scheduled_wakes; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE aurora_scheduled_wakes (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    wake_id character varying(128) NOT NULL,
    user_id uuid NOT NULL,
    surface character varying(64) NOT NULL,
    conversation_id character varying(128) NOT NULL,
    session_id uuid,
    runtime_session_id character varying(128),
    scheduled_at timestamp without time zone NOT NULL,
    reason text NOT NULL,
    planned_action character varying(128) NOT NULL,
    status character varying(32) NOT NULL,
    executed_at timestamp without time zone,
    urgency_score double precision DEFAULT '0.5'::double precision NOT NULL,
    payload jsonb NOT NULL,
    metadata jsonb NOT NULL,
    suppression_reason character varying(64)
);


ALTER TABLE aurora_scheduled_wakes OWNER TO brsama;

--
-- Name: aurora_state_snapshots; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE aurora_state_snapshots (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    surface character varying(64) NOT NULL,
    conversation_id character varying(128) NOT NULL,
    runtime_session_id character varying(128),
    snapshot_version integer DEFAULT 1 NOT NULL,
    snapshot_at timestamp without time zone NOT NULL,
    user_model_snapshot jsonb NOT NULL,
    informational_tensions jsonb NOT NULL,
    current_intent jsonb,
    latent_threads jsonb NOT NULL,
    activity_profile jsonb NOT NULL,
    last_decision_at timestamp without time zone,
    metadata jsonb NOT NULL
);


ALTER TABLE aurora_state_snapshots OWNER TO brsama;

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
-- Name: background_tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE background_tasks (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    task_type backgroundtasktype NOT NULL,
    name character varying(255) NOT NULL,
    status backgroundtaskstatus DEFAULT 'PENDING'::backgroundtaskstatus NOT NULL,
    progress double precision DEFAULT '0'::double precision,
    progress_message text,
    result_data jsonb,
    error_message text,
    related_entity_id uuid,
    related_entity_type character varying(50),
    external_task_id character varying(255),
    completed_at timestamp without time zone
);


ALTER TABLE background_tasks OWNER TO postgres;

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
-- Name: candidate_action_feedback; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE candidate_action_feedback (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    candidate_id character varying(64) NOT NULL,
    action_type character varying(32) NOT NULL,
    feedback_type character varying(16) NOT NULL,
    executed boolean DEFAULT false NOT NULL,
    completion_result jsonb,
    context_snapshot jsonb NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE candidate_action_feedback OWNER TO brsama;

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
-- Name: card_adoption_records; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE card_adoption_records (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    share_record_id uuid NOT NULL,
    adopter_user_id uuid NOT NULL,
    adopted_root_card_id uuid,
    import_mode character varying(24) NOT NULL,
    attribution_payload jsonb DEFAULT '{}'::jsonb NOT NULL
);


ALTER TABLE card_adoption_records OWNER TO brsama;

--
-- Name: card_edges; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE card_edges (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    from_card_id uuid NOT NULL,
    to_card_id uuid NOT NULL,
    edge_type character varying(32) NOT NULL,
    binding_mode character varying(24) DEFAULT '''OWNED'''::character varying NOT NULL,
    order_index integer,
    weight double precision,
    temporal_window jsonb,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    active boolean DEFAULT true NOT NULL,
    removed_at timestamp without time zone
);


ALTER TABLE card_edges OWNER TO brsama;

--
-- Name: card_share_records; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE card_share_records (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    snapshot_id uuid NOT NULL,
    root_card_id uuid,
    shared_by_user_id uuid NOT NULL,
    target_user_id uuid,
    group_id uuid,
    scope character varying(24) NOT NULL,
    permission character varying(24) DEFAULT '''ADOPT'''::character varying NOT NULL,
    message character varying(500),
    adoption_count integer DEFAULT 0 NOT NULL,
    view_count integer DEFAULT 0 NOT NULL,
    revoked_at timestamp without time zone,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


ALTER TABLE card_share_records OWNER TO brsama;

--
-- Name: card_snapshots; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE card_snapshots (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    root_card_id uuid,
    source_owner_id uuid,
    source_card_type character varying(32) NOT NULL,
    schema_version character varying(16) DEFAULT '''1.0'''::character varying NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


ALTER TABLE card_snapshots OWNER TO brsama;

--
-- Name: cards; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE cards (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    card_type character varying(32) NOT NULL,
    owner_id uuid NOT NULL,
    holder_id uuid NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    schema_version character varying(16) DEFAULT '''3.0'''::character varying NOT NULL,
    lifecycle_status character varying(24) DEFAULT '''DRAFT'''::character varying NOT NULL,
    visibility character varying(24) DEFAULT '''PRIVATE'''::character varying NOT NULL,
    tags jsonb DEFAULT '[]'::jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    source_type character varying(24) DEFAULT '''ORIGINAL'''::character varying NOT NULL,
    origin_card_id uuid,
    origin_snapshot_id uuid,
    created_by character varying(16) DEFAULT '''AI'''::character varying NOT NULL,
    updated_by character varying(16) DEFAULT '''AI'''::character varying NOT NULL,
    archived_at timestamp without time zone
);


ALTER TABLE cards OWNER TO brsama;

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
    deleted_at timestamp without time zone,
    group_id uuid,
    galaxy_scope character varying(32) DEFAULT 'shared'::character varying NOT NULL
);


ALTER TABLE collaborative_galaxies OWNER TO postgres;

--
-- Name: commitments; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE commitments (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    description text NOT NULL,
    node_id character varying(255) NOT NULL,
    success_criteria text NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    activated_at timestamp without time zone,
    resolved_at timestamp without time zone,
    resolution text,
    deadline timestamp without time zone NOT NULL,
    milestone_ids jsonb NOT NULL,
    witness_ids jsonb NOT NULL,
    window_override character varying(32),
    evidence_refs jsonb NOT NULL,
    projection_policy character varying(64) NOT NULL,
    write_path character varying(64) NOT NULL,
    shareability character varying(64) NOT NULL
);


ALTER TABLE commitments OWNER TO brsama;

--
-- Name: community_aggregate_signals; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE community_aggregate_signals (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    signal_id character varying(128) NOT NULL,
    cohort_id character varying(128) NOT NULL,
    cohort_key character varying(256) NOT NULL,
    cohort_criteria jsonb NOT NULL,
    signal_type character varying(64) NOT NULL,
    stat_name character varying(128) NOT NULL,
    cohort_size integer NOT NULL,
    min_cohort_size integer NOT NULL,
    privacy_tier character varying(32) NOT NULL,
    value double precision,
    noise_std double precision NOT NULL,
    confidence_interval jsonb NOT NULL,
    pattern jsonb NOT NULL,
    observation jsonb NOT NULL,
    privacy_cost double precision NOT NULL,
    status character varying(32) NOT NULL,
    generated_at timestamp without time zone NOT NULL,
    expires_at timestamp without time zone,
    metadata jsonb NOT NULL
);


ALTER TABLE community_aggregate_signals OWNER TO brsama;

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
-- Name: conflict_resolution_records; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE conflict_resolution_records (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    loser_record_id uuid,
    winner_record_id uuid,
    loser_lane character varying(40),
    winner_lane character varying(40),
    resolution_action character varying(32) NOT NULL,
    resolution_reason character varying(128) NOT NULL,
    resolved_at timestamp without time zone NOT NULL,
    conflict_key character varying(64),
    evidence_tokens json DEFAULT '[]'::json NOT NULL,
    metadata_payload json DEFAULT '{}'::json NOT NULL
);


ALTER TABLE conflict_resolution_records OWNER TO brsama;

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
-- Name: counterfactual_evaluation_reports; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE counterfactual_evaluation_reports (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id character varying(128) NOT NULL,
    context_signature jsonb NOT NULL,
    context_hash character varying(64) NOT NULL,
    policy_a character varying(128) NOT NULL,
    policy_b character varying(128) NOT NULL,
    estimate jsonb NOT NULL,
    confidence double precision DEFAULT '0'::double precision NOT NULL,
    evidence_grade integer DEFAULT 0 NOT NULL,
    generated_at timestamp without time zone NOT NULL,
    replaced_by_id uuid,
    promotion_candidate jsonb NOT NULL,
    promotion_status character varying(32) DEFAULT 'not_ready'::character varying NOT NULL,
    iron_law_compliance jsonb NOT NULL,
    metadata jsonb NOT NULL
);


ALTER TABLE counterfactual_evaluation_reports OWNER TO brsama;

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
-- Name: custom_expert_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE custom_expert_profiles (
    user_id uuid NOT NULL,
    name character varying(120) NOT NULL,
    description character varying(500),
    system_prompt text NOT NULL,
    base_expert_id character varying(100),
    preferred_model_key character varying(100),
    preferred_model_tier character varying(40),
    reasoning_mode character varying(40) DEFAULT 'balanced'::character varying NOT NULL,
    source character varying(40) DEFAULT 'user_defined'::character varying NOT NULL,
    metadata_json json,
    is_enabled boolean DEFAULT true NOT NULL,
    deleted_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE custom_expert_profiles OWNER TO postgres;

--
-- Name: custom_expert_teams; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE custom_expert_teams (
    user_id uuid NOT NULL,
    name character varying(120) NOT NULL,
    description character varying(500),
    collaboration_mode character varying(40) DEFAULT 'auto'::character varying NOT NULL,
    expert_ids json NOT NULL,
    answer_expert_ids json,
    metadata_json json,
    is_enabled boolean DEFAULT true NOT NULL,
    deleted_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE custom_expert_teams OWNER TO postgres;

--
-- Name: daily_behavior_vector; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE daily_behavior_vector (
    user_id uuid NOT NULL,
    vector_date date NOT NULL,
    dims_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    active_event_count integer DEFAULT 0 NOT NULL,
    stage30_dim_count integer DEFAULT 0 NOT NULL,
    silent_window_cut boolean DEFAULT false NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE daily_behavior_vector OWNER TO brsama;

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
-- Name: distilled_strategy_cache; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE distilled_strategy_cache (
    id uuid NOT NULL,
    title character varying(255) NOT NULL,
    description text NOT NULL,
    applicability_scope text NOT NULL,
    status character varying(64) NOT NULL,
    shareability character varying(64) NOT NULL,
    source_trajectory_type character varying(128) NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE distilled_strategy_cache OWNER TO brsama;

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
-- Name: document_retrieval_feedback; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE document_retrieval_feedback (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    file_id uuid NOT NULL,
    chunk_id uuid,
    query_intent_type character varying(64),
    feedback_score integer NOT NULL,
    feedback_source character varying(32) NOT NULL,
    conversation_id character varying(128),
    context json
);


ALTER TABLE document_retrieval_feedback OWNER TO brsama;

--
-- Name: durable_session_state_snapshots; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE durable_session_state_snapshots (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    session_id character varying(128) NOT NULL,
    user_id character varying(128),
    request_id character varying(128),
    fsm_state character varying(32) NOT NULL,
    details text NOT NULL,
    payload jsonb NOT NULL,
    recoverable boolean NOT NULL,
    last_seen_at timestamp without time zone NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    metadata jsonb NOT NULL
);


ALTER TABLE durable_session_state_snapshots OWNER TO brsama;

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
    archived_at timestamp without time zone,
    source_lane character varying(40) DEFAULT 'direct_capture'::character varying NOT NULL,
    confidence double precision,
    evidence_token character varying(128),
    decay_policy character varying(32),
    semantic_key character varying(64),
    revoked_at timestamp without time zone,
    subject_type character varying(32) NOT NULL,
    due_at timestamp without time zone,
    resolved_at timestamp without time zone,
    mentioned_entity_hash character varying(64),
    mentioned_entity_owner_user_id uuid
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
    is_deleted boolean,
    affected_node_id uuid,
    mastery_delta double precision
);


ALTER TABLE error_records OWNER TO postgres;

--
-- Name: event_bus_dlq; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE event_bus_dlq (
    stream character varying(255) NOT NULL,
    event_type character varying(255) NOT NULL,
    user_id uuid,
    group_name character varying(255) NOT NULL,
    consumer_name character varying(255) NOT NULL,
    message_id character varying(255) NOT NULL,
    retry_count integer DEFAULT 0 NOT NULL,
    failure_stage character varying(64) DEFAULT 'consume'::character varying NOT NULL,
    error text NOT NULL,
    payload jsonb NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE event_bus_dlq OWNER TO brsama;

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
-- Name: execution_audit_log; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE execution_audit_log (
    id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    intent_id uuid NOT NULL,
    user_id uuid NOT NULL,
    action character varying(64) NOT NULL,
    actor character varying(32) NOT NULL,
    details json,
    occurred_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE execution_audit_log OWNER TO brsama;

--
-- Name: execution_intents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE execution_intents (
    id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    plan_id uuid,
    task_id uuid NOT NULL,
    user_id uuid NOT NULL,
    execution_mode character varying(20) DEFAULT 'human'::character varying NOT NULL,
    executor character varying(20) DEFAULT 'manual'::character varying NOT NULL,
    goal text NOT NULL,
    instructions jsonb DEFAULT '[]'::jsonb NOT NULL,
    target_env character varying(20),
    policy jsonb DEFAULT '{}'::jsonb NOT NULL,
    success_criteria jsonb DEFAULT '{}'::jsonb NOT NULL,
    result_contract jsonb DEFAULT '{}'::jsonb NOT NULL,
    timeout_seconds integer DEFAULT 300 NOT NULL,
    status character varying(30) DEFAULT 'draft'::character varying NOT NULL,
    trust_level character varying(20) DEFAULT 'raw'::character varying NOT NULL,
    external_run_id character varying(255),
    idempotency_key character varying(255) NOT NULL,
    error_category character varying(100),
    error_message text,
    dispatched_at timestamp without time zone,
    completed_at timestamp without time zone
);


ALTER TABLE execution_intents OWNER TO postgres;

--
-- Name: execution_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE execution_records (
    id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    execution_intent_id uuid NOT NULL,
    user_id uuid NOT NULL,
    task_id uuid,
    executor_type character varying(50) DEFAULT 'openclaw'::character varying NOT NULL,
    external_run_id character varying(255),
    raw_response jsonb DEFAULT '{}'::jsonb NOT NULL,
    parsed_output jsonb,
    artifacts jsonb DEFAULT '[]'::jsonb NOT NULL,
    trust_level character varying(20) DEFAULT 'raw'::character varying NOT NULL,
    validation_passed integer,
    validation_total integer,
    quality_score double precision,
    duration_ms integer,
    token_usage jsonb,
    tool_calls_count integer DEFAULT 0,
    approval_requested integer DEFAULT 0,
    error_category character varying(100),
    error_message text,
    execution_started_at timestamp without time zone,
    execution_completed_at timestamp without time zone
);


ALTER TABLE execution_records OWNER TO postgres;

--
-- Name: execution_schedules; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE execution_schedules (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    task_id uuid NOT NULL,
    intent_template jsonb NOT NULL,
    trigger_type character varying(32) NOT NULL,
    trigger_config jsonb NOT NULL,
    last_run_at timestamp without time zone,
    next_run_at timestamp without time zone,
    is_active boolean DEFAULT true NOT NULL
);


ALTER TABLE execution_schedules OWNER TO brsama;

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
-- Name: focus_contracts; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE focus_contracts (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    version integer NOT NULL,
    scenario_pack_id character varying(128) NOT NULL,
    active_node character varying(255) NOT NULL,
    focus_description text NOT NULL,
    desire_hypothesis text,
    commitment_ids jsonb NOT NULL,
    created_at timestamp without time zone NOT NULL,
    created_by character varying(32) NOT NULL,
    trigger_decision_ref character varying(36),
    evidence_refs jsonb NOT NULL,
    projection_policy character varying(64) NOT NULL,
    write_path character varying(64) NOT NULL
);


ALTER TABLE focus_contracts OWNER TO brsama;

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
-- Name: goal_world_graph_snapshots; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE goal_world_graph_snapshots (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    graph_id character varying(128) NOT NULL,
    user_id character varying(128) NOT NULL,
    goal_id character varying(128) NOT NULL,
    goal_type character varying(64) NOT NULL,
    coverage double precision NOT NULL,
    payload jsonb NOT NULL,
    last_saved_at timestamp without time zone NOT NULL,
    metadata jsonb NOT NULL
);


ALTER TABLE goal_world_graph_snapshots OWNER TO brsama;

--
-- Name: goals; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE goals (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    title character varying(255) NOT NULL,
    goal_type character varying(64) DEFAULT 'general'::character varying NOT NULL,
    description text,
    status character varying(32) DEFAULT 'active'::character varying NOT NULL,
    target_date date,
    mastery double precision DEFAULT '0'::double precision,
    progress double precision DEFAULT '0'::double precision,
    priority character varying(16) DEFAULT 'normal'::character varying,
    is_primary boolean DEFAULT false,
    minimum_acceptance_criteria jsonb,
    domain_pack_id character varying(64),
    plan_id uuid,
    source character varying(32),
    source_metadata jsonb,
    completed_at timestamp without time zone,
    archived_at timestamp without time zone,
    metadata jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE goals OWNER TO brsama;

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
    deleted_at timestamp without time zone,
    trust_level groupfiletrustlevel DEFAULT 'member'::groupfiletrustlevel NOT NULL,
    is_knowledge_base boolean DEFAULT false NOT NULL,
    download_count integer DEFAULT 0 NOT NULL,
    citation_count integer DEFAULT 0 NOT NULL,
    rating_count integer DEFAULT 0 NOT NULL,
    rating_total double precision DEFAULT '0'::double precision NOT NULL,
    description character varying(500)
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
-- Name: growth_chronicle_snapshots; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE growth_chronicle_snapshots (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id character varying(128) NOT NULL,
    entry_count integer NOT NULL,
    confirmed_count integer NOT NULL,
    payload jsonb NOT NULL,
    last_saved_at timestamp without time zone NOT NULL,
    metadata jsonb NOT NULL
);


ALTER TABLE growth_chronicle_snapshots OWNER TO brsama;

--
-- Name: idempotency_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE idempotency_keys (
    key character varying(255) NOT NULL,
    user_id uuid NOT NULL,
    response json NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone NOT NULL,
    endpoint character varying(128) DEFAULT ''::character varying NOT NULL,
    response_hash character varying(64) DEFAULT ''::character varying NOT NULL
);


ALTER TABLE idempotency_keys OWNER TO postgres;

--
-- Name: identity_evidence; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE identity_evidence (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    dimension character varying(128) NOT NULL,
    evidence_type character varying(128) NOT NULL,
    description text NOT NULL,
    strength double precision NOT NULL,
    valence character varying(32) NOT NULL,
    source character varying(64) NOT NULL,
    evidence_refs jsonb NOT NULL,
    projection_policy character varying(64) NOT NULL,
    shareability character varying(64) NOT NULL
);


ALTER TABLE identity_evidence OWNER TO brsama;

--
-- Name: idiographic_associations; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE idiographic_associations (
    user_id uuid NOT NULL,
    dim_a character varying(64) NOT NULL,
    dim_b character varying(64) NOT NULL,
    dim_pair character varying(128) NOT NULL,
    direction character varying(24) DEFAULT 'positive_sync'::character varying NOT NULL,
    correlation double precision DEFAULT '0'::double precision NOT NULL,
    p_value_raw double precision DEFAULT '1'::double precision NOT NULL,
    p_value_bh double precision DEFAULT '1'::double precision NOT NULL,
    sample_days integer DEFAULT 0 NOT NULL,
    active_days integer DEFAULT 0 NOT NULL,
    rank_pair_count integer DEFAULT 0 NOT NULL,
    confidence double precision DEFAULT '0'::double precision NOT NULL,
    density_insufficient boolean DEFAULT true NOT NULL,
    visible boolean DEFAULT false NOT NULL,
    path_mode character varying(16) DEFAULT 'B'::character varying NOT NULL,
    window_start date,
    window_end date,
    disclaimer_text character varying(255) DEFAULT ''::character varying NOT NULL,
    rendered_text character varying(2000) DEFAULT ''::character varying NOT NULL,
    user_disconfirmed boolean DEFAULT false NOT NULL,
    user_disconfirmed_until timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE idiographic_associations OWNER TO brsama;

--
-- Name: idiographic_changepoints; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE idiographic_changepoints (
    user_id uuid NOT NULL,
    dim character varying(64) NOT NULL,
    change_date date NOT NULL,
    confidence double precision DEFAULT '0'::double precision NOT NULL,
    path_mode character varying(16) DEFAULT 'B'::character varying NOT NULL,
    rendered_text character varying(1000) DEFAULT ''::character varying NOT NULL,
    window_start date,
    window_end date,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE idiographic_changepoints OWNER TO brsama;

--
-- Name: insight_claims; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE insight_claims (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    claim_type character varying(128) NOT NULL,
    content text NOT NULL,
    source character varying(64) NOT NULL,
    confidence double precision NOT NULL,
    status character varying(32) NOT NULL,
    probed_at timestamp without time zone,
    resolved_at timestamp without time zone,
    evidence_refs jsonb NOT NULL,
    probe_outcome_ids jsonb NOT NULL,
    projection_policy character varying(64) NOT NULL,
    write_path character varying(64) NOT NULL,
    shareability character varying(64) NOT NULL
);


ALTER TABLE insight_claims OWNER TO brsama;

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
-- Name: intervention_outcomes; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE intervention_outcomes (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    plan_id uuid,
    task_id uuid,
    intervention_type character varying(64),
    trigger_reason character varying(128),
    target_concept character varying(256),
    target_node_id uuid,
    triggered_at timestamp without time zone NOT NULL,
    follow_up_at timestamp without time zone,
    outcome_checked_at timestamp without time zone,
    outcome_status character varying(32),
    mastery_before double precision,
    mastery_after double precision,
    effective boolean,
    user_adopted boolean,
    adopted_at timestamp without time zone,
    notes text
);


ALTER TABLE intervention_outcomes OWNER TO brsama;

--
-- Name: intervention_records; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE intervention_records (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    plan_card_id uuid,
    phase_card_id uuid,
    task_occurrence_id uuid,
    knowledge_card_id uuid,
    trigger_type character varying(32) NOT NULL,
    trigger_source_ref character varying(128),
    diagnosis_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    delivery_strategy character varying(24) NOT NULL,
    delivery_channel character varying(24) NOT NULL,
    content_version character varying(64) DEFAULT '''1'''::character varying NOT NULL,
    acceptance_status character varying(24) DEFAULT '''CREATED'''::character varying NOT NULL,
    action_payload jsonb,
    outcome_window_days integer DEFAULT 7 NOT NULL,
    outcome_status character varying(24) DEFAULT '''PENDING'''::character varying NOT NULL,
    evidence_payload jsonb
);


ALTER TABLE intervention_records OWNER TO brsama;

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
-- Name: intervention_strategy_outcomes; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE intervention_strategy_outcomes (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    intervention_id uuid NOT NULL,
    trigger_type intervention_trigger_enum NOT NULL,
    delivery_tone delivery_strategy_enum NOT NULL,
    delivery_channel delivery_channel_enum NOT NULL,
    acceptance_status intervention_acceptance_enum NOT NULL,
    outcome intervention_outcome_enum NOT NULL,
    time_to_action_seconds integer,
    context_snapshot json DEFAULT '{}'::json NOT NULL
);


ALTER TABLE intervention_strategy_outcomes OWNER TO brsama;

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
-- Name: item_similarities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE item_similarities (
    item_id_1 uuid NOT NULL,
    item_type_1 character varying(50) NOT NULL,
    item_id_2 uuid NOT NULL,
    item_type_2 character varying(50) NOT NULL,
    similarity_score double precision NOT NULL,
    common_learners integer DEFAULT 0 NOT NULL,
    last_calculated_at timestamp without time zone NOT NULL,
    meta json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE item_similarities OWNER TO postgres;

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
-- Name: knowledge_node_documents; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE knowledge_node_documents (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    node_id uuid NOT NULL,
    file_id uuid NOT NULL,
    is_primary boolean DEFAULT false NOT NULL
);


ALTER TABLE knowledge_node_documents OWNER TO brsama;

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
    deleted_at timestamp without time zone,
    sector_weights jsonb,
    dominant_sector_code character varying(20) DEFAULT 'VOID'::character varying NOT NULL,
    sector_classification_status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    sector_classification_model character varying(100),
    sector_classified_at timestamp without time zone,
    community_signal json,
    exam_weight double precision DEFAULT '0'::double precision NOT NULL,
    difficulty double precision DEFAULT '0.5'::double precision NOT NULL,
    trainability double precision DEFAULT '0.5'::double precision NOT NULL,
    mistakes integer DEFAULT 0 NOT NULL
);


ALTER TABLE knowledge_nodes OWNER TO postgres;

--
-- Name: leaderboard_snapshots; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE leaderboard_snapshots (
    snapshot_type character varying(50) NOT NULL,
    period character varying(20) NOT NULL,
    subject_id uuid,
    snapshot_date timestamp without time zone NOT NULL,
    snapshot_version integer NOT NULL,
    rankings json NOT NULL,
    total_participants integer NOT NULL,
    generation_time_ms double precision,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE leaderboard_snapshots OWNER TO brsama;

--
-- Name: learning_assets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE learning_assets (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    source_file_id uuid,
    status character varying(20) DEFAULT 'INBOX'::character varying NOT NULL,
    asset_kind character varying(20) DEFAULT 'WORD'::character varying NOT NULL,
    headword character varying(255) NOT NULL,
    definition text,
    translation text,
    example text,
    language_code character varying(10) DEFAULT 'en'::character varying NOT NULL,
    inbox_expires_at timestamp without time zone,
    snapshot_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    snapshot_schema_version integer DEFAULT 1 NOT NULL,
    provenance_json jsonb DEFAULT '{}'::jsonb,
    provenance_updated_at timestamp without time zone,
    selection_fp character varying(64),
    anchor_fp character varying(64),
    doc_fp character varying(64),
    norm_version character varying(20) DEFAULT 'v1'::character varying NOT NULL,
    match_profile character varying(50),
    review_due_at timestamp without time zone,
    review_count integer DEFAULT 0 NOT NULL,
    review_success_rate double precision DEFAULT '0'::double precision NOT NULL,
    last_seen_at timestamp without time zone,
    lookup_count integer DEFAULT 1 NOT NULL,
    star_count integer DEFAULT 0 NOT NULL,
    ignored_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE learning_assets OWNER TO postgres;

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
-- Name: marketplace_packs; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE marketplace_packs (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    pack_id character varying(64) NOT NULL,
    name character varying(160) NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    domain character varying(96) DEFAULT ''::character varying NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    source character varying(128) DEFAULT 'system'::character varying NOT NULL,
    status character varying(32) DEFAULT 'draft'::character varying NOT NULL,
    node_schema jsonb DEFAULT '{}'::jsonb NOT NULL,
    task_templates jsonb DEFAULT '[]'::jsonb NOT NULL,
    risk_rules jsonb DEFAULT '[]'::jsonb NOT NULL,
    skill_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    quality_evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    quality_score double precision DEFAULT '0'::double precision NOT NULL,
    negative_feedback_rate double precision DEFAULT '0'::double precision NOT NULL,
    revoke_rate double precision DEFAULT '0'::double precision NOT NULL,
    adoption_count integer DEFAULT 0 NOT NULL,
    privacy_report jsonb DEFAULT '{}'::jsonb NOT NULL,
    governance jsonb DEFAULT '{}'::jsonb NOT NULL,
    previous_versions jsonb DEFAULT '[]'::jsonb NOT NULL,
    rollback_of_id uuid,
    auto_deprecation_reason character varying(128),
    listed_at timestamp without time zone,
    deprecated_at timestamp without time zone
);


ALTER TABLE marketplace_packs OWNER TO brsama;

--
-- Name: marketplace_skills; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE marketplace_skills (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    skill_id character varying(64) NOT NULL,
    source_skill_id character varying(128),
    name character varying(160) NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    goal_type character varying(64) DEFAULT ''::character varying NOT NULL,
    domain character varying(96) DEFAULT ''::character varying NOT NULL,
    author_id uuid,
    version integer DEFAULT 1 NOT NULL,
    status character varying(32) DEFAULT 'draft'::character varying NOT NULL,
    trigger_condition text DEFAULT ''::text NOT NULL,
    action_template text DEFAULT ''::text NOT NULL,
    expected_outcome text DEFAULT ''::text NOT NULL,
    prerequisites jsonb DEFAULT '[]'::jsonb NOT NULL,
    contraindications jsonb DEFAULT '[]'::jsonb NOT NULL,
    context_signatures jsonb DEFAULT '[]'::jsonb NOT NULL,
    evidence_grade integer DEFAULT 0 NOT NULL,
    evidence_summary text DEFAULT ''::text NOT NULL,
    episode_count integer DEFAULT 0 NOT NULL,
    success_rate double precision DEFAULT '0'::double precision NOT NULL,
    quality_score double precision DEFAULT '0'::double precision NOT NULL,
    negative_feedback_rate double precision DEFAULT '0'::double precision NOT NULL,
    revoke_rate double precision DEFAULT '0'::double precision NOT NULL,
    adoption_count integer DEFAULT 0 NOT NULL,
    privacy_report jsonb DEFAULT '{}'::jsonb NOT NULL,
    governance jsonb DEFAULT '{}'::jsonb NOT NULL,
    previous_versions jsonb DEFAULT '[]'::jsonb NOT NULL,
    rollback_of_id uuid,
    auto_deprecation_reason character varying(128),
    listed_at timestamp without time zone,
    deprecated_at timestamp without time zone
);


ALTER TABLE marketplace_skills OWNER TO brsama;

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
-- Name: north_star_metric_events; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE north_star_metric_events (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    plan_id uuid,
    task_id uuid,
    event_type character varying(64) NOT NULL,
    event_key character varying(160) NOT NULL,
    source character varying(64) NOT NULL,
    metric_date date NOT NULL,
    occurred_at timestamp without time zone NOT NULL,
    value_float double precision,
    numerator integer,
    denominator integer,
    passed boolean,
    payload jsonb NOT NULL
);


ALTER TABLE north_star_metric_events OWNER TO brsama;

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
    updated_at timestamp without time zone NOT NULL,
    disabled_types jsonb NOT NULL
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
-- Name: pack_adoption_history; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE pack_adoption_history (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    adoption_id uuid NOT NULL,
    user_id uuid NOT NULL,
    asset_id character varying(64) NOT NULL,
    asset_type character varying(24) NOT NULL,
    trace_id character varying(128) NOT NULL,
    impact_type character varying(32) NOT NULL,
    impact_summary text DEFAULT ''::text NOT NULL,
    target_id character varying(128),
    before_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    after_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    outcome character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


ALTER TABLE pack_adoption_history OWNER TO brsama;

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
-- Name: persdyn_attractors; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE persdyn_attractors (
    user_id uuid NOT NULL,
    dim character varying(40) NOT NULL,
    baseline double precision DEFAULT '0'::double precision NOT NULL,
    variability double precision DEFAULT '0'::double precision NOT NULL,
    recovery_rate double precision DEFAULT '0'::double precision NOT NULL,
    confidence double precision DEFAULT '0'::double precision NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE persdyn_attractors OWNER TO brsama;

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
-- Name: planning_artifacts; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE planning_artifacts (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    plan_card_id uuid NOT NULL,
    artifact_type character varying(32) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    status character varying(24) DEFAULT '''DRAFT'''::character varying NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    based_on_versions jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_by_agent character varying(64),
    approved_by_user_id uuid,
    approved_at timestamp without time zone,
    superseded_at timestamp without time zone
);


ALTER TABLE planning_artifacts OWNER TO brsama;

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
    source_metadata jsonb,
    goal_id uuid
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
    like_count integer NOT NULL DEFAULT 0,
    comment_count integer NOT NULL DEFAULT 0,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);

-- Indexes for posts table (performance optimization)
CREATE INDEX idx_posts_created_at ON posts (created_at DESC);
CREATE INDEX idx_posts_not_deleted_created ON posts (deleted_at, created_at DESC) WHERE deleted_at IS NULL;

ALTER TABLE posts OWNER TO postgres;

--
-- Name: privacy_budget_ledger; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE privacy_budget_ledger (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    subject_id character varying(128) NOT NULL,
    subject_type character varying(32) NOT NULL,
    query_type character varying(64) NOT NULL,
    epsilon_spent double precision NOT NULL,
    max_epsilon double precision NOT NULL,
    remaining_epsilon double precision NOT NULL,
    window_key character varying(64) NOT NULL,
    allowed boolean NOT NULL,
    denial_reason character varying(128) NOT NULL,
    spent_at timestamp without time zone NOT NULL,
    metadata jsonb NOT NULL
);


ALTER TABLE privacy_budget_ledger OWNER TO brsama;

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
-- Name: probe_outcomes; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE probe_outcomes (
    id uuid NOT NULL,
    claim_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    probe_type character varying(64) NOT NULL,
    probe_content text NOT NULL,
    result character varying(64) NOT NULL,
    evidence text NOT NULL,
    confidence_adjustment double precision NOT NULL,
    evidence_refs jsonb NOT NULL
);


ALTER TABLE probe_outcomes OWNER TO brsama;

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
-- Name: push_delivery_records; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE push_delivery_records (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    notification_id uuid,
    policy_id character varying(64) NOT NULL,
    category character varying(64) NOT NULL,
    message_template_id character varying(128) NOT NULL,
    title character varying(255) NOT NULL,
    body character varying(1000) NOT NULL,
    evidence_token character varying(255) NOT NULL,
    delivery_channel character varying(32) DEFAULT 'websocket'::character varying NOT NULL,
    status character varying(32) DEFAULT 'sent'::character varying NOT NULL,
    scheduled_send_at timestamp without time zone NOT NULL,
    sent_at timestamp without time zone,
    read_at timestamp without time zone,
    dismissed_at timestamp without time zone,
    acted_at timestamp without time zone,
    retracted_at timestamp without time zone,
    retractable_until timestamp without time zone,
    category_disabled boolean DEFAULT false NOT NULL,
    metadata_payload json DEFAULT '{}'::json NOT NULL
);


ALTER TABLE push_delivery_records OWNER TO brsama;

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
-- Name: release_approval_requests; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE release_approval_requests (
    id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    category character varying(64) NOT NULL,
    object_type character varying(64) NOT NULL,
    object_id character varying(128) NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    status character varying(32) DEFAULT 'draft'::character varying NOT NULL,
    requested_by_id uuid,
    submitted_at timestamp without time zone,
    required_approvals integer DEFAULT 1 NOT NULL,
    approvals jsonb DEFAULT '[]'::jsonb NOT NULL,
    rejections jsonb DEFAULT '[]'::jsonb NOT NULL,
    reviewer_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    reviewed_at timestamp without time zone,
    rejection_reason text,
    applied_at timestamp without time zone,
    applied_by_id uuid,
    apply_result jsonb,
    notification_state jsonb DEFAULT '{}'::jsonb NOT NULL,
    needs_admin_attention boolean DEFAULT false NOT NULL,
    CONSTRAINT chk_release_approval_category CHECK (((category)::text = ANY ((ARRAY['policy_publish'::character varying, 'experiment_promote'::character varying, 'skill_systemize'::character varying, 'domain_pack_release'::character varying, 'kill_switch_promote'::character varying, 'high_risk_config'::character varying])::text[]))),
    CONSTRAINT chk_release_approval_required_positive CHECK ((required_approvals >= 1)),
    CONSTRAINT chk_release_approval_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'pending_review'::character varying, 'approved'::character varying, 'rejected'::character varying, 'applied'::character varying])::text[])))
);


ALTER TABLE release_approval_requests OWNER TO brsama;

--
-- Name: report_snapshots; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE report_snapshots (
    report_id character varying(128) NOT NULL,
    user_id uuid NOT NULL,
    snapshot_type character varying(64) NOT NULL,
    cache_version character varying(128),
    delivery_mode character varying(64),
    quality_mode character varying(64),
    trigger_source text,
    payload jsonb NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE report_snapshots OWNER TO brsama;

--
-- Name: research_consent_records; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE research_consent_records (
    user_id character varying(64) NOT NULL,
    protocol_id character varying(64) NOT NULL,
    granted_at timestamp without time zone NOT NULL,
    revoked_at timestamp without time zone,
    scope jsonb NOT NULL,
    evidence jsonb NOT NULL,
    version character varying(32) NOT NULL,
    source character varying(64) NOT NULL,
    grant_reason text,
    grant_initiator character varying(16) NOT NULL,
    grant_ip_hash character varying(64),
    revoke_reason text,
    revoke_initiator character varying(16),
    revoke_ip_hash character varying(64),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE research_consent_records OWNER TO brsama;

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
-- Name: routing_decision_log; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE routing_decision_log (
    decision_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    user_id uuid NOT NULL,
    decided_at timestamp without time zone NOT NULL,
    input_aggregator_snapshot_id character varying(128) NOT NULL,
    sufficiency_judgment_id uuid,
    decision_type character varying(64) NOT NULL,
    decision_payload json DEFAULT '{}'::json NOT NULL,
    outcome_signal_id character varying(128),
    outcome_type character varying(32),
    outcome_collected_at timestamp without time zone,
    skills_injected json,
    source_state_v2 json,
    source_state_v2_key character varying(255),
    outcome character varying(32),
    outcome_timestamp timestamp without time zone,
    idiographic_associations_injected jsonb
);


ALTER TABLE routing_decision_log OWNER TO brsama;

--
-- Name: safe_experiment_episodes; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE safe_experiment_episodes (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    experiment_id uuid NOT NULL,
    experiment_key character varying(64) NOT NULL,
    user_id uuid,
    context_signature jsonb DEFAULT '{}'::jsonb NOT NULL,
    candidate_actions jsonb DEFAULT '[]'::jsonb NOT NULL,
    selected_action character varying(160) NOT NULL,
    selection_reason character varying(160) DEFAULT ''::character varying NOT NULL,
    assignment_mode character varying(32) DEFAULT 'shadow'::character varying NOT NULL,
    risk_level character varying(32) DEFAULT 'low'::character varying NOT NULL,
    reward double precision,
    outcome_vector jsonb DEFAULT '{}'::jsonb NOT NULL,
    guardrail_result jsonb DEFAULT '{}'::jsonb NOT NULL,
    incident_trace jsonb
);


ALTER TABLE safe_experiment_episodes OWNER TO brsama;

--
-- Name: safe_experiments; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE safe_experiments (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    experiment_key character varying(64) NOT NULL,
    name character varying(200) NOT NULL,
    hypothesis text NOT NULL,
    domain character varying(80) NOT NULL,
    status character varying(32) DEFAULT 'draft'::character varying NOT NULL,
    eligible_context jsonb DEFAULT '{}'::jsonb NOT NULL,
    excluded_context jsonb DEFAULT '[]'::jsonb NOT NULL,
    policies jsonb DEFAULT '[]'::jsonb NOT NULL,
    assignment_mode character varying(32) DEFAULT 'shadow'::character varying NOT NULL,
    reward_model jsonb DEFAULT '{}'::jsonb NOT NULL,
    guardrails jsonb DEFAULT '{}'::jsonb NOT NULL,
    min_episodes integer DEFAULT 50 NOT NULL,
    min_distinct_users integer DEFAULT 15 NOT NULL,
    evidence_grade_required integer DEFAULT 3 NOT NULL,
    current_episodes integer DEFAULT 0 NOT NULL,
    distinct_users jsonb DEFAULT '[]'::jsonb NOT NULL,
    outcome_history jsonb DEFAULT '[]'::jsonb NOT NULL,
    rollback_version character varying(80),
    previous_versions jsonb DEFAULT '[]'::jsonb NOT NULL,
    kill_switch_key character varying(120) NOT NULL,
    incident_trace jsonb DEFAULT '[]'::jsonb NOT NULL,
    promotion_candidate jsonb,
    created_by uuid,
    started_at timestamp without time zone,
    paused_at timestamp without time zone,
    concluded_at timestamp without time zone
);


ALTER TABLE safe_experiments OWNER TO brsama;

--
-- Name: saga_instances; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE saga_instances (
    id uuid NOT NULL,
    saga_type text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    current_step integer DEFAULT 0 NOT NULL,
    input_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    step_results jsonb DEFAULT '[]'::jsonb NOT NULL,
    error text DEFAULT ''::text NOT NULL,
    correlation_id text DEFAULT ''::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE saga_instances OWNER TO brsama;

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
-- Name: scenes; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE scenes (
    scene_id character varying(80) NOT NULL,
    user_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    summary character varying(200) NOT NULL,
    member_memory_ids json DEFAULT '[]'::json NOT NULL,
    centroid_embedding vector(1024),
    time_start timestamp without time zone NOT NULL,
    time_end timestamp without time zone NOT NULL,
    quality_score double precision DEFAULT '0'::double precision NOT NULL,
    version character varying(32) DEFAULT 'scene.v1'::character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE scenes OWNER TO brsama;

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
-- Name: seed_library_ratings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE seed_library_ratings (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    user_id uuid NOT NULL,
    library_id uuid NOT NULL,
    score double precision NOT NULL,
    comment text
);


ALTER TABLE seed_library_ratings OWNER TO postgres;

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
-- Name: session_completions; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE session_completions (
    session_id character varying(255) NOT NULL,
    user_id uuid NOT NULL,
    completion_type character varying(64) NOT NULL,
    source_event character varying(64) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE session_completions OWNER TO brsama;

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
    knowledge_node_id uuid,
    seed_library_id uuid,
    seed_item_id uuid,
    card_share_record_id uuid,
    adoption_count integer DEFAULT 0,
    quality_score double precision DEFAULT 0,
    quality_hidden boolean DEFAULT false,
    negative_feedback_count integer DEFAULT 0
);


ALTER TABLE shared_resources OWNER TO postgres;

--
-- Name: shared_skills; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE shared_skills (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    share_slug character varying(80) NOT NULL,
    name character varying(40) NOT NULL,
    pattern_template character varying(4000) NOT NULL,
    activation_conditions json DEFAULT '[]'::json NOT NULL,
    examples json DEFAULT '[]'::json NOT NULL,
    author_label character varying(32) DEFAULT 'anonymous'::character varying NOT NULL,
    published_at timestamp without time zone NOT NULL,
    source_schema_version character varying(16) DEFAULT 'skill.v1'::character varying NOT NULL
);


ALTER TABLE shared_skills OWNER TO brsama;

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
-- Name: simulation_runs; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE simulation_runs (
    session_id character varying(128) NOT NULL,
    user_id uuid NOT NULL,
    scenario_key character varying(64) NOT NULL,
    topic text NOT NULL,
    state character varying(32) NOT NULL,
    payload jsonb NOT NULL,
    insight_summary text,
    last_active_at timestamp without time zone,
    completed_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE simulation_runs OWNER TO brsama;

--
-- Name: skill_share_moderation_queue; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE skill_share_moderation_queue (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    owner_user_id uuid NOT NULL,
    user_skill_id uuid NOT NULL,
    staged_name character varying(40) NOT NULL,
    staged_pattern_template character varying(4000) NOT NULL,
    staged_activation_conditions json DEFAULT '[]'::json NOT NULL,
    staged_examples json DEFAULT '[]'::json NOT NULL,
    pii_scan_reasons json DEFAULT '[]'::json NOT NULL,
    injection_scan_reasons json DEFAULT '[]'::json NOT NULL,
    moderation_status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    reviewer_label character varying(64),
    reviewed_at timestamp without time zone,
    published_shared_skill_id uuid,
    rejection_reason character varying(512)
);


ALTER TABLE skill_share_moderation_queue OWNER TO brsama;

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
-- Name: srl_phase_states; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE srl_phase_states (
    user_id uuid NOT NULL,
    current_phase character varying(32) NOT NULL,
    phase_started_at timestamp without time zone NOT NULL,
    previous_phase character varying(32),
    transition_evidence_ids json NOT NULL,
    confidence double precision NOT NULL,
    source character varying(32) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE srl_phase_states OWNER TO brsama;

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
    deleted_at timestamp without time zone,
    document_quality_score double precision DEFAULT '0'::double precision NOT NULL,
    source_file_id uuid,
    lifecycle_status character varying(32) DEFAULT 'active'::character varying NOT NULL,
    lifecycle_reason character varying(255),
    lifecycle_updated_at timestamp without time zone,
    archived_at timestamp without time zone,
    revoked_at timestamp without time zone,
    orphaned_at timestamp without time zone,
    archive_review_due_at timestamp without time zone,
    erased_at timestamp without time zone,
    erasure_receipt character varying(255),
    CONSTRAINT chk_stored_files_lifecycle_status CHECK (((lifecycle_status)::text = ANY ((ARRAY['active'::character varying, 'archived'::character varying, 'revoked'::character varying, 'orphaned'::character varying])::text[])))
);


ALTER TABLE stored_files OWNER TO postgres;

--
-- Name: strategy_belief_snapshots; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE strategy_belief_snapshots (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id character varying(128) NOT NULL,
    strategy_key character varying(128) NOT NULL,
    alpha double precision DEFAULT '1'::double precision NOT NULL,
    beta double precision DEFAULT '1'::double precision NOT NULL,
    evidence_count integer DEFAULT 0 NOT NULL,
    last_updated character varying(64) DEFAULT ''::character varying NOT NULL,
    counter_evidence jsonb DEFAULT '[]'::jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


ALTER TABLE strategy_belief_snapshots OWNER TO brsama;

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
-- Name: task_documents; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE task_documents (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    task_id uuid NOT NULL,
    file_id uuid NOT NULL,
    linked_by character varying(16) DEFAULT 'user'::character varying NOT NULL,
    source_reason character varying(500),
    fallback_action character varying(500)
);


ALTER TABLE task_documents OWNER TO brsama;

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
-- Name: task_occurrences; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE task_occurrences (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    series_card_id uuid NOT NULL,
    plan_card_id uuid,
    phase_card_id uuid,
    scheduled_for date,
    window_start timestamp without time zone,
    window_end timestamp without time zone,
    occurrence_status character varying(24) DEFAULT '''PLANNED'''::character varying NOT NULL,
    actual_minutes integer,
    completion_quality integer,
    deferral_count integer DEFAULT 0 NOT NULL,
    generated_by_rule_hash character varying(128) DEFAULT ''''''::character varying NOT NULL,
    feedback_payload jsonb,
    completed_at timestamp without time zone
);


ALTER TABLE task_occurrences OWNER TO brsama;

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
    deleted_at timestamp without time zone,
    order_index integer NOT NULL,
    execution_mode character varying(20),
    guide_json jsonb,
    ai_prompt text,
    source_planning_session_id character varying(64),
    phase_index integer,
    success_criteria text,
    paused_at timestamp without time zone,
    paused_reason text
);


ALTER TABLE tasks OWNER TO postgres;

--
-- Name: theater_candidate_bundles; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE theater_candidate_bundles (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    prediction_id character varying(64) NOT NULL,
    topic text NOT NULL,
    target_name character varying(255) NOT NULL,
    target_resolution_mode character varying(32) NOT NULL,
    status character varying(32) DEFAULT 'pending_review'::character varying NOT NULL,
    nodes_payload jsonb NOT NULL,
    edges_payload jsonb NOT NULL,
    semantic_matches jsonb NOT NULL,
    source_metadata jsonb NOT NULL
);


ALTER TABLE theater_candidate_bundles OWNER TO brsama;

--
-- Name: theater_predictions; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE theater_predictions (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    prediction_id character varying(64) NOT NULL,
    user_id uuid NOT NULL,
    topic text NOT NULL,
    target_name character varying(255) NOT NULL,
    target_node_id uuid,
    target_resolution_mode character varying(32) NOT NULL,
    horizon_days integer DEFAULT 14 NOT NULL,
    preview_mode boolean DEFAULT false NOT NULL,
    generated_at timestamp without time zone NOT NULL,
    candidate_bundle_id uuid,
    simulation_session_id character varying(128),
    recommended_route_id character varying(64),
    adopted_plan_id uuid,
    adopted_at timestamp without time zone,
    accuracy_status character varying(32) DEFAULT 'pending_feedback'::character varying NOT NULL,
    accuracy_due_on timestamp without time zone,
    paths jsonb NOT NULL,
    discussion_turns jsonb NOT NULL,
    timeline jsonb NOT NULL,
    selected_prediction jsonb,
    routing_notes jsonb NOT NULL,
    accuracy_tracking jsonb NOT NULL,
    accuracy_summary jsonb
);


ALTER TABLE theater_predictions OWNER TO brsama;

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
    deleted_at timestamp without time zone,
    model_tier character varying(40),
    ai_reasoning_mode character varying(16) DEFAULT 'balanced'::character varying NOT NULL
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
-- Name: transition_decision_records; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE transition_decision_records (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    decision_type character varying(64) NOT NULL,
    proposed_transition character varying(255),
    initiation_type character varying(32) NOT NULL,
    decision_mechanism character varying(32) NOT NULL,
    decision_basis character varying(64) NOT NULL,
    input_snapshot_ref character varying(128) NOT NULL,
    impact_class character varying(32) NOT NULL,
    inference_knobs jsonb,
    capability_gate jsonb,
    interaction_model_variant character varying(64) NOT NULL,
    rollback_anchor jsonb NOT NULL,
    evidence_refs jsonb NOT NULL,
    policy_version character varying(128) NOT NULL,
    confirmed_by_user boolean,
    user_feedback text,
    ux_intent character varying(64) NOT NULL,
    aurora_presence character varying(32) NOT NULL,
    projection_policy character varying(64) NOT NULL
);


ALTER TABLE transition_decision_records OWNER TO brsama;

--
-- Name: unresolved_conflicts; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE unresolved_conflicts (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    conflict_key character varying(64) NOT NULL,
    left_record_id uuid,
    right_record_id uuid,
    left_summary character varying(2000) NOT NULL,
    right_summary character varying(2000) NOT NULL,
    left_lane character varying(40) NOT NULL,
    right_lane character varying(40) NOT NULL,
    left_evidence_token character varying(128),
    right_evidence_token character varying(128),
    left_payload json DEFAULT '{}'::json NOT NULL,
    right_payload json DEFAULT '{}'::json NOT NULL,
    status character varying(32) DEFAULT 'pending_user'::character varying NOT NULL,
    surfaced_at timestamp without time zone NOT NULL,
    resolved_at timestamp without time zone,
    resolution_reason character varying(128),
    selected_side character varying(16)
);


ALTER TABLE unresolved_conflicts OWNER TO brsama;

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
    deleted_at timestamp without time zone,
    context_snapshot jsonb
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
-- Name: user_learning_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_learning_profiles (
    user_id uuid NOT NULL,
    preferred_difficulty double precision,
    preferred_duration_minutes integer,
    preferred_time_of_day character varying(20),
    subject_distribution json,
    total_study_minutes integer DEFAULT 0 NOT NULL,
    total_items_completed integer DEFAULT 0 NOT NULL,
    average_session_duration double precision,
    learning_vector json,
    cluster_id integer,
    last_updated_at timestamp without time zone NOT NULL,
    update_version integer DEFAULT 1 NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_learning_profiles OWNER TO postgres;

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
    deleted_at timestamp without time zone,
    allow_inferred_episodic boolean DEFAULT true NOT NULL
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
    updated_at timestamp without time zone NOT NULL,
    learning_path_snapshot json
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
    deleted_at timestamp without time zone,
    traits_prior jsonb DEFAULT '{}'::jsonb NOT NULL,
    trait_observation_state jsonb DEFAULT '{}'::jsonb NOT NULL,
    traits_coldstart_completed_at timestamp without time zone
);


ALTER TABLE user_preferences_center OWNER TO postgres;

--
-- Name: user_push_opt_in; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE user_push_opt_in (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    enabled boolean DEFAULT false NOT NULL,
    allow_commitment_follow_up boolean DEFAULT false NOT NULL,
    allow_engagement_recovery boolean DEFAULT false NOT NULL,
    quiet_hours_start character varying(5) DEFAULT '22:00'::character varying NOT NULL,
    quiet_hours_end character varying(5) DEFAULT '08:00'::character varying NOT NULL,
    timezone character varying(64) DEFAULT 'Asia/Shanghai'::character varying NOT NULL
);


ALTER TABLE user_push_opt_in OWNER TO brsama;

--
-- Name: user_scenario_states; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE user_scenario_states (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    pack_id character varying(128) NOT NULL,
    current_node character varying(255) NOT NULL,
    current_focus_contract_id uuid NOT NULL,
    current_focus_contract_version integer NOT NULL,
    drift_from_backbone text,
    is_on_backbone boolean NOT NULL,
    overrides jsonb NOT NULL,
    last_signal text,
    last_signal_at timestamp without time zone,
    projection_policy character varying(64) NOT NULL,
    write_path character varying(64) NOT NULL
);


ALTER TABLE user_scenario_states OWNER TO brsama;

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
    deleted_at timestamp without time zone,
    ai_reasoning_mode character varying(16) DEFAULT 'balanced'::character varying NOT NULL,
    current_goal_id character varying(64),
    safe_experiments_opt_out boolean DEFAULT false NOT NULL,
    accessibility_settings jsonb DEFAULT '{}'::jsonb NOT NULL,
    community_intelligence_enabled boolean DEFAULT true NOT NULL
);


ALTER TABLE user_settings OWNER TO postgres;

--
-- Name: user_similarities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_similarities (
    user_id_1 uuid NOT NULL,
    user_id_2 uuid NOT NULL,
    similarity_score double precision NOT NULL,
    common_items_count integer DEFAULT 0 NOT NULL,
    common_subjects json,
    last_calculated_at timestamp without time zone NOT NULL,
    calculation_version integer DEFAULT 1 NOT NULL,
    meta json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_similarities OWNER TO postgres;

--
-- Name: user_skill_adoptions; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE user_skill_adoptions (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    asset_id character varying(64) NOT NULL,
    asset_type character varying(24) NOT NULL,
    asset_version integer DEFAULT 1 NOT NULL,
    status character varying(24) DEFAULT 'active'::character varying NOT NULL,
    explicit_confirm boolean DEFAULT false NOT NULL,
    context_signature jsonb DEFAULT '{}'::jsonb NOT NULL,
    preview_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    trace_id character varying(128),
    revoked_at timestamp without time zone,
    revoked_reason character varying(256)
);


ALTER TABLE user_skill_adoptions OWNER TO brsama;

--
-- Name: user_skills; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE user_skills (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    user_id uuid NOT NULL,
    forked_from_share_id uuid,
    shared_catalog_id uuid,
    name character varying(40) NOT NULL,
    pattern_template character varying(4000) NOT NULL,
    activation_conditions json DEFAULT '[]'::json NOT NULL,
    examples json DEFAULT '[]'::json NOT NULL,
    privacy_level character varying(16) DEFAULT 'private'::character varying NOT NULL,
    usage_count integer DEFAULT 0 NOT NULL,
    last_activated_at timestamp without time zone,
    active boolean DEFAULT true NOT NULL,
    forked_at timestamp without time zone,
    schema_version character varying(16) DEFAULT 'skill.v1'::character varying NOT NULL
);


ALTER TABLE user_skills OWNER TO brsama;

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
    searchable_by searchvisibility DEFAULT 'everyone'::searchvisibility NOT NULL,
    username_hash character varying(64),
    email_hash character varying(64),
    google_id_hash character varying(64),
    apple_id_hash character varying(64),
    wechat_unionid_hash character varying(64)
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
-- Name: window_states; Type: TABLE; Schema: public; Owner: brsama
--

CREATE TABLE window_states (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    global_mode character varying(32) NOT NULL,
    commitment_overrides jsonb NOT NULL,
    set_by character varying(32) NOT NULL,
    trigger_decision_ref character varying(36),
    evidence_refs jsonb NOT NULL,
    projection_policy character varying(64) NOT NULL,
    write_path character varying(64) NOT NULL
);


ALTER TABLE window_states OWNER TO brsama;

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
-- Name: _ag_label_edge; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy._ag_label_edge (
    id ag_catalog.graphid NOT NULL,
    start_id ag_catalog.graphid NOT NULL,
    end_id ag_catalog.graphid NOT NULL,
    properties ag_catalog.agtype DEFAULT ag_catalog.agtype_build_map() NOT NULL
);


ALTER TABLE sparkle_galaxy._ag_label_edge OWNER TO postgres;

--
-- Name: APPLICATION; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy."APPLICATION" (
)
INHERITS (sparkle_galaxy._ag_label_edge);


ALTER TABLE sparkle_galaxy."APPLICATION" OWNER TO postgres;

--
-- Name: APPLICATION_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy."APPLICATION_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy."APPLICATION_id_seq" OWNER TO postgres;

--
-- Name: APPLICATION_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy."APPLICATION_id_seq" OWNED BY sparkle_galaxy."APPLICATION".id;


--
-- Name: APPLIES_TO; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy."APPLIES_TO" (
)
INHERITS (sparkle_galaxy._ag_label_edge);


ALTER TABLE sparkle_galaxy."APPLIES_TO" OWNER TO postgres;

--
-- Name: APPLIES_TO_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy."APPLIES_TO_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy."APPLIES_TO_id_seq" OWNER TO postgres;

--
-- Name: APPLIES_TO_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy."APPLIES_TO_id_seq" OWNED BY sparkle_galaxy."APPLIES_TO".id;


--
-- Name: INTERESTED_IN; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy."INTERESTED_IN" (
)
INHERITS (sparkle_galaxy._ag_label_edge);


ALTER TABLE sparkle_galaxy."INTERESTED_IN" OWNER TO postgres;

--
-- Name: INTERESTED_IN_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy."INTERESTED_IN_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy."INTERESTED_IN_id_seq" OWNER TO postgres;

--
-- Name: INTERESTED_IN_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy."INTERESTED_IN_id_seq" OWNED BY sparkle_galaxy."INTERESTED_IN".id;


--
-- Name: _ag_label_vertex; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy._ag_label_vertex (
    id ag_catalog.graphid NOT NULL,
    properties ag_catalog.agtype DEFAULT ag_catalog.agtype_build_map() NOT NULL
);


ALTER TABLE sparkle_galaxy._ag_label_vertex OWNER TO postgres;

--
-- Name: KnowledgeNode; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy."KnowledgeNode" (
)
INHERITS (sparkle_galaxy._ag_label_vertex);


ALTER TABLE sparkle_galaxy."KnowledgeNode" OWNER TO postgres;

--
-- Name: KnowledgeNode_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy."KnowledgeNode_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy."KnowledgeNode_id_seq" OWNER TO postgres;

--
-- Name: KnowledgeNode_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy."KnowledgeNode_id_seq" OWNED BY sparkle_galaxy."KnowledgeNode".id;


--
-- Name: MASTERED; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy."MASTERED" (
)
INHERITS (sparkle_galaxy._ag_label_edge);


ALTER TABLE sparkle_galaxy."MASTERED" OWNER TO postgres;

--
-- Name: MASTERED_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy."MASTERED_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy."MASTERED_id_seq" OWNER TO postgres;

--
-- Name: MASTERED_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy."MASTERED_id_seq" OWNED BY sparkle_galaxy."MASTERED".id;


--
-- Name: PREREQUISITE; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy."PREREQUISITE" (
)
INHERITS (sparkle_galaxy._ag_label_edge);


ALTER TABLE sparkle_galaxy."PREREQUISITE" OWNER TO postgres;

--
-- Name: PREREQUISITE_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy."PREREQUISITE_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy."PREREQUISITE_id_seq" OWNER TO postgres;

--
-- Name: PREREQUISITE_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy."PREREQUISITE_id_seq" OWNED BY sparkle_galaxy."PREREQUISITE".id;


--
-- Name: RELATED; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy."RELATED" (
)
INHERITS (sparkle_galaxy._ag_label_edge);


ALTER TABLE sparkle_galaxy."RELATED" OWNER TO postgres;

--
-- Name: RELATED_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy."RELATED_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy."RELATED_id_seq" OWNER TO postgres;

--
-- Name: RELATED_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy."RELATED_id_seq" OWNED BY sparkle_galaxy."RELATED".id;


--
-- Name: STUDIED; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy."STUDIED" (
)
INHERITS (sparkle_galaxy._ag_label_edge);


ALTER TABLE sparkle_galaxy."STUDIED" OWNER TO postgres;

--
-- Name: STUDIED_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy."STUDIED_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy."STUDIED_id_seq" OWNER TO postgres;

--
-- Name: STUDIED_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy."STUDIED_id_seq" OWNED BY sparkle_galaxy."STUDIED".id;


--
-- Name: STUDIES; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy."STUDIES" (
)
INHERITS (sparkle_galaxy._ag_label_edge);


ALTER TABLE sparkle_galaxy."STUDIES" OWNER TO postgres;

--
-- Name: STUDIES_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy."STUDIES_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy."STUDIES_id_seq" OWNER TO postgres;

--
-- Name: STUDIES_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy."STUDIES_id_seq" OWNED BY sparkle_galaxy."STUDIES".id;


--
-- Name: User; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy."User" (
)
INHERITS (sparkle_galaxy._ag_label_vertex);


ALTER TABLE sparkle_galaxy."User" OWNER TO postgres;

--
-- Name: User_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy."User_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy."User_id_seq" OWNER TO postgres;

--
-- Name: User_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy."User_id_seq" OWNED BY sparkle_galaxy."User".id;


--
-- Name: __SchemaSeed; Type: TABLE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE TABLE sparkle_galaxy."__SchemaSeed" (
)
INHERITS (sparkle_galaxy._ag_label_vertex);


ALTER TABLE sparkle_galaxy."__SchemaSeed" OWNER TO postgres;

--
-- Name: __SchemaSeed_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy."__SchemaSeed_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy."__SchemaSeed_id_seq" OWNER TO postgres;

--
-- Name: __SchemaSeed_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy."__SchemaSeed_id_seq" OWNED BY sparkle_galaxy."__SchemaSeed".id;


--
-- Name: _ag_label_edge_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy._ag_label_edge_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy._ag_label_edge_id_seq OWNER TO postgres;

--
-- Name: _ag_label_edge_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy._ag_label_edge_id_seq OWNED BY sparkle_galaxy._ag_label_edge.id;


--
-- Name: _ag_label_vertex_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy._ag_label_vertex_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 281474976710655
    CACHE 1;


ALTER SEQUENCE sparkle_galaxy._ag_label_vertex_id_seq OWNER TO postgres;

--
-- Name: _ag_label_vertex_id_seq; Type: SEQUENCE OWNED BY; Schema: sparkle_galaxy; Owner: postgres
--

ALTER SEQUENCE sparkle_galaxy._ag_label_vertex_id_seq OWNED BY sparkle_galaxy._ag_label_vertex.id;


--
-- Name: _label_id_seq; Type: SEQUENCE; Schema: sparkle_galaxy; Owner: postgres
--

CREATE SEQUENCE sparkle_galaxy._label_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 65535
    CACHE 1
    CYCLE;


ALTER SEQUENCE sparkle_galaxy._label_id_seq OWNER TO postgres;

--
-- Name: agent_execution_stats id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY agent_execution_stats ALTER COLUMN id SET DEFAULT nextval('agent_execution_stats_id_seq'::regclass);


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
-- Name: APPLICATION id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."APPLICATION" ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, 'APPLICATION'::name))::integer, nextval('sparkle_galaxy."APPLICATION_id_seq"'::regclass));


--
-- Name: APPLICATION properties; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."APPLICATION" ALTER COLUMN properties SET DEFAULT ag_catalog.agtype_build_map();


--
-- Name: APPLIES_TO id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."APPLIES_TO" ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, 'APPLIES_TO'::name))::integer, nextval('sparkle_galaxy."APPLIES_TO_id_seq"'::regclass));


--
-- Name: APPLIES_TO properties; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."APPLIES_TO" ALTER COLUMN properties SET DEFAULT ag_catalog.agtype_build_map();


--
-- Name: INTERESTED_IN id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."INTERESTED_IN" ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, 'INTERESTED_IN'::name))::integer, nextval('sparkle_galaxy."INTERESTED_IN_id_seq"'::regclass));


--
-- Name: INTERESTED_IN properties; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."INTERESTED_IN" ALTER COLUMN properties SET DEFAULT ag_catalog.agtype_build_map();


--
-- Name: KnowledgeNode id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."KnowledgeNode" ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, 'KnowledgeNode'::name))::integer, nextval('sparkle_galaxy."KnowledgeNode_id_seq"'::regclass));


--
-- Name: KnowledgeNode properties; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."KnowledgeNode" ALTER COLUMN properties SET DEFAULT ag_catalog.agtype_build_map();


--
-- Name: MASTERED id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."MASTERED" ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, 'MASTERED'::name))::integer, nextval('sparkle_galaxy."MASTERED_id_seq"'::regclass));


--
-- Name: MASTERED properties; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."MASTERED" ALTER COLUMN properties SET DEFAULT ag_catalog.agtype_build_map();


--
-- Name: PREREQUISITE id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."PREREQUISITE" ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, 'PREREQUISITE'::name))::integer, nextval('sparkle_galaxy."PREREQUISITE_id_seq"'::regclass));


--
-- Name: PREREQUISITE properties; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."PREREQUISITE" ALTER COLUMN properties SET DEFAULT ag_catalog.agtype_build_map();


--
-- Name: RELATED id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."RELATED" ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, 'RELATED'::name))::integer, nextval('sparkle_galaxy."RELATED_id_seq"'::regclass));


--
-- Name: RELATED properties; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."RELATED" ALTER COLUMN properties SET DEFAULT ag_catalog.agtype_build_map();


--
-- Name: STUDIED id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."STUDIED" ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, 'STUDIED'::name))::integer, nextval('sparkle_galaxy."STUDIED_id_seq"'::regclass));


--
-- Name: STUDIED properties; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."STUDIED" ALTER COLUMN properties SET DEFAULT ag_catalog.agtype_build_map();


--
-- Name: STUDIES id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."STUDIES" ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, 'STUDIES'::name))::integer, nextval('sparkle_galaxy."STUDIES_id_seq"'::regclass));


--
-- Name: STUDIES properties; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."STUDIES" ALTER COLUMN properties SET DEFAULT ag_catalog.agtype_build_map();


--
-- Name: User id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."User" ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, 'User'::name))::integer, nextval('sparkle_galaxy."User_id_seq"'::regclass));


--
-- Name: User properties; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."User" ALTER COLUMN properties SET DEFAULT ag_catalog.agtype_build_map();


--
-- Name: __SchemaSeed id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."__SchemaSeed" ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, '__SchemaSeed'::name))::integer, nextval('sparkle_galaxy."__SchemaSeed_id_seq"'::regclass));


--
-- Name: __SchemaSeed properties; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy."__SchemaSeed" ALTER COLUMN properties SET DEFAULT ag_catalog.agtype_build_map();


--
-- Name: _ag_label_edge id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy._ag_label_edge ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, '_ag_label_edge'::name))::integer, nextval('sparkle_galaxy._ag_label_edge_id_seq'::regclass));


--
-- Name: _ag_label_vertex id; Type: DEFAULT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy._ag_label_vertex ALTER COLUMN id SET DEFAULT ag_catalog._graphid((ag_catalog._label_id('sparkle_galaxy'::name, '_ag_label_vertex'::name))::integer, nextval('sparkle_galaxy._ag_label_vertex_id_seq'::regclass));


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
-- Name: accountability_checkin accountability_checkin_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY accountability_checkin
    ADD CONSTRAINT accountability_checkin_pkey PRIMARY KEY (id);


--
-- Name: accountability_partnership accountability_partnership_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY accountability_partnership
    ADD CONSTRAINT accountability_partnership_pkey PRIMARY KEY (id);


--
-- Name: accountability_policies accountability_policies_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY accountability_policies
    ADD CONSTRAINT accountability_policies_pkey PRIMARY KEY (id);


--
-- Name: accountability_policies accountability_policies_policy_id_key; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY accountability_policies
    ADD CONSTRAINT accountability_policies_policy_id_key UNIQUE (policy_id);


--
-- Name: achievements achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY achievements
    ADD CONSTRAINT achievements_pkey PRIMARY KEY (id);


--
-- Name: admin_audit_log admin_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY admin_audit_log
    ADD CONSTRAINT admin_audit_log_pkey PRIMARY KEY (id);


--
-- Name: agent_execution_stats agent_execution_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY agent_execution_stats
    ADD CONSTRAINT agent_execution_stats_pkey PRIMARY KEY (id);


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
-- Name: asset_suggestion_logs asset_suggestion_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY asset_suggestion_logs
    ADD CONSTRAINT asset_suggestion_logs_pkey PRIMARY KEY (id);


--
-- Name: aurora_core_session_snapshots aurora_core_session_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_core_session_snapshots
    ADD CONSTRAINT aurora_core_session_snapshots_pkey PRIMARY KEY (id);


--
-- Name: aurora_decision_telemetry aurora_decision_telemetry_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_decision_telemetry
    ADD CONSTRAINT aurora_decision_telemetry_pkey PRIMARY KEY (id);


--
-- Name: aurora_judgment_records aurora_judgment_records_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_judgment_records
    ADD CONSTRAINT aurora_judgment_records_pkey PRIMARY KEY (id);


--
-- Name: aurora_policy_versions aurora_policy_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_policy_versions
    ADD CONSTRAINT aurora_policy_versions_pkey PRIMARY KEY (id);


--
-- Name: aurora_scheduled_wakes aurora_scheduled_wakes_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_scheduled_wakes
    ADD CONSTRAINT aurora_scheduled_wakes_pkey PRIMARY KEY (id);


--
-- Name: aurora_state_snapshots aurora_state_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_state_snapshots
    ADD CONSTRAINT aurora_state_snapshots_pkey PRIMARY KEY (id);


--
-- Name: auth_audit_log auth_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY auth_audit_log
    ADD CONSTRAINT auth_audit_log_pkey PRIMARY KEY (id);


--
-- Name: background_tasks background_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY background_tasks
    ADD CONSTRAINT background_tasks_pkey PRIMARY KEY (id);


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
-- Name: candidate_action_feedback candidate_action_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY candidate_action_feedback
    ADD CONSTRAINT candidate_action_feedback_pkey PRIMARY KEY (id);


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
-- Name: card_adoption_records card_adoption_records_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_adoption_records
    ADD CONSTRAINT card_adoption_records_pkey PRIMARY KEY (id);


--
-- Name: card_edges card_edges_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_edges
    ADD CONSTRAINT card_edges_pkey PRIMARY KEY (id);


--
-- Name: card_share_records card_share_records_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_share_records
    ADD CONSTRAINT card_share_records_pkey PRIMARY KEY (id);


--
-- Name: card_snapshots card_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_snapshots
    ADD CONSTRAINT card_snapshots_pkey PRIMARY KEY (id);


--
-- Name: cards cards_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY cards
    ADD CONSTRAINT cards_pkey PRIMARY KEY (id);


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
-- Name: shop_purchases chk_shop_purchases_balance_after_non_negative; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE shop_purchases
    ADD CONSTRAINT chk_shop_purchases_balance_after_non_negative CHECK ((photon_balance_after >= 0)) NOT VALID;


--
-- Name: shop_purchases chk_shop_purchases_balance_before_non_negative; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE shop_purchases
    ADD CONSTRAINT chk_shop_purchases_balance_before_non_negative CHECK ((photon_balance_before >= 0)) NOT VALID;


--
-- Name: shop_purchases chk_shop_purchases_price_paid_non_negative; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE shop_purchases
    ADD CONSTRAINT chk_shop_purchases_price_paid_non_negative CHECK ((price_paid >= 0)) NOT VALID;


--
-- Name: tasks chk_tasks_actual_minutes_non_negative; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE tasks
    ADD CONSTRAINT chk_tasks_actual_minutes_non_negative CHECK (((actual_minutes IS NULL) OR (actual_minutes >= 0))) NOT VALID;


--
-- Name: tasks chk_tasks_difficulty_range; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE tasks
    ADD CONSTRAINT chk_tasks_difficulty_range CHECK (((difficulty >= 1) AND (difficulty <= 5))) NOT VALID;


--
-- Name: tasks chk_tasks_energy_cost_range; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE tasks
    ADD CONSTRAINT chk_tasks_energy_cost_range CHECK (((energy_cost >= 1) AND (energy_cost <= 5))) NOT VALID;


--
-- Name: tasks chk_tasks_estimated_minutes_non_negative; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE tasks
    ADD CONSTRAINT chk_tasks_estimated_minutes_non_negative CHECK ((estimated_minutes >= 0)) NOT VALID;


--
-- Name: tasks chk_tasks_subtask_counts_non_negative; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE tasks
    ADD CONSTRAINT chk_tasks_subtask_counts_non_negative CHECK (((subtasks_total >= 0) AND (subtasks_completed >= 0))) NOT VALID;


--
-- Name: tasks chk_tasks_subtasks_completed_lte_total; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE tasks
    ADD CONSTRAINT chk_tasks_subtasks_completed_lte_total CHECK ((subtasks_completed <= subtasks_total)) NOT VALID;


--
-- Name: users chk_users_curiosity_preference_range; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE users
    ADD CONSTRAINT chk_users_curiosity_preference_range CHECK (((curiosity_preference >= (0)::double precision) AND (curiosity_preference <= (1)::double precision))) NOT VALID;


--
-- Name: users chk_users_depth_preference_range; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE users
    ADD CONSTRAINT chk_users_depth_preference_range CHECK (((depth_preference >= (0)::double precision) AND (depth_preference <= (1)::double precision))) NOT VALID;


--
-- Name: users chk_users_flame_brightness_range; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE users
    ADD CONSTRAINT chk_users_flame_brightness_range CHECK (((flame_brightness >= (0)::double precision) AND (flame_brightness <= (1)::double precision))) NOT VALID;


--
-- Name: users chk_users_flame_level_range; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE users
    ADD CONSTRAINT chk_users_flame_level_range CHECK (((flame_level >= 0) AND (flame_level <= 100))) NOT VALID;


--
-- Name: users chk_users_photon_balance_non_negative; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE users
    ADD CONSTRAINT chk_users_photon_balance_non_negative CHECK ((photon_balance >= 0)) NOT VALID;


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
-- Name: commitments commitments_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY commitments
    ADD CONSTRAINT commitments_pkey PRIMARY KEY (id);


--
-- Name: community_aggregate_signals community_aggregate_signals_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY community_aggregate_signals
    ADD CONSTRAINT community_aggregate_signals_pkey PRIMARY KEY (id);


--
-- Name: compliance_check_logs compliance_check_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY compliance_check_logs
    ADD CONSTRAINT compliance_check_logs_pkey PRIMARY KEY (id);


--
-- Name: conflict_resolution_records conflict_resolution_records_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY conflict_resolution_records
    ADD CONSTRAINT conflict_resolution_records_pkey PRIMARY KEY (id);


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
-- Name: counterfactual_evaluation_reports counterfactual_evaluation_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY counterfactual_evaluation_reports
    ADD CONSTRAINT counterfactual_evaluation_reports_pkey PRIMARY KEY (id);


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
-- Name: custom_expert_profiles custom_expert_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY custom_expert_profiles
    ADD CONSTRAINT custom_expert_profiles_pkey PRIMARY KEY (id);


--
-- Name: custom_expert_teams custom_expert_teams_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY custom_expert_teams
    ADD CONSTRAINT custom_expert_teams_pkey PRIMARY KEY (id);


--
-- Name: daily_behavior_vector daily_behavior_vector_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY daily_behavior_vector
    ADD CONSTRAINT daily_behavior_vector_pkey PRIMARY KEY (id);


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
-- Name: distilled_strategy_cache distilled_strategy_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY distilled_strategy_cache
    ADD CONSTRAINT distilled_strategy_cache_pkey PRIMARY KEY (id);


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
-- Name: document_retrieval_feedback document_retrieval_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY document_retrieval_feedback
    ADD CONSTRAINT document_retrieval_feedback_pkey PRIMARY KEY (id);


--
-- Name: durable_session_state_snapshots durable_session_state_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY durable_session_state_snapshots
    ADD CONSTRAINT durable_session_state_snapshots_pkey PRIMARY KEY (id);


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
-- Name: event_bus_dlq event_bus_dlq_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY event_bus_dlq
    ADD CONSTRAINT event_bus_dlq_pkey PRIMARY KEY (id);


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
-- Name: execution_audit_log execution_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY execution_audit_log
    ADD CONSTRAINT execution_audit_log_pkey PRIMARY KEY (id);


--
-- Name: execution_intents execution_intents_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY execution_intents
    ADD CONSTRAINT execution_intents_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: execution_intents execution_intents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY execution_intents
    ADD CONSTRAINT execution_intents_pkey PRIMARY KEY (id);


--
-- Name: execution_records execution_records_execution_intent_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY execution_records
    ADD CONSTRAINT execution_records_execution_intent_id_key UNIQUE (execution_intent_id);


--
-- Name: execution_records execution_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY execution_records
    ADD CONSTRAINT execution_records_pkey PRIMARY KEY (id);


--
-- Name: execution_schedules execution_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY execution_schedules
    ADD CONSTRAINT execution_schedules_pkey PRIMARY KEY (id);


--
-- Name: expansion_feedback expansion_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY expansion_feedback
    ADD CONSTRAINT expansion_feedback_pkey PRIMARY KEY (id);


--
-- Name: focus_contracts focus_contracts_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY focus_contracts
    ADD CONSTRAINT focus_contracts_pkey PRIMARY KEY (id);


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
-- Name: goal_world_graph_snapshots goal_world_graph_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY goal_world_graph_snapshots
    ADD CONSTRAINT goal_world_graph_snapshots_pkey PRIMARY KEY (id);


--
-- Name: goals goals_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY goals
    ADD CONSTRAINT goals_pkey PRIMARY KEY (id);


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
-- Name: growth_chronicle_snapshots growth_chronicle_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY growth_chronicle_snapshots
    ADD CONSTRAINT growth_chronicle_snapshots_pkey PRIMARY KEY (id);


--
-- Name: idempotency_keys idempotency_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY idempotency_keys
    ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (key);


--
-- Name: identity_evidence identity_evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY identity_evidence
    ADD CONSTRAINT identity_evidence_pkey PRIMARY KEY (id);


--
-- Name: idiographic_associations idiographic_associations_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY idiographic_associations
    ADD CONSTRAINT idiographic_associations_pkey PRIMARY KEY (id);


--
-- Name: idiographic_changepoints idiographic_changepoints_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY idiographic_changepoints
    ADD CONSTRAINT idiographic_changepoints_pkey PRIMARY KEY (id);


--
-- Name: insight_claims insight_claims_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY insight_claims
    ADD CONSTRAINT insight_claims_pkey PRIMARY KEY (id);


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
-- Name: intervention_outcomes intervention_outcomes_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY intervention_outcomes
    ADD CONSTRAINT intervention_outcomes_pkey PRIMARY KEY (id);


--
-- Name: intervention_records intervention_records_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY intervention_records
    ADD CONSTRAINT intervention_records_pkey PRIMARY KEY (id);


--
-- Name: intervention_requests intervention_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_requests
    ADD CONSTRAINT intervention_requests_pkey PRIMARY KEY (id);


--
-- Name: intervention_strategy_outcomes intervention_strategy_outcomes_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY intervention_strategy_outcomes
    ADD CONSTRAINT intervention_strategy_outcomes_pkey PRIMARY KEY (id);


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
-- Name: item_similarities item_similarities_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY item_similarities
    ADD CONSTRAINT item_similarities_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: knowledge_node_documents knowledge_node_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY knowledge_node_documents
    ADD CONSTRAINT knowledge_node_documents_pkey PRIMARY KEY (id);


--
-- Name: knowledge_nodes knowledge_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY knowledge_nodes
    ADD CONSTRAINT knowledge_nodes_pkey PRIMARY KEY (id);


--
-- Name: leaderboard_snapshots leaderboard_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY leaderboard_snapshots
    ADD CONSTRAINT leaderboard_snapshots_pkey PRIMARY KEY (id);


--
-- Name: learning_assets learning_assets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY learning_assets
    ADD CONSTRAINT learning_assets_pkey PRIMARY KEY (id);


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
-- Name: marketplace_packs marketplace_packs_pack_id_key; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY marketplace_packs
    ADD CONSTRAINT marketplace_packs_pack_id_key UNIQUE (pack_id);


--
-- Name: marketplace_packs marketplace_packs_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY marketplace_packs
    ADD CONSTRAINT marketplace_packs_pkey PRIMARY KEY (id);


--
-- Name: marketplace_skills marketplace_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY marketplace_skills
    ADD CONSTRAINT marketplace_skills_pkey PRIMARY KEY (id);


--
-- Name: marketplace_skills marketplace_skills_skill_id_key; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY marketplace_skills
    ADD CONSTRAINT marketplace_skills_skill_id_key UNIQUE (skill_id);


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
-- Name: north_star_metric_events north_star_metric_events_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY north_star_metric_events
    ADD CONSTRAINT north_star_metric_events_pkey PRIMARY KEY (id);


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
-- Name: pack_adoption_history pack_adoption_history_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY pack_adoption_history
    ADD CONSTRAINT pack_adoption_history_pkey PRIMARY KEY (id);


--
-- Name: passive_signals passive_signals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY passive_signals
    ADD CONSTRAINT passive_signals_pkey PRIMARY KEY (id);


--
-- Name: persdyn_attractors persdyn_attractors_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY persdyn_attractors
    ADD CONSTRAINT persdyn_attractors_pkey PRIMARY KEY (id);


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
-- Name: planning_artifacts planning_artifacts_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY planning_artifacts
    ADD CONSTRAINT planning_artifacts_pkey PRIMARY KEY (id);


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
-- Name: privacy_budget_ledger privacy_budget_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY privacy_budget_ledger
    ADD CONSTRAINT privacy_budget_ledger_pkey PRIMARY KEY (id);


--
-- Name: private_messages private_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY private_messages
    ADD CONSTRAINT private_messages_pkey PRIMARY KEY (id);


--
-- Name: probe_outcomes probe_outcomes_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY probe_outcomes
    ADD CONSTRAINT probe_outcomes_pkey PRIMARY KEY (id);


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
-- Name: push_delivery_records push_delivery_records_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY push_delivery_records
    ADD CONSTRAINT push_delivery_records_pkey PRIMARY KEY (id);


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
-- Name: release_approval_requests release_approval_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY release_approval_requests
    ADD CONSTRAINT release_approval_requests_pkey PRIMARY KEY (id);


--
-- Name: report_snapshots report_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY report_snapshots
    ADD CONSTRAINT report_snapshots_pkey PRIMARY KEY (id);


--
-- Name: research_consent_records research_consent_records_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY research_consent_records
    ADD CONSTRAINT research_consent_records_pkey PRIMARY KEY (id);


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
-- Name: routing_decision_log routing_decision_log_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY routing_decision_log
    ADD CONSTRAINT routing_decision_log_pkey PRIMARY KEY (decision_id);


--
-- Name: safe_experiment_episodes safe_experiment_episodes_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY safe_experiment_episodes
    ADD CONSTRAINT safe_experiment_episodes_pkey PRIMARY KEY (id);


--
-- Name: safe_experiments safe_experiments_experiment_key_key; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY safe_experiments
    ADD CONSTRAINT safe_experiments_experiment_key_key UNIQUE (experiment_key);


--
-- Name: safe_experiments safe_experiments_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY safe_experiments
    ADD CONSTRAINT safe_experiments_pkey PRIMARY KEY (id);


--
-- Name: saga_instances saga_instances_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY saga_instances
    ADD CONSTRAINT saga_instances_pkey PRIMARY KEY (id);


--
-- Name: scaffolding_states scaffolding_states_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY scaffolding_states
    ADD CONSTRAINT scaffolding_states_pkey PRIMARY KEY (id);


--
-- Name: scenes scenes_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY scenes
    ADD CONSTRAINT scenes_pkey PRIMARY KEY (id);


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
-- Name: seed_library_ratings seed_library_ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY seed_library_ratings
    ADD CONSTRAINT seed_library_ratings_pkey PRIMARY KEY (id);


--
-- Name: semantic_links semantic_links_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY semantic_links
    ADD CONSTRAINT semantic_links_pkey PRIMARY KEY (id);


--
-- Name: session_completions session_completions_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY session_completions
    ADD CONSTRAINT session_completions_pkey PRIMARY KEY (session_id);


--
-- Name: shared_resources shared_resources_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT shared_resources_pkey PRIMARY KEY (id);


--
-- Name: shared_skills shared_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY shared_skills
    ADD CONSTRAINT shared_skills_pkey PRIMARY KEY (id);


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
-- Name: simulation_runs simulation_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY simulation_runs
    ADD CONSTRAINT simulation_runs_pkey PRIMARY KEY (id);


--
-- Name: skill_share_moderation_queue skill_share_moderation_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY skill_share_moderation_queue
    ADD CONSTRAINT skill_share_moderation_queue_pkey PRIMARY KEY (id);


--
-- Name: spark_contracts spark_contracts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY spark_contracts
    ADD CONSTRAINT spark_contracts_pkey PRIMARY KEY (user_id, id);


--
-- Name: srl_phase_states srl_phase_states_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY srl_phase_states
    ADD CONSTRAINT srl_phase_states_pkey PRIMARY KEY (id);


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
-- Name: strategy_belief_snapshots strategy_belief_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY strategy_belief_snapshots
    ADD CONSTRAINT strategy_belief_snapshots_pkey PRIMARY KEY (id);


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
-- Name: task_documents task_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY task_documents
    ADD CONSTRAINT task_documents_pkey PRIMARY KEY (id);


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
-- Name: task_occurrences task_occurrences_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY task_occurrences
    ADD CONSTRAINT task_occurrences_pkey PRIMARY KEY (id);


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
-- Name: theater_candidate_bundles theater_candidate_bundles_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY theater_candidate_bundles
    ADD CONSTRAINT theater_candidate_bundles_pkey PRIMARY KEY (id);


--
-- Name: theater_predictions theater_predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY theater_predictions
    ADD CONSTRAINT theater_predictions_pkey PRIMARY KEY (id);


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
-- Name: transition_decision_records transition_decision_records_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY transition_decision_records
    ADD CONSTRAINT transition_decision_records_pkey PRIMARY KEY (id);


--
-- Name: unresolved_conflicts unresolved_conflicts_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY unresolved_conflicts
    ADD CONSTRAINT unresolved_conflicts_pkey PRIMARY KEY (id);


--
-- Name: accountability_partnership uq_accountability_partnership_pair; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY accountability_partnership
    ADD CONSTRAINT uq_accountability_partnership_pair UNIQUE (initiator_id, partner_id);


--
-- Name: planning_artifacts uq_artifact_version; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY planning_artifacts
    ADD CONSTRAINT uq_artifact_version UNIQUE (plan_card_id, artifact_type, version);


--
-- Name: aurora_core_session_snapshots uq_aurora_core_session_snapshots_resume_token_hash; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_core_session_snapshots
    ADD CONSTRAINT uq_aurora_core_session_snapshots_resume_token_hash UNIQUE (resume_token_hash);


--
-- Name: aurora_core_session_snapshots uq_aurora_core_session_snapshots_session_id; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_core_session_snapshots
    ADD CONSTRAINT uq_aurora_core_session_snapshots_session_id UNIQUE (session_id);


--
-- Name: capsule_favorites uq_capsule_favorite; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY capsule_favorites
    ADD CONSTRAINT uq_capsule_favorite UNIQUE (user_id, capsule_id);


--
-- Name: card_edges uq_card_edge_unique; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_edges
    ADD CONSTRAINT uq_card_edge_unique UNIQUE (from_card_id, to_card_id, edge_type);


--
-- Name: collaborative_galaxies uq_collaborative_galaxies_group_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY collaborative_galaxies
    ADD CONSTRAINT uq_collaborative_galaxies_group_id UNIQUE (group_id);


--
-- Name: community_aggregate_signals uq_community_aggregate_signal_id; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY community_aggregate_signals
    ADD CONSTRAINT uq_community_aggregate_signal_id UNIQUE (signal_id);


--
-- Name: durable_session_state_snapshots uq_durable_session_state_snapshots_session_id; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY durable_session_state_snapshots
    ADD CONSTRAINT uq_durable_session_state_snapshots_session_id UNIQUE (session_id);


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
-- Name: growth_chronicle_snapshots uq_growth_chronicle_snapshots_user_id; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY growth_chronicle_snapshots
    ADD CONSTRAINT uq_growth_chronicle_snapshots_user_id UNIQUE (user_id);


--
-- Name: intervention_feedback uq_intervention_feedback_idempotency; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_feedback
    ADD CONSTRAINT uq_intervention_feedback_idempotency UNIQUE (user_id, request_id, feedback_type, idempotency_key);


--
-- Name: item_similarities uq_item_similarity_pair; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY item_similarities
    ADD CONSTRAINT uq_item_similarity_pair UNIQUE (item_id_1, item_type_1, item_id_2, item_type_2);


--
-- Name: knowledge_node_documents uq_knowledge_node_documents_user_node_file; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY knowledge_node_documents
    ADD CONSTRAINT uq_knowledge_node_documents_user_node_file UNIQUE (user_id, node_id, file_id);


--
-- Name: north_star_metric_events uq_north_star_metric_events_event_key; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY north_star_metric_events
    ADD CONSTRAINT uq_north_star_metric_events_event_key UNIQUE (event_key);


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
-- Name: scenes uq_scenes_scene_id; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY scenes
    ADD CONSTRAINT uq_scenes_scene_id UNIQUE (scene_id);


--
-- Name: seed_library_ratings uq_seed_library_ratings_user_library; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY seed_library_ratings
    ADD CONSTRAINT uq_seed_library_ratings_user_library UNIQUE (user_id, library_id);


--
-- Name: strategy_belief_snapshots uq_strategy_belief_snapshots_user_strategy; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY strategy_belief_snapshots
    ADD CONSTRAINT uq_strategy_belief_snapshots_user_strategy UNIQUE (user_id, strategy_key);


--
-- Name: intervention_strategy_outcomes uq_strategy_outcome_intervention; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY intervention_strategy_outcomes
    ADD CONSTRAINT uq_strategy_outcome_intervention UNIQUE (intervention_id);


--
-- Name: group_task_claims uq_task_claim; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_task_claims
    ADD CONSTRAINT uq_task_claim UNIQUE (group_task_id, user_id);


--
-- Name: task_documents uq_task_documents_task_file; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY task_documents
    ADD CONSTRAINT uq_task_documents_task_file UNIQUE (task_id, file_id);


--
-- Name: theater_candidate_bundles uq_theater_candidate_bundles_prediction_id; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY theater_candidate_bundles
    ADD CONSTRAINT uq_theater_candidate_bundles_prediction_id UNIQUE (prediction_id);


--
-- Name: theater_predictions uq_theater_predictions_prediction_id; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY theater_predictions
    ADD CONSTRAINT uq_theater_predictions_prediction_id UNIQUE (prediction_id);


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
-- Name: user_learning_profiles uq_user_learning_profile; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_learning_profiles
    ADD CONSTRAINT uq_user_learning_profile UNIQUE (user_id);


--
-- Name: user_skill_adoptions uq_user_marketplace_asset_adoption; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY user_skill_adoptions
    ADD CONSTRAINT uq_user_marketplace_asset_adoption UNIQUE (user_id, asset_type, asset_id);


--
-- Name: user_similarities uq_user_similarity_pair; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_similarities
    ADD CONSTRAINT uq_user_similarity_pair UNIQUE (user_id_1, user_id_2);


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
-- Name: user_learning_profiles user_learning_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_learning_profiles
    ADD CONSTRAINT user_learning_profiles_pkey PRIMARY KEY (id);


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
-- Name: user_push_opt_in user_push_opt_in_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY user_push_opt_in
    ADD CONSTRAINT user_push_opt_in_pkey PRIMARY KEY (id);


--
-- Name: user_push_opt_in user_push_opt_in_user_id_key; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY user_push_opt_in
    ADD CONSTRAINT user_push_opt_in_user_id_key UNIQUE (user_id);


--
-- Name: user_scenario_states user_scenario_states_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY user_scenario_states
    ADD CONSTRAINT user_scenario_states_pkey PRIMARY KEY (id);


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
-- Name: user_similarities user_similarities_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_similarities
    ADD CONSTRAINT user_similarities_pkey PRIMARY KEY (id);


--
-- Name: user_skill_adoptions user_skill_adoptions_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY user_skill_adoptions
    ADD CONSTRAINT user_skill_adoptions_pkey PRIMARY KEY (id);


--
-- Name: user_skills user_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY user_skills
    ADD CONSTRAINT user_skills_pkey PRIMARY KEY (id);


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
-- Name: window_states window_states_pkey; Type: CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY window_states
    ADD CONSTRAINT window_states_pkey PRIMARY KEY (id);


--
-- Name: word_books word_books_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY word_books
    ADD CONSTRAINT word_books_pkey PRIMARY KEY (id);


--
-- Name: _ag_label_edge _ag_label_edge_pkey; Type: CONSTRAINT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy._ag_label_edge
    ADD CONSTRAINT _ag_label_edge_pkey PRIMARY KEY (id);


--
-- Name: _ag_label_vertex _ag_label_vertex_pkey; Type: CONSTRAINT; Schema: sparkle_galaxy; Owner: postgres
--

ALTER TABLE ONLY sparkle_galaxy._ag_label_vertex
    ADD CONSTRAINT _ag_label_vertex_pkey PRIMARY KEY (id);


--
-- Name: idx_accountability_checkin_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_accountability_checkin_created_at ON accountability_checkin USING btree (created_at);


--
-- Name: idx_accountability_checkin_partnership_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_accountability_checkin_partnership_user ON accountability_checkin USING btree (partnership_id, user_id);


--
-- Name: idx_accountability_initiator_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_accountability_initiator_status ON accountability_partnership USING btree (initiator_id, status);


--
-- Name: idx_accountability_partner_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_accountability_partner_status ON accountability_partnership USING btree (partner_id, status);


--
-- Name: idx_accountability_policies_commitment_enabled; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_accountability_policies_commitment_enabled ON accountability_policies USING btree (commitment_id, is_enabled);


--
-- Name: idx_accountability_policies_user_next_trigger; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_accountability_policies_user_next_trigger ON accountability_policies USING btree (user_id, next_trigger_at);


--
-- Name: idx_accountability_slot_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_accountability_slot_status ON accountability_partnership USING btree (slot_type, status);


--
-- Name: idx_achievements_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_achievements_category ON achievements USING btree (category);


--
-- Name: idx_achievements_type_rarity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_achievements_type_rarity ON achievements USING btree (type, rarity);


--
-- Name: idx_admin_audit_category_occurred; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_admin_audit_category_occurred ON admin_audit_log USING btree (category, occurred_at);


--
-- Name: idx_admin_audit_user_occurred; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_admin_audit_user_occurred ON admin_audit_log USING btree (admin_user_id, occurred_at);


--
-- Name: idx_aurora_core_session_conversation; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_aurora_core_session_conversation ON aurora_core_session_snapshots USING btree (user_id, conversation_id, last_activity_at);


--
-- Name: idx_aurora_core_session_user_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_aurora_core_session_user_status ON aurora_core_session_snapshots USING btree (user_id, status, last_activity_at);


--
-- Name: idx_aurora_decision_telemetry_scope_ts; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_aurora_decision_telemetry_scope_ts ON aurora_decision_telemetry USING btree (user_id, conversation_id, decided_at);


--
-- Name: idx_aurora_decision_telemetry_surface_ts; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_aurora_decision_telemetry_surface_ts ON aurora_decision_telemetry USING btree (surface, decided_at);


--
-- Name: idx_aurora_judgment_records_user_computed; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_aurora_judgment_records_user_computed ON aurora_judgment_records USING btree (user_id, computed_at);


--
-- Name: idx_aurora_snapshot_scope; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_aurora_snapshot_scope ON aurora_state_snapshots USING btree (user_id, surface, conversation_id, snapshot_at);


--
-- Name: idx_aurora_wake_due; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_aurora_wake_due ON aurora_scheduled_wakes USING btree (status, scheduled_at);


--
-- Name: idx_aurora_wake_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_aurora_wake_id ON aurora_scheduled_wakes USING btree (wake_id);


--
-- Name: idx_aurora_wake_scope; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_aurora_wake_scope ON aurora_scheduled_wakes USING btree (user_id, surface, conversation_id);


--
-- Name: idx_auth_audit_user_occurred; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_auth_audit_user_occurred ON auth_audit_log USING btree (user_id, occurred_at);


--
-- Name: idx_background_tasks_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_background_tasks_type ON background_tasks USING btree (task_type);


--
-- Name: idx_background_tasks_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_background_tasks_user_status ON background_tasks USING btree (user_id, status);


--
-- Name: idx_candidate_feedback_action; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_candidate_feedback_action ON candidate_action_feedback USING btree (action_type);


--
-- Name: idx_candidate_feedback_created; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_candidate_feedback_created ON candidate_action_feedback USING btree (created_at);


--
-- Name: idx_candidate_feedback_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_candidate_feedback_type ON candidate_action_feedback USING btree (feedback_type);


--
-- Name: idx_candidate_feedback_user_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_candidate_feedback_user_type ON candidate_action_feedback USING btree (user_id, action_type);


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
-- Name: idx_cognitive_fragments_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cognitive_fragments_embedding_hnsw ON cognitive_fragments USING hnsw (embedding vector_cosine_ops) WHERE (embedding IS NOT NULL);


--
-- Name: idx_commitments_user_status_deadline; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_commitments_user_status_deadline ON commitments USING btree (user_id, status, deadline);


--
-- Name: idx_community_aggregate_cohort_stat; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_community_aggregate_cohort_stat ON community_aggregate_signals USING btree (cohort_key, stat_name, generated_at);


--
-- Name: idx_community_aggregate_status_generated; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_community_aggregate_status_generated ON community_aggregate_signals USING btree (status, generated_at);


--
-- Name: idx_conflict_resolution_records_user_conflict_key; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_conflict_resolution_records_user_conflict_key ON conflict_resolution_records USING btree (user_id, conflict_key);


--
-- Name: idx_conflict_resolution_records_user_resolved; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_conflict_resolution_records_user_resolved ON conflict_resolution_records USING btree (user_id, resolved_at);


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
-- Name: idx_counterfactual_report_pending; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_counterfactual_report_pending ON counterfactual_evaluation_reports USING btree (promotion_status, generated_at);


--
-- Name: idx_counterfactual_report_user_context_policies; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_counterfactual_report_user_context_policies ON counterfactual_evaluation_reports USING btree (user_id, context_hash, policy_a, policy_b, generated_at);


--
-- Name: idx_custom_expert_profiles_user_enabled; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_custom_expert_profiles_user_enabled ON custom_expert_profiles USING btree (user_id, is_enabled);


--
-- Name: idx_custom_expert_teams_user_enabled; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_custom_expert_teams_user_enabled ON custom_expert_teams USING btree (user_id, is_enabled);


--
-- Name: idx_daily_behavior_vector_user_active; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_daily_behavior_vector_user_active ON daily_behavior_vector USING btree (user_id, active_event_count);


--
-- Name: idx_daily_behavior_vector_user_date; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX idx_daily_behavior_vector_user_date ON daily_behavior_vector USING btree (user_id, vector_date);


--
-- Name: idx_dict_word; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dict_word ON dictionary_entries USING btree (word);


--
-- Name: idx_document_chunks_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops) WHERE (embedding IS NOT NULL);


--
-- Name: idx_durable_session_state_recovery; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_durable_session_state_recovery ON durable_session_state_snapshots USING btree (session_id, recoverable, expires_at);


--
-- Name: idx_durable_session_state_user_seen; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_durable_session_state_user_seen ON durable_session_state_snapshots USING btree (user_id, last_seen_at);


--
-- Name: idx_episodic_memories_archived_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_archived_at ON episodic_memories USING btree (archived_at);


--
-- Name: idx_episodic_memories_due_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_due_at ON episodic_memories USING btree (user_id, due_at);


--
-- Name: idx_episodic_memories_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_embedding_hnsw ON episodic_memories USING hnsw (embedding vector_cosine_ops) WHERE (embedding IS NOT NULL);


--
-- Name: idx_episodic_memories_evidence_missing; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_evidence_missing ON episodic_memories USING btree (evidence_missing);


--
-- Name: idx_episodic_memories_evidence_score; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_evidence_score ON episodic_memories USING btree (evidence_score);


--
-- Name: idx_episodic_memories_evidence_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_evidence_token ON episodic_memories USING btree (user_id, evidence_token);


--
-- Name: idx_episodic_memories_last_consumed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_last_consumed_at ON episodic_memories USING btree (last_consumed_at);


--
-- Name: idx_episodic_memories_semantic_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_semantic_key ON episodic_memories USING btree (user_id, semantic_key);


--
-- Name: idx_episodic_memories_source_lane; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_source_lane ON episodic_memories USING btree (user_id, source_lane);


--
-- Name: idx_episodic_memories_subject_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_subject_type ON episodic_memories USING btree (user_id, subject_type);


--
-- Name: idx_episodic_memories_user_occurred; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_episodic_memories_user_occurred ON episodic_memories USING btree (user_id, occurred_at);


--
-- Name: idx_error_records_affected_node; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_records_affected_node ON error_records USING btree (affected_node_id);


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
-- Name: idx_exec_intent_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exec_intent_created ON execution_intents USING btree (created_at);


--
-- Name: idx_exec_intent_external_run; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exec_intent_external_run ON execution_intents USING btree (external_run_id);


--
-- Name: idx_exec_intent_plan; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exec_intent_plan ON execution_intents USING btree (plan_id);


--
-- Name: idx_exec_intent_task; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exec_intent_task ON execution_intents USING btree (task_id);


--
-- Name: idx_exec_intent_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exec_intent_user_status ON execution_intents USING btree (user_id, status);


--
-- Name: idx_exec_record_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exec_record_created ON execution_records USING btree (created_at);


--
-- Name: idx_exec_record_intent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exec_record_intent ON execution_records USING btree (execution_intent_id);


--
-- Name: idx_exec_record_trust; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exec_record_trust ON execution_records USING btree (trust_level);


--
-- Name: idx_exec_record_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exec_record_user ON execution_records USING btree (user_id);


--
-- Name: idx_execution_audit_intent_occurred; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_execution_audit_intent_occurred ON execution_audit_log USING btree (intent_id, occurred_at);


--
-- Name: idx_execution_audit_user_action; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_execution_audit_user_action ON execution_audit_log USING btree (user_id, action);


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
-- Name: idx_execution_schedule_due; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_execution_schedule_due ON execution_schedules USING btree (is_active, next_run_at);


--
-- Name: idx_execution_schedule_user_trigger; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_execution_schedule_user_trigger ON execution_schedules USING btree (user_id, trigger_type);


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
-- Name: idx_goal_world_graph_user_goal; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX idx_goal_world_graph_user_goal ON goal_world_graph_snapshots USING btree (user_id, goal_id);


--
-- Name: idx_goal_world_graph_user_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_goal_world_graph_user_type ON goal_world_graph_snapshots USING btree (user_id, goal_type, last_saved_at);


--
-- Name: idx_goals_target_date; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_goals_target_date ON goals USING btree (target_date);


--
-- Name: idx_goals_user_primary; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_goals_user_primary ON goals USING btree (user_id, is_primary);


--
-- Name: idx_goals_user_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_goals_user_status ON goals USING btree (user_id, status);


--
-- Name: idx_goals_user_type_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_goals_user_type_status ON goals USING btree (user_id, goal_type, status);


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
-- Name: idx_group_files_knowledge_base; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_files_knowledge_base ON group_files USING btree (group_id, is_knowledge_base);


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
-- Name: idx_growth_chronicle_user_saved; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_growth_chronicle_user_saved ON growth_chronicle_snapshots USING btree (user_id, last_saved_at);


--
-- Name: idx_idempotency_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_idempotency_expires ON idempotency_keys USING btree (expires_at);


--
-- Name: idx_idiographic_associations_user_pair; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX idx_idiographic_associations_user_pair ON idiographic_associations USING btree (user_id, dim_pair);


--
-- Name: idx_idiographic_associations_user_visible; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_idiographic_associations_user_visible ON idiographic_associations USING btree (user_id, visible);


--
-- Name: idx_idiographic_changepoints_user_dim_date; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX idx_idiographic_changepoints_user_dim_date ON idiographic_changepoints USING btree (user_id, dim, change_date);


--
-- Name: idx_insight_claims_user_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_insight_claims_user_status ON insight_claims USING btree (user_id, status);


--
-- Name: idx_item_sim_item1; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_item_sim_item1 ON item_similarities USING btree (item_id_1);


--
-- Name: idx_item_sim_item2; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_item_sim_item2 ON item_similarities USING btree (item_id_2);


--
-- Name: idx_item_sim_score; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_item_sim_score ON item_similarities USING btree (similarity_score);


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
-- Name: idx_knowledge_node_documents_user_file_primary; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_knowledge_node_documents_user_file_primary ON knowledge_node_documents USING btree (user_id, file_id, is_primary);


--
-- Name: idx_knowledge_nodes_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_knowledge_nodes_embedding_hnsw ON knowledge_nodes USING hnsw (embedding vector_cosine_ops) WHERE (embedding IS NOT NULL);


--
-- Name: idx_leaderboard_snapshot_period; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_leaderboard_snapshot_period ON leaderboard_snapshots USING btree (period);


--
-- Name: idx_leaderboard_snapshot_type_date; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_leaderboard_snapshot_type_date ON leaderboard_snapshots USING btree (snapshot_type, snapshot_date);


--
-- Name: idx_learning_assets_headword; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_learning_assets_headword ON learning_assets USING btree (headword);


--
-- Name: idx_learning_assets_inbox_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_learning_assets_inbox_expires ON learning_assets USING btree (inbox_expires_at) WHERE ((status)::text = 'INBOX'::text);


--
-- Name: idx_learning_assets_review_due; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_learning_assets_review_due ON learning_assets USING btree (user_id, review_due_at) WHERE (((status)::text = 'ACTIVE'::text) AND (review_due_at IS NOT NULL));


--
-- Name: idx_learning_assets_selection_fp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_learning_assets_selection_fp ON learning_assets USING btree (user_id, selection_fp);


--
-- Name: idx_learning_assets_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_learning_assets_user_status ON learning_assets USING btree (user_id, status);


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
-- Name: idx_north_star_metric_events_plan_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_north_star_metric_events_plan_type ON north_star_metric_events USING btree (plan_id, event_type);


--
-- Name: idx_north_star_metric_events_type_date; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_north_star_metric_events_type_date ON north_star_metric_events USING btree (event_type, metric_date);


--
-- Name: idx_north_star_metric_events_user_date; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_north_star_metric_events_user_date ON north_star_metric_events USING btree (user_id, metric_date);


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
-- Name: idx_persdyn_attractors_user_confidence; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_persdyn_attractors_user_confidence ON persdyn_attractors USING btree (user_id, confidence);


--
-- Name: idx_persdyn_attractors_user_dim; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX idx_persdyn_attractors_user_dim ON persdyn_attractors USING btree (user_id, dim);


--
-- Name: idx_plan_states_updated_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plan_states_updated_at ON plan_states USING btree (updated_at);


--
-- Name: idx_plan_states_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plan_states_user_status ON plan_states USING btree (user_id, status);


--
-- Name: idx_plans_goal_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_goal_id ON plans USING btree (goal_id);


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
-- Name: idx_privacy_budget_allowed_spent; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_privacy_budget_allowed_spent ON privacy_budget_ledger USING btree (allowed, spent_at);


--
-- Name: idx_privacy_budget_subject_window; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_privacy_budget_subject_window ON privacy_budget_ledger USING btree (subject_id, window_key, query_type);


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
-- Name: idx_push_delivery_user_category; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_push_delivery_user_category ON push_delivery_records USING btree (user_id, category);


--
-- Name: idx_push_delivery_user_sent; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_push_delivery_user_sent ON push_delivery_records USING btree (user_id, sent_at);


--
-- Name: idx_rec_cache_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rec_cache_expires ON recommendation_cache USING btree (expires_at);


--
-- Name: idx_rec_cache_user_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rec_cache_user_type ON recommendation_cache USING btree (user_id, recommendation_type);


--
-- Name: idx_release_approval_category_status_created; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_release_approval_category_status_created ON release_approval_requests USING btree (category, status, created_at);


--
-- Name: idx_release_approval_object_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_release_approval_object_status ON release_approval_requests USING btree (object_type, object_id, status);


--
-- Name: idx_routing_decision_log_source_state_v2_key; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_routing_decision_log_source_state_v2_key ON routing_decision_log USING btree (source_state_v2_key);


--
-- Name: idx_routing_decision_log_user_decided; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_routing_decision_log_user_decided ON routing_decision_log USING btree (user_id, decided_at);


--
-- Name: idx_routing_decision_log_user_outcome; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_routing_decision_log_user_outcome ON routing_decision_log USING btree (user_id, outcome_collected_at);


--
-- Name: idx_routing_decision_log_user_outcome_v2; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_routing_decision_log_user_outcome_v2 ON routing_decision_log USING btree (user_id, outcome_timestamp);


--
-- Name: idx_safe_experiment_episodes_exp_created; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_safe_experiment_episodes_exp_created ON safe_experiment_episodes USING btree (experiment_id, created_at);


--
-- Name: idx_safe_experiments_status_domain; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_safe_experiments_status_domain ON safe_experiments USING btree (status, domain);


--
-- Name: idx_saga_instances_created; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_saga_instances_created ON saga_instances USING btree (created_at DESC);


--
-- Name: idx_saga_instances_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_saga_instances_status ON saga_instances USING btree (status);


--
-- Name: idx_saga_instances_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_saga_instances_type ON saga_instances USING btree (saga_type);


--
-- Name: idx_scenes_centroid_embedding_hnsw; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_scenes_centroid_embedding_hnsw ON scenes USING hnsw (centroid_embedding vector_cosine_ops) WHERE (centroid_embedding IS NOT NULL);


--
-- Name: idx_scenes_user_quality; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_scenes_user_quality ON scenes USING btree (user_id, quality_score);


--
-- Name: idx_scenes_user_time_window; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_scenes_user_time_window ON scenes USING btree (user_id, time_start, time_end);


--
-- Name: idx_scenes_user_version; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_scenes_user_version ON scenes USING btree (user_id, version);


--
-- Name: idx_seed_items_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_seed_items_embedding_hnsw ON seed_items USING hnsw (embedding vector_cosine_ops) WHERE (embedding IS NOT NULL);


--
-- Name: idx_share_card_share_record; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_card_share_record ON shared_resources USING btree (card_share_record_id);


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
-- Name: idx_share_resource_seed_item; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_resource_seed_item ON shared_resources USING btree (seed_item_id);


--
-- Name: idx_share_resource_seed_library; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_resource_seed_library ON shared_resources USING btree (seed_library_id);


--
-- Name: idx_share_target_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_target_user ON shared_resources USING btree (target_user_id);


--
-- Name: idx_shared_skills_published; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_shared_skills_published ON shared_skills USING btree (published_at);


--
-- Name: idx_skill_share_queue_owner_created; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_skill_share_queue_owner_created ON skill_share_moderation_queue USING btree (owner_user_id, created_at);


--
-- Name: idx_strategy_belief_user_score_inputs; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_strategy_belief_user_score_inputs ON strategy_belief_snapshots USING btree (user_id, strategy_key, evidence_count);


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
-- Name: idx_suggestion_log_policy; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_suggestion_log_policy ON asset_suggestion_logs USING btree (policy_id);


--
-- Name: idx_suggestion_log_user_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_suggestion_log_user_created ON asset_suggestion_logs USING btree (user_id, created_at);


--
-- Name: idx_task_documents_task_created; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_task_documents_task_created ON task_documents USING btree (task_id, created_at);


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
-- Name: idx_tasks_user_order_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_user_order_index ON tasks USING btree (user_id, order_index);


--
-- Name: idx_tasks_user_status_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_user_status_created_at ON tasks USING btree (user_id, status, created_at);


--
-- Name: idx_tdr_user_created_snapshot; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_tdr_user_created_snapshot ON transition_decision_records USING btree (user_id, created_at, input_snapshot_ref);


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
-- Name: idx_unresolved_conflicts_user_conflict_key; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_unresolved_conflicts_user_conflict_key ON unresolved_conflicts USING btree (user_id, conflict_key);


--
-- Name: idx_unresolved_conflicts_user_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_unresolved_conflicts_user_status ON unresolved_conflicts USING btree (user_id, status);


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
-- Name: idx_user_learning_profiles_cluster_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_learning_profiles_cluster_id ON user_learning_profiles USING btree (cluster_id);


--
-- Name: idx_user_learning_profiles_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_learning_profiles_user_id ON user_learning_profiles USING btree (user_id);


--
-- Name: idx_user_memory_settings_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_user_memory_settings_user ON user_memory_settings USING btree (user_id);


--
-- Name: idx_user_push_opt_in_user; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX idx_user_push_opt_in_user ON user_push_opt_in USING btree (user_id);


--
-- Name: idx_user_scenario_states_user_focus; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_user_scenario_states_user_focus ON user_scenario_states USING btree (user_id, current_focus_contract_id, current_focus_contract_version);


--
-- Name: idx_user_sessions_user_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_sessions_user_active ON user_sessions USING btree (user_id, is_active);


--
-- Name: idx_user_settings_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_user_settings_user ON user_settings USING btree (user_id);


--
-- Name: idx_user_sim_score; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_sim_score ON user_similarities USING btree (similarity_score);


--
-- Name: idx_user_sim_user1; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_sim_user1 ON user_similarities USING btree (user_id_1);


--
-- Name: idx_user_sim_user2; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_sim_user2 ON user_similarities USING btree (user_id_2);


--
-- Name: idx_user_skills_user_active; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_user_skills_user_active ON user_skills USING btree (user_id, active);


--
-- Name: idx_user_skills_user_updated; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX idx_user_skills_user_updated ON user_skills USING btree (user_id, updated_at);


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
-- Name: ix_accountability_policies_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_accountability_policies_deleted_at ON accountability_policies USING btree (deleted_at);


--
-- Name: ix_accountability_policies_policy_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_accountability_policies_policy_id ON accountability_policies USING btree (policy_id);


--
-- Name: ix_accountability_policies_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_accountability_policies_user_id ON accountability_policies USING btree (user_id);


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
-- Name: ix_admin_audit_log_action; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_action ON admin_audit_log USING btree (action);


--
-- Name: ix_admin_audit_log_admin_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_admin_user_id ON admin_audit_log USING btree (admin_user_id);


--
-- Name: ix_admin_audit_log_category; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_category ON admin_audit_log USING btree (category);


--
-- Name: ix_admin_audit_log_created_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_created_at ON admin_audit_log USING btree (created_at);


--
-- Name: ix_admin_audit_log_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_id ON admin_audit_log USING btree (id);


--
-- Name: ix_admin_audit_log_ip_address; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_ip_address ON admin_audit_log USING btree (ip_address);


--
-- Name: ix_admin_audit_log_occurred_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_occurred_at ON admin_audit_log USING btree (occurred_at);


--
-- Name: ix_admin_audit_log_outcome; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_outcome ON admin_audit_log USING btree (outcome);


--
-- Name: ix_admin_audit_log_path; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_path ON admin_audit_log USING btree (path);


--
-- Name: ix_admin_audit_log_request_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_request_id ON admin_audit_log USING btree (request_id);


--
-- Name: ix_admin_audit_log_retention_until; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_retention_until ON admin_audit_log USING btree (retention_until);


--
-- Name: ix_admin_audit_log_risk; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_risk ON admin_audit_log USING btree (risk);


--
-- Name: ix_admin_audit_log_status_code; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_status_code ON admin_audit_log USING btree (status_code);


--
-- Name: ix_admin_audit_log_trace_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_admin_audit_log_trace_id ON admin_audit_log USING btree (trace_id);


--
-- Name: ix_agent_execution_stats_agent_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_execution_stats_agent_type ON agent_execution_stats USING btree (agent_type);


--
-- Name: ix_agent_execution_stats_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_execution_stats_created_at ON agent_execution_stats USING btree (created_at);


--
-- Name: ix_agent_execution_stats_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_execution_stats_session_id ON agent_execution_stats USING btree (session_id);


--
-- Name: ix_agent_execution_stats_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_execution_stats_user_id ON agent_execution_stats USING btree (user_id);


--
-- Name: ix_agent_stats_user_agent_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_stats_user_agent_type ON agent_execution_stats USING btree (user_id, agent_type);


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
-- Name: ix_artifacts_artifact_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_artifacts_artifact_type ON planning_artifacts USING btree (artifact_type);


--
-- Name: ix_artifacts_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_artifacts_deleted_at ON planning_artifacts USING btree (deleted_at);


--
-- Name: ix_artifacts_plan_card_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_artifacts_plan_card_id ON planning_artifacts USING btree (plan_card_id);


--
-- Name: ix_artifacts_plan_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_artifacts_plan_type ON planning_artifacts USING btree (plan_card_id, artifact_type);


--
-- Name: ix_artifacts_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_artifacts_status ON planning_artifacts USING btree (status);


--
-- Name: ix_artifacts_type_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_artifacts_type_status ON planning_artifacts USING btree (artifact_type, status);


--
-- Name: ix_aurora_core_session_snapshots_conversation_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_core_session_snapshots_conversation_id ON aurora_core_session_snapshots USING btree (conversation_id);


--
-- Name: ix_aurora_core_session_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_core_session_snapshots_deleted_at ON aurora_core_session_snapshots USING btree (deleted_at);


--
-- Name: ix_aurora_core_session_snapshots_expires_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_core_session_snapshots_expires_at ON aurora_core_session_snapshots USING btree (expires_at);


--
-- Name: ix_aurora_core_session_snapshots_last_activity_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_core_session_snapshots_last_activity_at ON aurora_core_session_snapshots USING btree (last_activity_at);


--
-- Name: ix_aurora_core_session_snapshots_resume_token_hash; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_aurora_core_session_snapshots_resume_token_hash ON aurora_core_session_snapshots USING btree (resume_token_hash);


--
-- Name: ix_aurora_core_session_snapshots_session_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_core_session_snapshots_session_id ON aurora_core_session_snapshots USING btree (session_id);


--
-- Name: ix_aurora_core_session_snapshots_stage; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_core_session_snapshots_stage ON aurora_core_session_snapshots USING btree (stage);


--
-- Name: ix_aurora_core_session_snapshots_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_core_session_snapshots_status ON aurora_core_session_snapshots USING btree (status);


--
-- Name: ix_aurora_core_session_snapshots_surface; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_core_session_snapshots_surface ON aurora_core_session_snapshots USING btree (surface);


--
-- Name: ix_aurora_core_session_snapshots_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_core_session_snapshots_user_id ON aurora_core_session_snapshots USING btree (user_id);


--
-- Name: ix_aurora_decision_telemetry_action; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_decision_telemetry_action ON aurora_decision_telemetry USING btree (action);


--
-- Name: ix_aurora_decision_telemetry_conversation_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_decision_telemetry_conversation_id ON aurora_decision_telemetry USING btree (conversation_id);


--
-- Name: ix_aurora_decision_telemetry_decided_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_decision_telemetry_decided_at ON aurora_decision_telemetry USING btree (decided_at);


--
-- Name: ix_aurora_decision_telemetry_decision_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_aurora_decision_telemetry_decision_id ON aurora_decision_telemetry USING btree (decision_id);


--
-- Name: ix_aurora_decision_telemetry_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_decision_telemetry_deleted_at ON aurora_decision_telemetry USING btree (deleted_at);


--
-- Name: ix_aurora_decision_telemetry_energy_level; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_decision_telemetry_energy_level ON aurora_decision_telemetry USING btree (energy_level);


--
-- Name: ix_aurora_decision_telemetry_outcome; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_decision_telemetry_outcome ON aurora_decision_telemetry USING btree (outcome);


--
-- Name: ix_aurora_decision_telemetry_outcome_filled_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_decision_telemetry_outcome_filled_at ON aurora_decision_telemetry USING btree (outcome_filled_at);


--
-- Name: ix_aurora_decision_telemetry_request_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_decision_telemetry_request_id ON aurora_decision_telemetry USING btree (request_id);


--
-- Name: ix_aurora_decision_telemetry_surface; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_decision_telemetry_surface ON aurora_decision_telemetry USING btree (surface);


--
-- Name: ix_aurora_decision_telemetry_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_decision_telemetry_user_id ON aurora_decision_telemetry USING btree (user_id);


--
-- Name: ix_aurora_policy_versions_created_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_policy_versions_created_at ON aurora_policy_versions USING btree (created_at);


--
-- Name: ix_aurora_scheduled_wakes_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_scheduled_wakes_user_id ON aurora_scheduled_wakes USING btree (user_id);


--
-- Name: ix_aurora_scheduled_wakes_wake_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_scheduled_wakes_wake_id ON aurora_scheduled_wakes USING btree (wake_id);


--
-- Name: ix_aurora_state_snapshots_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_aurora_state_snapshots_user_id ON aurora_state_snapshots USING btree (user_id);


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
-- Name: ix_background_tasks_external_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_background_tasks_external_task_id ON background_tasks USING btree (external_task_id);


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
-- Name: ix_candidate_action_feedback_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_candidate_action_feedback_deleted_at ON candidate_action_feedback USING btree (deleted_at);


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
-- Name: ix_card_adoption_records_adopted_root_card_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_adoption_records_adopted_root_card_id ON card_adoption_records USING btree (adopted_root_card_id);


--
-- Name: ix_card_adoption_records_adopter_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_adoption_records_adopter_user_id ON card_adoption_records USING btree (adopter_user_id);


--
-- Name: ix_card_adoption_records_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_adoption_records_deleted_at ON card_adoption_records USING btree (deleted_at);


--
-- Name: ix_card_adoption_records_import_mode; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_adoption_records_import_mode ON card_adoption_records USING btree (import_mode);


--
-- Name: ix_card_adoption_records_share_record_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_adoption_records_share_record_id ON card_adoption_records USING btree (share_record_id);


--
-- Name: ix_card_adoption_user_mode; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_adoption_user_mode ON card_adoption_records USING btree (adopter_user_id, import_mode);


--
-- Name: ix_card_edges_active; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_edges_active ON card_edges USING btree (active);


--
-- Name: ix_card_edges_active_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_edges_active_type ON card_edges USING btree (active, edge_type);


--
-- Name: ix_card_edges_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_edges_deleted_at ON card_edges USING btree (deleted_at);


--
-- Name: ix_card_edges_edge_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_edges_edge_type ON card_edges USING btree (edge_type);


--
-- Name: ix_card_edges_from_card_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_edges_from_card_id ON card_edges USING btree (from_card_id);


--
-- Name: ix_card_edges_from_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_edges_from_type ON card_edges USING btree (from_card_id, edge_type);


--
-- Name: ix_card_edges_to_card_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_edges_to_card_id ON card_edges USING btree (to_card_id);


--
-- Name: ix_card_edges_to_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_edges_to_type ON card_edges USING btree (to_card_id, edge_type);


--
-- Name: ix_card_share_owner_scope; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_share_owner_scope ON card_share_records USING btree (shared_by_user_id, scope);


--
-- Name: ix_card_share_records_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_share_records_deleted_at ON card_share_records USING btree (deleted_at);


--
-- Name: ix_card_share_records_group_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_share_records_group_id ON card_share_records USING btree (group_id);


--
-- Name: ix_card_share_records_root_card_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_share_records_root_card_id ON card_share_records USING btree (root_card_id);


--
-- Name: ix_card_share_records_scope; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_share_records_scope ON card_share_records USING btree (scope);


--
-- Name: ix_card_share_records_shared_by_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_share_records_shared_by_user_id ON card_share_records USING btree (shared_by_user_id);


--
-- Name: ix_card_share_records_snapshot_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_share_records_snapshot_id ON card_share_records USING btree (snapshot_id);


--
-- Name: ix_card_share_records_target_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_share_records_target_user_id ON card_share_records USING btree (target_user_id);


--
-- Name: ix_card_share_scope_group; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_share_scope_group ON card_share_records USING btree (scope, group_id);


--
-- Name: ix_card_share_scope_target; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_share_scope_target ON card_share_records USING btree (scope, target_user_id);


--
-- Name: ix_card_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_snapshots_deleted_at ON card_snapshots USING btree (deleted_at);


--
-- Name: ix_card_snapshots_owner_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_snapshots_owner_type ON card_snapshots USING btree (source_owner_id, source_card_type);


--
-- Name: ix_card_snapshots_root_card_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_snapshots_root_card_id ON card_snapshots USING btree (root_card_id);


--
-- Name: ix_card_snapshots_root_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_snapshots_root_type ON card_snapshots USING btree (root_card_id, source_card_type);


--
-- Name: ix_card_snapshots_source_card_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_snapshots_source_card_type ON card_snapshots USING btree (source_card_type);


--
-- Name: ix_card_snapshots_source_owner_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_card_snapshots_source_owner_id ON card_snapshots USING btree (source_owner_id);


--
-- Name: ix_cards_card_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_cards_card_type ON cards USING btree (card_type);


--
-- Name: ix_cards_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_cards_deleted_at ON cards USING btree (deleted_at);


--
-- Name: ix_cards_holder_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_cards_holder_id ON cards USING btree (holder_id);


--
-- Name: ix_cards_holder_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_cards_holder_status ON cards USING btree (holder_id, lifecycle_status);


--
-- Name: ix_cards_lifecycle_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_cards_lifecycle_status ON cards USING btree (lifecycle_status);


--
-- Name: ix_cards_owner_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_cards_owner_id ON cards USING btree (owner_id);


--
-- Name: ix_cards_owner_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_cards_owner_type ON cards USING btree (owner_id, card_type);


--
-- Name: ix_cards_type_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_cards_type_status ON cards USING btree (card_type, lifecycle_status);


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
-- Name: ix_collaborative_galaxies_galaxy_scope; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_collaborative_galaxies_galaxy_scope ON collaborative_galaxies USING btree (galaxy_scope);


--
-- Name: ix_collaborative_galaxies_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_collaborative_galaxies_group_id ON collaborative_galaxies USING btree (group_id);


--
-- Name: ix_commitments_deadline; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_commitments_deadline ON commitments USING btree (deadline);


--
-- Name: ix_commitments_node_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_commitments_node_id ON commitments USING btree (node_id);


--
-- Name: ix_commitments_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_commitments_status ON commitments USING btree (status);


--
-- Name: ix_commitments_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_commitments_user_id ON commitments USING btree (user_id);


--
-- Name: ix_community_aggregate_signals_cohort_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_community_aggregate_signals_cohort_id ON community_aggregate_signals USING btree (cohort_id);


--
-- Name: ix_community_aggregate_signals_cohort_key; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_community_aggregate_signals_cohort_key ON community_aggregate_signals USING btree (cohort_key);


--
-- Name: ix_community_aggregate_signals_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_community_aggregate_signals_deleted_at ON community_aggregate_signals USING btree (deleted_at);


--
-- Name: ix_community_aggregate_signals_expires_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_community_aggregate_signals_expires_at ON community_aggregate_signals USING btree (expires_at);


--
-- Name: ix_community_aggregate_signals_generated_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_community_aggregate_signals_generated_at ON community_aggregate_signals USING btree (generated_at);


--
-- Name: ix_community_aggregate_signals_privacy_tier; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_community_aggregate_signals_privacy_tier ON community_aggregate_signals USING btree (privacy_tier);


--
-- Name: ix_community_aggregate_signals_signal_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_community_aggregate_signals_signal_id ON community_aggregate_signals USING btree (signal_id);


--
-- Name: ix_community_aggregate_signals_signal_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_community_aggregate_signals_signal_type ON community_aggregate_signals USING btree (signal_type);


--
-- Name: ix_community_aggregate_signals_stat_name; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_community_aggregate_signals_stat_name ON community_aggregate_signals USING btree (stat_name);


--
-- Name: ix_community_aggregate_signals_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_community_aggregate_signals_status ON community_aggregate_signals USING btree (status);


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
-- Name: ix_counterfactual_evaluation_reports_context_hash; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_counterfactual_evaluation_reports_context_hash ON counterfactual_evaluation_reports USING btree (context_hash);


--
-- Name: ix_counterfactual_evaluation_reports_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_counterfactual_evaluation_reports_deleted_at ON counterfactual_evaluation_reports USING btree (deleted_at);


--
-- Name: ix_counterfactual_evaluation_reports_evidence_grade; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_counterfactual_evaluation_reports_evidence_grade ON counterfactual_evaluation_reports USING btree (evidence_grade);


--
-- Name: ix_counterfactual_evaluation_reports_generated_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_counterfactual_evaluation_reports_generated_at ON counterfactual_evaluation_reports USING btree (generated_at);


--
-- Name: ix_counterfactual_evaluation_reports_policy_a; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_counterfactual_evaluation_reports_policy_a ON counterfactual_evaluation_reports USING btree (policy_a);


--
-- Name: ix_counterfactual_evaluation_reports_policy_b; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_counterfactual_evaluation_reports_policy_b ON counterfactual_evaluation_reports USING btree (policy_b);


--
-- Name: ix_counterfactual_evaluation_reports_promotion_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_counterfactual_evaluation_reports_promotion_status ON counterfactual_evaluation_reports USING btree (promotion_status);


--
-- Name: ix_counterfactual_evaluation_reports_replaced_by_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_counterfactual_evaluation_reports_replaced_by_id ON counterfactual_evaluation_reports USING btree (replaced_by_id);


--
-- Name: ix_counterfactual_evaluation_reports_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_counterfactual_evaluation_reports_user_id ON counterfactual_evaluation_reports USING btree (user_id);


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
-- Name: ix_custom_expert_profiles_base_expert_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_custom_expert_profiles_base_expert_id ON custom_expert_profiles USING btree (base_expert_id);


--
-- Name: ix_custom_expert_profiles_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_custom_expert_profiles_deleted_at ON custom_expert_profiles USING btree (deleted_at);


--
-- Name: ix_custom_expert_profiles_preferred_model_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_custom_expert_profiles_preferred_model_key ON custom_expert_profiles USING btree (preferred_model_key);


--
-- Name: ix_custom_expert_profiles_preferred_model_tier; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_custom_expert_profiles_preferred_model_tier ON custom_expert_profiles USING btree (preferred_model_tier);


--
-- Name: ix_custom_expert_profiles_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_custom_expert_profiles_user_id ON custom_expert_profiles USING btree (user_id);


--
-- Name: ix_custom_expert_teams_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_custom_expert_teams_deleted_at ON custom_expert_teams USING btree (deleted_at);


--
-- Name: ix_custom_expert_teams_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_custom_expert_teams_user_id ON custom_expert_teams USING btree (user_id);


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
-- Name: ix_distilled_strategy_cache_shareability; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_distilled_strategy_cache_shareability ON distilled_strategy_cache USING btree (shareability);


--
-- Name: ix_distilled_strategy_cache_source_trajectory_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_distilled_strategy_cache_source_trajectory_type ON distilled_strategy_cache USING btree (source_trajectory_type);


--
-- Name: ix_distilled_strategy_cache_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_distilled_strategy_cache_status ON distilled_strategy_cache USING btree (status);


--
-- Name: ix_distilled_strategy_cache_status_source; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_distilled_strategy_cache_status_source ON distilled_strategy_cache USING btree (status, source_trajectory_type);


--
-- Name: ix_distilled_strategy_cache_updated_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_distilled_strategy_cache_updated_at ON distilled_strategy_cache USING btree (updated_at);


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
-- Name: ix_document_retrieval_feedback_created_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_document_retrieval_feedback_created_at ON document_retrieval_feedback USING btree (created_at);


--
-- Name: ix_document_retrieval_feedback_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_document_retrieval_feedback_deleted_at ON document_retrieval_feedback USING btree (deleted_at);


--
-- Name: ix_document_retrieval_feedback_file_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_document_retrieval_feedback_file_id ON document_retrieval_feedback USING btree (file_id);


--
-- Name: ix_document_retrieval_feedback_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_document_retrieval_feedback_user_id ON document_retrieval_feedback USING btree (user_id);


--
-- Name: ix_durable_session_state_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_durable_session_state_snapshots_deleted_at ON durable_session_state_snapshots USING btree (deleted_at);


--
-- Name: ix_durable_session_state_snapshots_expires_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_durable_session_state_snapshots_expires_at ON durable_session_state_snapshots USING btree (expires_at);


--
-- Name: ix_durable_session_state_snapshots_fsm_state; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_durable_session_state_snapshots_fsm_state ON durable_session_state_snapshots USING btree (fsm_state);


--
-- Name: ix_durable_session_state_snapshots_last_seen_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_durable_session_state_snapshots_last_seen_at ON durable_session_state_snapshots USING btree (last_seen_at);


--
-- Name: ix_durable_session_state_snapshots_recoverable; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_durable_session_state_snapshots_recoverable ON durable_session_state_snapshots USING btree (recoverable);


--
-- Name: ix_durable_session_state_snapshots_request_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_durable_session_state_snapshots_request_id ON durable_session_state_snapshots USING btree (request_id);


--
-- Name: ix_durable_session_state_snapshots_session_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_durable_session_state_snapshots_session_id ON durable_session_state_snapshots USING btree (session_id);


--
-- Name: ix_durable_session_state_snapshots_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_durable_session_state_snapshots_user_id ON durable_session_state_snapshots USING btree (user_id);


--
-- Name: ix_episodic_memories_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_episodic_memories_deleted_at ON episodic_memories USING btree (deleted_at);


--
-- Name: ix_episodic_memories_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_episodic_memories_user_id ON episodic_memories USING btree (user_id);


--
-- Name: ix_event_bus_dlq_created_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_event_bus_dlq_created_at ON event_bus_dlq USING btree (created_at);


--
-- Name: ix_event_bus_dlq_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_event_bus_dlq_deleted_at ON event_bus_dlq USING btree (deleted_at);


--
-- Name: ix_event_bus_dlq_event_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_event_bus_dlq_event_type ON event_bus_dlq USING btree (event_type);


--
-- Name: ix_event_bus_dlq_failure_stage; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_event_bus_dlq_failure_stage ON event_bus_dlq USING btree (failure_stage);


--
-- Name: ix_event_bus_dlq_group_name; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_event_bus_dlq_group_name ON event_bus_dlq USING btree (group_name);


--
-- Name: ix_event_bus_dlq_message_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_event_bus_dlq_message_id ON event_bus_dlq USING btree (message_id);


--
-- Name: ix_event_bus_dlq_stream; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_event_bus_dlq_stream ON event_bus_dlq USING btree (stream);


--
-- Name: ix_event_bus_dlq_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_event_bus_dlq_user_id ON event_bus_dlq USING btree (user_id);


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
-- Name: ix_execution_audit_log_action; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_execution_audit_log_action ON execution_audit_log USING btree (action);


--
-- Name: ix_execution_audit_log_actor; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_execution_audit_log_actor ON execution_audit_log USING btree (actor);


--
-- Name: ix_execution_audit_log_intent_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_execution_audit_log_intent_id ON execution_audit_log USING btree (intent_id);


--
-- Name: ix_execution_audit_log_occurred_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_execution_audit_log_occurred_at ON execution_audit_log USING btree (occurred_at);


--
-- Name: ix_execution_audit_log_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_execution_audit_log_user_id ON execution_audit_log USING btree (user_id);


--
-- Name: ix_execution_schedules_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_execution_schedules_deleted_at ON execution_schedules USING btree (deleted_at);


--
-- Name: ix_execution_schedules_is_active; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_execution_schedules_is_active ON execution_schedules USING btree (is_active);


--
-- Name: ix_execution_schedules_next_run_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_execution_schedules_next_run_at ON execution_schedules USING btree (next_run_at);


--
-- Name: ix_execution_schedules_task_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_execution_schedules_task_id ON execution_schedules USING btree (task_id);


--
-- Name: ix_execution_schedules_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_execution_schedules_user_id ON execution_schedules USING btree (user_id);


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
-- Name: ix_focus_contracts_active_node; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_focus_contracts_active_node ON focus_contracts USING btree (active_node);


--
-- Name: ix_focus_contracts_scenario_pack_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_focus_contracts_scenario_pack_id ON focus_contracts USING btree (scenario_pack_id);


--
-- Name: ix_focus_contracts_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_focus_contracts_user_id ON focus_contracts USING btree (user_id);


--
-- Name: ix_focus_contracts_user_version; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_focus_contracts_user_version ON focus_contracts USING btree (user_id, version);


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
-- Name: ix_goal_world_graph_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_goal_world_graph_snapshots_deleted_at ON goal_world_graph_snapshots USING btree (deleted_at);


--
-- Name: ix_goal_world_graph_snapshots_goal_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_goal_world_graph_snapshots_goal_id ON goal_world_graph_snapshots USING btree (goal_id);


--
-- Name: ix_goal_world_graph_snapshots_goal_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_goal_world_graph_snapshots_goal_type ON goal_world_graph_snapshots USING btree (goal_type);


--
-- Name: ix_goal_world_graph_snapshots_graph_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_goal_world_graph_snapshots_graph_id ON goal_world_graph_snapshots USING btree (graph_id);


--
-- Name: ix_goal_world_graph_snapshots_last_saved_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_goal_world_graph_snapshots_last_saved_at ON goal_world_graph_snapshots USING btree (last_saved_at);


--
-- Name: ix_goal_world_graph_snapshots_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_goal_world_graph_snapshots_user_id ON goal_world_graph_snapshots USING btree (user_id);


--
-- Name: ix_goals_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_goals_user_id ON goals USING btree (user_id);


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
-- Name: ix_group_files_is_knowledge_base; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_files_is_knowledge_base ON group_files USING btree (is_knowledge_base);


--
-- Name: ix_group_files_shared_by_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_files_shared_by_id ON group_files USING btree (shared_by_id);


--
-- Name: ix_group_files_trust_level; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_files_trust_level ON group_files USING btree (trust_level);


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
-- Name: ix_growth_chronicle_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_growth_chronicle_snapshots_deleted_at ON growth_chronicle_snapshots USING btree (deleted_at);


--
-- Name: ix_growth_chronicle_snapshots_last_saved_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_growth_chronicle_snapshots_last_saved_at ON growth_chronicle_snapshots USING btree (last_saved_at);


--
-- Name: ix_growth_chronicle_snapshots_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_growth_chronicle_snapshots_user_id ON growth_chronicle_snapshots USING btree (user_id);


--
-- Name: ix_idempotency_keys_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_idempotency_keys_expires_at ON idempotency_keys USING btree (expires_at);


--
-- Name: ix_idempotency_keys_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_idempotency_keys_user_id ON idempotency_keys USING btree (user_id);


--
-- Name: ix_identity_evidence_created_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_identity_evidence_created_at ON identity_evidence USING btree (created_at);


--
-- Name: ix_identity_evidence_dimension; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_identity_evidence_dimension ON identity_evidence USING btree (dimension);


--
-- Name: ix_identity_evidence_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_identity_evidence_user_id ON identity_evidence USING btree (user_id);


--
-- Name: ix_insight_claims_created_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_insight_claims_created_at ON insight_claims USING btree (created_at);


--
-- Name: ix_insight_claims_source; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_insight_claims_source ON insight_claims USING btree (source);


--
-- Name: ix_insight_claims_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_insight_claims_status ON insight_claims USING btree (status);


--
-- Name: ix_insight_claims_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_insight_claims_user_id ON insight_claims USING btree (user_id);


--
-- Name: ix_intervention_acceptance_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_acceptance_status ON intervention_records USING btree (acceptance_status);


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
-- Name: ix_intervention_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_deleted_at ON intervention_records USING btree (deleted_at);


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
-- Name: ix_intervention_outcome; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_outcome ON intervention_records USING btree (outcome_status, outcome_window_days);


--
-- Name: ix_intervention_outcomes_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_outcomes_deleted_at ON intervention_outcomes USING btree (deleted_at);


--
-- Name: ix_intervention_outcomes_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_outcomes_user_id ON intervention_outcomes USING btree (user_id);


--
-- Name: ix_intervention_plan_card_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_plan_card_id ON intervention_records USING btree (plan_card_id);


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
-- Name: ix_intervention_strategy_outcomes_intervention_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_strategy_outcomes_intervention_id ON intervention_strategy_outcomes USING btree (intervention_id);


--
-- Name: ix_intervention_strategy_outcomes_outcome; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_strategy_outcomes_outcome ON intervention_strategy_outcomes USING btree (outcome);


--
-- Name: ix_intervention_strategy_outcomes_trigger_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_strategy_outcomes_trigger_type ON intervention_strategy_outcomes USING btree (trigger_type);


--
-- Name: ix_intervention_strategy_outcomes_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_strategy_outcomes_user_id ON intervention_strategy_outcomes USING btree (user_id);


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
-- Name: ix_intervention_trigger_channel; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_trigger_channel ON intervention_records USING btree (trigger_type, delivery_channel);


--
-- Name: ix_intervention_trigger_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_trigger_type ON intervention_records USING btree (trigger_type);


--
-- Name: ix_intervention_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_user_id ON intervention_records USING btree (user_id);


--
-- Name: ix_intervention_user_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_intervention_user_status ON intervention_records USING btree (user_id, acceptance_status);


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
-- Name: ix_item_similarities_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_item_similarities_deleted_at ON item_similarities USING btree (deleted_at);


--
-- Name: ix_jobs_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_jobs_deleted_at ON jobs USING btree (deleted_at);


--
-- Name: ix_jobs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_jobs_user_id ON jobs USING btree (user_id);


--
-- Name: ix_knowledge_node_documents_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_knowledge_node_documents_deleted_at ON knowledge_node_documents USING btree (deleted_at);


--
-- Name: ix_knowledge_node_documents_file_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_knowledge_node_documents_file_id ON knowledge_node_documents USING btree (file_id);


--
-- Name: ix_knowledge_node_documents_is_primary; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_knowledge_node_documents_is_primary ON knowledge_node_documents USING btree (is_primary);


--
-- Name: ix_knowledge_node_documents_node_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_knowledge_node_documents_node_id ON knowledge_node_documents USING btree (node_id);


--
-- Name: ix_knowledge_node_documents_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_knowledge_node_documents_user_id ON knowledge_node_documents USING btree (user_id);


--
-- Name: ix_knowledge_nodes_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_deleted_at ON knowledge_nodes USING btree (deleted_at);


--
-- Name: ix_knowledge_nodes_dominant_sector_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_dominant_sector_code ON knowledge_nodes USING btree (dominant_sector_code);


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
-- Name: ix_knowledge_nodes_sector_classification_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_sector_classification_status ON knowledge_nodes USING btree (sector_classification_status);


--
-- Name: ix_knowledge_nodes_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_status ON knowledge_nodes USING btree (status);


--
-- Name: ix_knowledge_nodes_subject_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_subject_id ON knowledge_nodes USING btree (subject_id);


--
-- Name: ix_leaderboard_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_leaderboard_snapshots_deleted_at ON leaderboard_snapshots USING btree (deleted_at);


--
-- Name: ix_leaderboard_snapshots_snapshot_date; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_leaderboard_snapshots_snapshot_date ON leaderboard_snapshots USING btree (snapshot_date);


--
-- Name: ix_leaderboard_snapshots_snapshot_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_leaderboard_snapshots_snapshot_type ON leaderboard_snapshots USING btree (snapshot_type);


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
-- Name: ix_marketplace_packs_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_packs_deleted_at ON marketplace_packs USING btree (deleted_at);


--
-- Name: ix_marketplace_packs_domain; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_packs_domain ON marketplace_packs USING btree (domain);


--
-- Name: ix_marketplace_packs_pack_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_marketplace_packs_pack_id ON marketplace_packs USING btree (pack_id);


--
-- Name: ix_marketplace_packs_quality; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_packs_quality ON marketplace_packs USING btree (status, quality_score);


--
-- Name: ix_marketplace_packs_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_packs_status ON marketplace_packs USING btree (status);


--
-- Name: ix_marketplace_packs_status_domain; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_packs_status_domain ON marketplace_packs USING btree (status, domain);


--
-- Name: ix_marketplace_skills_author_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_skills_author_id ON marketplace_skills USING btree (author_id);


--
-- Name: ix_marketplace_skills_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_skills_deleted_at ON marketplace_skills USING btree (deleted_at);


--
-- Name: ix_marketplace_skills_domain; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_skills_domain ON marketplace_skills USING btree (domain);


--
-- Name: ix_marketplace_skills_evidence_grade; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_skills_evidence_grade ON marketplace_skills USING btree (evidence_grade);


--
-- Name: ix_marketplace_skills_quality; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_skills_quality ON marketplace_skills USING btree (status, quality_score);


--
-- Name: ix_marketplace_skills_skill_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_marketplace_skills_skill_id ON marketplace_skills USING btree (skill_id);


--
-- Name: ix_marketplace_skills_source_skill_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_skills_source_skill_id ON marketplace_skills USING btree (source_skill_id);


--
-- Name: ix_marketplace_skills_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_skills_status ON marketplace_skills USING btree (status);


--
-- Name: ix_marketplace_skills_status_domain; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_marketplace_skills_status_domain ON marketplace_skills USING btree (status, domain);


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
-- Name: ix_north_star_metric_events_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_north_star_metric_events_deleted_at ON north_star_metric_events USING btree (deleted_at);


--
-- Name: ix_north_star_metric_events_event_key; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_north_star_metric_events_event_key ON north_star_metric_events USING btree (event_key);


--
-- Name: ix_north_star_metric_events_event_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_north_star_metric_events_event_type ON north_star_metric_events USING btree (event_type);


--
-- Name: ix_north_star_metric_events_metric_date; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_north_star_metric_events_metric_date ON north_star_metric_events USING btree (metric_date);


--
-- Name: ix_north_star_metric_events_occurred_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_north_star_metric_events_occurred_at ON north_star_metric_events USING btree (occurred_at);


--
-- Name: ix_north_star_metric_events_plan_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_north_star_metric_events_plan_id ON north_star_metric_events USING btree (plan_id);


--
-- Name: ix_north_star_metric_events_source; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_north_star_metric_events_source ON north_star_metric_events USING btree (source);


--
-- Name: ix_north_star_metric_events_task_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_north_star_metric_events_task_id ON north_star_metric_events USING btree (task_id);


--
-- Name: ix_north_star_metric_events_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_north_star_metric_events_user_id ON north_star_metric_events USING btree (user_id);


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
-- Name: ix_occurrences_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_occurrences_deleted_at ON task_occurrences USING btree (deleted_at);


--
-- Name: ix_occurrences_plan_card_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_occurrences_plan_card_id ON task_occurrences USING btree (plan_card_id);


--
-- Name: ix_occurrences_plan_date; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_occurrences_plan_date ON task_occurrences USING btree (plan_card_id, scheduled_for);


--
-- Name: ix_occurrences_scheduled_date; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_occurrences_scheduled_date ON task_occurrences USING btree (scheduled_for, occurrence_status);


--
-- Name: ix_occurrences_scheduled_for; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_occurrences_scheduled_for ON task_occurrences USING btree (scheduled_for);


--
-- Name: ix_occurrences_series_card_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_occurrences_series_card_id ON task_occurrences USING btree (series_card_id);


--
-- Name: ix_occurrences_series_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_occurrences_series_status ON task_occurrences USING btree (series_card_id, occurrence_status);


--
-- Name: ix_occurrences_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_occurrences_status ON task_occurrences USING btree (occurrence_status);


--
-- Name: ix_offline_message_queue_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_offline_message_queue_deleted_at ON offline_message_queue USING btree (deleted_at);


--
-- Name: ix_offline_message_queue_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_offline_message_queue_user_id ON offline_message_queue USING btree (user_id);


--
-- Name: ix_pack_adoption_history_adoption_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_pack_adoption_history_adoption_id ON pack_adoption_history USING btree (adoption_id);


--
-- Name: ix_pack_adoption_history_asset_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_pack_adoption_history_asset_id ON pack_adoption_history USING btree (asset_id);


--
-- Name: ix_pack_adoption_history_asset_trace; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_pack_adoption_history_asset_trace ON pack_adoption_history USING btree (asset_type, asset_id, trace_id);


--
-- Name: ix_pack_adoption_history_asset_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_pack_adoption_history_asset_type ON pack_adoption_history USING btree (asset_type);


--
-- Name: ix_pack_adoption_history_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_pack_adoption_history_deleted_at ON pack_adoption_history USING btree (deleted_at);


--
-- Name: ix_pack_adoption_history_impact_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_pack_adoption_history_impact_type ON pack_adoption_history USING btree (impact_type);


--
-- Name: ix_pack_adoption_history_outcome; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_pack_adoption_history_outcome ON pack_adoption_history USING btree (outcome);


--
-- Name: ix_pack_adoption_history_trace_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_pack_adoption_history_trace_id ON pack_adoption_history USING btree (trace_id);


--
-- Name: ix_pack_adoption_history_user_created; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_pack_adoption_history_user_created ON pack_adoption_history USING btree (user_id, created_at);


--
-- Name: ix_pack_adoption_history_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_pack_adoption_history_user_id ON pack_adoption_history USING btree (user_id);


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
-- Name: ix_privacy_budget_ledger_allowed; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_privacy_budget_ledger_allowed ON privacy_budget_ledger USING btree (allowed);


--
-- Name: ix_privacy_budget_ledger_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_privacy_budget_ledger_deleted_at ON privacy_budget_ledger USING btree (deleted_at);


--
-- Name: ix_privacy_budget_ledger_query_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_privacy_budget_ledger_query_type ON privacy_budget_ledger USING btree (query_type);


--
-- Name: ix_privacy_budget_ledger_spent_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_privacy_budget_ledger_spent_at ON privacy_budget_ledger USING btree (spent_at);


--
-- Name: ix_privacy_budget_ledger_subject_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_privacy_budget_ledger_subject_id ON privacy_budget_ledger USING btree (subject_id);


--
-- Name: ix_privacy_budget_ledger_subject_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_privacy_budget_ledger_subject_type ON privacy_budget_ledger USING btree (subject_type);


--
-- Name: ix_privacy_budget_ledger_window_key; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_privacy_budget_ledger_window_key ON privacy_budget_ledger USING btree (window_key);


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
-- Name: ix_probe_outcomes_claim_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_probe_outcomes_claim_id ON probe_outcomes USING btree (claim_id);


--
-- Name: ix_probe_outcomes_created_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_probe_outcomes_created_at ON probe_outcomes USING btree (created_at);


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
-- Name: ix_release_approval_requests_applied_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_release_approval_requests_applied_at ON release_approval_requests USING btree (applied_at);


--
-- Name: ix_release_approval_requests_applied_by_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_release_approval_requests_applied_by_id ON release_approval_requests USING btree (applied_by_id);


--
-- Name: ix_release_approval_requests_category; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_release_approval_requests_category ON release_approval_requests USING btree (category);


--
-- Name: ix_release_approval_requests_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_release_approval_requests_deleted_at ON release_approval_requests USING btree (deleted_at);


--
-- Name: ix_release_approval_requests_needs_admin_attention; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_release_approval_requests_needs_admin_attention ON release_approval_requests USING btree (needs_admin_attention);


--
-- Name: ix_release_approval_requests_object_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_release_approval_requests_object_id ON release_approval_requests USING btree (object_id);


--
-- Name: ix_release_approval_requests_object_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_release_approval_requests_object_type ON release_approval_requests USING btree (object_type);


--
-- Name: ix_release_approval_requests_requested_by_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_release_approval_requests_requested_by_id ON release_approval_requests USING btree (requested_by_id);


--
-- Name: ix_release_approval_requests_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_release_approval_requests_status ON release_approval_requests USING btree (status);


--
-- Name: ix_release_approval_requests_submitted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_release_approval_requests_submitted_at ON release_approval_requests USING btree (submitted_at);


--
-- Name: ix_report_snapshots_cache_version; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_report_snapshots_cache_version ON report_snapshots USING btree (cache_version);


--
-- Name: ix_report_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_report_snapshots_deleted_at ON report_snapshots USING btree (deleted_at);


--
-- Name: ix_report_snapshots_delivery_mode; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_report_snapshots_delivery_mode ON report_snapshots USING btree (delivery_mode);


--
-- Name: ix_report_snapshots_report_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_report_snapshots_report_id ON report_snapshots USING btree (report_id);


--
-- Name: ix_report_snapshots_snapshot_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_report_snapshots_snapshot_type ON report_snapshots USING btree (snapshot_type);


--
-- Name: ix_report_snapshots_user_cache; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_report_snapshots_user_cache ON report_snapshots USING btree (user_id, cache_version);


--
-- Name: ix_report_snapshots_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_report_snapshots_user_id ON report_snapshots USING btree (user_id);


--
-- Name: ix_research_consent_records_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_research_consent_records_deleted_at ON research_consent_records USING btree (deleted_at);


--
-- Name: ix_research_consent_records_granted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_research_consent_records_granted_at ON research_consent_records USING btree (granted_at);


--
-- Name: ix_research_consent_records_protocol_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_research_consent_records_protocol_id ON research_consent_records USING btree (protocol_id);


--
-- Name: ix_research_consent_records_revoked_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_research_consent_records_revoked_at ON research_consent_records USING btree (revoked_at);


--
-- Name: ix_research_consent_records_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_research_consent_records_user_id ON research_consent_records USING btree (user_id);


--
-- Name: ix_research_consent_user_active; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_research_consent_user_active ON research_consent_records USING btree (user_id, protocol_id, revoked_at);


--
-- Name: ix_research_consent_user_protocol; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_research_consent_user_protocol ON research_consent_records USING btree (user_id, protocol_id);


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
-- Name: ix_safe_experiment_episodes_experiment_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_safe_experiment_episodes_experiment_id ON safe_experiment_episodes USING btree (experiment_id);


--
-- Name: ix_safe_experiment_episodes_experiment_key; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_safe_experiment_episodes_experiment_key ON safe_experiment_episodes USING btree (experiment_key);


--
-- Name: ix_safe_experiment_episodes_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_safe_experiment_episodes_user_id ON safe_experiment_episodes USING btree (user_id);


--
-- Name: ix_safe_experiments_created_by; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_safe_experiments_created_by ON safe_experiments USING btree (created_by);


--
-- Name: ix_safe_experiments_domain; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_safe_experiments_domain ON safe_experiments USING btree (domain);


--
-- Name: ix_safe_experiments_experiment_key; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_safe_experiments_experiment_key ON safe_experiments USING btree (experiment_key);


--
-- Name: ix_safe_experiments_kill_switch_key; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_safe_experiments_kill_switch_key ON safe_experiments USING btree (kill_switch_key);


--
-- Name: ix_safe_experiments_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_safe_experiments_status ON safe_experiments USING btree (status);


--
-- Name: ix_scaffolding_states_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_scaffolding_states_deleted_at ON scaffolding_states USING btree (deleted_at);


--
-- Name: ix_scaffolding_states_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_scaffolding_states_user_id ON scaffolding_states USING btree (user_id);


--
-- Name: ix_scenes_scene_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_scenes_scene_id ON scenes USING btree (scene_id);


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
-- Name: ix_seed_library_ratings_library_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_library_ratings_library_id ON seed_library_ratings USING btree (library_id);


--
-- Name: ix_seed_library_ratings_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seed_library_ratings_user_id ON seed_library_ratings USING btree (user_id);


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
-- Name: ix_session_completions_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_session_completions_user_id ON session_completions USING btree (user_id);


--
-- Name: ix_session_completions_user_id_created_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_session_completions_user_id_created_at ON session_completions USING btree (user_id, created_at);


--
-- Name: ix_shared_resources_card_share_record_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shared_resources_card_share_record_id ON shared_resources USING btree (card_share_record_id);


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
-- Name: ix_shared_skills_share_slug; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_shared_skills_share_slug ON shared_skills USING btree (share_slug);


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
-- Name: ix_simulation_runs_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_simulation_runs_deleted_at ON simulation_runs USING btree (deleted_at);


--
-- Name: ix_simulation_runs_last_active_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_simulation_runs_last_active_at ON simulation_runs USING btree (last_active_at);


--
-- Name: ix_simulation_runs_scenario_key; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_simulation_runs_scenario_key ON simulation_runs USING btree (scenario_key);


--
-- Name: ix_simulation_runs_session_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_simulation_runs_session_id ON simulation_runs USING btree (session_id);


--
-- Name: ix_simulation_runs_state; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_simulation_runs_state ON simulation_runs USING btree (state);


--
-- Name: ix_simulation_runs_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_simulation_runs_user_id ON simulation_runs USING btree (user_id);


--
-- Name: ix_simulation_runs_user_last_active; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_simulation_runs_user_last_active ON simulation_runs USING btree (user_id, last_active_at);


--
-- Name: ix_skill_share_moderation_queue_user_skill_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_skill_share_moderation_queue_user_skill_id ON skill_share_moderation_queue USING btree (user_skill_id);


--
-- Name: ix_spark_contracts_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_spark_contracts_deleted_at ON spark_contracts USING btree (deleted_at);


--
-- Name: ix_srl_phase_states_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_srl_phase_states_deleted_at ON srl_phase_states USING btree (deleted_at);


--
-- Name: ix_srl_phase_states_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_srl_phase_states_user_id ON srl_phase_states USING btree (user_id);


--
-- Name: ix_stored_files_archive_review_due_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_archive_review_due_at ON stored_files USING btree (archive_review_due_at);


--
-- Name: ix_stored_files_archived_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_archived_at ON stored_files USING btree (archived_at);


--
-- Name: ix_stored_files_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_deleted_at ON stored_files USING btree (deleted_at);


--
-- Name: ix_stored_files_lifecycle_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_lifecycle_status ON stored_files USING btree (lifecycle_status);


--
-- Name: ix_stored_files_orphaned_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_orphaned_at ON stored_files USING btree (orphaned_at);


--
-- Name: ix_stored_files_revoked_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_revoked_at ON stored_files USING btree (revoked_at);


--
-- Name: ix_stored_files_source_file_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_source_file_id ON stored_files USING btree (source_file_id);


--
-- Name: ix_stored_files_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_user_id ON stored_files USING btree (user_id);


--
-- Name: ix_strategy_belief_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_strategy_belief_snapshots_deleted_at ON strategy_belief_snapshots USING btree (deleted_at);


--
-- Name: ix_strategy_belief_snapshots_strategy_key; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_strategy_belief_snapshots_strategy_key ON strategy_belief_snapshots USING btree (strategy_key);


--
-- Name: ix_strategy_belief_snapshots_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_strategy_belief_snapshots_user_id ON strategy_belief_snapshots USING btree (user_id);


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
-- Name: ix_strategy_outcomes_user_trigger; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_strategy_outcomes_user_trigger ON intervention_strategy_outcomes USING btree (user_id, trigger_type);


--
-- Name: ix_strategy_outcomes_user_trigger_tone; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_strategy_outcomes_user_trigger_tone ON intervention_strategy_outcomes USING btree (user_id, trigger_type, delivery_tone);


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
-- Name: ix_task_documents_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_task_documents_deleted_at ON task_documents USING btree (deleted_at);


--
-- Name: ix_task_documents_file_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_task_documents_file_id ON task_documents USING btree (file_id);


--
-- Name: ix_task_documents_task_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_task_documents_task_id ON task_documents USING btree (task_id);


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
-- Name: ix_tasks_source_planning_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_source_planning_session_id ON tasks USING btree (source_planning_session_id);


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
-- Name: ix_tdr_created_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_tdr_created_at ON transition_decision_records USING btree (created_at);


--
-- Name: ix_tdr_input_snapshot_ref; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_tdr_input_snapshot_ref ON transition_decision_records USING btree (input_snapshot_ref);


--
-- Name: ix_tdr_policy_version; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_tdr_policy_version ON transition_decision_records USING btree (policy_version);


--
-- Name: ix_tdr_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_tdr_user_id ON transition_decision_records USING btree (user_id);


--
-- Name: ix_theater_candidate_bundles_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_candidate_bundles_deleted_at ON theater_candidate_bundles USING btree (deleted_at);


--
-- Name: ix_theater_candidate_bundles_prediction_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_candidate_bundles_prediction_id ON theater_candidate_bundles USING btree (prediction_id);


--
-- Name: ix_theater_candidate_bundles_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_candidate_bundles_status ON theater_candidate_bundles USING btree (status);


--
-- Name: ix_theater_candidate_bundles_target_resolution_mode; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_candidate_bundles_target_resolution_mode ON theater_candidate_bundles USING btree (target_resolution_mode);


--
-- Name: ix_theater_candidate_bundles_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_candidate_bundles_user_id ON theater_candidate_bundles USING btree (user_id);


--
-- Name: ix_theater_predictions_accuracy_due_on; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_predictions_accuracy_due_on ON theater_predictions USING btree (accuracy_due_on);


--
-- Name: ix_theater_predictions_accuracy_pending; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_predictions_accuracy_pending ON theater_predictions USING btree (accuracy_status, accuracy_due_on);


--
-- Name: ix_theater_predictions_accuracy_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_predictions_accuracy_status ON theater_predictions USING btree (accuracy_status);


--
-- Name: ix_theater_predictions_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_predictions_deleted_at ON theater_predictions USING btree (deleted_at);


--
-- Name: ix_theater_predictions_generated_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_predictions_generated_at ON theater_predictions USING btree (generated_at);


--
-- Name: ix_theater_predictions_prediction_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_predictions_prediction_id ON theater_predictions USING btree (prediction_id);


--
-- Name: ix_theater_predictions_target_resolution_mode; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_predictions_target_resolution_mode ON theater_predictions USING btree (target_resolution_mode);


--
-- Name: ix_theater_predictions_user_generated; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_predictions_user_generated ON theater_predictions USING btree (user_id, generated_at DESC);


--
-- Name: ix_theater_predictions_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_theater_predictions_user_id ON theater_predictions USING btree (user_id);


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
-- Name: ix_user_learning_profiles_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_learning_profiles_deleted_at ON user_learning_profiles USING btree (deleted_at);


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
-- Name: ix_user_scenario_states_current_node; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_user_scenario_states_current_node ON user_scenario_states USING btree (current_node);


--
-- Name: ix_user_scenario_states_pack_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_user_scenario_states_pack_id ON user_scenario_states USING btree (pack_id);


--
-- Name: ix_user_scenario_states_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX ix_user_scenario_states_user_id ON user_scenario_states USING btree (user_id);


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
-- Name: ix_user_similarities_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_similarities_deleted_at ON user_similarities USING btree (deleted_at);


--
-- Name: ix_user_skill_adoptions_asset_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_user_skill_adoptions_asset_id ON user_skill_adoptions USING btree (asset_id);


--
-- Name: ix_user_skill_adoptions_asset_type; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_user_skill_adoptions_asset_type ON user_skill_adoptions USING btree (asset_type);


--
-- Name: ix_user_skill_adoptions_deleted_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_user_skill_adoptions_deleted_at ON user_skill_adoptions USING btree (deleted_at);


--
-- Name: ix_user_skill_adoptions_status; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_user_skill_adoptions_status ON user_skill_adoptions USING btree (status);


--
-- Name: ix_user_skill_adoptions_trace_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_user_skill_adoptions_trace_id ON user_skill_adoptions USING btree (trace_id);


--
-- Name: ix_user_skill_adoptions_user_asset; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_user_skill_adoptions_user_asset ON user_skill_adoptions USING btree (user_id, asset_type, asset_id);


--
-- Name: ix_user_skill_adoptions_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_user_skill_adoptions_user_id ON user_skill_adoptions USING btree (user_id);


--
-- Name: ix_user_skills_forked_from_share_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_user_skills_forked_from_share_id ON user_skills USING btree (forked_from_share_id);


--
-- Name: ix_user_skills_shared_catalog_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_user_skills_shared_catalog_id ON user_skills USING btree (shared_catalog_id);


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
-- Name: ix_users_apple_id_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_apple_id_hash ON users USING btree (apple_id_hash);


--
-- Name: ix_users_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_deleted_at ON users USING btree (deleted_at);


--
-- Name: ix_users_email_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_email_hash ON users USING btree (email_hash);


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
-- Name: ix_users_google_id_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_google_id_hash ON users USING btree (google_id_hash);


--
-- Name: ix_users_username_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_username_hash ON users USING btree (username_hash);


--
-- Name: ix_users_wechat_unionid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_wechat_unionid ON users USING btree (wechat_unionid);


--
-- Name: ix_users_wechat_unionid_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_wechat_unionid_hash ON users USING btree (wechat_unionid_hash);


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
-- Name: ix_window_states_created_at; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_window_states_created_at ON window_states USING btree (created_at);


--
-- Name: ix_window_states_trigger_decision_ref; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_window_states_trigger_decision_ref ON window_states USING btree (trigger_decision_ref);


--
-- Name: ix_window_states_user_id; Type: INDEX; Schema: public; Owner: brsama
--

CREATE INDEX ix_window_states_user_id ON window_states USING btree (user_id);


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
-- Name: uq_aurora_policy_versions_version; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX uq_aurora_policy_versions_version ON aurora_policy_versions USING btree (version);


--
-- Name: uq_execution_intents_active_task; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_execution_intents_active_task ON execution_intents USING btree (user_id, task_id) WHERE ((deleted_at IS NULL) AND ((status)::text = ANY ((ARRAY['draft'::character varying, 'ready'::character varying, 'dispatched'::character varying, 'running'::character varying, 'waiting_approval'::character varying])::text[])));


--
-- Name: uq_memory_preferences_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_memory_preferences_version ON memory_preferences USING btree (user_id, pref_key, version);


--
-- Name: uq_memory_rank_policies_scope; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_memory_rank_policies_scope ON memory_rank_policies USING btree (scope_type, scope_key);


--
-- Name: uq_research_consent_active_protocol; Type: INDEX; Schema: public; Owner: brsama
--

CREATE UNIQUE INDEX uq_research_consent_active_protocol ON research_consent_records USING btree (user_id, protocol_id) WHERE (revoked_at IS NULL);


--
-- Name: admin_audit_log trg_admin_audit_log_prevent_mutation; Type: TRIGGER; Schema: public; Owner: brsama
--

CREATE TRIGGER trg_admin_audit_log_prevent_mutation BEFORE DELETE OR UPDATE ON admin_audit_log FOR EACH ROW EXECUTE FUNCTION admin_audit_log_prevent_mutation();


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
-- Name: accountability_checkin accountability_checkin_partnership_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY accountability_checkin
    ADD CONSTRAINT accountability_checkin_partnership_id_fkey FOREIGN KEY (partnership_id) REFERENCES accountability_partnership(id) ON DELETE CASCADE;


--
-- Name: accountability_checkin accountability_checkin_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY accountability_checkin
    ADD CONSTRAINT accountability_checkin_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: accountability_partnership accountability_partnership_friendship_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY accountability_partnership
    ADD CONSTRAINT accountability_partnership_friendship_id_fkey FOREIGN KEY (friendship_id) REFERENCES friendships(id) ON DELETE SET NULL;


--
-- Name: accountability_partnership accountability_partnership_initiator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY accountability_partnership
    ADD CONSTRAINT accountability_partnership_initiator_id_fkey FOREIGN KEY (initiator_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: accountability_partnership accountability_partnership_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY accountability_partnership
    ADD CONSTRAINT accountability_partnership_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: accountability_policies accountability_policies_commitment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY accountability_policies
    ADD CONSTRAINT accountability_policies_commitment_id_fkey FOREIGN KEY (commitment_id) REFERENCES episodic_memories(id) ON DELETE CASCADE;


--
-- Name: accountability_policies accountability_policies_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY accountability_policies
    ADD CONSTRAINT accountability_policies_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: achievements achievements_first_unlocker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY achievements
    ADD CONSTRAINT achievements_first_unlocker_id_fkey FOREIGN KEY (first_unlocker_id) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: achievements achievements_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY achievements
    ADD CONSTRAINT achievements_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES achievements(id) ON DELETE SET NULL;


--
-- Name: admin_audit_log admin_audit_log_admin_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY admin_audit_log
    ADD CONSTRAINT admin_audit_log_admin_user_id_fkey FOREIGN KEY (admin_user_id) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: asset_suggestion_logs asset_suggestion_logs_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY asset_suggestion_logs
    ADD CONSTRAINT asset_suggestion_logs_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES learning_assets(id) ON DELETE SET NULL;


--
-- Name: asset_suggestion_logs asset_suggestion_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY asset_suggestion_logs
    ADD CONSTRAINT asset_suggestion_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: aurora_decision_telemetry aurora_decision_telemetry_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_decision_telemetry
    ADD CONSTRAINT aurora_decision_telemetry_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: aurora_judgment_records aurora_judgment_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_judgment_records
    ADD CONSTRAINT aurora_judgment_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: aurora_scheduled_wakes aurora_scheduled_wakes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_scheduled_wakes
    ADD CONSTRAINT aurora_scheduled_wakes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: aurora_state_snapshots aurora_state_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY aurora_state_snapshots
    ADD CONSTRAINT aurora_state_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: auth_audit_log auth_audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY auth_audit_log
    ADD CONSTRAINT auth_audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: behavior_patterns behavior_patterns_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY behavior_patterns
    ADD CONSTRAINT behavior_patterns_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: candidate_action_feedback candidate_action_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY candidate_action_feedback
    ADD CONSTRAINT candidate_action_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: card_adoption_records card_adoption_records_adopted_root_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_adoption_records
    ADD CONSTRAINT card_adoption_records_adopted_root_card_id_fkey FOREIGN KEY (adopted_root_card_id) REFERENCES cards(id) ON DELETE SET NULL;


--
-- Name: card_adoption_records card_adoption_records_adopter_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_adoption_records
    ADD CONSTRAINT card_adoption_records_adopter_user_id_fkey FOREIGN KEY (adopter_user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: card_adoption_records card_adoption_records_share_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_adoption_records
    ADD CONSTRAINT card_adoption_records_share_record_id_fkey FOREIGN KEY (share_record_id) REFERENCES card_share_records(id) ON DELETE CASCADE;


--
-- Name: card_edges card_edges_from_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_edges
    ADD CONSTRAINT card_edges_from_card_id_fkey FOREIGN KEY (from_card_id) REFERENCES cards(id) ON DELETE CASCADE;


--
-- Name: card_edges card_edges_to_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_edges
    ADD CONSTRAINT card_edges_to_card_id_fkey FOREIGN KEY (to_card_id) REFERENCES cards(id) ON DELETE CASCADE;


--
-- Name: card_share_records card_share_records_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_share_records
    ADD CONSTRAINT card_share_records_group_id_fkey FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE;


--
-- Name: card_share_records card_share_records_root_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_share_records
    ADD CONSTRAINT card_share_records_root_card_id_fkey FOREIGN KEY (root_card_id) REFERENCES cards(id) ON DELETE SET NULL;


--
-- Name: card_share_records card_share_records_shared_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_share_records
    ADD CONSTRAINT card_share_records_shared_by_user_id_fkey FOREIGN KEY (shared_by_user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: card_share_records card_share_records_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_share_records
    ADD CONSTRAINT card_share_records_snapshot_id_fkey FOREIGN KEY (snapshot_id) REFERENCES card_snapshots(id) ON DELETE CASCADE;


--
-- Name: card_share_records card_share_records_target_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_share_records
    ADD CONSTRAINT card_share_records_target_user_id_fkey FOREIGN KEY (target_user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: card_snapshots card_snapshots_root_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_snapshots
    ADD CONSTRAINT card_snapshots_root_card_id_fkey FOREIGN KEY (root_card_id) REFERENCES cards(id) ON DELETE SET NULL;


--
-- Name: card_snapshots card_snapshots_source_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY card_snapshots
    ADD CONSTRAINT card_snapshots_source_owner_id_fkey FOREIGN KEY (source_owner_id) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: cards cards_holder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY cards
    ADD CONSTRAINT cards_holder_id_fkey FOREIGN KEY (holder_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: cards cards_origin_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY cards
    ADD CONSTRAINT cards_origin_card_id_fkey FOREIGN KEY (origin_card_id) REFERENCES cards(id) ON DELETE SET NULL;


--
-- Name: cards cards_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY cards
    ADD CONSTRAINT cards_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages
    ADD CONSTRAINT chat_messages_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages
    ADD CONSTRAINT chat_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: chat_sessions chat_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_sessions
    ADD CONSTRAINT chat_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: cognitive_fragments cognitive_fragments_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cognitive_fragments
    ADD CONSTRAINT cognitive_fragments_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL;


--
-- Name: cognitive_fragments cognitive_fragments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cognitive_fragments
    ADD CONSTRAINT cognitive_fragments_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: commitments commitments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY commitments
    ADD CONSTRAINT commitments_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: compliance_check_logs compliance_check_logs_executed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY compliance_check_logs
    ADD CONSTRAINT compliance_check_logs_executed_by_fkey FOREIGN KEY (executed_by) REFERENCES users(id);


--
-- Name: conflict_resolution_records conflict_resolution_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY conflict_resolution_records
    ADD CONSTRAINT conflict_resolution_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: counterfactual_evaluation_reports counterfactual_evaluation_reports_replaced_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY counterfactual_evaluation_reports
    ADD CONSTRAINT counterfactual_evaluation_reports_replaced_by_id_fkey FOREIGN KEY (replaced_by_id) REFERENCES counterfactual_evaluation_reports(id) ON DELETE SET NULL;


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
    ADD CONSTRAINT curiosity_capsules_related_task_id_fkey FOREIGN KEY (related_task_id) REFERENCES tasks(id) ON DELETE SET NULL;


--
-- Name: curiosity_capsules curiosity_capsules_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY curiosity_capsules
    ADD CONSTRAINT curiosity_capsules_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: custom_expert_profiles custom_expert_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY custom_expert_profiles
    ADD CONSTRAINT custom_expert_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: custom_expert_teams custom_expert_teams_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY custom_expert_teams
    ADD CONSTRAINT custom_expert_teams_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: daily_behavior_vector daily_behavior_vector_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY daily_behavior_vector
    ADD CONSTRAINT daily_behavior_vector_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: document_retrieval_feedback document_retrieval_feedback_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY document_retrieval_feedback
    ADD CONSTRAINT document_retrieval_feedback_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES document_chunks(id) ON DELETE SET NULL;


--
-- Name: document_retrieval_feedback document_retrieval_feedback_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY document_retrieval_feedback
    ADD CONSTRAINT document_retrieval_feedback_file_id_fkey FOREIGN KEY (file_id) REFERENCES stored_files(id) ON DELETE CASCADE;


--
-- Name: document_retrieval_feedback document_retrieval_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY document_retrieval_feedback
    ADD CONSTRAINT document_retrieval_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: episodic_memories episodic_memories_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY episodic_memories
    ADD CONSTRAINT episodic_memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: error_records error_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY error_records
    ADD CONSTRAINT error_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: execution_audit_log execution_audit_log_intent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY execution_audit_log
    ADD CONSTRAINT execution_audit_log_intent_id_fkey FOREIGN KEY (intent_id) REFERENCES execution_intents(id) ON DELETE CASCADE;


--
-- Name: execution_audit_log execution_audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY execution_audit_log
    ADD CONSTRAINT execution_audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: execution_intents execution_intents_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY execution_intents
    ADD CONSTRAINT execution_intents_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE SET NULL;


--
-- Name: execution_intents execution_intents_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY execution_intents
    ADD CONSTRAINT execution_intents_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;


--
-- Name: execution_intents execution_intents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY execution_intents
    ADD CONSTRAINT execution_intents_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: execution_records execution_records_execution_intent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY execution_records
    ADD CONSTRAINT execution_records_execution_intent_id_fkey FOREIGN KEY (execution_intent_id) REFERENCES execution_intents(id) ON DELETE CASCADE;


--
-- Name: execution_records execution_records_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY execution_records
    ADD CONSTRAINT execution_records_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL;


--
-- Name: execution_records execution_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY execution_records
    ADD CONSTRAINT execution_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: execution_schedules execution_schedules_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY execution_schedules
    ADD CONSTRAINT execution_schedules_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;


--
-- Name: execution_schedules execution_schedules_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY execution_schedules
    ADD CONSTRAINT execution_schedules_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: collaborative_galaxies fk_collaborative_galaxies_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY collaborative_galaxies
    ADD CONSTRAINT fk_collaborative_galaxies_group_id FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE;


--
-- Name: plans fk_plans_goal_id_goals; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plans
    ADD CONSTRAINT fk_plans_goal_id_goals FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL;


--
-- Name: shared_resources fk_shared_resources_card_share_record_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT fk_shared_resources_card_share_record_id FOREIGN KEY (card_share_record_id) REFERENCES card_share_records(id) ON DELETE SET NULL;


--
-- Name: shared_resources fk_shared_resources_seed_item_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT fk_shared_resources_seed_item_id FOREIGN KEY (seed_item_id) REFERENCES seed_items(id);


--
-- Name: shared_resources fk_shared_resources_seed_library_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY shared_resources
    ADD CONSTRAINT fk_shared_resources_seed_library_id FOREIGN KEY (seed_library_id) REFERENCES seed_libraries(id);


--
-- Name: stored_files fk_stored_files_source_file_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY stored_files
    ADD CONSTRAINT fk_stored_files_source_file_id FOREIGN KEY (source_file_id) REFERENCES stored_files(id) ON DELETE SET NULL;


--
-- Name: subtasks fk_subtasks_knowledge_node_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY subtasks
    ADD CONSTRAINT fk_subtasks_knowledge_node_id FOREIGN KEY (knowledge_node_id) REFERENCES knowledge_nodes(id) ON DELETE SET NULL;


--
-- Name: focus_contracts focus_contracts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY focus_contracts
    ADD CONSTRAINT focus_contracts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: focus_sessions focus_sessions_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY focus_sessions
    ADD CONSTRAINT focus_sessions_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL;


--
-- Name: focus_sessions focus_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY focus_sessions
    ADD CONSTRAINT focus_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: goals goals_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY goals
    ADD CONSTRAINT goals_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES plans(id);


--
-- Name: goals goals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY goals
    ADD CONSTRAINT goals_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


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
-- Name: identity_evidence identity_evidence_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY identity_evidence
    ADD CONSTRAINT identity_evidence_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: idiographic_associations idiographic_associations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY idiographic_associations
    ADD CONSTRAINT idiographic_associations_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: idiographic_changepoints idiographic_changepoints_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY idiographic_changepoints
    ADD CONSTRAINT idiographic_changepoints_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: insight_claims insight_claims_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY insight_claims
    ADD CONSTRAINT insight_claims_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: intervention_records intervention_records_knowledge_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY intervention_records
    ADD CONSTRAINT intervention_records_knowledge_card_id_fkey FOREIGN KEY (knowledge_card_id) REFERENCES cards(id) ON DELETE SET NULL;


--
-- Name: intervention_records intervention_records_phase_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY intervention_records
    ADD CONSTRAINT intervention_records_phase_card_id_fkey FOREIGN KEY (phase_card_id) REFERENCES cards(id) ON DELETE SET NULL;


--
-- Name: intervention_records intervention_records_plan_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY intervention_records
    ADD CONSTRAINT intervention_records_plan_card_id_fkey FOREIGN KEY (plan_card_id) REFERENCES cards(id) ON DELETE SET NULL;


--
-- Name: intervention_records intervention_records_task_occurrence_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY intervention_records
    ADD CONSTRAINT intervention_records_task_occurrence_id_fkey FOREIGN KEY (task_occurrence_id) REFERENCES task_occurrences(id) ON DELETE SET NULL;


--
-- Name: intervention_records intervention_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY intervention_records
    ADD CONSTRAINT intervention_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: intervention_requests intervention_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intervention_requests
    ADD CONSTRAINT intervention_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: intervention_strategy_outcomes intervention_strategy_outcomes_intervention_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY intervention_strategy_outcomes
    ADD CONSTRAINT intervention_strategy_outcomes_intervention_id_fkey FOREIGN KEY (intervention_id) REFERENCES intervention_records(id) ON DELETE CASCADE;


--
-- Name: intervention_strategy_outcomes intervention_strategy_outcomes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY intervention_strategy_outcomes
    ADD CONSTRAINT intervention_strategy_outcomes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: jobs jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: knowledge_node_documents knowledge_node_documents_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY knowledge_node_documents
    ADD CONSTRAINT knowledge_node_documents_file_id_fkey FOREIGN KEY (file_id) REFERENCES stored_files(id) ON DELETE CASCADE;


--
-- Name: knowledge_node_documents knowledge_node_documents_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY knowledge_node_documents
    ADD CONSTRAINT knowledge_node_documents_node_id_fkey FOREIGN KEY (node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE;


--
-- Name: knowledge_node_documents knowledge_node_documents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY knowledge_node_documents
    ADD CONSTRAINT knowledge_node_documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: learning_assets learning_assets_source_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY learning_assets
    ADD CONSTRAINT learning_assets_source_file_id_fkey FOREIGN KEY (source_file_id) REFERENCES stored_files(id) ON DELETE SET NULL;


--
-- Name: learning_assets learning_assets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY learning_assets
    ADD CONSTRAINT learning_assets_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: marketplace_packs marketplace_packs_rollback_of_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY marketplace_packs
    ADD CONSTRAINT marketplace_packs_rollback_of_id_fkey FOREIGN KEY (rollback_of_id) REFERENCES marketplace_packs(id) ON DELETE SET NULL;


--
-- Name: marketplace_skills marketplace_skills_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY marketplace_skills
    ADD CONSTRAINT marketplace_skills_author_id_fkey FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: marketplace_skills marketplace_skills_rollback_of_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY marketplace_skills
    ADD CONSTRAINT marketplace_skills_rollback_of_id_fkey FOREIGN KEY (rollback_of_id) REFERENCES marketplace_skills(id) ON DELETE SET NULL;


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
    ADD CONSTRAINT memory_corrections_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: memory_goals memory_goals_linked_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_goals
    ADD CONSTRAINT memory_goals_linked_plan_id_fkey FOREIGN KEY (linked_plan_id) REFERENCES plans(id) ON DELETE SET NULL;


--
-- Name: memory_goals memory_goals_linked_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_goals
    ADD CONSTRAINT memory_goals_linked_task_id_fkey FOREIGN KEY (linked_task_id) REFERENCES tasks(id) ON DELETE SET NULL;


--
-- Name: memory_goals memory_goals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_goals
    ADD CONSTRAINT memory_goals_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: memory_preferences memory_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY memory_preferences
    ADD CONSTRAINT memory_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
    ADD CONSTRAINT nightly_reviews_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: north_star_metric_events north_star_metric_events_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY north_star_metric_events
    ADD CONSTRAINT north_star_metric_events_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE SET NULL;


--
-- Name: north_star_metric_events north_star_metric_events_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY north_star_metric_events
    ADD CONSTRAINT north_star_metric_events_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL;


--
-- Name: north_star_metric_events north_star_metric_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY north_star_metric_events
    ADD CONSTRAINT north_star_metric_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: pack_adoption_history pack_adoption_history_adoption_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY pack_adoption_history
    ADD CONSTRAINT pack_adoption_history_adoption_id_fkey FOREIGN KEY (adoption_id) REFERENCES user_skill_adoptions(id) ON DELETE CASCADE;


--
-- Name: pack_adoption_history pack_adoption_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY pack_adoption_history
    ADD CONSTRAINT pack_adoption_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: persdyn_attractors persdyn_attractors_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY persdyn_attractors
    ADD CONSTRAINT persdyn_attractors_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


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
-- Name: planning_artifacts planning_artifacts_approved_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY planning_artifacts
    ADD CONSTRAINT planning_artifacts_approved_by_user_id_fkey FOREIGN KEY (approved_by_user_id) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: planning_artifacts planning_artifacts_plan_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY planning_artifacts
    ADD CONSTRAINT planning_artifacts_plan_card_id_fkey FOREIGN KEY (plan_card_id) REFERENCES cards(id) ON DELETE CASCADE;


--
-- Name: plans plans_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plans
    ADD CONSTRAINT plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: probe_outcomes probe_outcomes_claim_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY probe_outcomes
    ADD CONSTRAINT probe_outcomes_claim_id_fkey FOREIGN KEY (claim_id) REFERENCES insight_claims(id) ON DELETE CASCADE;


--
-- Name: push_delivery_records push_delivery_records_notification_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY push_delivery_records
    ADD CONSTRAINT push_delivery_records_notification_id_fkey FOREIGN KEY (notification_id) REFERENCES notifications(id);


--
-- Name: push_delivery_records push_delivery_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY push_delivery_records
    ADD CONSTRAINT push_delivery_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


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
-- Name: release_approval_requests release_approval_requests_applied_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY release_approval_requests
    ADD CONSTRAINT release_approval_requests_applied_by_id_fkey FOREIGN KEY (applied_by_id) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: release_approval_requests release_approval_requests_requested_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY release_approval_requests
    ADD CONSTRAINT release_approval_requests_requested_by_id_fkey FOREIGN KEY (requested_by_id) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: report_snapshots report_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY report_snapshots
    ADD CONSTRAINT report_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: routing_decision_log routing_decision_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY routing_decision_log
    ADD CONSTRAINT routing_decision_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: safe_experiment_episodes safe_experiment_episodes_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY safe_experiment_episodes
    ADD CONSTRAINT safe_experiment_episodes_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES safe_experiments(id) ON DELETE CASCADE;


--
-- Name: safe_experiment_episodes safe_experiment_episodes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY safe_experiment_episodes
    ADD CONSTRAINT safe_experiment_episodes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: safe_experiments safe_experiments_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY safe_experiments
    ADD CONSTRAINT safe_experiments_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;


--
-- Name: scaffolding_states scaffolding_states_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY scaffolding_states
    ADD CONSTRAINT scaffolding_states_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: scenes scenes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY scenes
    ADD CONSTRAINT scenes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


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
-- Name: seed_library_ratings seed_library_ratings_library_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY seed_library_ratings
    ADD CONSTRAINT seed_library_ratings_library_id_fkey FOREIGN KEY (library_id) REFERENCES seed_libraries(id) ON DELETE CASCADE;


--
-- Name: seed_library_ratings seed_library_ratings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY seed_library_ratings
    ADD CONSTRAINT seed_library_ratings_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: session_completions session_completions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY session_completions
    ADD CONSTRAINT session_completions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: simulation_runs simulation_runs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY simulation_runs
    ADD CONSTRAINT simulation_runs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: skill_share_moderation_queue skill_share_moderation_queue_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY skill_share_moderation_queue
    ADD CONSTRAINT skill_share_moderation_queue_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES users(id);


--
-- Name: spark_contracts spark_contracts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY spark_contracts
    ADD CONSTRAINT spark_contracts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: srl_phase_states srl_phase_states_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY srl_phase_states
    ADD CONSTRAINT srl_phase_states_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: task_documents task_documents_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY task_documents
    ADD CONSTRAINT task_documents_file_id_fkey FOREIGN KEY (file_id) REFERENCES stored_files(id) ON DELETE CASCADE;


--
-- Name: task_documents task_documents_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY task_documents
    ADD CONSTRAINT task_documents_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;


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
-- Name: task_occurrences task_occurrences_phase_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY task_occurrences
    ADD CONSTRAINT task_occurrences_phase_card_id_fkey FOREIGN KEY (phase_card_id) REFERENCES cards(id) ON DELETE SET NULL;


--
-- Name: task_occurrences task_occurrences_plan_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY task_occurrences
    ADD CONSTRAINT task_occurrences_plan_card_id_fkey FOREIGN KEY (plan_card_id) REFERENCES cards(id) ON DELETE SET NULL;


--
-- Name: task_occurrences task_occurrences_series_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY task_occurrences
    ADD CONSTRAINT task_occurrences_series_card_id_fkey FOREIGN KEY (series_card_id) REFERENCES cards(id) ON DELETE CASCADE;


--
-- Name: task_resource_links task_resource_links_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_resource_links
    ADD CONSTRAINT task_resource_links_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_knowledge_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tasks
    ADD CONSTRAINT tasks_knowledge_node_id_fkey FOREIGN KEY (knowledge_node_id) REFERENCES knowledge_nodes(id) ON DELETE SET NULL;


--
-- Name: tasks tasks_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tasks
    ADD CONSTRAINT tasks_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tasks
    ADD CONSTRAINT tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: theater_candidate_bundles theater_candidate_bundles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY theater_candidate_bundles
    ADD CONSTRAINT theater_candidate_bundles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: theater_predictions theater_predictions_candidate_bundle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY theater_predictions
    ADD CONSTRAINT theater_predictions_candidate_bundle_id_fkey FOREIGN KEY (candidate_bundle_id) REFERENCES theater_candidate_bundles(id) ON DELETE SET NULL;


--
-- Name: theater_predictions theater_predictions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY theater_predictions
    ADD CONSTRAINT theater_predictions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: transition_decision_records transition_decision_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY transition_decision_records
    ADD CONSTRAINT transition_decision_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: unresolved_conflicts unresolved_conflicts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY unresolved_conflicts
    ADD CONSTRAINT unresolved_conflicts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_achievements user_achievements_achievement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_achievements
    ADD CONSTRAINT user_achievements_achievement_id_fkey FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE;


--
-- Name: user_achievements user_achievements_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_achievements
    ADD CONSTRAINT user_achievements_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
    ADD CONSTRAINT user_devices_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_encryption_keys user_encryption_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_encryption_keys
    ADD CONSTRAINT user_encryption_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_galaxy_skins user_galaxy_skins_skin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_galaxy_skins
    ADD CONSTRAINT user_galaxy_skins_skin_id_fkey FOREIGN KEY (skin_id) REFERENCES galaxy_skins(id) ON DELETE CASCADE;


--
-- Name: user_galaxy_skins user_galaxy_skins_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_galaxy_skins
    ADD CONSTRAINT user_galaxy_skins_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: user_learning_profiles user_learning_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_learning_profiles
    ADD CONSTRAINT user_learning_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


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
    ADD CONSTRAINT user_memory_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
    ADD CONSTRAINT user_preferences_center_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_push_opt_in user_push_opt_in_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY user_push_opt_in
    ADD CONSTRAINT user_push_opt_in_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_scenario_states user_scenario_states_current_focus_contract_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY user_scenario_states
    ADD CONSTRAINT user_scenario_states_current_focus_contract_id_fkey FOREIGN KEY (current_focus_contract_id) REFERENCES focus_contracts(id) ON DELETE RESTRICT;


--
-- Name: user_scenario_states user_scenario_states_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY user_scenario_states
    ADD CONSTRAINT user_scenario_states_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_settings user_settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_settings
    ADD CONSTRAINT user_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_similarities user_similarities_user_id_1_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_similarities
    ADD CONSTRAINT user_similarities_user_id_1_fkey FOREIGN KEY (user_id_1) REFERENCES users(id);


--
-- Name: user_similarities user_similarities_user_id_2_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_similarities
    ADD CONSTRAINT user_similarities_user_id_2_fkey FOREIGN KEY (user_id_2) REFERENCES users(id);


--
-- Name: user_skill_adoptions user_skill_adoptions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY user_skill_adoptions
    ADD CONSTRAINT user_skill_adoptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_skills user_skills_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY user_skills
    ADD CONSTRAINT user_skills_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


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
    ADD CONSTRAINT user_streak_stats_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: user_titles user_titles_source_achievement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_titles
    ADD CONSTRAINT user_titles_source_achievement_id_fkey FOREIGN KEY (source_achievement_id) REFERENCES achievements(id) ON DELETE SET NULL;


--
-- Name: user_titles user_titles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_titles
    ADD CONSTRAINT user_titles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: window_states window_states_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brsama
--

ALTER TABLE ONLY window_states
    ADD CONSTRAINT window_states_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: admin_audit_log; Type: ROW SECURITY; Schema: public; Owner: brsama
--

ALTER TABLE admin_audit_log ENABLE ROW LEVEL SECURITY;

--
-- Name: admin_audit_log admin_audit_log_insert_only; Type: POLICY; Schema: public; Owner: brsama
--

CREATE POLICY admin_audit_log_insert_only ON admin_audit_log FOR INSERT WITH CHECK (true);


--
-- Name: admin_audit_log admin_audit_log_select_only; Type: POLICY; Schema: public; Owner: brsama
--

CREATE POLICY admin_audit_log_select_only ON admin_audit_log FOR SELECT USING (true);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT USAGE ON SCHEMA public TO sparkle_gateway;
GRANT USAGE ON SCHEMA public TO sparkle_engine;
GRANT USAGE ON SCHEMA public TO sparkle_celery;
GRANT USAGE ON SCHEMA public TO sparkle_readonly;


--
-- Name: SCHEMA sparkle_galaxy; Type: ACL; Schema: -; Owner: postgres
--

GRANT USAGE ON SCHEMA sparkle_galaxy TO sparkle_engine;
GRANT USAGE ON SCHEMA sparkle_galaxy TO sparkle_celery;
GRANT USAGE ON SCHEMA sparkle_galaxy TO sparkle_readonly;


--
-- Name: TABLE ab_experiment_assignments; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ab_experiment_assignments TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ab_experiment_assignments TO sparkle_celery;
GRANT SELECT ON TABLE ab_experiment_assignments TO sparkle_readonly;


--
-- Name: TABLE ab_experiment_metrics; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ab_experiment_metrics TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ab_experiment_metrics TO sparkle_celery;
GRANT SELECT ON TABLE ab_experiment_metrics TO sparkle_readonly;


--
-- Name: TABLE ab_experiment_variants; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ab_experiment_variants TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ab_experiment_variants TO sparkle_celery;
GRANT SELECT ON TABLE ab_experiment_variants TO sparkle_readonly;


--
-- Name: TABLE ab_experiments; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ab_experiments TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ab_experiments TO sparkle_celery;
GRANT SELECT ON TABLE ab_experiments TO sparkle_readonly;


--
-- Name: TABLE accountability_checkin; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE accountability_checkin TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE accountability_checkin TO sparkle_celery;
GRANT SELECT ON TABLE accountability_checkin TO sparkle_readonly;


--
-- Name: TABLE accountability_partnership; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE accountability_partnership TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE accountability_partnership TO sparkle_celery;
GRANT SELECT ON TABLE accountability_partnership TO sparkle_readonly;


--
-- Name: TABLE accountability_policies; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE accountability_policies TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE accountability_policies TO sparkle_celery;
GRANT SELECT ON TABLE accountability_policies TO sparkle_readonly;


--
-- Name: TABLE achievements; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE achievements TO sparkle_readonly;


--
-- Name: TABLE admin_audit_log; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE admin_audit_log TO sparkle_readonly;


--
-- Name: TABLE agent_execution_stats; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE agent_execution_stats TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE agent_execution_stats TO sparkle_celery;
GRANT SELECT ON TABLE agent_execution_stats TO sparkle_readonly;


--
-- Name: SEQUENCE agent_execution_stats_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE agent_execution_stats_id_seq TO sparkle_gateway;
GRANT SELECT,USAGE ON SEQUENCE agent_execution_stats_id_seq TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE agent_execution_stats_id_seq TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE agent_execution_stats_id_seq TO sparkle_readonly;


--
-- Name: TABLE alembic_version; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE alembic_version TO sparkle_readonly;


--
-- Name: TABLE appeals; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE appeals TO sparkle_readonly;


--
-- Name: TABLE arbitration_cases; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE arbitration_cases TO sparkle_readonly;


--
-- Name: TABLE arbitration_decisions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE arbitration_decisions TO sparkle_readonly;


--
-- Name: TABLE asset_suggestion_logs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE asset_suggestion_logs TO sparkle_readonly;


--
-- Name: TABLE aurora_core_session_snapshots; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_core_session_snapshots TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_core_session_snapshots TO sparkle_celery;
GRANT SELECT ON TABLE aurora_core_session_snapshots TO sparkle_readonly;


--
-- Name: TABLE aurora_decision_telemetry; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_decision_telemetry TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_decision_telemetry TO sparkle_celery;
GRANT SELECT ON TABLE aurora_decision_telemetry TO sparkle_readonly;


--
-- Name: TABLE aurora_judgment_records; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_judgment_records TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_judgment_records TO sparkle_celery;
GRANT SELECT ON TABLE aurora_judgment_records TO sparkle_readonly;


--
-- Name: TABLE aurora_policy_versions; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_policy_versions TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_policy_versions TO sparkle_celery;
GRANT SELECT ON TABLE aurora_policy_versions TO sparkle_readonly;


--
-- Name: TABLE aurora_scheduled_wakes; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_scheduled_wakes TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_scheduled_wakes TO sparkle_celery;
GRANT SELECT ON TABLE aurora_scheduled_wakes TO sparkle_readonly;


--
-- Name: TABLE aurora_state_snapshots; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_state_snapshots TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE aurora_state_snapshots TO sparkle_celery;
GRANT SELECT ON TABLE aurora_state_snapshots TO sparkle_readonly;


--
-- Name: TABLE auth_audit_log; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE auth_audit_log TO sparkle_gateway;
GRANT SELECT ON TABLE auth_audit_log TO sparkle_readonly;


--
-- Name: TABLE background_tasks; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE background_tasks TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE background_tasks TO sparkle_celery;
GRANT SELECT ON TABLE background_tasks TO sparkle_readonly;


--
-- Name: TABLE behavior_patterns; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE behavior_patterns TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE behavior_patterns TO sparkle_celery;
GRANT SELECT ON TABLE behavior_patterns TO sparkle_readonly;


--
-- Name: TABLE behavioral_outcomes; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE behavioral_outcomes TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE behavioral_outcomes TO sparkle_celery;
GRANT SELECT ON TABLE behavioral_outcomes TO sparkle_readonly;


--
-- Name: TABLE broadcast_messages; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE broadcast_messages TO sparkle_readonly;


--
-- Name: TABLE calendar_events; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE calendar_events TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE calendar_events TO sparkle_celery;
GRANT SELECT ON TABLE calendar_events TO sparkle_readonly;


--
-- Name: TABLE candidate_action_feedback; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE candidate_action_feedback TO sparkle_readonly;


--
-- Name: TABLE capsule_favorites; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE capsule_favorites TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE capsule_favorites TO sparkle_celery;
GRANT SELECT ON TABLE capsule_favorites TO sparkle_readonly;


--
-- Name: TABLE capsule_feedbacks; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE capsule_feedbacks TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE capsule_feedbacks TO sparkle_celery;
GRANT SELECT ON TABLE capsule_feedbacks TO sparkle_readonly;


--
-- Name: TABLE capsule_generation_jobs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE capsule_generation_jobs TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE capsule_generation_jobs TO sparkle_celery;
GRANT SELECT ON TABLE capsule_generation_jobs TO sparkle_readonly;


--
-- Name: TABLE card_adoption_records; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE card_adoption_records TO sparkle_readonly;


--
-- Name: TABLE card_edges; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE card_edges TO sparkle_readonly;


--
-- Name: TABLE card_share_records; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE card_share_records TO sparkle_readonly;


--
-- Name: TABLE card_snapshots; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE card_snapshots TO sparkle_readonly;


--
-- Name: TABLE cards; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE cards TO sparkle_readonly;


--
-- Name: TABLE chat_messages; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE chat_messages TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE chat_messages TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE chat_messages TO sparkle_celery;
GRANT SELECT ON TABLE chat_messages TO sparkle_readonly;


--
-- Name: TABLE chat_sessions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE chat_sessions TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE chat_sessions TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE chat_sessions TO sparkle_celery;
GRANT SELECT ON TABLE chat_sessions TO sparkle_readonly;


--
-- Name: TABLE cognitive_fragments; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE cognitive_fragments TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE cognitive_fragments TO sparkle_celery;
GRANT SELECT ON TABLE cognitive_fragments TO sparkle_readonly;


--
-- Name: TABLE collaborative_galaxies; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE collaborative_galaxies TO sparkle_readonly;


--
-- Name: TABLE commitments; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE commitments TO sparkle_readonly;


--
-- Name: TABLE community_aggregate_signals; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE community_aggregate_signals TO sparkle_readonly;


--
-- Name: TABLE compliance_check_logs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE compliance_check_logs TO sparkle_readonly;


--
-- Name: TABLE conflict_resolution_records; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE conflict_resolution_records TO sparkle_readonly;


--
-- Name: TABLE context_budget_profiles; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE context_budget_profiles TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE context_budget_profiles TO sparkle_celery;
GRANT SELECT ON TABLE context_budget_profiles TO sparkle_readonly;


--
-- Name: TABLE context_pack_feedback; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE context_pack_feedback TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE context_pack_feedback TO sparkle_celery;
GRANT SELECT ON TABLE context_pack_feedback TO sparkle_readonly;


--
-- Name: TABLE context_pack_runs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE context_pack_runs TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE context_pack_runs TO sparkle_celery;
GRANT SELECT ON TABLE context_pack_runs TO sparkle_readonly;


--
-- Name: TABLE counterfactual_evaluation_reports; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE counterfactual_evaluation_reports TO sparkle_readonly;


--
-- Name: TABLE crdt_operation_log; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE crdt_operation_log TO sparkle_gateway;
GRANT SELECT ON TABLE crdt_operation_log TO sparkle_readonly;


--
-- Name: SEQUENCE crdt_operation_log_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE crdt_operation_log_id_seq TO sparkle_gateway;
GRANT SELECT,USAGE ON SEQUENCE crdt_operation_log_id_seq TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE crdt_operation_log_id_seq TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE crdt_operation_log_id_seq TO sparkle_readonly;


--
-- Name: TABLE crdt_snapshots; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE crdt_snapshots TO sparkle_gateway;
GRANT SELECT ON TABLE crdt_snapshots TO sparkle_readonly;


--
-- Name: TABLE crypto_shredding_certificates; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE crypto_shredding_certificates TO sparkle_readonly;


--
-- Name: TABLE curiosity_capsules; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE curiosity_capsules TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE curiosity_capsules TO sparkle_celery;
GRANT SELECT ON TABLE curiosity_capsules TO sparkle_readonly;


--
-- Name: TABLE custom_expert_profiles; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE custom_expert_profiles TO sparkle_readonly;


--
-- Name: TABLE custom_expert_teams; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE custom_expert_teams TO sparkle_readonly;


--
-- Name: TABLE daily_behavior_vector; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE daily_behavior_vector TO sparkle_readonly;


--
-- Name: TABLE data_access_logs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE data_access_logs TO sparkle_gateway;
GRANT SELECT ON TABLE data_access_logs TO sparkle_readonly;


--
-- Name: TABLE decision_records; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE decision_records TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE decision_records TO sparkle_celery;
GRANT SELECT ON TABLE decision_records TO sparkle_readonly;


--
-- Name: TABLE dictionary_entries; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE dictionary_entries TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE dictionary_entries TO sparkle_celery;
GRANT SELECT ON TABLE dictionary_entries TO sparkle_readonly;


--
-- Name: TABLE distilled_strategy_cache; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE distilled_strategy_cache TO sparkle_readonly;


--
-- Name: TABLE dlq_replay_audit_logs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE dlq_replay_audit_logs TO sparkle_celery;
GRANT SELECT ON TABLE dlq_replay_audit_logs TO sparkle_readonly;


--
-- Name: TABLE document_chunks; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE document_chunks TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE document_chunks TO sparkle_celery;
GRANT SELECT ON TABLE document_chunks TO sparkle_readonly;


--
-- Name: TABLE document_retrieval_feedback; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE document_retrieval_feedback TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE document_retrieval_feedback TO sparkle_celery;
GRANT SELECT ON TABLE document_retrieval_feedback TO sparkle_readonly;


--
-- Name: TABLE durable_session_state_snapshots; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE durable_session_state_snapshots TO sparkle_readonly;


--
-- Name: TABLE episodic_memories; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE episodic_memories TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE episodic_memories TO sparkle_celery;
GRANT SELECT ON TABLE episodic_memories TO sparkle_readonly;


--
-- Name: TABLE error_records; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE error_records TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE error_records TO sparkle_celery;
GRANT SELECT ON TABLE error_records TO sparkle_readonly;


--
-- Name: TABLE event_bus_dlq; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE event_bus_dlq TO sparkle_readonly;


--
-- Name: TABLE event_outbox; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE event_outbox TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE event_outbox TO sparkle_celery;
GRANT SELECT ON TABLE event_outbox TO sparkle_readonly;


--
-- Name: TABLE event_sequence_counters; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE event_sequence_counters TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE event_sequence_counters TO sparkle_celery;
GRANT SELECT ON TABLE event_sequence_counters TO sparkle_readonly;


--
-- Name: TABLE event_store; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE event_store TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE event_store TO sparkle_celery;
GRANT SELECT ON TABLE event_store TO sparkle_readonly;


--
-- Name: TABLE evolution_predictions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE evolution_predictions TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE evolution_predictions TO sparkle_celery;
GRANT SELECT ON TABLE evolution_predictions TO sparkle_readonly;


--
-- Name: TABLE execution_audit_log; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE execution_audit_log TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE execution_audit_log TO sparkle_celery;
GRANT SELECT ON TABLE execution_audit_log TO sparkle_readonly;


--
-- Name: TABLE execution_intents; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE execution_intents TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE execution_intents TO sparkle_celery;
GRANT SELECT ON TABLE execution_intents TO sparkle_readonly;


--
-- Name: TABLE execution_records; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE execution_records TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE execution_records TO sparkle_celery;
GRANT SELECT ON TABLE execution_records TO sparkle_readonly;


--
-- Name: TABLE execution_schedules; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE execution_schedules TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE execution_schedules TO sparkle_celery;
GRANT SELECT ON TABLE execution_schedules TO sparkle_readonly;


--
-- Name: TABLE expansion_feedback; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE expansion_feedback TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE expansion_feedback TO sparkle_celery;
GRANT SELECT ON TABLE expansion_feedback TO sparkle_readonly;


--
-- Name: TABLE focus_contracts; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE focus_contracts TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE focus_contracts TO sparkle_celery;
GRANT SELECT ON TABLE focus_contracts TO sparkle_readonly;


--
-- Name: TABLE focus_sessions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE focus_sessions TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE focus_sessions TO sparkle_celery;
GRANT SELECT ON TABLE focus_sessions TO sparkle_readonly;


--
-- Name: TABLE friendships; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE friendships TO sparkle_readonly;


--
-- Name: TABLE galaxy_skins; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE galaxy_skins TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE galaxy_skins TO sparkle_celery;
GRANT SELECT ON TABLE galaxy_skins TO sparkle_readonly;


--
-- Name: TABLE galaxy_user_permissions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE galaxy_user_permissions TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE galaxy_user_permissions TO sparkle_celery;
GRANT SELECT ON TABLE galaxy_user_permissions TO sparkle_readonly;


--
-- Name: TABLE goal_world_graph_snapshots; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE goal_world_graph_snapshots TO sparkle_readonly;


--
-- Name: TABLE goals; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE goals TO sparkle_readonly;


--
-- Name: TABLE group_files; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_files TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_files TO sparkle_celery;
GRANT SELECT ON TABLE group_files TO sparkle_readonly;


--
-- Name: TABLE group_members; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_members TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_members TO sparkle_celery;
GRANT SELECT ON TABLE group_members TO sparkle_readonly;


--
-- Name: TABLE group_message_reads; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_message_reads TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_message_reads TO sparkle_celery;
GRANT SELECT ON TABLE group_message_reads TO sparkle_readonly;


--
-- Name: TABLE group_messages; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_messages TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_messages TO sparkle_celery;
GRANT SELECT ON TABLE group_messages TO sparkle_readonly;


--
-- Name: TABLE group_task_claims; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_task_claims TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_task_claims TO sparkle_celery;
GRANT SELECT ON TABLE group_task_claims TO sparkle_readonly;


--
-- Name: TABLE group_tasks; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_tasks TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE group_tasks TO sparkle_celery;
GRANT SELECT ON TABLE group_tasks TO sparkle_readonly;


--
-- Name: TABLE groups; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE groups TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE groups TO sparkle_celery;
GRANT SELECT ON TABLE groups TO sparkle_readonly;


--
-- Name: TABLE growth_chronicle_snapshots; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE growth_chronicle_snapshots TO sparkle_readonly;


--
-- Name: TABLE idempotency_keys; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE idempotency_keys TO sparkle_gateway;
GRANT SELECT ON TABLE idempotency_keys TO sparkle_readonly;


--
-- Name: TABLE identity_evidence; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE identity_evidence TO sparkle_readonly;


--
-- Name: TABLE idiographic_associations; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE idiographic_associations TO sparkle_readonly;


--
-- Name: TABLE idiographic_changepoints; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE idiographic_changepoints TO sparkle_readonly;


--
-- Name: TABLE insight_claims; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE insight_claims TO sparkle_readonly;


--
-- Name: TABLE intervention_audit_logs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_audit_logs TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_audit_logs TO sparkle_celery;
GRANT SELECT ON TABLE intervention_audit_logs TO sparkle_readonly;


--
-- Name: TABLE intervention_feedback; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_feedback TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_feedback TO sparkle_celery;
GRANT SELECT ON TABLE intervention_feedback TO sparkle_readonly;


--
-- Name: TABLE intervention_outcomes; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_outcomes TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_outcomes TO sparkle_celery;
GRANT SELECT ON TABLE intervention_outcomes TO sparkle_readonly;


--
-- Name: TABLE intervention_records; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_records TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_records TO sparkle_celery;
GRANT SELECT ON TABLE intervention_records TO sparkle_readonly;


--
-- Name: TABLE intervention_requests; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_requests TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_requests TO sparkle_celery;
GRANT SELECT ON TABLE intervention_requests TO sparkle_readonly;


--
-- Name: TABLE intervention_strategy_outcomes; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_strategy_outcomes TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_strategy_outcomes TO sparkle_celery;
GRANT SELECT ON TABLE intervention_strategy_outcomes TO sparkle_readonly;


--
-- Name: TABLE intervention_templates; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_templates TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE intervention_templates TO sparkle_celery;
GRANT SELECT ON TABLE intervention_templates TO sparkle_readonly;


--
-- Name: TABLE irt_item_parameters; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE irt_item_parameters TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE irt_item_parameters TO sparkle_celery;
GRANT SELECT ON TABLE irt_item_parameters TO sparkle_readonly;


--
-- Name: TABLE item_similarities; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE item_similarities TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE item_similarities TO sparkle_celery;
GRANT SELECT ON TABLE item_similarities TO sparkle_readonly;


--
-- Name: TABLE jobs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE jobs TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE jobs TO sparkle_celery;
GRANT SELECT ON TABLE jobs TO sparkle_readonly;


--
-- Name: TABLE knowledge_node_documents; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE knowledge_node_documents TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE knowledge_node_documents TO sparkle_celery;
GRANT SELECT ON TABLE knowledge_node_documents TO sparkle_readonly;


--
-- Name: TABLE knowledge_nodes; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE knowledge_nodes TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE knowledge_nodes TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE knowledge_nodes TO sparkle_celery;
GRANT SELECT ON TABLE knowledge_nodes TO sparkle_readonly;


--
-- Name: TABLE leaderboard_snapshots; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE leaderboard_snapshots TO sparkle_readonly;


--
-- Name: TABLE learning_assets; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE learning_assets TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE learning_assets TO sparkle_celery;
GRANT SELECT ON TABLE learning_assets TO sparkle_readonly;


--
-- Name: TABLE legal_holds; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE legal_holds TO sparkle_readonly;


--
-- Name: TABLE login_attempts; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE login_attempts TO sparkle_gateway;
GRANT SELECT ON TABLE login_attempts TO sparkle_readonly;


--
-- Name: TABLE ltm_daily_snapshots; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ltm_daily_snapshots TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ltm_daily_snapshots TO sparkle_celery;
GRANT SELECT ON TABLE ltm_daily_snapshots TO sparkle_readonly;


--
-- Name: TABLE marketplace_packs; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE marketplace_packs TO sparkle_readonly;


--
-- Name: TABLE marketplace_skills; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE marketplace_skills TO sparkle_readonly;


--
-- Name: TABLE mastery_audit_log; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE mastery_audit_log TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE mastery_audit_log TO sparkle_celery;
GRANT SELECT ON TABLE mastery_audit_log TO sparkle_readonly;


--
-- Name: SEQUENCE mastery_audit_log_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE mastery_audit_log_id_seq TO sparkle_gateway;
GRANT SELECT,USAGE ON SEQUENCE mastery_audit_log_id_seq TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE mastery_audit_log_id_seq TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE mastery_audit_log_id_seq TO sparkle_readonly;


--
-- Name: TABLE memory_corrections; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE memory_corrections TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE memory_corrections TO sparkle_celery;
GRANT SELECT ON TABLE memory_corrections TO sparkle_readonly;


--
-- Name: TABLE memory_evolutions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE memory_evolutions TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE memory_evolutions TO sparkle_celery;
GRANT SELECT ON TABLE memory_evolutions TO sparkle_readonly;


--
-- Name: TABLE memory_goals; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE memory_goals TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE memory_goals TO sparkle_celery;
GRANT SELECT ON TABLE memory_goals TO sparkle_readonly;


--
-- Name: TABLE memory_preferences; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE memory_preferences TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE memory_preferences TO sparkle_celery;
GRANT SELECT ON TABLE memory_preferences TO sparkle_readonly;


--
-- Name: TABLE memory_rank_policies; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE memory_rank_policies TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE memory_rank_policies TO sparkle_celery;
GRANT SELECT ON TABLE memory_rank_policies TO sparkle_readonly;


--
-- Name: TABLE message_favorites; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE message_favorites TO sparkle_gateway;
GRANT SELECT ON TABLE message_favorites TO sparkle_readonly;


--
-- Name: TABLE message_reports; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE message_reports TO sparkle_gateway;
GRANT SELECT ON TABLE message_reports TO sparkle_readonly;


--
-- Name: TABLE next_action_selections; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE next_action_selections TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE next_action_selections TO sparkle_celery;
GRANT SELECT ON TABLE next_action_selections TO sparkle_readonly;


--
-- Name: TABLE nightly_reviews; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE nightly_reviews TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE nightly_reviews TO sparkle_celery;
GRANT SELECT ON TABLE nightly_reviews TO sparkle_readonly;


--
-- Name: TABLE node_expansion_queue; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE node_expansion_queue TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE node_expansion_queue TO sparkle_celery;
GRANT SELECT ON TABLE node_expansion_queue TO sparkle_readonly;


--
-- Name: TABLE node_relations; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE node_relations TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE node_relations TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE node_relations TO sparkle_celery;
GRANT SELECT ON TABLE node_relations TO sparkle_readonly;


--
-- Name: TABLE north_star_metric_events; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE north_star_metric_events TO sparkle_readonly;


--
-- Name: TABLE notification_interactions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE notification_interactions TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE notification_interactions TO sparkle_celery;
GRANT SELECT ON TABLE notification_interactions TO sparkle_readonly;


--
-- Name: TABLE notification_preferences; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE notification_preferences TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE notification_preferences TO sparkle_celery;
GRANT SELECT ON TABLE notification_preferences TO sparkle_readonly;


--
-- Name: TABLE notifications; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE notifications TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE notifications TO sparkle_celery;
GRANT SELECT ON TABLE notifications TO sparkle_readonly;


--
-- Name: TABLE offline_message_queue; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE offline_message_queue TO sparkle_gateway;
GRANT SELECT ON TABLE offline_message_queue TO sparkle_readonly;


--
-- Name: TABLE pack_adoption_history; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE pack_adoption_history TO sparkle_readonly;


--
-- Name: TABLE passive_signals; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE passive_signals TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE passive_signals TO sparkle_celery;
GRANT SELECT ON TABLE passive_signals TO sparkle_readonly;


--
-- Name: TABLE persdyn_attractors; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE persdyn_attractors TO sparkle_readonly;


--
-- Name: TABLE persona_snapshots; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE persona_snapshots TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE persona_snapshots TO sparkle_celery;
GRANT SELECT ON TABLE persona_snapshots TO sparkle_readonly;


--
-- Name: TABLE photon_transaction_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE photon_transaction_history TO sparkle_readonly;


--
-- Name: TABLE plan_execution_records; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE plan_execution_records TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE plan_execution_records TO sparkle_celery;
GRANT SELECT ON TABLE plan_execution_records TO sparkle_readonly;


--
-- Name: TABLE plan_states; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE plan_states TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE plan_states TO sparkle_celery;
GRANT SELECT ON TABLE plan_states TO sparkle_readonly;


--
-- Name: TABLE planning_artifacts; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE planning_artifacts TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE planning_artifacts TO sparkle_celery;
GRANT SELECT ON TABLE planning_artifacts TO sparkle_readonly;


--
-- Name: TABLE plans; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE plans TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE plans TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE plans TO sparkle_celery;
GRANT SELECT ON TABLE plans TO sparkle_readonly;


--
-- Name: TABLE post_likes; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE post_likes TO sparkle_readonly;


--
-- Name: TABLE posts; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE posts TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE posts TO sparkle_celery;
GRANT SELECT ON TABLE posts TO sparkle_readonly;


--
-- Name: TABLE privacy_budget_ledger; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE privacy_budget_ledger TO sparkle_readonly;


--
-- Name: TABLE private_messages; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE private_messages TO sparkle_readonly;


--
-- Name: TABLE probe_outcomes; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE probe_outcomes TO sparkle_readonly;


--
-- Name: TABLE processed_events; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE processed_events TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE processed_events TO sparkle_celery;
GRANT SELECT ON TABLE processed_events TO sparkle_readonly;


--
-- Name: TABLE projection_metadata; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE projection_metadata TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE projection_metadata TO sparkle_celery;
GRANT SELECT ON TABLE projection_metadata TO sparkle_readonly;


--
-- Name: TABLE projection_snapshots; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE projection_snapshots TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE projection_snapshots TO sparkle_celery;
GRANT SELECT ON TABLE projection_snapshots TO sparkle_readonly;


--
-- Name: TABLE push_delivery_records; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE push_delivery_records TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE push_delivery_records TO sparkle_celery;
GRANT SELECT ON TABLE push_delivery_records TO sparkle_readonly;


--
-- Name: TABLE push_histories; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE push_histories TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE push_histories TO sparkle_celery;
GRANT SELECT ON TABLE push_histories TO sparkle_readonly;


--
-- Name: TABLE push_preferences; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE push_preferences TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE push_preferences TO sparkle_celery;
GRANT SELECT ON TABLE push_preferences TO sparkle_readonly;


--
-- Name: TABLE recommendation_cache; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE recommendation_cache TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE recommendation_cache TO sparkle_celery;
GRANT SELECT ON TABLE recommendation_cache TO sparkle_readonly;


--
-- Name: TABLE release_approval_requests; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE release_approval_requests TO sparkle_readonly;


--
-- Name: TABLE report_snapshots; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE report_snapshots TO sparkle_readonly;


--
-- Name: TABLE research_consent_records; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE research_consent_records TO sparkle_readonly;


--
-- Name: TABLE response_feedback; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE response_feedback TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE response_feedback TO sparkle_celery;
GRANT SELECT ON TABLE response_feedback TO sparkle_readonly;


--
-- Name: TABLE review_feedback; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE review_feedback TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE review_feedback TO sparkle_celery;
GRANT SELECT ON TABLE review_feedback TO sparkle_readonly;


--
-- Name: TABLE review_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE review_history TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE review_history TO sparkle_celery;
GRANT SELECT ON TABLE review_history TO sparkle_readonly;


--
-- Name: TABLE review_overrides; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE review_overrides TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE review_overrides TO sparkle_celery;
GRANT SELECT ON TABLE review_overrides TO sparkle_readonly;


--
-- Name: TABLE routing_decision_log; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE routing_decision_log TO sparkle_readonly;


--
-- Name: TABLE safe_experiment_episodes; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE safe_experiment_episodes TO sparkle_readonly;


--
-- Name: TABLE safe_experiments; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE safe_experiments TO sparkle_readonly;


--
-- Name: TABLE saga_instances; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE saga_instances TO sparkle_readonly;


--
-- Name: TABLE scaffolding_states; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE scaffolding_states TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE scaffolding_states TO sparkle_celery;
GRANT SELECT ON TABLE scaffolding_states TO sparkle_readonly;


--
-- Name: TABLE scenes; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE scenes TO sparkle_readonly;


--
-- Name: TABLE security_audit_logs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE security_audit_logs TO sparkle_gateway;
GRANT SELECT ON TABLE security_audit_logs TO sparkle_readonly;


--
-- Name: TABLE seed_items; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE seed_items TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE seed_items TO sparkle_celery;
GRANT SELECT ON TABLE seed_items TO sparkle_readonly;


--
-- Name: TABLE seed_libraries; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE seed_libraries TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE seed_libraries TO sparkle_celery;
GRANT SELECT ON TABLE seed_libraries TO sparkle_readonly;


--
-- Name: TABLE seed_library_ratings; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE seed_library_ratings TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE seed_library_ratings TO sparkle_celery;
GRANT SELECT ON TABLE seed_library_ratings TO sparkle_readonly;


--
-- Name: TABLE semantic_links; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE semantic_links TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE semantic_links TO sparkle_celery;
GRANT SELECT ON TABLE semantic_links TO sparkle_readonly;


--
-- Name: TABLE session_completions; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE session_completions TO sparkle_readonly;


--
-- Name: TABLE shared_resources; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE shared_resources TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE shared_resources TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE shared_resources TO sparkle_celery;
GRANT SELECT ON TABLE shared_resources TO sparkle_readonly;


--
-- Name: TABLE shared_skills; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE shared_skills TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE shared_skills TO sparkle_celery;
GRANT SELECT ON TABLE shared_skills TO sparkle_readonly;


--
-- Name: TABLE shop_items; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE shop_items TO sparkle_readonly;


--
-- Name: TABLE shop_purchases; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE shop_purchases TO sparkle_readonly;


--
-- Name: TABLE simulation_runs; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE simulation_runs TO sparkle_readonly;


--
-- Name: TABLE skill_share_moderation_queue; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE skill_share_moderation_queue TO sparkle_readonly;


--
-- Name: TABLE spark_contracts; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE spark_contracts TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE spark_contracts TO sparkle_celery;
GRANT SELECT ON TABLE spark_contracts TO sparkle_readonly;


--
-- Name: TABLE srl_phase_states; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE srl_phase_states TO sparkle_readonly;


--
-- Name: TABLE stored_files; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE stored_files TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE stored_files TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE stored_files TO sparkle_celery;
GRANT SELECT ON TABLE stored_files TO sparkle_readonly;


--
-- Name: TABLE strategy_belief_snapshots; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE strategy_belief_snapshots TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE strategy_belief_snapshots TO sparkle_celery;
GRANT SELECT ON TABLE strategy_belief_snapshots TO sparkle_readonly;


--
-- Name: TABLE strategy_nodes; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE strategy_nodes TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE strategy_nodes TO sparkle_celery;
GRANT SELECT ON TABLE strategy_nodes TO sparkle_readonly;


--
-- Name: TABLE study_buddies; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE study_buddies TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE study_buddies TO sparkle_celery;
GRANT SELECT ON TABLE study_buddies TO sparkle_readonly;


--
-- Name: TABLE study_records; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE study_records TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE study_records TO sparkle_celery;
GRANT SELECT ON TABLE study_records TO sparkle_readonly;


--
-- Name: TABLE subjects; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE subjects TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE subjects TO sparkle_celery;
GRANT SELECT ON TABLE subjects TO sparkle_readonly;


--
-- Name: SEQUENCE subjects_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE subjects_id_seq TO sparkle_gateway;
GRANT SELECT,USAGE ON SEQUENCE subjects_id_seq TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE subjects_id_seq TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE subjects_id_seq TO sparkle_readonly;


--
-- Name: TABLE subtasks; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE subtasks TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE subtasks TO sparkle_celery;
GRANT SELECT ON TABLE subtasks TO sparkle_readonly;


--
-- Name: TABLE system_config_change_logs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE system_config_change_logs TO sparkle_readonly;


--
-- Name: TABLE task_documents; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE task_documents TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE task_documents TO sparkle_celery;
GRANT SELECT ON TABLE task_documents TO sparkle_readonly;


--
-- Name: TABLE task_feedbacks; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE task_feedbacks TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE task_feedbacks TO sparkle_celery;
GRANT SELECT ON TABLE task_feedbacks TO sparkle_readonly;


--
-- Name: TABLE task_knowledge_links; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE task_knowledge_links TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE task_knowledge_links TO sparkle_celery;
GRANT SELECT ON TABLE task_knowledge_links TO sparkle_readonly;


--
-- Name: TABLE task_occurrences; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE task_occurrences TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE task_occurrences TO sparkle_celery;
GRANT SELECT ON TABLE task_occurrences TO sparkle_readonly;


--
-- Name: TABLE task_resource_links; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE task_resource_links TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE task_resource_links TO sparkle_celery;
GRANT SELECT ON TABLE task_resource_links TO sparkle_readonly;


--
-- Name: TABLE tasks; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE tasks TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE tasks TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE tasks TO sparkle_celery;
GRANT SELECT ON TABLE tasks TO sparkle_readonly;


--
-- Name: TABLE theater_candidate_bundles; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE theater_candidate_bundles TO sparkle_readonly;


--
-- Name: TABLE theater_predictions; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE theater_predictions TO sparkle_readonly;


--
-- Name: TABLE token_usage; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE token_usage TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE token_usage TO sparkle_celery;
GRANT SELECT ON TABLE token_usage TO sparkle_readonly;


--
-- Name: TABLE tracking_events; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE tracking_events TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE tracking_events TO sparkle_celery;
GRANT SELECT ON TABLE tracking_events TO sparkle_readonly;


--
-- Name: TABLE transition_decision_records; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE transition_decision_records TO sparkle_readonly;


--
-- Name: TABLE unresolved_conflicts; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE unresolved_conflicts TO sparkle_readonly;


--
-- Name: TABLE user_achievements; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_achievements TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_achievements TO sparkle_celery;
GRANT SELECT ON TABLE user_achievements TO sparkle_readonly;


--
-- Name: TABLE user_blocks; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_blocks TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_blocks TO sparkle_celery;
GRANT SELECT ON TABLE user_blocks TO sparkle_readonly;


--
-- Name: TABLE user_consumables; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_consumables TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_consumables TO sparkle_celery;
GRANT SELECT ON TABLE user_consumables TO sparkle_readonly;


--
-- Name: TABLE user_daily_metrics; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_daily_metrics TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_daily_metrics TO sparkle_celery;
GRANT SELECT ON TABLE user_daily_metrics TO sparkle_readonly;


--
-- Name: TABLE user_devices; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_devices TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_devices TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_devices TO sparkle_celery;
GRANT SELECT ON TABLE user_devices TO sparkle_readonly;


--
-- Name: TABLE user_encryption_keys; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_encryption_keys TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_encryption_keys TO sparkle_celery;
GRANT SELECT ON TABLE user_encryption_keys TO sparkle_readonly;


--
-- Name: TABLE user_galaxy_skins; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_galaxy_skins TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_galaxy_skins TO sparkle_celery;
GRANT SELECT ON TABLE user_galaxy_skins TO sparkle_readonly;


--
-- Name: TABLE user_intervention_settings; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_intervention_settings TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_intervention_settings TO sparkle_celery;
GRANT SELECT ON TABLE user_intervention_settings TO sparkle_readonly;


--
-- Name: TABLE user_irt_ability; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_irt_ability TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_irt_ability TO sparkle_celery;
GRANT SELECT ON TABLE user_irt_ability TO sparkle_readonly;


--
-- Name: TABLE user_item_interactions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_item_interactions TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_item_interactions TO sparkle_celery;
GRANT SELECT ON TABLE user_item_interactions TO sparkle_readonly;


--
-- Name: TABLE user_learning_profiles; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_learning_profiles TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_learning_profiles TO sparkle_celery;
GRANT SELECT ON TABLE user_learning_profiles TO sparkle_readonly;


--
-- Name: TABLE user_library_subscriptions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_library_subscriptions TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_library_subscriptions TO sparkle_celery;
GRANT SELECT ON TABLE user_library_subscriptions TO sparkle_readonly;


--
-- Name: TABLE user_memory_settings; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_memory_settings TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_memory_settings TO sparkle_celery;
GRANT SELECT ON TABLE user_memory_settings TO sparkle_readonly;


--
-- Name: TABLE user_node_status; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE user_node_status TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_node_status TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_node_status TO sparkle_celery;
GRANT SELECT ON TABLE user_node_status TO sparkle_readonly;


--
-- Name: TABLE user_persona_keys; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_persona_keys TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_persona_keys TO sparkle_celery;
GRANT SELECT ON TABLE user_persona_keys TO sparkle_readonly;


--
-- Name: TABLE user_preferences_center; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_preferences_center TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_preferences_center TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_preferences_center TO sparkle_celery;
GRANT SELECT ON TABLE user_preferences_center TO sparkle_readonly;


--
-- Name: TABLE user_push_opt_in; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_push_opt_in TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_push_opt_in TO sparkle_celery;
GRANT SELECT ON TABLE user_push_opt_in TO sparkle_readonly;


--
-- Name: TABLE user_scenario_states; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_scenario_states TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_scenario_states TO sparkle_celery;
GRANT SELECT ON TABLE user_scenario_states TO sparkle_readonly;


--
-- Name: TABLE user_sessions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_sessions TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_sessions TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_sessions TO sparkle_celery;
GRANT SELECT ON TABLE user_sessions TO sparkle_readonly;


--
-- Name: TABLE user_settings; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_settings TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_settings TO sparkle_celery;
GRANT SELECT ON TABLE user_settings TO sparkle_readonly;


--
-- Name: TABLE user_similarities; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_similarities TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_similarities TO sparkle_celery;
GRANT SELECT ON TABLE user_similarities TO sparkle_readonly;


--
-- Name: TABLE user_skill_adoptions; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE user_skill_adoptions TO sparkle_readonly;


--
-- Name: TABLE user_skills; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_skills TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_skills TO sparkle_celery;
GRANT SELECT ON TABLE user_skills TO sparkle_readonly;


--
-- Name: TABLE user_state_snapshots; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_state_snapshots TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_state_snapshots TO sparkle_celery;
GRANT SELECT ON TABLE user_state_snapshots TO sparkle_readonly;


--
-- Name: TABLE user_streak_days; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_streak_days TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_streak_days TO sparkle_celery;
GRANT SELECT ON TABLE user_streak_days TO sparkle_readonly;


--
-- Name: TABLE user_streak_stats; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_streak_stats TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_streak_stats TO sparkle_celery;
GRANT SELECT ON TABLE user_streak_stats TO sparkle_readonly;


--
-- Name: TABLE user_titles; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_titles TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_titles TO sparkle_celery;
GRANT SELECT ON TABLE user_titles TO sparkle_readonly;


--
-- Name: TABLE user_tool_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_tool_history TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_tool_history TO sparkle_celery;
GRANT SELECT ON TABLE user_tool_history TO sparkle_readonly;


--
-- Name: SEQUENCE user_tool_history_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE user_tool_history_id_seq TO sparkle_gateway;
GRANT SELECT,USAGE ON SEQUENCE user_tool_history_id_seq TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE user_tool_history_id_seq TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE user_tool_history_id_seq TO sparkle_readonly;


--
-- Name: TABLE user_visual_configs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_visual_configs TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_visual_configs TO sparkle_celery;
GRANT SELECT ON TABLE user_visual_configs TO sparkle_readonly;


--
-- Name: TABLE user_visual_elements; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_visual_elements TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE user_visual_elements TO sparkle_celery;
GRANT SELECT ON TABLE user_visual_elements TO sparkle_readonly;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE users TO sparkle_gateway;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE users TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE users TO sparkle_celery;
GRANT SELECT ON TABLE users TO sparkle_readonly;


--
-- Name: TABLE visual_elements; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE visual_elements TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE visual_elements TO sparkle_celery;
GRANT SELECT ON TABLE visual_elements TO sparkle_readonly;


--
-- Name: TABLE window_states; Type: ACL; Schema: public; Owner: brsama
--

GRANT SELECT ON TABLE window_states TO sparkle_readonly;


--
-- Name: TABLE word_books; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE word_books TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE word_books TO sparkle_celery;
GRANT SELECT ON TABLE word_books TO sparkle_readonly;


--
-- Name: TABLE _ag_label_edge; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy._ag_label_edge TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy._ag_label_edge TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy._ag_label_edge TO sparkle_readonly;


--
-- Name: TABLE "APPLICATION"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."APPLICATION" TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."APPLICATION" TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy."APPLICATION" TO sparkle_readonly;


--
-- Name: SEQUENCE "APPLICATION_id_seq"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."APPLICATION_id_seq" TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."APPLICATION_id_seq" TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."APPLICATION_id_seq" TO sparkle_readonly;


--
-- Name: TABLE "APPLIES_TO"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."APPLIES_TO" TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."APPLIES_TO" TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy."APPLIES_TO" TO sparkle_readonly;


--
-- Name: SEQUENCE "APPLIES_TO_id_seq"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."APPLIES_TO_id_seq" TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."APPLIES_TO_id_seq" TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."APPLIES_TO_id_seq" TO sparkle_readonly;


--
-- Name: TABLE "INTERESTED_IN"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."INTERESTED_IN" TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."INTERESTED_IN" TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy."INTERESTED_IN" TO sparkle_readonly;


--
-- Name: SEQUENCE "INTERESTED_IN_id_seq"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."INTERESTED_IN_id_seq" TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."INTERESTED_IN_id_seq" TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."INTERESTED_IN_id_seq" TO sparkle_readonly;


--
-- Name: TABLE _ag_label_vertex; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy._ag_label_vertex TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy._ag_label_vertex TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy._ag_label_vertex TO sparkle_readonly;


--
-- Name: TABLE "KnowledgeNode"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."KnowledgeNode" TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."KnowledgeNode" TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy."KnowledgeNode" TO sparkle_readonly;


--
-- Name: SEQUENCE "KnowledgeNode_id_seq"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."KnowledgeNode_id_seq" TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."KnowledgeNode_id_seq" TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."KnowledgeNode_id_seq" TO sparkle_readonly;


--
-- Name: TABLE "MASTERED"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."MASTERED" TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."MASTERED" TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy."MASTERED" TO sparkle_readonly;


--
-- Name: SEQUENCE "MASTERED_id_seq"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."MASTERED_id_seq" TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."MASTERED_id_seq" TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."MASTERED_id_seq" TO sparkle_readonly;


--
-- Name: TABLE "PREREQUISITE"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."PREREQUISITE" TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."PREREQUISITE" TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy."PREREQUISITE" TO sparkle_readonly;


--
-- Name: SEQUENCE "PREREQUISITE_id_seq"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."PREREQUISITE_id_seq" TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."PREREQUISITE_id_seq" TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."PREREQUISITE_id_seq" TO sparkle_readonly;


--
-- Name: TABLE "RELATED"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."RELATED" TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."RELATED" TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy."RELATED" TO sparkle_readonly;


--
-- Name: SEQUENCE "RELATED_id_seq"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."RELATED_id_seq" TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."RELATED_id_seq" TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."RELATED_id_seq" TO sparkle_readonly;


--
-- Name: TABLE "STUDIED"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."STUDIED" TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."STUDIED" TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy."STUDIED" TO sparkle_readonly;


--
-- Name: SEQUENCE "STUDIED_id_seq"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."STUDIED_id_seq" TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."STUDIED_id_seq" TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."STUDIED_id_seq" TO sparkle_readonly;


--
-- Name: TABLE "STUDIES"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."STUDIES" TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."STUDIES" TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy."STUDIES" TO sparkle_readonly;


--
-- Name: SEQUENCE "STUDIES_id_seq"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."STUDIES_id_seq" TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."STUDIES_id_seq" TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."STUDIES_id_seq" TO sparkle_readonly;


--
-- Name: TABLE "User"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."User" TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."User" TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy."User" TO sparkle_readonly;


--
-- Name: SEQUENCE "User_id_seq"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."User_id_seq" TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."User_id_seq" TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."User_id_seq" TO sparkle_readonly;


--
-- Name: TABLE "__SchemaSeed"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."__SchemaSeed" TO sparkle_engine;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sparkle_galaxy."__SchemaSeed" TO sparkle_celery;
GRANT SELECT ON TABLE sparkle_galaxy."__SchemaSeed" TO sparkle_readonly;


--
-- Name: SEQUENCE "__SchemaSeed_id_seq"; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."__SchemaSeed_id_seq" TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."__SchemaSeed_id_seq" TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy."__SchemaSeed_id_seq" TO sparkle_readonly;


--
-- Name: SEQUENCE _ag_label_edge_id_seq; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy._ag_label_edge_id_seq TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy._ag_label_edge_id_seq TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy._ag_label_edge_id_seq TO sparkle_readonly;


--
-- Name: SEQUENCE _ag_label_vertex_id_seq; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy._ag_label_vertex_id_seq TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy._ag_label_vertex_id_seq TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy._ag_label_vertex_id_seq TO sparkle_readonly;


--
-- Name: SEQUENCE _label_id_seq; Type: ACL; Schema: sparkle_galaxy; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy._label_id_seq TO sparkle_engine;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy._label_id_seq TO sparkle_celery;
GRANT SELECT,USAGE ON SEQUENCE sparkle_galaxy._label_id_seq TO sparkle_readonly;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: brsama
--

ALTER DEFAULT PRIVILEGES FOR ROLE brsama IN SCHEMA public GRANT SELECT,USAGE ON SEQUENCES TO sparkle_gateway;
ALTER DEFAULT PRIVILEGES FOR ROLE brsama IN SCHEMA public GRANT SELECT,USAGE ON SEQUENCES TO sparkle_engine;
ALTER DEFAULT PRIVILEGES FOR ROLE brsama IN SCHEMA public GRANT SELECT,USAGE ON SEQUENCES TO sparkle_celery;
ALTER DEFAULT PRIVILEGES FOR ROLE brsama IN SCHEMA public GRANT SELECT,USAGE ON SEQUENCES TO sparkle_readonly;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: brsama
--

ALTER DEFAULT PRIVILEGES FOR ROLE brsama IN SCHEMA public GRANT SELECT ON TABLES TO sparkle_readonly;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: sparkle_galaxy; Owner: brsama
--

ALTER DEFAULT PRIVILEGES FOR ROLE brsama IN SCHEMA sparkle_galaxy GRANT SELECT,USAGE ON SEQUENCES TO sparkle_engine;
ALTER DEFAULT PRIVILEGES FOR ROLE brsama IN SCHEMA sparkle_galaxy GRANT SELECT,USAGE ON SEQUENCES TO sparkle_celery;
ALTER DEFAULT PRIVILEGES FOR ROLE brsama IN SCHEMA sparkle_galaxy GRANT SELECT,USAGE ON SEQUENCES TO sparkle_readonly;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: sparkle_galaxy; Owner: brsama
--

ALTER DEFAULT PRIVILEGES FOR ROLE brsama IN SCHEMA sparkle_galaxy GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES TO sparkle_engine;
ALTER DEFAULT PRIVILEGES FOR ROLE brsama IN SCHEMA sparkle_galaxy GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES TO sparkle_celery;
ALTER DEFAULT PRIVILEGES FOR ROLE brsama IN SCHEMA sparkle_galaxy GRANT SELECT ON TABLES TO sparkle_readonly;


--
-- PostgreSQL database dump complete
--


