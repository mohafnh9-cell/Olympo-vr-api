from pydantic import BaseModel
from enum import Enum
from typing import Optional

class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"

class Job(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.queued
    progress: int = 0
    error: Optional[str] = None
    vocals_master_url: Optional[str] = None
    instrumental_master_url: Optional[str] = None