from abc import abstractmethod
from typing import Any

from PyQt6.QtWidgets import QWidget


class ValueWidget(QWidget):
    """
    Value widget.
    """
    @property
    @abstractmethod
    def value(self) -> Any:
        """
        :returns: Widget value.
        """
        raise NotImplementedError()
