import pytest

from iv_lab.hardware import (
    HardwareCommandError,
    HardwareConnectionError,
    HardwareDevice,
    HardwareError,
    HardwareSafetyError,
    HardwareTimeoutError,
)


class DummyDevice(HardwareDevice):
    """Minimal concrete device recording lifecycle calls."""

    def __init__(self, name: str = "") -> None:
        super().__init__(name)
        self.calls: list[str] = []
        self.fail_on_open = False

    def _open(self) -> None:
        if self.fail_on_open:
            raise HardwareConnectionError("cannot open")
        self.calls.append("open")

    def _close(self) -> None:
        self.calls.append("close")


def test_abstract_base_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        HardwareDevice()  # type: ignore[abstract]


def test_dummy_subclass_lifecycle() -> None:
    device = DummyDevice()

    assert not device.is_connected()

    device.connect()
    assert device.is_connected()
    assert device.calls == ["open"]

    device.disconnect()
    assert not device.is_connected()
    assert device.calls == ["open", "close"]


def test_connect_when_connected_reconnects() -> None:
    # legacy SMU.connect / arduino.connect disconnect before re-connecting
    device = DummyDevice()
    device.connect()
    device.connect()

    assert device.is_connected()
    assert device.calls == ["open", "close", "open"]


def test_disconnect_when_not_connected_is_a_no_op() -> None:
    device = DummyDevice()
    device.disconnect()

    assert not device.is_connected()
    assert device.calls == []


def test_failed_open_leaves_device_disconnected() -> None:
    device = DummyDevice()
    device.fail_on_open = True

    with pytest.raises(HardwareConnectionError):
        device.connect()

    assert not device.is_connected()


def test_default_device_name_is_class_name() -> None:
    assert DummyDevice().name == "DummyDevice"
    assert DummyDevice("Keithley 2602").name == "Keithley 2602"


@pytest.mark.parametrize(
    "exc_type",
    [
        HardwareConnectionError,
        HardwareCommandError,
        HardwareTimeoutError,
        HardwareSafetyError,
    ],
)
def test_exceptions_inherit_from_hardware_error(exc_type: type) -> None:
    assert issubclass(exc_type, HardwareError)
    assert issubclass(exc_type, Exception)

    with pytest.raises(HardwareError):
        raise exc_type("boom")
