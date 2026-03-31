import redis
from rq import Queue
from datetime import datetime
import os

# Initialize Redis connection
redis_conn = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
job_queue = Queue(connection=redis_conn)


def enqueue_report_processing(report_id: str, file_path: str, org_id: int):
    """
    Enqueue a report for processing (parsing, AI analysis, comparison).
    """
    job = job_queue.enqueue(
        "tasks.process_report",
        report_id,
        file_path,
        org_id,
        job_timeout="30m",
    )
    return job.id


def get_job_status(job_id: str):
    """
    Check the status of a queued job.
    """
    from rq.job import Job
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        return {
            "id": job.id,
            "status": job.get_status(),
            "result": job.result,
            "error": job.exc_info,
        }
    except:
        return None
