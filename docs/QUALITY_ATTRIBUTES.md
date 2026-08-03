# Quality Attributes Specification
**Version:** 1.0.0  
**Status:** Approved  
**Prepared By:** Rachana Gandla  

This document specifies the non-functional quality attributes (architectural -ilities) of the DevTrack system and how they are achieved in the MVP design.

---

## 1. Performance
*   **Target Latency:** All GET requests (dashboard summaries, historical charts, user profile data) must respond in **under 200ms** under normal server load.
*   **How it is achieved:**
    *   **Asynchronous Processing:** Network-I/O bound sync tasks are offloaded to background threads. The API reads data directly from the local PostgreSQL database, eliminating real-time API calls.
    *   **Query Index Seeks:** Crucial read queries target database columns optimized with custom B-Tree indexes (see [DATABASE_INDEXING.md](file:///D:/workspace/DevTrack/docs/DATABASE_INDEXING.md)).

---

## 2. Scalability
*   **Decoupled Read/Write Paths:** The system isolates intensive write workloads (sync jobs, score evaluations) from read workloads (REST API endpoints). This separation prevents data writes from blocking dashboard reads.
*   **Caching Readiness:** The API-first design and decoupled repository pattern allow us to insert a Redis caching layer without modifying backend business logic or database schemas.

---

## 3. Security
*   **Stateless Authentication:** Secure routes require JSON Web Tokens (JWT) signed with `HS256` using secret keys loaded from environment variables.
*   **Data Protection:**
    *   Passwords are hashed using `bcrypt` before database storage. Raw passwords are never stored.
    *   API response schemas (Pydantic models) explicitly serialize output fields, preventing sensitive fields (such as hashed passwords or system IDs) from escaping the API boundaries.
    *   No write-access API tokens are requested from users. We only request public platform usernames, eliminating authentication liabilities.

---

## 4. Reliability
*   **Graceful Degradation:** If a background sync job to LeetCode fails due to network downtime:
    *   The worker records a "Degraded" status in the database.
    *   The user is served their last successfully cached snapshot.
    *   The application continues operating normally for the user and other platforms.
*   **Retry Mechanisms:** External client requests implement retries with exponential backoffs (up to 3 attempts) to handle temporary network issues.

---

## 5. Maintainability & Extensibility
*   **Layer Separation:** The codebase strictly divides controllers (`api/`), business services (`services/`), and data storage repositories (`repositories/`). Changing the database schema only requires editing repository files, leaving API routers untouched.
*   **Adapter Pattern:** Integration client classes inherit from a standard abstract base client (`BasePlatformClient`). This structure allows new coding platforms (such as Codeforces or CodeChef) to be added with minimal changes.

---

## 6. Testability
*   **Decoupled Logic:** The Score Engine and Recommendation rules are designed as pure Python service modules. They contain no direct database queries or web routing dependencies, allowing them to be fully unit tested using basic mock inputs.
*   **Standard Framework:** The system is pre-configured to run automated tests using `pytest` and mock external responses using `pytest-mock` or `responses`.

---

## 7. Observability
*   **Structured JSON Logging:** All log outputs are written as structured JSON lines. Each log records timestamp, level, message, and a unique `request_id` generated per HTTP request or background task.
*   **Sync Monitor API:** The endpoint `/api/v1/sync/status` exposes synchronization metrics (last execution timestamp, duration, error details) to check system health.
