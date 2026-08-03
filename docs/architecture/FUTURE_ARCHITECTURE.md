# Future Architecture and Scale Specification (Post-MVP)
**Version:** 1.0.0  
**Status:** Approved  
**Prepared By:** Rachana Gandla  

This document explains how DevTrack is architected to support future scaling requirements, caching layers, distributed workers, and AI features without requiring modifications to the core MVP code.

---

## 1. Introducing Redis Caching

As active user traffic scales, querying PostgreSQL on every read request could degrade latency. Redis will be introduced as an in-memory caching layer:

```
[React Client] ──> [FastAPI Controller] ──> [Redis Cache] (Hit)
                                                │
                                                ▼ (Miss)
                                         [PostgreSQL DB]
```

*   **How it is integrated:**
    *   We will place a Redis client dependency between the API Controller and the Repository layers.
    *   GET endpoints (e.g., `/api/v1/dashboard/summary`) will check Redis first. On a cache miss, the service queries PostgreSQL, writes the result to Redis with a Time-To-Live (TTL), and returns the payload.
*   **Zero Core Changes:** Because the Repository layer isolates database reads, we can wrap our existing repositories in a **Caching Decorator** without altering our API routers or business services.

---

## 2. Migrating to Celery & Redis Task Queue

When our user base grows to thousands of developers, running APScheduler in-process will cause CPU starvation in Uvicorn threads. We will offload sync jobs to a distributed Celery worker cluster:

```
                  [FastAPI API Server]
                            │
                            ▼ (Enqueue Sync Job)
                      [Redis Broker]
                            │
                     ┌──────┴──────┐
                     ▼             ▼
              [Celery Worker] [Celery Worker]
```

*   **How it is integrated:**
    *   APScheduler triggers inside Uvicorn will be disabled.
    *   We will introduce a Celery application module in `app/core/celery.py`.
    *   Our master synchronization function (`app/services/scheduler/sync_job.py`) will be wrapped in a Celery `@app.task` decorator.
*   **Zero Core Changes:** The synchronization logic is already written as a standalone, framework-agnostic Python function. Swapping the trigger runner from APScheduler to Celery does not require altering our integration adapters, scoring engines, or snapshot schemas.

---

## 3. Upgrading to AI-Generated Insights & Recommendations

The MVP uses rule-based logic (e.g., "if DP count < 20% then suggest practicing DP"). Post-MVP, we will use Large Language Models (like the Gemini API) to generate highly contextual, personalized advice:

*   **How it is integrated:**
    *   We will create an `AiInsightsService` and `AiRecommendationService` implementing the existing engine interfaces.
    *   The service will compile the user's historical progress JSON and send a prompt to the Gemini API (e.g., via the `google-generativeai` SDK).
    *   The generated output is saved to the existing `insights` and `recommendations` tables.
*   **Zero Core Changes:** Because our Recommendation and Insights engines are decoupled from the API controller and database schemas, we can swap out the rule-based classes for the AI service classes with zero impact on the frontend or other backend services.

---

## 4. Integrating Additional Coding Platforms

Adding platforms like Codeforces, CodeChef, or HackerRank will require no changes to our core database models or user management controllers:

*   **How it is integrated:**
    *   Create a new client class (e.g., `CodeforcesClient`) inheriting from `BasePlatformClient` under `app/services/integrations/`.
    *   Add corresponding snapshot and history tables mapped through Alembic.
    *   Register the new client adapter in the synchronization orchestrator factory.
*   **Zero Core Changes:** The sync coordinator handles all platforms uniformly by looping over registered adapters, allowing new sources to be plugged in seamlessly.
