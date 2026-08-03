# Domain Model Specification
**Version:** 1.0.0  
**Status:** Approved  
**Prepared By:** Rachana Gandla  

This document describes the core domain entities, their responsibilities, relationships, and boundaries in the DevTrack system.

---

## 1. Domain Class Diagram (Mermaid)

```mermaid
classDiagram
    class User {
        +UUID id
        +String email
        +String hashed_password
        +DateTime created_at
        +register()
        +login()
    }

    class Profile {
        +UUID id
        +UUID user_id
        +String bio
        +String avatar_url
        +String github_username
        +String leetcode_username
        +DateTime updated_at
        +link_platform()
    }

    class Snapshot {
        +UUID id
        +UUID user_id
        +String platform
        +JSON raw_data
        +DateTime fetched_at
    }

    class PlatformHistory {
        +UUID id
        +UUID user_id
        +DateTime date
        +Integer commits
        +Integer problems_solved
        +JSON parsed_metrics
    }

    class DeveloperScore {
        +UUID id
        +UUID user_id
        +Integer overall_score
        +Integer consistency_score
        +Integer depth_score
        +Integer impact_score
        +DateTime computed_at
    }

    class Insight {
        +UUID id
        +UUID user_id
        +String message
        +String type
        +DateTime generated_at
    }

    class Recommendation {
        +UUID id
        +UUID user_id
        +String title
        +String description
        +String priority
        +String status
        +DateTime created_at
    }

    class WeeklyReport {
        +UUID id
        +UUID user_id
        +DateTime week_start
        +DateTime week_end
        +JSON report_data
    }

    User "1" -- "1" Profile : Owns
    User "1" -- "*" Snapshot : Has
    User "1" -- "*" PlatformHistory : Has
    User "1" -- "*" DeveloperScore : Has
    User "1" -- "*" Insight : Receives
    User "1" -- "*" Recommendation : Receives
    User "1" -- "*" WeeklyReport : Receives
```

---

## 2. Entity Descriptions & Responsibilities

### 2.1 User (Aggregate Root)
*   **Description:** Represents the authenticated identity in the system.
*   **Responsibilities:** Enforces login validation, registration invariants, password hashes, and identity lookup.
*   **Ownership:** Top-level entity. Owns all subsequent data generated in the workspace.

### 2.2 Profile
*   **Description:** Contains user profile metadata and linked platform username handles.
*   **Responsibilities:** Links platform handles (GitHub, LeetCode), checks syntax rules, and stores user biography details.
*   **Ownership:** Owned 1-to-1 by `User`.

### 2.3 Snapshot (Immutable log)
*   **Description:** The raw data payload fetched from GitHub or LeetCode during a sync cycle.
*   **Responsibilities:** Preserves an exact, unparsed backup of the third-party response.
*   **Ownership:** Owned 1-to-many by `User`. A snapshot is never modified after it is created.

### 2.4 PlatformHistory
*   **Description:** Tabular, parsed historical metrics derived from Snapshots.
*   **Responsibilities:** Extracts parameters (e.g. commits count, problems solved by difficulty) into structured relational columns to support query performance for chart endpoints.
*   **Ownership:** Owned 1-to-many by `User`. Created automatically by the Analytics Engine.

### 2.5 DeveloperScore
*   **Description:** The computed score (0-1000) and sub-category breakdowns.
*   **Responsibilities:** Stores overall score, category weights (consistency, depth, impact), and trends for a specific sync point.
*   **Ownership:** Owned 1-to-many by `User`.

### 2.6 Insight
*   **Description:** Text observation indicating deviations or trends in developer performance.
*   **Responsibilities:** Tracks metrics (e.g. drop in DP questions solved) and represents positive/negative warnings for dashboard feeds.
*   **Ownership:** Owned 1-to-many by `User`.

### 2.7 Recommendation
*   **Description:** Actionable task suggestion targeted at enhancing the developer's skills.
*   **Responsibilities:** Stores recommendation title, details, priority scale (High, Medium, Low), and completion status (Active, Dismissed, Completed).
*   **Ownership:** Owned 1-to-many by `User`.

### 2.8 WeeklyReport
*   **Description:** Relational summaries of user performance over a 7-day period.
*   **Responsibilities:** Computes weekly change logs (growth, consistency metrics) and preserves weekly performance archives.
*   **Ownership:** Owned 1-to-many by `User`. Generated at the end of each week.
