# AI Usage

## Overview

This document specifies how AI tools, assistants, and generative models are utilized within this repository.

## AI Tools

- ChatGPT
- GitHub Copilot

## AI-assisted features
<!-- identify the feature or task and references the relevant source file, commit, or pull request -->

- `feat:ci` : file:.github/workflows/release-version.yml

## Advisor Login Interface

- Feature: responsive Advisor Login UI with email/password fields, loading and
  error states, workspace-tab toggle, API client integration, and successful
  navigation to the advisor dashboard.
- Source files: `frontend/src/pages/Login.jsx`,
  `frontend/src/services/AuthApi.js`, `frontend/src/styles/Login.css`,
  `frontend/src/App.jsx`, and related navigation and component tests.
- AI assistance: substantial assistance was used to implement and refine the
  frontend feature.
- Verification evidence:
  - `npm run test`: 26 tests passed across 6 test files.
  - Login-focused tests: 5 tests passed, including form input, loading,
    rejected credentials, successful navigation, and the workspace-tab toggle.
  - `npm exec eslint -- src/pages/Login.jsx src/services/AuthApi.js
    src/tests/Login.test.jsx src/App.jsx`: passed.
  - `npm run build`: production build completed successfully.
- Corrections made to AI output:
  - The initial dashboard route was `/`; it was changed so `/` opens the Login
    page and `/dashboard` opens the advisor workspace.
  - The login redirect and Dashboard navbar link were updated to use
    `/dashboard`.
  - The Advisor Workspace and Book A Meeting labels were changed from static
    text to an accessible local toggle that does not navigate to the separate
    booking workflow.
  - The workspace toggle was updated to use supported `tablist` and `tab` ARIA
    roles, and its test was updated to query the tabs by their accessible role.
  - The navigation test was updated to reflect the new dashboard route.


## Structured JSON Logging with PII Redaction

- Feature: structured JSON logging for the backend, with automatic PII
  redaction, a UUID `x-request-id` per request, request logging (method, path,
  status code, duration), and safe 500 error handling.
- Source files: `backend/app/logging_config.py`,
  `backend/app/middleware/request_logging.py`, `backend/app/routers/debug.py`,
  `backend/test/observability/test_structured_logging.py`, and
  `backend/demo/demo_logging.py`.
- AI assistance: substantial assistance was used to implement the logger,
  middleware, tests and demo, integrated with the existing
  `security/redactor.py`.
- Verification evidence:
  - `python -m pytest test/ -v`: 85 tests passed (26 new, 59 existing).
  - Mutation check: disabling redaction makes 11 logging tests fail, showing
    the tests detect PII leaks.
  - Live run with Uvicorn and curl: a request with a fake email and SIN
    returned a 500 with an `x-request-id`, and the matching log lines showed
    `[REDACTED]` with no PII in stdout or stderr.
- Corrections made to AI output:
  - The logging middleware was first added after CORS, which made 500
    responses lose their CORS headers; it was moved before CORS so the
    frontend can read the error and request id.
  - Error stack traces were too long to read (about 25 library frames); they
    were shortened to our own code with a `location` field, and
    `LOG_FULL_STACK` was added to show the full stack when needed.
  - The test filter was adjusted so log lines from the test client (httpx,
    asyncio) did not cause false failures.
