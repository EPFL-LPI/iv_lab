from enum import Enum, auto

from .lamps.keithley_filter_wheel import KeithleyFilterWheel
from .lamps.oriel_lss_7120 import OrielLSS7120
from .lamps.trinamic_tmcm_1260 import TrinamicTMCM1260
from .lamps.trinamic_tmcm_3110 import TrinamicTMCM3110
from .lamps.wavelabs_sinus_70 import WavelabsSinus70


class Lamp(Enum):
    KeithleyFilterWheel = auto()
    OrielLSS7120 = auto()
    TrinamicTMCM1260 = auto()
    TrinamicTMCM3110 = auto()
    WavelabsSinus70 = auto()


def get_controller(lamp: Lamp):
    """
    :param lamp: Type of lamp.
    :returns: Controller  for the specified lamp type.
    :raises ValueError: If invalid lamp type is given.
    """
    if lamp is Lamp.KeithleyFilterWheel:
        return KeithleyFilterWheel

    if lamp is Lamp.OrielLSS7120:
        return OrielLSS7120

    elif lamp is Lamp.TrinamicTMCM1260:
        return TrinamicTMCM1260

    elif lamp is Lamp.TrinamicTMCM3110:
        return TrinamicTMCM3110

    elif lamp is Lamp.WavelabsSinus70:
        return WavelabsSinus70

    # no match
    raise ValueError('Invalid lamp type')


def type_from_model(brand: str, model: str) -> Lamp:
    """
    Gets the type of lamp from the brand and model.

    :returns: Type of lamp.
    :raises ValueError: If type of lamp is not found.
    """
    brand = brand.lower()
    model = model.lower()

    if brand == 'keithley':
        if model == 'filter wheel':
            return Lamp.KeithleyFilterWheel

    elif brand == 'oriel':
        if model == 'lss 7120':
            return Lamp.OrielLSS7120

    elif brand == 'trinamic':
        if model == 'tmcm-3110':
            return Lamp.TrinamicTMCM3110

        elif model == 'tmcm-3110':
            return Lamp.TrinamicTMCM3110

    elif brand == 'wavelabs':
        if model == 'sinus70':
            return Lamp.WavelabsSinus70

    # no match found
    raise ValueError(f'Could not find matching lamp type with brand `{brand}` and model `{model}`')
