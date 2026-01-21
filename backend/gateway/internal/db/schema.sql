--
-- PostgreSQL database dump
--


-- Dumped from database version 16.11 (Debian 16.11-1.pgdg12+1)
-- Dumped by pg_dump version 16.11 (Debian 16.11-1.pgdg12+1)

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
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


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
    'PROGRESS',
    'ACHIEVEMENT',
    'CHECKIN',
    'SYSTEM',
    'CAPSULE_SHARE',
    'PRISM_SHARE'
);


ALTER TYPE messagetype OWNER TO postgres;

--
-- Name: plantype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE plantype AS ENUM (
    'SPRINT',
    'GROWTH'
);


ALTER TYPE plantype OWNER TO postgres;

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
    'PLANNING'
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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_execution_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE agent_execution_stats (
    id integer NOT NULL,
    user_id integer NOT NULL,
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
    metadata jsonb,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
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
-- Name: agent_stats_summary; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres
--

CREATE MATERIALIZED VIEW agent_stats_summary AS
 SELECT user_id,
    agent_type,
    count(*) AS execution_count,
    avg(duration_ms) AS avg_duration_ms,
    max(duration_ms) AS max_duration_ms,
    min(duration_ms) AS min_duration_ms,
    count(
        CASE
            WHEN ((status)::text = 'success'::text) THEN 1
            ELSE NULL::integer
        END) AS success_count,
    count(
        CASE
            WHEN ((status)::text = 'failed'::text) THEN 1
            ELSE NULL::integer
        END) AS failure_count,
    max(created_at) AS last_used_at
   FROM agent_execution_stats
  WHERE (completed_at IS NOT NULL)
  GROUP BY user_id, agent_type
  WITH NO DATA;


ALTER MATERIALIZED VIEW agent_stats_summary OWNER TO postgres;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE alembic_version (
    version_num character varying(255) NOT NULL
);


ALTER TABLE alembic_version OWNER TO postgres;

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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE behavior_patterns OWNER TO postgres;

--
-- Name: broadcast_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE broadcast_messages (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sender_id uuid NOT NULL,
    content text NOT NULL,
    content_data json,
    target_group_ids json NOT NULL,
    delivered_count integer DEFAULT 0 NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE broadcast_messages OWNER TO postgres;

--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
)
PARTITION BY RANGE (created_at);


ALTER TABLE chat_messages OWNER TO postgres;

--
-- Name: chat_messages_2024_q1; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_2024_q1 (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_2024_q1 OWNER TO postgres;

--
-- Name: chat_messages_2024_q2; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_2024_q2 (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_2024_q2 OWNER TO postgres;

--
-- Name: chat_messages_2024_q3; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_2024_q3 (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_2024_q3 OWNER TO postgres;

--
-- Name: chat_messages_2024_q4; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_2024_q4 (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_2024_q4 OWNER TO postgres;

--
-- Name: chat_messages_2025_q1; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_2025_q1 (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_2025_q1 OWNER TO postgres;

--
-- Name: chat_messages_2025_q2; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_2025_q2 (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_2025_q2 OWNER TO postgres;

--
-- Name: chat_messages_2025_q3; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_2025_q3 (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_2025_q3 OWNER TO postgres;

--
-- Name: chat_messages_2025_q4; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_2025_q4 (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_2025_q4 OWNER TO postgres;

--
-- Name: chat_messages_2026_q1; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_2026_q1 (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_2026_q1 OWNER TO postgres;

--
-- Name: chat_messages_2026_q2; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_2026_q2 (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_2026_q2 OWNER TO postgres;

--
-- Name: chat_messages_default; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_default (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_default OWNER TO postgres;

--
-- Name: chat_messages_legacy; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_legacy (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_legacy OWNER TO postgres;

--
-- Name: chat_messages_old; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE chat_messages_old (
    user_id uuid NOT NULL,
    task_id uuid,
    session_id uuid NOT NULL,
    message_id character varying(36),
    role messagerole NOT NULL,
    content text NOT NULL,
    actions json,
    parse_degraded boolean,
    tokens_used integer,
    model_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE chat_messages_old OWNER TO postgres;

--
-- Name: cognitive_fragments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE cognitive_fragments (
    user_id uuid NOT NULL,
    task_id uuid,
    source_type character varying(20) NOT NULL,
    resource_type character varying(20) NOT NULL,
    resource_url character varying(512),
    content text NOT NULL,
    sentiment character varying(20),
    tags json,
    error_tags json,
    context_tags json,
    severity integer NOT NULL,
    embedding vector(1024),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    persona_version character varying(50),
    source_event_id character varying(64),
    sensitive_tags_encrypted text,
    sensitive_tags_version integer,
    sensitive_tags_key_id character varying(100)
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
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    key_id character varying(128) NOT NULL,
    destruction_time timestamp without time zone NOT NULL,
    cloud_provider_ack text,
    certificate_data jsonb,
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
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
    id uuid NOT NULL,
    message_id character varying(128) NOT NULL,
    admin_id uuid NOT NULL,
    approver_id uuid NOT NULL,
    reason_code character varying(64) NOT NULL,
    payload_hash character varying(128) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE dlq_replay_audit_logs OWNER TO postgres;

--
-- Name: document_chunks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE document_chunks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    file_id uuid NOT NULL,
    user_id uuid NOT NULL,
    chunk_index integer NOT NULL,
    section_title character varying(255),
    content text NOT NULL,
    embedding vector(1024),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    deleted_at timestamp without time zone,
    page_numbers json,
    bbox json,
    quality_score double precision,
    pipeline_version character varying(50)
);


ALTER TABLE document_chunks OWNER TO postgres;

--
-- Name: error_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE error_records (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    question_text text,
    question_image_url character varying(500),
    user_answer text,
    correct_answer text,
    subject_code character varying(50) NOT NULL,
    chapter character varying(100),
    source character varying(50),
    difficulty integer,
    mastery_level double precision,
    review_count integer,
    next_review_at timestamp with time zone,
    last_reviewed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    is_deleted boolean,
    easiness_factor double precision DEFAULT '2.5'::double precision,
    interval_days double precision DEFAULT '0'::double precision,
    latest_analysis jsonb,
    linked_knowledge_node_ids uuid[] DEFAULT '{}'::uuid[],
    suggested_concepts text[] DEFAULT '{}'::text[],
    cognitive_tags character varying[] DEFAULT '{}'::character varying[],
    ai_analysis_summary text
);


ALTER TABLE error_records OWNER TO postgres;

--
-- Name: COLUMN error_records.question_text; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.question_text IS '题目原文';


--
-- Name: COLUMN error_records.question_image_url; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.question_image_url IS '题目图片URL（可选）';


--
-- Name: COLUMN error_records.user_answer; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.user_answer IS '用户的错误答案';


--
-- Name: COLUMN error_records.correct_answer; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.correct_answer IS '正确答案';


--
-- Name: COLUMN error_records.subject_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.subject_code IS '科目';


--
-- Name: COLUMN error_records.chapter; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.chapter IS '章节（可选）';


--
-- Name: COLUMN error_records.source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.source IS '来源';


--
-- Name: COLUMN error_records.difficulty; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.difficulty IS '难度1-5';


--
-- Name: COLUMN error_records.mastery_level; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.mastery_level IS '掌握度0-1';


--
-- Name: COLUMN error_records.review_count; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.review_count IS '复习次数';


--
-- Name: COLUMN error_records.next_review_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.next_review_at IS '下次复习时间';


--
-- Name: COLUMN error_records.last_reviewed_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN error_records.last_reviewed_at IS '上次复习时间';


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
    sequence_number bigint NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    published_at timestamp without time zone
);


ALTER TABLE event_outbox OWNER TO postgres;

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
-- Name: expansion_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE expansion_feedback (
    id uuid NOT NULL,
    expansion_queue_id uuid,
    trigger_node_id uuid NOT NULL,
    user_id uuid NOT NULL,
    rating integer,
    implicit_score double precision,
    feedback_type character varying(20),
    prompt_version character varying(50),
    model_name character varying(50),
    meta_data jsonb,
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
    id uuid NOT NULL,
    group_id uuid NOT NULL,
    file_id uuid NOT NULL,
    shared_by_id uuid NOT NULL,
    category character varying(64),
    tags json NOT NULL,
    view_role grouprole NOT NULL,
    download_role grouprole NOT NULL,
    manage_role grouprole NOT NULL,
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
    deleted_at timestamp without time zone,
    mute_until timestamp without time zone,
    warn_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE group_members OWNER TO postgres;

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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    thread_root_id uuid,
    is_revoked boolean DEFAULT false NOT NULL,
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
    forward_count integer DEFAULT 0 NOT NULL
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    announcement text,
    announcement_updated_at timestamp without time zone,
    keyword_filters json,
    mute_all boolean DEFAULT false NOT NULL,
    slow_mode_seconds integer DEFAULT 0 NOT NULL
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
    id uuid NOT NULL,
    request_id uuid NOT NULL,
    user_id uuid NOT NULL,
    action character varying(40) NOT NULL,
    guardrail_result jsonb,
    decision_trace jsonb,
    evidence_refs jsonb,
    requested_level character varying(40) NOT NULL,
    final_level character varying(40) NOT NULL,
    policy_version character varying(50),
    model_version character varying(80),
    schema_version character varying(50),
    occurred_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE intervention_audit_logs OWNER TO postgres;

--
-- Name: intervention_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE intervention_feedback (
    id uuid NOT NULL,
    request_id uuid NOT NULL,
    user_id uuid NOT NULL,
    feedback_type character varying(40) NOT NULL,
    extra_data jsonb,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE intervention_feedback OWNER TO postgres;

--
-- Name: intervention_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE intervention_requests (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    dedupe_key character varying(200),
    topic character varying(120),
    requested_level character varying(40) NOT NULL,
    final_level character varying(40) NOT NULL,
    status character varying(40) NOT NULL,
    reason jsonb,
    content jsonb,
    cooldown_policy jsonb,
    schema_version character varying(50) NOT NULL,
    policy_version character varying(50),
    model_version character varying(80),
    expires_at timestamp without time zone,
    is_retractable boolean DEFAULT true NOT NULL,
    supersedes_id uuid,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE intervention_requests OWNER TO postgres;

--
-- Name: irt_item_parameters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE irt_item_parameters (
    id uuid NOT NULL,
    question_id uuid NOT NULL,
    subject_id character varying(32),
    a double precision DEFAULT '1'::double precision NOT NULL,
    b double precision DEFAULT '0'::double precision NOT NULL,
    c double precision DEFAULT '0.2'::double precision NOT NULL,
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
    embedding vector(1024),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    position_x double precision,
    position_y double precision,
    global_spark_count integer DEFAULT 0 NOT NULL,
    source_file_id uuid,
    chunk_refs jsonb,
    status character varying(20)
);


ALTER TABLE knowledge_nodes OWNER TO postgres;

--
-- Name: legal_holds; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE legal_holds (
    id uuid NOT NULL,
    user_id uuid,
    device_id character varying(128),
    case_ref character varying(120) NOT NULL,
    reason text,
    admin_id uuid NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    released_at timestamp without time zone,
    released_by uuid,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE legal_holds OWNER TO postgres;

--
-- Name: login_attempts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE login_attempts (
    id uuid NOT NULL,
    user_id uuid,
    username character varying(100) NOT NULL,
    ip_address character varying(45) NOT NULL,
    user_agent character varying(500),
    success boolean NOT NULL,
    attempted_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE login_attempts OWNER TO postgres;

--
-- Name: mastery_audit_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE mastery_audit_log (
    id bigint NOT NULL,
    node_id uuid NOT NULL,
    user_id uuid NOT NULL,
    old_mastery integer NOT NULL,
    new_mastery integer NOT NULL,
    reason character varying(50) NOT NULL,
    ip_address inet,
    user_agent text,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE mastery_audit_log OWNER TO postgres;

--
-- Name: mastery_audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE mastery_audit_log_id_seq
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
-- Name: message_favorites; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE message_favorites (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    group_message_id uuid,
    private_message_id uuid,
    note text,
    tags json,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE message_favorites OWNER TO postgres;

--
-- Name: message_reports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE message_reports (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    reporter_id uuid NOT NULL,
    group_message_id uuid,
    private_message_id uuid,
    reason character varying(50) NOT NULL,
    description text,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    reviewed_by uuid,
    reviewed_at timestamp without time zone,
    action_taken character varying(50),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE message_reports OWNER TO postgres;

--
-- Name: nightly_reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE nightly_reviews (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    review_date date NOT NULL,
    summary_text character varying(2000),
    todo_items json,
    evidence_refs json,
    model_version character varying(50),
    status character varying(30) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    reviewed_at timestamp without time zone
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
    processed_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    prompt_version character varying(50),
    model_name character varying(50)
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
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    client_nonce character varying(100) NOT NULL,
    message_type character varying(50) NOT NULL,
    target_id uuid NOT NULL,
    payload json NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    retry_count integer DEFAULT 0 NOT NULL,
    last_retry_at timestamp without time zone,
    error_message text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    expires_at timestamp without time zone
);


ALTER TABLE offline_message_queue OWNER TO postgres;

--
-- Name: outbox_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE outbox_events (
    id bigint NOT NULL,
    aggregate_id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    payload jsonb NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    published_at timestamp without time zone
);


ALTER TABLE outbox_events OWNER TO postgres;

--
-- Name: outbox_events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE outbox_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE outbox_events_id_seq OWNER TO postgres;

--
-- Name: outbox_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE outbox_events_id_seq OWNED BY outbox_events.id;


--
-- Name: persona_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE persona_snapshots (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    persona_version character varying(50) NOT NULL,
    audit_token character varying(128),
    source_event_id character varying(64),
    snapshot_data jsonb NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE persona_snapshots OWNER TO postgres;

--
-- Name: plans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE plans (
    user_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    type plantype NOT NULL,
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


ALTER TABLE plans OWNER TO postgres;

--
-- Name: post_likes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE post_likes (
    user_id uuid NOT NULL,
    post_id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE post_likes OWNER TO postgres;

--
-- Name: posts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE posts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    content text NOT NULL,
    image_urls json,
    topic character varying(100),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    deleted_at timestamp without time zone,
    visibility character varying(20) DEFAULT 'public'::character varying,
    CONSTRAINT posts_visibility_check CHECK (((visibility)::text = ANY ((ARRAY['public'::character varying, 'private'::character varying, 'friends_only'::character varying])::text[])))
);


ALTER TABLE posts OWNER TO postgres;

--
-- Name: COLUMN posts.visibility; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN posts.visibility IS 'Controls post visibility: public (default), private (creator only), friends_only (creator + friends)';


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
    is_read boolean NOT NULL,
    read_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    thread_root_id uuid,
    is_revoked boolean DEFAULT false NOT NULL,
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
    forward_count integer DEFAULT 0 NOT NULL
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
    status character varying(20) DEFAULT '''active'''::character varying NOT NULL,
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
-- Name: semantic_links; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE semantic_links (
    id uuid NOT NULL,
    source_type character varying(30) NOT NULL,
    source_id character varying(64) NOT NULL,
    target_type character varying(30) NOT NULL,
    target_id character varying(64) NOT NULL,
    relation_type character varying(40) NOT NULL,
    strength double precision NOT NULL,
    created_by character varying(20) NOT NULL,
    evidence_refs json,
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
    permission character varying(20) NOT NULL,
    comment text,
    view_count integer,
    save_count integer,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    curiosity_capsule_id uuid,
    behavior_pattern_id uuid
);


ALTER TABLE shared_resources OWNER TO postgres;

--
-- Name: stored_files; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE stored_files (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    file_name character varying(255) NOT NULL,
    mime_type character varying(150) NOT NULL,
    file_size bigint NOT NULL,
    bucket character varying(128) NOT NULL,
    object_key character varying(512) NOT NULL,
    status character varying(32) DEFAULT 'uploading'::character varying NOT NULL,
    visibility character varying(32) DEFAULT 'private'::character varying NOT NULL,
    error_message character varying(255),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    deleted_at timestamp without time zone,
    retention_policy character varying(32) DEFAULT 'keep'::character varying NOT NULL
);


ALTER TABLE stored_files OWNER TO postgres;

--
-- Name: strategy_nodes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE strategy_nodes (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    description character varying(2000),
    subject_code character varying(50),
    tags json,
    content_hash character varying(64),
    source_type character varying(20) NOT NULL,
    evidence_refs json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE strategy_nodes OWNER TO postgres;

--
-- Name: study_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE study_records (
    user_id uuid NOT NULL,
    node_id uuid NOT NULL,
    task_id uuid,
    study_minutes integer NOT NULL,
    mastery_delta double precision NOT NULL,
    record_type character varying(20),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    initial_mastery double precision
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
    completed_at timestamp without time zone,
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
    id uuid NOT NULL,
    event_id character varying(64) NOT NULL,
    user_id uuid NOT NULL,
    event_type character varying(120) NOT NULL,
    schema_version character varying(50) NOT NULL,
    source character varying(50) NOT NULL,
    ts_ms bigint NOT NULL,
    entities jsonb,
    payload json,
    received_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE tracking_events OWNER TO postgres;

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
-- Name: user_encryption_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_encryption_keys (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    public_key text NOT NULL,
    key_type character varying(50) DEFAULT 'x25519'::character varying NOT NULL,
    device_id character varying(100),
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    expires_at timestamp without time zone
);


ALTER TABLE user_encryption_keys OWNER TO postgres;

--
-- Name: user_intervention_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_intervention_settings (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    interrupt_threshold double precision DEFAULT '0.5'::double precision NOT NULL,
    daily_interrupt_budget integer DEFAULT 3 NOT NULL,
    cooldown_minutes integer DEFAULT 120 NOT NULL,
    quiet_hours jsonb,
    topic_allowlist jsonb,
    topic_blocklist jsonb,
    do_not_disturb boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_intervention_settings OWNER TO postgres;

--
-- Name: user_irt_ability; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_irt_ability (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    subject_id character varying(32),
    theta double precision DEFAULT '0'::double precision NOT NULL,
    last_updated_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_irt_ability OWNER TO postgres;

--
-- Name: user_node_status; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_node_status (
    user_id uuid NOT NULL,
    node_id uuid NOT NULL,
    mastery_score double precision NOT NULL,
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
    first_unlock_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    revision bigint DEFAULT '0'::bigint NOT NULL,
    bkt_mastery_prob double precision DEFAULT '0'::double precision NOT NULL,
    bkt_last_updated_at timestamp without time zone
);


ALTER TABLE user_node_status OWNER TO postgres;

--
-- Name: user_persona_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_persona_keys (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    key_id character varying(128) NOT NULL,
    encrypted_key text,
    is_active boolean DEFAULT true NOT NULL,
    destroyed_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_persona_keys OWNER TO postgres;

--
-- Name: user_preferences_center; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_preferences_center (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    schema_version integer DEFAULT 1 NOT NULL,
    explicit jsonb DEFAULT '{}'::jsonb NOT NULL,
    inferred jsonb DEFAULT '{}'::jsonb NOT NULL,
    last_explicit_update timestamp without time zone,
    last_inferred_update timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_preferences_center OWNER TO postgres;

--
-- Name: user_state_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_state_snapshots (
    id uuid NOT NULL,
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
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE user_state_snapshots OWNER TO postgres;

--
-- Name: user_tool_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE user_tool_history (
    id integer NOT NULL,
    user_id uuid NOT NULL,
    tool_name character varying(100) NOT NULL,
    success boolean NOT NULL,
    execution_time_ms integer,
    error_message character varying(500),
    context_snapshot jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    is_minor boolean,
    age_verified boolean DEFAULT false NOT NULL,
    age_verification_source character varying(50),
    age_verified_at timestamp without time zone
);


ALTER TABLE users OWNER TO postgres;

--
-- Name: word_books; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE word_books (
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


ALTER TABLE word_books OWNER TO postgres;

--
-- Name: chat_messages_2024_q1; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_2024_q1 FOR VALUES FROM ('2024-01-01 00:00:00') TO ('2024-04-01 00:00:00');


--
-- Name: chat_messages_2024_q2; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_2024_q2 FOR VALUES FROM ('2024-04-01 00:00:00') TO ('2024-07-01 00:00:00');


--
-- Name: chat_messages_2024_q3; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_2024_q3 FOR VALUES FROM ('2024-07-01 00:00:00') TO ('2024-10-01 00:00:00');


--
-- Name: chat_messages_2024_q4; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_2024_q4 FOR VALUES FROM ('2024-10-01 00:00:00') TO ('2025-01-01 00:00:00');


--
-- Name: chat_messages_2025_q1; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_2025_q1 FOR VALUES FROM ('2025-01-01 00:00:00') TO ('2025-04-01 00:00:00');


--
-- Name: chat_messages_2025_q2; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_2025_q2 FOR VALUES FROM ('2025-04-01 00:00:00') TO ('2025-07-01 00:00:00');


--
-- Name: chat_messages_2025_q3; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_2025_q3 FOR VALUES FROM ('2025-07-01 00:00:00') TO ('2025-10-01 00:00:00');


--
-- Name: chat_messages_2025_q4; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_2025_q4 FOR VALUES FROM ('2025-10-01 00:00:00') TO ('2026-01-01 00:00:00');


--
-- Name: chat_messages_2026_q1; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_2026_q1 FOR VALUES FROM ('2026-01-01 00:00:00') TO ('2026-04-01 00:00:00');


--
-- Name: chat_messages_2026_q2; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_2026_q2 FOR VALUES FROM ('2026-04-01 00:00:00') TO ('2026-07-01 00:00:00');


--
-- Name: chat_messages_default; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_default DEFAULT;


--
-- Name: chat_messages_legacy; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages ATTACH PARTITION chat_messages_legacy FOR VALUES FROM (MINVALUE) TO ('2024-01-01 00:00:00');


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
-- Name: outbox_events id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY outbox_events ALTER COLUMN id SET DEFAULT nextval('outbox_events_id_seq'::regclass);


--
-- Name: subjects id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY subjects ALTER COLUMN id SET DEFAULT nextval('subjects_id_seq'::regclass);


--
-- Name: user_tool_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_tool_history ALTER COLUMN id SET DEFAULT nextval('user_tool_history_id_seq'::regclass);


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
-- Name: behavior_patterns behavior_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY behavior_patterns
    ADD CONSTRAINT behavior_patterns_pkey PRIMARY KEY (id);


--
-- Name: broadcast_messages broadcast_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY broadcast_messages
    ADD CONSTRAINT broadcast_messages_pkey PRIMARY KEY (id);


--
-- Name: chat_messages chat_messages_partitioned_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages
    ADD CONSTRAINT chat_messages_partitioned_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2024_q1 chat_messages_2024_q1_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_2024_q1
    ADD CONSTRAINT chat_messages_2024_q1_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2024_q2 chat_messages_2024_q2_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_2024_q2
    ADD CONSTRAINT chat_messages_2024_q2_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2024_q3 chat_messages_2024_q3_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_2024_q3
    ADD CONSTRAINT chat_messages_2024_q3_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2024_q4 chat_messages_2024_q4_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_2024_q4
    ADD CONSTRAINT chat_messages_2024_q4_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2025_q1 chat_messages_2025_q1_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_2025_q1
    ADD CONSTRAINT chat_messages_2025_q1_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2025_q2 chat_messages_2025_q2_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_2025_q2
    ADD CONSTRAINT chat_messages_2025_q2_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2025_q3 chat_messages_2025_q3_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_2025_q3
    ADD CONSTRAINT chat_messages_2025_q3_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2025_q4 chat_messages_2025_q4_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_2025_q4
    ADD CONSTRAINT chat_messages_2025_q4_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2026_q1 chat_messages_2026_q1_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_2026_q1
    ADD CONSTRAINT chat_messages_2026_q1_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2026_q2 chat_messages_2026_q2_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_2026_q2
    ADD CONSTRAINT chat_messages_2026_q2_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_default chat_messages_default_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_default
    ADD CONSTRAINT chat_messages_default_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_legacy chat_messages_legacy_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_legacy
    ADD CONSTRAINT chat_messages_legacy_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_old chat_messages_message_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_old
    ADD CONSTRAINT chat_messages_message_id_key UNIQUE (message_id);


--
-- Name: chat_messages_old chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_old
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


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
-- Name: event_store event_store_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY event_store
    ADD CONSTRAINT event_store_pkey PRIMARY KEY (id);


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
-- Name: mastery_audit_log mastery_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY mastery_audit_log
    ADD CONSTRAINT mastery_audit_log_pkey PRIMARY KEY (id);


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
-- Name: nightly_reviews nightly_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY nightly_reviews
    ADD CONSTRAINT nightly_reviews_pkey PRIMARY KEY (id);


--
-- Name: nightly_reviews nightly_reviews_user_id_review_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY nightly_reviews
    ADD CONSTRAINT nightly_reviews_user_id_review_date_key UNIQUE (user_id, review_date);


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
-- Name: outbox_events outbox_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY outbox_events
    ADD CONSTRAINT outbox_events_pkey PRIMARY KEY (id);


--
-- Name: persona_snapshots persona_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY persona_snapshots
    ADD CONSTRAINT persona_snapshots_pkey PRIMARY KEY (id);


--
-- Name: plans plans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plans
    ADD CONSTRAINT plans_pkey PRIMARY KEY (id);


--
-- Name: post_likes post_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY post_likes
    ADD CONSTRAINT post_likes_pkey PRIMARY KEY (user_id, post_id);


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
    ADD CONSTRAINT processed_events_pkey PRIMARY KEY (event_id);


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
-- Name: security_audit_logs security_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY security_audit_logs
    ADD CONSTRAINT security_audit_logs_pkey PRIMARY KEY (id);


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
-- Name: system_config_change_logs system_config_change_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY system_config_change_logs
    ADD CONSTRAINT system_config_change_logs_pkey PRIMARY KEY (id);


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
-- Name: tracking_events tracking_events_event_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tracking_events
    ADD CONSTRAINT tracking_events_event_id_key UNIQUE (event_id);


--
-- Name: tracking_events tracking_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tracking_events
    ADD CONSTRAINT tracking_events_pkey PRIMARY KEY (id);


--
-- Name: event_store unique_event; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY event_store
    ADD CONSTRAINT unique_event UNIQUE (aggregate_type, aggregate_id, sequence_number);


--
-- Name: projection_snapshots unique_snapshot; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY projection_snapshots
    ADD CONSTRAINT unique_snapshot UNIQUE (projection_name, aggregate_id);


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
-- Name: group_task_claims uq_task_claim; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY group_task_claims
    ADD CONSTRAINT uq_task_claim UNIQUE (group_task_id, user_id);


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
-- Name: user_daily_metrics user_daily_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_daily_metrics
    ADD CONSTRAINT user_daily_metrics_pkey PRIMARY KEY (id);


--
-- Name: user_encryption_keys user_encryption_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_encryption_keys
    ADD CONSTRAINT user_encryption_keys_pkey PRIMARY KEY (id);


--
-- Name: user_intervention_settings user_intervention_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_intervention_settings
    ADD CONSTRAINT user_intervention_settings_pkey PRIMARY KEY (id);


--
-- Name: user_intervention_settings user_intervention_settings_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_intervention_settings
    ADD CONSTRAINT user_intervention_settings_user_id_key UNIQUE (user_id);


--
-- Name: user_irt_ability user_irt_ability_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_irt_ability
    ADD CONSTRAINT user_irt_ability_pkey PRIMARY KEY (id);


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
-- Name: user_preferences_center user_preferences_center_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_preferences_center
    ADD CONSTRAINT user_preferences_center_user_id_key UNIQUE (user_id);


--
-- Name: user_state_snapshots user_state_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_state_snapshots
    ADD CONSTRAINT user_state_snapshots_pkey PRIMARY KEY (id);


--
-- Name: user_tool_history user_tool_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_tool_history
    ADD CONSTRAINT user_tool_history_pkey PRIMARY KEY (id);


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
-- Name: word_books word_books_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY word_books
    ADD CONSTRAINT word_books_pkey PRIMARY KEY (id);


--
-- Name: chat_messages_message_id_created_at_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_message_id_created_at_key ON ONLY chat_messages USING btree (message_id, created_at);


--
-- Name: chat_messages_2024_q1_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2024_q1_message_id_created_at_idx ON chat_messages_2024_q1 USING btree (message_id, created_at);


--
-- Name: chat_messages_2024_q2_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2024_q2_message_id_created_at_idx ON chat_messages_2024_q2 USING btree (message_id, created_at);


--
-- Name: chat_messages_2024_q3_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2024_q3_message_id_created_at_idx ON chat_messages_2024_q3 USING btree (message_id, created_at);


--
-- Name: chat_messages_2024_q4_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2024_q4_message_id_created_at_idx ON chat_messages_2024_q4 USING btree (message_id, created_at);


--
-- Name: chat_messages_2025_q1_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2025_q1_message_id_created_at_idx ON chat_messages_2025_q1 USING btree (message_id, created_at);


--
-- Name: chat_messages_2025_q2_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2025_q2_message_id_created_at_idx ON chat_messages_2025_q2 USING btree (message_id, created_at);


--
-- Name: chat_messages_2025_q3_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2025_q3_message_id_created_at_idx ON chat_messages_2025_q3 USING btree (message_id, created_at);


--
-- Name: chat_messages_2025_q4_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2025_q4_message_id_created_at_idx ON chat_messages_2025_q4 USING btree (message_id, created_at);


--
-- Name: chat_messages_2026_q1_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2026_q1_message_id_created_at_idx ON chat_messages_2026_q1 USING btree (message_id, created_at);


--
-- Name: chat_messages_2026_q2_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2026_q2_message_id_created_at_idx ON chat_messages_2026_q2 USING btree (message_id, created_at);


--
-- Name: chat_messages_default_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_default_message_id_created_at_idx ON chat_messages_default USING btree (message_id, created_at);


--
-- Name: chat_messages_legacy_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_legacy_message_id_created_at_idx ON chat_messages_legacy USING btree (message_id, created_at);


--
-- Name: idx_agent_stats_summary_user_agent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_agent_stats_summary_user_agent ON agent_stats_summary USING btree (user_id, agent_type);


--
-- Name: idx_audit_log_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_created_at ON mastery_audit_log USING btree (created_at);


--
-- Name: idx_audit_log_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_node_id ON mastery_audit_log USING btree (node_id);


--
-- Name: idx_audit_log_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_user_id ON mastery_audit_log USING btree (user_id);


--
-- Name: idx_chat_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_created_at ON chat_messages_old USING btree (created_at);


--
-- Name: idx_chat_messages_session_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_messages_session_created ON chat_messages_old USING btree (session_id, created_at DESC);


--
-- Name: idx_chat_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_role ON chat_messages_old USING btree (role);


--
-- Name: idx_chat_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_session_id ON chat_messages_old USING btree (session_id);


--
-- Name: idx_chat_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_task_id ON chat_messages_old USING btree (task_id);


--
-- Name: idx_chat_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_user_id ON chat_messages_old USING btree (user_id);


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

CREATE INDEX idx_cognitive_fragments_embedding_hnsw ON cognitive_fragments USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: idx_cognitive_fragments_source_event_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cognitive_fragments_source_event_id ON cognitive_fragments USING btree (source_event_id);


--
-- Name: idx_compliance_check_executed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_compliance_check_executed_at ON compliance_check_logs USING btree (executed_at);


--
-- Name: idx_compliance_check_executed_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_compliance_check_executed_by ON compliance_check_logs USING btree (executed_by);


--
-- Name: idx_compliance_check_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_compliance_check_status ON compliance_check_logs USING btree (status);


--
-- Name: idx_compliance_check_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_compliance_check_type ON compliance_check_logs USING btree (check_type);


--
-- Name: idx_config_change_changed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_config_change_changed_at ON system_config_change_logs USING btree (changed_at);


--
-- Name: idx_config_change_changed_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_config_change_changed_by ON system_config_change_logs USING btree (changed_by);


--
-- Name: idx_config_change_config_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_config_change_config_key ON system_config_change_logs USING btree (config_key);


--
-- Name: idx_crypto_shredding_certificates_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crypto_shredding_certificates_user ON crypto_shredding_certificates USING btree (user_id);


--
-- Name: idx_data_access_accessed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_data_access_accessed_at ON data_access_logs USING btree (accessed_at);


--
-- Name: idx_data_access_action; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_data_access_action ON data_access_logs USING btree (action);


--
-- Name: idx_data_access_ip; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_data_access_ip ON data_access_logs USING btree (ip_address);


--
-- Name: idx_data_access_resource_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_data_access_resource_id ON data_access_logs USING btree (resource_id);


--
-- Name: idx_data_access_resource_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_data_access_resource_type ON data_access_logs USING btree (resource_type);


--
-- Name: idx_data_access_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_data_access_user_id ON data_access_logs USING btree (user_id);


--
-- Name: idx_dict_word; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dict_word ON dictionary_entries USING btree (word);


--
-- Name: idx_dlq_replay_message; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dlq_replay_message ON dlq_replay_audit_logs USING btree (message_id);


--
-- Name: idx_document_chunks_chunk_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_document_chunks_chunk_index ON document_chunks USING btree (file_id, chunk_index);


--
-- Name: idx_error_records_cognitive_tags; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_records_cognitive_tags ON error_records USING gin (cognitive_tags);


--
-- Name: idx_errors_next_review; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_next_review ON error_records USING btree (user_id, next_review_at);


--
-- Name: idx_errors_question_fts; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_question_fts ON error_records USING gin (to_tsvector('simple'::regconfig, question_text));


--
-- Name: idx_errors_subject_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_subject_code ON error_records USING btree (subject_code);


--
-- Name: idx_errors_user_review; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_user_review ON error_records USING btree (user_id, next_review_at) WHERE (mastery_level < (1.0)::double precision);


--
-- Name: idx_errors_user_subject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_user_subject ON error_records USING btree (user_id, subject_code);


--
-- Name: idx_event_store_aggregate; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_store_aggregate ON event_store USING btree (aggregate_type, aggregate_id, sequence_number);


--
-- Name: idx_event_store_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_store_type ON event_store USING btree (event_type, created_at);


--
-- Name: idx_expansion_feedback_node; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_expansion_feedback_node ON expansion_feedback USING btree (trigger_node_id);


--
-- Name: idx_expansion_feedback_queue; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_expansion_feedback_queue ON expansion_feedback USING btree (expansion_queue_id);


--
-- Name: idx_expansion_feedback_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_expansion_feedback_user ON expansion_feedback USING btree (user_id);


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
-- Name: idx_group_files_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_files_deleted_at ON group_files USING btree (deleted_at);


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
-- Name: idx_group_messages_content_fts; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_messages_content_fts ON group_messages USING gin (to_tsvector('simple'::regconfig, COALESCE(content, ''::text))) WHERE (is_revoked = false);


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
-- Name: idx_intervention_audit_action; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_intervention_audit_action ON intervention_audit_logs USING btree (action);


--
-- Name: idx_intervention_audit_occurred; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_intervention_audit_occurred ON intervention_audit_logs USING btree (occurred_at);


--
-- Name: idx_intervention_audit_request; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_intervention_audit_request ON intervention_audit_logs USING btree (request_id);


--
-- Name: idx_intervention_audit_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_intervention_audit_user ON intervention_audit_logs USING btree (user_id);


--
-- Name: idx_intervention_feedback_request; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_intervention_feedback_request ON intervention_feedback USING btree (request_id);


--
-- Name: idx_intervention_feedback_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_intervention_feedback_type ON intervention_feedback USING btree (feedback_type);


--
-- Name: idx_intervention_feedback_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_intervention_feedback_user ON intervention_feedback USING btree (user_id);


--
-- Name: idx_intervention_requests_dedupe; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_intervention_requests_dedupe ON intervention_requests USING btree (dedupe_key);


--
-- Name: idx_intervention_requests_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_intervention_requests_status ON intervention_requests USING btree (status);


--
-- Name: idx_intervention_requests_topic; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_intervention_requests_topic ON intervention_requests USING btree (topic);


--
-- Name: idx_intervention_requests_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_intervention_requests_user ON intervention_requests USING btree (user_id);


--
-- Name: idx_intervention_settings_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_intervention_settings_user ON user_intervention_settings USING btree (user_id);


--
-- Name: idx_irt_item_question; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_irt_item_question ON irt_item_parameters USING btree (question_id);


--
-- Name: idx_irt_item_subject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_irt_item_subject ON irt_item_parameters USING btree (subject_id);


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
-- Name: idx_knowledge_nodes_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_knowledge_nodes_embedding_hnsw ON knowledge_nodes USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: idx_legal_holds_case; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_legal_holds_case ON legal_holds USING btree (case_ref);


--
-- Name: idx_legal_holds_device; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_legal_holds_device ON legal_holds USING btree (device_id);


--
-- Name: idx_legal_holds_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_legal_holds_user ON legal_holds USING btree (user_id);


--
-- Name: idx_login_attempts_attempted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_login_attempts_attempted_at ON login_attempts USING btree (attempted_at);


--
-- Name: idx_login_attempts_ip; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_login_attempts_ip ON login_attempts USING btree (ip_address);


--
-- Name: idx_login_attempts_success; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_login_attempts_success ON login_attempts USING btree (success);


--
-- Name: idx_login_attempts_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_login_attempts_user_id ON login_attempts USING btree (user_id);


--
-- Name: idx_login_attempts_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_login_attempts_username ON login_attempts USING btree (username);


--
-- Name: idx_member_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_member_group ON group_members USING btree (group_id);


--
-- Name: idx_member_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_member_user ON group_members USING btree (user_id);


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
-- Name: idx_message_topic; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_topic ON group_messages USING btree (group_id, topic);


--
-- Name: idx_nightly_reviews_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_nightly_reviews_date ON nightly_reviews USING btree (review_date);


--
-- Name: idx_nightly_reviews_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_nightly_reviews_user ON nightly_reviews USING btree (user_id);


--
-- Name: idx_offline_queue_nonce; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_offline_queue_nonce ON offline_message_queue USING btree (user_id, client_nonce);


--
-- Name: idx_offline_queue_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_offline_queue_user_status ON offline_message_queue USING btree (user_id, status);


--
-- Name: idx_outbox_aggregate; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_outbox_aggregate ON event_outbox USING btree (aggregate_type, aggregate_id, sequence_number);


--
-- Name: idx_outbox_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_outbox_status ON outbox_events USING btree (status) WHERE ((status)::text = 'pending'::text);


--
-- Name: idx_outbox_unpublished; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_outbox_unpublished ON event_outbox USING btree (created_at) WHERE (published_at IS NULL);


--
-- Name: idx_persona_snapshots_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_persona_snapshots_user ON persona_snapshots USING btree (user_id);


--
-- Name: idx_persona_snapshots_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_persona_snapshots_version ON persona_snapshots USING btree (persona_version);


--
-- Name: idx_plans_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_is_active ON plans USING btree (is_active);


--
-- Name: idx_plans_target_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_target_date ON plans USING btree (target_date);


--
-- Name: idx_plans_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_type ON plans USING btree (type);


--
-- Name: idx_plans_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_user_id ON plans USING btree (user_id);


--
-- Name: idx_post_likes_post_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_post_likes_post_id ON post_likes USING btree (post_id);


--
-- Name: idx_posts_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_created_at ON posts USING btree (created_at);


--
-- Name: idx_posts_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_user_id ON posts USING btree (user_id);


--
-- Name: idx_posts_visibility_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_visibility_created ON posts USING btree (visibility, created_at DESC) WHERE ((visibility)::text = 'public'::text);


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
-- Name: idx_private_messages_content_fts; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_private_messages_content_fts ON private_messages USING gin (to_tsvector('simple'::regconfig, COALESCE(content, ''::text))) WHERE (is_revoked = false);


--
-- Name: idx_processed_events_cleanup; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_processed_events_cleanup ON processed_events USING btree (processed_at);


--
-- Name: idx_processed_events_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_processed_events_group ON processed_events USING btree (consumer_group, processed_at);


--
-- Name: idx_security_audit_event_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_security_audit_event_type ON security_audit_logs USING btree (event_type);


--
-- Name: idx_security_audit_ip; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_security_audit_ip ON security_audit_logs USING btree (ip_address);


--
-- Name: idx_security_audit_resource; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_security_audit_resource ON security_audit_logs USING btree (resource);


--
-- Name: idx_security_audit_threat_level; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_security_audit_threat_level ON security_audit_logs USING btree (threat_level);


--
-- Name: idx_security_audit_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_security_audit_timestamp ON security_audit_logs USING btree ("timestamp");


--
-- Name: idx_security_audit_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_security_audit_user_id ON security_audit_logs USING btree (user_id);


--
-- Name: idx_semantic_links_relation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_semantic_links_relation ON semantic_links USING btree (relation_type);


--
-- Name: idx_semantic_links_source; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_semantic_links_source ON semantic_links USING btree (source_type, source_id);


--
-- Name: idx_semantic_links_target; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_semantic_links_target ON semantic_links USING btree (target_type, target_id);


--
-- Name: idx_share_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_group ON shared_resources USING btree (group_id);


--
-- Name: idx_share_resource_capsule; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_resource_capsule ON shared_resources USING btree (curiosity_capsule_id);


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
-- Name: idx_snapshots_projection; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_snapshots_projection ON projection_snapshots USING btree (projection_name, created_at);


--
-- Name: idx_strategy_nodes_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_strategy_nodes_hash ON strategy_nodes USING btree (content_hash);


--
-- Name: idx_strategy_nodes_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_strategy_nodes_user ON strategy_nodes USING btree (user_id);


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
-- Name: idx_tasks_tags_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_tags_gin ON tasks USING gin (tags);


--
-- Name: idx_tasks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_user_id ON tasks USING btree (user_id);


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
-- Name: idx_tracking_events_entities_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tracking_events_entities_gin ON tracking_events USING gin (entities);


--
-- Name: idx_tracking_events_event_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_tracking_events_event_id ON tracking_events USING btree (event_id);


--
-- Name: idx_tracking_events_ts; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tracking_events_ts ON tracking_events USING btree (ts_ms);


--
-- Name: idx_tracking_events_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tracking_events_type ON tracking_events USING btree (event_type);


--
-- Name: idx_tracking_events_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tracking_events_user ON tracking_events USING btree (user_id);


--
-- Name: idx_tracking_events_user_ts; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tracking_events_user_ts ON tracking_events USING btree (user_id, ts_ms);


--
-- Name: idx_user_encryption_keys_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_encryption_keys_user ON user_encryption_keys USING btree (user_id, is_active);


--
-- Name: idx_user_irt_subject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_irt_subject ON user_irt_ability USING btree (subject_id);


--
-- Name: idx_user_irt_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_irt_user ON user_irt_ability USING btree (user_id);


--
-- Name: idx_user_persona_keys_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_persona_keys_key ON user_persona_keys USING btree (key_id);


--
-- Name: idx_user_persona_keys_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_persona_keys_user ON user_persona_keys USING btree (user_id);


--
-- Name: idx_user_state_snapshot; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_state_snapshot ON user_state_snapshots USING btree (snapshot_at);


--
-- Name: idx_user_state_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_state_user ON user_state_snapshots USING btree (user_id);


--
-- Name: idx_user_tool_history_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_created_at ON user_tool_history USING btree (created_at);


--
-- Name: idx_user_tool_history_metrics; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_metrics ON user_tool_history USING btree (user_id, tool_name, success, created_at);


--
-- Name: idx_user_tool_history_success; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_success ON user_tool_history USING btree (user_id, tool_name, success);


--
-- Name: idx_user_tool_history_tool_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_tool_name ON user_tool_history USING btree (tool_name);


--
-- Name: idx_user_tool_history_user_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_user_created ON user_tool_history USING btree (user_id, created_at);


--
-- Name: idx_user_tool_history_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_user_id ON user_tool_history USING btree (user_id);


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
-- Name: ix_agent_stats_agent_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_stats_agent_type ON agent_execution_stats USING btree (agent_type);


--
-- Name: ix_agent_stats_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_stats_created_at ON agent_execution_stats USING btree (created_at);


--
-- Name: ix_agent_stats_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_stats_session_id ON agent_execution_stats USING btree (session_id);


--
-- Name: ix_agent_stats_user_agent_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_stats_user_agent_type ON agent_execution_stats USING btree (user_id, agent_type);


--
-- Name: ix_agent_stats_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_stats_user_id ON agent_execution_stats USING btree (user_id);


--
-- Name: ix_behavior_patterns_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_behavior_patterns_deleted_at ON behavior_patterns USING btree (deleted_at);


--
-- Name: ix_behavior_patterns_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_behavior_patterns_user_id ON behavior_patterns USING btree (user_id);


--
-- Name: ix_chat_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_messages_deleted_at ON chat_messages_old USING btree (deleted_at);


--
-- Name: ix_chat_messages_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_messages_session_id ON chat_messages_old USING btree (session_id);


--
-- Name: ix_chat_messages_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_messages_user_id ON chat_messages_old USING btree (user_id);


--
-- Name: ix_cognitive_fragments_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cognitive_fragments_deleted_at ON cognitive_fragments USING btree (deleted_at);


--
-- Name: ix_cognitive_fragments_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cognitive_fragments_user_id ON cognitive_fragments USING btree (user_id);


--
-- Name: ix_collaborative_galaxies_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_collaborative_galaxies_deleted_at ON collaborative_galaxies USING btree (deleted_at);


--
-- Name: ix_crdt_operation_log_galaxy_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_crdt_operation_log_galaxy_id ON crdt_operation_log USING btree (galaxy_id);


--
-- Name: ix_crdt_operation_log_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_crdt_operation_log_timestamp ON crdt_operation_log USING btree ("timestamp");


--
-- Name: ix_curiosity_capsules_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_curiosity_capsules_deleted_at ON curiosity_capsules USING btree (deleted_at);


--
-- Name: ix_curiosity_capsules_related_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_curiosity_capsules_related_task_id ON curiosity_capsules USING btree (related_task_id);


--
-- Name: ix_curiosity_capsules_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_curiosity_capsules_user_id ON curiosity_capsules USING btree (user_id);


--
-- Name: ix_dictionary_entries_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_dictionary_entries_deleted_at ON dictionary_entries USING btree (deleted_at);


--
-- Name: ix_dictionary_entries_word; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_dictionary_entries_word ON dictionary_entries USING btree (word);


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
-- Name: ix_group_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_messages_deleted_at ON group_messages USING btree (deleted_at);


--
-- Name: ix_group_messages_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_messages_group_id ON group_messages USING btree (group_id);


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
-- Name: ix_notifications_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notifications_deleted_at ON notifications USING btree (deleted_at);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notifications_user_id ON notifications USING btree (user_id);


--
-- Name: ix_plans_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_deleted_at ON plans USING btree (deleted_at);


--
-- Name: ix_plans_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_is_active ON plans USING btree (is_active);


--
-- Name: ix_plans_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_user_id ON plans USING btree (user_id);


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
-- Name: ix_stored_files_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_deleted_at ON stored_files USING btree (deleted_at);


--
-- Name: ix_stored_files_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stored_files_user_id ON stored_files USING btree (user_id);


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
-- Name: ix_tasks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_user_id ON tasks USING btree (user_id);


--
-- Name: ix_token_usage_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_token_usage_deleted_at ON token_usage USING btree (deleted_at);


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
-- Name: ix_user_node_status_next_review_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_node_status_next_review_at ON user_node_status USING btree (next_review_at);


--
-- Name: ix_user_preferences_center_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_preferences_center_deleted_at ON user_preferences_center USING btree (deleted_at);


--
-- Name: ix_user_preferences_center_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_preferences_center_user_id ON user_preferences_center USING btree (user_id);


--
-- Name: ix_users_apple_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_apple_id ON users USING btree (apple_id);


--
-- Name: ix_users_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_deleted_at ON users USING btree (deleted_at);


--
-- Name: ix_users_google_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_google_id ON users USING btree (google_id);


--
-- Name: ix_users_wechat_unionid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_wechat_unionid ON users USING btree (wechat_unionid);


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
-- Name: chat_messages_2024_q1_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_2024_q1_message_id_created_at_idx;


--
-- Name: chat_messages_2024_q1_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_2024_q1_pkey;


--
-- Name: chat_messages_2024_q2_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_2024_q2_message_id_created_at_idx;


--
-- Name: chat_messages_2024_q2_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_2024_q2_pkey;


--
-- Name: chat_messages_2024_q3_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_2024_q3_message_id_created_at_idx;


--
-- Name: chat_messages_2024_q3_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_2024_q3_pkey;


--
-- Name: chat_messages_2024_q4_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_2024_q4_message_id_created_at_idx;


--
-- Name: chat_messages_2024_q4_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_2024_q4_pkey;


--
-- Name: chat_messages_2025_q1_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_2025_q1_message_id_created_at_idx;


--
-- Name: chat_messages_2025_q1_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_2025_q1_pkey;


--
-- Name: chat_messages_2025_q2_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_2025_q2_message_id_created_at_idx;


--
-- Name: chat_messages_2025_q2_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_2025_q2_pkey;


--
-- Name: chat_messages_2025_q3_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_2025_q3_message_id_created_at_idx;


--
-- Name: chat_messages_2025_q3_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_2025_q3_pkey;


--
-- Name: chat_messages_2025_q4_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_2025_q4_message_id_created_at_idx;


--
-- Name: chat_messages_2025_q4_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_2025_q4_pkey;


--
-- Name: chat_messages_2026_q1_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_2026_q1_message_id_created_at_idx;


--
-- Name: chat_messages_2026_q1_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_2026_q1_pkey;


--
-- Name: chat_messages_2026_q2_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_2026_q2_message_id_created_at_idx;


--
-- Name: chat_messages_2026_q2_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_2026_q2_pkey;


--
-- Name: chat_messages_default_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_default_message_id_created_at_idx;


--
-- Name: chat_messages_default_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_default_pkey;


--
-- Name: chat_messages_legacy_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_message_id_created_at_key ATTACH PARTITION chat_messages_legacy_message_id_created_at_idx;


--
-- Name: chat_messages_legacy_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX chat_messages_partitioned_pkey ATTACH PARTITION chat_messages_legacy_pkey;


--
-- Name: behavior_patterns behavior_patterns_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY behavior_patterns
    ADD CONSTRAINT behavior_patterns_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: broadcast_messages broadcast_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY broadcast_messages
    ADD CONSTRAINT broadcast_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE chat_messages
    ADD CONSTRAINT chat_messages_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);


--
-- Name: chat_messages_old chat_messages_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_old
    ADD CONSTRAINT chat_messages_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);


--
-- Name: chat_messages chat_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE chat_messages
    ADD CONSTRAINT chat_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: chat_messages_old chat_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chat_messages_old
    ADD CONSTRAINT chat_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


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
    ADD CONSTRAINT mastery_audit_log_node_id_fkey FOREIGN KEY (node_id) REFERENCES knowledge_nodes(id);


--
-- Name: mastery_audit_log mastery_audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY mastery_audit_log
    ADD CONSTRAINT mastery_audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


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
-- Name: persona_snapshots persona_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY persona_snapshots
    ADD CONSTRAINT persona_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: plans plans_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY plans
    ADD CONSTRAINT plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: post_likes post_likes_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY post_likes
    ADD CONSTRAINT post_likes_post_id_fkey FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE;


--
-- Name: post_likes post_likes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY post_likes
    ADD CONSTRAINT post_likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


--
-- Name: posts posts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY posts
    ADD CONSTRAINT posts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: security_audit_logs security_audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY security_audit_logs
    ADD CONSTRAINT security_audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


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
-- Name: system_config_change_logs system_config_change_logs_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY system_config_change_logs
    ADD CONSTRAINT system_config_change_logs_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES users(id);


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
-- Name: user_daily_metrics user_daily_metrics_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_daily_metrics
    ADD CONSTRAINT user_daily_metrics_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_encryption_keys user_encryption_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_encryption_keys
    ADD CONSTRAINT user_encryption_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


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
-- Name: user_state_snapshots user_state_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_state_snapshots
    ADD CONSTRAINT user_state_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


--
-- Name: user_tool_history user_tool_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY user_tool_history
    ADD CONSTRAINT user_tool_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);


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

