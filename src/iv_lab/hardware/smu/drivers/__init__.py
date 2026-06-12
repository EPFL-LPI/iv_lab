"""SMU driver modules.

Importing this package imports every real driver module so their
``@register_smu_driver`` decorators run. Real hardware libraries remain
deferred inside the drivers' connection methods, so this import is safe
on machines without them installed.

The emulated driver does not register; the factory selects it directly.
"""

# Real driver modules (keithley_2400, keithley_26xx) are imported here as
# they are migrated, so that their registry decorators run.
