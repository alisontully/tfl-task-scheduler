# TFL Task Scheduler

A RESTful service built with **FastAPI**, **SQLAlchemy**, and **APScheduler** that lets you schedule tasks to query [Transport for London (TFL) Line API](https://api.tfl.gov.uk/) disruptions at a specific time and store the results.  

This project was developed as part of the **WovenLight development exercise**.  

---

## Features

- Schedule a task at a given time for one or more TFL lines.  
- Store the results of disruption queries in a database.  
- Retrieve all tasks or a single task (with results if completed).  
- Update or delete tasks before they run.  
- REST API built with FastAPI.  
- Jobs scheduled and run in the background using APScheduler.  
- Database managed with SQLAlchemy (SQLite by default).  
- Pre-commit hooks for formatting, linting, typing, and security checks.  
- Packaged and containerized with Docker.  

---

## Project Structure

```
src/tfl_task_scheduler/
│   main.py          # FastAPI entrypoint
│   db.py            # Database setup
│   models.py        # SQLAlchemy models
│   schemas.py       # Pydantic schemas
│   scheduler.py     # APScheduler integration
│   worker.py        # Task runner that calls TFL API
│
└── api/
    tasks.py         # REST endpoints for /tasks

tests/
    fixtures.py       # Shared pytest fixtures
    test_tasks.py     # API tests
    test_scheduler.py # Scheduler tests
```

---

## Requirements

- Python **3.12**
- Conda (for environment management) or Docker  

---

## Setup (Local with Conda + Poetry)

```bash
# Create environment
ENV_NAME=venv-tfl PYTHON_VERSION=3.12 ./setup.sh

# Activate
conda activate venv-tfl

# Run the app
poetry run uvicorn tfl_task_scheduler.main:app --reload --port 5555
```

---

## Setup (Docker)

```bash
# Build
docker compose build

# Up (foreground)
docker compose up

# Up (detached)
docker compose up -d

# Logs / status
docker compose logs -f
docker compose ps

# Stop + remove containers and network
docker compose down

# Stop + remove containers, network, and volumes (DB is deleted)
docker compose down -v
```

App will be available at:  
👉 [http://localhost:5555/docs](http://localhost:5555/docs) (interactive Swagger UI)

---

## Example Usage

Create a task for the Victoria line at a future time:
```bash
curl -X POST -H "Content-Type: application/json"   -d '{"schedule_time":"2025-09-03T16:45:00","lines":"victoria"}'   http://localhost:5555/tasks/
```

List all tasks:
```bash
curl http://localhost:5555/tasks/
```

Get results of a specific task:
```bash
curl http://localhost:5555/tasks/<task_id>
```

Update a scheduled time:
```bash
curl -X PATCH -H "Content-Type: application/json"   -d '{"schedule_time":"2025-08-27T18:00:00"}'   http://localhost:5555/tasks/<task_id>
```

Update a line:
```bash
curl -X PATCH -H "Content-Type: application/json"   -d '{"lines":"central"}'   http://localhost:5555/tasks/<task_id>
```

> **Note:** `PATCH /tasks/{task_id}` updates (changing `schedule_time` or `lines`) are **only allowed for tasks that haven’t run yet**. If a task already has a result, the API returns **400 Bad Request** with `{"detail":"Cannot update a task that has already run"}`.


Delete a task:
```bash
curl -X DELETE http://localhost:5555/tasks/<task_id>
```

Delete all tasks:
```bash
curl -X DELETE http://localhost:5555/tasks/
```

---

## Running Tests

```bash
poetry run pytest
```

---

## Development Workflow

- Code formatting: **Black**
- Import sorting: **isort**
- Linting: **Ruff** + **Pylint**
- Security scan: **Bandit**
- Typing: **Mypy**
- Docstring style: **Pydocstyle**

Pre-commit hooks enforce these automatically:
```bash
poetry run pre-commit run --all-files
```

---

## Limitations

- Uses SQLite (not production-ready for concurrency).  
- Tasks run in-process; no distributed scheduler.  
- No authentication or multi-user separation.  
- Results are stored as raw JSON strings from TFL API.  

---

## Time Spent

~X–Y hours.
