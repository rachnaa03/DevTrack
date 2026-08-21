# REST API Specification

**Version:** 1.0.0  
**Status:** Approved  
**Prepared By:** Rachana Gandla

This document details the API endpoint contracts for the DevTrack platform under the versioned prefix `/api/v1`.

---

## 1. Global Standard Specifications

### 1.1 Content Negotiation
*   All requests sending payloads must include the header `Content-Type: application/json`.
*   All responses return payloads in JSON format with `Content-Type: application/json`.

### 1.2 Authentication
*   Protected endpoints require a JWT Bearer token in the `Authorization` header:
    `Authorization: Bearer <JWT_ACCESS_TOKEN>`
*   Unauthorized calls to protected endpoints return HTTP `401 Unauthorized`.

### 1.3 Standard Error Payload
All API exceptions return the following standard JSON shape (as specified in [ERROR_HANDLING.md](file:///d:/workspace/DevTrack/docs/design/ERROR_HANDLING.md)):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed.",
    "request_id": "8c0a8767-f87c-4a30-8012-9c17621c43f2",
    "details": [
      {
        "field": "email",
        "issue": "value is not a valid email address"
      }
    ]
  }
}
```

---

## 2. Authentication & Identity Endpoints (`/api/v1/auth`)

### 2.1 Register Account
*   **Method**: `POST`
*   **URL**: `/api/v1/auth/register`
*   **Purpose**: Create a new developer account.
*   **Authentication**: None
*   **Request Body**:
    *   `email` (String, required): Valid email syntax, max 255 chars.
    *   `password` (String, required): Strong password rules (min 8 chars, max 64 chars).
*   **Validation Rules**:
    *   Reject duplicate email registers with `400 Bad Request` (`EMAIL_ALREADY_EXISTS`).
*   **Status Codes**:
    *   `201 Created`: Account successfully initialized.
    *   `400 Bad Request`: Validation failure or email duplicate.
*   **Example Request**:
    ```json
    {
      "email": "dev@example.com",
      "password": "SuperSecurePassword123"
    }
    ```
*   **Example Response (`201 Created`)**:
    ```json
    {
      "id": "e939a897-f0b4-4f81-9b1f-7bb66487fb01",
      "email": "dev@example.com",
      "created_at": "2026-08-03T22:00:00Z"
    }
    ```

---

### 2.2 Login (Token Acquisition)
*   **Method**: `POST`
*   **URL**: `/api/v1/auth/login`
*   **Purpose**: Verify credentials and return session tokens.
*   **Authentication**: None
*   **Request Body**:
    *   `email` (String, required): Valid email address.
    *   `password` (String, required): Password.
*   **Status Codes**:
    *   `200 OK`: Verification successful. Returns access and refresh tokens.
    *   `401 Unauthorized`: Invalid credentials.
*   **Example Request**:
    ```json
    {
      "email": "dev@example.com",
      "password": "SuperSecurePassword123"
    }
    ```
*   **Example Response (`200 OK`)**:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsIn...",
      "token_type": "bearer",
      "expires_in": 900
    }
    ```

---

### 2.3 Token Refresh
*   **Method**: `POST`
*   **URL**: `/api/v1/auth/refresh`
*   **Purpose**: Acquire a new short-lived access token using a long-lived refresh token.
*   **Authentication**: None (Refresh Token is supplied in the request body)
*   **Request Body**:
    *   `refresh_token` (String, required): Cryptographically signed refresh token.
*   **Status Codes**:
    *   `200 OK`: Token refreshed successfully.
    *   `401 Unauthorized`: Refresh token expired, revoked, or invalid.
*   **Example Request**:
    ```json
    {
      "refresh_token": "eyJhbGciOiJIUzI1NiIsIn..."
    }
    ```
*   **Example Response (`200 OK`)**:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
      "token_type": "bearer",
      "expires_in": 900
    }
    ```

---

### 2.4 Retrieve Authenticated Identity
*   **Method**: `GET`
*   **URL**: `/api/v1/auth/me`
*   **Purpose**: Get identity info for the currently authenticated user.
*   **Authentication**: Required (JWT Bearer)
*   **Status Codes**:
    *   `200 OK`: Success.
    *   `401 Unauthorized`: Invalid token.
*   **Example Response (`200 OK`)**:
    ```json
    {
      "id": "e939a897-f0b4-4f81-9b1f-7bb66487fb01",
      "email": "dev@example.com",
      "created_at": "2026-08-03T22:00:00Z"
    }
    ```

---

## 3. Profile Management Endpoints (`/api/v1/profile`)

### 3.1 Fetch Profile Metadata
*   **Method**: `GET`
*   **URL**: `/api/v1/profile`
*   **Purpose**: Retrieve profile bio, avatar link, and connected platform handles.
*   **Authentication**: Required (JWT Bearer)
*   **Behavior**: If the authenticated user does not have a Profile record in the database, an empty Profile is lazily created and persisted before being returned.
*   **Status Codes**:
    *   `200 OK`: Success.
    *   `401 Unauthorized`: Missing or invalid Bearer token.
*   **Example Response (`200 OK`)**:
    ```json
    {
      "id": "e939a897-f0b4-4f81-9b1f-7bb66487fb01",
      "user_id": "c3dc45a8-a58c-4f81-9b1f-7bb66487fb02",
      "bio": "Senior Python Developer | Open Source Enthusiast",
      "avatar_url": "https://avatars.example.com/dev.jpg",
      "github_username": "octocat",
      "leetcode_username": "lc_master",
      "created_at": "2026-08-03T22:00:00Z",
      "updated_at": "2026-08-03T22:10:00Z"
    }
    ```

---

### 3.2 Update Profile Metadata
*   **Method**: `PUT`
*   **URL**: `/api/v1/profile`
*   **Purpose**: Update profile biography and avatar URL.
*   **Authentication**: Required (JWT Bearer)
*   **Behavior**: Supports partial updates (omitted parameters remain unchanged in the DB, while explicitly provided fields are updated). Rejects any unknown or forbidden fields.
*   **Request Body**:
    *   `bio` (String, nullable, optional): Text profile description, max 1000 chars.
    *   `avatar_url` (String, nullable, optional): Fully qualified HTTP/HTTPS image URL (max 1024 chars).
*   **Status Codes**:
    *   `200 OK`: Update successful.
    *   `401 Unauthorized`: Missing or invalid Bearer token.
    *   `422 Unprocessable Content`: Input validation failed, URL protocol check failed, or forbidden fields (e.g. `github_username`, `user_id`) were submitted.
*   **Example Request**:
    ```json
    {
      "bio": "Principal Engineer at TechCorp",
      "avatar_url": "https://avatars.example.com/new_dev.jpg"
    }
    ```
*   **Example Response (`200 OK`)**:
    ```json
    {
      "id": "e939a897-f0b4-4f81-9b1f-7bb66487fb01",
      "user_id": "c3dc45a8-a58c-4f81-9b1f-7bb66487fb02",
      "bio": "Principal Engineer at TechCorp",
      "avatar_url": "https://avatars.example.com/new_dev.jpg",
      "github_username": "octocat",
      "leetcode_username": "lc_master",
      "created_at": "2026-08-03T22:00:00Z",
      "updated_at": "2026-08-03T22:15:00Z"
    }
    ```

---

### 3.3 Link Platform Account
*   **Method**: `POST`
*   **URL**: `/api/v1/profile/connect`
*   **Purpose**: Securely bind or update platform usernames.
*   **Authentication**: Required (JWT Bearer)
*   **Request Body**:
    *   `github_username` (String, nullable): GitHub handle.
    *   `leetcode_username` (String, nullable): LeetCode handle.
*   **Validation Rules**:
    *   Enforces alphanumeric constraints on username shapes.
    *   Accepts empty string/null to unlink.
*   **Status Codes**:
    *   `200 OK`: Handles successfully updated in the DB.
    *   `400 Bad Request`: Username format validation failed.
*   **Example Request**:
    ```json
    {
      "github_username": "octocat",
      "leetcode_username": "lc_master"
    }
    ```
*   **Example Response (`200 OK`)**:
    ```json
    {
      "github_username": "octocat",
      "leetcode_username": "lc_master",
      "message": "Platform accounts connected successfully. Initial synchronization scheduled."
    }
    ```

---

## 4. Dashboard & Analytics Endpoints (`/api/v1/dashboard`)

### 4.1 Fetch Summary Metrics
*   **Method**: `GET`
*   **URL**: `/api/v1/dashboard/summary`
*   **Purpose**: Get current overall Developer Score, consistency/depth/impact sub-scores, active streaks, and primary statistics.
*   **Authentication**: Required (JWT Bearer)
*   **Status Codes**:
    *   `200 OK`: Success. Returns cached summary details.
    *   `404 Not Found`: Ingestion has not completed yet for the user (score not computed).
*   **Example Response (`200 OK`)**:
    ```json
    {
      "developer_score": {
        "overall": 720,
        "consistency": 180,
        "depth": 270,
        "impact": 270,
        "computed_at": "2026-08-03T12:00:00Z"
      },
      "stats": {
        "github": {
          "total_commits_12m": 350,
          "total_repositories": 12,
          "stars_earned": 45,
          "primary_languages": ["Python", "TypeScript"]
        },
        "leetcode": {
          "total_solved": 150,
          "easy_solved": 50,
          "medium_solved": 80,
          "hard_solved": 20,
          "active_streak": 5
        }
      }
    }
    ```

---

### 4.2 Fetch Historical Chart Range Data
*   **Method**: `GET`
*   **URL**: `/api/v1/dashboard/charts`
*   **Purpose**: Get daily progressive counts for commits and problems solved to feed front-end charts.
*   **Authentication**: Required (JWT Bearer)
*   **Request Parameters (Query)**:
    *   `days` (Integer, optional, default: 30): Calendar interval filter (e.g. 7, 30, 90). Max 365.
*   **Status Codes**:
    *   `200 OK`: Success.
*   **Example Response (`200 OK`)**:
    ```json
    {
      "interval_days": 30,
      "history": [
        {
          "date": "2026-08-02",
          "commits": 5,
          "problems_solved": 2
        },
        {
          "date": "2026-08-03",
          "commits": 3,
          "problems_solved": 1
        }
      ]
    }
    ```

---

### 4.3 Fetch Timeline Events
*   **Method**: `GET`
*   **URL**: `/api/v1/dashboard/timeline`
*   **Purpose**: Get chronologically sorted achievements and actions.
*   **Authentication**: Required (JWT Bearer)
*   **Request Parameters (Query)**:
    *   `limit` (Integer, optional, default: 20): Maximum count of events, max 100.
*   **Status Codes**:
    *   `200 OK`: Success.
*   **Example Response (`200 OK`)**:
    ```json
    {
      "events": [
        {
          "event_date": "2026-08-03",
          "event_type": "milestone_earned",
          "title": "First Hard Problem Solved",
          "description": "Solved LeetCode Hard problem: 'Median of Two Sorted Arrays'."
        },
        {
          "event_date": "2026-08-01",
          "event_type": "account_linked",
          "title": "GitHub Profile Connected",
          "description": "Linked handle 'octocat' to DevTrack profile."
        }
      ]
    }
    ```

---

### 4.4 Fetch Earned Milestones
*   **Method**: `GET`
*   **URL**: `/api/v1/dashboard/milestones`
*   **Purpose**: Retrieve all earned profile badges.
*   **Authentication**: Required (JWT Bearer)
*   **Status Codes**:
    *   `200 OK`: Success.
*   **Example Response (`200 OK`)**:
    ```json
    {
      "milestones": [
        {
          "name": "Consistency Champion",
          "description": "Maintain a LeetCode streak for 5 consecutive days.",
          "badge_url": "https://assets.devtrack.com/badges/consistency_5.png",
          "achieved_at": "2026-08-03T12:00:00Z"
        }
      ]
    }
    ```

---

## 5. Synchronization Status Endpoints (`/api/v1/sync`)

### 5.1 Fetch Ingestion Job Status
*   **Method**: `GET`
*   **URL**: `/api/v1/sync/status`
*   **Purpose**: Get performance data and execution success/failure for the most recent background synchronization run.
*   **Authentication**: Required (JWT Bearer)
*   **Status Codes**:
    *   `200 OK`: Success.
    *   `404 Not Found`: Ingestion job history missing.
*   **Example Response (`200 OK`)**:
    ```json
    {
      "status": "completed",
      "started_at": "2026-08-03T08:00:00Z",
      "completed_at": "2026-08-03T08:00:15Z",
      "duration_seconds": 15,
      "platforms": {
        "github": "success",
        "leetcode": "success"
      }
    }
    ```

---

### 5.2 Trigger Manual Ingestion (Ad-hoc Sync)
*   **Method**: `POST`
*   **URL**: `/api/v1/sync/trigger`
*   **Purpose**: Manually trigger an out-of-band data synchronization run.
*   **Authentication**: Required (JWT Bearer)
*   **Validation Rules**:
    *   Subject to rate limits (e.g. max once per 6 hours per user account) to protect API resources.
*   **Status Codes**:
    *   `202 Accepted`: Job successfully enqueued in background scheduler.
    *   `429 Too Many Requests`: Trigger request blocked due to rate-limit.
*   **Example Response (`202 Accepted`)**:
    ```json
    {
      "job_id": "c1a9a897-f0b4-4f81-9b1f-7bb66487ab19",
      "status": "started",
      "message": "Data ingestion workflow initiated in the background."
    }
    ```

---

## 6. Recommendations & Insights Endpoints (`/api/v1/dashboard/recommendations` & `/api/v1/dashboard/insights`)

### 6.1 Retrieve Active Recommendations
*   **Method**: `GET`
*   **URL**: `/api/v1/dashboard/recommendations`
*   **Purpose**: Fetch all active study recommendations for the current user.
*   **Authentication**: Required (JWT Bearer)
*   **Status Codes**:
    *   `200 OK`: Success.
*   **Example Response (`200 OK`)**:
    ```json
    {
      "recommendations": [
        {
          "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
          "title": "Practice Dynamic Programming",
          "description": "Your DP category solutions make up less than 10% of total solved problems. Try solving 3 Medium DP problems.",
          "priority": "high",
          "status": "active",
          "created_at": "2026-08-03T12:00:00Z"
        }
      ]
    }
    ```

---

### 6.2 Update Recommendation Status
*   **Method**: `PATCH`
*   **URL**: `/api/v1/dashboard/recommendations/{id}`
*   **Purpose**: Complete or dismiss a study recommendation.
*   **Authentication**: Required (JWT Bearer)
*   **Request Body**:
    *   `status` (String, required): New status state. Allowed values: `dismissed`, `completed`.
*   **Status Codes**:
    *   `200 OK`: Recommendation updated successfully.
    *   `400 Bad Request`: Validation failure on status value.
    *   `404 Not Found`: Recommendation ID invalid.
*   **Example Request**:
    ```json
    {
      "status": "completed"
    }
    ```
*   **Example Response (`200 OK`)**:
    ```json
    {
      "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "status": "completed",
      "updated_at": "2026-08-03T22:20:00Z"
    }
    ```

---

### 6.3 Retrieve Historical Insights Feed
*   **Method**: `GET`
*   **URL**: `/api/v1/dashboard/insights`
*   **Purpose**: Get comparative trend insights for the user feed scroll.
*   **Authentication**: Required (JWT Bearer)
*   **Request Parameters (Query)**:
    *   `limit` (Integer, optional, default: 20): Max insight rows, max 50.
*   **Status Codes**:
    *   `200 OK`: Success.
*   **Example Response (`200 OK`)**:
    ```json
    {
      "insights": [
        {
          "id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
          "message": "Your Dynamic Programming practice dropped by 20% compared to last week.",
          "type": "leetcode_depth",
          "generated_at": "2026-08-03T12:00:00Z"
        }
      ]
    }
    ```

---

## 7. Reports Endpoints (`/api/v1/reports`)

### 7.1 Fetch Weekly Reports Index
*   **Method**: `GET`
*   **URL**: `/api/v1/reports/weekly`
*   **Purpose**: Get chronological listing of generated weekly retrospective reports.
*   **Authentication**: Required (JWT Bearer)
*   **Status Codes**:
    *   `200 OK`: Success.
*   **Example Response (`200 OK`)**:
    ```json
    {
      "reports": [
        {
          "id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
          "week_start": "2026-07-27",
          "week_end": "2026-08-02",
          "created_at": "2026-08-03T00:01:00Z"
        }
      ]
    }
    ```

---

### 7.2 Fetch Weekly Report Details
*   **Method**: `GET`
*   **URL**: `/api/v1/reports/weekly/{id}`
*   **Purpose**: Fetch the complete aggregated retrospective values of a specific weekly report.
*   **Authentication**: Required (JWT Bearer)
*   **Status Codes**:
    *   `200 OK`: Success.
    *   `404 Not Found`: Report ID invalid.
*   **Example Response (`200 OK`)**:
    ```json
    {
      "id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
      "week_start": "2026-07-27",
      "week_end": "2026-08-02",
      "report_data": {
        "commits_count": 25,
        "problems_solved": 8,
        "score_delta": 15,
        "summary": "Consistent performance this week. You excelled in Array algorithms and maintained a daily commit streak.",
        "weekly_subscores": {
          "consistency": 185,
          "depth": 275,
          "impact": 275
        }
      },
      "created_at": "2026-08-03T00:01:00Z"
    }
    ```
