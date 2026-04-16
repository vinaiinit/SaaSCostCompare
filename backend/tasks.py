"""
Background tasks for RQ workers.
"""
from database import SessionLocal
from ai_analysis import process_upload


def process_report(report_id: str, file_path: str, org_id: int):
    """
    Background task: extract structured data from uploaded files.
    Called by the job queue.
    """
    db = SessionLocal()
    try:
        result = process_upload(report_id, file_path, org_id, db)
        return result
    finally:
        db.close()
