// 50% or more Ai-generated code
import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';

const fgaServerLatency = new Trend('fga_query_duration_ms', true);

const API_URL = __ENV.OPENFGA_API_URL || 'http://openfga:8080';
const STORE_ID = __ENV.STORE_ID;
const MODEL_ID = __ENV.MODEL_ID;

export const options = {
  scenarios: {
    mixed_authz_workload: {
      executor: 'ramping-vus',
      startVUs: 5,
      stages: [
        { duration: '5s', target: 25 },  // Warm up connection pool & cache
        { duration: '15s', target: 50 }, // Sustained load across 50 virtual users
        { duration: '5s', target: 0 },   // Ramp down
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.001'],      // Less than 0.1% errors
    http_req_duration: ['p(95)<15', 'p(99)<30'], // 95% under 15ms, 99% under 30ms
  },
};

const params = { headers: { 'Content-Type': 'application/json' } };

export default function () {
  const roll = Math.random();
  let res;

  if (roll < 0.45) {
    // 1. Hierarchical Advisor Check (45% of traffic) -> Expected: allowed=true
    res = http.post(
      `${API_URL}/stores/${STORE_ID}/check`,
      JSON.stringify({
        authorization_model_id: MODEL_ID,
        tuple_key: {
          user: 'membership:advisor_1',
          relation: 'can_edit',
          object: 'meeting:child_meeting',
        },
      }),
      params
    );
    check(res, {
      'advisor check 200 & allowed=true': (r) =>
        r.status === 200 && r.json('allowed') === true,
    });
  } else if (roll < 0.75) {
    // 2. Time-Bounded Agent Conditional Check (30% of traffic) -> Expected: allowed=true
    res = http.post(
      `${API_URL}/stores/${STORE_ID}/check`,
      JSON.stringify({
        authorization_model_id: MODEL_ID,
        tuple_key: {
          user: 'agent:assistant_1',
          relation: 'can_propose',
          object: 'meeting:child_meeting',
        },
        context: { current_time: '2026-06-01T12:00:00Z' },
      }),
      params
    );
    check(res, {
      'agent conditional check 200 & allowed=true': (r) =>
        r.status === 200 && r.json('allowed') === true,
    });
  } else if (roll < 0.95) {
    // 3. Denied Cross-Org Check (20% of traffic) -> Expected: allowed=false
    res = http.post(
      `${API_URL}/stores/${STORE_ID}/check`,
      JSON.stringify({
        authorization_model_id: MODEL_ID,
        tuple_key: {
          user: 'membership:advisor_1',
          relation: 'can_view',
          object: 'folder:folder_org_2',
        },
      }),
      params
    );
    check(res, {
      'cross-org check 200 & allowed=false': (r) =>
        r.status === 200 && r.json('allowed') === false,
    });
  } else {
    // 4. Heavy ListObjects Query (5% of traffic)
    res = http.post(
      `${API_URL}/stores/${STORE_ID}/list-objects`,
      JSON.stringify({
        authorization_model_id: MODEL_ID,
        user: 'membership:advisor_1',
        relation: 'can_edit',
        type: 'folder',
      }),
      params
    );
    check(res, {
      'list-objects 200': (r) => r.status === 200,
    });
  }

  // Record internal OpenFGA evaluation time from response header
  const serverMs = res.headers['Fga-Query-Duration-Ms'];
  if (serverMs) {
    fgaServerLatency.add(parseFloat(serverMs));
  }
}
