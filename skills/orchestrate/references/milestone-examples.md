# Milestone Examples

This document provides examples of well-scoped and poorly-scoped milestones to guide the orchestrator when proposing and evaluating milestones.

---

## Well-Scoped Milestones

### Example 1: "Set up REST API skeleton with health check"

**Acceptance Criteria**:
1. Express (or equivalent) server starts and listens on a configurable port.
2. `GET /health` returns `200 OK` with `{ "status": "healthy" }`.
3. Project has a working `npm start` (or equivalent) command.
4. Basic error-handling middleware returns structured JSON errors.

**Estimated Files**: 5-7 (server entry point, health route, error middleware, config, package.json, tests, README update)

**Why This Is Good**:
- Completable in a single session. The scope is narrow and well-understood.
- Each acceptance criterion is independently verifiable with a simple HTTP request or command.
- Delivers independent value: after this milestone, the project has a running server that future milestones build upon.
- Clear boundary — you know exactly when it is done.

---

### Example 2: "Add user registration with email validation"

**Acceptance Criteria**:
1. `POST /api/users/register` accepts `{ email, password }` and creates a user record.
2. Email is validated for format; duplicate emails return `409 Conflict`.
3. Passwords are hashed before storage (bcrypt or equivalent).
4. Registration endpoint has unit tests covering success, invalid email, duplicate email, and weak password cases.
5. Endpoint returns the created user (without password) and a `201 Created` status.

**Estimated Files**: 8-10 (route, controller, user model, validation logic, hashing utility, tests, migration/schema, config update)

**Why This Is Good**:
- Focused on a single feature (registration) with no scope creep into login, sessions, or authorization.
- Five criteria, each testable with a specific request or assertion.
- Touches fewer than 15 files.
- Independently valuable: even without a login flow, user records exist and the validation logic is reusable.

---

## Poorly-Scoped Milestones

### Example 1: "Build the entire authentication system"

**Why This Is Bad**:
- Too large. "Entire authentication system" includes registration, login, logout, password reset, email verification, token management, role-based access control, session handling, and more. This is 3-5 milestones, not one.
- No clear acceptance criteria — what subset counts as "the entire system"?
- Likely touches 30+ files, far exceeding the 15-file guideline.

**How to Fix**: Split into focused milestones:
1. "Add user registration with email validation"
2. "Add login and JWT token issuance"
3. "Add password reset flow"
4. "Add role-based access middleware"

---

### Example 2: "Improve the codebase"

**Why This Is Bad**:
- Completely ambiguous. No acceptance criteria can be derived from this description.
- "Improve" is not measurable. There is no clear boundary for when this is done.
- Could mean refactoring, adding tests, fixing bugs, improving performance, or all of the above.

**How to Fix**: Replace with a specific, measurable milestone:
- "Refactor data access layer to use repository pattern" (with criteria: specific files moved, tests passing, no direct DB calls outside repositories).
- "Increase test coverage of `src/services/` from 40% to 80%" (with criteria: coverage report shows target met, no skipped tests).

---

### Example 3: "Set up CI/CD, monitoring, logging, and deployment"

**Why This Is Bad**:
- Bundles four unrelated concerns into one milestone. Each has its own tools, configuration, and verification steps.
- Likely touches many different file types (YAML pipelines, Docker configs, application code, infrastructure scripts) making review difficult.
- If one part fails (e.g., deployment), the milestone is incomplete, but the other parts (CI, logging) may be perfectly fine. This wastes completed work.

**How to Fix**: Split into independent milestones:
1. "Set up CI pipeline with lint and test stages"
2. "Add structured logging with request correlation IDs"
3. "Add health-check monitoring endpoint and alerting config"
4. "Create deployment pipeline to staging environment"

Each becomes independently valuable and reviewable.
