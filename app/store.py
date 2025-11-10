from typing import Dict, Optional
from .models import Job

# Simula una base de datos en memoria
_JOBS: Dict[str, Job] = {}

def create_job(job: Job):
    _JOBS[job.job_id] = job
    return job

def get_job(job_id: str) -> Optional[Job]:
    return _JOBS.get(job_id)

def update_job(job_id: str, **fields) -> Optional[Job]:
    job = _JOBS.get(job_id)
    if not job:
        return None
    for k, v in fields.items():
        setattr(job, k, v)
    _JOBS[job_id] = job
    return job