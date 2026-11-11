// 50% or more AI-generated

import http from 'k6/http';
import { check } from 'k6';

export const options = {
    noConnectionReuse: true,

    scenarios: {
        steady: {
            executor: 'constant-arrival-rate',
            rate: 50, timeUnit: '1s', duration: '60s',
            preAllocatedVUs: 50, maxVUs: 300,
        },
        spike: {
            executor: 'ramping-arrival-rate',
            startRate: 50, timeUnit: '1s',
            startTime: '65s',
            stages: [
                {target: 150, duration: '10s'},
                {target: 50, duration: '10s'},
            ],
            preAllocatedVUs: 50, maxVUs: 300,
        },
        ramp: {
            executor: 'ramping-arrival-rate',
            startRate: 5, timeUnit: '1s',
            startTime: '90s',
            stages: [{ target: 75, duration: '60s'}],
            preAllocatedVUs: 30, maxVUs: 200,
        },
    },

    thresholds: {
        http_req_failed: ['rate<0.01'],
        checks: ['rate>0.99'],
        'http_req_duration{name:health}' : ['p(95)<1000'],
        'http_req_duration{name:tasks}' : ['p(95)<1000'],
    },
};

export default function () {
    const health = http.get('http://localhost:8001/health', { tags: { name : 'health' } });
    check(health, { 'health status is 200': (r) => r.status === 200});

    const tasks = http.get('http://localhost:8001/api/v1/advisors/1/tasks', { tags: { name : 'tasks' } });

    check(tasks, {
        'advisor tasks status is 200': (r) => r.status === 200,
        'advisor tasks returns an array': (r) => {
            try {
                return Array.isArray(r.json());
            } catch {
                return false;
            }
        },
    });
   }
