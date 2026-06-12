"""Lamp driver modules.

Importing this package imports every real driver module so their
``@register_lamp_driver`` decorators run. Optional hardware libraries
remain deferred inside the drivers' connection-time code, so this import
is safe on machines without them installed.

The emulated driver does not register; the factory selects it directly.
"""

from . import manual  # noqa: F401
