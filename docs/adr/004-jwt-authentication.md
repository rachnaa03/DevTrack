# ADR 004: JWT Authentication for Session Management
**Status:** Approved  
**Date:** August 3, 2026  
**Prepared By:** Rachana Gandla  

## Context
DevTrack requires stateless session authentication to verify user access to protected API endpoints, such as profile editing, connection settings, and analytics dashboard summaries.

## Decision
We selected **JSON Web Tokens (JWT)** as the primary authentication mechanism, with symmetric cryptographic signatures (`HS256`).

## Alternatives Considered
*   **Cookie-based Sessions:** Involves storing session IDs in the database and checking them on every request. This is stateful, degrades database query performance under load, and can introduce cross-origin sharing (CORS) complications if our frontend React client and FastAPI backend are hosted on separate domains.
*   **API Keys:** Simpler to implement but lacks automatic expiration capabilities and requires database reads on every single request.

## Consequences
*   **Benefits:**
    *   Stateless sessions allow the backend to verify signatures in-memory without making a database query.
    *   Symmetric signatures (`HS256`) keep token verification rapid.
    *   Compatible with cross-origin domains out-of-the-box.
*   **Trade-offs:**
    *   Tokens cannot be invalidated easily before their natural expiration date. To mitigate this risk, access tokens will be short-lived (e.g., 15 minutes) and refresh tokens will be stored securely to obtain new credentials.
