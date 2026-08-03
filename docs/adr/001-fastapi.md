# ADR 001: FastAPI for Backend Framework
**Status:** Approved  
**Date:** August 3, 2026  
**Prepared By:** Rachana Gandla  

## Context
DevTrack requires a backend framework that provides excellent performance, facilitates clean code validation, is async-friendly, and integrates seamlessly with modern frontend systems via standard REST APIs. The platform retrieves data from third-party endpoints (GitHub and LeetCode) and needs to serve dashboards rapidly.

## Decision
We selected **FastAPI** as the core backend web framework.

## Alternatives Considered
*   **Flask:** Highly lightweight but runs synchronously, lacks built-in request/response data validation, and requires manual configuration for OpenAPI docs.
*   **Django:** A heavy full-stack framework with an opinionated ORM. Django introduces unnecessary features (such as template engines, built-in admin UI, and forms) that violate our decoupled, API-first frontend design.

## Consequences
*   **Benefits:**
    *   Native asynchronous routing speeds up integration network requests.
    *   Automatic validation of request parameters using Pydantic prevents runtime data pollution.
    *   Auto-generated Swagger documentation at `/api/v1/docs` simplifies frontend-backend integration.
*   **Trade-offs:**
    *   Requires asynchronous database drivers and session management patterns, which are slightly more complex to write than standard synchronous models.
