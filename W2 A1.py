from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator, model_validator

app = FastAPI()

TASKS = [
    {"id": 1, "title": "Write project proposal", "done": False},
    {"id": 2, "title": "Review sprint notes", "done": True},
    {"id": 3, "title": "Plan next task", "done": False},
]


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
    return JSONResponse(status_code=400, content={"error": "Title is required and cannot be empty"})


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
    return TASKS


@app.get("/tasks/{task_id}", description="Return one task by ID.")
def get_task(task_id: int):
    task = next((item for item in TASKS if item["id"] == task_id), None)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    return task


@app.post("/tasks", status_code=201, description="Create a new task.")
def create_task(task: TaskCreate):
    new_id = max((item["id"] for item in TASKS), default=0) + 1
    new_task = {"id": new_id, "title": task.title, "done": False}
    TASKS.append(new_task)
    return new_task


@app.put("/tasks/{task_id}", description="Update a task by ID.")
def update_task(task_id: int, task: TaskUpdate):
    for existing in TASKS:
        if existing["id"] == task_id:
            if task.title is not None:
                existing["title"] = task.title.strip()
            if task.done is not None:
                existing["done"] = task.done
            return existing
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


@app.delete("/tasks/{task_id}", description="Delete a task by ID.")
def delete_task(task_id: int):
    for index, task in enumerate(TASKS):
        if task["id"] == task_id:
            del TASKS[index]
            return Response(status_code=204)
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
