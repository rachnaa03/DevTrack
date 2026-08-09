# ADR 005: Immutable Historical Snapshots
**Status:** Approved  
**Date:** August 3, 2026  
**Prepared By:** Rachana Gandla  

## Context
DevTrack is a developer growth platform that measures long-term changes, streaks, and score histories. We need a reliable data model to store daily developer metrics (GitHub commits, LeetCode problems solved) that supports charting history and backfilling analytics without relying on real-time API calls.

## Decision
We selected **Immutable Historical Snapshots** stored as distinct daily database records (`github_snapshots`, `leetcode_snapshots` JSONB columns) and parsed history logs (`github_histories`, `leetcode_histories` tables).

## Alternatives Considered
*   **Aggregate Counters:** Storing only current running totals (e.g. `total_solved = 120`, `total_commits = 300`) and overwriting them on each sync run. This is extremely simple but makes it impossible to build historical charts (e.g. progress over 6 months) or generate weekly delta reports because historical state is lost.
*   **Time-Series Database (e.g. InfluxDB, TimescaleDB):** Ideal for heavy time-series data but adds massive operational and infrastructure overhead to our MVP setup.

## Consequences
*   **Benefits:**
    *   Preserves exact developer history, allowing us to calculate streaks and delta progress.
    *   Immutability guarantees that user records can be audited, re-analyzed, and debugged easily.
    *   Can be queried rapidly using standard SQL indexes.
*   **Trade-offs:**
    *   Database storage footprint will grow linearly with the number of active users. To mitigate this, we schedule sync runs at moderate intervals (twice daily) and will implement data pruning or archive pipelines post-MVP if database size becomes a bottleneck.

