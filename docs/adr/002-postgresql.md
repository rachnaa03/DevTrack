# ADR 002: PostgreSQL for Persistent Storage
**Status:** Approved  
**Date:** August 3, 2026  
**Prepared By:** Rachana Gandla  

## Context
DevTrack must maintain secure user login profiles, platform usernames, chronological progress snapshots, calculated scores, and weekly activity reports. These entities have tight relational integrity rules.

## Decision
We selected **PostgreSQL** as the primary relational database.

## Alternatives Considered
*   **SQLite:** Highly lightweight, but database-level file-locking makes it unsuitable for concurrent background synchronization writes while serving user read requests.
*   **MySQL:** A solid relational database, but it lacks the robust JSONB indexing and query features of PostgreSQL, which are necessary for storing raw third-party platform responses.
*   **MongoDB:** A document store that is good for JSON snapshots but lacks native relational integrity constraints, foreign key validation, and ACID-transaction capabilities for core financial/user profiling structures.

## Consequences
*   **Benefits:**
    *   ACID transactions guarantee data consistency.
    *   JSONB columns allow storing raw third-party responses as snapshots, which we can parse later without losing data.
    *   Superior indexing and query features support fast rendering of historical trend graphs.
*   **Trade-offs:**
    *   Requires setting up a persistent local or cloud database service (unlike SQLite which is a flat file).
