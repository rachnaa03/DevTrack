# Software Requirements Specification (SRS)
## Project: DevTrack (Unified Developer Analytics Platform)
**Version:** 1.0.0  
**Status:** Approved  
**Date:** August 3, 2026  
**Prepared By:** Rachana Gandla  

---

## 1. Introduction

### 1.1 Purpose
This document specifies the software requirements for the first version (MVP) of DevTrack. It outlines the functional and non-functional requirements, system constraints, and design justifications to align the development team and stakeholders before implementation.

### 1.2 Scope
DevTrack is a unified developer analytics platform that aggregates, stores, and analyzes developer activity from GitHub and LeetCode. The backend will:
1. Periodically fetch and cache activity data from GitHub and LeetCode.
2. Maintain historical snapshots of user progress.
3. Compute a custom developer growth score (Developer Score).
4. Generate actionable, rule-based recommendations and insights.
5. Provide secure REST APIs to power a responsive React dashboard.

### 1.3 Definitions, Acronyms, and Abbreviations
*   **JWT (JSON Web Token):** A compact, URL-safe means of representing claims to be transferred between two parties.
*   **ORM (Object-Relational Mapping):** A programming technique for converting data between incompatible type systems in databases and object-oriented programming languages.
*   **MVP (Minimum Viable Product):** A version of a product with just enough features to be usable by early customers who can then provide feedback.
*   **ACID:** Atomicity, Consistency, Isolation, Durability (database properties).
*   **Developer Score:** A proprietary weighted score combining open-source contribution metrics and algorithmic problem-solving capabilities.

### 1.4 Project Philosophy
DevTrack is not intended to be just another statistics dashboard. Its purpose is to transform fragmented developer activity into a unified developer profile that provides measurable growth, actionable insights, and continuous feedback.

---

## 2. Overall Description

### 2.1 Product Perspective
DevTrack serves as a centralized companion for developers. Instead of developers checking multiple platform profiles (like GitHub contributions and LeetCode stats) in isolation, DevTrack brings them together under a single dashboard, mapping daily coding habits to long-term career growth.

```
+-------------------------------------------------------------+
|                        DevTrack Web App                     |
+------------------------------+------------------------------+
                               | (HTTPS REST APIs / JWT)
                               v
+-------------------------------------------------------------+
|                      FastAPI Backend Engine                 |
+-------------------------------------------------------------+
   | (Sync / Scheduler)                                  | (ORM)
   v                                                     v
+------------------------+                     +---------------+
| GitHub & LeetCode APIs |                     | PostgreSQL DB |
+------------------------+                     +---------------+
```

### 2.2 Product Functions (MVP Scope)
*   **User Management:** Register, login, and update profile information.
*   **Third-Party Credentials:** Securely save public handles for GitHub and LeetCode.
*   **Background Fetching:** Retrieve profile info, repositories, commits, and problem-solving statistics without blocking user actions.
*   **Analytics Calculation:** Parse raw data to extract patterns (e.g., language distribution, problem difficulty, streaks).
*   **Scoring:** Run algorithms to determine the Developer Score.
*   **Recommendations:** Consume analytics output to generate personalized practice suggestions.
*   **Interactive History:** Expose timeline milestones and weekly progress reports.

### 2.3 User Classes and Characteristics
*   **Developers (End Users):** Range from junior developers/students looking to build consistent habits to senior developers tracking their open-source contributions and algorithmic progress.
*   **Administrators (Internal):** Monitor system health, rate limit usage, and synchronize jobs manually if necessary.

### 2.4 Design and Implementation Constraints
*   **Python 3.11+:** The backend must be written in modern Python.
*   **FastAPI:** Chosen for its performance, asynchronous support, and automatic OpenAPI generation.
*   **PostgreSQL:** Must be used for persistent transactional data.
*   **API Rate Limits:** The background service must respect GitHub and LeetCode API limits.

### 2.5 Assumptions
*   Users own valid public GitHub and LeetCode accounts.
*   GitHub and LeetCode APIs remain available.
*   Internet connectivity is available during synchronization.
*   Historical snapshots are collected periodically.
*   Users provide correct usernames.

### 2.6 Constraints
*   MVP supports only GitHub and LeetCode.
*   Only public data will be synchronized.
*   Developer Score is rule-based, not machine learning.
*   Synchronization is periodic, not real-time.
*   Mobile applications are outside the MVP scope.

---

## 3. System Features (Functional Requirements)

### 3.1 Authentication & User Management
*   **FR-1.1 (Register):** Users must be able to create an account using an email, username, and password.
*   **FR-1.2 (Login):** Users must be authenticated using their credentials, returning a JWT access token (short-lived) and a refresh token (long-lived).
*   **FR-1.3 (Secure Endpoints):** All data-fetching and profile endpoints must require a valid JWT in the HTTP Authorization header.
*   **FR-1.4 (Account Linkage):** Users must be able to add/update their public GitHub and LeetCode usernames in their profile.

### 3.2 GitHub Data Integration & Synchronization
*   **FR-2.1 (Profile Metadata):** Fetch user bio, avatar, public repository count, star count, and followers.
*   **FR-2.2 (Repository Stats):** Fetch list of public repositories including stars, forks, primary programming languages, and creation dates.
*   **FR-2.3 (Commit Activity):** Fetch commit frequency history across public repositories for the past 12 months.

### 3.3 LeetCode Data Integration & Synchronization
*   **FR-3.1 (Solved Problems):** Fetch count of problems solved broken down by difficulty (Easy, Medium, Hard).
*   **FR-3.2 (Submissions):** Fetch recent submissions, acceptance rates, and current active streak.
*   **FR-3.3 (Contest & Badges):** Retrieve contest ranking, contest rating, and earned profile badges.
*   **FR-3.4 (Topic Mastery):** Fetch number of problems solved categorized by topic tags (e.g., Dynamic Programming, Graphs, Arrays).

### 3.4 Developer Analytics Engine
The Developer Analytics Engine is responsible for translating raw, unstructured snapshots into structured, calculated analytics. It consists of the following internal components:
*   **GitHub Analyzer:** Parses raw repository stats and commit data. It calculates repository growth, identifies the user's most active and starred repositories, details the programming language distribution, computes commit frequency, and measures contribution streak lengths.
*   **LeetCode Analyzer:** Evaluates LeetCode snapshot data. It calculates the difficulty distribution (Easy/Medium/Hard ratios), tracks topic-wise progress (e.g., number of trees vs. graphs solved), monitors contest performance over time, calculates submission consistency trends, and computes average problems solved per day alongside streak details.
*   **Score Engine:** Calculates the custom, rule-based **Developer Score** (out of 1000) using a weighted evaluation model:
    *   *Coding Consistency (30%):* Based on LeetCode streak and commit history.
    *   *Problem-Solving Depth (35%):* Evaluates Medium/Hard problems ratios and contest rating.
    *   *Open Source Impact (35%):* Evaluates repository stars, fork count, repository volume, and commit depth.
*   **Insights Engine:** Compares the newly generated analytics snapshot with past historical snapshots to generate text-based comparative insights (e.g., "Your Dynamic Programming practice dropped by 20% compared to last week" or "You solved 15 more Medium problems than last month").

These components operate sequentially. First, the GitHub and LeetCode Analyzers parse the raw data. Then, the Score Engine and Insights Engine use these structured analyses to compute scores and compare metrics. The final computed data models are saved to the database.

### 3.5 Recommendation Engine
The Recommendation Engine is a separate functional module dependent on the output of the Developer Analytics Engine.
*   **FR-5.1 (Rule-Based Recommendations):** Consumes the generated scores, weak topic counts (from the LeetCode Analyzer), and consistency indicators (from the GitHub/LeetCode Analyzers) to produce personalized, actionable recommendations (e.g., "Practice Graphs to balance your algorithm skills" or "Solve 5 more Medium problems to increase your Developer Score").
*   **Dependency Rationale:** By decoupling Recommendations from Analytics, the engine can be modified, A/B tested, or upgraded to machine learning in the future without affecting the core analytics parsing pipeline.

### 3.6 Timeline & Milestones
*   **FR-6.1 (Timeline Generation):** Generate chronological events (e.g., "Linked LeetCode Account on Aug 3", "First Repository Created on Jan 14, 2023").
*   **FR-6.2 (Milestone Badges):** Award achievements (e.g., "100 LeetCode Problems", "First Hard Problem", "50 commits in a month").

### 3.7 Background Synchronization Service
*   **FR-7.1 (Automated Fetch):** Run background tasks at regular intervals (e.g., twice daily) to sync all users.
*   **FR-7.2 (Asynchronous Sync Workflow):** To ensure optimal responsiveness of the REST API, synchronization runs completely out-of-band using the following workflow:
    ```
    [Scheduler Trigger]
            │
            ▼
    [Fetch Latest Platform Data] (GitHub & LeetCode APIs)
            │
            ▼
    [Validate Response Data] (Check schema completeness)
            │
            ▼
    [Store Historical Snapshot] (Immutable DB insert)
            │
            ▼
    [Run Analytics Engine] (GitHub & LeetCode Analyzers)
            │
            ▼
    [Recalculate Developer Score] (Score Engine execution)
            │
            ▼
    [Generate Insights] (Compare snapshots via Insights Engine)
            │
            ▼
    [Generate Recommendations] (Recommendation Engine execution)
            │
            ▼
    [Refresh Dashboard Cache] (Update read-optimized cache tables)
    ```
*   **Rationale:** Querying third-party APIs during a frontend request causes high latency and quickly triggers external rate limits. Running this pipeline asynchronously guarantees that dashboard endpoints serve pre-calculated, read-optimized data in milliseconds.

---

## 4. Non-Functional Requirements

### 4.1 Performance & Scalability
*   **NFR-1.1 (Latency):** All REST APIs must respond in under 200ms (excluding external API synchronizations, which are handled in the background).
*   **NFR-1.2 (API Decoupling):** API queries must read from the PostgreSQL cache, never making real-time calls to third-party endpoints during user page loads.
*   **NFR-1.3 (Rate-Limit Resiliency):** Background jobs must implement exponential backoff when encountering API rate limits from GitHub or LeetCode.

### 4.2 Security & Compliance
*   **NFR-2.1 (Data Protection):** Passwords must be hashed using `bcrypt` before database storage.
*   **NFR-2.2 (Token Security):** JWTs must be signed using `HS256` or `RS256` with environment-injected secret keys. Refresh tokens must be stored securely.
*   **NFR-2.3 (Public Data Only):** The platform will initially only fetch public data (public repositories, public LeetCode stats) to avoid requiring OAuth write-tokens or sensitive access scopes.

### 4.3 Maintainability & Reliability
*   **NFR-3.1 (Error Tracking):** Backend must implement structured JSON logging with request IDs to track transaction paths.
*   **NFR-3.2 (Test Coverage):** Business logic (Scoring, Recommendations) must maintain a minimum of 80% unit test coverage.
*   **NFR-3.3 (Extensibility):** Platform interfaces must be defined as abstract base classes (`BasePlatformClient`) so that Codeforces or HackerRank can be added later with minimal modification to the sync service.

---

## 5. Architecture Goals & Design Principles

To ensure DevTrack is built to production standards, the backend architecture adheres to these core goals:

*   **Scalability:** The read paths and write paths (data ingestion) are completely separated. APIs serve reads from the database instantly, while ingestion happens asynchronously in background workers.
*   **Maintainability:** By structuring the backend using layered architecture (Controller -> Service -> Repository), components are isolated, making the system easier to debug and refactor.
*   **Modularity:** Features are isolated into domains (User, Sync, Analytics, Recommendation).
*   **API-First Design:** All business logic is exposed through uniform REST APIs. The React dashboard, future mobile apps, or browser extensions will consume the same endpoints, ensuring consistency and preventing logic duplication.
*   **Separation of Concerns:** The API web layer handles HTTP requests and authentication, the Service layer coordinates transactions, the Analytics Engine performs computations, and the Repository layer handles raw SQL/ORM interactions.
*   **Extensibility:** Third-party integrations are abstracted behind platform adapters. Adding a new platform like Codeforces requires writing a new adapter subclass without changing the synchronization scheduling pipeline.
*   **Reliability:** Background jobs run independently. A failure in LeetCode’s API synchronization will not prevent the rest of the application or the GitHub synchronization from operating normally.
*   **Testability:** Since the Analytics and Scoring Engines are isolated from database and web frameworks, they can be tested using mock inputs with pure Python unit tests.

---

## 6. Database Design Philosophy

DevTrack's database layout is designed with these key principles:
*   **Single Source of Truth:** PostgreSQL is the definitive source of truth for all user profiles, calculated analytics, historical snapshots, and scores.
*   **Snapshot Immutability:** Historical snapshots are treated as immutable log entries. Once a snapshot is recorded for a day or sync cycle, it is never modified. This preserves precise developer history for long-term analytics.
*   **Read/Write Decoupling:** Dashboard APIs read directly from structured local cache tables, avoiding real-time third-party network fetches.
*   **Asynchronous Updates:** Write operations (like sync jobs) append new snapshots and compute updated stats asynchronously, ensuring read operations remain entirely lock-free.

---

## 7. Risks and Mitigation

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **GitHub API Rate Limits** | High | Minimize fetches by checking cache headers, perform incremental queries, and implement exponential backoff retry patterns in the background worker. |
| **LeetCode API Schema Changes** | High | Since LeetCode uses an unofficial GraphQL API, schema shifts can break queries. We encapsulate LeetCode queries inside a dedicated client class, ensuring updates are confined to a single file. |
| **Temporary Sync Failures** | Medium | Implement retry mechanisms with limit thresholds. If a sync fails, the user is served their last successfully cached data, and the synchronization status is updated to "Degraded/Failed". |
| **Network Interruptions** | Medium | Wrap sync tasks in robust try-except blocks. Log errors with detailed traces and trace-ids to standard error streams without crashing the API process. |
| **Invalid Usernames** | Low | Perform a lightweight check of the username (e.g. ping the profile URL) during the account connection phase. Reject invalid profiles immediately. |

---

## 8. Success Criteria

The DevTrack MVP will be considered successful when:
1.  **Successful Platform Connection:** A user can input valid GitHub and LeetCode usernames and see them successfully linked to their profile.
2.  **Autonomous Synchronization:** The background service schedules, fetches, and parses user data without manual administrator intervention.
3.  **Low Latency Reads:** Dashboard APIs return profile and score metrics in under 200ms under ordinary network load.
4.  **Accurate Scoring:** The Score Engine successfully evaluates and outputs a score out of 1000 based on the configured rules.
5.  **Growth Tracking:** Historical snapshot data is created at the scheduled interval, allowing the API to return historical scoring progress.
6.  **Actionable Feedback:** The Recommendation Engine generates at least three relevant recommendations when a user's score or topic distributions show weak areas.
7.  **Weekly Report Generation:** Weekly reports summarize commits, problems solved, and growth delta, and are rendered in the dashboard.

---

## 9. Architectural Design Decisions & Rationale

1.  **Pull-based Background Workers vs. Real-Time/Push Sync:**
    *   *Decision:* We synchronize user profiles using background tasks and read from our database cache when serving endpoints.
    *   *Rationale:* LeetCode does not support webhooks (push-based sync). Additionally, users connect public GitHub accounts where they might not be repository administrators, preventing us from installing webhooks. Polling in real-time during web requests would make the React dashboard feel slow and run us into API rate limits.
2.  **State Snapshotting vs. Aggregate Counters:**
    *   *Decision:* We store distinct historical snapshot records (e.g., daily snapshots of problems solved and commit counts) instead of just updating a single user stats record.
    *   *Rationale:* Storing historical snapshots is the only way we can construct growth charts (e.g., "LeetCode progress over 6 months") and generate retrospective weekly reports without integrating heavy time-series databases at this stage.
3.  **Third-Party API Auth Scopes (Username-only vs. OAuth token):**
    *   *Decision:* The MVP will rely on users entering their public usernames. No password/OAuth tokens are required for LeetCode or GitHub public data.
    *   *Rationale:* Minimizes the security liability on our backend. Asking users for full GitHub OAuth tokens or LeetCode passwords creates high user friction and security risks. Public APIs allow us to fetch all the required data for our MVP metrics securely.
