# Coding Standards and Code Conventions
**Version:** 1.0.0  
**Status:** Approved  
**Prepared By:** Rachana Gandla  

This document describes the code formatting, style guidelines, typing rules, naming patterns, and commit conventions used in the DevTrack project.

---

## 1. Style & Formatting Standards

*   **PEP 8 Compliance:** All Python source files must adhere to PEP 8 standards.
*   **Formatter & Linter:** We use **Ruff** for linting and code formatting. Rules enforced include:
    *   Single quotes for regular strings where appropriate, double quotes for raw docstrings.
    *   Maximum line length of 100 characters.
    *   Automatic removal of unused imports and sorting of import declarations (conforming to `isort`).
*   **Asynchronous Patterns:**
    *   Database connection methods and repository CRUD calls must utilize `async`/`await` patterns.
    *   Outgoing HTTP calls inside platform clients must use async libraries (e.g. `httpx.AsyncClient`).

---

## 2. Naming Conventions

Consistency across files, variables, and API responses is critical:

| Case Convention | Targets | Examples |
| :--- | :--- | :--- |
| **PascalCase** | Classes, Declarative Models, Pydantic schemas | `User`, `BasePlatformClient`, `DashboardSummary` |
| **snake_case** | Python variables, functions, module paths, table columns | `user_id`, `calculate_score()`, `user_repo.py` |
| **UPPER_CASE** | Global constants, environment configurations | `JWT_SECRET_KEY`, `LOG_LEVEL` |
| **camelCase** | Outgoing API JSON fields | `problemsSolved`, `githubUsername` |

---

## 3. Type Hints

*   **Mandatory Declaration:** All functions, methods, and class properties must include explicit PEP 484 type annotations for inputs and output returns.
*   **Use Standard Collections:** Python 3.11+ syntax is preferred (e.g. `list[str]` instead of `typing.List[str]`, and `int | None` instead of `typing.Optional[int]`).

```python
# Standard Compliant Code Example
async def get_user_score_history(user_id: str, limit: int = 10) -> list[DeveloperScore]:
    ...
```

---

## 4. Layer Separation Policy (Repository vs Service)

To avoid spaghetti code, developer modules must follow this strict rule:

### 4.1 Repository Layer (`app/repositories/`)
*   **Allowed Operations:** Executes raw SQL/SQLAlchemy statements, filters entities, executes joins, and handles database transactions.
*   **Prohibited Operations:** Repositories must *never* contain business calculations, math scoring formulas, or outgoing network calls to third-party endpoints.

### 4.2 Service Layer (`app/services/`)
*   **Allowed Operations:** Scoring math rules, snapshot extraction, insights comparisons, and task schedules.
*   **Prohibited Operations:** Services must *never* execute raw SQL or construct SQLAlchemy queries directly. They delegate database writes to the Repository layer.

---

## 5. Commit Message Guidelines

All Git commits must utilize semantic prefixes so progress history remains readable and clean:

| Commit Prefix | Scenario | Example |
| :--- | :--- | :--- |
| **`feat(...)`** | Addition of a new feature | `feat(auth): implement registration endpoint` |
| **`fix(...)`** | Resolution of a bug | `fix(sync): resolve rate limit backoff delay crash` |
| **`docs(...)`** | Updates to markdown documents | `docs(readme): update setup guidelines` |
| **`refactor(...)`**| Code alteration that does not change functional behavior | `refactor(score): isolate scoring formulas into pure functions` |
| **`test(...)`** | Adding or fixing test suites | `test(api): write login auth checks` |
| **`setup(...)`** | Setting up local environments, dependencies, configs | `setup: configure Alembic migration scripts` |
