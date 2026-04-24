import threading
import queue
import logging
from typing import Callable
from flask import Flask
logger = logging.getLogger("TaskProcessor")


class TaskProcessor:
    def __init__(self, name, max_queue_size: int = 0):
        self.name = name
        self.task_queue = queue.Queue(maxsize=max_queue_size)
        self._stop_event = threading.Event()
        self.worker_thread = None
        self.is_running = False

    def _worker(self):
        logger.info(f"{self.name}: Working thread is started")
        while not self._stop_event.is_set():
            try:
                task = self.task_queue.get(timeout=1)
                if task is None:
                    logger.info(f"{self.name}: Stopping worker thread")
                    self.task_queue.task_done()
                    break
                self._execute_task(task)
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"{self.name}: Error when execute task: {e}")
        logger.info(f"{self.name}: Working thread is completed")

    def _execute_task(self, task: dict):
        try:
            with self.app.app_context():
                func = task['func']
                args = task.get('args', ())
                kwargs = task.get('kwargs', {})
                logger.info(f"{self.name}: Start executed task {func.__name__} with args {args} and kwargs {kwargs}")
                result = func(*args, **kwargs)
                logger.info(f"{self.name}: Task executed successfully: {func.__name__}, result: {result}")
        except Exception as e:
            logger.error(f"{self.name}: Error in task {func.__name__}: {e}")
            self.task_queue.task_done()
            raise

    def start(self, app: Flask):
        if self.is_running:
            logger.warning(f"{self.name}: Processor is already running")
            return

        self.is_running = True
        self.app = app
        self.worker_thread = threading.Thread(
            target=self._worker,
            name="TaskWorker"
        )
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logger.info(f"{self.name}: Task processor is started")

    def stop(self, wait: bool = True):
        if not self.is_running:
            return

        logger.info(f"{self.name}: Stopping task processor...")
        self._stop_event.set()
        self.task_queue.put(None)

        if wait and self.worker_thread:
            self.worker_thread.join(timeout=5)
            if self.worker_thread.is_alive():
                logger.warning(f"{self.name}: Task processor is not stopped")

        self.is_running = False
        logger.info(f"{self.name}: Task processor is stopped")

    def add_task(self, func: Callable, *args, **kwargs):
        task = {
            'func': func,
            'args': args,
            'kwargs': kwargs
        }
        self.task_queue.put(task)
        logger.info(f"{self.name}: Task is added: {func.__name__}")

    def wait_completion(self):
        self.task_queue.join()
        logger.info(f"{self.name}: All task is completed")