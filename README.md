# DevTrack — Unified Developer Analytics Platform

DevTrack is an API-first developer growth companion that transforms fragmented developer metrics into a single, unified analytical feed. By integrating with third-party developer platforms (such as GitHub and LeetCode), DevTrack tracks, analyzes, and scores coding consistency, problem-solving depth, and open-source impact to provide actionable growth recommendations.

---

## 🚀 Core Pipeline Flow

```
Collect (GitHub & LeetCode APIs)
   ↓
Store (Immutable JSONB snapshots)
   ↓
Analyze (Language share, streaks, topics)
   ↓
Score (Custom weighted Developer Score)
   ↓
Generate Insights (Comparative trend highlights)
   ↓
Generate Recommendations (Targeted practice tips)
   ↓
Track Long-Term Growth (Weekly retrospective reports)
```

---

## 🛠 Technology Stack

### Backend Framework
*   **FastAPI**: Async-first routing, automatic OpenAPI validation, and Swagger interface.
*   **Python 3.11+**: Standard for data manipulation and analytics.

### Database & Ingestions
*   **PostgreSQL**: relational storage with native `JSONB` support.
*   **SQLAlchemy 2.0+**: Asynchronous database query mappings.
*   **Alembic**: Database schema migration tracker.
*   **APScheduler**: In-process background job task scheduler.

### Security & Validation
*   **Pydantic v2.0+**: Robust boundary data validators.
*   **JWT & Bcrypt**: Stateless session authorization and secure password hashing.

---

## 📂 Folder Structure

```
DevTrack/
│
├── README.md                   # Project summary & execution guidelines
├── PROJECT_PROGRESS.md         # Phase and roadmap progress tracker
├── TASKS.md                    # Detailed atomic task logs
├── CHANGELOG.md                # Project changelog (Keep a Changelog format)
│
├── app/                        # Application source code
│   ├── api/                    # Presentation layer (HTTP Routers)
│   │   ├── auth/               # User signup and authentication endpoints
│   │   ├── profile/            # Handles profile settings and handle links
│   │   ├── dashboard/          # Summary metrics, charts, timeline feeds
│   │   └── reports/            # Weekly retrospective reports endpoints
│   │
│   ├── core/                   # Shared system utilities (config, database, security)
│   ├── models/                 # SQLAlchemy Declarative Models (Database tables)
│   ├── schemas/                # Request/Response validation schemas
│   ├── repositories/           # Database persistence operations (CRUD only)
│   ├── services/               # Core business logic and platforms integrations
│   │   ├── integrations/       # Platform Adapters (GitHub/LeetCode clients)
│   │   ├── analytics/          # Progress metrics analyzers
│   │   ├── scoring/            # Weighted score calculator
│   │   ├── insights/           # Snapshot comparative logs engine
│   │   ├── recommendations/    # Study recommendations generator
│   │   └── scheduler/          # Background worker tasks
│   │
│   └── utils/                  # Stateless helpers
│
├── tests/                      # Pytest automated testing suite
│   ├── api/                    # Router security and schema validation tests
│   └── services/               # Score and analytics unit tests
│
├── docs/                       # Specifications and Design decisions
│   ├── architecture/           # System design specifications
│   ├── design/                 # Requirements and API contracts
│   └── adr/                    # Architecture Decision Records
│
└── alembic/                    # Database migrations folder
```

---

## ⚙️ Local Installation & Setup

### 1. Prerequisites
Ensure you have Python 3.11+ and PostgreSQL installed on your machine.

### 2. Set Up Virtual Environment
Initialize a Python virtual environment and activate it:
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Linux / macOS)
source .venv/bin/activate
```

### 3. Install Dependencies
Install all package requirements listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Settings
Create a `.env` file in the project root based on the provided template:
```bash
cp .env.example .env
```
Fill in the values:
*   `DATABASE_URL`: Your local asynchronous PostgreSQL connection string.
*   `JWT_SECRET_KEY`: A cryptographically strong secret key.

---

## 🏃 Running the Application

To boot the FastAPI application locally using Uvicorn:
```bash
python -m uvicorn app.main:app --reload
```
Once running, the interactive Swagger API documentation will be available at:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## 🧪 Running Tests

To run the Pytest suite:
```bash
pytest
```
