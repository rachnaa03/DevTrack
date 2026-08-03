# ADR 003: SQLAlchemy for ORM Framework
**Status:** Proposed  
**Date:** August 3, 2026  
**Prepared By:** Rachana Gandla  

## Context
DevTrack requires an Object-Relational Mapping (ORM) framework to communicate with the PostgreSQL database. The application must support asynchronous database sessions, type hints, and scalable schema management.

## Decision
We select **SQLAlchemy v2.0+** as the core ORM framework.

## Alternatives Considered
*   **SQLModel:** Offers quick setup but lacks maturity and can limit advanced database query and configuration needs.
*   **Django ORM:** Opinionated and tightly coupled with the Django web framework, which conflicts with our FastAPI selection.

## Consequences
*   **Benefits:**
    *   Highly stable, mature, and industry-standard ORM.
    *   Native async database engine support.
    *   Strict separation of concerns.
*   **Trade-offs:**
    *   More verbose configuration compared to SQLModel.
