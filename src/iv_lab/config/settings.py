"""Typed loading of system settings from ``.json`` or ``.toml`` files.

This is the only module in the new package that reads settings files.
All other modules receive the typed settings objects defined here.

The JSON structure, key names, and nesting of the legacy file are preserved
exactly (see ``IVLab/system_settings.json`` and the per-system template
files in ``IVLab/``). During migration every model allows extra fields so
that existing machine configurations keep loading even if they contain keys
that are not mapped yet.

Defaults for optional fields replicate the legacy defaults set in
``IVLab/IVlab.py`` (``system.__init__`` for the ``IVsys`` section and
``SMU.__init__`` for the ``SMU`` section).
"""

from __future__ import annotations

import json
from pathlib import Path

import tomllib
from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Default settings filename.  The loader accepts .json and .toml.
DEFAULT_SETTINGS_FILENAME = "config/system_settings.toml"


class LegacyCompatibleModel(BaseModel):
    """Base model that tolerates unmapped legacy keys during migration."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ComputerSettings(LegacyCompatibleModel):
    """The ``computer`` section."""

    hardware: str
    os: str
    basePath: str
    #: Empty string disables the scrambled duplicate copy and ``ivlablog.txt``.
    sdPath: str


class IVSystemSettings(LegacyCompatibleModel):
    """The ``IVsys`` section."""

    sysName: str
    fullSunReferenceCurrent: float
    calibrationDateTime: str
    referenceDiodeImax: float
    saveDataAutomatic: bool = False
    checkVOCBeforeScan: bool = True
    firstPointDwellTime: float = 5.0
    MPPVoltageStepInitial: float = 0.002
    MPPVoltageStepMax: float = 0.002
    MPPVoltageStepMin: float = 0.001


class LampSettings(LegacyCompatibleModel):
    """The ``lamp`` section.

    ``lightLevelDict`` maps light level in percent of one sun to a
    lamp-type-specific value: a Wavelabs recipe name (str), a filter wheel
    angle (int/float), or a digital filter code (int). JSON only allows
    string keys; they are coerced to float here, as the legacy ``__main__``
    block of ``IVLab/IVlab.py`` does.
    """

    brand: str
    model: str
    emulate: bool
    display_name: str | None = Field(default=None, alias="display name")
    lightLevelDict: dict[float, int | float | str] | None = None
    visa_address: str | None = None
    visa_library: str | None = None

    @model_validator(mode="after")
    def _apply_legacy_rules(self) -> LampSettings:
        # Legacy syst_param.__init__ fills in 'display name' if absent.
        if self.display_name is None:
            self.display_name = f"{self.brand} {self.model}"
        # Legacy lamp.__init__ reads lightLevelDict for every brand except
        # 'manual' (case-sensitive comparison, as in the legacy code).
        # 'VeraSol' also skips the requirement: it accepts continuous amplitude
        # directly from light_int and does not need a lookup table.
        _no_dict_brands = {"manual", "verasol"}
        if self.brand.lower() not in _no_dict_brands and self.lightLevelDict is None:
            raise ValueError(
                f"lamp brand {self.brand!r} requires a 'lightLevelDict' entry"
            )
        return self


class SMUSettings(LegacyCompatibleModel):
    """The ``SMU`` section."""

    brand: str
    model: str
    visa_address: str
    visa_library: str
    emulate: bool
    referenceDiodeSenseMode: str = "2 wire"
    autorange: bool = True
    measSpeed: str = "normal"
    useReferenceDiode: bool = True
    #: Instrument serial number (the 3rd field of ``*IDN?``).  Optional; used
    #: to apply per-unit workarounds — e.g. a specific Keithley 2400 whose
    #: current autorange is unreliable falls back to a fixed range (see
    #: ``keithley_2400.py``).
    serial_number: str | None = None
    #: Serial (RS-232 / ``ASRL``) connection parameters.  Ignored for GPIB/USB
    #: addresses, where termination is handled by the bus (EOI).  For a serial
    #: Keithley these must match the instrument's front-panel RS-232 settings,
    #: or every read hangs until the VISA timeout.  ``None`` means "use the
    #: driver default" (see ``keithley_2400.py``).
    baud_rate: int | None = None
    read_termination: str | None = None
    write_termination: str | None = None
    #: VISA read timeout in milliseconds (applies to all interface types).
    timeout_ms: float | None = None


class ArduinoSettings(LegacyCompatibleModel):
    """The optional ``arduino`` section (shutter / cell selection)."""

    brand: str
    model: str
    visa_address: str
    visa_library: str | None = None
    emulate: bool = False


class SystemSettings(LegacyCompatibleModel):
    """Top-level model for ``system_settings.json``."""

    computer: ComputerSettings
    IVsys: IVSystemSettings
    lamp: LampSettings
    SMU: SMUSettings
    arduino: ArduinoSettings | None = None


def _update_toml_scalars(toml_node, data: dict) -> None:
    """Recursively update *toml_node* in place with values from *data*.

    Only keys already present in *toml_node* are touched; new keys are
    not inserted.  Non-string keys (e.g. float keys produced by Pydantic
    coercion of ``lightLevelDict``) are skipped — those values are only
    set during machine configuration, never by code.
    """
    for key, value in data.items():
        if not isinstance(key, str) or key not in toml_node:
            continue
        if isinstance(value, dict):
            _update_toml_scalars(toml_node[key], value)
        else:
            toml_node[key] = value


def load_settings(path: str | Path) -> SystemSettings:
    """Load and validate a system settings file (.json or .toml).

    The file format is detected from the file extension.  Both formats
    produce the same Python dict structure so all Pydantic validation
    applies identically.  ``tomllib`` is part of the Python standard
    library since 3.11.
    """
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".toml":
        raw = tomllib.loads(p.read_text(encoding="utf-8"))
    elif suffix == ".json":
        raw = json.loads(p.read_text(encoding="utf-8"))
    else:
        raise ValueError(
            f"unsupported settings file format {suffix!r} — expected .json or .toml"
        )
    return SystemSettings.model_validate(raw)


def save_settings(path: str | Path, settings: SystemSettings) -> None:
    """Write *settings* back to *path*, auto-detecting format by extension.

    For ``.json``: full rewrite via ``json.dumps``.
    For ``.toml``: round-trip via ``tomlkit`` — the existing file is
    parsed, only the values that are present in both the file and the
    model are updated in place, and the result is written back.  Comments
    and formatting in the original file are preserved.
    """
    p = Path(path)
    suffix = p.suffix.lower()
    data = settings.model_dump(by_alias=True, exclude_none=True)
    if suffix == ".json":
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    elif suffix == ".toml":
        import tomlkit

        doc = tomlkit.loads(p.read_text(encoding="utf-8"))
        _update_toml_scalars(doc, data)
        p.write_text(tomlkit.dumps(doc), encoding="utf-8")
    else:
        raise ValueError(
            f"unsupported settings file format {suffix!r} — expected .json or .toml"
        )
