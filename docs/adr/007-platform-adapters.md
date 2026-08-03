# ADR 007: Adapter Pattern for Third-Party Integrations
**Status:** Proposed  
**Date:** August 3, 2026  
**Prepared By:** Rachana Gandla  

## Context
DevTrack integrates with external developer platforms (GitHub and LeetCode) to aggregate developer metrics. We need a design that makes it easy to add new platforms (e.g., Codeforces, HackerRank) without altering the scheduling worker or core dashboard API endpoints.

## Decision
We select the **Adapter Pattern** to abstract third-party interactions. The system will define an abstract base class `BasePlatformClient` that all platform integration clients must implement.

## Alternatives Considered
*   **Direct Inline Integrations:** Directly fetching data in API endpoints or scheduling tasks. This creates spaghetti code and breaks modularity.

## Consequences
*   **Benefits:**
    *   Ensures consistent interface definitions across platform integrations.
    *   Decouples integration-specific implementation details from core business logic.
    *   Enables painless expansion to new platforms.
*   **Trade-offs:**
    *   Adds a layer of abstraction that requires proper subclass interface conformity.
