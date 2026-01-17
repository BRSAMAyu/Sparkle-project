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
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS '';


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

CREATE TYPE public.avatarstatus AS ENUM (
    'APPROVED',
    'PENDING',
    'REJECTED'
);


ALTER TYPE public.avatarstatus OWNER TO postgres;

--
-- Name: focusstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.focusstatus AS ENUM (
    'COMPLETED',
    'INTERRUPTED'
);


ALTER TYPE public.focusstatus OWNER TO postgres;

--
-- Name: focustype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.focustype AS ENUM (
    'POMODORO',
    'STOPWATCH'
);


ALTER TYPE public.focustype OWNER TO postgres;

--
-- Name: friendshipstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.friendshipstatus AS ENUM (
    'PENDING',
    'ACCEPTED',
    'BLOCKED'
);


ALTER TYPE public.friendshipstatus OWNER TO postgres;

--
-- Name: grouprole; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.grouprole AS ENUM (
    'OWNER',
    'ADMIN',
    'MEMBER'
);


ALTER TYPE public.grouprole OWNER TO postgres;

--
-- Name: grouptype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.grouptype AS ENUM (
    'SQUAD',
    'SPRINT',
    'OFFICIAL'
);


ALTER TYPE public.grouptype OWNER TO postgres;

--
-- Name: messagerole; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.messagerole AS ENUM (
    'USER',
    'ASSISTANT',
    'SYSTEM'
);


ALTER TYPE public.messagerole OWNER TO postgres;

--
-- Name: messagetype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.messagetype AS ENUM (
    'TEXT',
    'TASK_SHARE',
    'PLAN_SHARE',
    'FRAGMENT_SHARE',
    'PROGRESS',
    'ACHIEVEMENT',
    'CHECKIN',
    'SYSTEM',
    'CAPSULE_SHARE',
    'PRISM_SHARE',
    'FILE_SHARE'
);


ALTER TYPE public.messagetype OWNER TO postgres;

--
-- Name: plantype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.plantype AS ENUM (
    'SPRINT',
    'GROWTH'
);


ALTER TYPE public.plantype OWNER TO postgres;

--
-- Name: taskstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.taskstatus AS ENUM (
    'PENDING',
    'IN_PROGRESS',
    'COMPLETED',
    'ABANDONED'
);


ALTER TYPE public.taskstatus OWNER TO postgres;

--
-- Name: tasktype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.tasktype AS ENUM (
    'LEARNING',
    'TRAINING',
    'ERROR_FIX',
    'REFLECTION',
    'SOCIAL',
    'PLANNING'
);


ALTER TYPE public.tasktype OWNER TO postgres;

--
-- Name: userstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.userstatus AS ENUM (
    'ONLINE',
    'OFFLINE',
    'INVISIBLE'
);


ALTER TYPE public.userstatus OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_execution_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_execution_stats (
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


ALTER TABLE public.agent_execution_stats OWNER TO postgres;

--
-- Name: agent_execution_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_execution_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.agent_execution_stats_id_seq OWNER TO postgres;

--
-- Name: agent_execution_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_execution_stats_id_seq OWNED BY public.agent_execution_stats.id;


--
-- Name: agent_stats_summary; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres
--

CREATE MATERIALIZED VIEW public.agent_stats_summary AS
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
   FROM public.agent_execution_stats
  WHERE (completed_at IS NOT NULL)
  GROUP BY user_id, agent_type
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.agent_stats_summary OWNER TO postgres;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(64) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: asset_suggestion_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asset_suggestion_logs (
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


ALTER TABLE public.asset_suggestion_logs OWNER TO postgres;

--
-- Name: behavior_patterns; Type: TABLE; Schema: public; Owner: postgres
--

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
    deleted_at timestamp without time zone
);


ALTER TABLE public.behavior_patterns OWNER TO postgres;

--
-- Name: broadcast_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.broadcast_messages (
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


ALTER TABLE public.broadcast_messages OWNER TO postgres;

--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
)
PARTITION BY RANGE (created_at);


ALTER TABLE public.chat_messages OWNER TO postgres;

--
-- Name: chat_messages_2024_q1; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_2024_q1 (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_2024_q1 OWNER TO postgres;

--
-- Name: chat_messages_2024_q2; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_2024_q2 (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_2024_q2 OWNER TO postgres;

--
-- Name: chat_messages_2024_q3; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_2024_q3 (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_2024_q3 OWNER TO postgres;

--
-- Name: chat_messages_2024_q4; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_2024_q4 (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_2024_q4 OWNER TO postgres;

--
-- Name: chat_messages_2025_q1; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_2025_q1 (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_2025_q1 OWNER TO postgres;

--
-- Name: chat_messages_2025_q2; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_2025_q2 (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_2025_q2 OWNER TO postgres;

--
-- Name: chat_messages_2025_q3; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_2025_q3 (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_2025_q3 OWNER TO postgres;

--
-- Name: chat_messages_2025_q4; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_2025_q4 (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_2025_q4 OWNER TO postgres;

--
-- Name: chat_messages_2026_q1; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_2026_q1 (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_2026_q1 OWNER TO postgres;

--
-- Name: chat_messages_2026_q2; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_2026_q2 (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_2026_q2 OWNER TO postgres;

--
-- Name: chat_messages_default; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_default (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_default OWNER TO postgres;

--
-- Name: chat_messages_legacy; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_legacy (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_legacy OWNER TO postgres;

--
-- Name: chat_messages_old; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages_old (
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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.chat_messages_old OWNER TO postgres;

--
-- Name: cognitive_fragments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cognitive_fragments (
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
    embedding public.vector(1536),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.cognitive_fragments OWNER TO postgres;

--
-- Name: curiosity_capsules; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: dictionary_entries; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: error_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.error_records (
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
    suggested_concepts text[] DEFAULT '{}'::text[]
);


ALTER TABLE public.error_records OWNER TO postgres;

--
-- Name: COLUMN error_records.question_text; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.question_text IS '题目原文';


--
-- Name: COLUMN error_records.question_image_url; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.question_image_url IS '题目图片URL（可选）';


--
-- Name: COLUMN error_records.user_answer; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.user_answer IS '用户的错误答案';


--
-- Name: COLUMN error_records.correct_answer; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.correct_answer IS '正确答案';


--
-- Name: COLUMN error_records.subject_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.subject_code IS '科目';


--
-- Name: COLUMN error_records.chapter; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.chapter IS '章节（可选）';


--
-- Name: COLUMN error_records.source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.source IS '来源';


--
-- Name: COLUMN error_records.difficulty; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.difficulty IS '难度1-5';


--
-- Name: COLUMN error_records.mastery_level; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.mastery_level IS '掌握度0-1';


--
-- Name: COLUMN error_records.review_count; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.review_count IS '复习次数';


--
-- Name: COLUMN error_records.next_review_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.next_review_at IS '下次复习时间';


--
-- Name: COLUMN error_records.last_reviewed_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.error_records.last_reviewed_at IS '上次复习时间';


--
-- Name: event_outbox; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.event_outbox (
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


ALTER TABLE public.event_outbox OWNER TO postgres;

--
-- Name: event_sequence_counters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.event_sequence_counters (
    aggregate_type character varying(100) NOT NULL,
    aggregate_id uuid NOT NULL,
    next_sequence bigint DEFAULT 1 NOT NULL
);


ALTER TABLE public.event_sequence_counters OWNER TO postgres;

--
-- Name: event_store; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.event_store (
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


ALTER TABLE public.event_store OWNER TO postgres;

--
-- Name: focus_sessions; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: friendships; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: group_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_members (
    group_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role public.grouprole NOT NULL,
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


ALTER TABLE public.group_members OWNER TO postgres;

--
-- Name: group_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_messages (
    group_id uuid NOT NULL,
    sender_id uuid,
    message_type public.messagetype NOT NULL,
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


ALTER TABLE public.group_messages OWNER TO postgres;

--
-- Name: group_task_claims; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: group_tasks; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: groups; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.groups OWNER TO postgres;

--
-- Name: idempotency_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.idempotency_keys (
    key character varying(64) NOT NULL,
    user_id uuid NOT NULL,
    response json NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone NOT NULL
);


ALTER TABLE public.idempotency_keys OWNER TO postgres;

--
-- Name: jobs; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: knowledge_nodes; Type: TABLE; Schema: public; Owner: postgres
--

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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    position_x double precision,
    position_y double precision,
    global_spark_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.knowledge_nodes OWNER TO postgres;

--
-- Name: learning_assets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.learning_assets (
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
    review_success_rate double precision DEFAULT 0.0 NOT NULL,
    last_seen_at timestamp without time zone,
    lookup_count integer DEFAULT 1 NOT NULL,
    star_count integer DEFAULT 0 NOT NULL,
    ignored_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.learning_assets OWNER TO postgres;

--
-- Name: mastery_audit_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mastery_audit_log (
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


ALTER TABLE public.mastery_audit_log OWNER TO postgres;

--
-- Name: mastery_audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.mastery_audit_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mastery_audit_log_id_seq OWNER TO postgres;

--
-- Name: mastery_audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.mastery_audit_log_id_seq OWNED BY public.mastery_audit_log.id;


--
-- Name: message_favorites; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.message_favorites (
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


ALTER TABLE public.message_favorites OWNER TO postgres;

--
-- Name: message_reports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.message_reports (
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


ALTER TABLE public.message_reports OWNER TO postgres;

--
-- Name: node_expansion_queue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.node_expansion_queue (
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
    deleted_at timestamp without time zone
);


ALTER TABLE public.node_expansion_queue OWNER TO postgres;

--
-- Name: node_relations; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: offline_message_queue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.offline_message_queue (
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


ALTER TABLE public.offline_message_queue OWNER TO postgres;

--
-- Name: outbox_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.outbox_events (
    id bigint NOT NULL,
    aggregate_id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    payload jsonb NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    published_at timestamp without time zone
);


ALTER TABLE public.outbox_events OWNER TO postgres;

--
-- Name: outbox_events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.outbox_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.outbox_events_id_seq OWNER TO postgres;

--
-- Name: outbox_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.outbox_events_id_seq OWNED BY public.outbox_events.id;


--
-- Name: plans; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: post_likes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.post_likes (
    user_id uuid NOT NULL,
    post_id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.post_likes OWNER TO postgres;

--
-- Name: posts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posts (
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


ALTER TABLE public.posts OWNER TO postgres;

--
-- Name: COLUMN posts.visibility; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts.visibility IS 'Controls post visibility: public (default), private (creator only), friends_only (creator + friends)';


--
-- Name: private_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.private_messages (
    sender_id uuid NOT NULL,
    receiver_id uuid NOT NULL,
    message_type public.messagetype NOT NULL,
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


ALTER TABLE public.private_messages OWNER TO postgres;

--
-- Name: processed_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.processed_events (
    event_id character varying(100) NOT NULL,
    consumer_group character varying(100) NOT NULL,
    processed_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.processed_events OWNER TO postgres;

--
-- Name: projection_metadata; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projection_metadata (
    projection_name character varying(100) NOT NULL,
    last_processed_position character varying(100),
    last_processed_at timestamp without time zone,
    version integer DEFAULT 1 NOT NULL,
    status character varying(20) DEFAULT '''active'''::character varying NOT NULL,
    error_message text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.projection_metadata OWNER TO postgres;

--
-- Name: projection_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projection_snapshots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    projection_name character varying(100) NOT NULL,
    aggregate_id uuid,
    snapshot_data jsonb NOT NULL,
    stream_position character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.projection_snapshots OWNER TO postgres;

--
-- Name: push_histories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.push_histories (
    user_id uuid NOT NULL,
    trigger_type character varying(50) NOT NULL,
    content_hash character varying(64),
    status character varying(50) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.push_histories OWNER TO postgres;

--
-- Name: push_preferences; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: shared_resources; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shared_resources (
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


ALTER TABLE public.shared_resources OWNER TO postgres;

--
-- Name: study_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.study_records (
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


ALTER TABLE public.study_records OWNER TO postgres;

--
-- Name: subjects; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: subjects_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.subjects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.subjects_id_seq OWNER TO postgres;

--
-- Name: subjects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.subjects_id_seq OWNED BY public.subjects.id;


--
-- Name: tasks; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.tasks OWNER TO postgres;

--
-- Name: user_daily_metrics; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: user_encryption_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_encryption_keys (
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


ALTER TABLE public.user_encryption_keys OWNER TO postgres;

--
-- Name: user_node_status; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_node_status (
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
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.user_node_status OWNER TO postgres;

--
-- Name: user_tool_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_tool_history (
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


ALTER TABLE public.user_tool_history OWNER TO postgres;

--
-- Name: user_tool_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_tool_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_tool_history_id_seq OWNER TO postgres;

--
-- Name: user_tool_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_tool_history_id_seq OWNED BY public.user_tool_history.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

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
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: word_books; Type: TABLE; Schema: public; Owner: postgres
--

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

--
-- Name: chat_messages_2024_q1; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_2024_q1 FOR VALUES FROM ('2024-01-01 00:00:00') TO ('2024-04-01 00:00:00');


--
-- Name: chat_messages_2024_q2; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_2024_q2 FOR VALUES FROM ('2024-04-01 00:00:00') TO ('2024-07-01 00:00:00');


--
-- Name: chat_messages_2024_q3; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_2024_q3 FOR VALUES FROM ('2024-07-01 00:00:00') TO ('2024-10-01 00:00:00');


--
-- Name: chat_messages_2024_q4; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_2024_q4 FOR VALUES FROM ('2024-10-01 00:00:00') TO ('2025-01-01 00:00:00');


--
-- Name: chat_messages_2025_q1; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_2025_q1 FOR VALUES FROM ('2025-01-01 00:00:00') TO ('2025-04-01 00:00:00');


--
-- Name: chat_messages_2025_q2; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_2025_q2 FOR VALUES FROM ('2025-04-01 00:00:00') TO ('2025-07-01 00:00:00');


--
-- Name: chat_messages_2025_q3; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_2025_q3 FOR VALUES FROM ('2025-07-01 00:00:00') TO ('2025-10-01 00:00:00');


--
-- Name: chat_messages_2025_q4; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_2025_q4 FOR VALUES FROM ('2025-10-01 00:00:00') TO ('2026-01-01 00:00:00');


--
-- Name: chat_messages_2026_q1; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_2026_q1 FOR VALUES FROM ('2026-01-01 00:00:00') TO ('2026-04-01 00:00:00');


--
-- Name: chat_messages_2026_q2; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_2026_q2 FOR VALUES FROM ('2026-04-01 00:00:00') TO ('2026-07-01 00:00:00');


--
-- Name: chat_messages_default; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_default DEFAULT;


--
-- Name: chat_messages_legacy; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ATTACH PARTITION public.chat_messages_legacy FOR VALUES FROM (MINVALUE) TO ('2024-01-01 00:00:00');


--
-- Name: agent_execution_stats id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_execution_stats ALTER COLUMN id SET DEFAULT nextval('public.agent_execution_stats_id_seq'::regclass);


--
-- Name: mastery_audit_log id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mastery_audit_log ALTER COLUMN id SET DEFAULT nextval('public.mastery_audit_log_id_seq'::regclass);


--
-- Name: outbox_events id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.outbox_events ALTER COLUMN id SET DEFAULT nextval('public.outbox_events_id_seq'::regclass);


--
-- Name: subjects id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjects ALTER COLUMN id SET DEFAULT nextval('public.subjects_id_seq'::regclass);


--
-- Name: user_tool_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_tool_history ALTER COLUMN id SET DEFAULT nextval('public.user_tool_history_id_seq'::regclass);


--
-- Name: agent_execution_stats agent_execution_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_execution_stats
    ADD CONSTRAINT agent_execution_stats_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: asset_suggestion_logs asset_suggestion_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_suggestion_logs
    ADD CONSTRAINT asset_suggestion_logs_pkey PRIMARY KEY (id);


--
-- Name: behavior_patterns behavior_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.behavior_patterns
    ADD CONSTRAINT behavior_patterns_pkey PRIMARY KEY (id);


--
-- Name: broadcast_messages broadcast_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.broadcast_messages
    ADD CONSTRAINT broadcast_messages_pkey PRIMARY KEY (id);


--
-- Name: chat_messages chat_messages_partitioned_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_partitioned_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2024_q1 chat_messages_2024_q1_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_2024_q1
    ADD CONSTRAINT chat_messages_2024_q1_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2024_q2 chat_messages_2024_q2_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_2024_q2
    ADD CONSTRAINT chat_messages_2024_q2_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2024_q3 chat_messages_2024_q3_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_2024_q3
    ADD CONSTRAINT chat_messages_2024_q3_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2024_q4 chat_messages_2024_q4_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_2024_q4
    ADD CONSTRAINT chat_messages_2024_q4_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2025_q1 chat_messages_2025_q1_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_2025_q1
    ADD CONSTRAINT chat_messages_2025_q1_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2025_q2 chat_messages_2025_q2_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_2025_q2
    ADD CONSTRAINT chat_messages_2025_q2_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2025_q3 chat_messages_2025_q3_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_2025_q3
    ADD CONSTRAINT chat_messages_2025_q3_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2025_q4 chat_messages_2025_q4_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_2025_q4
    ADD CONSTRAINT chat_messages_2025_q4_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2026_q1 chat_messages_2026_q1_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_2026_q1
    ADD CONSTRAINT chat_messages_2026_q1_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_2026_q2 chat_messages_2026_q2_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_2026_q2
    ADD CONSTRAINT chat_messages_2026_q2_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_default chat_messages_default_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_default
    ADD CONSTRAINT chat_messages_default_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_legacy chat_messages_legacy_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_legacy
    ADD CONSTRAINT chat_messages_legacy_pkey PRIMARY KEY (id, created_at);


--
-- Name: chat_messages_old chat_messages_message_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_old
    ADD CONSTRAINT chat_messages_message_id_key UNIQUE (message_id);


--
-- Name: chat_messages_old chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_old
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- Name: cognitive_fragments cognitive_fragments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cognitive_fragments
    ADD CONSTRAINT cognitive_fragments_pkey PRIMARY KEY (id);


--
-- Name: curiosity_capsules curiosity_capsules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.curiosity_capsules
    ADD CONSTRAINT curiosity_capsules_pkey PRIMARY KEY (id);


--
-- Name: dictionary_entries dictionary_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dictionary_entries
    ADD CONSTRAINT dictionary_entries_pkey PRIMARY KEY (id);


--
-- Name: error_records error_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.error_records
    ADD CONSTRAINT error_records_pkey PRIMARY KEY (id);


--
-- Name: event_outbox event_outbox_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_outbox
    ADD CONSTRAINT event_outbox_pkey PRIMARY KEY (id);


--
-- Name: event_sequence_counters event_sequence_counters_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_sequence_counters
    ADD CONSTRAINT event_sequence_counters_pkey PRIMARY KEY (aggregate_type, aggregate_id);


--
-- Name: event_store event_store_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_store
    ADD CONSTRAINT event_store_pkey PRIMARY KEY (id);


--
-- Name: focus_sessions focus_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.focus_sessions
    ADD CONSTRAINT focus_sessions_pkey PRIMARY KEY (id);


--
-- Name: friendships friendships_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.friendships
    ADD CONSTRAINT friendships_pkey PRIMARY KEY (id);


--
-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (id);


--
-- Name: group_messages group_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_pkey PRIMARY KEY (id);


--
-- Name: group_task_claims group_task_claims_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_task_claims
    ADD CONSTRAINT group_task_claims_pkey PRIMARY KEY (id);


--
-- Name: group_tasks group_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_tasks
    ADD CONSTRAINT group_tasks_pkey PRIMARY KEY (id);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: idempotency_keys idempotency_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (key);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: knowledge_nodes knowledge_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.knowledge_nodes
    ADD CONSTRAINT knowledge_nodes_pkey PRIMARY KEY (id);


--
-- Name: learning_assets learning_assets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learning_assets
    ADD CONSTRAINT learning_assets_pkey PRIMARY KEY (id);


--
-- Name: mastery_audit_log mastery_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mastery_audit_log
    ADD CONSTRAINT mastery_audit_log_pkey PRIMARY KEY (id);


--
-- Name: message_favorites message_favorites_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_favorites
    ADD CONSTRAINT message_favorites_pkey PRIMARY KEY (id);


--
-- Name: message_reports message_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_reports
    ADD CONSTRAINT message_reports_pkey PRIMARY KEY (id);


--
-- Name: node_expansion_queue node_expansion_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_pkey PRIMARY KEY (id);


--
-- Name: node_relations node_relations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.node_relations
    ADD CONSTRAINT node_relations_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: offline_message_queue offline_message_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.offline_message_queue
    ADD CONSTRAINT offline_message_queue_pkey PRIMARY KEY (id);


--
-- Name: outbox_events outbox_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.outbox_events
    ADD CONSTRAINT outbox_events_pkey PRIMARY KEY (id);


--
-- Name: plans plans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.plans
    ADD CONSTRAINT plans_pkey PRIMARY KEY (id);


--
-- Name: post_likes post_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_likes
    ADD CONSTRAINT post_likes_pkey PRIMARY KEY (user_id, post_id);


--
-- Name: posts posts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_pkey PRIMARY KEY (id);


--
-- Name: private_messages private_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_pkey PRIMARY KEY (id);


--
-- Name: processed_events processed_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.processed_events
    ADD CONSTRAINT processed_events_pkey PRIMARY KEY (event_id);


--
-- Name: projection_metadata projection_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projection_metadata
    ADD CONSTRAINT projection_metadata_pkey PRIMARY KEY (projection_name);


--
-- Name: projection_snapshots projection_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projection_snapshots
    ADD CONSTRAINT projection_snapshots_pkey PRIMARY KEY (id);


--
-- Name: push_histories push_histories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.push_histories
    ADD CONSTRAINT push_histories_pkey PRIMARY KEY (id);


--
-- Name: push_preferences push_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.push_preferences
    ADD CONSTRAINT push_preferences_pkey PRIMARY KEY (id);


--
-- Name: shared_resources shared_resources_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_pkey PRIMARY KEY (id);


--
-- Name: study_records study_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.study_records
    ADD CONSTRAINT study_records_pkey PRIMARY KEY (id);


--
-- Name: subjects subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: event_store unique_event; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_store
    ADD CONSTRAINT unique_event UNIQUE (aggregate_type, aggregate_id, sequence_number);


--
-- Name: projection_snapshots unique_snapshot; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projection_snapshots
    ADD CONSTRAINT unique_snapshot UNIQUE (projection_name, aggregate_id);


--
-- Name: friendships uq_friendship; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.friendships
    ADD CONSTRAINT uq_friendship UNIQUE (user_id, friend_id);


--
-- Name: group_members uq_group_member; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT uq_group_member UNIQUE (group_id, user_id);


--
-- Name: group_task_claims uq_task_claim; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_task_claims
    ADD CONSTRAINT uq_task_claim UNIQUE (group_task_id, user_id);


--
-- Name: user_daily_metrics uq_user_daily_metric; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_daily_metrics
    ADD CONSTRAINT uq_user_daily_metric UNIQUE (user_id, date);


--
-- Name: word_books uq_user_word; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.word_books
    ADD CONSTRAINT uq_user_word UNIQUE (user_id, word);


--
-- Name: user_daily_metrics user_daily_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_daily_metrics
    ADD CONSTRAINT user_daily_metrics_pkey PRIMARY KEY (id);


--
-- Name: user_encryption_keys user_encryption_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_encryption_keys
    ADD CONSTRAINT user_encryption_keys_pkey PRIMARY KEY (id);


--
-- Name: user_node_status user_node_status_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_node_status
    ADD CONSTRAINT user_node_status_pkey PRIMARY KEY (user_id, node_id);


--
-- Name: user_tool_history user_tool_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_tool_history
    ADD CONSTRAINT user_tool_history_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: word_books word_books_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.word_books
    ADD CONSTRAINT word_books_pkey PRIMARY KEY (id);


--
-- Name: agent_stats_summary_user_id_agent_type_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX agent_stats_summary_user_id_agent_type_idx ON public.agent_stats_summary USING btree (user_id, agent_type);


--
-- Name: chat_messages_message_id_created_at_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_message_id_created_at_key ON ONLY public.chat_messages USING btree (message_id, created_at);


--
-- Name: chat_messages_2024_q1_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2024_q1_message_id_created_at_idx ON public.chat_messages_2024_q1 USING btree (message_id, created_at);


--
-- Name: chat_messages_2024_q2_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2024_q2_message_id_created_at_idx ON public.chat_messages_2024_q2 USING btree (message_id, created_at);


--
-- Name: chat_messages_2024_q3_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2024_q3_message_id_created_at_idx ON public.chat_messages_2024_q3 USING btree (message_id, created_at);


--
-- Name: chat_messages_2024_q4_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2024_q4_message_id_created_at_idx ON public.chat_messages_2024_q4 USING btree (message_id, created_at);


--
-- Name: chat_messages_2025_q1_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2025_q1_message_id_created_at_idx ON public.chat_messages_2025_q1 USING btree (message_id, created_at);


--
-- Name: chat_messages_2025_q2_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2025_q2_message_id_created_at_idx ON public.chat_messages_2025_q2 USING btree (message_id, created_at);


--
-- Name: chat_messages_2025_q3_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2025_q3_message_id_created_at_idx ON public.chat_messages_2025_q3 USING btree (message_id, created_at);


--
-- Name: chat_messages_2025_q4_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2025_q4_message_id_created_at_idx ON public.chat_messages_2025_q4 USING btree (message_id, created_at);


--
-- Name: chat_messages_2026_q1_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2026_q1_message_id_created_at_idx ON public.chat_messages_2026_q1 USING btree (message_id, created_at);


--
-- Name: chat_messages_2026_q2_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_2026_q2_message_id_created_at_idx ON public.chat_messages_2026_q2 USING btree (message_id, created_at);


--
-- Name: chat_messages_default_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_default_message_id_created_at_idx ON public.chat_messages_default USING btree (message_id, created_at);


--
-- Name: chat_messages_legacy_message_id_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX chat_messages_legacy_message_id_created_at_idx ON public.chat_messages_legacy USING btree (message_id, created_at);


--
-- Name: idx_audit_log_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_created_at ON public.mastery_audit_log USING btree (created_at);


--
-- Name: idx_audit_log_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_node_id ON public.mastery_audit_log USING btree (node_id);


--
-- Name: idx_audit_log_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_user_id ON public.mastery_audit_log USING btree (user_id);


--
-- Name: idx_chat_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_created_at ON public.chat_messages_old USING btree (created_at);


--
-- Name: idx_chat_messages_session_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_messages_session_created ON public.chat_messages_old USING btree (session_id, created_at DESC);


--
-- Name: idx_chat_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_role ON public.chat_messages_old USING btree (role);


--
-- Name: idx_chat_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_session_id ON public.chat_messages_old USING btree (session_id);


--
-- Name: idx_chat_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_task_id ON public.chat_messages_old USING btree (task_id);


--
-- Name: idx_chat_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_user_id ON public.chat_messages_old USING btree (user_id);


--
-- Name: idx_claim_task; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_claim_task ON public.group_task_claims USING btree (group_task_id);


--
-- Name: idx_claim_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_claim_user ON public.group_task_claims USING btree (user_id);


--
-- Name: idx_cognitive_fragments_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cognitive_fragments_embedding_hnsw ON public.cognitive_fragments USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: idx_dict_word; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dict_word ON public.dictionary_entries USING btree (word);


--
-- Name: idx_errors_next_review; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_next_review ON public.error_records USING btree (user_id, next_review_at);


--
-- Name: idx_errors_question_fts; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_question_fts ON public.error_records USING gin (to_tsvector('simple'::regconfig, question_text));


--
-- Name: idx_errors_subject_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_subject_code ON public.error_records USING btree (subject_code);


--
-- Name: idx_errors_user_review; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_user_review ON public.error_records USING btree (user_id, next_review_at) WHERE (mastery_level < (1.0)::double precision);


--
-- Name: idx_errors_user_subject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_errors_user_subject ON public.error_records USING btree (user_id, subject_code);


--
-- Name: idx_event_store_aggregate; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_store_aggregate ON public.event_store USING btree (aggregate_type, aggregate_id, sequence_number);


--
-- Name: idx_event_store_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_store_type ON public.event_store USING btree (event_type, created_at);


--
-- Name: idx_focus_user_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_focus_user_time ON public.focus_sessions USING btree (user_id, start_time);


--
-- Name: idx_friendship_friend; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_friendship_friend ON public.friendships USING btree (friend_id);


--
-- Name: idx_friendship_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_friendship_status ON public.friendships USING btree (status);


--
-- Name: idx_friendship_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_friendship_user ON public.friendships USING btree (user_id);


--
-- Name: idx_group_messages_content_fts; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_messages_content_fts ON public.group_messages USING gin (to_tsvector('simple'::regconfig, COALESCE(content, ''::text))) WHERE (is_revoked = false);


--
-- Name: idx_group_public; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_public ON public.groups USING btree (is_public);


--
-- Name: idx_group_task_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_task_group ON public.group_tasks USING btree (group_id);


--
-- Name: idx_group_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_type ON public.groups USING btree (type);


--
-- Name: idx_idempotency_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_idempotency_expires ON public.idempotency_keys USING btree (expires_at);


--
-- Name: idx_jobs_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_jobs_status ON public.jobs USING btree (status);


--
-- Name: idx_jobs_status_timeout; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_jobs_status_timeout ON public.jobs USING btree (status, timeout_at) WHERE ((status)::text = 'running'::text);


--
-- Name: idx_jobs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_jobs_user_id ON public.jobs USING btree (user_id);


--
-- Name: idx_knowledge_nodes_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_knowledge_nodes_embedding_hnsw ON public.knowledge_nodes USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: idx_member_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_member_group ON public.group_members USING btree (group_id);


--
-- Name: idx_member_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_member_user ON public.group_members USING btree (user_id);


--
-- Name: idx_message_favorites_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_favorites_user ON public.message_favorites USING btree (user_id);


--
-- Name: idx_message_group_thread; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_group_thread ON public.group_messages USING btree (group_id, thread_root_id, created_at);


--
-- Name: idx_message_group_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_group_time ON public.group_messages USING btree (group_id, created_at);


--
-- Name: idx_message_reports_group_msg; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_reports_group_msg ON public.message_reports USING btree (group_message_id);


--
-- Name: idx_message_reports_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_reports_status ON public.message_reports USING btree (status);


--
-- Name: idx_message_topic; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_topic ON public.group_messages USING btree (group_id, topic);


--
-- Name: idx_nodes_keywords_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_nodes_keywords_gin ON public.knowledge_nodes USING gin (keywords);


--
-- Name: idx_nodes_position; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_nodes_position ON public.knowledge_nodes USING btree (position_x, position_y);


--
-- Name: idx_offline_queue_nonce; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_offline_queue_nonce ON public.offline_message_queue USING btree (user_id, client_nonce);


--
-- Name: idx_offline_queue_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_offline_queue_user_status ON public.offline_message_queue USING btree (user_id, status);


--
-- Name: idx_outbox_aggregate; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_outbox_aggregate ON public.event_outbox USING btree (aggregate_type, aggregate_id, sequence_number);


--
-- Name: idx_outbox_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_outbox_status ON public.outbox_events USING btree (status) WHERE ((status)::text = 'pending'::text);


--
-- Name: idx_outbox_unpublished; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_outbox_unpublished ON public.event_outbox USING btree (created_at) WHERE (published_at IS NULL);


--
-- Name: idx_plans_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_is_active ON public.plans USING btree (is_active);


--
-- Name: idx_plans_target_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_target_date ON public.plans USING btree (target_date);


--
-- Name: idx_plans_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_type ON public.plans USING btree (type);


--
-- Name: idx_plans_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_plans_user_id ON public.plans USING btree (user_id);


--
-- Name: idx_post_likes_post_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_post_likes_post_id ON public.post_likes USING btree (post_id);


--
-- Name: idx_posts_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_created_at ON public.posts USING btree (created_at);


--
-- Name: idx_posts_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_user_id ON public.posts USING btree (user_id);


--
-- Name: idx_posts_visibility_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_visibility_created ON public.posts USING btree (visibility, created_at DESC) WHERE ((visibility)::text = 'public'::text);


--
-- Name: idx_private_message_conversation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_private_message_conversation ON public.private_messages USING btree (sender_id, receiver_id, created_at);


--
-- Name: idx_private_message_receiver_unread; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_private_message_receiver_unread ON public.private_messages USING btree (receiver_id, is_read);


--
-- Name: idx_private_message_thread; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_private_message_thread ON public.private_messages USING btree (sender_id, receiver_id, thread_root_id, created_at);


--
-- Name: idx_private_messages_content_fts; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_private_messages_content_fts ON public.private_messages USING gin (to_tsvector('simple'::regconfig, COALESCE(content, ''::text))) WHERE (is_revoked = false);


--
-- Name: idx_processed_events_cleanup; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_processed_events_cleanup ON public.processed_events USING btree (processed_at);


--
-- Name: idx_processed_events_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_processed_events_group ON public.processed_events USING btree (consumer_group, processed_at);


--
-- Name: idx_share_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_group ON public.shared_resources USING btree (group_id);


--
-- Name: idx_share_resource_capsule; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_resource_capsule ON public.shared_resources USING btree (curiosity_capsule_id);


--
-- Name: idx_share_resource_pattern; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_resource_pattern ON public.shared_resources USING btree (behavior_pattern_id);


--
-- Name: idx_share_resource_plan; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_resource_plan ON public.shared_resources USING btree (plan_id);


--
-- Name: idx_share_target_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_target_user ON public.shared_resources USING btree (target_user_id);


--
-- Name: idx_snapshots_projection; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_snapshots_projection ON public.projection_snapshots USING btree (projection_name, created_at);


--
-- Name: idx_tasks_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_created_at ON public.tasks USING btree (created_at);


--
-- Name: idx_tasks_due_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_due_date ON public.tasks USING btree (due_date);


--
-- Name: idx_tasks_plan_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_plan_id ON public.tasks USING btree (plan_id);


--
-- Name: idx_tasks_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_status ON public.tasks USING btree (status);


--
-- Name: idx_tasks_tags_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_tags_gin ON public.tasks USING gin (tags);


--
-- Name: idx_tasks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_user_id ON public.tasks USING btree (user_id);


--
-- Name: idx_user_encryption_keys_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_encryption_keys_user ON public.user_encryption_keys USING btree (user_id, is_active);


--
-- Name: idx_user_tool_history_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_created_at ON public.user_tool_history USING btree (created_at);


--
-- Name: idx_user_tool_history_metrics; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_metrics ON public.user_tool_history USING btree (user_id, tool_name, success, created_at);


--
-- Name: idx_user_tool_history_success; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_success ON public.user_tool_history USING btree (user_id, tool_name, success);


--
-- Name: idx_user_tool_history_tool_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_tool_name ON public.user_tool_history USING btree (tool_name);


--
-- Name: idx_user_tool_history_user_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_user_created ON public.user_tool_history USING btree (user_id, created_at);


--
-- Name: idx_user_tool_history_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tool_history_user_id ON public.user_tool_history USING btree (user_id);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_username ON public.users USING btree (username);


--
-- Name: idx_wordbook_review; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_wordbook_review ON public.word_books USING btree (user_id, next_review_at);


--
-- Name: ix_agent_stats_agent_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_stats_agent_type ON public.agent_execution_stats USING btree (agent_type);


--
-- Name: ix_agent_stats_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_stats_created_at ON public.agent_execution_stats USING btree (created_at);


--
-- Name: ix_agent_stats_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_stats_session_id ON public.agent_execution_stats USING btree (session_id);


--
-- Name: ix_agent_stats_user_agent_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_stats_user_agent_type ON public.agent_execution_stats USING btree (user_id, agent_type);


--
-- Name: ix_agent_stats_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_stats_user_id ON public.agent_execution_stats USING btree (user_id);


--
-- Name: idx_suggestion_log_user_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_suggestion_log_user_created ON public.asset_suggestion_logs USING btree (user_id, created_at);


--
-- Name: idx_suggestion_log_policy; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_suggestion_log_policy ON public.asset_suggestion_logs USING btree (policy_id);


--
-- Name: ix_behavior_patterns_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_behavior_patterns_deleted_at ON public.behavior_patterns USING btree (deleted_at);


--
-- Name: ix_behavior_patterns_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_behavior_patterns_user_id ON public.behavior_patterns USING btree (user_id);


--
-- Name: ix_chat_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_messages_deleted_at ON public.chat_messages_old USING btree (deleted_at);


--
-- Name: ix_chat_messages_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_messages_session_id ON public.chat_messages_old USING btree (session_id);


--
-- Name: ix_chat_messages_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_messages_user_id ON public.chat_messages_old USING btree (user_id);


--
-- Name: ix_cognitive_fragments_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cognitive_fragments_deleted_at ON public.cognitive_fragments USING btree (deleted_at);


--
-- Name: ix_cognitive_fragments_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cognitive_fragments_user_id ON public.cognitive_fragments USING btree (user_id);


--
-- Name: ix_curiosity_capsules_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_curiosity_capsules_deleted_at ON public.curiosity_capsules USING btree (deleted_at);


--
-- Name: ix_curiosity_capsules_related_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_curiosity_capsules_related_task_id ON public.curiosity_capsules USING btree (related_task_id);


--
-- Name: ix_curiosity_capsules_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_curiosity_capsules_user_id ON public.curiosity_capsules USING btree (user_id);


--
-- Name: ix_dictionary_entries_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_dictionary_entries_deleted_at ON public.dictionary_entries USING btree (deleted_at);


--
-- Name: ix_dictionary_entries_word; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_dictionary_entries_word ON public.dictionary_entries USING btree (word);


--
-- Name: ix_focus_sessions_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_focus_sessions_deleted_at ON public.focus_sessions USING btree (deleted_at);


--
-- Name: ix_focus_sessions_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_focus_sessions_task_id ON public.focus_sessions USING btree (task_id);


--
-- Name: ix_focus_sessions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_focus_sessions_user_id ON public.focus_sessions USING btree (user_id);


--
-- Name: ix_friendships_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_friendships_deleted_at ON public.friendships USING btree (deleted_at);


--
-- Name: ix_friendships_friend_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_friendships_friend_id ON public.friendships USING btree (friend_id);


--
-- Name: ix_friendships_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_friendships_user_id ON public.friendships USING btree (user_id);


--
-- Name: ix_group_members_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_members_deleted_at ON public.group_members USING btree (deleted_at);


--
-- Name: ix_group_members_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_members_group_id ON public.group_members USING btree (group_id);


--
-- Name: ix_group_members_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_members_user_id ON public.group_members USING btree (user_id);


--
-- Name: ix_group_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_messages_deleted_at ON public.group_messages USING btree (deleted_at);


--
-- Name: ix_group_messages_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_messages_group_id ON public.group_messages USING btree (group_id);


--
-- Name: ix_group_task_claims_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_task_claims_deleted_at ON public.group_task_claims USING btree (deleted_at);


--
-- Name: ix_group_task_claims_group_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_task_claims_group_task_id ON public.group_task_claims USING btree (group_task_id);


--
-- Name: ix_group_task_claims_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_task_claims_user_id ON public.group_task_claims USING btree (user_id);


--
-- Name: ix_group_tasks_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_tasks_deleted_at ON public.group_tasks USING btree (deleted_at);


--
-- Name: ix_group_tasks_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_tasks_group_id ON public.group_tasks USING btree (group_id);


--
-- Name: ix_groups_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_groups_deleted_at ON public.groups USING btree (deleted_at);


--
-- Name: ix_idempotency_keys_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_idempotency_keys_expires_at ON public.idempotency_keys USING btree (expires_at);


--
-- Name: ix_idempotency_keys_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_idempotency_keys_user_id ON public.idempotency_keys USING btree (user_id);


--
-- Name: ix_jobs_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_jobs_deleted_at ON public.jobs USING btree (deleted_at);


--
-- Name: ix_jobs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_jobs_user_id ON public.jobs USING btree (user_id);


--
-- Name: ix_knowledge_nodes_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_deleted_at ON public.knowledge_nodes USING btree (deleted_at);


--
-- Name: ix_knowledge_nodes_parent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_parent_id ON public.knowledge_nodes USING btree (parent_id);


--
-- Name: ix_knowledge_nodes_subject_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_knowledge_nodes_subject_id ON public.knowledge_nodes USING btree (subject_id);


--
-- Name: idx_learning_assets_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_learning_assets_user_status ON public.learning_assets USING btree (user_id, status);


--
-- Name: idx_learning_assets_headword; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_learning_assets_headword ON public.learning_assets USING btree (headword);


--
-- Name: idx_learning_assets_selection_fp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_learning_assets_selection_fp ON public.learning_assets USING btree (user_id, selection_fp);


--
-- Name: idx_learning_assets_inbox_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_learning_assets_inbox_expires ON public.learning_assets USING btree (inbox_expires_at) WHERE (status = 'INBOX'::text);


--
-- Name: idx_learning_assets_review_due; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_learning_assets_review_due ON public.learning_assets USING btree (user_id, review_due_at) WHERE ((status = 'ACTIVE'::text) AND (review_due_at IS NOT NULL));


--
-- Name: idx_learning_assets_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_learning_assets_deleted_at ON public.learning_assets USING btree (deleted_at);


--
-- Name: ix_node_expansion_queue_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_expansion_queue_deleted_at ON public.node_expansion_queue USING btree (deleted_at);


--
-- Name: ix_node_expansion_queue_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_expansion_queue_status ON public.node_expansion_queue USING btree (status);


--
-- Name: ix_node_expansion_queue_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_expansion_queue_user_id ON public.node_expansion_queue USING btree (user_id);


--
-- Name: ix_node_relations_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_relations_deleted_at ON public.node_relations USING btree (deleted_at);


--
-- Name: ix_node_relations_source_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_relations_source_node_id ON public.node_relations USING btree (source_node_id);


--
-- Name: ix_node_relations_target_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_node_relations_target_node_id ON public.node_relations USING btree (target_node_id);


--
-- Name: ix_notifications_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notifications_deleted_at ON public.notifications USING btree (deleted_at);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_plans_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_deleted_at ON public.plans USING btree (deleted_at);


--
-- Name: ix_plans_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_is_active ON public.plans USING btree (is_active);


--
-- Name: ix_plans_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_plans_user_id ON public.plans USING btree (user_id);


--
-- Name: ix_private_messages_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_private_messages_deleted_at ON public.private_messages USING btree (deleted_at);


--
-- Name: ix_private_messages_receiver_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_private_messages_receiver_id ON public.private_messages USING btree (receiver_id);


--
-- Name: ix_private_messages_sender_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_private_messages_sender_id ON public.private_messages USING btree (sender_id);


--
-- Name: ix_push_histories_content_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_push_histories_content_hash ON public.push_histories USING btree (content_hash);


--
-- Name: ix_push_histories_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_push_histories_deleted_at ON public.push_histories USING btree (deleted_at);


--
-- Name: ix_push_histories_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_push_histories_user_id ON public.push_histories USING btree (user_id);


--
-- Name: ix_push_preferences_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_push_preferences_deleted_at ON public.push_preferences USING btree (deleted_at);


--
-- Name: ix_push_preferences_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_push_preferences_user_id ON public.push_preferences USING btree (user_id);


--
-- Name: ix_shared_resources_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shared_resources_deleted_at ON public.shared_resources USING btree (deleted_at);


--
-- Name: ix_shared_resources_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shared_resources_group_id ON public.shared_resources USING btree (group_id);


--
-- Name: ix_shared_resources_target_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shared_resources_target_user_id ON public.shared_resources USING btree (target_user_id);


--
-- Name: ix_study_records_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_study_records_deleted_at ON public.study_records USING btree (deleted_at);


--
-- Name: ix_study_records_node_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_study_records_node_id ON public.study_records USING btree (node_id);


--
-- Name: ix_study_records_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_study_records_user_id ON public.study_records USING btree (user_id);


--
-- Name: ix_subjects_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subjects_category ON public.subjects USING btree (category);


--
-- Name: ix_subjects_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subjects_is_active ON public.subjects USING btree (is_active);


--
-- Name: ix_subjects_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_subjects_name ON public.subjects USING btree (name);


--
-- Name: ix_tasks_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_deleted_at ON public.tasks USING btree (deleted_at);


--
-- Name: ix_tasks_plan_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_plan_id ON public.tasks USING btree (plan_id);


--
-- Name: ix_tasks_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_status ON public.tasks USING btree (status);


--
-- Name: ix_tasks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_user_id ON public.tasks USING btree (user_id);


--
-- Name: ix_user_daily_metrics_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_daily_metrics_date ON public.user_daily_metrics USING btree (date);


--
-- Name: ix_user_daily_metrics_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_daily_metrics_deleted_at ON public.user_daily_metrics USING btree (deleted_at);


--
-- Name: ix_user_daily_metrics_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_daily_metrics_user_id ON public.user_daily_metrics USING btree (user_id);


--
-- Name: ix_user_node_status_next_review_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_node_status_next_review_at ON public.user_node_status USING btree (next_review_at);


--
-- Name: ix_users_apple_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_apple_id ON public.users USING btree (apple_id);


--
-- Name: ix_users_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_deleted_at ON public.users USING btree (deleted_at);


--
-- Name: ix_users_google_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_google_id ON public.users USING btree (google_id);


--
-- Name: ix_users_wechat_unionid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_wechat_unionid ON public.users USING btree (wechat_unionid);


--
-- Name: ix_word_books_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_word_books_deleted_at ON public.word_books USING btree (deleted_at);


--
-- Name: ix_word_books_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_word_books_user_id ON public.word_books USING btree (user_id);


--
-- Name: ix_word_books_word; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_word_books_word ON public.word_books USING btree (word);


--
-- Name: chat_messages_2024_q1_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_2024_q1_message_id_created_at_idx;


--
-- Name: chat_messages_2024_q1_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_2024_q1_pkey;


--
-- Name: chat_messages_2024_q2_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_2024_q2_message_id_created_at_idx;


--
-- Name: chat_messages_2024_q2_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_2024_q2_pkey;


--
-- Name: chat_messages_2024_q3_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_2024_q3_message_id_created_at_idx;


--
-- Name: chat_messages_2024_q3_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_2024_q3_pkey;


--
-- Name: chat_messages_2024_q4_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_2024_q4_message_id_created_at_idx;


--
-- Name: chat_messages_2024_q4_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_2024_q4_pkey;


--
-- Name: chat_messages_2025_q1_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_2025_q1_message_id_created_at_idx;


--
-- Name: chat_messages_2025_q1_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_2025_q1_pkey;


--
-- Name: chat_messages_2025_q2_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_2025_q2_message_id_created_at_idx;


--
-- Name: chat_messages_2025_q2_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_2025_q2_pkey;


--
-- Name: chat_messages_2025_q3_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_2025_q3_message_id_created_at_idx;


--
-- Name: chat_messages_2025_q3_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_2025_q3_pkey;


--
-- Name: chat_messages_2025_q4_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_2025_q4_message_id_created_at_idx;


--
-- Name: chat_messages_2025_q4_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_2025_q4_pkey;


--
-- Name: chat_messages_2026_q1_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_2026_q1_message_id_created_at_idx;


--
-- Name: chat_messages_2026_q1_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_2026_q1_pkey;


--
-- Name: chat_messages_2026_q2_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_2026_q2_message_id_created_at_idx;


--
-- Name: chat_messages_2026_q2_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_2026_q2_pkey;


--
-- Name: chat_messages_default_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_default_message_id_created_at_idx;


--
-- Name: chat_messages_default_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_default_pkey;


--
-- Name: chat_messages_legacy_message_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_message_id_created_at_key ATTACH PARTITION public.chat_messages_legacy_message_id_created_at_idx;


--
-- Name: chat_messages_legacy_pkey; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.chat_messages_partitioned_pkey ATTACH PARTITION public.chat_messages_legacy_pkey;


--
-- Name: asset_suggestion_logs asset_suggestion_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_suggestion_logs
    ADD CONSTRAINT asset_suggestion_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: asset_suggestion_logs asset_suggestion_logs_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_suggestion_logs
    ADD CONSTRAINT asset_suggestion_logs_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.learning_assets(id) ON DELETE SET NULL;


--
-- Name: behavior_patterns behavior_patterns_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.behavior_patterns
    ADD CONSTRAINT behavior_patterns_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: broadcast_messages broadcast_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.broadcast_messages
    ADD CONSTRAINT broadcast_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.chat_messages
    ADD CONSTRAINT chat_messages_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: chat_messages_old chat_messages_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_old
    ADD CONSTRAINT chat_messages_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: chat_messages chat_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.chat_messages
    ADD CONSTRAINT chat_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: chat_messages_old chat_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages_old
    ADD CONSTRAINT chat_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: cognitive_fragments cognitive_fragments_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cognitive_fragments
    ADD CONSTRAINT cognitive_fragments_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: cognitive_fragments cognitive_fragments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cognitive_fragments
    ADD CONSTRAINT cognitive_fragments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: curiosity_capsules curiosity_capsules_related_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.curiosity_capsules
    ADD CONSTRAINT curiosity_capsules_related_task_id_fkey FOREIGN KEY (related_task_id) REFERENCES public.tasks(id);


--
-- Name: curiosity_capsules curiosity_capsules_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.curiosity_capsules
    ADD CONSTRAINT curiosity_capsules_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: error_records error_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.error_records
    ADD CONSTRAINT error_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: focus_sessions focus_sessions_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.focus_sessions
    ADD CONSTRAINT focus_sessions_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: focus_sessions focus_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.focus_sessions
    ADD CONSTRAINT focus_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: friendships friendships_friend_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.friendships
    ADD CONSTRAINT friendships_friend_id_fkey FOREIGN KEY (friend_id) REFERENCES public.users(id);


--
-- Name: friendships friendships_initiated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.friendships
    ADD CONSTRAINT friendships_initiated_by_fkey FOREIGN KEY (initiated_by) REFERENCES public.users(id);


--
-- Name: friendships friendships_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.friendships
    ADD CONSTRAINT friendships_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: group_members group_members_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: group_members group_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: group_messages group_messages_forwarded_from_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_forwarded_from_id_fkey FOREIGN KEY (forwarded_from_id) REFERENCES public.group_messages(id);


--
-- Name: group_messages group_messages_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: group_messages group_messages_reply_to_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_reply_to_id_fkey FOREIGN KEY (reply_to_id) REFERENCES public.group_messages(id);


--
-- Name: group_messages group_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);


--
-- Name: group_messages group_messages_thread_root_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_messages
    ADD CONSTRAINT group_messages_thread_root_id_fkey FOREIGN KEY (thread_root_id) REFERENCES public.group_messages(id);


--
-- Name: group_task_claims group_task_claims_group_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_task_claims
    ADD CONSTRAINT group_task_claims_group_task_id_fkey FOREIGN KEY (group_task_id) REFERENCES public.group_tasks(id) ON DELETE CASCADE;


--
-- Name: group_task_claims group_task_claims_personal_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_task_claims
    ADD CONSTRAINT group_task_claims_personal_task_id_fkey FOREIGN KEY (personal_task_id) REFERENCES public.tasks(id);


--
-- Name: group_task_claims group_task_claims_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_task_claims
    ADD CONSTRAINT group_task_claims_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: group_tasks group_tasks_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_tasks
    ADD CONSTRAINT group_tasks_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: group_tasks group_tasks_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_tasks
    ADD CONSTRAINT group_tasks_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: idempotency_keys idempotency_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: jobs jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: knowledge_nodes knowledge_nodes_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.knowledge_nodes
    ADD CONSTRAINT knowledge_nodes_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.knowledge_nodes(id);


--
-- Name: knowledge_nodes knowledge_nodes_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.knowledge_nodes
    ADD CONSTRAINT knowledge_nodes_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id);


--
-- Name: learning_assets learning_assets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learning_assets
    ADD CONSTRAINT learning_assets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: learning_assets learning_assets_source_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.learning_assets
    ADD CONSTRAINT learning_assets_source_file_id_fkey FOREIGN KEY (source_file_id) REFERENCES public.stored_files(id) ON DELETE SET NULL;


--
-- Name: mastery_audit_log mastery_audit_log_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mastery_audit_log
    ADD CONSTRAINT mastery_audit_log_node_id_fkey FOREIGN KEY (node_id) REFERENCES public.knowledge_nodes(id);


--
-- Name: mastery_audit_log mastery_audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mastery_audit_log
    ADD CONSTRAINT mastery_audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: message_favorites message_favorites_group_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_favorites
    ADD CONSTRAINT message_favorites_group_message_id_fkey FOREIGN KEY (group_message_id) REFERENCES public.group_messages(id) ON DELETE CASCADE;


--
-- Name: message_favorites message_favorites_private_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_favorites
    ADD CONSTRAINT message_favorites_private_message_id_fkey FOREIGN KEY (private_message_id) REFERENCES public.private_messages(id) ON DELETE CASCADE;


--
-- Name: message_favorites message_favorites_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_favorites
    ADD CONSTRAINT message_favorites_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: message_reports message_reports_group_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_reports
    ADD CONSTRAINT message_reports_group_message_id_fkey FOREIGN KEY (group_message_id) REFERENCES public.group_messages(id) ON DELETE SET NULL;


--
-- Name: message_reports message_reports_private_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_reports
    ADD CONSTRAINT message_reports_private_message_id_fkey FOREIGN KEY (private_message_id) REFERENCES public.private_messages(id) ON DELETE SET NULL;


--
-- Name: message_reports message_reports_reporter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_reports
    ADD CONSTRAINT message_reports_reporter_id_fkey FOREIGN KEY (reporter_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: message_reports message_reports_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_reports
    ADD CONSTRAINT message_reports_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: node_expansion_queue node_expansion_queue_trigger_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_trigger_node_id_fkey FOREIGN KEY (trigger_node_id) REFERENCES public.knowledge_nodes(id);


--
-- Name: node_expansion_queue node_expansion_queue_trigger_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_trigger_task_id_fkey FOREIGN KEY (trigger_task_id) REFERENCES public.tasks(id);


--
-- Name: node_expansion_queue node_expansion_queue_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.node_expansion_queue
    ADD CONSTRAINT node_expansion_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: node_relations node_relations_source_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.node_relations
    ADD CONSTRAINT node_relations_source_node_id_fkey FOREIGN KEY (source_node_id) REFERENCES public.knowledge_nodes(id);


--
-- Name: node_relations node_relations_target_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.node_relations
    ADD CONSTRAINT node_relations_target_node_id_fkey FOREIGN KEY (target_node_id) REFERENCES public.knowledge_nodes(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: offline_message_queue offline_message_queue_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.offline_message_queue
    ADD CONSTRAINT offline_message_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: plans plans_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.plans
    ADD CONSTRAINT plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: post_likes post_likes_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_likes
    ADD CONSTRAINT post_likes_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.posts(id) ON DELETE CASCADE;


--
-- Name: post_likes post_likes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_likes
    ADD CONSTRAINT post_likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: posts posts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: private_messages private_messages_forwarded_from_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_forwarded_from_id_fkey FOREIGN KEY (forwarded_from_id) REFERENCES public.private_messages(id);


--
-- Name: private_messages private_messages_receiver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_receiver_id_fkey FOREIGN KEY (receiver_id) REFERENCES public.users(id);


--
-- Name: private_messages private_messages_reply_to_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_reply_to_id_fkey FOREIGN KEY (reply_to_id) REFERENCES public.private_messages(id);


--
-- Name: private_messages private_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);


--
-- Name: private_messages private_messages_thread_root_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_thread_root_id_fkey FOREIGN KEY (thread_root_id) REFERENCES public.private_messages(id);


--
-- Name: push_histories push_histories_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.push_histories
    ADD CONSTRAINT push_histories_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: push_preferences push_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.push_preferences
    ADD CONSTRAINT push_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: shared_resources shared_resources_behavior_pattern_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_behavior_pattern_id_fkey FOREIGN KEY (behavior_pattern_id) REFERENCES public.behavior_patterns(id);


--
-- Name: shared_resources shared_resources_cognitive_fragment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_cognitive_fragment_id_fkey FOREIGN KEY (cognitive_fragment_id) REFERENCES public.cognitive_fragments(id);


--
-- Name: shared_resources shared_resources_curiosity_capsule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_curiosity_capsule_id_fkey FOREIGN KEY (curiosity_capsule_id) REFERENCES public.curiosity_capsules(id);


--
-- Name: shared_resources shared_resources_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: shared_resources shared_resources_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(id);


--
-- Name: shared_resources shared_resources_shared_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_shared_by_fkey FOREIGN KEY (shared_by) REFERENCES public.users(id);


--
-- Name: shared_resources shared_resources_target_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_target_user_id_fkey FOREIGN KEY (target_user_id) REFERENCES public.users(id);


--
-- Name: shared_resources shared_resources_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: study_records study_records_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.study_records
    ADD CONSTRAINT study_records_node_id_fkey FOREIGN KEY (node_id) REFERENCES public.knowledge_nodes(id);


--
-- Name: study_records study_records_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.study_records
    ADD CONSTRAINT study_records_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: study_records study_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.study_records
    ADD CONSTRAINT study_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: tasks tasks_knowledge_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_knowledge_node_id_fkey FOREIGN KEY (knowledge_node_id) REFERENCES public.knowledge_nodes(id);


--
-- Name: tasks tasks_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(id);


--
-- Name: tasks tasks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_daily_metrics user_daily_metrics_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_daily_metrics
    ADD CONSTRAINT user_daily_metrics_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_encryption_keys user_encryption_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_encryption_keys
    ADD CONSTRAINT user_encryption_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_node_status user_node_status_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_node_status
    ADD CONSTRAINT user_node_status_node_id_fkey FOREIGN KEY (node_id) REFERENCES public.knowledge_nodes(id);


--
-- Name: user_node_status user_node_status_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_node_status
    ADD CONSTRAINT user_node_status_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_tool_history user_tool_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_tool_history
    ADD CONSTRAINT user_tool_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: word_books word_books_source_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.word_books
    ADD CONSTRAINT word_books_source_task_id_fkey FOREIGN KEY (source_task_id) REFERENCES public.tasks(id);


--
-- Name: word_books word_books_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.word_books
    ADD CONSTRAINT word_books_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: stored_files; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stored_files (
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
    CONSTRAINT stored_files_pkey PRIMARY KEY (id)
);


ALTER TABLE public.stored_files OWNER TO postgres;


--
-- Name: idx_stored_files_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_stored_files_created_at ON public.stored_files USING btree (created_at);


--
-- Name: idx_stored_files_object_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_stored_files_object_key ON public.stored_files USING btree (object_key);


--
-- Name: idx_stored_files_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_stored_files_status ON public.stored_files USING btree (status);


--
-- Name: idx_stored_files_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_stored_files_user_id ON public.stored_files USING btree (user_id);


--
-- Name: stored_files stored_files_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stored_files
    ADD CONSTRAINT stored_files_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: group_files; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_files (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    group_id uuid NOT NULL,
    file_id uuid NOT NULL,
    shared_by_id uuid NOT NULL,
    category character varying(64),
    tags json NOT NULL,
    view_role public.grouprole NOT NULL,
    download_role public.grouprole NOT NULL,
    manage_role public.grouprole NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    deleted_at timestamp without time zone,
    CONSTRAINT group_files_pkey PRIMARY KEY (id),
    CONSTRAINT uq_group_files_group_file UNIQUE (group_id, file_id)
);


ALTER TABLE public.group_files OWNER TO postgres;


--
-- Name: idx_group_files_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_files_category ON public.group_files USING btree (category);


--
-- Name: idx_group_files_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_files_deleted_at ON public.group_files USING btree (deleted_at);


--
-- Name: idx_group_files_file; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_files_file ON public.group_files USING btree (file_id);


--
-- Name: idx_group_files_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_files_group ON public.group_files USING btree (group_id);


--
-- Name: idx_group_files_shared_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_files_shared_by ON public.group_files USING btree (shared_by_id);


--
-- Name: group_files group_files_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_files
    ADD CONSTRAINT group_files_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.stored_files(id) ON DELETE CASCADE;


--
-- Name: group_files group_files_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_files
    ADD CONSTRAINT group_files_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: group_files group_files_shared_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_files
    ADD CONSTRAINT group_files_shared_by_id_fkey FOREIGN KEY (shared_by_id) REFERENCES public.users(id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


--
-- PostgreSQL database dump complete
--
