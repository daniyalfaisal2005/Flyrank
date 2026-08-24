import os
from typing import Optional, Protocol

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, model_validator, field_validator
from psycopg import connect
from psycopg.rows import dict_row

load_dotenv()

app = FastAPI()


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


class TaskRepository(Protocol):
	def list_tasks(self) -> list[dict]:
		...

	def get_task(self, task_id: int) -> Optional[dict]:
		...

	def create_task(self, title: str) -> dict:
		...

	def update_task(self, task_id: int, title: Optional[str], done: Optional[bool]) -> Optional[dict]:
		...

	def delete_task(self, task_id: int) -> bool:
		...


class InMemoryTaskRepository:
	def __init__(self):
		self.tasks = [
			{"id": 1, "title": "Write project proposal", "done": False},
			{"id": 2, "title": "Review sprint notes", "done": True},
			{"id": 3, "title": "Plan next task", "done": False},
		]

	def list_tasks(self) -> list[dict]:
		return self.tasks

	def get_task(self, task_id: int) -> Optional[dict]:
		return next((task for task in self.tasks if task["id"] == task_id), None)

	def create_task(self, title: str) -> dict:
		new_id = max((task["id"] for task in self.tasks), default=0) + 1
		new_task = {"id": new_id, "title": title, "done": False}
		self.tasks.append(new_task)
		return new_task

	def update_task(self, task_id: int, title: Optional[str], done: Optional[bool]) -> Optional[dict]:
		task = self.get_task(task_id)
		if task is None:
			return None
		if title is not None:
			task["title"] = title.strip()
		if done is not None:
			task["done"] = done
		return task

	def delete_task(self, task_id: int) -> bool:
		for index, task in enumerate(self.tasks):
			if task["id"] == task_id:
				del self.tasks[index]
				return True
		return False


class PostgresTaskRepository:
	def __init__(self, database_url: str):
		self.database_url = database_url

	def _connect(self):
		return connect(self.database_url, row_factory=dict_row)

	def _normalize(self, task: dict) -> dict:
		return {
			"id": task["id"],
			"title": task["title"],
			"done": bool(task["done"]),
		}

	def list_tasks(self) -> list[dict]:
		with self._connect() as conn:
			with conn.cursor() as cur:
				cur.execute("SELECT id, title, done FROM tasks ORDER BY id")
				return [self._normalize(row) for row in cur.fetchall()]

	def get_task(self, task_id: int) -> Optional[dict]:
		with self._connect() as conn:
			with conn.cursor() as cur:
				cur.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
				row = cur.fetchone()
				return None if row is None else self._normalize(row)

	def create_task(self, title: str) -> dict:
		with self._connect() as conn:
			with conn.cursor() as cur:
				cur.execute(
					"INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
					(title, False),
				)
				task = cur.fetchone()
			conn.commit()
			return self._normalize(task)

	def update_task(self, task_id: int, title: Optional[str], done: Optional[bool]) -> Optional[dict]:
		existing = self.get_task(task_id)
		if existing is None:
			return None

		updated_title = title.strip() if title is not None else existing["title"]
		updated_done = done if done is not None else existing["done"]

		with self._connect() as conn:
			with conn.cursor() as cur:
				cur.execute(
					"""
					UPDATE tasks
					SET title = %s, done = %s
					WHERE id = %s
					RETURNING id, title, done
					""",
					(updated_title, updated_done, task_id),
				)
				row = cur.fetchone()
			conn.commit()
			return None if row is None else self._normalize(row)

	def delete_task(self, task_id: int) -> bool:
		with self._connect() as conn:
			with conn.cursor() as cur:
				cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
				deleted = cur.rowcount > 0
			conn.commit()
			return deleted


class TaskService:
	def __init__(self, repository: TaskRepository):
		self.repository = repository

	def list_tasks(self) -> list[dict]:
		return self.repository.list_tasks()

	def get_task(self, task_id: int) -> Optional[dict]:
		return self.repository.get_task(task_id)

	def create_task(self, title: str) -> dict:
		return self.repository.create_task(title)

	def update_task(self, task_id: int, title: Optional[str], done: Optional[bool]) -> Optional[dict]:
		return self.repository.update_task(task_id, title, done)

	def delete_task(self, task_id: int) -> bool:
		return self.repository.delete_task(task_id)


def create_repository() -> TaskRepository:
	if os.getenv("TASK_REPOSITORY", "postgres") == "memory":
		return InMemoryTaskRepository()

	database_url = os.getenv("DATABASE_URL")
	if not database_url:
		raise RuntimeError("DATABASE_URL is required when TASK_REPOSITORY is postgres")
	return PostgresTaskRepository(database_url)


service = TaskService(create_repository())


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
	return service.list_tasks()


@app.get("/tasks/{task_id}", description="Return one task by ID.")
def get_task(task_id: int):
	task = service.get_task(task_id)
	if task is None:
		return JSONResponse(status_code=404, content={"error": "Task not found"})
	return task


@app.post("/tasks", status_code=201, description="Create a new task.")
def create_task(task: TaskCreate):
	return service.create_task(task.title)


@app.put("/tasks/{task_id}", description="Update a task by ID.")
def update_task(task_id: int, task: TaskUpdate):
	updated = service.update_task(task_id, task.title, task.done)
	if updated is None:
		return JSONResponse(status_code=404, content={"error": "Task not found"})
	return updated


@app.delete("/tasks/{task_id}", description="Delete a task by ID.")
def delete_task(task_id: int):
	deleted = service.delete_task(task_id)
	if not deleted:
		return JSONResponse(status_code=404, content={"error": "Task not found"})
	return Response(status_code=204)
