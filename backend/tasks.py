"""
Background tasks for RQ workers.
"""
from database import SessionLocal
from ai_analysis import process_report as analyze_report


def process_report(report_id: str, file_path: str, org_id: int):
    """
    Background task: process a report (parse, analyze, compare).
    Called by the job queue.
    """
    db = SessionLocal()
    try:
        result = analyze_report(report_id, file_path, org_id, db)
        return result
    finally:
        db.close()
