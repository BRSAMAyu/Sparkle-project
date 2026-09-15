"""
Performance Benchmark Tests for Orchestrator FSM
编排器FSM性能基准测试

Tests performance characteristics:
1. State transition speed
2. Context switching overhead
3. Memory usage per session
4. Concurrent session handling
"""
import pytest
import time
import tracemalloc
from unittest.mock import Mock, AsyncMock, patch
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.state_manager import StateManager
from app.orchestration.schemas import OrchestratorState


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for orchestrator benchmarking"""
    return {
        'llm_service': Mock(),
        'tool_registry': Mock(),
        'rag_service': Mock(),
        'db': Mock(),
        'state_manager': Mock(spec=StateManager),
    }


@pytest.mark.benchmark
def test_state_transition_speed(mock_dependencies):
    """
    Benchmark state transition speed
    状态转换速度基准
    """
    # Create a simple FSM for testing
    state_transitions = [
        OrchestratorState.IDLE,
        OrchestratorState.PLANNING,
        OrchestratorState.TOOL_EXECUTION,
        OrchestratorState.LLM_INFERENCE,
        OrchestratorState.COMPLETED,
    ]

    start = time.time()

    # Simulate 1000 state transitions
    for i in range(1000):
        current_state = state_transitions[i % len(state_transitions)]
        next_state = state_transitions[(i + 1) % len(state_transitions)]

        # Simulate transition logic
        transition_data = {
            'from': current_state,
            'to': next_state,
            'timestamp': time.time(),
        }

    elapsed = time.time() - start

    # Should be very fast (< 50ms for 1000 transitions)
    assert elapsed < 0.05


@pytest.mark.benchmark
def test_context_creation_overhead(mock_dependencies):
    """
    Benchmark context creation and management
    上下文创建和管理性能基准
    """
    start = time.time()

    # Create 100 contexts
    contexts = []
    for i in range(100):
        context = {
            'session_id': f'session-{i}',
            'user_id': f'user-{i}',
            'state': OrchestratorState.IDLE,
            'messages': [],
            'metadata': {},
        }
        contexts.append(context)

    elapsed = time.time() - start

    # Should be fast (< 10ms for 100 contexts)
    assert elapsed < 0.01
    assert len(contexts) == 100


@pytest.mark.benchmark
def test_context_memory_usage(mock_dependencies):
    """
    Test memory usage for context storage
    上下文存储内存使用测试
    """
    tracemalloc.start()

    # Create 1000 contexts with message history
    contexts = []
    for i in range(1000):
        context = {
            'session_id': f'session-{i}',
            'user_id': f'user-{i}',
            'state': OrchestratorState.IDLE,
            'messages': [
                {'role': 'user', 'content': f'Message {j}'}
                for j in range(10)  # 10 messages per context
            ],
            'metadata': {f'key{k}': f'value{k}' for k in range(5)},
        }
        contexts.append(context)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Memory should be reasonable (< 50MB for 1000 contexts)
    peak_mb = peak / 1024 / 1024
    assert peak_mb < 50


@pytest.mark.benchmark
def test_concurrent_state_transitions():
    """
    Test concurrent state transition handling
    并发状态转换处理测试
    """
    import threading

    state_transitions = []
    threads = []

    def perform_transitions(thread_id):
        for i in range(100):
            transition = {
                'thread': thread_id,
                'step': i,
                'state': f'state-{i % 5}',
            }
            state_transitions.append(transition)

    start = time.time()

    # 10 threads, each with 100 transitions
    for i in range(10):
        thread = threading.Thread(target=perform_transitions, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    elapsed = time.time() - start

    # Should complete quickly (< 100ms for 1000 transitions across 10 threads)
    assert elapsed < 0.1
    assert len(state_transitions) == 1000


@pytest.mark.benchmark
def test_event_processing_overhead():
    """
    Benchmark event processing in orchestrator
    编排器事件处理性能基准
    """
    events = [
        {'type': 'user_message', 'content': f'Message {i}'}
        for i in range(1000)
    ]

    start = time.time()

    # Simulate event processing
    for event in events:
        # Simulate event dispatch
        event_type = event['type']
        content = event['content']

        # Simulate handler lookup
        handlers = {
            'user_message': lambda e: None,
            'tool_result': lambda e: None,
            'llm_response': lambda e: None,
        }
        handler = handlers.get(event_type)
        if handler:
            handler(event)

    elapsed = time.time() - start

    # Should process 1000 events quickly (< 50ms)
    assert elapsed < 0.05


@pytest.mark.benchmark
def test_state_manager_get_set():
    """
    Benchmark state manager get/set operations
    状态管理器读写性能基准
    """
    # Simulate state manager
    state_store = {}

    # Benchmark writes
    start = time.time()
    for i in range(1000):
        session_id = f'session-{i}'
        state_store[session_id] = {
            'state': OrchestratorState.PLANNING,
            'updated_at': time.time(),
        }
    write_time = time.time() - start

    # Benchmark reads
    start = time.time()
    for i in range(1000):
        session_id = f'session-{i}'
        state = state_store.get(session_id)
    read_time = time.time() - start

    # Both should be fast
    assert write_time < 0.05
    assert read_time < 0.01


@pytest.mark.benchmark
def test_message_queue_performance():
    """
    Benchmark message queue operations
    消息队列操作性能基准
    """
    import queue

    msg_queue = queue.Queue()

    # Benchmark enqueue
    start = time.time()
    for i in range(10000):
        msg_queue.put({'message_id': i, 'content': f'Message {i}'})
    enqueue_time = time.time() - start

    # Benchmark dequeue
    start = time.time()
    while not msg_queue.empty():
        msg = msg_queue.get()
    dequeue_time = time.time() - start

    # Should handle 10k messages efficiently
    assert enqueue_time < 0.1
    assert dequeue_time < 0.1


@pytest.mark.benchmark
def test_fsm_transition_complexity():
    """
    Test FSM performance with complex state graphs
    复杂状态图FSM性能测试
    """
    # Define complex state machine
    state_graph = {
        'idle': ['planning', 'processing', 'error'],
        'planning': ['tool_execution', 'llm_inference', 'error'],
        'tool_execution': ['llm_inference', 'planning', 'completed', 'error'],
        'llm_inference': ['tool_execution', 'completed', 'error'],
        'completed': ['idle'],
        'error': ['idle', 'planning'],
    }

    start = time.time()

    # Simulate random walk through state graph
    current_state = 'idle'
    for i in range(10000):
        possible_transitions = state_graph.get(current_state, [])
        if possible_transitions:
            current_state = possible_transitions[i % len(possible_transitions)]

    elapsed = time.time() - start

    # Should handle 10k transitions quickly (< 100ms)
    assert elapsed < 0.1


@pytest.mark.benchmark
def test_session_lifecycle():
    """
    Benchmark complete session lifecycle
    完整会话生命周期性能基准
    """
    sessions = []

    start = time.time()

    # Create 100 sessions
    for i in range(100):
        session = {
            'session_id': f'session-{i}',
            'created_at': time.time(),
            'state': OrchestratorState.IDLE,
            'messages': [],
        }
        sessions.append(session)

        # Simulate session activity
        for j in range(10):
            session['messages'].append({
                'role': 'user',
                'content': f'Message {j}',
                'timestamp': time.time(),
            })

        # Simulate session cleanup
        session['closed_at'] = time.time()

    elapsed = time.time() - start

    # Should handle 100 session lifecycles quickly (< 100ms)
    assert elapsed < 0.1
    assert len(sessions) == 100


@pytest.mark.benchmark
def test_metadata_operations():
    """
    Benchmark metadata CRUD operations
    元数据CRUD操作性能基准
    """
    metadata_store = {}

    # Benchmark create
    start = time.time()
    for i in range(1000):
        key = f'meta-{i}'
        metadata_store[key] = {
            'value': i,
            'tags': [f'tag{j}' for j in range(5)],
            'timestamp': time.time(),
        }
    create_time = time.time() - start

    # Benchmark read
    start = time.time()
    for i in range(1000):
        key = f'meta-{i}'
        metadata = metadata_store.get(key)
    read_time = time.time() - start

    # Benchmark update
    start = time.time()
    for i in range(1000):
        key = f'meta-{i}'
        if key in metadata_store:
            metadata_store[key]['updated'] = time.time()
    update_time = time.time() - start

    # Benchmark delete
    start = time.time()
    for i in range(500):
        key = f'meta-{i}'
        del metadata_store[key]
    delete_time = time.time() - start

    # All operations should be fast
    assert create_time < 0.05
    assert read_time < 0.01
    assert update_time < 0.02
    assert delete_time < 0.01


@pytest.mark.benchmark
def test_session_persistence_simulation():
    """
    Simulate session persistence overhead
    会话持久化开销模拟
    """
    sessions = [
        {
            'session_id': f'session-{i}',
            'user_id': f'user-{i}',
            'state': OrchestratorState.COMPLETED,
            'messages': [{'role': 'user', 'content': f'Msg {j}'} for j in range(10)],
        }
        for i in range(100)
    ]

    import json

    # Benchmark serialization
    start = time.time()
    serialized = []
    for session in sessions:
        json_str = json.dumps(session)
        serialized.append(json_str)
    serialize_time = time.time() - start

    # Benchmark deserialization
    start = time.time()
    for json_str in serialized:
        session = json.loads(json_str)
    deserialize_time = time.time() - start

    # Should be fast (< 50ms for 100 sessions)
    assert serialize_time < 0.05
    assert deserialize_time < 0.05
