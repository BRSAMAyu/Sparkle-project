-- PostgreSQL database dump


-- Dumped from database version 16.11 (Debian 16.11-1.pgdg12+1)
-- Dumped by pg_dump version 16.11 (Debian 16.11-1.pgdg12+1)


-- Name: vector; Type: EXTENSION; Schema: -; Owner: -

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


-- Name: analysisstatus; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.analysisstatus AS ENUM (
    'PENDING',
    'PROCESSING',
    'COMPLETED',
    'FAILED'
);


ALTER TYPE public.analysisstatus OWNER TO postgres;

-- Name: avatarstatus; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.avatarstatus AS ENUM (
    'APPROVED',
    'PENDING',
    'REJECTED'
);


ALTER TYPE public.avatarstatus OWNER TO postgres;

-- Name: focusstatus; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.focusstatus AS ENUM (
    'COMPLETED',
    'INTERRUPTED'
);


ALTER TYPE public.focusstatus OWNER TO postgres;

-- Name: focustype; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.focustype AS ENUM (
    'POMODORO',
    'STOPWATCH'
);


ALTER TYPE public.focustype OWNER TO postgres;

-- Name: friendshipstatus; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.friendshipstatus AS ENUM (
    'PENDING',
    'ACCEPTED',
    'BLOCKED'
);


ALTER TYPE public.friendshipstatus OWNER TO postgres;

-- Name: grouprole; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.grouprole AS ENUM (
    'OWNER',
    'ADMIN',
    'MEMBER'
);


ALTER TYPE public.grouprole OWNER TO postgres;

-- Name: grouptype; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.grouptype AS ENUM (
    'SQUAD',
    'SPRINT',
    'OFFICIAL'
);


ALTER TYPE public.grouptype OWNER TO postgres;

-- Name: messagerole; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.messagerole AS ENUM (
    'USER',
    'ASSISTANT',
    'SYSTEM'
);


ALTER TYPE public.messagerole OWNER TO postgres;

-- Name: messagetype; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.messagetype AS ENUM (
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


ALTER TYPE public.messagetype OWNER TO postgres;

-- Name: moderationaction; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.moderationaction AS ENUM (
    'WARN',
    'MUTE',
    'KICK',
    'BAN'
);


ALTER TYPE public.moderationaction OWNER TO postgres;

-- Name: offlinemessagestatus; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.offlinemessagestatus AS ENUM (
    'PENDING',
    'SENT',
    'FAILED',
    'EXPIRED'
);


ALTER TYPE public.offlinemessagestatus OWNER TO postgres;

-- Name: plantype; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.plantype AS ENUM (
    'SPRINT',
    'GROWTH'
);


ALTER TYPE public.plantype OWNER TO postgres;

-- Name: reportreason; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.reportreason AS ENUM (
    'SPAM',
    'HARASSMENT',
    'VIOLENCE',
    'MISINFORMATION',
    'INAPPROPRIATE',
    'OTHER'
);


ALTER TYPE public.reportreason OWNER TO postgres;

-- Name: reportstatus; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.reportstatus AS ENUM (
    'PENDING',
    'REVIEWED',
    'DISMISSED',
    'ACTIONED'
);


ALTER TYPE public.reportstatus OWNER TO postgres;

-- Name: taskstatus; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.taskstatus AS ENUM (
    'PENDING',
    'IN_PROGRESS',
    'COMPLETED',
    'ABANDONED'
);


ALTER TYPE public.taskstatus OWNER TO postgres;

-- Name: tasktype; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.tasktype AS ENUM (
    'LEARNING',
    'TRAINING',
    'ERROR_FIX',
    'REFLECTION',
    'SOCIAL',
    'PLANNING'
);


ALTER TYPE public.tasktype OWNER TO postgres;

-- Name: userstatus; Type: TYPE; Schema: public; Owner: postgres

CREATE TYPE public.userstatus AS ENUM (
    'ONLINE',
    'OFFLINE',
    'INVISIBLE'
);


ALTER TYPE public.userstatus OWNER TO postgres;



-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

-- Name: behavior_patterns; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.behavior_patterns (
    user_id uuid NOT NULL,
    pattern_name character varying(100) NOT NULL,
    pattern_type character varying(50) NOT NULL,
    description text,
    solution_text text,
    evidence_ids json,
    confidence_score double precision,
    frequency integer,
    is_archived boolean,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    last_observed_at timestamp without time zone,
    last_decay_at timestamp without time zone
);


ALTER TABLE public.behavior_patterns OWNER TO postgres;

-- Name: behavioral_outcomes; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.behavioral_outcomes (
    user_id uuid NOT NULL,
    intervention_id uuid NOT NULL,
    outcome_type character varying(50) NOT NULL,
    time_to_outcome integer NOT NULL,
    success boolean NOT NULL,
    context jsonb,
    "timestamp" timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.behavioral_outcomes OWNER TO postgres;

-- Name: broadcast_messages; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.broadcast_messages (
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


ALTER TABLE public.broadcast_messages OWNER TO postgres;

-- Name: chat_sessions; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.chat_sessions (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    title text,
    last_message_at timestamp without time zone,
    last_preview text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.chat_sessions OWNER TO postgres;

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_pkey PRIMARY KEY (id);

-- Name: chat_messages; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.chat_messages (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role public.messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages OWNER TO postgres;

-- Name: cognitive_fragments; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.cognitive_fragments (
    user_id uuid NOT NULL,
    task_id uuid,
    analysis_status public.analysisstatus NOT NULL,
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
    embedding public.vector(1536),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.cognitive_fragments OWNER TO postgres;

-- Name: collaborative_galaxies; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.collaborative_galaxies (
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


ALTER TABLE public.collaborative_galaxies OWNER TO postgres;

-- Name: compliance_check_logs; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.compliance_check_logs (
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


ALTER TABLE public.compliance_check_logs OWNER TO postgres;

-- Name: context_budget_profiles; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.context_budget_profiles (
    intent character varying(30) NOT NULL,
    bucket character varying(30) NOT NULL,
    multiplier double precision NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.context_budget_profiles OWNER TO postgres;

-- Name: context_pack_feedback; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.context_pack_feedback (
    pack_run_id uuid NOT NULL,
    feedback_type character varying(20) NOT NULL,
    reasons jsonb,
    score double precision,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.context_pack_feedback OWNER TO postgres;

-- Name: context_pack_runs; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.context_pack_runs (
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


ALTER TABLE public.context_pack_runs OWNER TO postgres;

-- Name: crdt_operation_log; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.crdt_operation_log (
    id bigint NOT NULL,
    galaxy_id uuid NOT NULL,
    user_id uuid NOT NULL,
    operation_type character varying(50),
    operation_data jsonb,
    "timestamp" timestamp without time zone NOT NULL
);


ALTER TABLE public.crdt_operation_log OWNER TO postgres;

-- Name: crdt_operation_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres

CREATE SEQUENCE public.crdt_operation_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.crdt_operation_log_id_seq OWNER TO postgres;

-- Name: crdt_operation_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres

ALTER SEQUENCE public.crdt_operation_log_id_seq OWNED BY public.crdt_operation_log.id;


-- Name: crdt_snapshots; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.crdt_snapshots (
    galaxy_id uuid NOT NULL,
    state_data bytea NOT NULL,
    operation_count integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.crdt_snapshots OWNER TO postgres;

-- Name: crypto_shredding_certificates; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.crypto_shredding_certificates (
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


ALTER TABLE public.crypto_shredding_certificates OWNER TO postgres;

-- Name: curiosity_capsules; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.curiosity_capsules (
    user_id uuid NOT NULL,
    title character varying(255) NOT NULL,
    content text NOT NULL,
    related_subject character varying(255),
    related_task_id uuid,
    is_read boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.curiosity_capsules OWNER TO postgres;

-- Name: data_access_logs; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.data_access_logs (
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


ALTER TABLE public.data_access_logs OWNER TO postgres;

-- Name: decision_records; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.decision_records (
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


ALTER TABLE public.decision_records OWNER TO postgres;

-- Name: dictionary_entries; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.dictionary_entries (
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


ALTER TABLE public.dictionary_entries OWNER TO postgres;

-- Name: dlq_replay_audit_logs; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.dlq_replay_audit_logs (
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


ALTER TABLE public.dlq_replay_audit_logs OWNER TO postgres;

-- Name: document_chunks; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.document_chunks (
    file_id uuid NOT NULL,
    user_id uuid NOT NULL,
    chunk_index integer NOT NULL,
    page_number integer,
    section_title character varying(255),
    content text NOT NULL,
    embedding public.vector(1536),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.document_chunks OWNER TO postgres;

-- Name: episodic_memories; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.episodic_memories (
    user_id uuid NOT NULL,
    summary character varying(2000) NOT NULL,
    source_type character varying(30) NOT NULL,
    source_id character varying(100),
    occurred_at timestamp without time zone NOT NULL,
    importance_score double precision,
    tags jsonb,
    evidence_refs jsonb NOT NULL,
    embedding public.vector(1536),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    evidence_missing boolean DEFAULT false NOT NULL,
    evidence_checked_at timestamp without time zone,
    evidence_snapshot jsonb,
    retracted_at timestamp without time zone,
    evidence_score double precision DEFAULT 0.0 NOT NULL,
    correction_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.episodic_memories OWNER TO postgres;

-- Name: error_records; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.error_records (
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


ALTER TABLE public.error_records OWNER TO postgres;

-- Name: event_outbox; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.event_outbox (
    id uuid NOT NULL,
    aggregate_type character varying(100) NOT NULL,
    aggregate_id character varying(100) NOT NULL,
    event_type character varying(100) NOT NULL,
    event_version integer NOT NULL,
    payload jsonb NOT NULL,
    metadata jsonb,
    sequence_number bigint NOT NULL,
    created_at timestamp without time zone NOT NULL,
    published_at timestamp without time zone
);


ALTER TABLE public.event_outbox OWNER TO postgres;

-- Name: event_outbox_sequence_number_seq; Type: SEQUENCE; Schema: public; Owner: postgres

ALTER TABLE public.event_outbox ALTER COLUMN sequence_number ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.event_outbox_sequence_number_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


-- Name: event_store; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.event_store (
    id bigint NOT NULL,
    aggregate_type character varying(100) NOT NULL,
    aggregate_id character varying(100) NOT NULL,
    event_type character varying(100) NOT NULL,
    event_version integer NOT NULL,
    sequence_number bigint NOT NULL,
    payload jsonb NOT NULL,
    metadata jsonb,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.event_store OWNER TO postgres;

-- Name: event_store_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres

ALTER TABLE public.event_store ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.event_store_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


-- Name: expansion_feedback; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.expansion_feedback (
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


ALTER TABLE public.expansion_feedback OWNER TO postgres;

-- Name: focus_sessions; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.focus_sessions (
    user_id uuid NOT NULL,
    task_id uuid,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    duration_minutes integer NOT NULL,
    focus_type public.focustype NOT NULL,
    status public.focusstatus NOT NULL,
    white_noise_type integer,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.focus_sessions OWNER TO postgres;

-- Name: friendships; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.friendships (
    user_id uuid NOT NULL,
    friend_id uuid NOT NULL,
    status public.friendshipstatus NOT NULL,
    initiated_by uuid NOT NULL,
    match_reason json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.friendships OWNER TO postgres;

-- Name: galaxy_user_permissions; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.galaxy_user_permissions (
    galaxy_id uuid NOT NULL,
    user_id uuid NOT NULL,
    permission_level character varying(20) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.galaxy_user_permissions OWNER TO postgres;

-- Name: group_files; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.group_files (
    group_id uuid NOT NULL,
    file_id uuid NOT NULL,
    shared_by_id uuid NOT NULL,
    category character varying(64),
    tags json NOT NULL,
    view_role public.grouprole NOT NULL,
    download_role public.grouprole NOT NULL,
    manage_role public.grouprole NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.group_files OWNER TO postgres;

-- Name: group_members; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.group_members (
    group_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role public.grouprole NOT NULL,
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


ALTER TABLE public.group_members OWNER TO postgres;

-- Name: group_messages; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.group_messages (
    group_id uuid NOT NULL,
    sender_id uuid,
    message_type public.messagetype NOT NULL,
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


ALTER TABLE public.group_messages OWNER TO postgres;

-- Name: group_task_claims; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.group_task_claims (
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


ALTER TABLE public.group_task_claims OWNER TO postgres;

-- Name: group_tasks; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.group_tasks (
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


ALTER TABLE public.group_tasks OWNER TO postgres;

-- Name: groups; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.groups (
    name character varying(100) NOT NULL,
    description text,
    avatar_url character varying(500),
    type public.grouptype NOT NULL,
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


ALTER TABLE public.groups OWNER TO postgres;

-- Name: idempotency_keys; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.idempotency_keys (
    key character varying(64) NOT NULL,
    user_id uuid NOT NULL,
    response json NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone NOT NULL
);


ALTER TABLE public.idempotency_keys OWNER TO postgres;

-- Name: intervention_audit_logs; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.intervention_audit_logs (
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


ALTER TABLE public.intervention_audit_logs OWNER TO postgres;

-- Name: intervention_feedback; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.intervention_feedback (
    request_id uuid NOT NULL,
    user_id uuid NOT NULL,
    feedback_type character varying(40) NOT NULL,
    extra_data json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    idempotency_key character varying(200) NOT NULL
);


ALTER TABLE public.intervention_feedback OWNER TO postgres;

-- Name: intervention_requests; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.intervention_requests (
    user_id uuid NOT NULL,
    dedupe_key character varying(200),
    topic character varying(120),
    requested_level character varying(40) NOT NULL,
    final_level character varying(40) NOT NULL,
    status character varying(40) NOT NULL,
    reason json,
    content json,
    cooldown_policy json,
    schema_version character varying(50) NOT NULL,
    policy_version character varying(50),
    model_version character varying(80),
    expires_at timestamp without time zone,
    is_retractable boolean NOT NULL,
    supersedes_id uuid,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    delivery_method character varying(20),
    template_id character varying(100),
    template_variant_id character varying(100),
    scaffolding_level integer,
    intent_type character varying(50)
);


ALTER TABLE public.intervention_requests OWNER TO postgres;

-- Name: intervention_templates; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.intervention_templates (
    template_id character varying(100) NOT NULL,
    intent_type character varying(50) NOT NULL,
    support_level integer NOT NULL,
    variants jsonb NOT NULL,
    meta jsonb,
    version integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.intervention_templates OWNER TO postgres;

-- Name: irt_item_parameters; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.irt_item_parameters (
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


ALTER TABLE public.irt_item_parameters OWNER TO postgres;

-- Name: jobs; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.jobs (
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


ALTER TABLE public.jobs OWNER TO postgres;

-- Name: knowledge_nodes; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.knowledge_nodes (
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
    embedding public.vector(1536),
    position_x double precision,
    position_y double precision,
    global_spark_count integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.knowledge_nodes OWNER TO postgres;

-- Name: legal_holds; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.legal_holds (
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


ALTER TABLE public.legal_holds OWNER TO postgres;

-- Name: login_attempts; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.login_attempts (
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


ALTER TABLE public.login_attempts OWNER TO postgres;

-- Name: ltm_daily_snapshots; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.ltm_daily_snapshots (
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    snapshot_date date NOT NULL,
    payload jsonb NOT NULL
);


ALTER TABLE public.ltm_daily_snapshots OWNER TO postgres;

-- Name: mastery_audit_log; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.mastery_audit_log (
    id integer NOT NULL,
    user_id uuid NOT NULL,
    node_id uuid NOT NULL,
    old_mastery double precision NOT NULL,
    new_mastery double precision NOT NULL,
    change_reason character varying(100) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.mastery_audit_log OWNER TO postgres;

-- Name: mastery_audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres

ALTER TABLE public.mastery_audit_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.mastery_audit_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


-- Name: memory_corrections; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.memory_corrections (
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


ALTER TABLE public.memory_corrections OWNER TO postgres;

-- Name: memory_goals; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.memory_goals (
    user_id uuid NOT NULL,
    title character varying(255) NOT NULL,
    status character varying(30) NOT NULL,
    target_date date,
    expires_at timestamp without time zone,
    linked_task_id uuid,
    linked_plan_id uuid,
    evidence_refs jsonb NOT NULL,
    metadata jsonb,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    evidence_missing boolean DEFAULT false NOT NULL,
    evidence_checked_at timestamp without time zone,
    retracted_at timestamp without time zone,
    evidence_score double precision DEFAULT 0.0 NOT NULL,
    correction_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.memory_goals OWNER TO postgres;

-- Name: memory_preferences; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.memory_preferences (
    user_id uuid NOT NULL,
    pref_key character varying(80) NOT NULL,
    pref_value jsonb NOT NULL,
    version integer NOT NULL,
    replaced_by_id uuid,
    confidence double precision,
    evidence_refs jsonb NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    evidence_missing boolean DEFAULT false NOT NULL,
    evidence_checked_at timestamp without time zone,
    retracted_at timestamp without time zone,
    evidence_score double precision DEFAULT 0.0 NOT NULL,
    correction_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.memory_preferences OWNER TO postgres;

-- Name: memory_rank_policies; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.memory_rank_policies (
    scope_type character varying(20) NOT NULL,
    scope_key character varying(120),
    weights jsonb NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.memory_rank_policies OWNER TO postgres;

-- Name: message_favorites; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.message_favorites (
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


ALTER TABLE public.message_favorites OWNER TO postgres;

-- Name: message_reports; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.message_reports (
    reporter_id uuid NOT NULL,
    group_message_id uuid,
    private_message_id uuid,
    reason public.reportreason NOT NULL,
    description text,
    status public.reportstatus NOT NULL,
    reviewed_by uuid,
    reviewed_at timestamp without time zone,
    action_taken public.moderationaction,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.message_reports OWNER TO postgres;

-- Name: nightly_reviews; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.nightly_reviews (
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


ALTER TABLE public.nightly_reviews OWNER TO postgres;

-- Name: node_expansion_queue; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.node_expansion_queue (
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


ALTER TABLE public.node_expansion_queue OWNER TO postgres;

-- Name: node_relations; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.node_relations (
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


ALTER TABLE public.node_relations OWNER TO postgres;

-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.notifications (
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


ALTER TABLE public.notifications OWNER TO postgres;

-- Name: offline_message_queue; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.offline_message_queue (
    user_id uuid NOT NULL,
    client_nonce character varying(100) NOT NULL,
    message_type character varying(50) NOT NULL,
    target_id uuid NOT NULL,
    payload json NOT NULL,
    status public.offlinemessagestatus NOT NULL,
    retry_count integer NOT NULL,
    last_retry_at timestamp without time zone,
    error_message text,
    expires_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.offline_message_queue OWNER TO postgres;

-- Name: outbox_events; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.outbox_events (
    id integer NOT NULL,
    event_type character varying(100) NOT NULL,
    payload json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    processed boolean DEFAULT false
);


ALTER TABLE public.outbox_events OWNER TO postgres;

-- Name: outbox_events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres

ALTER TABLE public.outbox_events ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.outbox_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


-- Name: passive_signals; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.passive_signals (
    user_id uuid NOT NULL,
    signal_type character varying(50) NOT NULL,
    intervention_id uuid,
    "timestamp" timestamp without time zone NOT NULL,
    context jsonb,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.passive_signals OWNER TO postgres;

-- Name: persona_snapshots; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.persona_snapshots (
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


ALTER TABLE public.persona_snapshots OWNER TO postgres;

-- Name: plans; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.plans (
    user_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    type public.plantype NOT NULL,
    description text,
    target_date date,
    daily_available_minutes integer NOT NULL,
    total_estimated_hours double precision,
    subject character varying(100),
    mastery_level double precision NOT NULL,
    progress double precision NOT NULL,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.plans OWNER TO postgres;

-- Name: post_likes; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.post_likes (
    user_id uuid NOT NULL,
    post_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.post_likes OWNER TO postgres;

-- Name: posts; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.posts (
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


ALTER TABLE public.posts OWNER TO postgres;

-- Name: private_messages; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.private_messages (
    sender_id uuid NOT NULL,
    receiver_id uuid NOT NULL,
    message_type public.messagetype NOT NULL,
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


ALTER TABLE public.private_messages OWNER TO postgres;

-- Name: processed_events; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.processed_events (
    event_id uuid NOT NULL,
    consumer_group character varying(100) NOT NULL,
    processed_at timestamp without time zone NOT NULL
);


ALTER TABLE public.processed_events OWNER TO postgres;

-- Name: projection_metadata; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.projection_metadata (
    projection_name character varying(100) NOT NULL,
    status character varying(20) NOT NULL,
    last_processed_position bigint DEFAULT '0'::bigint NOT NULL,
    last_processed_at timestamp without time zone,
    version integer NOT NULL,
    error_message text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.projection_metadata OWNER TO postgres;

-- Name: projection_snapshots; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.projection_snapshots (
    id uuid NOT NULL,
    projection_name character varying(100) NOT NULL,
    aggregate_id character varying(100),
    snapshot_data jsonb NOT NULL,
    stream_position bigint NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.projection_snapshots OWNER TO postgres;

-- Name: push_histories; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.push_histories (
    user_id uuid NOT NULL,
    trigger_type character varying(50) NOT NULL,
    content_hash character varying(64),
    status character varying(50) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    interaction_type character varying(50),
    interacted_at timestamp without time zone
);


ALTER TABLE public.push_histories OWNER TO postgres;

-- Name: push_preferences; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.push_preferences (
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


ALTER TABLE public.push_preferences OWNER TO postgres;

-- Name: response_feedback; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.response_feedback (
    user_id uuid NOT NULL,
    response_id uuid NOT NULL,
    trace_id character varying NOT NULL,
    workflow_id character varying(64),
    prompt_version character varying(50),
    feedback_type smallint NOT NULL,
    reasons jsonb,
    free_text character varying,
    meta jsonb,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    intervention_id uuid,
    scaffolding_level integer,
    template_variant_id character varying(100),
    time_to_response integer,
    action_taken character varying(40)
);


ALTER TABLE public.response_feedback OWNER TO postgres;

-- Name: scaffolding_states; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.scaffolding_states (
    user_id uuid NOT NULL,
    capability_level double precision NOT NULL,
    current_zone character varying(20) NOT NULL,
    support_level integer NOT NULL,
    template_variant_id character varying(100),
    consecutive_successes integer NOT NULL,
    consecutive_failures integer NOT NULL,
    last_intervention_timestamp timestamp without time zone,
    history jsonb,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.scaffolding_states OWNER TO postgres;

-- Name: security_audit_logs; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.security_audit_logs (
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


ALTER TABLE public.security_audit_logs OWNER TO postgres;

-- Name: semantic_links; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.semantic_links (
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


ALTER TABLE public.semantic_links OWNER TO postgres;

-- Name: shared_resources; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.shared_resources (
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
    deleted_at timestamp without time zone
);


ALTER TABLE public.shared_resources OWNER TO postgres;

-- Name: stored_files; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.stored_files (
    user_id uuid NOT NULL,
    file_name character varying(255) NOT NULL,
    mime_type character varying(150) NOT NULL,
    file_size bigint NOT NULL,
    bucket character varying(128) NOT NULL,
    object_key character varying(512) NOT NULL,
    status character varying(32) NOT NULL,
    visibility character varying(32) NOT NULL,
    error_message character varying(255),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.stored_files OWNER TO postgres;

-- Name: strategy_nodes; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.strategy_nodes (
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


ALTER TABLE public.strategy_nodes OWNER TO postgres;

-- Name: study_records; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.study_records (
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


ALTER TABLE public.study_records OWNER TO postgres;

-- Name: subjects; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.subjects (
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


ALTER TABLE public.subjects OWNER TO postgres;

-- Name: subjects_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres

CREATE SEQUENCE public.subjects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.subjects_id_seq OWNER TO postgres;

-- Name: subjects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres

ALTER SEQUENCE public.subjects_id_seq OWNED BY public.subjects.id;


-- Name: system_config_change_logs; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.system_config_change_logs (
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


ALTER TABLE public.system_config_change_logs OWNER TO postgres;

-- Name: tasks; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.tasks (
    user_id uuid NOT NULL,
    plan_id uuid,
    title character varying(255) NOT NULL,
    type public.tasktype NOT NULL,
    tags jsonb NOT NULL,
    estimated_minutes integer NOT NULL,
    difficulty integer NOT NULL,
    energy_cost integer NOT NULL,
    guide_content text,
    status public.taskstatus NOT NULL,
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.tasks OWNER TO postgres;

-- Name: token_usage; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.token_usage (
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


ALTER TABLE public.token_usage OWNER TO postgres;

-- Name: tracking_events; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.tracking_events (
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


ALTER TABLE public.tracking_events OWNER TO postgres;

-- Name: user_daily_metrics; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.user_daily_metrics (
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


ALTER TABLE public.user_daily_metrics OWNER TO postgres;

-- Name: user_encryption_keys; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.user_encryption_keys (
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


ALTER TABLE public.user_encryption_keys OWNER TO postgres;

-- Name: user_intervention_settings; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.user_intervention_settings (
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


ALTER TABLE public.user_intervention_settings OWNER TO postgres;

-- Name: user_irt_ability; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.user_irt_ability (
    user_id uuid NOT NULL,
    subject_id character varying(32),
    theta double precision NOT NULL,
    last_updated_at timestamp without time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.user_irt_ability OWNER TO postgres;

-- Name: user_memory_settings; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.user_memory_settings (
    user_id uuid NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    allow_preferences boolean DEFAULT true NOT NULL,
    allow_goals boolean DEFAULT true NOT NULL,
    allow_episodic boolean DEFAULT true NOT NULL,
    capture_level character varying(20) DEFAULT 'medium'::character varying NOT NULL,
    blocked_pref_keys jsonb DEFAULT '[]'::jsonb NOT NULL,
    blocked_sources jsonb DEFAULT '[]'::jsonb NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.user_memory_settings OWNER TO postgres;

-- Name: user_node_status; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.user_node_status (
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


ALTER TABLE public.user_node_status OWNER TO postgres;

-- Name: user_persona_keys; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.user_persona_keys (
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


ALTER TABLE public.user_persona_keys OWNER TO postgres;

-- Name: user_preferences_center; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.user_preferences_center (
    user_id uuid NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    schema_version integer DEFAULT 1 NOT NULL,
    explicit jsonb DEFAULT '{}'::jsonb NOT NULL,
    inferred jsonb DEFAULT '{}'::jsonb NOT NULL,
    last_explicit_update timestamp without time zone,
    last_inferred_update timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.user_preferences_center OWNER TO postgres;

-- Name: user_state_snapshots; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.user_state_snapshots (
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


ALTER TABLE public.user_state_snapshots OWNER TO postgres;

-- Name: users; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.users (
    username character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(100),
    nickname character varying(100),
    avatar_url character varying(500),
    avatar_status public.avatarstatus NOT NULL,
    pending_avatar_url character varying(500),
    flame_level integer NOT NULL,
    flame_brightness double precision NOT NULL,
    depth_preference double precision NOT NULL,
    curiosity_preference double precision NOT NULL,
    schedule_preferences json,
    weather_preferences json,
    is_active boolean NOT NULL,
    is_superuser boolean NOT NULL,
    status public.userstatus NOT NULL,
    google_id character varying(255),
    apple_id character varying(255),
    wechat_unionid character varying(255),
    registration_source character varying(50) NOT NULL,
    last_login_at timestamp without time zone,
    is_minor boolean,
    age_verified boolean NOT NULL,
    age_verification_source character varying(50),
    age_verified_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO postgres;

-- Name: word_books; Type: TABLE; Schema: public; Owner: postgres

CREATE TABLE public.word_books (
    user_id uuid NOT NULL,
    word character varying(100) NOT NULL,
    phonetic character varying(100),
    definition text NOT NULL,
    mastery_level integer,
    next_review_at timestamp without time zone,
    last_review_at timestamp without time zone,
    review_count integer,
    context_sentence text,
    source_task_id uuid,
    tags json,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.word_books OWNER TO postgres;

-- Name: crdt_operation_log id; Type: DEFAULT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.crdt_operation_log ALTER COLUMN id SET DEFAULT nextval('public.crdt_operation_log_id_seq'::regclass);


-- Name: subjects id; Type: DEFAULT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.subjects ALTER COLUMN id SET DEFAULT nextval('public.subjects_id_seq'::regclass);


-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


-- Name: behavior_patterns behavior_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.behavior_patterns
    ADD CONSTRAINT behavior_patterns_pkey PRIMARY KEY (id);


-- Name: behavioral_outcomes behavioral_outcomes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.behavioral_outcomes
    ADD CONSTRAINT behavioral_outcomes_pkey PRIMARY KEY (id);


-- Name: broadcast_messages broadcast_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.broadcast_messages
    ADD CONSTRAINT broadcast_messages_pkey PRIMARY KEY (id);


-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id, created_at);


-- Name: cognitive_fragments cognitive_fragments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.cognitive_fragments
    ADD CONSTRAINT cognitive_fragments_pkey PRIMARY KEY (id);


-- Name: collaborative_galaxies collaborative_galaxies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.collaborative_galaxies
    ADD CONSTRAINT collaborative_galaxies_pkey PRIMARY KEY (id);


-- Name: compliance_check_logs compliance_check_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.compliance_check_logs
    ADD CONSTRAINT compliance_check_logs_pkey PRIMARY KEY (id);


-- Name: context_budget_profiles context_budget_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.context_budget_profiles
    ADD CONSTRAINT context_budget_profiles_pkey PRIMARY KEY (id);


-- Name: context_pack_feedback context_pack_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.context_pack_feedback
    ADD CONSTRAINT context_pack_feedback_pkey PRIMARY KEY (id);


-- Name: context_pack_runs context_pack_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.context_pack_runs
    ADD CONSTRAINT context_pack_runs_pkey PRIMARY KEY (id);


-- Name: crdt_operation_log crdt_operation_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.crdt_operation_log
    ADD CONSTRAINT crdt_operation_log_pkey PRIMARY KEY (id);


-- Name: crdt_snapshots crdt_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.crdt_snapshots
    ADD CONSTRAINT crdt_snapshots_pkey PRIMARY KEY (galaxy_id);


-- Name: crypto_shredding_certificates crypto_shredding_certificates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.crypto_shredding_certificates
    ADD CONSTRAINT crypto_shredding_certificates_pkey PRIMARY KEY (id);


-- Name: curiosity_capsules curiosity_capsules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.curiosity_capsules
    ADD CONSTRAINT curiosity_capsules_pkey PRIMARY KEY (id);


-- Name: data_access_logs data_access_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.data_access_logs
    ADD CONSTRAINT data_access_logs_pkey PRIMARY KEY (id);


-- Name: decision_records decision_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.decision_records
    ADD CONSTRAINT decision_records_pkey PRIMARY KEY (id);


-- Name: dictionary_entries dictionary_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.dictionary_entries
    ADD CONSTRAINT dictionary_entries_pkey PRIMARY KEY (id);


-- Name: dlq_replay_audit_logs dlq_replay_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.dlq_replay_audit_logs
    ADD CONSTRAINT dlq_replay_audit_logs_pkey PRIMARY KEY (id);


-- Name: document_chunks document_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_pkey PRIMARY KEY (id);


-- Name: episodic_memories episodic_memories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.episodic_memories
    ADD CONSTRAINT episodic_memories_pkey PRIMARY KEY (id);


-- Name: error_records error_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.error_records
    ADD CONSTRAINT error_records_pkey PRIMARY KEY (id);


-- Name: event_outbox event_outbox_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.event_outbox
    ADD CONSTRAINT event_outbox_pkey PRIMARY KEY (id);


-- Name: event_store event_store_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.event_store
    ADD CONSTRAINT event_store_pkey PRIMARY KEY (id);


-- Name: expansion_feedback expansion_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.expansion_feedback
    ADD CONSTRAINT expansion_feedback_pkey PRIMARY KEY (id);


-- Name: focus_sessions focus_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.focus_sessions
    ADD CONSTRAINT focus_sessions_pkey PRIMARY KEY (id);


-- Name: friendships friendships_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.friendships
    ADD CONSTRAINT friendships_pkey PRIMARY KEY (id);


-- Name: galaxy_user_permissions galaxy_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.galaxy_user_permissions
    ADD CONSTRAINT galaxy_user_permissions_pkey PRIMARY KEY (galaxy_id, user_id);


-- Name: group_files group_files_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_files
    ADD CONSTRAINT group_files_pkey PRIMARY KEY (id);


-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (id);


-- Name: group_messages group_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_pkey PRIMARY KEY (id);


-- Name: group_task_claims group_task_claims_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_task_claims
    ADD CONSTRAINT group_task_claims_pkey PRIMARY KEY (id);


-- Name: group_tasks group_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_tasks
    ADD CONSTRAINT group_tasks_pkey PRIMARY KEY (id);


-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


-- Name: idempotency_keys idempotency_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (key);


-- Name: intervention_audit_logs intervention_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.intervention_audit_logs
    ADD CONSTRAINT intervention_audit_logs_pkey PRIMARY KEY (id);


-- Name: intervention_feedback intervention_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.intervention_feedback
    ADD CONSTRAINT intervention_feedback_pkey PRIMARY KEY (id);


-- Name: intervention_requests intervention_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.intervention_requests
    ADD CONSTRAINT intervention_requests_pkey PRIMARY KEY (id);


-- Name: intervention_templates intervention_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.intervention_templates
    ADD CONSTRAINT intervention_templates_pkey PRIMARY KEY (id);


-- Name: intervention_templates intervention_templates_template_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.intervention_templates
    ADD CONSTRAINT intervention_templates_template_id_key UNIQUE (template_id);


-- Name: irt_item_parameters irt_item_parameters_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.irt_item_parameters
    ADD CONSTRAINT irt_item_parameters_pkey PRIMARY KEY (id);


-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


-- Name: knowledge_nodes knowledge_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.knowledge_nodes
    ADD CONSTRAINT knowledge_nodes_pkey PRIMARY KEY (id);


-- Name: legal_holds legal_holds_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.legal_holds
    ADD CONSTRAINT legal_holds_pkey PRIMARY KEY (id);


-- Name: login_attempts login_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.login_attempts
    ADD CONSTRAINT login_attempts_pkey PRIMARY KEY (id);


-- Name: ltm_daily_snapshots ltm_daily_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.ltm_daily_snapshots
    ADD CONSTRAINT ltm_daily_snapshots_pkey PRIMARY KEY (id);


-- Name: ltm_daily_snapshots ltm_daily_snapshots_snapshot_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.ltm_daily_snapshots
    ADD CONSTRAINT ltm_daily_snapshots_snapshot_date_key UNIQUE (snapshot_date);


-- Name: mastery_audit_log mastery_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.mastery_audit_log
    ADD CONSTRAINT mastery_audit_log_pkey PRIMARY KEY (id);


-- Name: memory_corrections memory_corrections_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.memory_corrections
    ADD CONSTRAINT memory_corrections_pkey PRIMARY KEY (id);


-- Name: memory_goals memory_goals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.memory_goals
    ADD CONSTRAINT memory_goals_pkey PRIMARY KEY (id);


-- Name: memory_preferences memory_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.memory_preferences
    ADD CONSTRAINT memory_preferences_pkey PRIMARY KEY (id);


-- Name: memory_preferences memory_preferences_user_id_pref_key_version_key; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.memory_preferences
    ADD CONSTRAINT memory_preferences_user_id_pref_key_version_key UNIQUE (user_id, pref_key, version);


-- Name: memory_rank_policies memory_rank_policies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.memory_rank_policies
    ADD CONSTRAINT memory_rank_policies_pkey PRIMARY KEY (id);


-- Name: message_favorites message_favorites_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.message_favorites
    ADD CONSTRAINT message_favorites_pkey PRIMARY KEY (id);


-- Name: message_reports message_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.message_reports
    ADD CONSTRAINT message_reports_pkey PRIMARY KEY (id);


-- Name: nightly_reviews nightly_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.nightly_reviews
    ADD CONSTRAINT nightly_reviews_pkey PRIMARY KEY (id);


-- Name: node_expansion_queue node_expansion_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_pkey PRIMARY KEY (id);


-- Name: node_relations node_relations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.node_relations
    ADD CONSTRAINT node_relations_pkey PRIMARY KEY (id);


-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


-- Name: offline_message_queue offline_message_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.offline_message_queue
    ADD CONSTRAINT offline_message_queue_pkey PRIMARY KEY (id);


-- Name: outbox_events outbox_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.outbox_events
    ADD CONSTRAINT outbox_events_pkey PRIMARY KEY (id);


-- Name: passive_signals passive_signals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.passive_signals
    ADD CONSTRAINT passive_signals_pkey PRIMARY KEY (id);


-- Name: persona_snapshots persona_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.persona_snapshots
    ADD CONSTRAINT persona_snapshots_pkey PRIMARY KEY (id);


-- Name: plans plans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.plans
    ADD CONSTRAINT plans_pkey PRIMARY KEY (id);


-- Name: post_likes post_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.post_likes
    ADD CONSTRAINT post_likes_pkey PRIMARY KEY (id);


-- Name: posts posts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_pkey PRIMARY KEY (id);


-- Name: private_messages private_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_pkey PRIMARY KEY (id);


-- Name: processed_events processed_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.processed_events
    ADD CONSTRAINT processed_events_pkey PRIMARY KEY (event_id, consumer_group);


-- Name: projection_metadata projection_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.projection_metadata
    ADD CONSTRAINT projection_metadata_pkey PRIMARY KEY (projection_name);


-- Name: projection_snapshots projection_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.projection_snapshots
    ADD CONSTRAINT projection_snapshots_pkey PRIMARY KEY (id);


-- Name: push_histories push_histories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.push_histories
    ADD CONSTRAINT push_histories_pkey PRIMARY KEY (id);


-- Name: push_preferences push_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.push_preferences
    ADD CONSTRAINT push_preferences_pkey PRIMARY KEY (id);


-- Name: response_feedback response_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.response_feedback
    ADD CONSTRAINT response_feedback_pkey PRIMARY KEY (id);


-- Name: scaffolding_states scaffolding_states_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.scaffolding_states
    ADD CONSTRAINT scaffolding_states_pkey PRIMARY KEY (id);


-- Name: scaffolding_states scaffolding_states_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.scaffolding_states
    ADD CONSTRAINT scaffolding_states_user_id_key UNIQUE (user_id);


-- Name: security_audit_logs security_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.security_audit_logs
    ADD CONSTRAINT security_audit_logs_pkey PRIMARY KEY (id);


-- Name: semantic_links semantic_links_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.semantic_links
    ADD CONSTRAINT semantic_links_pkey PRIMARY KEY (id);


-- Name: shared_resources shared_resources_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_pkey PRIMARY KEY (id);


-- Name: stored_files stored_files_object_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.stored_files
    ADD CONSTRAINT stored_files_object_key_key UNIQUE (object_key);


-- Name: stored_files stored_files_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.stored_files
    ADD CONSTRAINT stored_files_pkey PRIMARY KEY (id);


-- Name: strategy_nodes strategy_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.strategy_nodes
    ADD CONSTRAINT strategy_nodes_pkey PRIMARY KEY (id);


-- Name: study_records study_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.study_records
    ADD CONSTRAINT study_records_pkey PRIMARY KEY (id);


-- Name: subjects subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_pkey PRIMARY KEY (id);


-- Name: system_config_change_logs system_config_change_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.system_config_change_logs
    ADD CONSTRAINT system_config_change_logs_pkey PRIMARY KEY (id);


-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


-- Name: token_usage token_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_pkey PRIMARY KEY (id);


-- Name: token_usage token_usage_request_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_request_id_key UNIQUE (request_id);


-- Name: tracking_events tracking_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.tracking_events
    ADD CONSTRAINT tracking_events_pkey PRIMARY KEY (id);


-- Name: context_budget_profiles uq_context_budget_profiles_intent_bucket; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.context_budget_profiles
    ADD CONSTRAINT uq_context_budget_profiles_intent_bucket UNIQUE (intent, bucket);


-- Name: friendships uq_friendship; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.friendships
    ADD CONSTRAINT uq_friendship UNIQUE (user_id, friend_id);


-- Name: group_files uq_group_files_group_file; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_files
    ADD CONSTRAINT uq_group_files_group_file UNIQUE (group_id, file_id);


-- Name: group_members uq_group_member; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT uq_group_member UNIQUE (group_id, user_id);


-- Name: intervention_feedback uq_intervention_feedback_idempotency; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.intervention_feedback
    ADD CONSTRAINT uq_intervention_feedback_idempotency UNIQUE (user_id, request_id, feedback_type, idempotency_key);


-- Name: offline_message_queue uq_offline_queue_nonce; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.offline_message_queue
    ADD CONSTRAINT uq_offline_queue_nonce UNIQUE (user_id, client_nonce);


-- Name: post_likes uq_post_like; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.post_likes
    ADD CONSTRAINT uq_post_like UNIQUE (user_id, post_id);


-- Name: projection_snapshots uq_projection_snapshot; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.projection_snapshots
    ADD CONSTRAINT uq_projection_snapshot UNIQUE (projection_name, aggregate_id);


-- Name: response_feedback uq_response_feedback_user_response; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.response_feedback
    ADD CONSTRAINT uq_response_feedback_user_response UNIQUE (user_id, response_id);


-- Name: group_task_claims uq_task_claim; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_task_claims
    ADD CONSTRAINT uq_task_claim UNIQUE (group_task_id, user_id);


-- Name: user_daily_metrics uq_user_daily_metric; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_daily_metrics
    ADD CONSTRAINT uq_user_daily_metric UNIQUE (user_id, date);


-- Name: user_memory_settings uq_user_memory_settings_user; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_memory_settings
    ADD CONSTRAINT uq_user_memory_settings_user UNIQUE (user_id);


-- Name: user_preferences_center uq_user_preferences_center_user; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_preferences_center
    ADD CONSTRAINT uq_user_preferences_center_user UNIQUE (user_id);


-- Name: word_books uq_user_word; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.word_books
    ADD CONSTRAINT uq_user_word UNIQUE (user_id, word);


-- Name: user_daily_metrics user_daily_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_daily_metrics
    ADD CONSTRAINT user_daily_metrics_pkey PRIMARY KEY (id);


-- Name: user_encryption_keys user_encryption_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_encryption_keys
    ADD CONSTRAINT user_encryption_keys_pkey PRIMARY KEY (id);


-- Name: user_intervention_settings user_intervention_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_intervention_settings
    ADD CONSTRAINT user_intervention_settings_pkey PRIMARY KEY (id);


-- Name: user_irt_ability user_irt_ability_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_irt_ability
    ADD CONSTRAINT user_irt_ability_pkey PRIMARY KEY (id);


-- Name: user_memory_settings user_memory_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_memory_settings
    ADD CONSTRAINT user_memory_settings_pkey PRIMARY KEY (id);


-- Name: user_node_status user_node_status_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_node_status
    ADD CONSTRAINT user_node_status_pkey PRIMARY KEY (user_id, node_id);


-- Name: user_persona_keys user_persona_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_persona_keys
    ADD CONSTRAINT user_persona_keys_pkey PRIMARY KEY (id);


-- Name: user_preferences_center user_preferences_center_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_preferences_center
    ADD CONSTRAINT user_preferences_center_pkey PRIMARY KEY (id);


-- Name: user_state_snapshots user_state_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_state_snapshots
    ADD CONSTRAINT user_state_snapshots_pkey PRIMARY KEY (id);


-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


-- Name: word_books word_books_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.word_books
    ADD CONSTRAINT word_books_pkey PRIMARY KEY (id);


-- Name: idx_chat_created_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_chat_created_at ON public.chat_messages USING btree (created_at);


-- Name: idx_chat_role; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_chat_role ON public.chat_messages USING btree (role);


-- Name: idx_chat_session_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_chat_session_id ON public.chat_messages USING btree (session_id);


-- Name: idx_chat_task_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_chat_task_id ON public.chat_messages USING btree (task_id);


-- Name: idx_chat_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_chat_user_id ON public.chat_messages USING btree (user_id);


-- Name: idx_claim_task; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_claim_task ON public.group_task_claims USING btree (group_task_id);


-- Name: idx_claim_user; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_claim_user ON public.group_task_claims USING btree (user_id);


-- Name: idx_context_budget_profiles_intent; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_context_budget_profiles_intent ON public.context_budget_profiles USING btree (intent);


-- Name: idx_context_pack_runs_intent; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_context_pack_runs_intent ON public.context_pack_runs USING btree (intent);


-- Name: idx_context_pack_runs_user_created; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_context_pack_runs_user_created ON public.context_pack_runs USING btree (user_id, created_at);


-- Name: idx_dict_word; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_dict_word ON public.dictionary_entries USING btree (word);


-- Name: idx_document_chunks_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_document_chunks_embedding_hnsw ON public.document_chunks USING hnsw (embedding public.vector_cosine_ops) WHERE (embedding IS NOT NULL);


-- Name: idx_episodic_memories_evidence_missing; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_episodic_memories_evidence_missing ON public.episodic_memories USING btree (evidence_missing);


-- Name: idx_episodic_memories_evidence_score; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_episodic_memories_evidence_score ON public.episodic_memories USING btree (evidence_score);


-- Name: idx_episodic_memories_user_occurred; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_episodic_memories_user_occurred ON public.episodic_memories USING btree (user_id, occurred_at);


-- Name: idx_error_records_cognitive_tags; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_error_records_cognitive_tags ON public.error_records USING gin (cognitive_tags);


-- Name: idx_errors_subject; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_errors_subject ON public.error_records USING btree (subject_code);


-- Name: idx_errors_user_review; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_errors_user_review ON public.error_records USING btree (user_id, next_review_at) WHERE (mastery_level < (1.0)::double precision);


-- Name: idx_focus_user_time; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_focus_user_time ON public.focus_sessions USING btree (user_id, start_time);


-- Name: idx_friendship_friend; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_friendship_friend ON public.friendships USING btree (friend_id);


-- Name: idx_friendship_status; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_friendship_status ON public.friendships USING btree (status);


-- Name: idx_friendship_user; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_friendship_user ON public.friendships USING btree (user_id);


-- Name: idx_group_files_category; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_group_files_category ON public.group_files USING btree (category);


-- Name: idx_group_files_file; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_group_files_file ON public.group_files USING btree (file_id);


-- Name: idx_group_files_group; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_group_files_group ON public.group_files USING btree (group_id);


-- Name: idx_group_files_shared_by; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_group_files_shared_by ON public.group_files USING btree (shared_by_id);


-- Name: idx_group_public; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_group_public ON public.groups USING btree (is_public);


-- Name: idx_group_task_group; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_group_task_group ON public.group_tasks USING btree (group_id);


-- Name: idx_group_type; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_group_type ON public.groups USING btree (type);


-- Name: idx_idempotency_expires; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_idempotency_expires ON public.idempotency_keys USING btree (expires_at);


-- Name: idx_jobs_status; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_jobs_status ON public.jobs USING btree (status);


-- Name: idx_jobs_status_timeout; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_jobs_status_timeout ON public.jobs USING btree (status, timeout_at) WHERE ((status)::text = 'running'::text);


-- Name: idx_jobs_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_jobs_user_id ON public.jobs USING btree (user_id);


-- Name: idx_knowledge_nodes_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_knowledge_nodes_embedding_hnsw ON public.knowledge_nodes USING hnsw (embedding public.vector_cosine_ops) WHERE (embedding IS NOT NULL);


-- Name: idx_ltm_daily_snapshots_date; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX idx_ltm_daily_snapshots_date ON public.ltm_daily_snapshots USING btree (snapshot_date);


-- Name: idx_member_group; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_member_group ON public.group_members USING btree (group_id);


-- Name: idx_member_user; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_member_user ON public.group_members USING btree (user_id);


-- Name: idx_memory_corrections_user_type_created; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_memory_corrections_user_type_created ON public.memory_corrections USING btree (user_id, memory_type, created_at);


-- Name: idx_memory_goals_evidence_missing; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_memory_goals_evidence_missing ON public.memory_goals USING btree (evidence_missing);


-- Name: idx_memory_goals_evidence_score; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_memory_goals_evidence_score ON public.memory_goals USING btree (evidence_score);


-- Name: idx_memory_goals_expires_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_memory_goals_expires_at ON public.memory_goals USING btree (expires_at);


-- Name: idx_memory_goals_user_status_target; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_memory_goals_user_status_target ON public.memory_goals USING btree (user_id, status, target_date);


-- Name: idx_memory_preferences_evidence_missing; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_memory_preferences_evidence_missing ON public.memory_preferences USING btree (evidence_missing);


-- Name: idx_memory_preferences_evidence_score; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_memory_preferences_evidence_score ON public.memory_preferences USING btree (evidence_score);


-- Name: idx_memory_preferences_user_pref; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_memory_preferences_user_pref ON public.memory_preferences USING btree (user_id, pref_key);


-- Name: idx_message_favorites_user; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_message_favorites_user ON public.message_favorites USING btree (user_id);


-- Name: idx_message_group_thread; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_message_group_thread ON public.group_messages USING btree (group_id, thread_root_id, created_at);


-- Name: idx_message_group_time; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_message_group_time ON public.group_messages USING btree (group_id, created_at);


-- Name: idx_message_reports_group_msg; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_message_reports_group_msg ON public.message_reports USING btree (group_message_id);


-- Name: idx_message_reports_status; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_message_reports_status ON public.message_reports USING btree (status);


-- Name: idx_offline_queue_user_status; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_offline_queue_user_status ON public.offline_message_queue USING btree (user_id, status);


-- Name: idx_outbox_aggregate; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_outbox_aggregate ON public.event_outbox USING btree (aggregate_type, aggregate_id);


-- Name: idx_outbox_published; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_outbox_published ON public.event_outbox USING btree (published_at);


-- Name: idx_plans_is_active; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_plans_is_active ON public.plans USING btree (is_active);


-- Name: idx_plans_target_date; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_plans_target_date ON public.plans USING btree (target_date);


-- Name: idx_plans_type; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_plans_type ON public.plans USING btree (type);


-- Name: idx_plans_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_plans_user_id ON public.plans USING btree (user_id);


-- Name: idx_post_like_post; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_post_like_post ON public.post_likes USING btree (post_id);


-- Name: idx_post_like_user; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_post_like_user ON public.post_likes USING btree (user_id);


-- Name: idx_private_message_conversation; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_private_message_conversation ON public.private_messages USING btree (sender_id, receiver_id, created_at);


-- Name: idx_private_message_receiver_unread; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_private_message_receiver_unread ON public.private_messages USING btree (receiver_id, is_read);


-- Name: idx_private_message_thread; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_private_message_thread ON public.private_messages USING btree (sender_id, receiver_id, thread_root_id, created_at);


-- Name: idx_share_group; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_share_group ON public.shared_resources USING btree (group_id);


-- Name: idx_share_resource_capsule; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_share_resource_capsule ON public.shared_resources USING btree (curiosity_capsule_id);


-- Name: idx_share_resource_pattern; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_share_resource_pattern ON public.shared_resources USING btree (behavior_pattern_id);


-- Name: idx_share_resource_plan; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_share_resource_plan ON public.shared_resources USING btree (plan_id);


-- Name: idx_share_target_user; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_share_target_user ON public.shared_resources USING btree (target_user_id);


-- Name: idx_snapshot_projection_aggregate; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_snapshot_projection_aggregate ON public.projection_snapshots USING btree (projection_name, aggregate_id);


-- Name: idx_store_aggregate; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_store_aggregate ON public.event_store USING btree (aggregate_type, aggregate_id);


-- Name: idx_store_aggregate_seq; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX idx_store_aggregate_seq ON public.event_store USING btree (aggregate_type, aggregate_id, sequence_number);


-- Name: idx_tasks_created_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_tasks_created_at ON public.tasks USING btree (created_at);


-- Name: idx_tasks_due_date; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_tasks_due_date ON public.tasks USING btree (due_date);


-- Name: idx_tasks_plan_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_tasks_plan_id ON public.tasks USING btree (plan_id);


-- Name: idx_tasks_status; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_tasks_status ON public.tasks USING btree (status);


-- Name: idx_tasks_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_tasks_user_id ON public.tasks USING btree (user_id);


-- Name: idx_token_usage_created_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_token_usage_created_at ON public.token_usage USING btree (created_at);


-- Name: idx_token_usage_session_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_token_usage_session_id ON public.token_usage USING btree (session_id);


-- Name: idx_token_usage_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_token_usage_user_id ON public.token_usage USING btree (user_id);


-- Name: idx_user_encryption_keys_user; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_user_encryption_keys_user ON public.user_encryption_keys USING btree (user_id, is_active);


-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_users_email ON public.users USING btree (email);


-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_users_username ON public.users USING btree (username);


-- Name: idx_wordbook_review; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX idx_wordbook_review ON public.word_books USING btree (user_id, next_review_at);


-- Name: ix_behavior_patterns_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_behavior_patterns_deleted_at ON public.behavior_patterns USING btree (deleted_at);


-- Name: ix_behavior_patterns_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_behavior_patterns_user_id ON public.behavior_patterns USING btree (user_id);


-- Name: ix_behavioral_outcomes_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_behavioral_outcomes_deleted_at ON public.behavioral_outcomes USING btree (deleted_at);


-- Name: ix_behavioral_outcomes_intervention_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_behavioral_outcomes_intervention_id ON public.behavioral_outcomes USING btree (intervention_id);


-- Name: ix_behavioral_outcomes_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_behavioral_outcomes_user_id ON public.behavioral_outcomes USING btree (user_id);


-- Name: ix_broadcast_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_broadcast_messages_deleted_at ON public.broadcast_messages USING btree (deleted_at);


-- Name: ix_broadcast_messages_sender_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_broadcast_messages_sender_id ON public.broadcast_messages USING btree (sender_id);


-- Name: ix_chat_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_chat_messages_deleted_at ON public.chat_messages USING btree (deleted_at);


-- Name: ix_chat_messages_session_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_chat_messages_session_id ON public.chat_messages USING btree (session_id);


-- Name: ix_chat_messages_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_chat_messages_user_id ON public.chat_messages USING btree (user_id);


-- Name: ix_cognitive_fragments_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_cognitive_fragments_deleted_at ON public.cognitive_fragments USING btree (deleted_at);


-- Name: ix_cognitive_fragments_source_event_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_cognitive_fragments_source_event_id ON public.cognitive_fragments USING btree (source_event_id);


-- Name: ix_cognitive_fragments_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_cognitive_fragments_user_id ON public.cognitive_fragments USING btree (user_id);


-- Name: ix_collaborative_galaxies_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_collaborative_galaxies_deleted_at ON public.collaborative_galaxies USING btree (deleted_at);


-- Name: ix_compliance_check_logs_check_type; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_compliance_check_logs_check_type ON public.compliance_check_logs USING btree (check_type);


-- Name: ix_compliance_check_logs_executed_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_compliance_check_logs_executed_at ON public.compliance_check_logs USING btree (executed_at);


-- Name: ix_compliance_check_logs_executed_by; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_compliance_check_logs_executed_by ON public.compliance_check_logs USING btree (executed_by);


-- Name: ix_compliance_check_logs_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_compliance_check_logs_id ON public.compliance_check_logs USING btree (id);


-- Name: ix_context_budget_profiles_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_context_budget_profiles_deleted_at ON public.context_budget_profiles USING btree (deleted_at);


-- Name: ix_context_pack_feedback_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_context_pack_feedback_deleted_at ON public.context_pack_feedback USING btree (deleted_at);


-- Name: ix_context_pack_feedback_pack_run_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_context_pack_feedback_pack_run_id ON public.context_pack_feedback USING btree (pack_run_id);


-- Name: ix_context_pack_runs_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_context_pack_runs_deleted_at ON public.context_pack_runs USING btree (deleted_at);


-- Name: ix_crdt_operation_log_galaxy_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_crdt_operation_log_galaxy_id ON public.crdt_operation_log USING btree (galaxy_id);


-- Name: ix_crdt_operation_log_timestamp; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_crdt_operation_log_timestamp ON public.crdt_operation_log USING btree ("timestamp");


-- Name: ix_crypto_shredding_certificates_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_crypto_shredding_certificates_deleted_at ON public.crypto_shredding_certificates USING btree (deleted_at);


-- Name: ix_crypto_shredding_certificates_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_crypto_shredding_certificates_user_id ON public.crypto_shredding_certificates USING btree (user_id);


-- Name: ix_curiosity_capsules_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_curiosity_capsules_deleted_at ON public.curiosity_capsules USING btree (deleted_at);


-- Name: ix_curiosity_capsules_related_task_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_curiosity_capsules_related_task_id ON public.curiosity_capsules USING btree (related_task_id);


-- Name: ix_curiosity_capsules_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_curiosity_capsules_user_id ON public.curiosity_capsules USING btree (user_id);


-- Name: ix_data_access_logs_accessed_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_data_access_logs_accessed_at ON public.data_access_logs USING btree (accessed_at);


-- Name: ix_data_access_logs_action; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_data_access_logs_action ON public.data_access_logs USING btree (action);


-- Name: ix_data_access_logs_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_data_access_logs_id ON public.data_access_logs USING btree (id);


-- Name: ix_data_access_logs_ip_address; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_data_access_logs_ip_address ON public.data_access_logs USING btree (ip_address);


-- Name: ix_data_access_logs_resource_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_data_access_logs_resource_id ON public.data_access_logs USING btree (resource_id);


-- Name: ix_data_access_logs_resource_type; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_data_access_logs_resource_type ON public.data_access_logs USING btree (resource_type);


-- Name: ix_data_access_logs_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_data_access_logs_user_id ON public.data_access_logs USING btree (user_id);


-- Name: ix_decision_records_created_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_decision_records_created_at ON public.decision_records USING btree (created_at);


-- Name: ix_decision_records_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_decision_records_deleted_at ON public.decision_records USING btree (deleted_at);


-- Name: ix_decision_records_module; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_decision_records_module ON public.decision_records USING btree (module);


-- Name: ix_decision_records_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_decision_records_user_id ON public.decision_records USING btree (user_id);


-- Name: ix_dictionary_entries_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_dictionary_entries_deleted_at ON public.dictionary_entries USING btree (deleted_at);


-- Name: ix_dictionary_entries_word; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_dictionary_entries_word ON public.dictionary_entries USING btree (word);


-- Name: ix_dlq_replay_audit_logs_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_dlq_replay_audit_logs_deleted_at ON public.dlq_replay_audit_logs USING btree (deleted_at);


-- Name: ix_dlq_replay_audit_logs_message_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_dlq_replay_audit_logs_message_id ON public.dlq_replay_audit_logs USING btree (message_id);


-- Name: ix_document_chunks_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_document_chunks_deleted_at ON public.document_chunks USING btree (deleted_at);


-- Name: ix_document_chunks_file_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_document_chunks_file_id ON public.document_chunks USING btree (file_id);


-- Name: ix_document_chunks_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_document_chunks_user_id ON public.document_chunks USING btree (user_id);


-- Name: ix_episodic_memories_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_episodic_memories_deleted_at ON public.episodic_memories USING btree (deleted_at);


-- Name: ix_expansion_feedback_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_expansion_feedback_deleted_at ON public.expansion_feedback USING btree (deleted_at);


-- Name: ix_expansion_feedback_expansion_queue_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_expansion_feedback_expansion_queue_id ON public.expansion_feedback USING btree (expansion_queue_id);


-- Name: ix_expansion_feedback_trigger_node_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_expansion_feedback_trigger_node_id ON public.expansion_feedback USING btree (trigger_node_id);


-- Name: ix_expansion_feedback_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_expansion_feedback_user_id ON public.expansion_feedback USING btree (user_id);


-- Name: ix_focus_sessions_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_focus_sessions_deleted_at ON public.focus_sessions USING btree (deleted_at);


-- Name: ix_focus_sessions_task_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_focus_sessions_task_id ON public.focus_sessions USING btree (task_id);


-- Name: ix_focus_sessions_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_focus_sessions_user_id ON public.focus_sessions USING btree (user_id);


-- Name: ix_friendships_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_friendships_deleted_at ON public.friendships USING btree (deleted_at);


-- Name: ix_friendships_friend_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_friendships_friend_id ON public.friendships USING btree (friend_id);


-- Name: ix_friendships_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_friendships_user_id ON public.friendships USING btree (user_id);


-- Name: ix_group_files_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_files_deleted_at ON public.group_files USING btree (deleted_at);


-- Name: ix_group_files_file_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_files_file_id ON public.group_files USING btree (file_id);


-- Name: ix_group_files_group_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_files_group_id ON public.group_files USING btree (group_id);


-- Name: ix_group_files_shared_by_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_files_shared_by_id ON public.group_files USING btree (shared_by_id);


-- Name: ix_group_members_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_members_deleted_at ON public.group_members USING btree (deleted_at);


-- Name: ix_group_members_group_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_members_group_id ON public.group_members USING btree (group_id);


-- Name: ix_group_members_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_members_user_id ON public.group_members USING btree (user_id);


-- Name: ix_group_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_messages_deleted_at ON public.group_messages USING btree (deleted_at);


-- Name: ix_group_messages_group_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_messages_group_id ON public.group_messages USING btree (group_id);


-- Name: ix_group_messages_thread_root_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_messages_thread_root_id ON public.group_messages USING btree (thread_root_id);


-- Name: ix_group_task_claims_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_task_claims_deleted_at ON public.group_task_claims USING btree (deleted_at);


-- Name: ix_group_task_claims_group_task_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_task_claims_group_task_id ON public.group_task_claims USING btree (group_task_id);


-- Name: ix_group_task_claims_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_task_claims_user_id ON public.group_task_claims USING btree (user_id);


-- Name: ix_group_tasks_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_tasks_deleted_at ON public.group_tasks USING btree (deleted_at);


-- Name: ix_group_tasks_group_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_group_tasks_group_id ON public.group_tasks USING btree (group_id);


-- Name: ix_groups_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_groups_deleted_at ON public.groups USING btree (deleted_at);


-- Name: ix_idempotency_keys_expires_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_idempotency_keys_expires_at ON public.idempotency_keys USING btree (expires_at);


-- Name: ix_idempotency_keys_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_idempotency_keys_user_id ON public.idempotency_keys USING btree (user_id);


-- Name: ix_intervention_audit_logs_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_audit_logs_deleted_at ON public.intervention_audit_logs USING btree (deleted_at);


-- Name: ix_intervention_audit_logs_occurred_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_audit_logs_occurred_at ON public.intervention_audit_logs USING btree (occurred_at);


-- Name: ix_intervention_audit_logs_request_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_audit_logs_request_id ON public.intervention_audit_logs USING btree (request_id);


-- Name: ix_intervention_audit_logs_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_audit_logs_user_id ON public.intervention_audit_logs USING btree (user_id);


-- Name: ix_intervention_feedback_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_feedback_deleted_at ON public.intervention_feedback USING btree (deleted_at);


-- Name: ix_intervention_feedback_feedback_type; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_feedback_feedback_type ON public.intervention_feedback USING btree (feedback_type);


-- Name: ix_intervention_feedback_request_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_feedback_request_id ON public.intervention_feedback USING btree (request_id);


-- Name: ix_intervention_feedback_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_feedback_user_id ON public.intervention_feedback USING btree (user_id);


-- Name: ix_intervention_requests_dedupe_key; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_requests_dedupe_key ON public.intervention_requests USING btree (dedupe_key);


-- Name: ix_intervention_requests_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_requests_deleted_at ON public.intervention_requests USING btree (deleted_at);


-- Name: ix_intervention_requests_status; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_requests_status ON public.intervention_requests USING btree (status);


-- Name: ix_intervention_requests_topic; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_requests_topic ON public.intervention_requests USING btree (topic);


-- Name: ix_intervention_requests_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_requests_user_id ON public.intervention_requests USING btree (user_id);


-- Name: ix_intervention_templates_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_templates_deleted_at ON public.intervention_templates USING btree (deleted_at);


-- Name: ix_intervention_templates_intent_type; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_intervention_templates_intent_type ON public.intervention_templates USING btree (intent_type);


-- Name: ix_intervention_templates_template_id; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_intervention_templates_template_id ON public.intervention_templates USING btree (template_id);


-- Name: ix_irt_item_parameters_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_irt_item_parameters_deleted_at ON public.irt_item_parameters USING btree (deleted_at);


-- Name: ix_irt_item_parameters_question_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_irt_item_parameters_question_id ON public.irt_item_parameters USING btree (question_id);


-- Name: ix_irt_item_parameters_subject_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_irt_item_parameters_subject_id ON public.irt_item_parameters USING btree (subject_id);


-- Name: ix_jobs_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_jobs_deleted_at ON public.jobs USING btree (deleted_at);


-- Name: ix_jobs_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_jobs_user_id ON public.jobs USING btree (user_id);


-- Name: ix_knowledge_nodes_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_knowledge_nodes_deleted_at ON public.knowledge_nodes USING btree (deleted_at);


-- Name: ix_knowledge_nodes_parent_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_knowledge_nodes_parent_id ON public.knowledge_nodes USING btree (parent_id);


-- Name: ix_knowledge_nodes_position_x; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_knowledge_nodes_position_x ON public.knowledge_nodes USING btree (position_x);


-- Name: ix_knowledge_nodes_position_y; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_knowledge_nodes_position_y ON public.knowledge_nodes USING btree (position_y);


-- Name: ix_knowledge_nodes_subject_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_knowledge_nodes_subject_id ON public.knowledge_nodes USING btree (subject_id);


-- Name: ix_legal_holds_case_ref; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_legal_holds_case_ref ON public.legal_holds USING btree (case_ref);


-- Name: ix_legal_holds_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_legal_holds_deleted_at ON public.legal_holds USING btree (deleted_at);


-- Name: ix_legal_holds_device_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_legal_holds_device_id ON public.legal_holds USING btree (device_id);


-- Name: ix_legal_holds_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_legal_holds_user_id ON public.legal_holds USING btree (user_id);


-- Name: ix_login_attempts_attempted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_login_attempts_attempted_at ON public.login_attempts USING btree (attempted_at);


-- Name: ix_login_attempts_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_login_attempts_deleted_at ON public.login_attempts USING btree (deleted_at);


-- Name: ix_login_attempts_ip_address; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_login_attempts_ip_address ON public.login_attempts USING btree (ip_address);


-- Name: ix_login_attempts_success; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_login_attempts_success ON public.login_attempts USING btree (success);


-- Name: ix_login_attempts_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_login_attempts_user_id ON public.login_attempts USING btree (user_id);


-- Name: ix_login_attempts_username; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_login_attempts_username ON public.login_attempts USING btree (username);


-- Name: ix_memory_corrections_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_memory_corrections_deleted_at ON public.memory_corrections USING btree (deleted_at);


-- Name: ix_memory_goals_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_memory_goals_deleted_at ON public.memory_goals USING btree (deleted_at);


-- Name: ix_memory_preferences_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_memory_preferences_deleted_at ON public.memory_preferences USING btree (deleted_at);


-- Name: ix_memory_rank_policies_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_memory_rank_policies_deleted_at ON public.memory_rank_policies USING btree (deleted_at);


-- Name: ix_message_favorites_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_message_favorites_deleted_at ON public.message_favorites USING btree (deleted_at);


-- Name: ix_message_favorites_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_message_favorites_user_id ON public.message_favorites USING btree (user_id);


-- Name: ix_message_reports_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_message_reports_deleted_at ON public.message_reports USING btree (deleted_at);


-- Name: ix_message_reports_reporter_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_message_reports_reporter_id ON public.message_reports USING btree (reporter_id);


-- Name: ix_nightly_reviews_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_nightly_reviews_deleted_at ON public.nightly_reviews USING btree (deleted_at);


-- Name: ix_nightly_reviews_review_date; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_nightly_reviews_review_date ON public.nightly_reviews USING btree (review_date);


-- Name: ix_nightly_reviews_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_nightly_reviews_user_id ON public.nightly_reviews USING btree (user_id);


-- Name: ix_node_expansion_queue_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_node_expansion_queue_deleted_at ON public.node_expansion_queue USING btree (deleted_at);


-- Name: ix_node_expansion_queue_status; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_node_expansion_queue_status ON public.node_expansion_queue USING btree (status);


-- Name: ix_node_expansion_queue_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_node_expansion_queue_user_id ON public.node_expansion_queue USING btree (user_id);


-- Name: ix_node_relations_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_node_relations_deleted_at ON public.node_relations USING btree (deleted_at);


-- Name: ix_node_relations_source_node_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_node_relations_source_node_id ON public.node_relations USING btree (source_node_id);


-- Name: ix_node_relations_target_node_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_node_relations_target_node_id ON public.node_relations USING btree (target_node_id);


-- Name: ix_notifications_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_notifications_deleted_at ON public.notifications USING btree (deleted_at);


-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


-- Name: ix_offline_message_queue_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_offline_message_queue_deleted_at ON public.offline_message_queue USING btree (deleted_at);


-- Name: ix_offline_message_queue_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_offline_message_queue_user_id ON public.offline_message_queue USING btree (user_id);


-- Name: ix_passive_signals_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_passive_signals_deleted_at ON public.passive_signals USING btree (deleted_at);


-- Name: ix_passive_signals_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_passive_signals_user_id ON public.passive_signals USING btree (user_id);


-- Name: ix_persona_snapshots_audit_token; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_persona_snapshots_audit_token ON public.persona_snapshots USING btree (audit_token);


-- Name: ix_persona_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_persona_snapshots_deleted_at ON public.persona_snapshots USING btree (deleted_at);


-- Name: ix_persona_snapshots_persona_version; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_persona_snapshots_persona_version ON public.persona_snapshots USING btree (persona_version);


-- Name: ix_persona_snapshots_source_event_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_persona_snapshots_source_event_id ON public.persona_snapshots USING btree (source_event_id);


-- Name: ix_persona_snapshots_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_persona_snapshots_user_id ON public.persona_snapshots USING btree (user_id);


-- Name: ix_plans_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_plans_deleted_at ON public.plans USING btree (deleted_at);


-- Name: ix_plans_is_active; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_plans_is_active ON public.plans USING btree (is_active);


-- Name: ix_plans_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_plans_user_id ON public.plans USING btree (user_id);


-- Name: ix_post_likes_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_post_likes_deleted_at ON public.post_likes USING btree (deleted_at);


-- Name: ix_posts_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_posts_deleted_at ON public.posts USING btree (deleted_at);


-- Name: ix_posts_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_posts_user_id ON public.posts USING btree (user_id);


-- Name: ix_private_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_private_messages_deleted_at ON public.private_messages USING btree (deleted_at);


-- Name: ix_private_messages_receiver_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_private_messages_receiver_id ON public.private_messages USING btree (receiver_id);


-- Name: ix_private_messages_sender_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_private_messages_sender_id ON public.private_messages USING btree (sender_id);


-- Name: ix_private_messages_thread_root_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_private_messages_thread_root_id ON public.private_messages USING btree (thread_root_id);


-- Name: ix_push_histories_content_hash; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_push_histories_content_hash ON public.push_histories USING btree (content_hash);


-- Name: ix_push_histories_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_push_histories_deleted_at ON public.push_histories USING btree (deleted_at);


-- Name: ix_push_histories_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_push_histories_user_id ON public.push_histories USING btree (user_id);


-- Name: ix_push_preferences_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_push_preferences_deleted_at ON public.push_preferences USING btree (deleted_at);


-- Name: ix_push_preferences_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_push_preferences_user_id ON public.push_preferences USING btree (user_id);


-- Name: ix_response_feedback_created_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_response_feedback_created_at ON public.response_feedback USING btree (created_at);


-- Name: ix_response_feedback_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_response_feedback_deleted_at ON public.response_feedback USING btree (deleted_at);


-- Name: ix_response_feedback_response_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_response_feedback_response_id ON public.response_feedback USING btree (response_id);


-- Name: ix_response_feedback_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_response_feedback_user_id ON public.response_feedback USING btree (user_id);


-- Name: ix_response_feedback_workflow_prompt_created; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_response_feedback_workflow_prompt_created ON public.response_feedback USING btree (workflow_id, prompt_version, created_at);


-- Name: ix_scaffolding_states_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_scaffolding_states_deleted_at ON public.scaffolding_states USING btree (deleted_at);


-- Name: ix_scaffolding_states_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_scaffolding_states_user_id ON public.scaffolding_states USING btree (user_id);


-- Name: ix_security_audit_logs_event_type; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_security_audit_logs_event_type ON public.security_audit_logs USING btree (event_type);


-- Name: ix_security_audit_logs_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_security_audit_logs_id ON public.security_audit_logs USING btree (id);


-- Name: ix_security_audit_logs_ip_address; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_security_audit_logs_ip_address ON public.security_audit_logs USING btree (ip_address);


-- Name: ix_security_audit_logs_resource; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_security_audit_logs_resource ON public.security_audit_logs USING btree (resource);


-- Name: ix_security_audit_logs_threat_level; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_security_audit_logs_threat_level ON public.security_audit_logs USING btree (threat_level);


-- Name: ix_security_audit_logs_timestamp; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_security_audit_logs_timestamp ON public.security_audit_logs USING btree ("timestamp");


-- Name: ix_security_audit_logs_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_security_audit_logs_user_id ON public.security_audit_logs USING btree (user_id);


-- Name: ix_semantic_links_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_semantic_links_deleted_at ON public.semantic_links USING btree (deleted_at);


-- Name: ix_semantic_links_relation_type; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_semantic_links_relation_type ON public.semantic_links USING btree (relation_type);


-- Name: ix_semantic_links_source_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_semantic_links_source_id ON public.semantic_links USING btree (source_id);


-- Name: ix_semantic_links_source_type; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_semantic_links_source_type ON public.semantic_links USING btree (source_type);


-- Name: ix_semantic_links_target_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_semantic_links_target_id ON public.semantic_links USING btree (target_id);


-- Name: ix_semantic_links_target_type; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_semantic_links_target_type ON public.semantic_links USING btree (target_type);


-- Name: ix_shared_resources_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_shared_resources_deleted_at ON public.shared_resources USING btree (deleted_at);


-- Name: ix_shared_resources_group_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_shared_resources_group_id ON public.shared_resources USING btree (group_id);


-- Name: ix_shared_resources_target_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_shared_resources_target_user_id ON public.shared_resources USING btree (target_user_id);


-- Name: ix_stored_files_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_stored_files_deleted_at ON public.stored_files USING btree (deleted_at);


-- Name: ix_stored_files_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_stored_files_user_id ON public.stored_files USING btree (user_id);


-- Name: ix_strategy_nodes_content_hash; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_strategy_nodes_content_hash ON public.strategy_nodes USING btree (content_hash);


-- Name: ix_strategy_nodes_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_strategy_nodes_deleted_at ON public.strategy_nodes USING btree (deleted_at);


-- Name: ix_strategy_nodes_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_strategy_nodes_user_id ON public.strategy_nodes USING btree (user_id);


-- Name: ix_study_records_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_study_records_deleted_at ON public.study_records USING btree (deleted_at);


-- Name: ix_study_records_node_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_study_records_node_id ON public.study_records USING btree (node_id);


-- Name: ix_study_records_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_study_records_user_id ON public.study_records USING btree (user_id);


-- Name: ix_subjects_category; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_subjects_category ON public.subjects USING btree (category);


-- Name: ix_subjects_is_active; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_subjects_is_active ON public.subjects USING btree (is_active);


-- Name: ix_subjects_name; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_subjects_name ON public.subjects USING btree (name);


-- Name: ix_system_config_change_logs_changed_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_system_config_change_logs_changed_at ON public.system_config_change_logs USING btree (changed_at);


-- Name: ix_system_config_change_logs_changed_by; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_system_config_change_logs_changed_by ON public.system_config_change_logs USING btree (changed_by);


-- Name: ix_system_config_change_logs_config_key; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_system_config_change_logs_config_key ON public.system_config_change_logs USING btree (config_key);


-- Name: ix_system_config_change_logs_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_system_config_change_logs_id ON public.system_config_change_logs USING btree (id);


-- Name: ix_tasks_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_tasks_deleted_at ON public.tasks USING btree (deleted_at);


-- Name: ix_tasks_plan_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_tasks_plan_id ON public.tasks USING btree (plan_id);


-- Name: ix_tasks_status; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_tasks_status ON public.tasks USING btree (status);


-- Name: ix_tasks_tool_result_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_tasks_tool_result_id ON public.tasks USING btree (tool_result_id);


-- Name: ix_tasks_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_tasks_user_id ON public.tasks USING btree (user_id);


-- Name: ix_token_usage_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_token_usage_deleted_at ON public.token_usage USING btree (deleted_at);


-- Name: ix_token_usage_session_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_token_usage_session_id ON public.token_usage USING btree (session_id);


-- Name: ix_token_usage_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_token_usage_user_id ON public.token_usage USING btree (user_id);


-- Name: ix_tracking_events_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_tracking_events_deleted_at ON public.tracking_events USING btree (deleted_at);


-- Name: ix_tracking_events_event_id; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_tracking_events_event_id ON public.tracking_events USING btree (event_id);


-- Name: ix_tracking_events_event_type; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_tracking_events_event_type ON public.tracking_events USING btree (event_type);


-- Name: ix_tracking_events_ts_ms; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_tracking_events_ts_ms ON public.tracking_events USING btree (ts_ms);


-- Name: ix_tracking_events_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_tracking_events_user_id ON public.tracking_events USING btree (user_id);


-- Name: ix_user_daily_metrics_date; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_daily_metrics_date ON public.user_daily_metrics USING btree (date);


-- Name: ix_user_daily_metrics_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_daily_metrics_deleted_at ON public.user_daily_metrics USING btree (deleted_at);


-- Name: ix_user_daily_metrics_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_daily_metrics_user_id ON public.user_daily_metrics USING btree (user_id);


-- Name: ix_user_encryption_keys_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_encryption_keys_deleted_at ON public.user_encryption_keys USING btree (deleted_at);


-- Name: ix_user_encryption_keys_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_encryption_keys_user_id ON public.user_encryption_keys USING btree (user_id);


-- Name: ix_user_intervention_settings_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_intervention_settings_deleted_at ON public.user_intervention_settings USING btree (deleted_at);


-- Name: ix_user_intervention_settings_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_user_intervention_settings_user_id ON public.user_intervention_settings USING btree (user_id);


-- Name: ix_user_irt_ability_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_irt_ability_deleted_at ON public.user_irt_ability USING btree (deleted_at);


-- Name: ix_user_irt_ability_subject_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_irt_ability_subject_id ON public.user_irt_ability USING btree (subject_id);


-- Name: ix_user_irt_ability_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_irt_ability_user_id ON public.user_irt_ability USING btree (user_id);


-- Name: ix_user_memory_settings_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_memory_settings_deleted_at ON public.user_memory_settings USING btree (deleted_at);


-- Name: ix_user_memory_settings_user; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_user_memory_settings_user ON public.user_memory_settings USING btree (user_id);


-- Name: ix_user_node_status_next_review_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_node_status_next_review_at ON public.user_node_status USING btree (next_review_at);


-- Name: ix_user_persona_keys_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_persona_keys_deleted_at ON public.user_persona_keys USING btree (deleted_at);


-- Name: ix_user_persona_keys_key_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_persona_keys_key_id ON public.user_persona_keys USING btree (key_id);


-- Name: ix_user_persona_keys_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_persona_keys_user_id ON public.user_persona_keys USING btree (user_id);


-- Name: ix_user_preferences_center_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_preferences_center_deleted_at ON public.user_preferences_center USING btree (deleted_at);


-- Name: ix_user_preferences_center_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_user_preferences_center_user_id ON public.user_preferences_center USING btree (user_id);


-- Name: ix_user_state_snapshots_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_state_snapshots_deleted_at ON public.user_state_snapshots USING btree (deleted_at);


-- Name: ix_user_state_snapshots_snapshot_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_state_snapshots_snapshot_at ON public.user_state_snapshots USING btree (snapshot_at);


-- Name: ix_user_state_snapshots_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_user_state_snapshots_user_id ON public.user_state_snapshots USING btree (user_id);


-- Name: ix_users_apple_id; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_users_apple_id ON public.users USING btree (apple_id);


-- Name: ix_users_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_users_deleted_at ON public.users USING btree (deleted_at);


-- Name: ix_users_google_id; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_users_google_id ON public.users USING btree (google_id);


-- Name: ix_users_wechat_unionid; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX ix_users_wechat_unionid ON public.users USING btree (wechat_unionid);


-- Name: ix_word_books_deleted_at; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_word_books_deleted_at ON public.word_books USING btree (deleted_at);


-- Name: ix_word_books_user_id; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_word_books_user_id ON public.word_books USING btree (user_id);


-- Name: ix_word_books_word; Type: INDEX; Schema: public; Owner: postgres

CREATE INDEX ix_word_books_word ON public.word_books USING btree (word);


-- Name: uq_memory_rank_policies_scope; Type: INDEX; Schema: public; Owner: postgres

CREATE UNIQUE INDEX uq_memory_rank_policies_scope ON public.memory_rank_policies USING btree (scope_type, scope_key);


-- Name: behavior_patterns behavior_patterns_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.behavior_patterns
    ADD CONSTRAINT behavior_patterns_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: behavioral_outcomes behavioral_outcomes_intervention_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.behavioral_outcomes
    ADD CONSTRAINT behavioral_outcomes_intervention_id_fkey FOREIGN KEY (intervention_id) REFERENCES public.intervention_requests(id);


-- Name: behavioral_outcomes behavioral_outcomes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.behavioral_outcomes
    ADD CONSTRAINT behavioral_outcomes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: broadcast_messages broadcast_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.broadcast_messages
    ADD CONSTRAINT broadcast_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: chat_messages chat_messages_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


-- Name: chat_messages chat_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: cognitive_fragments cognitive_fragments_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.cognitive_fragments
    ADD CONSTRAINT cognitive_fragments_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


-- Name: cognitive_fragments cognitive_fragments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.cognitive_fragments
    ADD CONSTRAINT cognitive_fragments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: collaborative_galaxies collaborative_galaxies_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.collaborative_galaxies
    ADD CONSTRAINT collaborative_galaxies_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


-- Name: collaborative_galaxies collaborative_galaxies_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.collaborative_galaxies
    ADD CONSTRAINT collaborative_galaxies_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id);


-- Name: compliance_check_logs compliance_check_logs_executed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.compliance_check_logs
    ADD CONSTRAINT compliance_check_logs_executed_by_fkey FOREIGN KEY (executed_by) REFERENCES public.users(id);


-- Name: crdt_operation_log crdt_operation_log_galaxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.crdt_operation_log
    ADD CONSTRAINT crdt_operation_log_galaxy_id_fkey FOREIGN KEY (galaxy_id) REFERENCES public.collaborative_galaxies(id);


-- Name: crdt_operation_log crdt_operation_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.crdt_operation_log
    ADD CONSTRAINT crdt_operation_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: crdt_snapshots crdt_snapshots_galaxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.crdt_snapshots
    ADD CONSTRAINT crdt_snapshots_galaxy_id_fkey FOREIGN KEY (galaxy_id) REFERENCES public.collaborative_galaxies(id);


-- Name: crypto_shredding_certificates crypto_shredding_certificates_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.crypto_shredding_certificates
    ADD CONSTRAINT crypto_shredding_certificates_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: curiosity_capsules curiosity_capsules_related_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.curiosity_capsules
    ADD CONSTRAINT curiosity_capsules_related_task_id_fkey FOREIGN KEY (related_task_id) REFERENCES public.tasks(id);


-- Name: curiosity_capsules curiosity_capsules_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.curiosity_capsules
    ADD CONSTRAINT curiosity_capsules_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: data_access_logs data_access_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.data_access_logs
    ADD CONSTRAINT data_access_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: decision_records decision_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.decision_records
    ADD CONSTRAINT decision_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: dlq_replay_audit_logs dlq_replay_audit_logs_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.dlq_replay_audit_logs
    ADD CONSTRAINT dlq_replay_audit_logs_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.users(id);


-- Name: dlq_replay_audit_logs dlq_replay_audit_logs_approver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.dlq_replay_audit_logs
    ADD CONSTRAINT dlq_replay_audit_logs_approver_id_fkey FOREIGN KEY (approver_id) REFERENCES public.users(id);


-- Name: document_chunks document_chunks_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.stored_files(id) ON DELETE CASCADE;


-- Name: document_chunks document_chunks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: episodic_memories episodic_memories_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.episodic_memories
    ADD CONSTRAINT episodic_memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: error_records error_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.error_records
    ADD CONSTRAINT error_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: expansion_feedback expansion_feedback_expansion_queue_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.expansion_feedback
    ADD CONSTRAINT expansion_feedback_expansion_queue_id_fkey FOREIGN KEY (expansion_queue_id) REFERENCES public.node_expansion_queue(id);


-- Name: expansion_feedback expansion_feedback_trigger_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.expansion_feedback
    ADD CONSTRAINT expansion_feedback_trigger_node_id_fkey FOREIGN KEY (trigger_node_id) REFERENCES public.knowledge_nodes(id);


-- Name: expansion_feedback expansion_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.expansion_feedback
    ADD CONSTRAINT expansion_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: focus_sessions focus_sessions_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.focus_sessions
    ADD CONSTRAINT focus_sessions_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


-- Name: focus_sessions focus_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.focus_sessions
    ADD CONSTRAINT focus_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: friendships friendships_friend_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.friendships
    ADD CONSTRAINT friendships_friend_id_fkey FOREIGN KEY (friend_id) REFERENCES public.users(id);


-- Name: friendships friendships_initiated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.friendships
    ADD CONSTRAINT friendships_initiated_by_fkey FOREIGN KEY (initiated_by) REFERENCES public.users(id);


-- Name: friendships friendships_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.friendships
    ADD CONSTRAINT friendships_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: galaxy_user_permissions galaxy_user_permissions_galaxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.galaxy_user_permissions
    ADD CONSTRAINT galaxy_user_permissions_galaxy_id_fkey FOREIGN KEY (galaxy_id) REFERENCES public.collaborative_galaxies(id);


-- Name: galaxy_user_permissions galaxy_user_permissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.galaxy_user_permissions
    ADD CONSTRAINT galaxy_user_permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: group_files group_files_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_files
    ADD CONSTRAINT group_files_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.stored_files(id) ON DELETE CASCADE;


-- Name: group_files group_files_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_files
    ADD CONSTRAINT group_files_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


-- Name: group_files group_files_shared_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_files
    ADD CONSTRAINT group_files_shared_by_id_fkey FOREIGN KEY (shared_by_id) REFERENCES public.users(id);


-- Name: group_members group_members_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


-- Name: group_members group_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: group_messages group_messages_forwarded_from_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_forwarded_from_id_fkey FOREIGN KEY (forwarded_from_id) REFERENCES public.group_messages(id);


-- Name: group_messages group_messages_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


-- Name: group_messages group_messages_reply_to_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_reply_to_id_fkey FOREIGN KEY (reply_to_id) REFERENCES public.group_messages(id);


-- Name: group_messages group_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);


-- Name: group_messages group_messages_thread_root_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_thread_root_id_fkey FOREIGN KEY (thread_root_id) REFERENCES public.group_messages(id);


-- Name: group_task_claims group_task_claims_group_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_task_claims
    ADD CONSTRAINT group_task_claims_group_task_id_fkey FOREIGN KEY (group_task_id) REFERENCES public.group_tasks(id) ON DELETE CASCADE;


-- Name: group_task_claims group_task_claims_personal_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_task_claims
    ADD CONSTRAINT group_task_claims_personal_task_id_fkey FOREIGN KEY (personal_task_id) REFERENCES public.tasks(id);


-- Name: group_task_claims group_task_claims_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_task_claims
    ADD CONSTRAINT group_task_claims_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: group_tasks group_tasks_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_tasks
    ADD CONSTRAINT group_tasks_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


-- Name: group_tasks group_tasks_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.group_tasks
    ADD CONSTRAINT group_tasks_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


-- Name: idempotency_keys idempotency_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: intervention_audit_logs intervention_audit_logs_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.intervention_audit_logs
    ADD CONSTRAINT intervention_audit_logs_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.intervention_requests(id);


-- Name: intervention_audit_logs intervention_audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.intervention_audit_logs
    ADD CONSTRAINT intervention_audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: intervention_feedback intervention_feedback_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.intervention_feedback
    ADD CONSTRAINT intervention_feedback_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.intervention_requests(id);


-- Name: intervention_feedback intervention_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.intervention_feedback
    ADD CONSTRAINT intervention_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: intervention_requests intervention_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.intervention_requests
    ADD CONSTRAINT intervention_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: jobs jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: knowledge_nodes knowledge_nodes_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.knowledge_nodes
    ADD CONSTRAINT knowledge_nodes_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.knowledge_nodes(id);


-- Name: knowledge_nodes knowledge_nodes_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.knowledge_nodes
    ADD CONSTRAINT knowledge_nodes_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id);


-- Name: legal_holds legal_holds_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.legal_holds
    ADD CONSTRAINT legal_holds_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.users(id);


-- Name: legal_holds legal_holds_released_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.legal_holds
    ADD CONSTRAINT legal_holds_released_by_fkey FOREIGN KEY (released_by) REFERENCES public.users(id);


-- Name: legal_holds legal_holds_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.legal_holds
    ADD CONSTRAINT legal_holds_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: login_attempts login_attempts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.login_attempts
    ADD CONSTRAINT login_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: mastery_audit_log mastery_audit_log_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.mastery_audit_log
    ADD CONSTRAINT mastery_audit_log_node_id_fkey FOREIGN KEY (node_id) REFERENCES public.knowledge_nodes(id);


-- Name: mastery_audit_log mastery_audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.mastery_audit_log
    ADD CONSTRAINT mastery_audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: memory_corrections memory_corrections_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.memory_corrections
    ADD CONSTRAINT memory_corrections_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: memory_goals memory_goals_linked_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.memory_goals
    ADD CONSTRAINT memory_goals_linked_plan_id_fkey FOREIGN KEY (linked_plan_id) REFERENCES public.plans(id);


-- Name: memory_goals memory_goals_linked_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.memory_goals
    ADD CONSTRAINT memory_goals_linked_task_id_fkey FOREIGN KEY (linked_task_id) REFERENCES public.tasks(id);


-- Name: memory_goals memory_goals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.memory_goals
    ADD CONSTRAINT memory_goals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: memory_preferences memory_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.memory_preferences
    ADD CONSTRAINT memory_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: message_favorites message_favorites_group_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.message_favorites
    ADD CONSTRAINT message_favorites_group_message_id_fkey FOREIGN KEY (group_message_id) REFERENCES public.group_messages(id) ON DELETE CASCADE;


-- Name: message_favorites message_favorites_private_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.message_favorites
    ADD CONSTRAINT message_favorites_private_message_id_fkey FOREIGN KEY (private_message_id) REFERENCES public.private_messages(id) ON DELETE CASCADE;


-- Name: message_favorites message_favorites_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.message_favorites
    ADD CONSTRAINT message_favorites_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: message_reports message_reports_group_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.message_reports
    ADD CONSTRAINT message_reports_group_message_id_fkey FOREIGN KEY (group_message_id) REFERENCES public.group_messages(id) ON DELETE SET NULL;


-- Name: message_reports message_reports_private_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.message_reports
    ADD CONSTRAINT message_reports_private_message_id_fkey FOREIGN KEY (private_message_id) REFERENCES public.private_messages(id) ON DELETE SET NULL;


-- Name: message_reports message_reports_reporter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.message_reports
    ADD CONSTRAINT message_reports_reporter_id_fkey FOREIGN KEY (reporter_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: message_reports message_reports_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.message_reports
    ADD CONSTRAINT message_reports_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


-- Name: nightly_reviews nightly_reviews_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.nightly_reviews
    ADD CONSTRAINT nightly_reviews_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: node_expansion_queue node_expansion_queue_trigger_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_trigger_node_id_fkey FOREIGN KEY (trigger_node_id) REFERENCES public.knowledge_nodes(id);


-- Name: node_expansion_queue node_expansion_queue_trigger_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_trigger_task_id_fkey FOREIGN KEY (trigger_task_id) REFERENCES public.tasks(id);


-- Name: node_expansion_queue node_expansion_queue_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: node_relations node_relations_source_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.node_relations
    ADD CONSTRAINT node_relations_source_node_id_fkey FOREIGN KEY (source_node_id) REFERENCES public.knowledge_nodes(id);


-- Name: node_relations node_relations_target_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.node_relations
    ADD CONSTRAINT node_relations_target_node_id_fkey FOREIGN KEY (target_node_id) REFERENCES public.knowledge_nodes(id);


-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: offline_message_queue offline_message_queue_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.offline_message_queue
    ADD CONSTRAINT offline_message_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: passive_signals passive_signals_intervention_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.passive_signals
    ADD CONSTRAINT passive_signals_intervention_id_fkey FOREIGN KEY (intervention_id) REFERENCES public.intervention_requests(id);


-- Name: passive_signals passive_signals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.passive_signals
    ADD CONSTRAINT passive_signals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: persona_snapshots persona_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.persona_snapshots
    ADD CONSTRAINT persona_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: plans plans_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.plans
    ADD CONSTRAINT plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: post_likes post_likes_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.post_likes
    ADD CONSTRAINT post_likes_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.posts(id);


-- Name: post_likes post_likes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.post_likes
    ADD CONSTRAINT post_likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: posts posts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: private_messages private_messages_forwarded_from_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_forwarded_from_id_fkey FOREIGN KEY (forwarded_from_id) REFERENCES public.private_messages(id);


-- Name: private_messages private_messages_receiver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_receiver_id_fkey FOREIGN KEY (receiver_id) REFERENCES public.users(id);


-- Name: private_messages private_messages_reply_to_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_reply_to_id_fkey FOREIGN KEY (reply_to_id) REFERENCES public.private_messages(id);


-- Name: private_messages private_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);


-- Name: private_messages private_messages_thread_root_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_thread_root_id_fkey FOREIGN KEY (thread_root_id) REFERENCES public.private_messages(id);


-- Name: push_histories push_histories_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.push_histories
    ADD CONSTRAINT push_histories_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: push_preferences push_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.push_preferences
    ADD CONSTRAINT push_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: scaffolding_states scaffolding_states_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.scaffolding_states
    ADD CONSTRAINT scaffolding_states_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: security_audit_logs security_audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.security_audit_logs
    ADD CONSTRAINT security_audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: shared_resources shared_resources_behavior_pattern_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_behavior_pattern_id_fkey FOREIGN KEY (behavior_pattern_id) REFERENCES public.behavior_patterns(id);


-- Name: shared_resources shared_resources_cognitive_fragment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_cognitive_fragment_id_fkey FOREIGN KEY (cognitive_fragment_id) REFERENCES public.cognitive_fragments(id);


-- Name: shared_resources shared_resources_curiosity_capsule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_curiosity_capsule_id_fkey FOREIGN KEY (curiosity_capsule_id) REFERENCES public.curiosity_capsules(id);


-- Name: shared_resources shared_resources_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


-- Name: shared_resources shared_resources_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(id);


-- Name: shared_resources shared_resources_shared_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_shared_by_fkey FOREIGN KEY (shared_by) REFERENCES public.users(id);


-- Name: shared_resources shared_resources_target_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_target_user_id_fkey FOREIGN KEY (target_user_id) REFERENCES public.users(id);


-- Name: shared_resources shared_resources_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


-- Name: stored_files stored_files_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.stored_files
    ADD CONSTRAINT stored_files_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: strategy_nodes strategy_nodes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.strategy_nodes
    ADD CONSTRAINT strategy_nodes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: study_records study_records_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.study_records
    ADD CONSTRAINT study_records_node_id_fkey FOREIGN KEY (node_id) REFERENCES public.knowledge_nodes(id);


-- Name: study_records study_records_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.study_records
    ADD CONSTRAINT study_records_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


-- Name: study_records study_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.study_records
    ADD CONSTRAINT study_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: system_config_change_logs system_config_change_logs_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.system_config_change_logs
    ADD CONSTRAINT system_config_change_logs_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id);


-- Name: tasks tasks_knowledge_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_knowledge_node_id_fkey FOREIGN KEY (knowledge_node_id) REFERENCES public.knowledge_nodes(id);


-- Name: tasks tasks_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(id);


-- Name: tasks tasks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: token_usage token_usage_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: tracking_events tracking_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.tracking_events
    ADD CONSTRAINT tracking_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: user_daily_metrics user_daily_metrics_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_daily_metrics
    ADD CONSTRAINT user_daily_metrics_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: user_encryption_keys user_encryption_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_encryption_keys
    ADD CONSTRAINT user_encryption_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: user_intervention_settings user_intervention_settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_intervention_settings
    ADD CONSTRAINT user_intervention_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: user_irt_ability user_irt_ability_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_irt_ability
    ADD CONSTRAINT user_irt_ability_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: user_node_status user_node_status_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_node_status
    ADD CONSTRAINT user_node_status_node_id_fkey FOREIGN KEY (node_id) REFERENCES public.knowledge_nodes(id);


-- Name: user_node_status user_node_status_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_node_status
    ADD CONSTRAINT user_node_status_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: user_persona_keys user_persona_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_persona_keys
    ADD CONSTRAINT user_persona_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Name: user_preferences_center user_preferences_center_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_preferences_center
    ADD CONSTRAINT user_preferences_center_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: user_state_snapshots user_state_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.user_state_snapshots
    ADD CONSTRAINT user_state_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- Name: word_books word_books_source_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.word_books
    ADD CONSTRAINT word_books_source_task_id_fkey FOREIGN KEY (source_task_id) REFERENCES public.tasks(id);


-- Name: word_books word_books_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres

ALTER TABLE ONLY public.word_books
    ADD CONSTRAINT word_books_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


-- PostgreSQL database dump complete


