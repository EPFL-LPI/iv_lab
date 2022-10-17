"""
Functionality related to running experiments.
"""
import os
import sys
import logging
from collections import deque
from typing import Union, Tuple, Type


from PyQt6.QtCore import QThread, pyqtSignal
from pymeasure.experiment import Worker

from . import common
from . import Store
from .types import PathLike, RunnerState
from .base_classes import (
    Results,
    Experiment,
)
from .parameters import CompleteParameters


ExperimentInfo = Tuple[Type[Experiment], CompleteParameters]

# create typing for dequeue[Results] based on python version
if sys.version_info < (3, 9, 0):
    from typing_extensions import Annotated
    ResultsDeque = Annotated[deque, Results]
    ExperimentInfoDeque = Annotated[deque, ExperimentInfo]

else:
    ResultsDeque = deque[Results]
    ExperimentInfoDeque = deque[ExperimentInfo]

logger = logging.getLogger('iv_lab')


class ResultsRunner(QThread):
    """
    Runs `Results` in a separate thread to allow the UI to remian unblocked.
    """
    progress = pyqtSignal(Results, int, int)  # current results, index, total

    def __init__(self, results_queue: ResultsDeque):
        super().__init__()

        self.active_worker: Union[Worker, None] = None
        self.results_queue = results_queue

    def run(self):
        o_len = len(self.results_queue)

        # run results
        i = 0
        while len(self.results_queue) > 0:
            while self.active_worker is not None:
                # wait for worker to be free
                QThread.sleep(0.25)

            results = self.results_queue.popleft()
            self.active_worker = Worker(results)

            self.progress.emit(results, i, o_len)
            self.active_worker.start()
            self.active_worker.join(3600)  # @note: Hardcoded timeout may need to be changed.

            i += 1
            self.active_worker = None

            # copy resutls to admin
            try:
                copy_results_to_admin(results)

            except Exception as err:
                logger.debug('[runner] Error copying result to admin\n%s', err)

    def stop(self):
        """
        Stops the current experiment and prevents more from running.
        """
        self.results_queue.clear()
        self.active_worker.stop()


class Runner():
    """
    Experiment runner.
    """
    def __init__(self):
        """
        """
        self._state: RunnerState = RunnerState.Standby
        self._queue: deque[ExperimentInfo] = deque()
        self._results_queue: ResultsDeque = deque()
        self._results_runner: Union[ResultsRunner, None] = None

    @property
    def state(self) -> RunnerState:
        """
        :returns: Runner state.
        """
        return self._state

    def _set_state(self, state: RunnerState):
        self._state = state
        Store.set('runner_state', self.state)

    @property
    def queue(self) -> ExperimentInfoDeque:
        """
        :returns: The procedure queue.
        """
        return self._queue

    def queue_experiment(
        self,
        experiment: Type[Experiment],
        parameters: CompleteParameters
    ):
        """
        Queues an experiment to be run.

        :param experiment: Experiment to be run.
        :param parameters: Parameters to use.
        """
        self._queue.append((experiment, parameters))

    def clear_queue(self):
        """
        Clears the experiment queue.
        """
        self._queue.clear()

    def run(self, cell_name: str):
        """
        Runs all experiments in the queue.

        :param name: Name of the cell.
        """
        self._set_state(RunnerState.Running)
        Store.set('status_msg', 'Running experiments...')

        # queue results to be run
        while len(self.queue) > 0:
            exp, params = self.queue.popleft()
            results = self.experiment_to_results(exp, params, cell_name)
            self._results_queue.append(results)

        self.run_results()

    def run_next(self, cell_name: str):
        """
        Starts the next measurement.

        :param cell_name: Name of the cell.
        """
        Store.set('status_msg', 'Running experiments...')
        Store.set('runner_state', RunnerState.Running)

        exp, params = self.queue.popleft()
        results = self.experiment_to_results(exp, params, cell_name)
        self._results_queue.append(results)
        self.run_results()

    def run_results(self):
        """
        Runs all results in queue.
        """
        def on_finished():
            self._set_state(RunnerState.Standby)
            msg = 'Experiments complete'
            Store.set('status_msg', msg)
            logger.info(msg)
            self._results_runner = None

        def on_progress(results: Results, index: int, total: int):
            msg = f'Running experiment {index + 1} of {total}'
            Store.set('status_msg', msg)
            logger.info(msg)
            self.add_results(results)

        self._results_runner = ResultsRunner(self._results_queue)
        self._results_runner.finished.connect(on_finished)
        self._results_runner.progress.connect(on_progress)
        self._results_runner.start()

    def experiment_to_results(
        self,
        exp: Type[Experiment],
        params: CompleteParameters,
        cell_name: str,
    ) -> Results:
        """
        Converts an experiment with parameters to a results object that can be run.

        :param exp: Experiment.
        :param params: Parameters to use.
        :param cell_name: Cell name.
        :returns: Results.
        """
        system = Store.get('system')
        procedure = exp.create_procedure(params.to_dict_parameters())
        procedure.lamp = system.lamp
        procedure.smu = system.smu

        data_path = self.data_file(cell_name, exp.name)
        results = Results(procedure, data_path)

        return results

    def data_file(self, cell_name: str, exp_name: str) -> PathLike:
        """
        Runs a procedure.

        :param cell_name: Name of the cell.
        :param exp_name: Experiment name.
        :returns: Data path for an experiment.
        """
        user = Store.get('user')
        daily_dir = common.get_user_daily_data_directory(user)

        filename = f'{cell_name}--{exp_name}'
        data_path = os.path.join(daily_dir, filename)
        data_path += '.csv'
        data_path = common.unique_file(data_path)

        return data_path

    def add_results(self, result: Results):
        """
        """
        results = Store.get('experiment_results')
        results.append(result)
        Store.set('experiment_results', results)

    def abort(self):
        """
        Abort run.
        """
        self._set_state(RunnerState.Aborting)
        Store.set('status_msg', "Aborting measurements...")
        logger.info('Aborting measurements')

        self._results_runner.stop()


# ------------------------
# --- helper functions ---
# ------------------------

def copy_results_to_admin(results: Results):
    """
    Copy the results data to the daily admin directory.

    :param results: Results to copy.
    """
    user = Store.get('user')
    if user is not None:
        user = user.username

    common.copy_file_to_admin(results.data_filename, user=user)
