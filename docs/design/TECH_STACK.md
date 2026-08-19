# Technology Stack Specification
## Project: DevTrack (Unified Developer Analytics Platform)
**Version:** 1.0.0  
**Status:** Approved  
**Prepared By:** Rachana Gandla  

---

## 1. Backend Framework: FastAPI
*   **Why it was chosen:**
    *   **Performance:** FastAPI is built on Starlette and Uvicorn, placing it among the fastest Python web frameworks available.
    *   **Asynchronous Support:** Built-in native support for `async`/`await` enables concurrency-friendly external API integrations and non-blocking database queries.
    *   **Data Validation:** Deep integration with Pydantic ensures inputs/outputs are validated at runtime with auto-generated schemas.
    *   **Interactive Documentation:** Generates interactive Swagger UI and ReDoc pages automatically.
*   **Decision Record: Why FastAPI instead of Flask?**
    *   *Flask* is highly extensible but operates synchronously. Handling periodic concurrent outgoing API requests to GitHub and LeetCode would require complex multi-threading setups in Flask. Additionally, Flask has no built-in data validation (requiring manual integration of marshmallow/apispec) and lacks native automatic OpenAPI documentation generation. FastAPI provides all of this out-of-the-box with superior speed.

---

## 2. Programming Language: Python 3.11+
*   **Why it fits this project:**
    *   **Data Processing Capabilities:** Python is the industry standard for data manipulation, analytics, and string parsing. Writing analyzers (parsing JSON arrays of commits, scoring algorithms, and string insights) is highly expressive and clean in Python.
    *   **Ecosystem:** Rich ecosystem of packages for HTTP connections (`httpx`, `requests`), scheduling (`apscheduler`), and cryptographic hashing (`bcrypt`).

---

## 3. Database: PostgreSQL
*   **Why it was chosen:**
    *   **Production Reliability:** PostgreSQL is a highly robust, open-source object-relational database with excellent compliance to SQL standards.
    *   **JSONB Support:** PostgreSQL natively supports JSONB (binary JSON). This is highly useful for DevTrack because we can store the raw, semi-structured responses from GitHub and LeetCode as backups inside snapshot tables while parsing structured fields out into standard relational tables.
*   **Decision Record: Why PostgreSQL instead of SQLite?**
    *   *SQLite* is excellent for lightweight local testing, but it lacks concurrency and lock-free writes. When the background sync worker is writing snapshots, SQLite's database-level locking can cause API read queries to block or time out. PostgreSQL supports multi-version concurrency control (MVCC), allowing simultaneous background writes and API reads without locking.

---

## 4. ORM: SQLAlchemy (v2.0+)
*   **Why it was chosen:**
    *   **Industry Standard:** SQLAlchemy is the most mature and feature-rich ORM in the Python ecosystem.
    *   **Async Driver Support:** Fully supports asynchronous operations via async database drivers like `asyncpg`.
    *   **SQLAlchemy 2.0 Syntax:** Promotes strong PEP-484 typing and clear declarative models, reducing common runtime type errors.
*   **Decision Record: Why SQLAlchemy instead of SQLModel?**
    *   *SQLModel* is a wrapper that combines SQLAlchemy and Pydantic. While it simplifies basic CRUD apps by using a single class for both database models and API schemas, it lacks maturity, has slow release cycles, and makes advanced SQLAlchemy configurations (like hybrid attributes, complex relationship mappings, and advanced async joins) difficult. In a production-quality application, enforcing a strict separation of concern between database persistence models (SQLAlchemy) and API request/response schemas (Pydantic) is a cleaner architectural practice.

---

## 5. Database Migrations: Alembic
*   **Purpose:**
    *   **Database Version Control:** Alembic tracks all database schema changes over time as incremental migration scripts.
    *   **Production Safety:** It allows us to apply schema changes (adding new columns for third-party platforms, altering indexes) in production in a structured, transactional, and reversible manner, ensuring we never lose historical snapshot data.

---

## 6. Authentication: JWT & Password Hashing
*   **JWT (JSON Web Token):**
    *   Used for stateless, secure user sessions.
    *   Token payload contains the user ID, issue timestamp, and expiration time. Signed using `HS256` with a server-side secret key.
*   **Password Hashing:**
    *   Passwords will be hashed using native `bcrypt` before saving to PostgreSQL. Raw passwords are never stored.
*   **Authentication Flow:**
    ```
    [Frontend]                        [FastAPI Backend]                [PostgreSQL]
        │                                    │                              │
        │─── 1. Login (Email + Password) ───>│                              │
        │                                    │─── 2. Query Hash ───────────>│
        │                                    │<── 3. Return Hash ───────────│
        │                                    │                              │
        │                                    │─── 4. Verify Password        │
        │                                    │    (Match verified)          │
        │                                    │                              │
        │                                    │─── 5. Sign JWTs              │
        │                                    │    (Access & Refresh)        │
        │<── 6. Return Access + Refresh ─────│                              │
        │                                    │                              │
        │                                    │                              │
        │─── 7. API Call (Bearer Token) ────>│                              │
        │                                    │─── 8. Validate JWT Signature │
        │<── 9. Return Protected Data ───────│                              │
    ```

---

## 7. Data Validation: Pydantic (v2.0+)
*   **Purpose:**
    *   Used at the boundaries of our backend application.
    *   Validates incoming JSON payloads (e.g., registration body) and ensures they conform to explicit Python types, formats, and rules before reaching business logic.
    *   Serializes database models into clean JSON schemas for API output, filtering out sensitive properties like password hashes.

---

## 8. Background Jobs: APScheduler
*   **Why it is sufficient for the MVP:**
    *   **Low Operational Complexity:** APScheduler runs directly in-process alongside the FastAPI web application, using the same Python runtime. It does not require setting up and paying for additional message broker servers or background system daemons.
    *   **PostgreSQL Job Store:** APScheduler can use PostgreSQL as its persistent job store. If the web server restarts, scheduled sync runs are not lost.
*   **Decision Record: Why APScheduler instead of Celery?**
    *   *Celery* is a heavy-duty distributed task queue that requires a dedicated message broker (like Redis or RabbitMQ) and separate worker processes running on the host. This introduces significant operational overhead, deployment complexity, and increased infrastructure cost. For our MVP with low initial concurrency needs, APScheduler’s in-process runner is lightweight and sufficient, while storing task data in PostgreSQL makes migrating to Celery later a simple task.

---

## 9. API Documentation: Swagger / OpenAPI
*   **Purpose:**
    *   Provides an interactive sandbox (at `/docs`) where we can test our API endpoints manually.
    *   Acts as a living API specification contract between the backend and frontend, eliminating the need to update external Postman collections or static documentation websites manually.

---

## 10. Logging: Structured JSON Logging
*   **Purpose:**
    *   Replaces basic string logs with structured format output (JSON).
    *   Each log line contains contextual metadata (timestamp, log level, endpoint path, unique `request_id`).
    *   Allows for easy indexing, searching, and troubleshooting in production log aggregates.

---

## 11. Frontend Framework: React (Lightweight MVP)
*   **Purpose:**
    *   A high-performance library for building interactive user dashboards.
    *   **Strict Decoupling:** The React frontend acts purely as a consumption client. It fetches data asynchronously via HTTP endpoints, stores state in memory, and visualizes stats using a charting library (like Recharts). It contains zero backend, database, or sync business logic.
*   **Decision Record: Why React instead of Next.js?**
    *   *Next.js* is a full-stack meta-framework designed for server-side rendering (SSR) and combined client-server compilation. Since we are building a dedicated backend API with FastAPI, using Next.js would add redundant server routing layers, increase hosting complexity, and raise resource usage. A standard, lightweight client-side React app (scaffolded via Vite) can be built as static assets and hosted cheaply on a CDN (Netlify/Vercel/S3), maintaining a clean API-first separation.

---

## 12. Project Folder Structure
DevTrack will follow a modular, domain-driven structure within a layered design:

```
DevTrack/
│
├── app/                        # Application Source Code
│   ├── api/                    # HTTP Endpoints & Route Handlers
│   │   ├── auth/               # Signup, Login, Password Refresh Routes
│   │   ├── profile/            # Profile Get/Update and Platform Linkage Routes
│   │   ├── dashboard/          # Summary, Charts, Timeline, Milestones Routes
│   │   └── reports/            # Weekly Progress Reports Routes
│   │
│   ├── core/                   # Shared Configuration & Infrastructure
│   │   ├── config.py           # Pydantic Settings & Env Variable Loading
│   │   ├── database.py         # SQLAlchemy Async Engine & Session Setup
│   │   ├── security.py         # JWT Token Signing & Password Hashing
│   │   └── logging.py          # Structured JSON Logger Configuration
│   │
│   ├── models/                 # SQLAlchemy DB Persistence Models
│   │   ├── user.py             # User and Profile Entities
│   │   ├── snapshot.py         # Raw JSON Snapshots (GitHub & LeetCode)
│   │   ├── history.py          # Tabular Historical Progress logs
│   │   ├── score.py            # Computed Developer Scores
│   │   ├── insight.py          # Text-based comparative logs
│   │   ├── recommendation.py   # Actionable developer recommendations
│   │   └── report.py           # Weekly report summaries
│   │
│   ├── schemas/                # Pydantic Request/Response validation schemas
│   │   ├── auth.py             # Registration/Login schemas
│   │   ├── profile.py          # Profile response serialization schemas
│   │   └── dashboard.py        # Dashboard summary and chart payload definitions
│   │
│   ├── repositories/           # Database Query layer (CRUD abstractions)
│   │   ├── user_repo.py        # User/Profile DB queries
│   │   ├── snapshot_repo.py    # Snapshot persistence queries
│   │   └── score_repo.py       # Scoring history queries
│   │
│   ├── services/               # Core Business Logic & Orchestrations
│   │   ├── integrations/       # Platform Adapters (GitHub/LeetCode clients)
│   │   ├── analytics/          # Data parsing & trend extraction
│   │   ├── scoring/            # Weighted score calculations
│   │   ├── insights/           # Snapshot comparisons and alerts
│   │   ├── recommendations/    # Rule-based suggestions engine
│   │   └── scheduler/          # APScheduler background tasks
│   │
│   └── utils/                  # Shared Utility helpers
│       ├── datetime_utils.py   # Timezone-aware date parsing helpers
│       └── string_utils.py     # String sanitation helpers
│
├── tests/                      # Testing Suite (Pytest)
│   ├── conftest.py             # Test Fixtures & Mock DB sessions
│   ├── api/                    # Route security and response tests
│   └── services/               # Scoring & recommendation unit tests
│
├── docs/                       # Project Design and Requirements Docs
│   ├── architecture/           # System Architecture & Technical Specifications
│   │   ├── ARCHITECTURE.md
│   │   ├── DOMAIN_MODEL.md
│   │   ├── DATABASE_DESIGN.md
│   │   ├── DATABASE_INDEXING.md
│   │   ├── FUTURE_ARCHITECTURE.md
│   │   └── QUALITY_ATTRIBUTES.md
│   ├── design/                 # Requirements & Functional Specifications
│   │   ├── SRS.md
│   │   ├── TECH_STACK.md
│   │   ├── IMPLEMENTATION_ROADMAP.md
│   │   ├── CONFIGURATION.md
│   │   ├── CODING_STANDARDS.md
│   │   ├── ERROR_HANDLING.md
│   │   └── API_SPECIFICATION.md
│   ├── adr/                    # Architectural Decision Records
│   │   ├── 001-fastapi.md
│   │   ├── 002-postgresql.md
│   │   ├── 003-sqlalchemy.md
│   │   ├── 004-jwt-authentication.md
│   │   ├── 005-historical-snapshots.md
│   │   ├── 006-api-first.md
│   │   └── 007-platform-adapters.md
│   ├── diagrams/               # Visual Architecture Diagrams
│   └── images/                 # Embedded Design Images
│
├── alembic/                    # Database Schema Migration folder
├── .env                        # Local Secret environment variables
├── requirements.txt            # Python dependencies list
└── README.md                   # Installation & Setup guidelines
```

### Folder Roles and Responsibilities
*   `app/api/`: Acts as the Controller layer. It maps HTTP routes, extracts request parameters, runs Pydantic validators, and delegates execution to the service layer.
*   `app/core/`: Initializes shared system services (config loader, db connection pools, logging sinks, security crypt-helpers).
*   `app/models/`: Declares the structural persistence layer mapped directly to database tables.
*   `app/schemas/`: Implements boundary validators preventing invalid shapes from entering the API, and serializes database models to sanitize API outputs.
*   `app/repositories/`: Isolates database operations (raw queries, ORM execution). This prevents API route files and business logic services from containing raw database query syntax.
*   `app/services/`: The core business engine of DevTrack. It contains the orchestrators, third-party clients, scoring algorithms, and task schedules.
*   `app/utils/`: Lightweight, stateless functions that perform helper calculations (formatting dates, sanitizing strings).

---

## 13. Development Tools
*   **Version Control:** Git (hosted on GitHub for source code backup and version management).
*   **IDE:** VS Code (configured with Ruff/Black for formatting, Pyright/Mypy for type safety checks).
*   **API Client:** Postman or Bruno (for local manual testing of REST requests before frontend integration).

---

## 14. Testing Strategy (Future Implementation)
While robust testing is critical for a production application, full implementation of the test suite is deferred until the MVP schemas and endpoint models stabilize.
*   **Strategy:**
    *   *Unit Testing:* We will use `pytest` to write automated tests for pure business logic (Scoring calculation algorithms, Recommendation logic, and Insights generators) using mock inputs.
    *   *Integration Testing:* We will use FastAPI’s built-in `TestClient` to mock HTTP requests, verifying endpoint security, error handlers, and database operations.
    *   *External Mocks:* External API calls (GitHub/LeetCode) will be mocked out using libraries like `pytest-mock` or `responses` to prevent hitting rate limits during testing cycles.

---

## 15. Future Technologies (Intentionally Excluded from MVP)
*   **Redis:** Deferred because local PostgreSQL query execution is more than fast enough for low-traffic loads. PostgreSQL can act as our cached read layer. Once traffic scales, Redis will be introduced as an in-memory caching layer.
*   **Docker:** Deferred to keep initial developer workspace setups simple. However, our configuration files will follow Twelve-Factor App design rules (using environment variables for secrets/configs), making containerization with Docker a trivial upgrade.
*   **Celery:** Deferred due to message broker overhead. The scheduler's database schema is designed to scale horizontally if we migrate to Celery workers later.
*   **CI/CD (GitHub Actions):** Deferred until automated testing runs are written. Once tests are in place, a basic CI workflow will compile the project and run checks on every pull request.
*   **Kubernetes:** Deferred due to extreme operational overhead. Single-instance hosting on platforms like AWS App Runner, Render, or a VPS is more than sufficient for the MVP.

---

## 16. Alignment with Project Goals
Our technology choices align directly with DevTrack's core philosophy of being **modular, scalable, and maintainable**:
*   **Separation of Concerns:** By using **FastAPI** for web layers, **SQLAlchemy** for database queries, and **APScheduler** for task triggering, we keep our systems modular. If we need to replace APScheduler with Celery or add a Redis cache in the future, we can swap those modules with zero changes to our core Analytics Engine.
*   **Development Speed vs. Production Quality:** By utilizing Pydantic validation, Alembic migrations, and PostgreSQL from day one, we avoid the typical technical debt of basic "hackathon" MVPs, while skipping heavy-duty infrastructure (Redis, Celery, Docker, K8s) to speed up our path to launch.
