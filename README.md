# Task API

A small in-memory to-do list API built with Python and FastAPI.

## Run

Use Python 3.14 or newer with compatible FastAPI wheels:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python "W2 A1.py"
```

The API runs at `http://127.0.0.1:8000`. Swagger UI is available at `http://127.0.0.1:8000/docs`.

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

## curl example

```powershell
curl http://127.0.0.1:8000/health
```

Output:

```json
{"status":"ok"}
```

## Swagger screenshot

![FastAPI Swagger UI](swagger.png)
