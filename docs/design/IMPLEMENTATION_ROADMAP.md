# DevTrack Project Implementation Roadmap
**Version:** 1.0.0  
**Status:** Approved  
**Prepared By:** Rachana Gandla  

This document outlines the detailed roadmap for designing, implementing, testing, and deploying DevTrack. The project is split into 18 execution phases (Phase 0 to Phase 17) grouped under 6 major milestones. Every task is atomic, designed to match a single Git commit, and includes clear acceptance criteria and explicit dependencies.

---

## 📅 Project Folder Structure Reference
We will adhere to the folder layout specified in [TECH_STACK.md](file:///d:/workspace/DevTrack/docs/design/TECH_STACK.md):
*   `app/api/`: API Endpoint Routers (auth, profile, dashboard, reports).
*   `app/core/`: Application settings, DB session pools, security/JWT helpers, logging configs.
*   `app/models/`: SQLAlchemy ORM database models.
*   `app/schemas/`: Pydantic validation schemas.
*   `app/repositories/`: Database query logic (CRUD abstractions).
*   `app/services/`: Core Business Logic Engines.
    *   `app/services/integrations/`: Platform client adapters (GitHub/LeetCode clients).
    *   `app/services/analytics/`: Data parsing & trend extraction.
    *   `app/services/scoring/`: Developer score calculations.
    *   `app/services/insights/`: Snapshot comparisons.
    *   `app/services/recommendations/`: Rule suggestions engine.
    *   `app/services/scheduler/`: APScheduler background orchestrators.
*   `app/utils/`: Stateless helpers.

---

## 🏆 Project Milestones
*   **Milestone 1: Planning Complete** (Phase 0)
*   **Milestone 2: Backend Foundation Complete** (Phases 1–3)
*   **Milestone 3: Platform Integrations Complete** (Phases 4–7)
*   **Milestone 4: Analytics Engine Complete** (Phases 8–11)
*   **Milestone 5: Dashboard APIs Complete** (Phases 12–14)
*   **Milestone 6: MVP Complete** (Phase 15 & Phase 17 MVP tasks)

---

## 🏁 Milestone 1: Planning Complete

### Phase 0: Planning (MVP)
*   **Objective:** Gather requirements and design the core components of the system before writing code.
*   **Deliverables:** Completed SRS, Tech Stack, Architecture, DB Design, and API Spec documents.
*   **Estimated Complexity:** Low
*   **Dependencies:** None
*   **Exit Criteria:** All planning documents are created, reviewed, and approved.
*   **Risk Assessment:**
    *   *Risk:* Scope creep or unclear scoring formulas.
    *   *Mitigation:* Define explicit MVP constraints and rule-based formulas in the SRS.

#### Tasks
*   **Task 0.1: Gather Requirements & Complete SRS**
    *   *Objective:* Finalize scope, requirements, assumptions, and constraints.
    *   *Description:* Write and finalize the `docs/design/SRS.md` file.
    *   *Difficulty:* Easy
    *   *Dependencies:* None
    *   *Expected Deliverables:* Completed `docs/design/SRS.md` file.
    *   *Suggested Commit:* `docs: write software requirements specification`
    *   *Acceptance Criteria:* Document covers all functional/non-functional requirements and contains user-approved semantic versions.
*   **Task 0.2: Design Technology Stack Specification**
    *   *Objective:* Detail libraries, frameworks, database, and rationale.
    *   *Description:* Write and finalize the `docs/design/TECH_STACK.md` file.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 0.1
    *   *Expected Deliverables:* Completed `docs/design/TECH_STACK.md` file.
    *   *Suggested Commit:* `docs: finalize technology stack specification`
    *   *Acceptance Criteria:* Includes explicit Decision Records (FastAPI vs. Flask, SQLAlchemy vs. SQLModel, etc.) and Folder Structure.
*   **Task 0.3: Design System Architecture**
    *   *Objective:* Define component relationships, data flow, and layers.
    *   *Description:* Create `docs/architecture/ARCHITECTURE.md` explaining modules and async execution.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 0.2
    *   *Expected Deliverables:* System architecture document.
    *   *Suggested Commit:* `docs: design system architecture and data flows`
    *   *Acceptance Criteria:* Flowchart shows the exact asynchronous background synchronization cycle.
*   **Task 0.4: Design Database Schema (ERD)**
    *   *Objective:* Model database tables, relationships, types, and indexes.
    *   *Description:* Create `docs/architecture/DATABASE_DESIGN.md` including table definitions.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 0.3
    *   *Expected Deliverables:* Detailed ERD layout document.
    *   *Suggested Commit:* `docs: design database entity relationship diagram`
    *   *Acceptance Criteria:* Defines users, profiles, snapshots, history, scores, insights, recommendations, and reports tables.
*   **Task 0.5: Define API Endpoint Contracts**
    *   *Objective:* Formulate exact request payloads, response bodies, and error response schemas.
    *   *Description:* Create `docs/design/API_SPECIFICATION.md` defining endpoints for auth, profile, and dashboard.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 0.4
    *   *Expected Deliverables:* API Endpoint design contracts.
    *   *Suggested Commit:* `docs: define REST API endpoints and data schemas`
    *   *Acceptance Criteria:* All MVP endpoints mapped with correct query parameters and Pydantic request/response structures.

---

## 🏁 Milestone 2: Backend Foundation Complete

### Phase 1: Project Setup (MVP)
*   **Objective:** Bootstrap the FastAPI framework, configure settings, establish database connection pool, initialize migrations, and configure logging.
*   **Deliverables:** Runable backend with basic config, async connection pool, migrations, JSON logging, and a health endpoint.
*   **Estimated Complexity:** Low
*   **Dependencies:** Phase 0 Completed
*   **Exit Criteria:** Database connectivity successfully checked via a working `/health` API.
*   **Risk Assessment:**
    *   *Risk:* Database connection failure during local startup.
    *   *Mitigation:* Provide clear Docker/local PostgreSQL connection credentials and verify with try/except blocks.

#### Tasks
*   **Task 1.1: FastAPI App Initialization & Directory Setup**
    *   *Objective:* Setup Python environment and folder structures.
    *   *Description:* Create app directories and initialize `main.py` with Uvicorn.
    *   *Difficulty:* Easy
    *   *Dependencies:* Phase 0
    *   *Expected Deliverables:* Directory structure and run scripts.
    *   *Suggested Commit:* `setup: initialize FastAPI application structure`
    *   *Acceptance Criteria:* Server boots up locally and serves standard `404` pages on empty routes.
*   **Task 1.2: Environment Variable Configuration**
    *   *Objective:* Set up configuration settings using Pydantic Settings.
    *   *Description:* Create `app/core/config.py` loading database, security, and logging values.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 1.1
    *   *Expected Deliverables:* Configuration module (`app/core/config.py`).
    *   *Suggested Commit:* `feat(core): implement Pydantic settings and env loading`
    *   *Acceptance Criteria:* App fails to start if crucial variables (e.g. `DATABASE_URL`) are missing.
*   **Task 1.3: PostgreSQL Connection & SQLAlchemy Engine Setup**
    *   *Objective:* Establish asynchronous database sessions.
    *   *Description:* Set up SQLAlchemy async engine, sessionmaker, and declarative base class in `app/core/database.py`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 1.2
    *   *Expected Deliverables:* Async session helper.
    *   *Suggested Commit:* `feat(db): establish async SQLAlchemy engine and session management`
    *   *Acceptance Criteria:* Async db session can be injected as a dependency in FastAPI routes.
*   **Task 1.4: Alembic Migration Initialization**
    *   *Objective:* Install database migration tracker.
    *   *Description:* Run `alembic init` and update configuration to read database URL dynamically.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 1.3
    *   *Expected Deliverables:* Alembic directory and configuration.
    *   *Suggested Commit:* `setup: initialize Alembic migrations configuration`
    *   *Acceptance Criteria:* `alembic current` command runs without errors.
*   **Task 1.5: Structured Logging Configuration**
    *   *Objective:* Setup standardized JSON logging output.
    *   *Description:* Configure Python logging dictConfig to write JSON logs with request-ids in `app/core/logging.py`.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 1.1
    *   *Expected Deliverables:* Logging config setup.
    *   *Suggested Commit:* `feat(core): configure structured JSON logging`
    *   *Acceptance Criteria:* Log statements print out as structured JSON strings containing level, message, and timestamp.
*   **Task 1.6: Health Check API Endpoint**
    *   *Objective:* Expose health indicator.
    *   *Description:* Add `/health` endpoint verifying database connection status.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 1.3, Task 1.5
    *   *Expected Deliverables:* Route handler for health status.
    *   *Suggested Commit:* `feat(api): implement database health check endpoint`
    *   *Acceptance Criteria:* Calling `/health` returns `{"status": "healthy"}` and HTTP `200` if database connection succeeds.

---

### Phase 2: Authentication & User Management (MVP)
*   **Objective:** Implement secure user signups, signins, and session tokens under the `/api/v1/auth` path.
*   **Deliverables:** User database models, registration, login, and token-refresh endpoints secured by password hashing and JWT validation.
*   **Estimated Complexity:** Medium
*   **Dependencies:** Phase 1 Completed
*   **Exit Criteria:** Complete validation that protected endpoints reject requests lacking valid JWT authorization headers.
*   **Risk Assessment:**
    *   *Risk:* Insecure password storage or vulnerable token signing.
    *   *Mitigation:* Enforce `bcrypt` hashing and strict token signature checks using environment variables for secrets.

#### Tasks
*   **Task 2.1: Define User and Auth DB Models**
    *   *Objective:* Create relational schemas for users.
    *   *Description:* Define the `User` database model mapping to the `users` table in `app/models/user.py`.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 1.4
    *   *Expected Deliverables:* SQLAlchemy model for User.
    *   *Suggested Commit:* `feat(models): create user db model`
    *   *Acceptance Criteria:* Table has columns for id, email, hashed_password, and created_at. Migration successfully applied.
*   **Task 2.2: Implement Password Hashing Utility Functions**
    *   *Objective:* Secure passwords using standard cryptographic algorithms.
    *   *Description:* Write hashing and verification helpers using `passlib[bcrypt]` in `app/core/security.py`.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 2.1
    *   *Expected Deliverables:* Security utility functions.
    *   *Suggested Commit:* `feat(auth): implement bcrypt password hashing helpers`
    *   *Acceptance Criteria:* `verify_password` returns `True` only when checking matching plain password and hash.
*   **Task 2.3: Implement User Registration API**
    *   *Objective:* Create sign up endpoint.
    *   *Description:* Write registration route `/api/v1/auth/register` and Pydantic schemas. Verify duplicate emails are rejected.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 2.2
    *   *Expected Deliverables:* `/api/v1/auth/register` API endpoint.
    *   *Suggested Commit:* `feat(api): implement user registration endpoint`
    *   *Acceptance Criteria:* Valid details return HTTP `201` and user details without password hash. Duplicate emails return HTTP `400`.
*   **Task 2.4: Implement User Login API**
    *   *Objective:* Generate access tokens for valid logins.
    *   *Description:* Create login endpoint `/api/v1/auth/login` verifying hash and signing JWTs.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 2.3
    *   *Expected Deliverables:* `/api/v1/auth/login` API endpoint returning JWT.
    *   *Suggested Commit:* `feat(api): implement user login endpoint`
    *   *Acceptance Criteria:* Correct credentials return access token, refresh token, and token type. Incorrect credentials return HTTP `401`.
*   **Task 2.5: Implement JWT Dependency Injection**
    *   *Objective:* Secure routes using FastAPI dependencies.
    *   *Description:* Implement JWT decoding dependency to extract current user from HTTP headers.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 2.4
    *   *Expected Deliverables:* Reusable authentication security dependency.
    *   *Suggested Commit:* `feat(auth): implement JWT validation dependency`
    *   *Acceptance Criteria:* Correct bearer token injects User model to route. Invalid, expired, or absent tokens raise HTTP `401`.
*   **Task 2.6: Create Protected Routes Verification**
    *   *Objective:* Verify endpoints are secure.
    *   *Description:* Create `/api/v1/auth/me` route requiring authentication dependency.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 2.5
    *   *Expected Deliverables:* Route test confirming authentication validation.
    *   *Suggested Commit:* `feat(api): create protected user route to verify auth`
    *   *Acceptance Criteria:* Accessing `/api/v1/auth/me` with a valid token returns current logged-in user profile metrics.

---

### Phase 3: User Profile Management (MVP)
*   **Objective:** Manage user metadata and connect third-party platforms.
*   **Deliverables:** Profile database model, and profile CRUD & account connection endpoints under `/api/v1/profile`.
*   **Estimated Complexity:** Low
*   **Dependencies:** Phase 2 Completed
*   **Exit Criteria:** Profile connection API successfully updates username handles in the database.
*   **Risk Assessment:**
    *   *Risk:* Users submit invalid platform usernames.
    *   *Mitigation:* Perform validation of username formats before database persistence.

#### Tasks
*   **Task 3.1: Design Profile Database Model**
    *   *Objective:* Relate a User to a Profile.
    *   *Description:* Create `Profile` table storing bio, avatar, github_username, and leetcode_username.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 2.1, Task 1.4
    *   *Expected Deliverables:* Profile SQLAlchemy Model in `app/models/user.py`.
    *   *Suggested Commit:* `feat(models): create user profile database model`
    *   *Acceptance Criteria:* Profile record is created automatically or linked via foreign key to User table. Migration applied.
*   **Task 3.2: Implement Profile Retrieval & Update API**
    *   *Objective:* Access and update profile info.
    *   *Description:* Create `/api/v1/profile` endpoints (GET to view, PUT to update basic details).
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 3.1, Task 2.5
    *   *Expected Deliverables:* Profile CRUD endpoints.
    *   *Suggested Commit:* `feat(api): implement profile fetch and update endpoints`
    *   *Acceptance Criteria:* Profile retrieval endpoints require JWT. Updating profile details returns updated profile fields.
*   **Task 3.3: Implement Platform Username Connection API**
    *   *Objective:* Link GitHub and LeetCode handles.
    *   *Description:* Write endpoint `/api/v1/profile/connect` validating username syntax and saving to profile.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 3.2
    *   *Expected Deliverables:* Linkage endpoints with username syntax validation.
    *   *Suggested Commit:* `feat(api): implement platform connection endpoints`
    *   *Acceptance Criteria:* Connection route parses and persists `github_username` and `leetcode_username`.

---

## 🏁 Milestone 3: Platform Integrations Complete

### Phase 4: Integration Framework (MVP)
*   **Objective:** Define the abstract platform contracts, shared structures, rate limit handlers, and schema validation components to ensure consistency across integrations.
*   **Deliverables:** Platform base classes, shared HTTP clients, rate limiting decorators, and validation helpers.
*   **Estimated Complexity:** Medium
*   **Dependencies:** Phase 3 Completed
*   **Exit Criteria:** Abstract integration client classes written and validated via mock structures.
*   **Risk Assessment:**
    *   *Risk:* External network delays hang worker threads.
    *   *Mitigation:* Configure strict connection and read timeouts (e.g. 10 seconds) on the HTTP clients.

#### Tasks
*   **Task 4.1: Implement Base Platform Client Abstract Class**
    *   *Objective:* Create contract for platform integrations.
    *   *Description:* Define abstract class `BasePlatformClient` in `app/services/integrations/base.py` declaring raw fetch structures.
    *   *Difficulty:* Easy
    *   *Dependencies:* Phase 3
    *   *Expected Deliverables:* Abstract platform client definition.
    *   *Suggested Commit:* `feat(sync): create abstract base platform client class`
    *   *Acceptance Criteria:* Defines abstract method signatures for `fetch_raw_data`.
*   **Task 4.2: Define Synchronization Schema Validation Helpers**
    *   *Objective:* Ensure external JSON payloads conform to expected models.
    *   *Description:* Implement shared validation functions checking for necessary structure keys before snapshot storage.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 4.1
    *   *Expected Deliverables:* Shared validation middleware.
    *   *Suggested Commit:* `feat(sync): add platform response validation helpers`
    *   *Acceptance Criteria:* Payloads lacking critical identity fields are rejected immediately.
*   **Task 4.3: Implement Global Rate Limiting and Retry Helpers**
    *   *Objective:* Prevent sync failures due to temporary blocking.
    *   *Description:* Write decorator classes implementing exponential backoff retries for outgoing HTTP client requests.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 4.2
    *   *Expected Deliverables:* Rate limiting retry module.
    *   *Suggested Commit:* `feat(sync): implement backoff retry decorators`
    *   *Acceptance Criteria:* Decodes rate limit response headers (e.g. `X-RateLimit-Reset`) and schedules pauses when triggers are hit.

---

### Phase 5: GitHub Integration (MVP)
*   **Objective:** Establish communication with GitHub REST API and write raw sync logic.
*   **Deliverables:** GitHub API client adapter, repository metadata fetcher, commit history parsing logic, and raw JSON storage.
*   **Estimated Complexity:** Medium
*   **Dependencies:* Phase 4 Completed
*   **Exit Criteria:** Raw JSON response payloads fetched from GitHub REST API successfully stored in snapshot tables.
*   **Risk Assessment:**
    *   *Risk:* GitHub rate limits our requests (60 per hour for unauthenticated, 5000 for authenticated).
    *   *Mitigation:* Support optional personal access tokens (PAT) in settings, implement exponential backoff retry.

#### Tasks
*   **Task 5.1: Implement GitHub HTTP Client Adapter**
    *   *Objective:* Fetch raw payloads from GitHub API using `httpx`.
    *   *Description:* Create `GitHubClient` subclass in `app/services/integrations/github.py` inheriting from `BasePlatformClient`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 4.3
    *   *Expected Deliverables:* GitHub Client class module.
    *   *Suggested Commit:* `feat(sync): implement GitHub API client adapter`
    *   *Acceptance Criteria:* Correctly fetches user bio and public repository stats using mock or live credentials.
*   **Task 5.2: Create GitHub Data Parser & Synchronization Service**
    *   *Objective:* Fetch profile metadata, repositories, and commit history.
    *   *Description:* Write sync methods to aggregate user repositories, forks, stars, languages, and commit history.
    *   *Difficulty:* Hard
    *   *Dependencies:* Task 5.1
    *   *Expected Deliverables:* Parser data schemas and sync controller logic.
    *   *Suggested Commit:* `feat(sync): implement GitHub data extraction service`
    *   *Acceptance Criteria:* Service combines user stats, repository metadata, and commit frequencies into a unified dictionary structure.
*   **Task 5.3: Design GitHub Raw Snapshot Model & Storage**
    *   *Objective:* Backup fetched raw JSON payloads.
    *   *Description:* Create `github_snapshots` database table with a JSONB data type in `app/models/snapshot.py`.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 5.2, Task 1.4
    *   *Expected Deliverables:* Snapshot model, migration script, and persistence function.
    *   *Suggested Commit:* `feat(db): create github snapshots model and migration`
    *   *Acceptance Criteria:* Raw JSON dictionary saved successfully in snapshot table with foreign key reference to User.

---

### Phase 6: LeetCode Integration (MVP)
*   **Objective:** Establish communication with LeetCode GraphQL endpoint and write raw sync logic.
*   **Deliverables:** LeetCode API client adapter, problem-solving, submissions, and contest stats fetcher, and raw JSON storage.
*   **Estimated Complexity:** Medium
*   **Dependencies:** Phase 4 Completed
*   **Exit Criteria:** Raw JSON response payloads fetched from LeetCode GraphQL API successfully stored in snapshot tables.
*   **Risk Assessment:**
    *   *Risk:* LeetCode does not have an official public API; graphql schema may change.
    *   *Mitigation:* Wrap all GraphQL queries in a single client module to isolate shifts.

#### Tasks
*   **Task 6.1: Implement LeetCode GraphQL Client Adapter**
    *   *Objective:* Establish communication with LeetCode API.
    *   *Description:* Create `LeetCodeClient` subclass in `app/services/integrations/leetcode.py` issuing GraphQL POST requests.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 4.3
    *   *Expected Deliverables:* GraphQL LeetCode adapter class.
    *   *Suggested Commit:* `feat(sync): implement LeetCode GraphQL client adapter`
    *   *Acceptance Criteria:* GraphQL requests to LeetCode endpoint return successful user data profiles.
*   **Task 6.2: Create LeetCode Data Parser & Synchronization Service**
    *   *Objective:* Fetch problems solved, contest rating, streaks, and topic stats.
    *   *Description:* Write query handlers to fetch, parse, and aggregate LeetCode metrics.
    *   *Difficulty:* Hard
    *   *Dependencies:* Task 6.1
    *   *Expected Deliverables:* Parser data schemas and sync controller logic.
    *   *Suggested Commit:* `feat(sync): implement LeetCode data extraction service`
    *   *Acceptance Criteria:* Service compiles user stats, streaks, difficulty distributions, and topic counts.
*   **Task 6.3: Design LeetCode Raw Snapshot Model & Storage**
    *   *Objective:* Backup fetched raw JSON payloads.
    *   *Description:* Create `leetcode_snapshots` database table with a JSONB data type in `app/models/snapshot.py`.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 6.2, Task 1.4
    *   *Expected Deliverables:* Snapshot model, migration script, and persistence function.
    *   *Suggested Commit:* `feat(db): create leetcode snapshots model and migration`
    *   *Acceptance Criteria:* Raw JSON dictionary saved successfully in snapshot table with foreign key reference to User.

---

### Phase 7: Historical Data & Snapshot Tables (MVP)
*   **Objective:** Model tables to store structured chronological snapshots of developers' progress.
*   **Deliverables:** Schema migrations and CRUD repositories for GitHub and LeetCode daily history snapshots.
*   **Estimated Complexity:** Low
*   **Dependencies:** Phase 5 and Phase 6 Completed
*   **Exit Criteria:** Database tables successfully created and populated with daily structured snapshot logs.
*   **Risk Assessment:**
    *   *Risk:* Table rows grow extensively over time.
    *   *Mitigation:* Create compound indexes on `(user_id, date)` to maintain fast query lookups.

#### Tasks
*   **Task 7.1: Create Structured GitHub and LeetCode History Tables**
    *   *Objective:* Design tabular structures for parsed metrics.
    *   *Description:* Define `github_histories` and `leetcode_histories` tables in `app/models/history.py`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 5.3, Task 6.3, Task 1.4
    *   *Expected Deliverables:* Relational history models and migration.
    *   *Suggested Commit:* `feat(db): implement github and leetcode history tables`
    *   *Acceptance Criteria:* Migration runs. Tables have fields for solved metrics, stars, commits, and timestamps.
*   **Task 7.2: Implement History CRUD Repository Services**
    *   *Objective:* Provide standard interface to append and retrieve history logs.
    *   *Description:* Write transactional service functions in `app/repositories/snapshot_repo.py` to record and query history logs.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 7.1
    *   *Expected Deliverables:* DB service CRUD functions.
    *   *Suggested Commit:* `feat(db): create history repository services`
    *   *Acceptance Criteria:* Functions successfully insert records and query ranges (e.g. last 30 days) filtered by `user_id`.
*   **Task 7.3: Implement Trend Query Engine**
    *   *Objective:* Query delta trends (weekly or monthly growth data).
    *   *Description:* Write query handlers in `app/services/analytics/` computing changes between two dates.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 7.2
    *   *Expected Deliverables:* Analytics utility functions for data extraction.
    *   *Suggested Commit:* `feat(db): implement historical trend query methods`
    *   *Acceptance Criteria:* Trend calculations return correct growth values (e.g. +10 problems solved, +15 commits).

---

## 🏁 Milestone 4: Analytics Engine Complete

### Phase 8: Developer Analytics Engine (MVP)
*   **Objective:** Compute structured statistics and growth parameters from historical data snapshots.
*   **Deliverables:** GitHub Analyzer, LeetCode Analyzer, and a combined Analytics coordinator service.
*   **Estimated Complexity:** Medium
*   **Dependencies:** Phase 7 Completed
*   **Exit Criteria:** System parses platform records and compiles active repository growth, commit trends, and topic progress logs in DB.
*   **Risk Assessment:**
    *   *Risk:* Missing data snapshots for a specific day break growth trend comparisons.
    *   *Mitigation:* Use closest available historical snapshot date or default to zero growth.

#### Tasks
*   **Task 8.1: Develop GitHub Analyzer Service**
    *   *Objective:* Parse repository volume, commit distributions, and active days.
    *   *Description:* Write analyzer code counting active repositories, language shares, and contribution streaks in `app/services/analytics/github.py`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 7.3
    *   *Expected Deliverables:* GitHub Analyzer module.
    *   *Suggested Commit:* `feat(analytics): implement GitHub analyzer service`
    *   *Acceptance Criteria:* Correctly identifies most starred repo, primary languages, and commit streak from snapshot.
*   **Task 8.2: Develop LeetCode Analyzer Service**
    *   *Objective:* Parse topic counts, difficulty allocations, and streak lengths.
    *   *Description:* Write analyzer code parsing topic-wise counts, easy/medium/hard percentages, and contest progress in `app/services/analytics/leetcode.py`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 7.3
    *   *Expected Deliverables:* LeetCode Analyzer module.
    *   *Suggested Commit:* `feat(analytics): implement LeetCode analyzer service`
    *   *Acceptance Criteria:* Computes easy/medium/hard distribution ratios and extracts topic mastery counts.
*   **Task 8.3: Create Analytics Database Storage & Migration**
    *   *Objective:* Persist compiled developer metrics.
    *   *Description:* Design `developer_analytics` table in `app/models/history.py` storing compiled stats.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 8.1, Task 8.2, Task 1.4
    *   *Expected Deliverables:* Database model and schema migration.
    *   *Suggested Commit:* `feat(db): create developer analytics table and migration`
    *   *Acceptance Criteria:* Analytics record written and retrieved from database matching parsed properties.

---

### Phase 9: Developer Score Engine (MVP)
*   **Objective:** Formulate and calculate the custom, rule-based Developer Score.
*   **Deliverables:** Scoring algorithm, Score database tables, and calculation service functions.
*   **Estimated Complexity:** Medium
*   **Dependencies:** Phase 8 Completed
*   **Exit Criteria:** Score Engine outputs a weighted overall score (out of 1000) and saves it to the database score table.
*   **Risk Assessment:**
    *   *Risk:* Zero activity logs produce division-by-zero or calculation bugs.
    *   *Mitigation:* Check for zero/empty states and return default base scores.

#### Tasks
*   **Task 9.1: Design and Implement Weighted Developer Scoring Rules**
    *   *Objective:* Code the mathematical formula for Developer Score.
    *   *Description:* Implement a scoring module that applies weights (Consistency, Depth, Open Source impact) in `app/services/scoring/calculator.py`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 8.3
    *   *Expected Deliverables:* Scoring calculation module.
    *   *Suggested Commit:* `feat(score): implement weighted scoring algorithm`
    *   *Acceptance Criteria:* Math checks out: 30% consistency, 35% problem depth, 35% open-source impact. Returns integers between 0 and 1000.
*   **Task 9.2: Implement Score History Model & Schema Migration**
    *   *Objective:* Track changes in Developer Score over time.
    *   *Description:* Design `developer_scores` table storing overall score, category breakdowns, and timestamp in `app/models/score.py`.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 9.1, Task 1.4
    *   *Expected Deliverables:* ORM model and schema migration.
    *   *Suggested Commit:* `feat(db): create developer score model and migration`
    *   *Acceptance Criteria:* Table supports storage of sub-category breakdowns. Migration executes.
*   **Task 9.3: Develop Score Recording Service**
    *   *Objective:* Trigger score updates and save scores.
    *   *Description:* Write service layers validating intermediate states, running the calculator, and updating the database records.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 9.2, Task 8.3
    *   *Expected Deliverables:* Score coordinator service.
    *   *Suggested Commit:* `feat(score): implement score calculation and storage service`
    *   *Acceptance Criteria:* Service fetches latest analytics, calculates score, and writes a history record to database.

---

### Phase 10: Insights Engine (MVP)
*   **Objective:** Generate comparison alerts between snapshots (e.g. increase/decrease in practice).
*   **Deliverables:** Rule-based Insights generator, insights database model, and generation pipeline.
*   **Estimated Complexity:** Medium
*   **Dependencies:** Phase 8 Completed
*   **Exit Criteria:** System compares current and past stats to save structured insights in the database.
*   **Risk Assessment:**
    *   *Risk:* Database query checks fail when comparing snapshots.
    *   *Mitigation:* Fallback gracefully by skipping insights if previous data is unavailable.

#### Tasks
*   **Task 10.1: Write Rule-Based Comparison Algorithms**
    *   *Objective:* Write algorithms detecting changes in user progress over time.
    *   *Description:* Create functions comparing current and past snapshot values in `app/services/insights/rules.py`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 8.3
    *   *Expected Deliverables:* Comparison logic module.
    *   *Suggested Commit:* `feat(insights): implement comparison rule algorithms`
    *   *Acceptance Criteria:* Logic correctly tags increase/decrease thresholds (e.g., > 10% drop in topic commits).
*   **Task 10.2: Create Insights Database Model & Migration**
    *   *Objective:* Persist text insights.
    *   *Description:* Design `insights` table storing user ID, insight text, type, and timestamp in `app/models/insight.py`.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 10.1, Task 1.4
    *   *Expected Deliverables:* ORM model and schema migration.
    *   *Suggested Commit:* `feat(db): create insights model and migration`
    *   *Acceptance Criteria:* Table successfully holds VARCHAR/TEXT strings and relational foreign keys. Migration runs.
*   **Task 10.3: Create Insights Generation Service**
    *   *Objective:* Orchestrate the evaluation and storage of insights.
    *   *Description:* Implement service coordinating past snapshot queries, running rules, and updating active insights.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 10.2, Task 7.3
    *   *Expected Deliverables:* Service layer module.
    *   *Suggested Commit:* `feat(insights): implement insights generation service`
    *   *Acceptance Criteria:* Executing service generates and writes insights to database when historical discrepancies occur.

---

### Phase 11: Recommendation Engine (MVP)
*   **Objective:** Produce practice suggestions based on weak categories, scoring trends, or inactivity.
*   **Deliverables:** Rule-based Recommendation algorithm, recommendations database model, and recommendation generator service.
*   **Estimated Complexity:** Medium
*   **Dependencies:** Phase 8, Phase 9, and Phase 10 Completed
*   **Exit Criteria:** System evaluates analytics metrics and saves personalized recommendations in the database.
*   **Risk Assessment:**
    *   *Risk:* Duplicated or spam recommendations saved to profile.
    *   *Mitigation:* Clear out old recommendation statuses before writing new active ones.

#### Tasks
*   **Task 11.1: Design Rule-Based Recommendation Algorithms**
    *   *Objective:* Programmatic rules matching weak scores/topics to recommendations.
    *   *Description:* Write functions reading analytics metrics and returning specific recommendations in `app/services/recommendations/rules.py`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 8.3, Task 9.3
    *   *Expected Deliverables:* Rule compiler logic module.
    *   *Suggested Commit:* `feat(recs): implement recommendation compiler rules`
    *   *Acceptance Criteria:* Returns specific strings (e.g. "Practice Backtracking") when score indicates a weak area.
*   **Task 11.2: Create Recommendations Database Model & Migration**
    *   *Objective:* Persist suggestions in the database.
    *   *Description:* Design `recommendations` table storing user ID, title, priority, and status in `app/models/recommendation.py`.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 11.1, Task 1.4
    *   *Expected Deliverables:* ORM model and schema migration.
    *   *Suggested Commit:* `feat(db): create recommendations model and migration`
    *   *Acceptance Criteria:* Database columns support enum fields for priority and completion status.
*   **Task 11.3: Create Recommendation Orchestrator Service**
    *   *Objective:* Execute logic and update recommendations database.
    *   *Description:* Write service class checking existing entries, clearing outdated ones, and inserting new recommendations.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 11.2, Task 10.3
    *   *Expected Deliverables:* Recommendations service coordinator.
    *   *Suggested Commit:* `feat(recs): implement recommendation manager service`
    *   *Acceptance Criteria:* Service successfully aggregates active recommendation records in database.

---

## 🏁 Milestone 5: Dashboard APIs Complete

### Phase 12: Dashboard & Analytics APIs (MVP)
*   **Objective:** Expose endpoints returning aggregated statistics, history charts, milestones, and timelines under the `/api/v1/dashboard/...` routes.
*   **Deliverables:** REST API routes delivering combined scores, analytics, timeline events, and recommendation lists.
*   **Estimated Complexity:** Medium
*   **Dependencies:** Phase 9, Phase 10, and Phase 11 Completed
*   **Exit Criteria:** Frontend-consumable endpoints returning pre-calculated dashboard payloads in under 200ms.
*   **Risk Assessment:**
    *   *Risk:* Inefficient database queries lead to slow response times.
    *   *Mitigation:* Create database indexes on commonly queried foreign keys and date columns.

#### Tasks
*   **Task 12.1: Implement Dashboard Summary API Endpoint**
    *   *Objective:* Serve high-level dashboard parameters.
    *   *Description:* Create `/api/v1/dashboard/summary` combining current score, problems solved, repositories, and streaks.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 9.3, Task 3.2
    *   *Expected Deliverables:* Route handler and validation schemas.
    *   *Suggested Commit:* `feat(api): implement dashboard summary endpoint`
    *   *Acceptance Criteria:* Endpoint requires JWT auth and returns current developer metrics.
*   **Task 12.2: Implement Historical Charts APIs**
    *   *Objective:* Expose chronological data feeds for front-end charts.
    *   *Description:* Create `/api/v1/dashboard/charts` route outputting history snapshots for problems and commits.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 7.3
    *   *Expected Deliverables:* Chart response formatting schemas and route.
    *   *Suggested Commit:* `feat(api): implement historical charts endpoints`
    *   *Acceptance Criteria:* Endpoint yields daily arrays of commits and problems solved over selected intervals.
*   **Task 12.3: Implement Milestone Badges and Timeline Endpoints**
    *   *Objective:* Expose user history achievements.
    *   *Description:* Write DB models/migrations for `timeline_events` and `milestones` and expose `/api/v1/dashboard/timeline` and `/api/v1/dashboard/milestones` API routes.
    *   *Difficulty:* Hard
    *   *Dependencies:* Task 7.2, Task 1.4
    *   *Expected Deliverables:* Models, migrations, and routes.
    *   *Suggested Commit:* `feat(api): implement timeline and milestones endpoints`
    *   *Acceptance Criteria:* Returning milestones matches achievements (e.g. 100 problems solved) with user status.

---

### Phase 13: Background Synchronization Service (MVP)
*   **Objective:** Automate the fetch-parse-analyze-score-recommend cycle asynchronously.
*   **Deliverables:** APScheduler orchestration script, retry controllers, and synchronization status endpoints.
*   **Estimated Complexity:** Hard
*   **Dependencies:** Phase 5, Phase 6, and Phase 12 Completed
*   **Exit Criteria:** Background worker runs scheduled sync jobs and posts the status to local cache tables.
*   **Risk Assessment:**
    *   *Risk:* Background job crashes due to third-party connection drop and blocks subsequent runs.
    *   *Mitigation:* Wrap execution steps in try/catch and record failure status to `sync_jobs`.

#### Tasks
*   **Task 13.1: Integrate APScheduler in FastAPI Lifespan**
    *   *Objective:* Start/Stop scheduler along with web server.
    *   *Description:* Register APScheduler in FastAPI startup/shutdown lifespans using SQLAlchemy job store in `app/services/scheduler/manager.py`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Phase 1 Completed
    *   *Expected Deliverables:* Scheduler lifespan configurations.
    *   *Suggested Commit:* `feat(scheduler): integrate APScheduler with FastAPI lifespan`
    *   *Acceptance Criteria:* Scheduler initializes during app launch and stops gracefully on shutdown.
*   **Task 13.2: Implement Synchronizer Orchestrator Workflow**
    *   *Objective:* Coordinate the 9-step pipeline execution.
    *   *Description:* Write the master service function calling fetchers, database writers, analyzers, and engines in sequence in `app/services/scheduler/sync_job.py`.
    *   *Difficulty:* Hard
    *   *Dependencies:* Task 13.1, Task 5.2, Task 6.2, Task 8.3, Task 9.3, Task 10.3, Task 11.3
    *   *Expected Deliverables:* Execution orchestrator function.
    *   *Suggested Commit:* `feat(scheduler): implement master sync workflow orchestrator`
    *   *Acceptance Criteria:* Invoking the orchestrator successfully updates snapshots, history, scores, insights, and recommendations.
*   **Task 13.3: Add Sync Retries, Backoffs, and Error logging**
    *   *Objective:* Guarantee robustness of API synchronization.
    *   *Description:* Configure error catches, job retries with exponential backoffs, and log trace attachments.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 13.2
    *   *Expected Deliverables:* Error handling decorators.
    *   *Suggested Commit:* `feat(scheduler): configure job retry policies and error handling`
    *   *Acceptance Criteria:* Triggered errors log JSON trace statements and retry up to 3 times with delay intervals.
*   **Task 13.4: Implement Sync Status & Health APIs**
    *   *Objective:* Inform users about status of data freshness.
    *   *Description:* Write DB models/migrations for `sync_jobs` and expose `/api/v1/sync/status` returning details of last run.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 13.2, Task 1.4
    *   *Expected Deliverables:* Sync status database schema, models, and endpoints.
    *   *Suggested Commit:* `feat(api): implement synchronization status endpoints`
    *   *Acceptance Criteria:* Endpoint displays sync timestamps, durations, and state ("Healthy", "Degraded") for platforms.

---

### Phase 14: Weekly Reports (MVP)
*   **Objective:** Generate aggregated retrospective weekly summaries.
*   **Deliverables:** Weekly report generator scheduler job and REST APIs to fetch history reports.
*   **Estimated Complexity:** Medium
*   **Dependencies:** Phase 12 and Phase 13 Completed
*   **Exit Criteria:** Weekly summaries compiled and exposed to routes on-schedule.
*   **Risk Assessment:**
    *   *Risk:* Run overlaps or missed dates due to downtime.
    *   *Mitigation:* Write report logic that can be backfilled manually or checks for missing periods on launch.

#### Tasks
*   **Task 14.1: Create Weekly Report Database Model & Migration**
    *   *Objective:* Persist calculated weekly summaries.
    *   *Description:* Design `weekly_reports` table containing overall progress, score delta, and weak topics in `app/models/report.py`.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 13.4, Task 1.4
    *   *Expected Deliverables:* ORM model and migration.
    *   *Suggested Commit:* `feat(db): create weekly reports table and migration`
    *   *Acceptance Criteria:* Table supports string arrays and numeric deltas. Migration applied.
*   **Task 14.2: Implement Weekly Summary Aggregation Logic**
    *   *Objective:* Calculate weekly change logs.
    *   *Description:* Write functions reading the differences in histories over 7-day increments in `app/services/analytics/`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 14.1, Task 7.3
    *   *Expected Deliverables:* Reporting calculation functions.
    *   *Suggested Commit:* `feat(reports): implement weekly summary calculation logic`
    *   *Acceptance Criteria:* Calculations return correct deltas matching metrics over 7-day spans.
*   **Task 14.3: Implement Get Weekly Reports Endpoint**
    *   *Objective:* Retrieve reports.
    *   *Description:* Create `/api/v1/reports/weekly` route returning index of available reports and detailed payloads.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 14.2, Task 2.5
    *   *Expected Deliverables:* Route handler and output validation schemas.
    *   *Suggested Commit:* `feat(api): implement weekly reports REST endpoint`
    *   *Acceptance Criteria:* Endpoint requires JWT auth and yields correct list of historic weekly summaries.

---

## 🏁 Milestone 6: MVP Complete

### Phase 15: Frontend Dashboard (MVP)
*   **Objective:** Construct a React web application to consume backend APIs and present graphs, scores, and timelines.
*   **Deliverables:** React dashboard UI with charts, timeline feeds, authentication screens, and profile connect prompts.
*   **Estimated Complexity:** Hard
*   **Dependencies:** Phase 12, Phase 13, and Phase 14 Completed
*   **Exit Criteria:** React dashboard loads static views and dynamically renders all endpoint data.
*   **Risk Assessment:**
    *   *Risk:* CORS blocks backend request handling.
    *   *Mitigation:* Configure FastAPI `CORSMiddleware` in Phase 1 setup to allow specific origins.

#### Tasks
*   **Task 15.1: Initialize React Application & Asset Setup**
    *   *Objective:* Setup React code using Vite.
    *   *Description:* Create React app with Vite, configure vanilla CSS layout, and install charting/icon libraries (Recharts, Lucide).
    *   *Difficulty:* Easy
    *   *Dependencies:* Phase 12
    *   *Expected Deliverables:* React scaffold.
    *   *Suggested Commit:* `frontend: bootstrap React app using Vite`
    *   *Acceptance Criteria:* React app boots and hot-reloads locally with no console errors.
*   **Task 15.2: Build Login and Registration UI**
    *   *Objective:* Build screens capturing credentials.
    *   *Description:* Create sign up/login pages, configure API clients, and manage local storage of access tokens.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 15.1, Task 2.3, Task 2.4
    *   *Expected Deliverables:* Authentication page screens.
    *   *Suggested Commit:* `frontend: build login and registration pages`
    *   *Acceptance Criteria:* Logging in stores token and redirects user to main dashboard. Log out clears tokens.
*   **Task 15.3: Implement Dashboard Shell, Navigation, and Theme**
    *   *Objective:* Setup dashboard UI layout and dark mode styles.
    *   *Description:* Build sidebar, header, global state contexts, and main dashboard view wrappers.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 15.2
    *   *Expected Deliverables:* Core page shell structure.
    *   *Suggested Commit:* `frontend: construct dashboard shell and shell navigation`
    *   *Acceptance Criteria:* Sidebar navigation loads responsive page components cleanly.
*   **Task 15.4: Add Dashboard Summary Cards & Growth Charts**
    *   *Objective:* Render scores and histories.
    *   *Description:* Render score gauges, problem distributions (bar charts), and commit trends (area graphs) using Recharts.
    *   *Difficulty:* Hard
    *   *Dependencies:* Task 15.3, Task 12.1, Task 12.2
    *   *Expected Deliverables:* Visualization dashboard pages.
    *   *Suggested Commit:* `frontend: implement dashboard stats cards and charts`
    *   *Acceptance Criteria:* Charts dynamically render data points returned from backend endpoints.
*   **Task 15.5: Build Profile Setup & Platform Linking UI**
    *   *Objective:* Let users connect accounts.
    *   *Description:* Create forms validating handles, invoking connection APIs, and showing connection health states.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 15.3, Task 3.3, Task 13.4
    *   *Expected Deliverables:* Account settings screen.
    *   *Suggested Commit:* `frontend: build profile settings and platform connection page`
    *   *Acceptance Criteria:* Link configurations successfully execute connection endpoints and render platform statuses.
*   **Task 15.6: Implement Timeline, Milestones, and Recommendations Feeds**
    *   *Objective:* Visualize accomplishments and suggestions.
    *   *Description:* Fetch and display feeds for chronological timelines, milestone badge cards, and action recommendation lists.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 15.4, Task 12.3, Task 11.3
    *   *Expected Deliverables:* Feed cards UI components.
    *   *Suggested Commit:* `frontend: implement timeline, milestones, and recommendations`
    *   *Acceptance Criteria:* Milestone lists and recommendation feeds render dynamically based on user state.

---

### Phase 16: Testing Strategy (Post-MVP)
*   **Objective:** Write test suites verifying business logic, API security, and database transactions.
*   **Deliverables:** Integrated pytest fixtures, mocked HTTP client services, and endpoint test coverage reports.
*   **Estimated Complexity:** Medium
*   **Dependencies:** Phase 14 Completed
*   **Exit Criteria:** Backend achieves a minimum of 80% test coverage with zero failing tests.
*   **Risk Assessment:**
    *   *Risk:* External API mocks fail or expire.
    *   *Mitigation:* Use static json file mock fixtures for mock payloads.

#### Tasks
*   **Task 16.1: Configure Pytest Environment and Fixtures**
    *   *Objective:* Initialize testing library.
    *   *Description:* Install pytest, write async database session configurations, and initialize mock databases in `tests/conftest.py`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Phase 14
    *   *Expected Deliverables:* Pytest configuration file.
    *   *Suggested Commit:* `test: configure pytest framework and database fixtures`
    *   *Acceptance Criteria:* Running `pytest` successfully completes a dummy test pass.
*   **Task 16.2: Write Unit Tests for Scoring & Recommendation Engines**
    *   *Objective:* Validate calculators mathematically.
    *   *Description:* Write tests passing various inputs to calculator logic to check correct scoring weights and thresholds in `tests/services/`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 16.1, Task 9.1, Task 11.1
    *   *Expected Deliverables:* Analytics logic unit tests.
    *   *Suggested Commit:* `test: implement unit tests for scoring and recommendation rules`
    *   *Acceptance Criteria:* Tests assert math computations are precise and corner cases handled correctly.
*   **Task 16.3: Write Integration Tests for APIs**
    *   *Objective:* Validate route security and response contents.
    *   *Description:* Use FastAPI TestClient to test authentication headers, registrations, profiles, and error statuses in `tests/api/`.
    *   *Difficulty:* Medium
    *   *Dependencies:* Task 16.2
    *   *Expected Deliverables:* API Endpoint integration tests.
    *   *Suggested Commit:* `test: implement REST API endpoint integration tests`
    *   *Acceptance Criteria:* Endpoint queries verify token validations, schema formats, and database side effects.

---

### Phase 17: Documentation & Guides (MVP & Post-MVP)
*   **Objective:** Supply guides for running, deploying, and extending DevTrack.
*   **Deliverables:** Final deployment setup parameters, installation guidelines, and database maps.
*   **Estimated Complexity:** Low
*   **Dependencies:** None (Incremental writes)
*   **Exit Criteria:** Project repository contains a complete README, schema map, and deployment guidelines.
*   **Risk Assessment:**
    *   *Risk:* Setup instructions quickly become out of date.
    *   *Mitigation:* Run through instructions on a fresh local terminal to verify accuracy.

#### Tasks
*   **Task 17.1: Compile Installation & Execution Guide (MVP)**
    *   *Objective:* Step-by-step setup guides in README.md.
    *   *Description:* Outline virtual environment setup, seed commands, local database creation, and run commands.
    *   *Difficulty:* Easy
    *   *Dependencies:* None
    *   *Expected Deliverables:* Setup instructions in project root README.
    *   *Suggested Commit:* `docs: update README with installation and execution guides`
    *   *Acceptance Criteria:* Fresh local setups can be completed using only instructions from README.
*   **Task 17.2: Create Database ERD and Schema Description (MVP)**
    *   *Objective:* Map schemas.
    *   *Description:* Document relations, indexing targets, and column tables in `docs/architecture/DATABASE_DESIGN.md`.
    *   *Difficulty:* Easy
    *   *Dependencies:* Task 0.4
    *   *Expected Deliverables:* DB architecture document.
    *   *Suggested Commit:* `docs: write database schema description guide`
    *   *Acceptance Criteria:* Guide outlines every database table, foreign key, index rationale, and data type.
*   **Task 17.3: Document Production Deployment Steps (Post-MVP)**
    *   *Objective:* VPS hosting parameters.
    *   *Description:* Detail environment configurations, reverse proxies (Nginx), and database parameters in `docs/design/DEPLOYMENT.md`.
    *   *Difficulty:* Easy
    *   *Dependencies:* Phase 15
    *   *Expected Deliverables:* Production deployment guide.
    *   *Suggested Commit:* `docs: compile production deployment instructions`
    *   *Acceptance Criteria:* Guide contains production config parameters and checklist.

---

## 🛡 Git Workflow
For every task in the roadmap, we must follow this workflow strictly:
1.  **Implement one task only.**
2.  **Test the implementation** to ensure it is functional and meets the task objective.
3.  **Update documentation** (like progress logs) as needed.
4.  **Recommend a Git commit message** in the chat.
5.  **Commit the changes** using the recommended message.
6.  **Wait for approval** from the mentor/user before starting the next task.

*Never combine multiple tasks into a single commit.*

---

## 📏 Definition of Done (DoD)
A task is considered complete only when:
- [ ] The code is fully implemented according to the task description.
- [ ] The code functionality is explained to the user.
- [ ] API documentation is updated and endpoints display in Swagger `/docs` (if applicable).
- [ ] No linting, formatting, or syntax errors exist in the codebase.
- [ ] Relevant test files are executed and pass (where applicable).
- [ ] The suggested Git commit message is provided.
- [ ] Tracking documents (`PROJECT_PROGRESS.md`, `TASKS.md`) are updated.

---

## 📜 Documentation Update Policy
Immediately after completing any task:
1.  Update the progress tracker `PROJECT_PROGRESS.md` in the workspace.
2.  Mark tasks as completed in `TASKS.md` or similar task-tracking files.
3.  Document any changes to database schemas or endpoint configurations in their respective markdown documents.
4.  Present a Git commit message recommendation in the chat.
5.  **Stop and wait for user approval** before proceeding to any subsequent tasks.

---

## 🎯 MVP Focus Guarantee
To ensure we build a lean, production-grade MVP on schedule, we will not write any code or configure infrastructure for the following future enhancements during this roadmap:
*   No Redis caching setups (PostgreSQL database handles initial reads).
*   No Docker files or container orchestrations (Local Python virtual envs).
*   No Celery worker engines or Redis brokers (APScheduler runs in-process).
*   No CI/CD pipeline automations.
*   No Kubernetes deployment parameters.
*   No external OAuth integrations (Username connections only).
*   No AI analytics or ML models (Rule-based engines only).
*   No extra platforms (HackerRank, Codeforces) until LeetCode/GitHub syncs run securely.
