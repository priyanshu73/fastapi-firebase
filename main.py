from typing import Dict, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import pyrebase
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)



# Pyrebase configuration for Firebase
config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": "chore-chart-397cc.firebaseapp.com",
    "databaseURL": "https://chore-chart-397cc-default-rtdb.firebaseio.com/",
    "storageBucket": "chore-chart-397cc.appspot.com",
    "serviceAccount": os.getenv("FIREBASE_SERVICE_ACCOUNT")  # Path to service account
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

# Global variable to store task data
tasks_data = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan function to load tasks at startup."""
    load_tasks()  # Load tasks when the application starts
    yield  # Yield control to allow app operation

app = FastAPI(lifespan=lifespan)

# CORS configuration for allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://aptchorechart.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TaskUpdate(BaseModel):
    taskType: str
    name: str
    completed: bool
    date: str

def fetch_tasks() -> Dict[str, List[Dict]]:
    """Fetch all tasks from Firebase Realtime Database."""
    try:
        tasks = db.get().val()
        return tasks if tasks else {}
    except Exception as e:
        logging.error(f"Error fetching tasks: {e}")
        raise HTTPException(status_code=500, detail="Error fetching tasks from database")

def load_tasks():
    """Load tasks into the global variable."""
    global tasks_data
    tasks_data = fetch_tasks()

def update_json_data(update_dict: Dict):
    """Update the Firebase database with the provided dictionary."""
    try:
        db.update(update_dict)  # Use update to preserve existing data
    except Exception as e:
        logging.error(f"Error updating tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to update tasks")

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/tasks")
def get_tasks():
    """Retrieve tasks data."""
    return {"tasks": tasks_data if tasks_data else {}}

@app.put("/update_task")
def update_task(task_update: TaskUpdate):
    """Update a specific task's completion status and date."""
    taskType = task_update.taskType
    name = task_update.name
    completed = task_update.completed
    date = task_update.date

    if taskType not in tasks_data:
        raise HTTPException(status_code=404, detail="Task type not found")

    for entry in tasks_data[taskType]:
        if entry["name"] == name:
            entry["completed"] = completed
            entry["date"] = date
            update_json_data(tasks_data)  # Update Firebase data
            return {"message": "Task updated successfully"}

    raise HTTPException(status_code=404, detail="Task not found")

@app.put("/reset")
def reset_table():
    """Reset the completion status and date for all tasks."""
    if not tasks_data:  # Check if tasks exist to reset
        return {"message": "No tasks to reset."}

    for task_type in tasks_data:
        for entry in tasks_data[task_type]:
            entry["completed"] = False
            entry["date"] = ""

    update_json_data(tasks_data)  

    return {"message": "Table Reset Successful"}
