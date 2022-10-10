from iv_lab_controller.store import Store, Observer
from iv_lab_controller.base_classes import ValueWidget

from ...base_classes import ToggleUiInterface
from ...types import HardwareState, ApplicationState


class ParametersWidgetBase(ValueWidget, ToggleUiInterface):
    """
    Base class for common functionality of individual parameter widgets.
    """
    def init_observers(self):
        # hardware state
        def enable_hardware_ui(state: HardwareState):
            if state is HardwareState.Uninitialized:
                self.disable_ui()

            elif state is HardwareState.Initialized:
                self.enable_ui()

            elif state is HardwareState.Error:
                self.disable_ui()

            else:
                # @unreachable
                raise ValueError('Unknown hardware state')

        def hardware_state_changed(state: HardwareState, o_state: HardwareState):
            enable_hardware_ui(state)

        hardware_state_observer = Observer(changed=hardware_state_changed)
        Store.subscribe('hardware_state', hardware_state_observer)

        # application state
        def app_state_changed(state: ApplicationState, o_state: ApplicationState):
            if state is ApplicationState.Disabled:
                self.disable_ui()

            elif state is ApplicationState.Active:
                enable_hardware_ui(Store.get('hardware_state'))

            elif state is ApplicationState.Error:
                self.disable_ui()

            else:
                # @unreachable
                raise ValueError('Unknonw application state.')

        app_state_observer = Observer(changed=app_state_changed)
        Store.subscribe('application_state', app_state_observer)

        # reset fields
        Store.on('reset_parameter_fields', self.reset_fields)

    def reset_fields(self):
        """
        Reset fields.
        """
        raise NotImplementedError('`reset_fields` should be implemented by subclass')
