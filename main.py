from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import uuid

app = FastAPI()

# ✅ CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Scheduler setup
scheduler = BackgroundScheduler()
scheduler.start()

# ✅ Database setup
Base = declarative_base()
engine = create_engine("sqlite:///jobs.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class JobModel(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    type = Column(String)
    time = Column(String)
    enabled = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)

class LogModel(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String)
    job_name = Column(String)
    run_time = Column(DateTime)
    output = Column(String)

Base.metadata.create_all(bind=engine)

# ✅ Pydantic models
class JobCreate(BaseModel):
    name: str
    type: str
    time: str
    enabled: Optional[bool] = True

class JobOut(BaseModel):
    id: str
    name: str
    type: str
    time: str
    enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]

class LogOut(BaseModel):
    job_id: str
    job_name: str
    run_time: datetime
    output: str

# ✅ Job logic
def run_job(job_id: str):
    db = SessionLocal()
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        return

    job.last_run = datetime.now()
    log = LogModel(
        job_id=job.id,
        job_name=job.name,
        run_time=job.last_run,
        output="Hello World"
    )
    db.add(log)
    db.commit()

    try:
        aps_job = scheduler.get_job(job.id)
        job.next_run = aps_job.next_run_time if aps_job else None
    except:
        pass

    db.commit()
    db.close()
    print(f"[{datetime.now()}] Ran job: {job.name}")

def schedule_job(job: JobModel):
    if job.enabled:
        if job.type == "hourly":
            trigger = CronTrigger(minute=job.time)
        elif job.type == "daily":
            hour, minute = map(int, job.time.split(":"))
            trigger = CronTrigger(hour=hour, minute=minute)
        elif job.type == "weekly":
            day, hm = job.time.split(" ")
            hour, minute = map(int, hm.split(":"))
            trigger = CronTrigger(day_of_week=day.lower(), hour=hour, minute=minute)
        else:
            return
        scheduler.add_job(run_job, trigger, args=[job.id], id=job.id, replace_existing=True)

# ✅ API endpoints
@app.post("/jobs", response_model=JobOut)
def create_job(job_data: JobCreate):
    db = SessionLocal()
    job_id = str(uuid.uuid4())
    job = JobModel(
        id=job_id,
        name=job_data.name,
        type=job_data.type,
        time=job_data.time,
        enabled=job_data.enabled
    )
    db.add(job)
    db.commit()
    schedule_job(job)
    db.refresh(job)
    db.close()
    return job

@app.get("/jobs", response_model=List[JobOut])
def list_jobs():
    db = SessionLocal()
    jobs = db.query(JobModel).all()
    db.close()
    return jobs

@app.post("/jobs/{job_id}/run")
def run_now(job_id: str):
    try:
        run_job(job_id)
        return {"status": "Job triggered manually"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/jobs/{job_id}/toggle")
def toggle_job(job_id: str):
    db = SessionLocal()
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.enabled = not job.enabled
    db.commit()

    if job.enabled:
        schedule_job(job)
    else:
        scheduler.remove_job(job.id)

    db.refresh(job)
    db.close()
    return {"status": "Toggled", "enabled": job.enabled}

@app.get("/logs", response_model=List[LogOut])
def get_logs():
    db = SessionLocal()
    logs = db.query(LogModel).order_by(LogModel.run_time.desc()).all()
    db.close()
    return logs

# ✅ Initial job scheduling on server startup
def load_jobs():
    db = SessionLocal()
    jobs = db.query(JobModel).filter(JobModel.enabled == True).all()
    for job in jobs:
        schedule_job(job)
    db.close()

load_jobs()
