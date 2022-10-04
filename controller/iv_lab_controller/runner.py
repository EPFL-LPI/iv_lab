from collections import deque
from typing import Union

from pymeasure.experiments.workers import Worker

from .measurements.base_classes.result import Result


class Runner():
    """
    An experiment runner.
    """

    def __init__(self):
        """
        """
        self._result_queue: deque[Result] = deque()
        self._active_worker: Union[Worker, None] = None

    @property
    def result_queue(self) -> deque[Result]:
        """
        :returns: The procedure queue.
        """
        return self._result_queue

    @property
    def active_worker(self) -> Union[Worker, None]:
        """
        :returns: Result of active worker, or None.
        """
        return self._active_worker

    def run_next(self):
        """
        Starts the next measurement.
        """
        result = self._result_queue.popleft()
        self._active_worker = Worker(result)

        self.active_worker.start()
        self.active_worker.join()
        self._active_worker = None
