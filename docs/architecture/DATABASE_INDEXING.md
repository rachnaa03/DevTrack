# Database Indexing and Performance Specification
**Version:** 1.0.0  
**Status:** Approved  
**Prepared By:** Rachana Gandla  

This document outlines the database indexing strategy for DevTrack to ensure read queries from our cache tables execute under our target latency of 200ms.

---

## 1. Indexing Strategy by Table

### 1.1 `users` Table
*   **Index:** Unique Index on `email`
*   **Target Query:** `SELECT * FROM users WHERE email = ?`
*   **Rationale:** Enforces data uniqueness at the database level and ensures that the user lookup during authentication (login) is a sub-millisecond index seek.

### 1.2 `profiles` Table
*   **Index:** Unique Index on `user_id`
*   **Target Query:** `SELECT * FROM profiles WHERE user_id = ?`
*   **Rationale:** Ensures fast linking between the User and Profile records during profile queries and secure token evaluations.

### 1.3 `github_snapshots` and `leetcode_snapshots` Tables
*   **Index:** Compound Index on `(user_id, fetched_at)`
*   **Target Query:** `SELECT * FROM github_snapshots WHERE user_id = ? ORDER BY fetched_at DESC LIMIT 1`
*   **Rationale:** Background workers query the database for the most recent snapshot of a user before running analytics. This compound index avoids full-table scans.

### 1.4 `github_histories` and `leetcode_histories` Tables
*   **Index:** Compound Index on `(user_id, date)`
*   **Target Query:** `SELECT * FROM github_histories WHERE user_id = ? AND date BETWEEN ? AND ?`
*   **Rationale:** History tables are queried by the dashboard charting APIs to retrieve metrics over specific date intervals (e.g., last 30 days). A compound index on user and date allows rapid range queries.

### 1.5 `developer_scores` Table
*   **Index:** Compound Index on `(user_id, computed_at)`
*   **Target Query:** `SELECT * FROM developer_scores WHERE user_id = ? ORDER BY computed_at DESC`
*   **Rationale:** Powers the Developer Score history line chart on the dashboard.

### 1.6 `insights` Table
*   **Index:** Compound Index on `(user_id, generated_at)`
*   **Target Query:** `SELECT * FROM insights WHERE user_id = ? ORDER BY generated_at DESC LIMIT 20`
*   **Rationale:** Feeds the dashboard insights scroll container. The compound index ensures the most recent insights are returned instantly.

### 1.7 `recommendations` Table
*   **Index:** Compound Index on `(user_id, status)`
*   **Target Query:** `SELECT * FROM recommendations WHERE user_id = ? AND status = 'active'`
*   **Rationale:** The dashboard recommendation panel queries for the active recommendations of the current user. Indexing on status limits scans to active recommendations.

### 1.8 `weekly_reports` Table
*   **Index:** Compound Index on `(user_id, week_start)`
*   **Target Query:** `SELECT * FROM weekly_reports WHERE user_id = ? ORDER BY week_start DESC`
*   **Rationale:** Allows users to access past weekly summaries.

---

## 2. Summary of Indexes (DDL Syntax)

During migrations, the database creation scripts will implement these indexes:

```sql
-- Core Identity Indexes
CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_profiles_user_id ON profiles(user_id);

-- Snapshot log search optimization
CREATE INDEX idx_github_snapshots_user_date ON github_snapshots(user_id, fetched_at DESC);
CREATE INDEX idx_leetcode_snapshots_user_date ON leetcode_snapshots(user_id, fetched_at DESC);

-- Chart and Trend query optimization
CREATE INDEX idx_github_histories_user_date ON github_histories(user_id, date DESC);
CREATE INDEX idx_leetcode_histories_user_date ON leetcode_histories(user_id, date DESC);

-- Score History and Feed Sorting
CREATE INDEX idx_scores_user_date ON developer_scores(user_id, computed_at DESC);
CREATE INDEX idx_insights_user_date ON insights(user_id, generated_at DESC);
CREATE INDEX idx_recommendations_user_status ON recommendations(user_id, status);
CREATE INDEX idx_reports_user_date ON weekly_reports(user_id, week_start DESC);
```
