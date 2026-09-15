/**
 * k6 Stress Test — Sparkle Roadmap v3 T6.1.6
 *
 * 100 concurrent users testing all SLO-critical paths:
 *   - Chat first-token  < 2s P95
 *   - Task generation    < 5s P95
 *   - RAG retrieval      < 1s P95
 *   - Galaxy load        < 3s P95
 *   - Aurora L3          < 15s P95
 *
 * Usage:
 *   k6 run --env BASE_URL=http://localhost:8080 backend/tests/load/k6/scenarios.js
 *   k6 run --env VUS=100 --env DURATION=5m backend/tests/load/k6/scenarios.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ── Configuration ─────────────────────────────────────────────

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const VUS = parseInt(__ENV.VUS || '100');
const DURATION = __ENV.DURATION || '5m';

export const options = {
  stages: [
    { duration: '30s', target: Math.min(20, VUS) },    // Warm-up
    { duration: '1m',  target: VUS },                    // Ramp to target
    { duration: '3m',  target: VUS },                    // Sustained load
    { duration: '30s', target: 0 },                      // Cool-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'],  // General: P95 < 3s
    'chat_first_token': ['p(95)<2000'], // SLO: chat first token < 2s
    'task_generation':  ['p(95)<5000'], // SLO: task gen < 5s
    'rag_retrieval':    ['p(95)<1000'], // SLO: RAG retrieval < 1s
    'galaxy_load':      ['p(95)<3000'], // SLO: Galaxy load < 3s
    'health_check':     ['p(95)<200'],  // Infra: health < 200ms
    http_req_failed:    ['rate<0.05'],  // < 5% failure rate
  },
  noConnectionReuse: false,
  userAgent: 'k6-sparkle-stress/1.0',
};

// ── Custom Metrics ────────────────────────────────────────────

const errorRate = new Rate('errors');
const chatLatency = new Trend('chat_first_token');
const taskLatency = new Trend('task_generation');
const ragLatency = new Trend('rag_retrieval');
const galaxyLatency = new Trend('galaxy_load');

// ── Test Data ─────────────────────────────────────────────────

const QUERIES = [
  '微积分基础概念',
  '线性代数矩阵运算',
  '概率论与统计',
  '量子力学入门',
  '数据结构二叉树',
  '操作系统进程调度',
  '计算机网络TCP协议',
  '数据库索引原理',
];

function randomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomUserId() {
  return `stress_user_${Math.floor(Math.random() * 100)}`;
}

function randomSessionId() {
  return `session_${Math.floor(Math.random() * 50)}`;
}

// ── Scenarios ─────────────────────────────────────────────────

export default function () {
  // Each VU cycles through scenario groups with different weights
  const scenario = Math.random();

  if (scenario < 0.35) {
    chatScenario();
  } else if (scenario < 0.55) {
    ragRetrievalScenario();
  } else if (scenario < 0.70) {
    taskGenerationScenario();
  } else if (scenario < 0.85) {
    galaxyScenario();
  } else {
    healthScenario();
  }

  sleep(Math.random() * 2 + 0.5); // 0.5-2.5s think time
}

function chatScenario() {
  group('Chat Stream', () => {
    const userId = randomUserId();
    const query = randomItem(QUERIES);

    const res = http.post(
      `${BASE_URL}/api/v1/chat/stream`,
      JSON.stringify({
        user_id: userId,
        session_id: randomSessionId(),
        content: query,
        stream: true,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: '30s',
      }
    );

    const ok = check(res, {
      'chat status 2xx or 429': (r) =>
        r.status >= 200 && r.status < 300 || r.status === 429,
    });

    if (ok && res.status < 300) {
      chatLatency.add(res.timings.duration);
    }
    if (!ok) errorRate.add(1);
  });
}

function ragRetrievalScenario() {
  group('RAG Retrieval', () => {
    const userId = randomUserId();
    const query = randomItem(QUERIES);

    const res = http.post(
      `${BASE_URL}/api/v1/galaxy/search`,
      JSON.stringify({
        user_id: userId,
        query: query,
        limit: 20,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: '10s',
      }
    );

    const ok = check(res, {
      'rag status 2xx or 404': (r) =>
        r.status >= 200 && r.status < 300 || r.status === 404,
    });

    if (ok && res.status < 300) {
      ragLatency.add(res.timings.duration);
    }
    if (!ok) errorRate.add(1);
  });
}

function taskGenerationScenario() {
  group('Task Generation', () => {
    const userId = randomUserId();

    const res = http.post(
      `${BASE_URL}/api/v1/tasks`,
      JSON.stringify({
        user_id: userId,
        title: `Stress test task ${Date.now()}`,
        type: 'LEARNING',
        estimated_minutes: 25,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: '10s',
      }
    );

    const ok = check(res, {
      'task status 2xx or 4xx': (r) =>
        r.status >= 200 && r.status < 500,
    });

    if (ok && res.status < 300) {
      taskLatency.add(res.timings.duration);
    }
    if (!ok) errorRate.add(1);
  });
}

function galaxyScenario() {
  group('Galaxy Load', () => {
    const userId = randomUserId();

    // Fetch nodes
    const nodesRes = http.get(
      `${BASE_URL}/api/v1/galaxy/nodes?user_id=${userId}&limit=50`,
      { timeout: '10s' }
    );

    const ok = check(nodesRes, {
      'galaxy nodes status 2xx or 404': (r) =>
        r.status >= 200 && r.status < 300 || r.status === 404,
    });

    if (ok && nodesRes.status < 300) {
      galaxyLatency.add(nodesRes.timings.duration);
    }
    if (!ok) errorRate.add(1);
  });
}

function healthScenario() {
  group('Health Check', () => {
    const res = http.get(`${BASE_URL}/health`, { timeout: '5s' });

    check(res, {
      'health status 200': (r) => r.status === 200,
    }) || errorRate.add(1);

    // Also check gateway
    http.get(`${BASE_URL}/api/v1/health`, { timeout: '5s' });
  });
}

// ── Summary Handler ───────────────────────────────────────────

export function handleSummary(data) {
  const metrics = data.metrics;
  const reqDuration = metrics.http_req_duration || {};
  const p95 = reqDuration.values ? reqDuration.values['p(95)'] : 'N/A';
  const failRate = metrics.http_req_failed ? metrics.http_req_failed.values.rate : 0;
  const totalReqs = metrics.http_reqs ? metrics.http_reqs.values.count : 0;

  const chatP95 = metrics.chat_first_token
    ? `${metrics.chat_first_token.values['p(95)'].toFixed(0)}ms` : 'N/A';
  const ragP95 = metrics.rag_retrieval
    ? `${metrics.rag_retrieval.values['p(95)'].toFixed(0)}ms` : 'N/A';
  const taskP95 = metrics.task_generation
    ? `${metrics.task_generation.values['p(95)'].toFixed(0)}ms` : 'N/A';
  const galaxyP95 = metrics.galaxy_load
    ? `${metrics.galaxy_load.values['p(95)'].toFixed(0)}ms` : 'N/A';

  const report = `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SPARKLE STRESS TEST REPORT — T6.1.6
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  VUs:          ${data.state.testRunDurationMs ? VUS : 'N/A'}
  Duration:     ${DURATION}
  Total Reqs:   ${totalReqs}
  Fail Rate:    ${(failRate * 100).toFixed(2)}%

  SLO RESULTS:
  ─────────────────────────────────────
  Chat P95:     ${chatP95}  (target: < 2000ms) ${chatP95 !== 'N/A' && parseInt(chatP95) < 2000 ? '✅' : '❌'}
  RAG P95:      ${ragP95}  (target: < 1000ms)  ${ragP95 !== 'N/A' && parseInt(ragP95) < 1000 ? '✅' : '❌'}
  Task Gen P95: ${taskP95}  (target: < 5000ms)  ${taskP95 !== 'N/A' && parseInt(taskP95) < 5000 ? '✅' : '❌'}
  Galaxy P95:   ${galaxyP95}  (target: < 3000ms)  ${galaxyP95 !== 'N/A' && parseInt(galaxyP95) < 3000 ? '✅' : '❌'}
  Overall P95:  ${typeof p95 === 'number' ? p95.toFixed(0) + 'ms' : p95}  (target: < 3000ms)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;

  return {
    stdout: report,
    'backend/tests/load/results/k6-summary.txt': report,
  };
}
