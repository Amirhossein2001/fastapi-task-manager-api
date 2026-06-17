from database import engine, Base
import models
from sqlalchemy.orm import Session
from models import Task
from schemas import TaskCreate, TaskResponse
from typing import List
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth import hash_password
from fastapi import HTTPException
from auth import verify_password, create_access_token, get_current_user
from schemas import TaskCreate
from schemas import UserCreate, UserResponse


app = FastAPI()

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    

@app.get("/")
def home():
    return {"message": "API is working 🚀"}

@app.post("/tasks")
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    db_user = db.query(User).filter(User.username == user).first()

    new_task = Task(
        title=task.title,
        description=task.description,
        user_id=db_user.id
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task

@app.get("/tasks")
def get_tasks(
    page: int = 1,
    limit: int = 10,
    done: bool = None,
    title: str = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    db_user = db.query(User).filter(User.username == user).first()

    offset = (page - 1) * limit

    query = db.query(Task).filter(Task.user_id == db_user.id)

    # 🔥 Filter 1: done or not done
    if done is not None:
        query = query.filter(Task.done == done)

    # 🔥 Filter 2: search by title
    if title:
        query = query.filter(Task.title.contains(title))

    tasks = query.offset(offset).limit(limit).all()

    return tasks

@app.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    db_user = db.query(User).filter(User.username == user).first()

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == db_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()

    return {"message": "Task deleted"}


@app.put("/tasks/{task_id}")
def update_task(
    task_id: int,
    updated_task: TaskCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    db_user = db.query(User).filter(User.username == user).first()

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == db_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.title = updated_task.title
    task.description = updated_task.description

    db.commit()
    db.refresh(task)

    return task

@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.username == user.username).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed = hash_password(user.password)

    new_user = User(
        username=user.username,
        hashed_password=hashed
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
@app.post("/login")
def login(user: dict, db: Session = Depends(get_db)):

    db_user = db.query(User).filter(User.username == user["username"]).first()

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(user["password"], db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(data={"sub": db_user.username})

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@app.get("/db-test")
def test(db: Session = Depends(get_db)):
    return {"status": "DB connected"}