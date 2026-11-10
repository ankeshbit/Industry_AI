"""
Background Worker Process for INDUSTRIA AI (PRD v1.2 §8.5, §18.3, AC-JOB-1..5)
Polls the jobs table, claims jobs, updates heartbeats, and executes workloads.
"""

import os
import sys
import time
import uuid
import logging
from datetime import datetime

from backend.app.database import SessionLocal
from backend.app.services.queue_service import claim_next_job, execute_job_synchronous

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker")

def run_worker_loop(worker_id: str = None, poll_interval: float = 1.0, max_iterations: int = None):
    """Worker polling loop claiming and running jobs."""
    if not worker_id:
        worker_id = f"worker-{os.getpid()}-{str(uuid.uuid4())[:8]}"

    logger.info(f"Starting background worker: {worker_id}")
    iterations = 0

    while True:
        if max_iterations is not None and iterations >= max_iterations:
            break
        iterations += 1

        db = SessionLocal()
        try:
            job = claim_next_job(db, worker_id)
            if job:
                logger.info(f"Claimed job {job.id} (type: {job.job_type}, org: {job.organisation_id})")
                execute_job_synchronous(db, job)
                logger.info(f"Finished job {job.id} with status: {job.status}")
            else:
                time.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Worker iteration error: {e}", exc_info=True)
            time.sleep(poll_interval)
        finally:
            db.close()

if __name__ == "__main__":
    run_worker_loop()

