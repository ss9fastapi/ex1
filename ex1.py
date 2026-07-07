from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional, Any, Tuple, Literal

app = FastAPI(
    title="Team Task Manager API",
    description="API quản lý công việc nhóm với định dạng Unified Envelope"
)

tasks_db = [
    {
        "id": 1, 
        "title": "Thiet ke database Shop AI", 
        "description": "Xay dung bang va toi uu index", 
        "assignee": "QuyDev", 
        "priority": 1, 
        "status": "todo",
        "created_at": "2026-07-01T09:00:00Z"
    },
    {
        "id": 2, 
        "title": "Code bo API Authen", 
        "description": "Trien khai filter verify JWT token", 
        "assignee": "FixerQ", 
        "priority": 2, 
        "status": "done",
        "created_at": "2026-07-01T10:00:00Z"
    }
]

def get_current_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

class UnifiedResponse(BaseModel):
    statusCode: int
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str
    path: str

class TaskCreateSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str
    assignee: str
    priority: int = Field(..., ge=1, le=5)

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Tiêu đề không được để trống hoặc chỉ chứa khoảng trắng.")
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Mô tả công việc không được để trống hoặc chỉ chứa khoảng trắng.")
        return v

    @field_validator('assignee')
    @classmethod
    def validate_assignee(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Người được phân công không được để trống.")
        if v != v.strip():
            raise ValueError("Người được phân công không được chứa khoảng trắng ở đầu hoặc cuối.")
        if "  " in v:
            raise ValueError("Người được phân công không được chứa nhiều khoảng trắng liên tiếp.")
        return v

class TaskStatusUpdateSchema(BaseModel):
    status: Literal["todo", "in_progress", "done"]

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "statusCode": 422,
            "message": "Lỗi: Dữ liệu đầu vào không hợp lệ hoặc sai định dạng quy định!",
            "data": None,
            "error": "ERR-VAL-422: Validation error at Request Body fields constraint layout.",
            "timestamp": get_current_timestamp(),
            "path": request.url.path
        }
    )

@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    message = "Yêu cầu không hợp lệ"
    error_code = None

    if isinstance(detail, dict):
        message = detail.get("message", message)
        error_code = detail.get("error", None)
    else:
        message = str(detail)
        error_code = str(detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "statusCode": exc.status_code,
            "message": message,
            "data": None,
            "error": error_code,
            "timestamp": get_current_timestamp(),
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print("Unhandled exception occurred:")
    traceback.print_exc()

    return JSONResponse(
        status_code=500,
        content={
            "statusCode": 500,
            "message": "Đã xảy ra lỗi hệ thống. Vui lòng liên hệ quản trị viên.",
            "data": None,
            "error": f"ERR-SYS-500: {str(exc)}",
            "timestamp": get_current_timestamp(),
            "path": request.url.path
        }
    )


def calculate_team_metrics() -> Tuple[int, int, float]:
    total_tasks = len(tasks_db)
    if total_tasks == 0:
        return 0, 0, 0.0
    completed_tasks = sum(1 for t in tasks_db if t["status"] == "done")
    completion_rate_percentage = round((completed_tasks / total_tasks) * 100.0, 1)
    return total_tasks, completed_tasks, completion_rate_percentage

@app.get("/tasks", response_model=UnifiedResponse)
def get_all_tasks(request: Request, status: Optional[str] = None):
    if status is not None:
        filtered_tasks = [t for t in tasks_db if t["status"] == status]
    else:
        filtered_tasks = tasks_db

    return JSONResponse(
        status_code=200,
        content={
            "statusCode": 200,
            "message": "Lấy danh sách công việc thành công!",
            "data": filtered_tasks,
            "error": None,
            "timestamp": get_current_timestamp(),
            "path": request.url.path
        }
    )

@app.post("/tasks", response_model=UnifiedResponse, status_code=201)
def create_task(request: Request, task_in: TaskCreateSchema):
    title_exists = any(t["title"] == task_in.title for t in tasks_db)
    if title_exists:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Lỗi: Tiêu đề công việc này đã tồn tại trong nhóm!",
                "error": "ERR-TASK-01: Task conflict: Title field duplicates an existing record."
            }
        )

    max_id = max(t["id"] for t in tasks_db) if tasks_db else 0
    new_id = max_id + 1

    new_task = {
        "id": new_id,
        "title": task_in.title,
        "description": task_in.description,
        "assignee": task_in.assignee,
        "priority": task_in.priority,
        "status": "todo",
        "created_at": get_current_timestamp()
    }
    tasks_db.append(new_task)

    return JSONResponse(
        status_code=201,
        content={
            "statusCode": 201,
            "message": "Khởi tạo công việc mới thành công!",
            "data": new_task,
            "error": None,
            "timestamp": get_current_timestamp(),
            "path": request.url.path
        }
    )

@app.put("/tasks/{task_id}", response_model=UnifiedResponse)
def update_task_status(request: Request, task_id: int, status_in: TaskStatusUpdateSchema):
    # Find the task
    task = next((t for t in tasks_db if t["id"] == task_id), None)
    if not task:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Lỗi: Không tìm thấy công việc yêu cầu!",
                "error": "ERR-TASK-03: Task ID not found."
            }
        )

    if task["status"] == "done":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Lỗi: Công việc đã ở trạng thái hoàn thành, không thể cập nhật lùi tiến độ!",
                "error": "ERR-TASK-04: Cannot regress or change status of a completed task."
            }
        )

    task["status"] = status_in.status

    return JSONResponse(
        status_code=200,
        content={
            "statusCode": 200,
            "message": "Cập nhật tiến độ công việc thành công!",
            "data": task,
            "error": None,
            "timestamp": get_current_timestamp(),
            "path": request.url.path
        }
    )

@app.get("/tasks/analytics/dashboard", response_model=UnifiedResponse)
def get_dashboard_analytics(request: Request):
    total_tasks, completed_tasks, completion_rate_percentage = calculate_team_metrics()
    
    analytics_data = {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate_percentage": completion_rate_percentage
    }

    return JSONResponse(
        status_code=200,
        content={
            "statusCode": 200,
            "message": "Lấy số liệu thống kê hiệu suất nhóm thành công!",
            "data": analytics_data,
            "error": None,
            "timestamp": get_current_timestamp(),
            "path": request.url.path
        }
    )
