# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Implemented `/api/v1/health` endpoint to monitor application liveness and PostgreSQL readiness.
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
