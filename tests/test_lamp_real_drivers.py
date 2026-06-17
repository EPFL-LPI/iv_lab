"""Tests for the real lamp drivers (Wavelabs, Oriel, Trinamic, Keithley
filter wheel, VeraSol).

No hardware library is required: pyvisa and pytrinamic are faked via
``sys.modules`` injection, the Wavelabs socket is faked by patching the
driver module's ``socket``, and the Keithley filter wheel uses a
recording dummy SMU.
"""

import sys
import types

import pytest

from iv_lab.config import LampSettings
from iv_lab.hardware import (
    HardwareCommandError,
    HardwareConnectionError,
    HardwareTimeoutError,
)
from iv_lab.hardware.lamp import create_lamp, get_lamp_driver
from iv_lab.hardware.lamp.drivers.keithley_filter import KeithleyFilterWheelLamp
from iv_lab.hardware.lamp.drivers.oriel import OrielLSS7120Lamp
from iv_lab.hardware.lamp.drivers.trinamic import TrinamicFilterWheelLamp
from iv_lab.hardware.lamp.drivers.verasol import VeraSolLamp
from iv_lab.hardware.lamp.drivers.wavelabs import WavelabsLamp
from iv_lab.hardware.smu.base import SMUChannel
from iv_lab.hardware.smu.drivers.emulated import EmulatedSMU


def lamp_settings(brand, model, light_levels, **overrides) -> LampSettings:
    data = {
        "brand": brand,
        "model": model,
        "emulate": False,
        "lightLevelDict": light_levels,
    }
    data.update(overrides)
    return LampSettings(**data)


def test_real_drivers_are_registered() -> None:
    assert get_lamp_driver("Wavelabs", "Sinus70") is WavelabsLamp
    assert get_lamp_driver("Oriel", "LSS-7120") is OrielLSS7120Lamp
    assert get_lamp_driver("VeraSol", "LSS-7120") is VeraSolLamp
    assert get_lamp_driver("keithley", "filter wheel") is KeithleyFilterWheelLamp
    for model in ("TMCM-1260", "TMCM-1160", "TMCM-3110"):
        assert get_lamp_driver("Trinamic", model) is TrinamicFilterWheelLamp


def test_driver_imports_do_not_import_hardware_libraries() -> None:
    # all driver modules are imported at the top of this file
    for module in ("pyvisa", "pytrinamic"):
        assert module not in sys.modules


# --- Wavelabs ---


class FakeWavelabsConnection:
    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.sent: list[str] = []
        self.closed = False
        self._pending = b""

    def settimeout(self, timeout) -> None:
        pass

    def sendall(self, data: bytes) -> None:
        self.sent.append(str(data, "utf-8"))
        self._pending = bytes(self.replies.pop(0), "utf-8")

    def recv(self, size: int) -> bytes:
        chunk, self._pending = self._pending[:size], self._pending[size:]
        return chunk

    def close(self) -> None:
        self.closed = True


class FakeWavelabsSocketModule:
    """Stands in for the stdlib socket module inside the driver."""

    AF_INET = object()
    SOCK_STREAM = object()

    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.sockets: list = []
        self.connections: list[FakeWavelabsConnection] = []

    def socket(self, family, kind):
        module = self

        class FakeServerSocket:
            def __init__(self) -> None:
                self.closed = False
                module.sockets.append(self)

            def bind(self, address) -> None:
                self.address = address

            def settimeout(self, timeout) -> None:
                pass

            def listen(self, backlog) -> None:
                pass

            def accept(self):
                connection = FakeWavelabsConnection(module.replies)
                module.connections.append(connection)
                return connection, ("127.0.0.1", 12345)

            def close(self) -> None:
                self.closed = True

        return FakeServerSocket()


OK_REPLY = "<WLRC iEC='0'/>"
ERROR_REPLY = r"<WLRC iEC='5' sError='No such recipe'\>x"


def make_wavelabs(monkeypatch, replies):
    settings = lamp_settings(
        "Wavelabs", "Sinus70", {"100": "1 sun, 1 h", "0": "dummy"}
    )
    lamp = WavelabsLamp(settings)
    fake_socket = FakeWavelabsSocketModule(replies)
    monkeypatch.setattr(
        "iv_lab.hardware.lamp.drivers.wavelabs.socket", fake_socket
    )
    lamp.connect()
    return lamp, fake_socket


def test_wavelabs_light_on_activates_and_starts_recipe(monkeypatch) -> None:
    lamp, fake_socket = make_wavelabs(monkeypatch, [OK_REPLY, OK_REPLY])

    lamp.light_on(100.0)

    assert lamp.light_is_on
    connection = fake_socket.connections[0]
    assert "ActivateRecipe iSeq='0' sRecipe='1 sun, 1 h'" in connection.sent[0]
    assert "StartRecipe iSeq='1'" in connection.sent[1]
    assert connection.closed
    assert fake_socket.sockets[0].closed


def test_wavelabs_light_on_zero_takes_no_action(monkeypatch) -> None:
    lamp, fake_socket = make_wavelabs(monkeypatch, [])

    lamp.light_on(0.0)

    # legacy: no socket interaction, but the light still counts as on
    assert lamp.light_is_on
    assert fake_socket.connections == []


def test_wavelabs_undefined_level_raises_legacy_message(monkeypatch) -> None:
    lamp, _ = make_wavelabs(monkeypatch, [])

    with pytest.raises(HardwareCommandError, match='"50.0 % sun" is not defined'):
        lamp.light_on(50.0)


def test_wavelabs_activate_error_raises_and_closes(monkeypatch) -> None:
    lamp, fake_socket = make_wavelabs(monkeypatch, [ERROR_REPLY])

    with pytest.raises(HardwareCommandError, match="No such recipe"):
        lamp.light_on(100.0)

    assert not lamp.light_is_on
    assert fake_socket.connections[0].closed


def test_wavelabs_light_off_cancels_recipe(monkeypatch) -> None:
    lamp, fake_socket = make_wavelabs(monkeypatch, [OK_REPLY, OK_REPLY, OK_REPLY])
    lamp.light_on(100.0)

    lamp.light_off()

    assert not lamp.light_is_on
    connection = fake_socket.connections[1]
    assert "CancelRecipe iSeq='0'" in connection.sent[0]


def test_wavelabs_light_off_when_off_does_nothing(monkeypatch) -> None:
    lamp, fake_socket = make_wavelabs(monkeypatch, [])

    lamp.light_off()

    assert fake_socket.connections == []


def test_wavelabs_turn_off_closes_open_socket(monkeypatch) -> None:
    lamp, fake_socket = make_wavelabs(monkeypatch, [OK_REPLY])
    # simulate a socket left open mid-command
    lamp._wavelabs_connect()
    assert lamp.connection_open

    lamp.turn_off()

    assert not lamp.connection_open
    assert fake_socket.connections[-1].closed


# --- Oriel LSS-7120 ---


class FakeOrielResource:
    def __init__(self) -> None:
        self.written: list[str] = []
        self.closed = False
        self.idn = "Newport Corporation,LSS-7120,sn123,rev1"
        self.ampl_reply = "100.0"
        self.outp_state = "OFF"

    def write(self, command: str) -> None:
        self.written.append(command)
        if command.startswith("OUTP"):
            self.outp_state = command.split(" ", 1)[1]

    def query(self, command: str) -> str:
        if command == "*IDN?":
            return self.idn
        if command == "AMPL?":
            return self.ampl_reply
        if command == "OUTP?":
            return self.outp_state
        raise AssertionError(f"unexpected query {command}")

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_pyvisa(monkeypatch):
    resource = FakeOrielResource()

    class FakeResourceManager:
        def open_resource(self, address):
            resource.address = address
            return resource

    module = types.ModuleType("pyvisa")
    module.ResourceManager = FakeResourceManager
    monkeypatch.setitem(sys.modules, "pyvisa", module)
    return resource


def make_oriel(**overrides) -> OrielLSS7120Lamp:
    settings = lamp_settings(
        "Oriel",
        "LSS-7120",
        {"100": 100, "50": 50, "0": 0},
        visa_address="ASRL5::INSTR",
        **overrides,
    )
    return OrielLSS7120Lamp(settings)


def test_oriel_connect_verifies_idn(fake_pyvisa) -> None:
    lamp = make_oriel()
    lamp.connect()

    assert lamp.is_connected()
    assert fake_pyvisa.address == "ASRL5::INSTR"


def test_oriel_bad_idn_raises_and_stays_disconnected(fake_pyvisa) -> None:
    fake_pyvisa.idn = "Some Other Device,XYZ"
    lamp = make_oriel()

    with pytest.raises(HardwareConnectionError, match="IDN incorrect"):
        lamp.connect()

    assert not lamp.is_connected()


def test_oriel_light_on_sets_amplitude_and_output(fake_pyvisa) -> None:
    lamp = make_oriel()
    lamp.connect()

    lamp.light_on(100.0)

    assert lamp.light_is_on
    # legacy writes the amplitude as light_int/100
    assert "AMPL 1.0" in fake_pyvisa.written
    assert "OUTP ON" in fake_pyvisa.written


def test_oriel_setpoint_mismatch_raises(fake_pyvisa) -> None:
    fake_pyvisa.ampl_reply = "98.0"  # outside the 0.5 legacy tolerance
    lamp = make_oriel()
    lamp.connect()

    with pytest.raises(HardwareCommandError, match="not properly set"):
        lamp.light_on(100.0)

    assert not lamp.light_is_on


def test_oriel_light_off_verifies_output(fake_pyvisa) -> None:
    lamp = make_oriel()
    lamp.connect()
    lamp.light_on(100.0)

    lamp.light_off()

    assert not lamp.light_is_on
    assert "OUTP OFF" in fake_pyvisa.written


def test_oriel_disconnect_closes_resource(fake_pyvisa) -> None:
    lamp = make_oriel()
    lamp.connect()
    lamp.disconnect()

    assert fake_pyvisa.closed


# --- Trinamic filter wheel ---


class FakeMotor:
    def __init__(self) -> None:
        self.moves: list[int] = []
        self.position_reached = True
        self.stopped = False
        self.drive_settings = types.SimpleNamespace()
        self.linear_ramp = types.SimpleNamespace()
        self.axis_parameters: dict[int, int] = {}
        self.ENUM = types.SimpleNamespace(MicrostepResolution256Microsteps=8)

    def set_axis_parameter(self, parameter, value) -> None:
        self.axis_parameters[parameter] = value

    def move_to(self, position: int) -> None:
        self.moves.append(position)

    def get_position_reached(self) -> bool:
        return self.position_reached

    def stop(self) -> None:
        self.stopped = True


class FakeTrinamicInterface:
    def __init__(self) -> None:
        self.reference_calls: list[tuple] = []
        self.homed = True
        self.closed = False

    def reference_search(self, search_type, motor_id):
        self.reference_calls.append((search_type, motor_id))
        if search_type == 2:  # status poll: 0 means done
            return 0 if self.homed else 1
        return None

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_pytrinamic(monkeypatch):
    state = types.SimpleNamespace(
        motor=FakeMotor(),
        interfaces=[],
        option_strings=[],
        modules_created=[],
    )

    class FakeConnectionContext:
        def __init__(self) -> None:
            self.interface = FakeTrinamicInterface()
            self.interface.homed = getattr(state, "homed", True)
            state.interfaces.append(self.interface)

        def __enter__(self):
            return self.interface

        def __exit__(self, *exc) -> bool:
            return False

    class FakeConnectionManager:
        def __init__(self, option_string: str = "") -> None:
            state.option_strings.append(option_string)

        def connect(self):
            return FakeConnectionContext()

    class FakeModule:
        def __init__(self, interface) -> None:
            state.modules_created.append(self)
            self.motors = [state.motor]

    connections_mod = types.ModuleType("pytrinamic.connections")
    connections_mod.ConnectionManager = FakeConnectionManager
    modules_mod = types.ModuleType("pytrinamic.modules")
    modules_mod.TMCM1260 = FakeModule
    modules_mod.TMCM1160 = FakeModule
    modules_mod.TMCM3110 = FakeModule
    pytrinamic_mod = types.ModuleType("pytrinamic")
    pytrinamic_mod.connections = connections_mod
    pytrinamic_mod.modules = modules_mod

    monkeypatch.setitem(sys.modules, "pytrinamic", pytrinamic_mod)
    monkeypatch.setitem(sys.modules, "pytrinamic.connections", connections_mod)
    monkeypatch.setitem(sys.modules, "pytrinamic.modules", modules_mod)

    return state


def make_trinamic(model="TMCM-1260") -> TrinamicFilterWheelLamp:
    settings = lamp_settings(
        "Trinamic", model, {"100": 17, "55": 77, "12": 137, "0": 257}
    )
    lamp = TrinamicFilterWheelLamp(settings)
    lamp.homing_poll_interval = 0.0
    lamp.move_poll_interval = 0.0
    return lamp


def microsteps(angle: float) -> int:
    return int(angle * (200 / 360) * 2**8)


def test_trinamic_connect_homes_and_parks_dark(fake_pytrinamic) -> None:
    lamp = make_trinamic()
    lamp.connect()

    assert lamp.is_connected()
    # reference search started, polled, and the wheel moved to the 0 % angle
    assert (0, 0) in fake_pytrinamic.interfaces[0].reference_calls
    assert fake_pytrinamic.motor.moves == [microsteps(257)]
    # legacy drive settings applied
    assert fake_pytrinamic.motor.drive_settings.max_current == 128
    assert fake_pytrinamic.motor.axis_parameters[193] == 135
    assert fake_pytrinamic.motor.linear_ramp.max_velocity == 5000


def test_trinamic_1160_uses_data_rate_option_only_for_homing(fake_pytrinamic) -> None:
    lamp = make_trinamic("TMCM-1160")
    lamp.connect()
    lamp.light_on(55.0)

    # legacy passes --data-rate 9600 when homing but not when moving
    assert fake_pytrinamic.option_strings == ["--data-rate 9600", ""]
    # 1160 uses the slow ramp parameters
    assert fake_pytrinamic.motor.linear_ramp.max_velocity == 200


def test_trinamic_homing_failure_raises(fake_pytrinamic) -> None:
    fake_pytrinamic.homed = False
    lamp = make_trinamic()
    lamp.trinamic_homing_timeout = 0.0

    with pytest.raises(HardwareConnectionError, match="Unable to reference"):
        lamp.connect()

    assert not lamp.is_connected()
    # the search was stopped (legacy reference_search(1, 0))
    assert (1, 0) in fake_pytrinamic.interfaces[0].reference_calls


def test_trinamic_light_on_moves_to_angle(fake_pytrinamic) -> None:
    lamp = make_trinamic()
    lamp.connect()

    lamp.light_on(55.0)

    assert lamp.light_is_on
    assert fake_pytrinamic.motor.moves[-1] == microsteps(77)


def test_trinamic_light_off_moves_to_dark_only_when_on(fake_pytrinamic) -> None:
    lamp = make_trinamic()
    lamp.connect()
    moves_after_connect = len(fake_pytrinamic.motor.moves)

    lamp.light_off()  # light not on: legacy does not move
    assert len(fake_pytrinamic.motor.moves) == moves_after_connect

    lamp.light_on(100.0)
    lamp.light_off()
    assert fake_pytrinamic.motor.moves[-1] == microsteps(257)
    assert not lamp.light_is_on


def test_trinamic_move_timeout_stops_motor_and_raises(fake_pytrinamic) -> None:
    lamp = make_trinamic()
    lamp.connect()
    fake_pytrinamic.motor.position_reached = False
    lamp.trinamic_move_timeout = 0.0

    with pytest.raises(HardwareTimeoutError):
        lamp.light_on(100.0)

    assert fake_pytrinamic.motor.stopped
    assert not lamp.light_is_on


# --- Keithley filter wheel ---


class RecordingSMU(EmulatedSMU):
    def __init__(self) -> None:
        super().__init__(None)
        self.ttl_levels: list[int] = []

    def set_ttl_level(self, level: int) -> None:
        self.ttl_levels.append(level)


def make_keithley_filter(smu) -> KeithleyFilterWheelLamp:
    settings = lamp_settings(
        "keithley", "filter wheel", {"100": 0, "50": 5, "20": 4, "0": 2}
    )
    lamp = KeithleyFilterWheelLamp(settings, smu=smu)
    lamp.light_on_wait = 0.0
    lamp.light_off_wait = 0.0
    return lamp


def test_keithley_filter_requires_smu() -> None:
    lamp = make_keithley_filter(None)

    with pytest.raises(HardwareConnectionError, match="requires the SMU"):
        lamp.connect()

    assert not lamp.is_connected()


def test_keithley_filter_connect_moves_wheel_dark() -> None:
    smu = RecordingSMU()
    lamp = make_keithley_filter(smu)

    lamp.connect()

    # legacy connect calls light_off: dark position code
    assert smu.ttl_levels == [2]
    assert not lamp.light_is_on


def test_keithley_filter_light_on_sets_ttl_code() -> None:
    smu = RecordingSMU()
    lamp = make_keithley_filter(smu)
    lamp.connect()

    lamp.light_on(50.0)

    assert lamp.light_is_on
    assert smu.ttl_levels[-1] == 5


def test_keithley_filter_light_off_always_moves_dark() -> None:
    smu = RecordingSMU()
    lamp = make_keithley_filter(smu)
    lamp.connect()

    lamp.light_off()  # legacy moves to dark even if already off

    assert smu.ttl_levels[-1] == 2


def test_keithley_filter_undefined_level_raises() -> None:
    smu = RecordingSMU()
    lamp = make_keithley_filter(smu)
    lamp.connect()

    with pytest.raises(HardwareCommandError, match="is not defined"):
        lamp.light_on(33.0)


def test_factory_passes_smu_to_keithley_filter() -> None:
    smu = RecordingSMU()
    settings = lamp_settings("keithley", "filter wheel", {"100": 0, "0": 2})

    lamp = create_lamp(settings, smu=smu)

    assert isinstance(lamp, KeithleyFilterWheelLamp)
    assert lamp.smu is smu
    # sanity: the dummy SMU still behaves like a BaseSMU
    assert smu.measure_current(SMUChannel.CELL) is not None


# --- VeraSol LSS-7120 ---


class FakeVeraSol:
    """Stand-in for _verasol_lib.VeraSol used in tests."""

    def __init__(self, resource_name=None, timeout_ms=10_000) -> None:
        self.resource_name = resource_name
        self._amplitude: float = 1.0
        self._output: bool = False
        self.idn_str: str = "Newport Corporation,LSS-7120,sn123,rev1"
        self.closed: bool = False

    def identify(self) -> str:
        return self.idn_str

    def set_amplitude(self, suns: float) -> None:
        self._amplitude = suns

    def get_amplitude(self) -> float:
        return self._amplitude

    def set_output(self, on: bool) -> None:
        self._output = on

    def get_output(self) -> bool:
        return self._output

    def set_spectrum_am15g(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_verasol_lib(monkeypatch):
    instance = FakeVeraSol()

    def _make(resource_name=None, timeout_ms=10_000):
        instance.resource_name = resource_name
        return instance

    module = types.ModuleType("iv_lab.hardware.lamp.drivers._verasol_lib")
    module.VeraSol = _make
    monkeypatch.setitem(
        sys.modules, "iv_lab.hardware.lamp.drivers._verasol_lib", module
    )
    return instance


def make_verasol(**overrides) -> VeraSolLamp:
    data = {"brand": "VeraSol", "model": "LSS-7120", "emulate": False}
    data.update(overrides)
    settings = LampSettings(**data)
    return VeraSolLamp(settings)


def test_verasol_connect_checks_idn(fake_verasol_lib) -> None:
    lamp = make_verasol()
    lamp.connect()

    assert lamp.is_connected()


def test_verasol_bad_idn_raises(fake_verasol_lib) -> None:
    fake_verasol_lib.idn_str = "Some Other Device,XYZ,000"
    lamp = make_verasol()

    with pytest.raises(HardwareConnectionError, match="IDN check failed"):
        lamp.connect()

    assert not lamp.is_connected()


def test_verasol_connect_missing_pyvisa_raises(monkeypatch) -> None:
    module = types.ModuleType("iv_lab.hardware.lamp.drivers._verasol_lib")

    def _raise(*args, **kwargs):
        raise ImportError("No module named 'pyvisa'")

    module.VeraSol = _raise
    monkeypatch.setitem(
        sys.modules, "iv_lab.hardware.lamp.drivers._verasol_lib", module
    )
    lamp = make_verasol()

    with pytest.raises(HardwareConnectionError, match="pyvisa"):
        lamp.connect()


def test_verasol_light_on_sets_amplitude_and_output(fake_verasol_lib) -> None:
    lamp = make_verasol()
    lamp.connect()

    lamp.light_on(100.0)

    assert lamp.light_is_on
    assert lamp.light_int == 100.0
    assert fake_verasol_lib._amplitude == pytest.approx(1.0)
    assert fake_verasol_lib._output is True


def test_verasol_light_on_50_percent(fake_verasol_lib) -> None:
    lamp = make_verasol()
    lamp.connect()

    lamp.light_on(50.0)

    assert lamp.light_is_on
    assert fake_verasol_lib._amplitude == pytest.approx(0.5)
    assert fake_verasol_lib._output is True


def test_verasol_light_on_zero_turns_output_off(fake_verasol_lib) -> None:
    lamp = make_verasol()
    lamp.connect()
    fake_verasol_lib._output = True   # simulate output was on

    lamp.light_on(0.0)

    assert lamp.light_is_on          # legacy: still counts as "on"
    assert lamp.light_int == 0.0
    assert fake_verasol_lib._output is False


def test_verasol_light_on_below_minimum_raises(fake_verasol_lib) -> None:
    lamp = make_verasol()
    lamp.connect()

    with pytest.raises(HardwareCommandError, match="minimum amplitude"):
        lamp.light_on(5.0)

    assert not lamp.light_is_on


def test_verasol_amplitude_mismatch_raises(fake_verasol_lib) -> None:
    # Fake an instrument that reports a different amplitude than requested.
    fake_verasol_lib._amplitude = 0.5  # will be reported after set_amplitude

    def _bad_set(self, suns):
        pass  # don't update _amplitude — simulate mismatch

    fake_verasol_lib.set_amplitude = _bad_set.__get__(fake_verasol_lib, FakeVeraSol)

    lamp = make_verasol()
    lamp.connect()

    with pytest.raises(HardwareCommandError, match="amplitude mismatch"):
        lamp.light_on(100.0)

    assert not lamp.light_is_on


def test_verasol_light_off_turns_output_off(fake_verasol_lib) -> None:
    lamp = make_verasol()
    lamp.connect()
    lamp.light_on(100.0)

    lamp.light_off()

    assert not lamp.light_is_on
    assert fake_verasol_lib._output is False


def test_verasol_light_off_safe_when_already_off(fake_verasol_lib) -> None:
    lamp = make_verasol()
    lamp.connect()

    lamp.light_off()   # must not raise

    assert not lamp.light_is_on


def test_verasol_disconnect_closes_lib(fake_verasol_lib) -> None:
    lamp = make_verasol()
    lamp.connect()
    lamp.disconnect()

    assert fake_verasol_lib.closed
    assert not lamp.is_connected()


def test_verasol_settings_without_light_level_dict() -> None:
    # VeraSol does not require lightLevelDict in its settings.
    settings = LampSettings(brand="VeraSol", model="LSS-7120", emulate=False)

    assert settings.lightLevelDict is None


def test_verasol_auto_discover_passes_none_resource(fake_verasol_lib) -> None:
    # When visa_address is omitted from settings, the driver passes None
    # to _verasol_lib.VeraSol so it auto-discovers the instrument.
    lamp = make_verasol()   # no visa_address keyword
    lamp.connect()

    assert fake_verasol_lib.resource_name is None


def test_verasol_explicit_visa_address_is_forwarded(fake_verasol_lib) -> None:
    lamp = make_verasol(visa_address="USB0::0x1028::0x0001::71201234::INSTR")
    lamp.connect()

    assert fake_verasol_lib.resource_name == "USB0::0x1028::0x0001::71201234::INSTR"


# --- _write() protocol tests (NI-VISA vs _WinUSBTMC acknowledgement encoding) ---
#
# The VeraSol acknowledges write commands with a 0-byte USB END (EOM) message.
# _WinUSBTMC translates this to the string "Ready"; NI-VISA returns "".
# Both must be accepted.  A non-empty unexpected string must raise RuntimeError.
#
# These tests load _verasol_lib with a *fake* pyvisa so the real pyvisa library
# never enters sys.modules (which would break test_smu_emulation isolation checks).


@pytest.fixture
def verasol_cls(monkeypatch):
    """Provide the VeraSol class loaded against a fake pyvisa.

    Uses monkeypatch to inject a fake pyvisa module before importing
    _verasol_lib, then cleans up _verasol_lib from sys.modules at teardown.
    Real pyvisa is never loaded, preserving sys.modules isolation for other tests.
    """
    import importlib

    fake_pyvisa = types.ModuleType("pyvisa")
    fake_pyvisa.errors = types.SimpleNamespace(VisaIOError=OSError)
    # monkeypatch records "pyvisa was absent" and will delete it at teardown
    monkeypatch.setitem(sys.modules, "pyvisa", fake_pyvisa)

    _key = "iv_lab.hardware.lamp.drivers._verasol_lib"
    sys.modules.pop(_key, None)           # remove any cached copy with real pyvisa
    lib = importlib.import_module(_key)   # fresh import against fake pyvisa

    yield lib.VeraSol

    sys.modules.pop(_key, None)           # remove so no live reference to fake pyvisa


class _FakeInstr:
    """Minimal pyvisa-resource stand-in: records writes and returns a preset ack."""

    def __init__(self, ack: str) -> None:
        self._ack = ack
        self.written: list[str] = []
        self.read_termination = "\n"   # default; __init__ should change this to ""
        self.write_termination = "\n"
        self.timeout = 10_000

    def write(self, cmd: str) -> None:
        self.written.append(cmd)

    def read(self) -> str:
        return self._ack

    def close(self) -> None:
        pass


def _make_write_obj(VeraSol, ack: str):
    """Create a VeraSol instance via object.__new__ with a preset fake _instr.

    Bypasses __init__ so no VISA connection is attempted.
    """
    obj = object.__new__(VeraSol)
    obj._instr = _FakeInstr(ack)
    return obj, obj._instr


def test_write_accepts_empty_ack_ni_visa(verasol_cls) -> None:
    # NI-VISA returns "" for the 0-byte EOM acknowledgement — must not raise.
    lamp, _ = _make_write_obj(verasol_cls, ack="")
    lamp._write("AMPLITUDE 1.000")


def test_write_accepts_ready_ack_winusbtmc(verasol_cls) -> None:
    # _WinUSBTMC returns "Ready" for the 0-byte EOM acknowledgement — must not raise.
    lamp, _ = _make_write_obj(verasol_cls, ack="Ready")
    lamp._write("OUTPUT ON")


def test_write_rejects_unexpected_ack(verasol_cls) -> None:
    # Any non-empty string that is not "ready" signals an instrument fault.
    lamp, _ = _make_write_obj(verasol_cls, ack="ERROR: invalid command")

    with pytest.raises(RuntimeError, match="Unexpected acknowledgement"):
        lamp._write("AMPLITUDE 1.000")


def test_read_termination_is_empty_on_ni_visa_path(verasol_cls, monkeypatch) -> None:
    # Verify that VeraSol.__init__ sets read_termination="" on the pyvisa resource,
    # so NI-VISA terminates reads on the USB END bit rather than waiting for "\n".
    fake_res = _FakeInstr(ack="")   # read_termination starts as "\n"
    fake_rm = types.SimpleNamespace(
        list_resources=lambda _: ["USB0::fake::INSTR"],
        open_resource=lambda _: fake_res,
        close=lambda: None,
    )
    sys.modules["pyvisa"].ResourceManager = lambda: fake_rm

    lamp = verasol_cls(resource_name="USB0::fake::INSTR")

    assert lamp._instr.read_termination == ""
