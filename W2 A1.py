from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

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


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Title is required and cannot be empty"})


@app.get("/")
def read_root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/tasks")
def get_tasks():
    return TASKS


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = next((item for item in TASKS if item["id"] == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    new_id = max((item["id"] for item in TASKS), default=0) + 1
    new_task = {"id": new_id, "title": task.title, "done": False}
    TASKS.append(new_task)
    return new_task


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
