import sqlite3
from contextlib import closing
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator, model_validator

app = FastAPI()

DB_PATH = "tasks.db"
SEED_TASKS = [
	("Write project proposal", 0),
	("Review sprint notes", 1),
	("Plan next task", 0),
]


def get_connection() -> sqlite3.Connection:
	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	return conn


def row_to_task(row: sqlite3.Row) -> dict:
	return {
		"id": row["id"],
		"title": row["title"],
		"done": bool(row["done"]),
	}


def init_db() -> None:
	with closing(get_connection()) as conn:
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS tasks (
				id INTEGER PRIMARY KEY,
				title TEXT NOT NULL,
				done INTEGER NOT NULL CHECK (done IN (0, 1))
			)
			"""
		)

		row_count = conn.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()["total"]
		if row_count == 0:
			conn.executemany(
				"INSERT INTO tasks (title, done) VALUES (?, ?)",
				SEED_TASKS,
			)
		conn.commit()


@app.on_event("startup")
def on_startup() -> None:
	init_db()


class TaskCreate(BaseModel):
	title: str = Field(..., min_length=1)

	@field_validator("title")
	@classmethod
	def title_must_not_be_blank(cls, value: str) -> str:
		value = value.strip()
		if not value:
			raise ValueError("Title is required and cannot be empty")
		return value


class TaskUpdate(BaseModel):
	title: Optional[str] = None
	done: Optional[bool] = None

	@model_validator(mode="after")
	def validate_fields(self):
		if self.title is None and self.done is None:
			raise ValueError("At least one of title or done must be provided")
		if self.title is not None and not self.title.strip():
			raise ValueError("Title cannot be empty")
		return self


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
	first_error = exc.errors()[0]
	message = first_error.get("msg", "Invalid request")
	return JSONResponse(status_code=400, content={"error": message})


@app.get("/", description="Return Task API metadata.")
def read_root():
	return {
		"name": "Task API",
		"version": "1.0",
		"endpoints": ["/tasks"],
	}


@app.get("/health", description="Check whether the API is healthy.")
def health_check():
	return {"status": "ok"}


@app.get("/tasks", description="List all tasks.")
def get_tasks():
	with closing(get_connection()) as conn:
		rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
		return [row_to_task(row) for row in rows]


@app.get("/tasks/{task_id}", description="Return one task by ID.")
def get_task(task_id: int):
	with closing(get_connection()) as conn:
		row = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
		if row is None:
			return JSONResponse(status_code=404, content={"error": "Task not found"})
		return row_to_task(row)


@app.post("/tasks", status_code=201, description="Create a new task.")
def create_task(task: TaskCreate):
	with closing(get_connection()) as conn:
		cursor = conn.execute(
			"INSERT INTO tasks (title, done) VALUES (?, ?)",
			(task.title, 0),
		)
		conn.commit()
		new_id = cursor.lastrowid

		row = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (new_id,)).fetchone()
		return row_to_task(row)


@app.put("/tasks/{task_id}", description="Update a task by ID.")
def update_task(task_id: int, task: TaskUpdate):
	with closing(get_connection()) as conn:
		existing = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
		if existing is None:
			return JSONResponse(status_code=404, content={"error": "Task not found"})

		updated_title = task.title.strip() if task.title is not None else existing["title"]
		updated_done = int(task.done) if task.done is not None else existing["done"]

		conn.execute(
			"UPDATE tasks SET title = ?, done = ? WHERE id = ?",
			(updated_title, updated_done, task_id),
		)
		conn.commit()

		row = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
		return row_to_task(row)


@app.delete("/tasks/{task_id}", description="Delete a task by ID.")
def delete_task(task_id: int):
	with closing(get_connection()) as conn:
		cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
		conn.commit()
		if cursor.rowcount == 0:
			return JSONResponse(status_code=404, content={"error": "Task not found"})
		return Response(status_code=204)


if __name__ == "__main__":
	import uvicorn

	uvicorn.run(app, host="127.0.0.1", port=8000)
