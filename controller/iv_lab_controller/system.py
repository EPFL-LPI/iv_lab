import sys
import inspect
import importlib.util
from typing import Tuple

from .base_classes.system import System


def load_system(file: str, emulate: bool = False) -> Tuple[str, System]:
    """
    :param file: Path to file containing the system definition.
    :param emulate: Run in emulation mode. [Default: False]
    :returns: Tuple of (name, System).
    :raises RuntimeError: If system can not be found.
    """
    # load file as python module
    spec = importlib.util.spec_from_file_location('_system', file)
    if spec is None:
        raise RuntimeError(f'File `{file}` could not be loaded as a Python module.')

    mod_system = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod_system)

    # extract class defined in module
    all_classes = inspect.getmembers(mod_system, inspect.isclass)
    mod_classes = [obj for obj in all_classes if obj[1].__module__ == '_system']

    if len(mod_classes) != 1:
        raise RuntimeError(f'System module must only define one class, found {len(mod_classes)}.')

    system = mod_classes[0]
    return system