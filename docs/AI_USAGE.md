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
