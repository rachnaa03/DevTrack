# DevTrack 🚀

> **A Unified Developer Analytics Platform that helps developers measure, understand, and improve their coding journey.**

DevTrack aggregates coding activity from platforms like **GitHub** and **LeetCode**, stores historical snapshots, analyzes developer growth, calculates a custom **Developer Score**, and generates actionable insights and recommendations through a modern analytics dashboard.

Rather than treating GitHub and LeetCode as isolated platforms, DevTrack combines their data into a **single developer profile** that reflects overall technical growth over time.

---

# ✨ Features

## 🔐 Authentication & User Management

- User Registration & Login
- JWT Authentication
- User Profile Management
- Connect GitHub & LeetCode accounts

---

## 🔗 Platform Integrations

### GitHub

- User Profile
- Repository Statistics
- Programming Languages
- Stars & Forks
- Commit Activity
- Contribution History

### LeetCode

- Problems Solved
- Difficulty Distribution
- Contest Rating
- Acceptance Rate
- Topic-wise Progress
- Recent Activity

---

## 📊 Analytics Dashboard

- Developer Overview
- Coding Activity
- GitHub Activity
- Progress Charts
- Language Distribution
- Topic Distribution
- Coding Consistency
- Growth Trends

---

## ⭐ Developer Score

A custom rule-based scoring system that evaluates a developer's overall growth using multiple metrics such as:

- Coding Consistency
- Problem Solving
- Repository Quality
- GitHub Activity
- Contest Participation

---

## 🧠 Insights Engine

DevTrack transforms raw statistics into meaningful observations.

Examples:

- Your Graph practice decreased by 40% this month.
- GitHub activity increased for three consecutive weeks.
- Medium problem solving improved significantly.

---

## 🎯 Recommendation Engine

Generate personalized recommendations such as:

- Practice Graph problems
- Improve GitHub consistency
- Solve more Medium problems
- Participate in weekly contests

---

## 📈 Progress Tracking

- Weekly Progress
- Monthly Progress
- Historical Growth
- Coding Streaks
- Milestones
- Developer Timeline

---

# 🏗 System Pipeline

```text
GitHub API        LeetCode API
        │
        ▼
Background Synchronization Service
        │
        ▼
Historical Snapshots (PostgreSQL)
        │
        ▼
Analytics Engine
        │
        ▼
Developer Score Engine
        │
        ▼
Insights Engine
        │
        ▼
Recommendation Engine
        │
        ▼
FastAPI REST API
        │
        ▼
Frontend Dashboard
```

---

# 🛠 Technology Stack

| Category | Technology |
|----------|------------|
| Backend | FastAPI |
| Language | Python 3.11+ |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Background Jobs | APScheduler |
| Authentication | JWT + Bcrypt |
| Validation | Pydantic v2 |
| HTTP Client | HTTPX |
| Frontend | React (MVP) |

---

# 📂 Project Structure

```text
DevTrack/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   └── utils/
│
├── docs/
├── tests/
├── alembic/
│
├── README.md
├── requirements.txt
└── .env.example
```

---

# 🚀 Getting Started

## Clone the repository

```bash
git clone https://github.com/your-username/DevTrack.git

cd DevTrack
```

## Create a virtual environment

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
source .venv/bin/activate
```

## Install dependencies

```bash
pip install -r requirements.txt
```

## Configure environment variables

Create a `.env` file.

Example:

```env
DATABASE_URL=postgresql+asyncpg://...
JWT_SECRET_KEY=your-secret-key
```

## Run the application

```bash
python -m uvicorn app.main:app --reload
```

---

# 📖 API Documentation

Once the server is running:

Swagger UI

```
http://127.0.0.1:8000/docs
```

ReDoc

```
http://127.0.0.1:8000/redoc
```

---

# 🧪 Running Tests

```bash
pytest
```

---

# 📚 Documentation

Detailed project documentation is available in the `docs/` directory.

- Software Requirements Specification (SRS)
- Architecture
- Domain Model
- Database Design
- API Specification
- Technology Stack
- Implementation Roadmap
- Architecture Decision Records (ADRs)

---

# 🚧 Current Status

The project is currently under active development.

Current focus:

- ✅ Planning & Architecture
- 🚧 Backend Foundation
- ⏳ GitHub Integration
- ⏳ LeetCode Integration
- ⏳ Analytics Engine
- ⏳ Developer Score
- ⏳ Recommendation Engine
- ⏳ Dashboard APIs
- ⏳ Frontend Dashboard

---

# 🔮 Future Enhancements

- Codeforces Integration
- CodeChef Integration
- HackerRank Integration
- AI-powered Insights
- Resume Analyzer
- Placement Readiness Score
- Email Reports
- Browser Extension

---

# 📄 License

This project is licensed under the MIT License.
