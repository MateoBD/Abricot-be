"""
Simple async notification queue with exponential backoff retry logic.

Alternative to Celery: uses threading + queue for async email dispatch.
"""

import logging
import threading
import time
from queue import Queue, Empty
from typing import Callable
from uuid import UUID

logger = logging.getLogger(__name__)


class AsyncNotificationWorker:
    """Worker that processes notification jobs from a queue with retries."""

    def __init__(self, send_func: Callable[[str, str, str, UUID | None], bool]):
        """
        Initialize worker.

        Args:
            send_func: Callable(to, subject, body, event_id) -> bool
        """
        self._send_func = send_func
        self._queue: Queue = Queue()
        self._worker_thread: threading.Thread | None = None
        self._running = False
        self._stats = {"sent": 0, "failed": 0, "retried": 0}

    def start(self) -> None:
        """Start the worker thread."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=False)
        self._worker_thread.start()
        logger.info("async_worker_started")

    def stop(self, timeout: float = 10.0) -> None:
        """Stop worker and wait for pending jobs."""
        if not self._running:
            return
        self._running = False
        self._queue.join()
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
        logger.info("async_worker_stopped", extra={"sent": self._stats["sent"], "failed": self._stats["failed"]})

    def enqueue(
        self,
        recipient: str,
        subject: str,
        body: str,
        event_id: UUID | None = None,
    ) -> None:
        """Enqueue a notification job."""
        job = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "event_id": event_id,
            "retry_count": 0,
            "max_retries": 3,
        }
        self._queue.put(job)
        logger.debug(
            "notification_job_enqueued",
            extra={"recipient": recipient, "queue_size": self._queue.qsize()},
        )

    def _worker_loop(self) -> None:
        """Main worker loop: process jobs with retry logic."""
        while self._running:
            try:
                job = self._queue.get(timeout=1.0)
            except Empty:
                continue

            try:
                self._process_job(job)
            finally:
                self._queue.task_done()

    def _process_job(self, job: dict) -> None:
        """Process a job: send email or retry/fail."""
        try:
            success = self._send_func(
                to=job["recipient"],
                subject=job["subject"],
                body=job["body"],
                event_id=job["event_id"],
            )

            if success:
                self._stats["sent"] += 1
                logger.info(
                    "notification_job_sent",
                    extra={"recipient": job["recipient"], "retries": job["retry_count"]},
                )
                return

            # Send failed — prepare for retry or dead-letter
            if job["retry_count"] < job["max_retries"]:
                job["retry_count"] += 1
                backoff = 2 ** (job["retry_count"] - 1)  # 2, 4, 8 seconds
                self._stats["retried"] += 1
                logger.warning(
                    "notification_job_retry",
                    extra={
                        "recipient": job["recipient"],
                        "retry": job["retry_count"],
                        "backoff_sec": backoff,
                    },
                )
                time.sleep(backoff)
                self._queue.put(job)  # Re-queue
            else:
                self._stats["failed"] += 1
                logger.error(
                    "notification_job_dead_letter",
                    extra={
                        "recipient": job["recipient"],
                        "max_retries": job["max_retries"],
                    },
                )

        except Exception as e:
            # Unexpected error
            if job["retry_count"] < job["max_retries"]:
                job["retry_count"] += 1
                self._stats["retried"] += 1
                logger.warning(
                    "notification_job_exception_retry",
                    extra={"recipient": job["recipient"], "error": str(e)},
                    exc_info=True,
                )
                time.sleep(2 ** (job["retry_count"] - 1))
                self._queue.put(job)
            else:
                self._stats["failed"] += 1
                logger.error(
                    "notification_job_exception_dead_letter",
                    extra={"recipient": job["recipient"], "error": str(e)},
                    exc_info=True,
                )

    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {**self._stats, "queue_size": self._queue.qsize()}
