// 50% or more AI-generated

import http from 'k6/http';
import { check } from 'k6';

export const options = {
    noConnectionReuse: true,

    scenarios: {
        steady: {
            executor: 'constant-arrival-rate',
            rate: 100, timeUnit: '1s', duration: '60s',
            preAllocatedVUs: 100, maxVUs: 500,
        },
        spike: {
            executor: 'ramping-arrival-rate',
            startRate: 100, timeUnit: '1s',
            startTime: '65s',
            stages: [
                {target: 300, duration: '10s'},
                {target: 100, duration: '10s'},
            ],
            preAllocatedVUs: 100, maxVUs: 500,
        },
        ramp: {
            executor: 'ramping-arrival-rate',
            startRate: 10, timeUnit: '1s',
            startTime: '90s',
            stages: [{ target: 150, duration: '60s'}],
            preAllocatedVUs: 50, maxVUs: 300,
        },
    },

    thresholds: {
        http_req_failed: ['rate<0.01'],
        checks: ['rate>0.99'],
        'http_req_duration{scenario:steady}' : ['p(95)<100'],
        http_req_duration: ['p(95)<500'],
    },
};

export default function () {
    const res = http.get('http://localhost:8001/health');
    check(res, { 'status is 200': (r) => r.status === 200})
}