from fastapi import FastAPI, HTTPException

app = FastAPI()

TASKS = [
    {"id": 1, "title": "Write project proposal", "done": False},
    {"id": 2, "title": "Review sprint notes", "done": True},
    {"id": 3, "title": "Plan next task", "done": False},
]


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
