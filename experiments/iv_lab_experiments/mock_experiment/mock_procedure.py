import time
import random

from pymeasure.experiment import BooleanParameter, IntegerParameter, FloatParameter

from iv_lab_controller.base_classes import Procedure


class MockProcedure(Procedure):
    """
    A mock procedure.

    Data consists of [`index`, `value`] where `value` is between 0 and 100.
    """
    DATA_COLUMNS = ['index', 'value']

    iterations = IntegerParameter('Iterations')
    log = BooleanParameter('Log', default=False)
    min_value = IntegerParameter('Minimum value', default=0)
    max_value = IntegerParameter('Maximum value', default=100)
    sleep = FloatParameter('Sleep', default = 0.1)

    def execute(self):
        if self.log:
            print("starting mock")

        r_gen = random.Random()
        for i in range(self.iterations):
            if self.should_stop():
                if self.log:
                    print('should stop')

                break

            if self.log:
                print(f'iteration {i+1}...')

            value = r_gen.randint(
                self.min_value,
                self.max_value
            )

            data = {
                'index': i,
                'value': value
            }

            self.emit('results', data)
            time.sleep(self.sleep)

        if self.log:
            print("mock finished")
