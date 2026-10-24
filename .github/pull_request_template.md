# PR Rules

A review must provide sufficient technical evidence:

- \>=1 technical question, concern, suggestion **OR**
- A requested change on correctness, testing, security, error handling, architecture, maintainability, or another relevant property
- A reviewer approves and leaves a comment describing >=1 aspect checked, even when no change is required

## Traceability & Related Issue

<!-- Link the GitHub Issue that this PR addresses. -->
Closes / Fixes #

Contributors: @

## Description & Changes

<!-- Briefly describe what this PR does, why, and the main components modified. -->
- 
- 

## Substantive Feature Classification

- [ ] **N/A** — Refactoring, CI/CD, documentation, or non-feature bugfix
- [ ] Business rules or validation beyond basic required-field checks
- [ ] State transition or multi-step workflow
- [ ] Data transformation, aggregation, ranking, calculation, or algorithmic processing
- [ ] Coordinates multiple internal components or services
- [ ] Non-trivial authorization or permission logic
- [ ] Background or asynchronous processing
- [ ] External service integration with result processing/transformation
- [ ] Significant domain-specific logic unique to Orbit

## Automated Testing Evidence

### Test Files

- `path/to/test_file`

- [ ] **Happy Path:** >=1 test verifies expected behavior
- [ ] **Edge / Error Cases:** Tests for invalid input, boundary conditions, failure cases, or alternative paths
- [ ] **Integration (if applicable):** Tests component interaction (DB, API/Frontend, Auth flow, or mocked external service).
- [ ] **Local Tests Pass:** Linter, formatter, and test suites pass.

## 4. Responsible Use of AI Disclosure

**AI Contribution Level for this PR (Select ONE):**

- [ ] No substantial AI-generated code
- [ ] Below 50% AI-generated
- [ ] 50% or more AI-generated

**AI-Assisted Source Files in this PR:**

- `none` <!-- or list files, e.g., src/auth/service.ts -->

**AI Compliance Checklist:**

- [ ] Every modified source file contains the required AI-contribution declaration header at the top of the file.
- [ ] If substantial AI assistance was used, updated `AI_USAGE.md` with the feature, verification method (test/review), and any corrections made to AI output

## Notes for Reviewers

<!-- Mention anything specific that reviewers should pay attention to. -->
