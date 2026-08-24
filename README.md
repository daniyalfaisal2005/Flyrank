# Task API (W3 A2)

This version runs FastAPI + Postgres together with Docker Compose and stores tasks in Postgres instead of in-memory storage.

## Goal

Run Postgres in Docker, connect the service to it through a repository layer, and start the full stack with one command.

## Stack

- App: FastAPI
- Database: Postgres 16 (Docker)
- Orchestration: Docker Compose
- Config: `.env` (ignored) + `.env.example` (committed)

## Project files for A2

- API and layering: `W3 A2.py`
- Compose stack: `docker-compose.yml`
- App image: `Dockerfile`
- DB schema/init SQL: `sql/init.sql`
- Env template: `.env.example`

## Environment variables

Copy `.env.example` to `.env` and keep `.env` private.

Example values:

```env
POSTGRES_USER=task_user
POSTGRES_PASSWORD=task_password
POSTGRES_DB=tasks_db
DATABASE_URL=postgresql://task_user:task_password@db:5432/tasks_db
TASK_REPOSITORY=postgres
```

## Run with one command

```powershell
docker compose up --build
```

App: `http://127.0.0.1:8000`

Swagger UI: `http://127.0.0.1:8000/docs`

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/` | Return API metadata |
| GET | `/health` | Check API health |
| GET | `/tasks` | List all tasks |
| GET | `/tasks/{task_id}` | Return one task |
| POST | `/tasks` | Create a task |
| PUT | `/tasks/{task_id}` | Update a task |
| DELETE | `/tasks/{task_id}` | Delete a task |

## Architecture note (service/routes unchanged)

Routes call `TaskService`, and `TaskService` depends on a repository interface. The storage swap is done by changing which repository is created (`PostgresTaskRepository` vs `InMemoryTaskRepository`), without rewriting route logic.

## SQL table creation

The table is created from `sql/init.sql` when the Postgres container initializes:

```sql
CREATE TABLE IF NOT EXISTS tasks (
	id SERIAL PRIMARY KEY,
	title TEXT NOT NULL,
	done BOOLEAN NOT NULL DEFAULT FALSE
);
```

## Persistence proof steps

1. Start stack:

```powershell
docker compose up --build
```

2. Create a task:

```powershell
curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d '{"title":"survive restart"}'
```

3. Confirm it exists:

```powershell
curl http://127.0.0.1:8000/tasks
```

4. Restart app + db containers:

```powershell
docker compose down
docker compose up --build
```

5. Confirm the same task still exists:

```powershell
curl http://127.0.0.1:8000/tasks
```

Because Postgres uses a named Docker volume (`pgdata`), rows persist across restarts.

Observed check in this repo:

- Created task: `persist after restart`
- Restarted both containers with `docker compose restart app db`
- Verified the same task still existed in `GET /tasks`
