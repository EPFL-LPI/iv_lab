"""Arduino driver modules.

Importing this package imports every real driver module so their
``@register_arduino_driver`` decorators run. ``pyvisa`` remains deferred
inside the drivers' connection-time code.

The emulated driver does not register; the factory selects it directly.
"""

from . import shutter_controller  # noqa: F401
