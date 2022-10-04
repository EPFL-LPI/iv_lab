from time import sleep

from pymeasure.experiment import Procedure
from pymeasure.experiment import BooleanParameter, IntegerParameter


class MockProcedure(Procedure):
    """
    A mock procedure.
    """
    log = BooleanParameter('Log')
    times = IntegerParameter('Times')

    def execute(self):
        print("starting mock")
        for i in range(self.times):
            if self.log:
                print(f"iteration {i}...")

            sleep(1)

        print("mock finished")
