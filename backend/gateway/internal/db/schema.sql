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
    'SYSTEM'
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
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

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
);


ALTER TABLE public.chat_messages OWNER TO postgres;

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
    user_id uuid NOT NULL,
    task_id uuid,
    subject_id integer,
    subject character varying(100) NOT NULL,
    topic character varying(255) NOT NULL,
    error_type character varying(100) NOT NULL,
    description text NOT NULL,
    correct_approach text,
    image_urls json,
    frequency integer NOT NULL,
    last_occurred_at timestamp without time zone NOT NULL,
    is_resolved boolean NOT NULL,
    resolved_at timestamp without time zone,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.error_records OWNER TO postgres;

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
    deleted_at timestamp without time zone
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
    deleted_at timestamp without time zone
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
    deleted_at timestamp without time zone
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
    keywords json,
    importance_level integer NOT NULL,
    is_seed boolean,
    source_type character varying(20),
    source_task_id uuid,
    embedding public.vector(1536),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.knowledge_nodes OWNER TO postgres;

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
    deleted_at timestamp without time zone
);


ALTER TABLE public.private_messages OWNER TO postgres;

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
    deleted_at timestamp without time zone
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
    deleted_at timestamp without time zone
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
    tags json NOT NULL,
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
-- Name: subjects id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjects ALTER COLUMN id SET DEFAULT nextval('public.subjects_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: behavior_patterns behavior_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.behavior_patterns
    ADD CONSTRAINT behavior_patterns_pkey PRIMARY KEY (id);


--
-- Name: chat_messages chat_messages_message_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_message_id_key UNIQUE (message_id);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
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
-- Name: plans plans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.plans
    ADD CONSTRAINT plans_pkey PRIMARY KEY (id);


--
-- Name: private_messages private_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.private_messages
    ADD CONSTRAINT private_messages_pkey PRIMARY KEY (id);


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
-- Name: user_node_status user_node_status_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_node_status
    ADD CONSTRAINT user_node_status_pkey PRIMARY KEY (user_id, node_id);


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
-- Name: idx_chat_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_created_at ON public.chat_messages USING btree (created_at);


--
-- Name: idx_chat_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_role ON public.chat_messages USING btree (role);


--
-- Name: idx_chat_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_session_id ON public.chat_messages USING btree (session_id);


--
-- Name: idx_chat_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_task_id ON public.chat_messages USING btree (task_id);


--
-- Name: idx_chat_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_user_id ON public.chat_messages USING btree (user_id);


--
-- Name: idx_claim_task; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_claim_task ON public.group_task_claims USING btree (group_task_id);


--
-- Name: idx_claim_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_claim_user ON public.group_task_claims USING btree (user_id);


--
-- Name: idx_dict_word; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dict_word ON public.dictionary_entries USING btree (word);


--
-- Name: idx_error_is_resolved; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_is_resolved ON public.error_records USING btree (is_resolved);


--
-- Name: idx_error_last_occurred; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_last_occurred ON public.error_records USING btree (last_occurred_at);


--
-- Name: idx_error_subject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_subject ON public.error_records USING btree (subject);


--
-- Name: idx_error_subject_topic; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_subject_topic ON public.error_records USING btree (subject, topic);


--
-- Name: idx_error_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_task_id ON public.error_records USING btree (task_id);


--
-- Name: idx_error_topic; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_topic ON public.error_records USING btree (topic);


--
-- Name: idx_error_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_user_id ON public.error_records USING btree (user_id);


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
-- Name: idx_member_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_member_group ON public.group_members USING btree (group_id);


--
-- Name: idx_member_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_member_user ON public.group_members USING btree (user_id);


--
-- Name: idx_message_group_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_group_time ON public.group_messages USING btree (group_id, created_at);


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
-- Name: idx_private_message_conversation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_private_message_conversation ON public.private_messages USING btree (sender_id, receiver_id, created_at);


--
-- Name: idx_private_message_receiver_unread; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_private_message_receiver_unread ON public.private_messages USING btree (receiver_id, is_read);


--
-- Name: idx_share_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_group ON public.shared_resources USING btree (group_id);


--
-- Name: idx_share_resource_plan; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_resource_plan ON public.shared_resources USING btree (plan_id);


--
-- Name: idx_share_target_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_share_target_user ON public.shared_resources USING btree (target_user_id);


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
-- Name: idx_tasks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_user_id ON public.tasks USING btree (user_id);


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

CREATE INDEX ix_chat_messages_deleted_at ON public.chat_messages USING btree (deleted_at);


--
-- Name: ix_chat_messages_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_messages_session_id ON public.chat_messages USING btree (session_id);


--
-- Name: ix_chat_messages_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chat_messages_user_id ON public.chat_messages USING btree (user_id);


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
-- Name: ix_error_records_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_error_records_deleted_at ON public.error_records USING btree (deleted_at);


--
-- Name: ix_error_records_is_resolved; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_error_records_is_resolved ON public.error_records USING btree (is_resolved);


--
-- Name: ix_error_records_subject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_error_records_subject ON public.error_records USING btree (subject);


--
-- Name: ix_error_records_topic; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_error_records_topic ON public.error_records USING btree (topic);


--
-- Name: ix_error_records_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_error_records_user_id ON public.error_records USING btree (user_id);


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
-- Name: behavior_patterns behavior_patterns_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.behavior_patterns
    ADD CONSTRAINT behavior_patterns_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: chat_messages chat_messages_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: chat_messages chat_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
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
-- Name: error_records error_records_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.error_records
    ADD CONSTRAINT error_records_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id);


--
-- Name: error_records error_records_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.error_records
    ADD CONSTRAINT error_records_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: error_records error_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.error_records
    ADD CONSTRAINT error_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


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
-- Name: plans plans_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.plans
    ADD CONSTRAINT plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


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
-- Name: shared_resources shared_resources_cognitive_fragment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_resources
    ADD CONSTRAINT shared_resources_cognitive_fragment_id_fkey FOREIGN KEY (cognitive_fragment_id) REFERENCES public.cognitive_fragments(id);


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
-- PostgreSQL database dump complete
--




--
-- Community Module Tables
--

CREATE TABLE public.posts (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    content text NOT NULL,
    image_urls json,
    topic character varying(100),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    deleted_at timestamp without time zone
);

ALTER TABLE public.posts OWNER TO postgres;

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

CREATE INDEX idx_posts_user_id ON public.posts USING btree (user_id);
CREATE INDEX idx_posts_created_at ON public.posts USING btree (created_at);

CREATE TABLE public.post_likes (
    user_id uuid NOT NULL,
    post_id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.post_likes OWNER TO postgres;

ALTER TABLE ONLY public.post_likes
    ADD CONSTRAINT post_likes_pkey PRIMARY KEY (user_id, post_id);

ALTER TABLE ONLY public.post_likes
    ADD CONSTRAINT post_likes_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.posts(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.post_likes
    ADD CONSTRAINT post_likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

CREATE INDEX idx_post_likes_post_id ON public.post_likes USING btree (post_id);

--
-- CQRS Infrastructure Tables
--

-- 1. Outbox table (transactional event publishing)
CREATE TABLE public.event_outbox (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type character varying(100) NOT NULL,
    aggregate_id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    event_version integer NOT NULL DEFAULT 1,
    payload jsonb NOT NULL,
    metadata jsonb,
    sequence_number bigserial,
    created_at timestamp without time zone NOT NULL DEFAULT NOW(),
    published_at timestamp without time zone,

    CONSTRAINT unique_aggregate_sequence
        UNIQUE (aggregate_type, aggregate_id, sequence_number)
);

ALTER TABLE public.event_outbox OWNER TO postgres;

CREATE INDEX idx_outbox_unpublished ON public.event_outbox (created_at)
    WHERE published_at IS NULL;

-- 2. Event Store (complete event history)
CREATE TABLE public.event_store (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type character varying(100) NOT NULL,
    aggregate_id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    event_version integer NOT NULL,
    sequence_number bigint NOT NULL,
    payload jsonb NOT NULL,
    metadata jsonb,
    created_at timestamp without time zone NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_event
        UNIQUE (aggregate_type, aggregate_id, sequence_number)
);

ALTER TABLE public.event_store OWNER TO postgres;

CREATE INDEX idx_event_store_aggregate
    ON public.event_store (aggregate_type, aggregate_id, sequence_number);
CREATE INDEX idx_event_store_type ON public.event_store (event_type, created_at);

-- 3. Idempotency tracking
CREATE TABLE public.processed_events (
    event_id character varying(100) PRIMARY KEY,
    consumer_group character varying(100) NOT NULL,
    processed_at timestamp without time zone NOT NULL DEFAULT NOW()
);

ALTER TABLE public.processed_events OWNER TO postgres;

CREATE INDEX idx_processed_events_cleanup ON public.processed_events (processed_at);

-- 4. Projection metadata
CREATE TABLE public.projection_metadata (
    projection_name character varying(100) PRIMARY KEY,
    last_processed_position character varying(100),
    last_processed_at timestamp without time zone,
    version integer NOT NULL DEFAULT 1,
    status character varying(20) NOT NULL DEFAULT 'active',
    error_message text,
    created_at timestamp without time zone NOT NULL DEFAULT NOW(),
    updated_at timestamp without time zone NOT NULL DEFAULT NOW()
);

ALTER TABLE public.projection_metadata OWNER TO postgres;

-- 5. Projection snapshots
CREATE TABLE public.projection_snapshots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    projection_name character varying(100) NOT NULL,
    aggregate_id uuid,
    snapshot_data jsonb NOT NULL,
    stream_position character varying(100) NOT NULL,
    created_at timestamp without time zone NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_snapshot UNIQUE (projection_name, aggregate_id)
);

ALTER TABLE public.projection_snapshots OWNER TO postgres;
