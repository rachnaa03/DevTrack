# ADR 008: APScheduler for Background Scheduling
**Status:** Approved  
**Date:** August 3, 2026  
**Prepared By:** Rachana Gandla  

## Context
DevTrack periodically synchronizes user data from external platform APIs in the background. The synchronization job is scheduled (e.g. twice daily) and needs to execute out-of-band relative to the REST API request-response threads.

## Decision
We selected **APScheduler (Advanced Python Scheduler)** as our task scheduling library, running in-process using PostgreSQL as a persistent job store.

## Alternatives Considered
*   **Celery:** A powerful distributed worker queue. However, Celery requires a dedicated message broker (like Redis or RabbitMQ) and separate daemon processes, which dramatically increases setup complexity, local footprint, and infrastructure costs for an MVP.
*   **Custom Sleep Loops:** Running an infinite Python `while True: sleep()` loop. This is error-prone, lacks scheduling durability, loses tasks upon server restarts, and lacks progress monitoring.

## Consequences
*   **Benefits:**
    *   Zero external brokers required; runs inside the FastAPI process.
    *   SQLAlchemy Job Store allows scheduling state to persist across server restarts.
    *   Extremely low operational and deployment overhead.
*   **Trade-offs:**
    *   Shares CPU resources with the FastAPI web server. Since our tasks are network-I/O bound rather than CPU-bound, this is acceptable for the MVP. We will migrate to Celery post-MVP if background worker volume causes performance degradation.
