#!/usr/bin/env python
"""
RQ Worker for background tasks.
Run: python worker.py
"""
from job_queue import redis_conn, job_queue
from rq import Worker

if __name__ == "__main__":
    worker = Worker([job_queue], connection=redis_conn)
    worker.work()
