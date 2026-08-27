# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Implemented pure `DeveloperScoreCalculator` in `app/services/scoring/calculator.py` for computing the rule-based Developer Score v1 out of 1000.
- Added typed Pydantic models for Developer Score result and subcomponent breakdown in `app/schemas/score.py`.
- Added unit tests in `tests/services/scoring/test_calculator.py` covering all scoring combinations and boundaries.
- Created separate `github_analytics` and `leetcode_analytics` database tables to persist computed developer metrics independently.
- Created `GitHubAnalyticsRepository` and `LeetCodeAnalyticsRepository` encapsulating database queries and same-day upserts.
- Generated database schema migration and added repository tests.
- Implemented `LeetCodeAnalyzer` service in `app/services/analytics/leetcode.py` for computing comprehensive difficulty statistics, topic shares, growth deltas, observed daily consistency/frequency metrics, and contribution streaks.
- Added typed Pydantic models for LeetCode analysis results in `app/schemas/leetcode_analysis.py`.
- Added unit tests in `tests/services/analytics/test_leetcode_analyzer.py` verifying snapshot missing states, topic deduplication, growth, observed transitions, and streak boundaries.
- Implemented `GitHubAnalyzer` service in `app/services/analytics/github.py` for computing comprehensive repository volume statistics, language shares, growth deltas, and contribution streaks.
- Added typed Pydantic models for GitHub analysis results in `app/schemas/github_analysis.py`.
- Added unit tests in `tests/services/analytics/test_github_analyzer.py` verifying snapshot failures, sorting stability, growth ranges, observed-day frequency/consistency, and stale/ambiguous current/longest streak behaviors.
- Implemented `TrendQueryEngine` service in `app/services/analytics/trends.py` coordinating historical query range retrievals and metric trend calculations.
- Added typed Pydantic models for metric deltas in `app/schemas/trends.py`.
- Added optimized database method `get_recent_by_user_id` to both `GitHubHistoryRepository` and `LeetCodeHistoryRepository`.
- Added `InvalidMetricException` to `app/utils/exceptions.py` raising custom HTTP 400 validation error for unsupported metrics.
- Created Trend Query Engine mock unit tests in `tests/services/analytics/test_trends.py`.
- Implemented `GitHubHistoryRepository` in `app/repositories/github_history.py` and `LeetCodeHistoryRepository` in `app/repositories/leetcode_history.py` utilizing PostgreSQL-native `ON CONFLICT DO UPDATE` for atomic daily upserts.
- Added repository unit tests for both history repositories under `tests/repositories/` verifying create/upsert, date filtering, ordering, and transaction rollbacks.
- Designed `GitHubHistory` SQLAlchemy model in `app/models/github_history.py` and `LeetCodeHistory` SQLAlchemy model in `app/models/leetcode_history.py` representing structured historical metrics.
- Created unique constraints `uq_github_histories_user_date` and `uq_leetcode_histories_user_date` and composite indexes `idx_github_histories_user_date` and `idx_leetcode_histories_user_date` supporting fast daily queries.
- Configured a database migration script `bf37cdd39cb0_create_history_tables.py` using Alembic and registered relationships on the `User` model.
- Designed `LeetCodeSnapshot` SQLAlchemy model in `app/models/leetcode_snapshot.py` and `LeetCodeSnapshotRepository` in `app/repositories/leetcode_snapshot.py` supporting postgres `JSONB` daily raw API backups.
- Configured a database migration script `185f6bbb7554_create_leetcode_snapshots_table.py` using Alembic and registered relationships on the `User` model.
- Integrated Option A stage-wise transaction flow into `LeetCodeSyncService` to commit raw payloads prior to parsing.
- Created repository/model unit tests in `tests/services/integrations/test_leetcode_snapshot.py` and extended existing integration tests in `tests/services/integrations/test_leetcode_sync.py` to check snapshot limits, cascades, and transaction boundaries.
- Designed and implemented `LeetCodeClient` HTTP adapter in `app/services/integrations/leetcode.py` issuing GraphQL query POST requests with retry and sliding-window rate limit handlers.
- Implemented `LeetCodeDataParser` in `app/services/integrations/leetcode_parser.py` validating raw GraphQL payloads against deep Pydantic schemas and deriving totals when "All" is missing.
- Implemented `LeetCodeSyncService` in `app/services/integrations/leetcode_sync.py` orchestrating LeetCode data sync and non-destructively updating local database profiles.
- Extended the test suite in `tests/services/integrations/test_leetcode_sync.py` covering parser counts, Tag lists, nonexistent handles, profile updates, and idempotency states.
- Created `LeetCodeClient` test suite in `tests/services/integrations/test_leetcode_client.py` covering success responses, nonexistent users, rate-limits, GraphQL failures, timeouts, and transient errors.
- Implemented `/api/v1/health` endpoint to monitor application liveness and PostgreSQL readiness.
- Designed `GitHubSnapshot` SQLAlchemy model in `app/models/github_snapshot.py` and `GitHubSnapshotRepository` in `app/repositories/github_snapshot.py` supporting postgres `JSONB` daily raw API backups.
- Configured a database migration script `914773fe5de6_create_github_snapshots_table.py` using Alembic and registered relationships on the `User` model.
- Integrated Option A stage-wise transaction flow into `GitHubSyncService` to commit raw payloads prior to parsing.
- Created repository/model unit tests in `tests/services/integrations/test_github_snapshot.py` and extended existing integration tests in `tests/services/integrations/test_github_sync.py` to check snapshot limits, cascades, and transaction boundaries.
- Implemented `GitHubDataParser` in `app/services/integrations/github_parser.py` validating and converting raw API payloads into strongly-typed models with accumulated metric aggregation.
- Implemented `GitHubSyncService` in `app/services/integrations/github_sync.py` executing the profile synchronization pipeline with strict null-checking updates and local state constraints.
- Added custom local business logic exception `PlatformNotConnectedException` for missing platform credentials.
- Created `GitHubSyncService` test suite in `tests/services/integrations/test_github_sync.py` covering parser types, profile diff updates, idempotency, and database failures.
- Designed and implemented `GitHubClient` HTTP client adapter in `app/services/integrations/github.py` with repository pagination, token security boundary headers, and configurable sliding-window rate limit fallbacks.
- Added custom downstream platform Exceptions (`PlatformUserNotFoundException`, `PlatformRateLimitException`, `PlatformAuthException`, `PlatformTransientException`, `PlatformClientException`) for precise status classifications.
- Created `GitHubClient` test suite in `tests/services/integrations/test_github_client.py` covering error mapping, transient retries, pagination, and token safety.
- Designed and implemented `AsyncRateLimiter` (sliding-window async limiter) and `async_retry` (exponential backoff retry decorator) inside `app/services/integrations/helpers.py`.
- Created comprehensive helper tests in `tests/services/integrations/test_helpers.py` checking validation, concurrency limits, and retry semantics.
- Created generic synchronization validation helper `validate_platform_data` and custom exception `PlatformValidationException` to format and check external APIs structurally.
- Designed foundational Pydantic v2 schemas `GitHubProfileSyncSchema` and `GitHubRepoSyncSchema` to validate GitHub profiles and repositories with strict field checks.
- Implemented sync validation test cases in `tests/services/integrations/test_sync_validation.py`.
- Implemented `BasePlatformClient` abstract base class in `app/services/integrations/base.py` defining contracts for asynchronous data ingestion.
- Added base abstract class unit tests in `tests/services/integrations/test_base_client.py`.
- Implemented authenticated platform username connection endpoint `PUT /api/v1/profile/connect` allowing users to bind GitHub/LeetCode handles with strict regex formats and validation checks.
- Implemented authenticated user profile metadata fetch (`GET /api/v1/profile`) and update (`PUT /api/v1/profile`) endpoints with strict extra parameter rejection.
- Configured lazy database profile provisioning (Option B) and partial field update validation handlers.
- Created endpoint integration tests in `tests/api/test_profile_api.py`.
- Designed `Profile` database model in `app/models/profile.py` with bio, avatar, and integration handles.
- Generated Alembic database schema migration to provision the `profiles` table and `idx_profiles_user_id` unique index.
- Configured 1:1 bidirectional mapping between `User` and `Profile` models in SQLAlchemy.
- Created model mapping unit tests in `tests/models/test_profile_model.py`.
- Verified security controls for the protected user route `GET /api/v1/auth/me` to prevent unauthorized resource leakage.
- Implemented JWT token validation and reusable dependency `get_current_user` inside `app/api/dependencies/auth.py`.
- Added protected endpoint `GET /api/v1/auth/me` returning safe details of the authenticated developer.
- Added database lookup method `get_by_id` inside `UserRepository` in `app/repositories/user.py`.
- Added custom exception `AuthenticationException` in `app/utils/exceptions.py` mapping to generic HTTP 401 validation failures.
- Added integration test suite `tests/api/test_auth_dependency.py` covering token expiry, invalid signatures, missing headers, and nonexistent user matching.
- Implemented user login endpoint `POST /api/v1/auth/login` returning signed JWT access and refresh tokens.
- Centralized JWT signing functions (`create_access_token`, `create_refresh_token`) inside `app/core/security.py` using HS256 algorithm and environment configuration.
- Added custom exception `InvalidCredentialsException` in `app/utils/exceptions.py` mapping to generic HTTP 401 failures.
- Added timing attack protection inside `AuthService.authenticate_user(...)` via dummy bcrypt hashing for non-existent emails.
- Added unit and integration test suites in `tests/api/test_login.py` and `tests/services/test_auth_service.py`.
- Implemented user registration endpoint `POST /api/v1/auth/register` mapping request schemas, duplicate validations, and credentials storage.
- Created database operations layer `UserRepository` in `app/repositories/user.py`.
- Created authentication service layer `AuthService` in `app/services/auth.py`.
- Defined application exceptions (`DevTrackException`, `EmailAlreadyExistsException`) in `app/utils/exceptions.py`.
- Created API and service integration test suites `tests/api/test_auth.py` and `tests/services/test_auth_service.py`.
- Implemented secure password hashing and verification utilities (`hash_password`, `verify_password`) using native `bcrypt` in `app/core/security.py`.
- Created automated unit tests in `tests/core/test_security.py` verifying hash salting, successful matches, and validation failures.
- Defined SQLAlchemy 2.0 database model for the `User` entity (`users` table).
- Implemented unique index constraint `idx_users_email` on the `email` column.
- Created Alembic database schema migration script to provision the `users` table.

### Fixed
- Replaced `OAuth2PasswordBearer` with `HTTPBearer` to resolve Swagger UI authorization prompt mismatches, allowing token authorization without requesting username/password forms.
- Explicitly check and validate token scheme prefixes to prevent accepting unsupported authentication headers.
- Created model unit tests in `tests/models/test_user.py` to verify attributes, columns, and index constraints.
- Created `HealthResponse` Pydantic response schema in `app/schemas/health.py`.
- Configured structured exception logging for database connectivity failures in the health router.
- Added unit and integration test suite `tests/api/test_health.py` for mocking successful/unhealthy DB connection states.

## [0.1.0] - 2026-08-03

### Added
- Initial project requirements in Software Requirements Specification ([SRS.md](file:///d:/workspace/DevTrack/docs/design/SRS.md)).
- Technology stack selection document ([TECH_STACK.md](file:///d:/workspace/DevTrack/docs/design/TECH_STACK.md)).
- Overall system design in System Architecture Specification ([ARCHITECTURE.md](file:///d:/workspace/DevTrack/docs/architecture/ARCHITECTURE.md)).
- Conceptual entities in Domain Model Specification ([DOMAIN_MODEL.md](file:///d:/workspace/DevTrack/docs/architecture/DOMAIN_MODEL.md)).
- Database optimization rules in Database Indexing Specification ([DATABASE_INDEXING.md](file:///d:/workspace/DevTrack/docs/architecture/DATABASE_INDEXING.md)).
- Initial implementation roadmap in ([IMPLEMENTATION_ROADMAP.md](file:///d:/workspace/DevTrack/docs/design/IMPLEMENTATION_ROADMAP.md)).
- Initial configuration settings description ([CONFIGURATION.md](file:///d:/workspace/DevTrack/docs/design/CONFIGURATION.md)).
- Error response layout definition ([ERROR_HANDLING.md](file:///d:/workspace/DevTrack/docs/design/ERROR_HANDLING.md)).
- Coding standards specification ([CODING_STANDARDS.md](file:///d:/workspace/DevTrack/docs/design/CODING_STANDARDS.md)).
- Quality attributes target metrics ([QUALITY_ATTRIBUTES.md](file:///d:/workspace/DevTrack/docs/architecture/QUALITY_ATTRIBUTES.md)).
- Post-MVP scaling strategy ([FUTURE_ARCHITECTURE.md](file:///d:/workspace/DevTrack/docs/architecture/FUTURE_ARCHITECTURE.md)).
- Initial ADRs for FastAPI ([001-fastapi.md](file:///d:/workspace/DevTrack/docs/adr/001-fastapi.md)), PostgreSQL ([002-postgresql.md](file:///d:/workspace/DevTrack/docs/adr/002-postgresql.md)), APScheduler ([008-apscheduler.md](file:///d:/workspace/DevTrack/docs/adr/008-apscheduler.md)), JWT ([004-jwt-authentication.md](file:///d:/workspace/DevTrack/docs/adr/004-jwt-authentication.md)), and historical snapshots ([005-historical-snapshots.md](file:///d:/workspace/DevTrack/docs/adr/005-historical-snapshots.md)).
- Placeholders for Database Design ([DATABASE_DESIGN.md](file:///d:/workspace/DevTrack/docs/architecture/DATABASE_DESIGN.md)), API Specifications ([API_SPECIFICATION.md](file:///d:/workspace/DevTrack/docs/design/API_SPECIFICATION.md)), and ADRs for SQLAlchemy ([003-sqlalchemy.md](file:///d:/workspace/DevTrack/docs/adr/003-sqlalchemy.md)), API-First ([006-api-first.md](file:///d:/workspace/DevTrack/docs/adr/006-api-first.md)), and Platform Adapters ([007-platform-adapters.md](file:///d:/workspace/DevTrack/docs/adr/007-platform-adapters.md)).
- Reorganized directory structure: split `docs/` into `architecture/`, `design/`, `adr/`, `diagrams/`, and `images/`.
- Created project tracking documents `PROJECT_PROGRESS.md` and `TASKS.md` in the root workspace.
